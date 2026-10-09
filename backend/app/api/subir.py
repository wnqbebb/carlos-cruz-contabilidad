"""Una sola puerta: suba lo que sea y el backend decide qué hacer con ello.

POR QUÉ EXISTE
Antes había dos puertas —«Importar Excel» en Clientes y «Subir» en Trabajar— y
el contador tenía que acertar cuál. Si subía la contabilidad de un cliente en
la carga masiva del directorio, veía «No se encontraron las columnas
obligatorias NIT y RAZÓN SOCIAL» y se quedaba ahí.

Ahora el flujo es:
  1. `POST /api/subir`              → se leen los archivos, se clasifican y se
                                      propone de quién son. Los bytes quedan
                                      guardados en la sesión.
  2. `POST /api/subir/{id}/confirmar` → el contador confirma (o crea el cliente)
                                      y se sigue, SIN volver a pedir el archivo.
"""
from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Body, File, HTTPException, Query, UploadFile

from ..contabilidad.puc import Mapeador
from ..exactitud import a_json
from ..importadores import clasificador as clas
from ..importadores import clientes_excel
from ..importadores import identidad as ident
from ..modelos import Empresa
from ..repositorio import alias as repo_alias
from ..repositorio import bitacora as repo_bitacora
from ..repositorio import clientes as repo_clientes
from ..repositorio import sesiones
from ..repositorio import subidas as repo_subidas
from ..seguridad import aislado
from ..seguridad import archivos as seg_archivos
from ..utils import nit as unit
from ..utils.numeros import NOMBRE_MES

router = APIRouter(prefix="/api", tags=["subir"])

EXTENSIONES = (".xlsx", ".xlsm", ".xls", ".csv", ".txt", ".pdf", ".docx", ".doc")
MAX_ARCHIVO = 25 * 1024 * 1024
MAX_TOTAL = 60 * 1024 * 1024


# ── 1. subir ────────────────────────────────────────────────────────────────
def _leer_subida(archivos: list[UploadFile]) -> list[tuple[str, bytes]]:
    datos: list[tuple[str, bytes]] = []
    total = 0
    for a in archivos:
        nombre = a.filename or "archivo"
        if not nombre.lower().endswith(EXTENSIONES):
            raise HTTPException(400, {
                "codigo": "formato_no_admitido",
                "mensaje": (f"«{nombre}» no es un formato que se pueda leer. Se aceptan "
                            + ", ".join(EXTENSIONES) + "."),
                "archivo": nombre,
            })
        contenido = a.file.read()
        total += len(contenido)
        if len(contenido) > MAX_ARCHIVO:
            raise HTTPException(413, {
                "codigo": "archivo_grande",
                "mensaje": f"«{nombre}» pesa más de {MAX_ARCHIVO // (1024 * 1024)} MB.",
            })
        datos.append((nombre, contenido))
    if not datos:
        raise HTTPException(400, {"codigo": "sin_archivos", "mensaje": "No se recibió ningún archivo."})
    if total > MAX_TOTAL:
        raise HTTPException(413, {
            "codigo": "subida_grande",
            "mensaje": f"Entre todos pesan más de {MAX_TOTAL // (1024 * 1024)} MB. Súbalos por partes.",
        })
    validar_o_rechazar(datos, EXTENSIONES)
    return datos


def validar_o_rechazar(datos: list[tuple[str, bytes]], permitidas: tuple[str, ...]) -> list[str]:
    """Revisión de seguridad de cada archivo antes de abrirlo (v2.3 · C20–C23)."""
    try:
        return seg_archivos.validar_todos(datos, permitidas)
    except seg_archivos.ArchivoRechazado as ex:
        raise HTTPException(400, {"codigo": ex.codigo, "mensaje": str(ex)}) from ex


def leer_aislado(ruta: str, *args):
    """Lee en un proceso aparte, con tiempo y memoria limitados (v2.3 · C24)."""
    try:
        return aislado.ejecutar(ruta, *args)
    except aislado.ArchivoNoProcesable as ex:
        raise HTTPException(422, {"codigo": ex.codigo, "mensaje": str(ex)}) from ex


def _parecidos(nombre: str, limite: int = 5) -> list[dict]:
    """Clientes que ya existen y se parecen al nombre encontrado (≥ 90 %)."""
    if not nombre:
        return []
    try:
        from rapidfuzz import fuzz
    except ImportError:  # pragma: no cover - dependencia declarada
        return []
    candidatos = repo_clientes.sugerencias_busqueda(nombre, 25)
    salida = []
    for c in candidatos:
        puntaje = fuzz.token_set_ratio(nombre.upper(), (c.get("titulo") or "").upper())
        if puntaje >= 90:
            salida.append({**c, "parecido": round(puntaje)})
    return sorted(salida, key=lambda x: -x["parecido"])[:limite]


def _propuesta(lectura: clas.Lectura, cliente_id: str | None) -> dict:
    """Lo que se le muestra al contador para que confirme de un vistazo."""
    campos = lectura.identidad
    nit = campos.valor("nit")
    razon = campos.valor("razon_social")

    cliente = None
    if cliente_id:
        try:
            cliente = repo_clientes.obtener(cliente_id)
        except repo_clientes.ErrorCliente:
            cliente = None

    # 5 · si el NIT ya está en el directorio, es ese cliente y no hay que preguntar.
    if cliente is None and nit:
        iguales = repo_clientes.listar(q=unit.limpiar(nit), estado="", por_pagina=5)["clientes"]
        exactos = [c for c in iguales if unit.limpiar(c["nit"]) == unit.limpiar(nit)]
        if exactos:
            cliente = exactos[0]

    coincidencias = [] if cliente else _parecidos(razon)

    falta = []
    if not cliente:
        if not razon:
            falta.append("razon_social")
        if not nit:
            falta.append("nit")

    ficha = lectura.ficha()
    formatos = []
    for h in lectura.hojas_de(clas.CONTABILIDAD):
        for parte in (h.razon or "").split(", "):
            if parte and parte not in formatos:
                formatos.append(parte)
    periodo = None
    hoy = date.today()
    fechas = sorted(f for f in lectura.fechas if f and f <= hoy)
    if fechas:
        periodo = {"desde": fechas[0].replace(day=1).isoformat(), "hasta": fechas[-1].isoformat(),
                   "texto": _texto_periodo(fechas[0], fechas[-1])}
    return {
        "cliente": cliente,
        "coincidencias": coincidencias,
        "identidad": campos.a_json(),
        "falta": falta,
        "contenido": formatos,
        "periodo": periodo,
        # La ficha completa que traen los documentos: se usa al crear el cliente.
        "ficha": ficha.a_json(),
        "hojas": [
            {"archivo": h.hoja.archivo, "hoja": h.hoja.nombre, "clase": h.clase,
             "formato": h.formato, "razon": h.razon, "filas": h.filas_datos}
            for h in lectura.hojas
        ],
        "ilegibles": lectura.ilegibles,
    }


def _texto_periodo(desde, hasta) -> str:
    """«enero a septiembre de 2026», «diciembre de 2025 a marzo de 2026», «marzo de 2026»."""
    m1, m2 = NOMBRE_MES[desde.month].lower(), NOMBRE_MES[hasta.month].lower()
    if (desde.year, desde.month) == (hasta.year, hasta.month):
        return f"{m1} de {desde.year}"
    if desde.year == hasta.year:
        return f"{m1} a {m2} de {hasta.year}"
    return f"{m1} de {desde.year} a {m2} de {hasta.year}"


@router.post("/subir")
def subir(archivos: list[UploadFile] = File(...), cliente_id: str = Query("")):
    """Lee los archivos, dice qué son y de quién, y guarda los bytes para seguir."""
    datos = _leer_subida(archivos)

    empresa, _ = (Empresa(), None)
    mapeador = Mapeador()
    if cliente_id:
        try:
            ficha = repo_clientes.obtener(cliente_id)
            empresa = repo_clientes.a_empresa(ficha)
            mapeador = Mapeador(repo_alias.de_cliente(empresa.nit))
        except repo_clientes.ErrorCliente as ex:
            raise HTTPException(404, str(ex)) from ex

    lectura = leer_aislado("app.importadores.clasificador.leer", datos, mapeador, empresa)
    clase = lectura.clase

    if clase == clas.DESCONOCIDO and lectura.ilegibles:
        raise HTTPException(400, {
            "codigo": "ilegible",
            "mensaje": lectura.ilegibles[0]["motivo"],
            "ilegibles": lectura.ilegibles,
        })

    # Los bytes van a disco; la sesión guarda solo dónde quedaron (A5).
    sid = sesiones.crear({"archivos": [], "clase": clase, "propuesta": None},
                         cliente_id=cliente_id or None)
    sesiones.actualizar(sid, archivos=repo_subidas.guardar(sid, datos))
    propuesta = _propuesta(lectura, cliente_id or None)
    sesiones.actualizar(sid, propuesta=propuesta)

    repo_bitacora.registrar("archivos_subidos", cliente_id or None,
                            archivos=[n for n, _ in datos], clase=clase, subida=sid)

    return a_json({"subida_id": sid, "clase": clase, **propuesta})


# ── 2. confirmar ────────────────────────────────────────────────────────────
@router.post("/subir/{subida_id}/confirmar")
def confirmar(subida_id: str, cuerpo: dict = Body(default={})):
    """Sigue adelante con lo que se subió, sin volver a pedir el archivo.

    `cuerpo` admite:
      · `cliente_id`  → trabajar sobre un cliente que ya existe
      · `crear`       → ficha mínima para darlo de alta ({nit, razon_social, …})
      · `clase`       → forzar «directorio» o «contabilidad» cuando es ambiguo
    """
    try:
        s = sesiones.obtener(subida_id)
    except sesiones.SesionExpirada as ex:
        raise HTTPException(404, {
            "codigo": "subida_expirada",
            "mensaje": "La subida caducó. Vuelva a arrastrar el archivo.",
        }) from ex

    archivos: list[tuple[str, bytes]] = repo_subidas.leer(s.get("archivos") or [])
    if not archivos:
        raise HTTPException(400, {"codigo": "sin_archivos", "mensaje": "Esa subida ya no tiene archivos."})

    clase = (cuerpo.get("clase") or s.get("clase") or clas.DESCONOCIDO).strip()
    cliente_id = (cuerpo.get("cliente_id") or s.get("cliente_id") or "").strip()

    # ── carga masiva del directorio ─────────────────────────────────────────
    if clase == clas.DIRECTORIO:
        informe = None
        for nombre, contenido in archivos:
            try:
                informe = clientes_excel.importar(
                    contenido, nombre,
                    actualizar_existentes=bool(cuerpo.get("actualizar_existentes", True)),
                    solo_revisar=bool(cuerpo.get("solo_revisar", False)),
                )
            except ValueError:
                continue
        if informe is None:
            raise HTTPException(400, {
                "codigo": "directorio_ilegible",
                "mensaje": "Ninguno de los archivos tenía columnas de NIT y razón social.",
            })
        if not cuerpo.get("solo_revisar"):
            repo_bitacora.registrar("clientes_importados", None, insertados=informe.get("insertados"),
                                    actualizados=informe.get("actualizados"))
        return {"clase": clas.DIRECTORIO, "informe": informe}

    # ── contabilidad de un cliente ──────────────────────────────────────────
    if not cliente_id:
        ficha = dict(cuerpo.get("crear") or {})
        if not ficha:
            # Se reconstruye desde lo que se detectó, por si la pantalla no lo mandó.
            propuesta = s.get("propuesta") or {}
            campos = (propuesta.get("identidad") or {}).get("campos") or {}
            ficha = {k: v["valor"] for k, v in campos.items() if k in ("nit", "razon_social", "dv")}
        if not ficha.get("nit") or not ficha.get("razon_social"):
            raise HTTPException(422, {
                "codigo": "faltan_datos_cliente",
                "mensaje": "Para guardar la contabilidad hace falta el nombre y el NIT o cédula del cliente.",
                "falta": [k for k in ("razon_social", "nit") if not ficha.get(k)],
            })
        ficha.setdefault("_origen", "documentos")
        # Un DV mal escrito en un documento no debe impedir crear el cliente: el
        # DV se calcula del NIT. Se descarta el leído si no coincide.
        if ficha.get("dv") and str(ficha["dv"]) != unit.digito_verificacion(ficha.get("nit")):
            ficha.pop("dv")
        socios = []
        extraida = (s.get("propuesta") or {}).get("ficha") or {}
        if not cuerpo.get("solo_minimo"):
            for campo, dato in (extraida.get("campos") or {}).items():
                if campo not in ficha and campo in repo_clientes.CAMPOS_FICHA and campo != "dv":
                    ficha[campo] = dato["valor"]
            socios = extraida.get("socios") or []
        try:
            cliente = repo_clientes.crear(ficha)
        except repo_clientes.ErrorCliente as ex:
            # Si ya existía con ese NIT, se trabaja sobre él en vez de fallar.
            iguales = repo_clientes.listar(q=unit.limpiar(ficha["nit"]), estado="", por_pagina=5)["clientes"]
            exacto = next((c for c in iguales if unit.limpiar(c["nit"]) == unit.limpiar(ficha["nit"])), None)
            if not exacto:
                raise HTTPException(400, str(ex)) from ex
            cliente = exacto
        else:
            if socios:
                repo_clientes.guardar_socios(cliente["id"], socios)
            repo_bitacora.registrar("cliente_creado", cliente["id"], nit=cliente["nit"],
                                    razon_social=cliente["razon_social"], origen="documentos",
                                    campos=sorted(k for k in ficha if not k.startswith("_")))
        cliente_id = cliente["id"]
        repo_bitacora.asociar_subida(subida_id, cliente_id)

    # Se reusa el mismo camino de siempre: los bytes ya están en memoria.
    from .trabajo import _importar

    salida = _importar(archivos, cliente_id)
    sesiones.cerrar(subida_id)
    repo_subidas.borrar(subida_id)
    return {"clase": clas.CONTABILIDAD, "cliente_id": cliente_id, **salida}


# ── identidad suelta, para la pantalla de crear cliente ────────────────────
@router.post("/identidad")
def solo_identidad(archivos: list[UploadFile] = File(...)):
    """Lee documentos y devuelve la ficha que se puede deducir de ellos.

    No guarda nada: la usa el formulario de cliente nuevo para llenarse solo.
    """
    datos = _leer_subida(archivos)
    lectura = leer_aislado("app.importadores.clasificador.leer", datos)
    return a_json({
        "identidad": lectura.identidad.a_json(),
        "ficha": lectura.ficha().a_json(),
        "sugerido_del_nombre": ident.nombre_desde_archivo(datos[0][0]),
        "ilegibles": lectura.ilegibles,
    })


@router.post("/clientes/{cliente_id}/ficha/comparar")
def comparar_ficha(cliente_id: str, archivos: list[UploadFile] = File(...)):
    """Qué campos de la ficha cambiarían con estos documentos. No guarda nada."""
    try:
        actual = repo_clientes.obtener(cliente_id)
    except repo_clientes.ErrorCliente as ex:
        raise HTTPException(404, str(ex)) from ex
    datos = _leer_subida(archivos)
    ficha = leer_aislado("app.importadores.clasificador.leer", datos).ficha()
    j = ficha.a_json()
    cambios = []
    for campo, dato in j["campos"].items():
        if campo not in actual:
            continue
        antes = actual.get(campo)
        antes_txt = "" if antes in (None, "") else str(antes)
        if _igual(antes_txt, dato["valor"]):
            continue
        cambios.append({"campo": campo, "actual": antes_txt, "nuevo": dato["valor"], "origen": dato["origen"],
                        "confianza": dato["confianza"], "conflicto": j["conflictos"].get(campo, [])})
    socios_actuales = actual.get("socios") or []
    return a_json({"cambios": cambios, "documentos": j["documentos"],
                   "socios": {"actual": len(socios_actuales), "nuevo": j["socios"], "origen": j["socios_origen"]}
                   if j["socios"] else None})


def _igual(a: str, b: str) -> bool:
    """Igualdad tolerante: mayúsculas, tildes, puntos de miles y decimales en cero no son un cambio."""
    from decimal import Decimal, InvalidOperation

    from ..utils.numeros import normalizar

    try:
        return Decimal(a) == Decimal(b)
    except (InvalidOperation, ValueError):
        pass
    return normalizar(a).replace(" ", "") == normalizar(b).replace(" ", "")
