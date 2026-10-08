"""Directorio de clientes: alta, edición, búsqueda e importación masiva."""
from __future__ import annotations

from fastapi import APIRouter, Body, File, HTTPException, Query, UploadFile
from fastapi.responses import Response

from ..importadores import clientes_excel
from ..repositorio import bitacora
from ..repositorio import clientes as repo

router = APIRouter(prefix="/api/clientes", tags=["clientes"])

MAX_ARCHIVO = 40 * 1024 * 1024  # 40 MB: alcanza para ~200.000 filas de directorio


def _error(ex: repo.ErrorCliente) -> HTTPException:
    return HTTPException(400, str(ex))


@router.get("")
def listar(
    q: str = Query("", description="Texto libre: NIT, razón social, municipio, representante…"),
    estado: str = Query("activo", description="activo | inactivo | archivado. Vacío = todos"),
    etiqueta: str = Query(""),
    orden: str = Query("razon_social"),
    descendente: bool = Query(False),
    pagina: int = Query(1, ge=1),
    por_pagina: int = Query(50, ge=1, le=500),
):
    return repo.listar(q=q, estado=estado, etiqueta=etiqueta, orden=orden,
                       descendente=descendente, pagina=pagina, por_pagina=por_pagina)


@router.get("/demostracion")
def demostracion():
    """Clientes de demostración cargados (los que borra «Eliminar clientes de demostración»)."""
    return {"clientes": repo.de_demostracion()}


@router.post("/demostracion/eliminar")
def eliminar_demostracion():
    salida = repo.eliminar_demostracion()
    if salida["eliminados"]:
        bitacora.registrar("clientes_demo_eliminados", None, eliminados=salida["eliminados"],
                           clientes=salida["clientes"])
    return salida


@router.get("/plantilla")
def plantilla():
    """CSV de ejemplo con los encabezados que el importador reconoce."""
    return Response(
        clientes_excel.plantilla_csv(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="plantilla_clientes_CarlosCruz.csv"'},
    )


@router.post("/importar")
async def importar(
    archivo: UploadFile = File(...),
    actualizar_existentes: bool = Query(True),
    solo_revisar: bool = Query(False, description="True = simulacro, no escribe nada"),
):
    contenido = await archivo.read()
    if len(contenido) > MAX_ARCHIVO:
        raise HTTPException(413, f"El archivo pesa más de {MAX_ARCHIVO // (1024 * 1024)} MB. Divídalo en partes.")
    if not contenido:
        raise HTTPException(400, "El archivo llegó vacío.")
    try:
        informe = clientes_excel.importar(
            contenido, archivo.filename or "clientes.xlsx",
            actualizar_existentes=actualizar_existentes, solo_revisar=solo_revisar,
        )
    except ValueError as ex:
        raise HTTPException(400, str(ex)) from ex
    if not solo_revisar:
        bitacora.registrar("clientes_importados", None, archivo=archivo.filename,
                           insertados=informe.get("insertados"), actualizados=informe.get("actualizados"),
                           rechazados=informe.get("rechazados"))
    return informe


@router.post("")
def crear(datos: dict = Body(...)):
    try:
        cliente = repo.crear(datos)
    except repo.ErrorCliente as ex:
        raise _error(ex) from ex
    if datos.get("socios"):
        repo.guardar_socios(cliente["id"], datos["socios"])
        cliente = repo.obtener(cliente["id"])
    bitacora.registrar("cliente_creado", cliente["id"],
                       nit=cliente["nit"], razon_social=cliente["razon_social"],
                       origen=datos.get("_origen") or "formulario")
    return cliente


@router.get("/{cliente_id}")
def obtener(cliente_id: str):
    from .trabajo import tiene_archivos_de_muestra

    try:
        cliente = repo.obtener(cliente_id)
    except repo.ErrorCliente as ex:
        raise HTTPException(404, str(ex)) from ex
    cliente["archivos_de_muestra"] = tiene_archivos_de_muestra(cliente.get("nit", ""))
    return cliente


@router.patch("/{cliente_id}")
def actualizar(cliente_id: str, datos: dict = Body(...)):
    try:
        if "socios" in datos:
            repo.guardar_socios(cliente_id, datos.pop("socios") or [])
        repo.actualizar(cliente_id, datos)
        cliente = repo.obtener(cliente_id)
        bitacora.registrar("cliente_editado", cliente_id,
                           campos=sorted(k for k in datos if not k.startswith("_")))
        return cliente
    except repo.ErrorCliente as ex:
        raise _error(ex) from ex


@router.delete("/{cliente_id}")
def eliminar(cliente_id: str, definitivo: bool = Query(False)):
    """Por defecto archiva. `definitivo=true` borra el cliente y toda su contabilidad."""
    try:
        if definitivo:
            ficha = repo.obtener(cliente_id)
            salida = repo.eliminar(cliente_id)
            bitacora.registrar("cliente_eliminado", None, nit=ficha["nit"],
                               razon_social=ficha["razon_social"],
                               periodos=salida.get("periodos_borrados"))
            return salida
        cliente = repo.archivar(cliente_id)
        bitacora.registrar("cliente_archivado", cliente_id, razon_social=cliente["razon_social"])
        return {"ok": True, "archivado": True, "cliente": cliente}
    except repo.ErrorCliente as ex:
        raise _error(ex) from ex


@router.post("/{cliente_id}/restaurar")
def restaurar(cliente_id: str):
    try:
        cliente = repo.archivar(cliente_id, archivado=False)
    except repo.ErrorCliente as ex:
        raise _error(ex) from ex
    bitacora.registrar("cliente_restaurado", cliente_id, razon_social=cliente["razon_social"])
    return cliente


