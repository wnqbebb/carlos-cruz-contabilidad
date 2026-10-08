"""Histórico por cliente, libro diario consultable, sugerencias y buscador global."""
from __future__ import annotations

from fastapi import APIRouter, Body, HTTPException, Query
from fastapi.responses import Response

from ..contabilidad import libros
from ..exactitud import a_json
from ..exportar import excel, pdf
from ..inteligencia import sugerencias as sug
from ..inteligencia import tablero as tablero_cartera
from ..modelos import Empresa
from ..repositorio import clientes as repo_clientes
from ..repositorio import bitacora
from ..repositorio import importaciones
from ..repositorio import periodos as repo
from ..utils.numeros import parse_fecha

router = APIRouter(prefix="/api", tags=["análisis"])


def _cliente(cliente_id: str) -> dict:
    try:
        return repo_clientes.obtener(cliente_id)
    except repo_clientes.ErrorCliente as ex:
        raise HTTPException(404, str(ex)) from ex


# ── periodos de un cliente ──────────────────────────────────────────────────
@router.get("/clientes/{cliente_id}/periodos")
def periodos_del_cliente(cliente_id: str, limite: int = Query(120, ge=1, le=1000)):
    _cliente(cliente_id)
    return {"periodos": repo.listar(cliente_id, limite), "cierres": repo.listar_cierres(cliente_id)}


@router.get("/clientes/{cliente_id}/serie")
def serie_del_cliente(cliente_id: str, limite: int = Query(24, ge=2, le=120)):
    """Histórico listo para graficar: un punto por periodo, en orden cronológico."""
    _cliente(cliente_id)
    return {"serie": repo.serie(cliente_id, limite)}


@router.get("/clientes/{cliente_id}/movimientos")
def movimientos_del_cliente(
    cliente_id: str,
    cuenta: str = Query("", description="Prefijo de cuenta PUC: 1, 11, 1105…"),
    desde: str = Query(""),
    hasta: str = Query(""),
    pagina: int = Query(1, ge=1),
    por_pagina: int = Query(200, ge=1, le=2000),
    periodo_id: str = Query("", description="Solo el libro diario de ese periodo"),
):
    _cliente(cliente_id)
    return repo.movimientos(cliente_id, cuenta=cuenta, desde=parse_fecha(desde),
                            hasta=parse_fecha(hasta), pagina=pagina, por_pagina=por_pagina,
                            periodo_id=periodo_id)


@router.get("/clientes/{cliente_id}/sugerencias")
def sugerencias_del_cliente(cliente_id: str):
    _cliente(cliente_id)
    return sug.de_cliente(cliente_id)


# ── un periodo concreto ─────────────────────────────────────────────────────
@router.get("/periodos/{periodo_id}")
def periodo(periodo_id: str):
    try:
        return repo.obtener(periodo_id)
    except repo.ErrorPeriodo as ex:
        raise HTTPException(404, str(ex)) from ex


@router.patch("/periodos/{periodo_id}")
def nota_del_periodo(periodo_id: str, datos: dict = Body(...)):
    """Solo la nota de revisión: las cifras de un periodo se cambian recalculando, nunca a mano."""
    if set(datos) - {"nota"}:
        raise HTTPException(400, "Del periodo solo se puede editar la nota de revisión.")
    try:
        periodo = repo.poner_nota(periodo_id, str(datos.get("nota") or ""))
    except repo.ErrorPeriodo as ex:
        raise HTTPException(404, str(ex)) from ex
    bitacora.registrar("nota_periodo", periodo["cliente_id"], periodo=periodo_id)
    return periodo


@router.get("/periodos/{periodo_id}/resultado")
def resultado_del_periodo(periodo_id: str):
    """Vuelve a abrir unos estados financieros ya calculados, tal como quedaron."""
    datos = repo.resultado(periodo_id)
    if not datos:
        raise HTTPException(404, "Ese periodo no tiene un resultado guardado. Vuelva a calcularlo.")
    return {**datos, "resultado": completar_libros(datos["resultado"], periodo_id)}


LIBROS = {"libro-diario": ("libro_diario", "Libro_diario"), "mayor-balances": ("mayor_balances", "Mayor_y_balances")}


@router.get("/periodos/{periodo_id}/{libro}/{formato}")
def libro_del_periodo(periodo_id: str, libro: str, formato: str):
    """Un libro oficial suelto, en Excel o PDF: libro-diario o mayor-balances."""
    if libro not in LIBROS or formato not in ("excel", "pdf"):
        raise HTTPException(404, "Libro o formato desconocido.")
    clave, base = LIBROS[libro]
    resultado, empresa, _ = _resultado_guardado(periodo_id)
    rep = resultado["reportes"].get(clave)
    if not rep:
        raise HTTPException(404, "Ese periodo no tiene con qué armar el libro.")
    if formato == "pdf":
        return Response(pdf.generar(resultado, empresa, [clave]), media_type="application/pdf",
                        headers={"Content-Disposition": f'attachment; filename="{_nombre_archivo(empresa, base, "pdf")}"'})
    return Response(excel.reporte_suelto(rep, empresa), media_type=XLSX,
                    headers={"Content-Disposition": f'attachment; filename="{_nombre_archivo(empresa, base, "xlsx")}"'})


@router.get("/periodos/{periodo_id}/versiones")
def versiones_del_periodo(periodo_id: str):
    """Versiones anteriores guardadas antes de cada recálculo, cierre o reapertura."""
    return {"versiones": repo.versiones(periodo_id)}


@router.get("/versiones/{version_id}")
def ver_version(version_id: int):
    try:
        return repo.version(version_id)
    except repo.ErrorPeriodo as ex:
        raise HTTPException(404, str(ex)) from ex


@router.post("/versiones/{version_id}/restaurar")
def restaurar_version(version_id: int):
    """Devuelve el periodo al estado de esa versión. El estado actual queda como versión nueva."""
    try:
        periodo = repo.restaurar_version(version_id)
    except repo.ErrorPeriodo as ex:
        raise HTTPException(404, str(ex)) from ex
    bitacora.registrar("version_restaurada", periodo["cliente_id"],
                       periodo=periodo["id"], version=int(version_id))
    return periodo


@router.get("/clientes/{cliente_id}/actividad")
def actividad_del_cliente(cliente_id: str, limite: int = Query(40, ge=1, le=200)):
    """Bitácora del cliente: qué se hizo y cuándo."""
    _cliente(cliente_id)
    return {"actividad": bitacora.listar(cliente_id, limite),
            "importaciones": importaciones.listar(cliente_id, 20)}


@router.get("/actividad")
def actividad_general(limite: int = Query(20, ge=1, le=200)):
    """Últimas acciones de toda la cartera, para el Tablero."""
    return {"actividad": bitacora.listar(None, limite)}


@router.delete("/periodos/{periodo_id}")
def eliminar_periodo(periodo_id: str):
    try:
        periodo = repo.obtener(periodo_id)
        salida = repo.eliminar(periodo_id)
    except repo.ErrorPeriodo as ex:
        raise HTTPException(400, str(ex)) from ex
    bitacora.registrar("periodo_eliminado", periodo["cliente_id"],
                       desde=periodo["desde"], hasta=periodo["hasta"])
    return salida


@router.post("/periodos/{periodo_id}/reabrir")
def reabrir_periodo(periodo_id: str):
    try:
        periodo = repo.obtener(periodo_id)
        salida = repo.reabrir(periodo_id)
    except repo.ErrorPeriodo as ex:
        raise HTTPException(400, str(ex)) from ex
    bitacora.registrar("periodo_reabierto", periodo["cliente_id"],
                       periodo=periodo_id, desde=periodo["desde"], hasta=periodo["hasta"])
    return salida


# ── panorama general ────────────────────────────────────────────────────────
@router.get("/tablero")
def tablero():
    """El tablero del contador en una sola llamada: indicadores, tareas, meses, recientes y actividad.

    H13: los agregados de la cartera por mes (cerrados, abiertos, sin
    contabilizar) y los clientes al día o atrasados se cuentan aquí; la
    pantalla ya no los deduce.
    """
    return tablero_cartera.armar()


@router.post("/tareas/{clave}/posponer")
def posponer_tarea(clave: str):
    """«Posponer hasta mañana»: la tarea desaparece del tablero hasta mañana y queda en la bitácora."""
    codigo, _, cliente_id = clave.partition(":")
    hasta = tablero_cartera.manana()
    bitacora.registrar("tarea_pospuesta", cliente_id or None, clave=clave, codigo=codigo, hasta=hasta)
    return {"ok": True, "clave": clave, "hasta": hasta}


@router.post("/tareas/{clave}/hacer")
def hacer_tarea(clave: str):
    """«Hacer ahora»: solo deja constancia; la pantalla lleva al contador al sitio."""
    codigo, _, cliente_id = clave.partition(":")
    bitacora.registrar("tarea_iniciada", cliente_id or None, clave=clave, codigo=codigo)
    return {"ok": True}


@router.get("/buscar")
def buscar_global(q: str = Query("", description="NIT, razón social, municipio…"),
                  limite: int = Query(8, ge=1, le=25)):
    """Buscador del menú: por ahora busca clientes; la respuesta ya trae el tipo de cada resultado."""
    texto = (q or "").strip()
    if not texto:
        return {"q": "", "resultados": []}
    clientes = repo_clientes.sugerencias_busqueda(texto, limite)
    return {
        "q": texto,
        "resultados": [
            {"tipo": "cliente", "id": c["id"], "titulo": c["razon_social"],
             "subtitulo": f"NIT {c['nit_formateado']}" + (f" · {c['municipio']}" if c["municipio"] else ""),
             "estado": c["estado"]}
            for c in clientes
        ],
    }


# ── descargas de un periodo ya guardado ─────────────────────────────────────
# El libro se arma desde el resultado guardado en la base, sin necesidad de
# volver a subir los archivos. `exportar/excel.py` acepta los importes en
# cadena, que es como quedan guardados.
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _resultado_guardado(periodo_id: str) -> tuple[dict, Empresa, dict]:
    datos = repo.resultado(periodo_id)
    if not datos:
        raise HTTPException(
            404,
            "Ese periodo no tiene un resultado guardado. Vuelva a calcularlo desde «Trabajar».",
        )
    resultado = completar_libros(datos["resultado"], periodo_id)
    empresa = Empresa.desde_dict(resultado.get("empresa") or {})
    return resultado, empresa, datos


def completar_libros(resultado: dict, periodo_id: str) -> dict:
    """Los periodos guardados antes de la v2.2 no traen los libros oficiales.

    Se arman con lo que sí está guardado: el diario con los movimientos de la
    base y el mayor y balances con el balance de prueba ajustado. Nada se
    inventa: si no hay movimientos, el libro lo dice.
    """
    reportes = dict(resultado.get("reportes") or {})
    periodo = (resultado.get("resumen") or {}).get("periodo", "")
    if "libro_diario" not in reportes:
        movs = libros.movimientos_desde_guardados(repo.movimientos_de_periodo(periodo_id))
        reportes["libro_diario"] = a_json(libros.reporte_libro_diario(movs, periodo))
    if "mayor_balances" not in reportes and reportes.get("balance_ajustado"):
        reportes["mayor_balances"] = a_json(libros.mayor_balances_desde_balance(reportes["balance_ajustado"], periodo))
    return {**resultado, "reportes": reportes}


def _nombre_archivo(empresa: Empresa, base: str, ext: str) -> str:
    etiqueta = empresa.sigla or "".join(c for c in empresa.razon_social if c.isalnum())[:20] or "empresa"
    return f"{base}_{etiqueta}_{empresa.periodo_desde}_{empresa.periodo_hasta}.{ext}"


@router.get("/periodos/{periodo_id}/excel")
def excel_del_periodo(periodo_id: str):
    resultado, empresa, _ = _resultado_guardado(periodo_id)
    return Response(
        excel.libro_completo(resultado, empresa),
        media_type=XLSX,
        headers={"Content-Disposition": f'attachment; filename="{_nombre_archivo(empresa, "Contabilidad", "xlsx")}"'},
    )


@router.get("/periodos/{periodo_id}/pdf")
def pdf_del_periodo(periodo_id: str):
    resultado, empresa, _ = _resultado_guardado(periodo_id)
    return Response(
        pdf.generar(resultado, empresa),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{_nombre_archivo(empresa, "Estados_financieros", "pdf")}"'},
    )


@router.get("/periodos/{periodo_id}/saldos")
def saldos_del_periodo(periodo_id: str):
    resultado, empresa, _ = _resultado_guardado(periodo_id)
    return Response(
        excel.saldos_xlsx(resultado.get("saldos_siguiente") or []),
        media_type=XLSX,
        headers={"Content-Disposition": f'attachment; filename="{_nombre_archivo(empresa, "Saldos_iniciales_siguiente", "xlsx")}"'},
    )
