"""El trabajo contable: subir archivos → revisar y mapear → calcular → cerrar → exportar."""
from __future__ import annotations

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
from ..importadores.detector import detectar_archivos
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
EXTENSIONES = (".xlsx", ".xlsm", ".xls", ".csv", ".txt", ".pdf")
ARCHIVOS_EJEMPLO = ["CONTABILIDAD.xls", "ESTADOS_FINANCIEROS.xlsx", "NOMINA__enero__2025.xlsx"]


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


def _periodo_sugerido(dets, empresa: Empresa) -> dict:
    """De dónde salen las fechas del periodo, en orden de confianza."""
    for d in dets:
        if d.formato == "plantilla" and d.paquete.empresa:
            desde = parse_fecha(d.paquete.empresa.get("periodo_desde"))
            hasta = parse_fecha(d.paquete.empresa.get("periodo_hasta"))
            if desde and hasta:
                return {"desde": desde, "hasta": hasta, "fuente": "Hoja EMPRESA de la plantilla"}
    for d in dets:
        if d.formato == "nomina" and d.incluir and d.resumen.get("mes") and d.resumen.get("año"):
            a, m = d.resumen["año"], d.resumen["mes"]
            fin = date(a + (m == 12), m % 12 + 1, 1)
            return {"desde": date(a, m, 1), "hasta": fin - timedelta(days=1),
                    "fuente": f"Mes de la nómina «{d.hoja}»"}
    return {"desde": empresa.periodo_desde, "hasta": empresa.periodo_hasta,
            "fuente": "Último periodo registrado del cliente"}


def _importar(archivos: list[tuple[str, bytes]], cliente_id: str | None) -> dict:
    empresa, cliente = _empresa_base(cliente_id)
    mapeador = Mapeador(repo_alias.de_cliente(empresa.nit))
    dets = detectar_archivos(archivos, mapeador, empresa)

    # La plantilla puede traer datos de empresa que completan la ficha.
    for d in dets:
        if d.formato == "plantilla" and d.paquete.empresa:
            empresa = Empresa.desde_dict({**a_json(empresa), **d.paquete.empresa})

    periodo = _periodo_sugerido(dets, empresa)
    empresa.periodo_desde, empresa.periodo_hasta = periodo["desde"], periodo["hasta"]

    sid = sesiones.crear({"dets": dets, "empresa": empresa, "resultado": None, "peticion": None},
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
                            archivos=[n for n, _ in archivos], hojas=len(dets), sesion=sid)

    return a_json({
        "repetidos": repetidos,
        "sesion_id": sid,
        "cliente_id": cliente_id,
        "cliente": cliente,
        "empresa": empresa,
        "periodo_sugerido": periodo,
        "mapeo": motor.items_mapeo(dets, mapeador),
        "hojas": [{"id": d.id, "archivo": d.archivo, "hoja": d.hoja, "formato": d.formato,
                   "formato_nombre": d.formato_nombre, "incluir": d.incluir, "motivo": d.motivo,
                   "resumen": d.resumen, "solo_auditoria": d.solo_auditoria,
                   "alertas": d.paquete.alertas, "filas_ignoradas": d.paquete.filas_ignoradas}
                  for d in dets],
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
    faltan = [n for n in ARCHIVOS_EJEMPLO if not (FUENTES / n).exists()]
    if faltan:
        raise HTTPException(404, f"No se encuentran en docs/fuentes: {', '.join(faltan)}")
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
@router.post("/calcular")
def calcular(peticion: dict = Body(...)):
    s = _sesion(peticion.get("sesion_id", ""))
    cliente_id = peticion.get("cliente_id") or s.get("cliente_id")

    empresa = Empresa.desde_dict({**a_json(s["empresa"]), **(peticion.get("empresa") or {})})
    if empresa.periodo_hasta < empresa.periodo_desde:
        raise HTTPException(400, "El periodo es inválido: la fecha final es anterior a la inicial.")

    mapeo = {k: v for k, v in (peticion.get("mapeo") or {}).items() if v}
    if peticion.get("recordar_alias", True) and mapeo:
        repo_alias.guardar(empresa.nit, mapeo, cliente_id)

    paquete, alertas, aud_nom, aud_ef = motor.preparar_paquete(
        s["dets"], peticion.get("incluir") or {}, mapeo
    )

    # Si el periodo no trae saldos iniciales, se toman del cierre anterior del cliente.
    if not paquete.saldos_iniciales and cliente_id:
        previo = repo_periodos.saldos_previos(cliente_id, empresa.periodo_desde)
        if previo:
            paquete.saldos_iniciales = previo[1]
            alertas.append(Alerta(
                "SALDOS", "info",
                f"Saldos iniciales tomados del cierre guardado al {previo[0].isoformat()}.",
            ))

    config = motor.Config.desde_dict(peticion.get("config"))
    try:
        resultado = motor.calcular(paquete, empresa, config, peticion.get("decisiones") or {},
                                   alertas, aud_nom, aud_ef)
    except Exception as ex:  # se informa en español sin tumbar el servidor
        raise HTTPException(500, f"No se pudo calcular: {ex}") from ex

    sesiones.actualizar(peticion["sesion_id"], resultado=resultado, peticion=peticion,
                        empresa_calculo=empresa, cliente_id=cliente_id)

    salida = a_json({k: v for k, v in resultado.items() if k != "mayor_ajustado"})

    # Se guarda en la base solo si el trabajo pertenece a un cliente del directorio.
    if cliente_id:
        # Estas dos no se tragan: son decisiones del contador, no fallos técnicos.
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
        try:
            guardados = repo_periodos.guardar_movimientos(cliente_id, periodo["id"], _movs_json(resultado))
            salida["periodo"] = periodo
            salida["guardado"] = True
            salida["movimientos_guardados"] = guardados
            repo_bitacora.registrar(
                "periodo_calculado", cliente_id, periodo=periodo["id"],
                desde=periodo["desde"], hasta=periodo["hasta"],
                cuentas=periodo["cuentas"], movimientos=guardados,
                utilidad=periodo.get("utilidad"), cuadra=periodo.get("cuadra"),
            )
        except Exception as ex:  # no se pierde el cálculo por un fallo de la base
            salida["guardado"] = False
            salida["aviso_guardado"] = f"El cálculo salió bien pero no se pudo guardar en la base: {ex}"
    else:
        salida["guardado"] = False

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


@router.get("/plantilla-demo")
def descargar_demo(caso: str = Query("completo")):
    clave = (caso or "completo").lower()
    return Response(
        gen_plantilla.construir(caso=clave),
        media_type=XLSX,
        headers={"Content-Disposition": f'attachment; filename="ejemplo_{clave}_CarlosCruz.xlsx"'},
    )
