"""«Datos del periodo»: ver, editar, deshacer y descargar para editar (rescate H7, J5 y J6).

    GET  /api/periodos/{id}/datos              tablas editables + validación + archivos
    POST /api/periodos/{id}/datos/validar      valida sin guardar (para avisar mientras escribe)
    PUT  /api/periodos/{id}/datos              guarda, recalcula y deja la versión anterior
    POST /api/periodos/{id}/deshacer           vuelve a la versión de antes del último guardado
    POST /api/periodos/{id}/recalcular         vuelve a procesar con lo guardado
    POST /api/periodos/{id}/archivos/quitar    saca todo lo que aportó un archivo
    GET  /api/periodos/{id}/datos/excel        plantilla oficial con los datos actuales
"""
from __future__ import annotations

import logging
from datetime import date

from fastapi import APIRouter, Body, HTTPException
from fastapi.responses import Response

from ..contabilidad import editar, entrada as E
from ..repositorio import bitacora
from ..repositorio import periodos as repo
from ..seguridad import incidentes

router = APIRouter(prefix="/api", tags=["datos del periodo"])
log = logging.getLogger("carloscruz.datos")
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _periodo(periodo_id: str) -> dict:
    try:
        return repo.obtener(periodo_id)
    except repo.ErrorPeriodo as ex:
        raise HTTPException(404, str(ex)) from ex


def _entrada(p: dict) -> dict:
    datos = repo.entrada(p["id"])
    if datos:
        return datos
    # Periodo de antes del rescate: se arma con su libro diario y los saldos del cierre anterior.
    guardado = repo.resultado(p["id"])
    previos = repo.saldos_previos(p["cliente_id"], date.fromisoformat(p["desde"]))
    return editar.entrada_desde_guardado(p, (guardado or {}).get("resultado"), repo.movimientos_de_periodo(p["id"]),
                                         previos[1] if previos else [])


def _vista(p: dict, entrada: dict) -> dict:
    paquete, *_ = E.piezas(entrada)
    return {
        "periodo": p,
        "editable": p["estado"] != "cerrado",
        "motivo_bloqueo": "" if p["estado"] != "cerrado" else
        "Este periodo está cerrado. Reábralo para editar: el cierre actual queda guardado en el historial.",
        "tablas": editar.tablas(entrada),
        "validacion": editar.validar(paquete),
        "archivos": editar.archivos(entrada),
        "versiones": len(repo.versiones(p["id"])),
    }


@router.get("/periodos/{periodo_id}/datos")
def ver_datos(periodo_id: str):
    p = _periodo(periodo_id)
    return _vista(p, _entrada(p))


@router.post("/periodos/{periodo_id}/datos/validar")
def validar_datos(periodo_id: str, cambios: dict = Body(...)):
    p = _periodo(periodo_id)
    try:
        nueva = editar.aplicar(_entrada(p), cambios.get("tablas") or {})
    except editar.ErrorEdicion as ex:
        raise HTTPException(400, {"codigo": "datos_invalidos", "mensaje": str(ex)}) from ex
    paquete, *_ = E.piezas(nueva)
    return editar.validar(paquete)


def _guardar(p: dict, nueva: dict, motivo: str) -> dict:
    if p["estado"] == "cerrado":
        raise HTTPException(409, {"codigo": "periodo_cerrado", "mensaje":
                                  "Este periodo está cerrado. Reábralo para editar: el cierre actual queda en el historial."})
    paquete, *_ = E.piezas(nueva)
    validacion = editar.validar(paquete)
    if validacion["errores"]:
        raise HTTPException(422, {"codigo": "datos_con_errores", "mensaje": validacion["errores"][0]["mensaje"],
                                  "validacion": validacion})
    try:
        crudo = E.recalcular(nueva)
    except Exception as ex:   # el contador ve un mensaje; el detalle va al registro
        codigo = incidentes.nuevo_codigo()
        log.error("%s · recalcular al editar", codigo, exc_info=ex)
        raise HTTPException(500, {"codigo": "incidente", "incidente": codigo, "mensaje":
                                  f"No se pudo recalcular con estos datos. Código de incidente {codigo}."}) from ex
    salida = E.salida(crudo, nueva.get("origenes") or {})
    guardado = repo.resultado(p["id"]) or {}
    try:
        periodo = repo.guardar_resultado(p["cliente_id"], salida, guardado.get("peticion") or {},
                                         entrada=E.comprimir(nueva), motivo=motivo)
    except repo.ResultadoVacio as ex:
        raise HTTPException(422, {"codigo": "resultado_vacio", "mensaje": str(ex)}) from ex
    repo.guardar_movimientos(p["cliente_id"], p["id"], E.movimientos_del_resultado(crudo))
    bitacora.registrar("periodo_editado", p["cliente_id"], periodo=p["id"], motivo=motivo,
                       movimientos=len(paquete.movimientos), cuadra=periodo.get("cuadra"))
    vista = _vista(periodo, nueva)
    vista["resumen"] = editar.resumen_periodo(salida)
    vista["guardado"] = True
    return vista


@router.put("/periodos/{periodo_id}/datos")
def guardar_datos(periodo_id: str, cambios: dict = Body(...)):
    p = _periodo(periodo_id)
    try:
        nueva = editar.aplicar(_entrada(p), cambios.get("tablas") or {})
    except editar.ErrorEdicion as ex:
        raise HTTPException(400, {"codigo": "datos_invalidos", "mensaje": str(ex)}) from ex
    return _guardar(p, nueva, "edicion")


@router.post("/periodos/{periodo_id}/recalcular")
def recalcular(periodo_id: str):
    p = _periodo(periodo_id)
    return _guardar(p, _entrada(p), "recalculo")


@router.post("/periodos/{periodo_id}/archivos/quitar")
def quitar_archivo(periodo_id: str, cuerpo: dict = Body(...)):
    p = _periodo(periodo_id)
    try:
        nueva = editar.quitar_archivo(_entrada(p), str(cuerpo.get("archivo") or ""))
    except editar.ErrorEdicion as ex:
        raise HTTPException(400, {"codigo": "datos_invalidos", "mensaje": str(ex)}) from ex
    return _guardar(p, nueva, "quitar_archivo")


@router.post("/periodos/{periodo_id}/deshacer")
def deshacer(periodo_id: str):
    p = _periodo(periodo_id)
    if p["estado"] == "cerrado":
        raise HTTPException(409, {"codigo": "periodo_cerrado", "mensaje": "Este periodo está cerrado. Reábralo primero."})
    versiones = repo.versiones(periodo_id)
    if not versiones:
        raise HTTPException(404, {"codigo": "sin_versiones", "mensaje": "No hay una versión anterior para volver."})
    periodo = repo.restaurar_version(versiones[0]["id"])
    bitacora.registrar("periodo_deshecho", p["cliente_id"], periodo=periodo_id, version=versiones[0]["id"])
    return _vista(periodo, _entrada(periodo))


@router.get("/periodos/{periodo_id}/datos/excel")
def datos_para_editar(periodo_id: str):
    from ..exportar import plantilla

    p = _periodo(periodo_id)
    entrada = _entrada(p)
    contenido = plantilla.con_datos(entrada.get("paquete") or {}, entrada.get("empresa") or {})
    nombre = f"datos para editar {p['desde'][:7]}.xlsx"
    return Response(contenido, media_type=XLSX, headers={"Content-Disposition": f'attachment; filename="{nombre}"'})
