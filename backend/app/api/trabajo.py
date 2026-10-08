"""El trabajo contable: subir archivos → revisar y mapear → calcular → cerrar → exportar."""
from __future__ import annotations

import calendar
from datetime import date, timedelta

from fastapi import APIRouter, Body, File, HTTPException, Query, UploadFile
from fastapi.responses import JSONResponse, Response

from .. import motor
from ..config import FUENTES
from ..contabilidad.puc import Mapeador
from ..exactitud import a_json
from ..exportar import excel, pdf
from ..exportar import casos
from ..exportar import plantilla as gen_plantilla
from ..contabilidad import periodizar
from ..importadores import auxiliares
from ..importadores.detector import detectar_conjunto
from ..modelos import Alerta, Empresa
from ..repositorio import alias as repo_alias
from ..repositorio import bitacora as repo_bitacora
from ..repositorio import clientes as repo_clientes
from ..repositorio import importaciones as repo_importaciones
from ..repositorio import periodos as repo_periodos
from ..repositorio import sesiones
from ..utils.numeros import parse_fecha

router = APIRouter(prefix="/api", tags=["trabajo"])

XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
MAX_ARCHIVO = 25 * 1024 * 1024
EXTENSIONES = (".xlsx", ".xlsm", ".xls", ".csv", ".txt", ".pdf", ".docx")
ARCHIVOS_EJEMPLO = ["CONTABILIDAD.xls", "ESTADOS_FINANCIEROS.xlsx", "NOMINA__enero__2025.xlsx"]


def tiene_archivos_de_muestra(nit: str) -> bool:
    """¿Hay en este equipo archivos de muestra de ESTE cliente? (H10)

    Los archivos de muestra son de una sola empresa (la de `data/empresa_fanant.json`)
    y viven fuera del repositorio. Solo se ofrecen en su ficha y solo si están.
    """
    import json

    from ..config import DATA
    from ..utils.nit import limpiar

    try:
        dueño = json.loads((DATA / "empresa_fanant.json").read_text(encoding="utf-8")).get("nit", "")
    except (OSError, ValueError):
        return False
    return bool(nit) and limpiar(nit) == limpiar(dueño) and all((FUENTES / n).exists() for n in ARCHIVOS_EJEMPLO)


# ── utilidades internas ─────────────────────────────────────────────────────
def _sesion(sid: str) -> dict:
    try:
        return sesiones.obtener(sid)
    except sesiones.SesionExpirada as ex:
        raise HTTPException(404, str(ex)) from ex


def _empresa_base(cliente_id: str | None) -> tuple[Empresa, dict | None]:
    """Empresa de partida: la ficha del cliente, o una VACÍA si todavía no hay cliente.

    Hasta la v2.1 aquí se devolvía la empresa de FANANT, así que subir un
    archivo sin elegir cliente calculaba la contabilidad a nombre de otra
    empresa. Ahora queda vacía: la identidad sale de los propios archivos
    (`importadores/identidad.py`) y, si falta, se le pide al contador.
    """
    if not cliente_id:
        return Empresa(), None
    try:
        cliente = repo_clientes.obtener(cliente_id)
    except repo_clientes.ErrorCliente as ex:
        raise HTTPException(404, str(ex)) from ex
    return repo_clientes.a_empresa(cliente), cliente


def _periodo_sugerido(dets, empresa: Empresa, conversion=None) -> dict:
    """De dónde salen las fechas del periodo, en orden de confianza."""
    for d in dets:
        if d.formato == "plantilla" and d.paquete.empresa:
            desde = parse_fecha(d.paquete.empresa.get("periodo_desde"))
            hasta = parse_fecha(d.paquete.empresa.get("periodo_hasta"))
            if desde and hasta:
                return {"desde": desde, "hasta": hasta, "fuente": "Hoja EMPRESA de la plantilla"}
    # Registros con fecha (listas de ventas, libro diario): el periodo es el que cubren.
    fechas = [m.fecha for d in dets if d.incluir and d.formato in ("auxiliares", "libro_diario")
              for m in d.paquete.movimientos if m.fecha]
    if conversion and conversion.desde and conversion.hasta:
        fechas += [conversion.desde, conversion.hasta]
    if fechas:
        ini, fin = min(fechas), max(fechas)
        ultimo = calendar.monthrange(fin.year, fin.month)[1]
        return {"desde": ini.replace(day=1), "hasta": fin.replace(day=ultimo),
                "fuente": "Fechas de los registros del archivo"}
    for d in dets:
        if d.formato in ("nomina", "balance") and d.incluir and d.resumen.get("mes") and d.resumen.get("año"):
            a, m = d.resumen["año"], d.resumen["mes"]
            fin = date(a + (m == 12), m % 12 + 1, 1)
            que = "la nómina" if d.formato == "nomina" else "corte del balance"
            return {"desde": date(a, m, 1), "hasta": fin - timedelta(days=1),
                    "fuente": f"Mes de {que} «{d.hoja}»"}
    return {"desde": empresa.periodo_desde, "hasta": empresa.periodo_hasta,
            "fuente": "Último periodo registrado del cliente"}


def _periodizacion(dets, periodo: dict, cliente: dict | None) -> dict:
    """¿Cubre varios meses? Entonces se ofrece procesarlo periodo a periodo (4.3)."""
    con_fecha = [d for d in dets if d.incluir and d.formato in ("auxiliares", "libro_diario")]
    desde, hasta = periodo["desde"], periodo["hasta"]
    meses = (hasta.year - desde.year) * 12 + hasta.month - desde.month + 1
    periodicidad = (cliente or {}).get("periodicidad") or "mensual"
    por = periodizar.MESES_POR_PERIODICIDAD.get(periodicidad, 1)
    partes = periodizar.dividir(desde, hasta, por)
    posible = bool(con_fecha) and len(partes) > 1
    return {
        "posible": posible, "meses": meses, "periodicidad": periodicidad, "meses_por_periodo": por,
        "periodos": [{"desde": a, "hasta": b} for a, b in partes] if posible else [],
        "defecto": "por_periodo" if posible else "unico",
    }


def _origenes(dets, conversion) -> dict[str, list[str]]:
    """Fila original de cada registro, para verla desde el libro diario."""
    salida: dict[str, list[str]] = {}
    if conversion:
        salida.update(conversion.origenes)
    for d in dets:
        salida.update(getattr(d, "origenes", {}) or {})
    return salida


def _importar(archivos: list[tuple[str, bytes]], cliente_id: str | None) -> dict:
    empresa, cliente = _empresa_base(cliente_id)
    mapeador = Mapeador(repo_alias.de_cliente(empresa.nit))
    dets, conversion = detectar_conjunto(archivos, mapeador, empresa)

    # La plantilla puede traer datos de empresa que completan la ficha.
    for d in dets:
        if d.formato == "plantilla" and d.paquete.empresa:
            empresa = Empresa.desde_dict({**a_json(empresa), **d.paquete.empresa})

    periodo = _periodo_sugerido(dets, empresa, conversion)
    empresa.periodo_desde, empresa.periodo_hasta = periodo["desde"], periodo["hasta"]

    sid = sesiones.crear({"dets": dets, "empresa": empresa, "resultado": None, "peticion": None,
                          "conversion": conversion, "mapeador": mapeador},
                         cliente_id=cliente_id)

    # Rastro de qué archivo entró y qué se reconoció en él (H08).
    repetidos = []
    for nombre, contenido in archivos:
        previo = repo_importaciones.ya_subido(cliente_id, contenido)
        if previo:
            repetidos.append({"archivo": nombre, **previo})
        repo_importaciones.registrar(cliente_id, nombre, contenido, [
            {"hoja": d.hoja, "formato": d.formato, "filas": d.resumen.get("movimientos") or 0,
             "alertas": d.paquete.alertas}
            for d in dets if d.archivo == nombre
        ])
    repo_bitacora.registrar("archivos_subidos", cliente_id,
                            archivos=[n for n, _ in archivos], hojas=len(dets), sesion=sid,
                            preguntas=len(conversion.preguntas) if conversion else 0)

    return a_json({
        "repetidos": repetidos,
        "sesion_id": sid,
        "cliente_id": cliente_id,
        "cliente": cliente,
        "empresa": empresa,
        "periodo_sugerido": periodo,
        "periodizacion": _periodizacion(dets, periodo, cliente),
        "preguntas": conversion.preguntas if conversion else [],
        "mapeo": motor.items_mapeo(dets, mapeador, conversion.mapeo_sugerido if conversion else None),
        "hojas": _hojas_json(dets),
    })


def _hojas_json(dets) -> list[dict]:
    return [{"id": d.id, "archivo": d.archivo, "hoja": d.hoja, "formato": d.formato,
             "formato_nombre": d.formato_nombre, "incluir": d.incluir, "motivo": d.motivo,
             "resumen": d.resumen, "solo_auditoria": d.solo_auditoria,
             "alertas": d.paquete.alertas, "filas_ignoradas": d.paquete.filas_ignoradas}
            for d in dets]


@router.get("/importar/{sid}")
def ver_importacion(sid: str):
    """Vuelve a abrir una subida que quedó a medias (con preguntas sin responder)."""
    s = _sesion(sid)
    if "dets" not in s:
        raise HTTPException(404, "Esa sesión no es una importación.")
    dets, conversion, empresa = s["dets"], s.get("conversion"), s["empresa"]
    cliente = None
    if s.get("cliente_id"):
        try:
            cliente = repo_clientes.obtener(s["cliente_id"])
        except repo_clientes.ErrorCliente:
            cliente = None
    periodo = {"desde": empresa.periodo_desde, "hasta": empresa.periodo_hasta,
               "fuente": "Sesión guardada"}
    return a_json({
        "repetidos": [], "sesion_id": sid, "cliente_id": s.get("cliente_id"), "cliente": cliente,
        "empresa": empresa, "periodo_sugerido": periodo,
        "periodizacion": _periodizacion(dets, periodo, cliente),
        "preguntas": conversion.preguntas if conversion else [],
        "mapeo": motor.items_mapeo(dets, s.get("mapeador") or Mapeador(), conversion.mapeo_sugerido if conversion else None),
        "hojas": _hojas_json(dets),
    })


# ── 1. subir archivos ───────────────────────────────────────────────────────
@router.post("/importar")
async def importar(archivos: list[UploadFile] = File(...), cliente_id: str = Query("")):
    datos = []
    for a in archivos:
        nombre = a.filename or "archivo.xlsx"
        if not nombre.lower().endswith(EXTENSIONES):
            raise HTTPException(
                400,
                f"«{nombre}»: formato no admitido. Se aceptan "
                + ", ".join(EXTENSIONES) + ".",
            )
        contenido = await a.read()
        if len(contenido) > MAX_ARCHIVO:
            raise HTTPException(413, f"{nombre}: el archivo pesa más de {MAX_ARCHIVO // (1024*1024)} MB.")
        datos.append((nombre, contenido))
    if not datos:
        raise HTTPException(400, "No se recibió ningún archivo.")
    return _importar(datos, cliente_id or None)


@router.post("/importar/ejemplo")
def importar_ejemplo(cliente_id: str = Query("")):
    _, cliente = _empresa_base(cliente_id or None)
    if not cliente or not tiene_archivos_de_muestra(cliente.get("nit", "")):
        raise HTTPException(404, "Este cliente no tiene archivos de muestra en este equipo.")
    return _importar([(n, (FUENTES / n).read_bytes()) for n in ARCHIVOS_EJEMPLO], cliente_id or None)


@router.get("/casos")
def listar_casos():
    """Los tres ejemplos que se pueden cargar sin datos reales."""
    return casos.listar()


@router.post("/importar/demo")
def importar_demo(cliente_id: str = Query(""), caso: str = Query("completo")):
    """Carga uno de los casos de ejemplo: completo, mediocre o basico."""
    datos = gen_plantilla.construir(caso=caso)
    nombre = f"ejemplo_{(caso or 'completo').lower()}.xlsx"
    return _importar([(nombre, datos)], cliente_id or None)


# ── 2. calcular ─────────────────────────────────────────────────────────────
def _con_respuestas(s: dict, peticion: dict, empresa: Empresa) -> dict[str, str]:
    """Vuelve a armar los asientos de los registros auxiliares con las respuestas del contador."""
    respuestas = {str(k): str(v) for k, v in (peticion.get("respuestas") or {}).items()}
    if s.get("conversion") is not None:
        conversion = auxiliares.convertir(s["dets"], respuestas, empresa)
        s["conversion"] = conversion
    return respuestas


def _saldos_de_apertura(paquete, alertas: list[Alerta], cliente_id: str | None, desde: date) -> None:
    """Saldos iniciales: los del archivo, o los del cierre anterior del cliente.

    Los saldos de apertura que salen de los registros auxiliares (cartera que
    venía de antes, inventario inicial) ya están en el cierre anterior si lo
    hay: se usan los del cierre y no se suman dos veces.
    """
    propios = [s for s in paquete.saldos_iniciales if not s.origen.startswith(auxiliares.PREFIJO_APERTURA)]
    apertura = [s for s in paquete.saldos_iniciales if s.origen.startswith(auxiliares.PREFIJO_APERTURA)]
    if propios:
        return
    previo = repo_periodos.saldos_previos(cliente_id, desde) if cliente_id else None
    if previo:
        paquete.saldos_iniciales = previo[1]
        alertas.append(Alerta("SALDOS", "info", f"Saldos iniciales tomados del cierre guardado al {previo[0].isoformat()}."))
        if apertura:
            alertas.append(Alerta(
                "SALDOS", "advertencia",
                f"El archivo trae {len(apertura) // 2} saldo(s) de apertura (cartera, cuentas por pagar o inventario "
                f"inicial), pero el cliente ya tiene un cierre al {previo[0].isoformat()}: se usan los saldos del cierre "
                "para no contarlos dos veces. Revise que la cartera del archivo coincida con la del cierre."))
    elif any(d for d in [paquete.movimientos]) and not paquete.saldos_iniciales:
        alertas.append(Alerta(
            "SALDOS", "info",
            "No hay saldos iniciales: caja y capital empiezan en 0. Si el negocio ya tenía dinero, mercancía o deudas al "
            "empezar el periodo, cargue un balance de apertura (hoja SALDOS INICIALES de la plantilla)."))


def _guardar(cliente_id: str, resultado: dict, salida: dict, peticion: dict, empresa: Empresa) -> dict:
    """Guarda un periodo calculado. Lanza las HTTPException de periodo cerrado o vacío."""
    try:
        periodo = repo_periodos.guardar_resultado(cliente_id, salida, peticion)
    except repo_periodos.PeriodoCerrado as ex:
        existente = repo_periodos.asegurar(cliente_id, empresa.periodo_desde, empresa.periodo_hasta)
        repo_bitacora.registrar("calculo_rechazado", cliente_id,
                                motivo="periodo_cerrado", periodo=existente["id"])
        raise HTTPException(409, {
            "codigo": "periodo_cerrado",
            "mensaje": str(ex),
            "periodo_id": existente["id"],
            "desde": existente["desde"], "hasta": existente["hasta"],
        }) from ex
    except repo_periodos.ResultadoVacio as ex:
        repo_bitacora.registrar("calculo_rechazado", cliente_id, motivo="resultado_vacio")
        raise HTTPException(422, {"codigo": "resultado_vacio", "mensaje": str(ex)}) from ex
    guardados = repo_periodos.guardar_movimientos(cliente_id, periodo["id"], _movs_json(resultado))
    repo_bitacora.registrar(
        "periodo_calculado", cliente_id, periodo=periodo["id"],
        desde=periodo["desde"], hasta=periodo["hasta"],
        cuentas=periodo["cuentas"], movimientos=guardados,
        utilidad=periodo.get("utilidad"), cuadra=periodo.get("cuadra"),
    )
    return {"periodo": periodo, "movimientos_guardados": guardados}


def _salida(resultado: dict, origenes: dict[str, list[str]]) -> dict:
    salida = a_json({k: v for k, v in resultado.items() if k != "mayor_ajustado"})
    usados = {m["origen"] for m in _movs_json(resultado) if m.get("origen")}
    salida["origenes"] = {k: v for k, v in origenes.items() if k in usados}
    return salida


@router.post("/calcular")
def calcular(peticion: dict = Body(...)):
    s = _sesion(peticion.get("sesion_id", ""))
    cliente_id = peticion.get("cliente_id") or s.get("cliente_id")

    empresa = Empresa.desde_dict({**a_json(s["empresa"]), **(peticion.get("empresa") or {})})
    if empresa.periodo_hasta < empresa.periodo_desde:
        raise HTTPException(400, "El periodo es inválido: la fecha final es anterior a la inicial.")

    _con_respuestas(s, peticion, empresa)
    conversion = s.get("conversion")

    mapeo = {k: v for k, v in (peticion.get("mapeo") or {}).items() if v}
    # Nombres que aparecen por una respuesta (p. ej. ventas a crédito según la cartera)
    # y que la pantalla todavía no conocía: se usa la cuenta que propone el importador.
    if conversion:
        for nombre, codigo in conversion.mapeo_sugerido.items():
            mapeo.setdefault(nombre, codigo)
    if peticion.get("recordar_alias", True) and peticion.get("mapeo"):
        repo_alias.guardar(empresa.nit, {k: v for k, v in peticion["mapeo"].items() if v}, cliente_id)

    paquete, alertas, aud_nom, aud_ef = motor.preparar_paquete(
        s["dets"], peticion.get("incluir") or {}, mapeo
    )
    config = motor.Config.desde_dict(peticion.get("config"))
    decisiones = peticion.get("decisiones") or {}
    origenes = _origenes(s["dets"], conversion)

    if peticion.get("periodizacion") == "por_periodo" and cliente_id and periodizar.todo_con_fecha(paquete):
        return _calcular_por_periodos(s, peticion, cliente_id, empresa, paquete, alertas, aud_nom, aud_ef,
                                      config, decisiones, origenes)

    _saldos_de_apertura(paquete, alertas, cliente_id, empresa.periodo_desde)
    try:
        resultado = motor.calcular(paquete, empresa, config, decisiones, alertas, aud_nom, aud_ef)
    except Exception as ex:  # se informa en español sin tumbar el servidor
        raise HTTPException(500, f"No se pudo calcular: {ex}") from ex

    sesiones.actualizar(peticion["sesion_id"], resultado=resultado, peticion=peticion,
                        empresa_calculo=empresa, cliente_id=cliente_id)
    salida = _salida(resultado, origenes)

    # Se guarda en la base solo si el trabajo pertenece a un cliente del directorio.
    if cliente_id:
        try:
            salida.update(_guardar(cliente_id, resultado, salida, peticion, empresa))
            salida["guardado"] = True
        except HTTPException:
            raise
        except Exception as ex:  # no se pierde el cálculo por un fallo de la base
            salida["guardado"] = False
            salida["aviso_guardado"] = f"El cálculo salió bien pero no se pudo guardar en la base: {ex}"
    else:
        salida["guardado"] = False

    return JSONResponse(salida)


def _calcular_por_periodos(s, peticion, cliente_id, empresa, paquete, alertas, aud_nom, aud_ef,
                           config, decisiones, origenes) -> JSONResponse:
    """Procesa el archivo periodo a periodo: calcula, guarda y cierra cada uno.

    El cierre de cada periodo abre el siguiente. El ÚLTIMO queda calculado y sin
    cerrar, para que el contador lo revise y lo cierre él (o se cierra también
    si la petición trae `cerrar_ultimo`). Un periodo que ya estaba cerrado no se
    toca: se deja como está y su cierre abre el siguiente.
    """
    cliente = repo_clientes.obtener(cliente_id)
    por = periodizar.MESES_POR_PERIODICIDAD.get(cliente.get("periodicidad") or "mensual", 1)
    partes = periodizar.dividir(empresa.periodo_desde, empresa.periodo_hasta, por)
    cerrar_ultimo = bool(peticion.get("cerrar_ultimo"))
    resumen_periodos = []
    ultimo = None
    for i, (desde, hasta) in enumerate(partes):
        emp_i = Empresa.desde_dict({**a_json(empresa), "periodo_desde": desde, "periodo_hasta": hasta})
        sub = periodizar.recortar(paquete, desde, hasta, primero=(i == 0), metodo=config.metodo_inventario)
        if not sub.movimientos and not sub.saldos_iniciales:
            resumen_periodos.append({"desde": desde, "hasta": hasta, "estado": "sin_movimientos"})
            continue
        existente = repo_periodos.buscar(cliente_id, desde, hasta)
        if existente and existente["estado"] == "cerrado":
            resumen_periodos.append({"desde": desde, "hasta": hasta, "estado": "ya_cerrado", "periodo_id": existente["id"],
                                     "utilidad": existente.get("utilidad"), "cuadra": existente.get("cuadra")})
            continue
        alertas_i = [a for a in alertas]
        _saldos_de_apertura(sub, alertas_i, cliente_id, desde)
        try:
            resultado = motor.calcular(sub, emp_i, config, decisiones, alertas_i, aud_nom, aud_ef)
        except Exception as ex:
            raise HTTPException(500, f"No se pudo calcular {desde.isoformat()} a {hasta.isoformat()}: {ex}") from ex
        pet_i = {**peticion, "empresa": {**(peticion.get("empresa") or {}),
                                        "periodo_desde": desde.isoformat(), "periodo_hasta": hasta.isoformat()}}
        salida = _salida(resultado, origenes)
        guardado = _guardar(cliente_id, resultado, salida, pet_i, emp_i)
        periodo = guardado["periodo"]
        es_ultimo = i == len(partes) - 1
        estado = "calculado"
        if not es_ultimo or cerrar_ultimo:
            repo_periodos.cerrar(cliente_id, periodo["id"], a_json(resultado["saldos_siguiente"]))
            repo_bitacora.registrar("periodo_cerrado", cliente_id, periodo=periodo["id"], fecha_corte=hasta.isoformat(),
                                    cuentas=len(resultado["saldos_siguiente"]), modo="por_periodo")
            estado = "cerrado"
        resumen_periodos.append({"desde": desde, "hasta": hasta, "estado": estado, "periodo_id": periodo["id"],
                                 "utilidad": resultado["resumen"]["utilidad_neta"],
                                 "cuadra": bool(periodo.get("cuadra"))})
        ultimo = (resultado, salida, emp_i, pet_i, guardado)

    if ultimo is None:
        raise HTTPException(422, {"codigo": "resultado_vacio",
                                  "mensaje": "Ningún periodo tenía movimientos para calcular; no se guardó nada."})
    resultado, salida, emp_i, pet_i, guardado = ultimo
    sesiones.actualizar(peticion["sesion_id"], resultado=resultado, peticion=pet_i, empresa_calculo=emp_i,
                        cliente_id=cliente_id)
    salida.update(guardado)
    salida["guardado"] = True
    salida["periodos_procesados"] = a_json(resumen_periodos)
    return JSONResponse(salida)


def _movs_json(resultado: dict) -> list[dict]:
    """Movimientos del libro mayor ajustado, para guardarlos como libro diario."""
    mayor = resultado.get("mayor_ajustado") or {}
    filas = []
    for cuenta in mayor.values():
        for m in getattr(cuenta, "movimientos", []) or []:
            filas.append({
                "cuenta": getattr(m, "cuenta", ""),
                "nombre_cuenta": getattr(m, "nombre_cuenta", ""),
                "debito": getattr(m, "debito", 0), "credito": getattr(m, "credito", 0),
                "fecha": getattr(m, "fecha", None), "comprobante": getattr(m, "comprobante", ""),
                "tipo": getattr(m, "tipo", ""), "tercero_id": getattr(m, "tercero_id", ""),
                "tercero_nombre": getattr(m, "tercero_nombre", ""),
                "descripcion": getattr(m, "descripcion", ""), "origen": getattr(m, "origen", ""),
            })
    return a_json(filas)


# ── 3. resultado, cierre y exportación ──────────────────────────────────────
def _resultado(sid: str) -> tuple[dict, Empresa]:
    s = _sesion(sid)
    if not s.get("resultado"):
        raise HTTPException(400, "Primero ejecute «Calcular todo».")
    return s["resultado"], s["empresa_calculo"]


def _nombre(empresa: Empresa, base: str, ext: str) -> str:
    etiqueta = empresa.sigla or "".join(c for c in empresa.razon_social if c.isalnum())[:20] or "empresa"
    return f"{base}_{etiqueta}_{empresa.periodo_desde.isoformat()}_{empresa.periodo_hasta.isoformat()}.{ext}"


@router.get("/exportar/{sid}/excel")
def exportar_excel(sid: str):
    res, emp = _resultado(sid)
    return Response(excel.libro_completo(res, emp), media_type=XLSX,
                    headers={"Content-Disposition": f'attachment; filename="{_nombre(emp, "Contabilidad", "xlsx")}"'})


@router.get("/exportar/{sid}/pdf")
def exportar_pdf(sid: str):
    res, emp = _resultado(sid)
    return Response(pdf.generar(res, emp), media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="{_nombre(emp, "Estados_financieros", "pdf")}"'})


@router.get("/exportar/{sid}/saldos")
def exportar_saldos(sid: str):
    res, emp = _resultado(sid)
    return Response(excel.saldos_xlsx(res["saldos_siguiente"]), media_type=XLSX,
                    headers={"Content-Disposition": f'attachment; filename="{_nombre(emp, "Saldos_iniciales_siguiente", "xlsx")}"'})


@router.post("/cierre/{sid}")
def cerrar(sid: str):
    s = _sesion(sid)
    res, emp = _resultado(sid)
    cliente_id = s.get("cliente_id")
    if not cliente_id:
        raise HTTPException(
            400,
            "Para guardar un cierre hay que trabajar sobre un cliente del directorio. "
            "Abra el cliente y repita la carga desde su ficha.",
        )
    periodo = repo_periodos.asegurar(cliente_id, emp.periodo_desde, emp.periodo_hasta)
    salida = repo_periodos.cerrar(cliente_id, periodo["id"], a_json(res["saldos_siguiente"]))
    repo_bitacora.registrar("periodo_cerrado", cliente_id, periodo=periodo["id"],
                            fecha_corte=salida["fecha_corte"], cuentas=salida["cuentas"])
    return salida


@router.get("/plantilla")
def descargar_plantilla():
    return Response(gen_plantilla.construir(False), media_type=XLSX,
                    headers={"Content-Disposition": 'attachment; filename="plantilla_contable_CarlosCruz.xlsx"'})


