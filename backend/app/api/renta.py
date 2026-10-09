"""Declaración de renta de personas naturales (formulario 210) — v2.3 · Fase 5.

Todas las rutas piden sesión (middleware de `main.py`).
"""
from __future__ import annotations

import io
import zipfile
from datetime import date

from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel

import logging

from .. import sesion
from ..exactitud import a_json
from ..repositorio import bitacora
from ..seguridad import aislado, incidentes
from ..seguridad import archivos as seg_archivos
from ..exportar import renta as exportar
from ..renta import parametros, servicio
from ..repositorio import renta as repo
from ..repositorio.clientes import ErrorCliente

router = APIRouter(prefix="/api/renta", tags=["renta"])
log = logging.getLogger("carloscruz.renta")

TAMANO_MAXIMO = 25 * 1024 * 1024
MAXIMO_ARCHIVOS = 20
PERMITIDAS = (".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff", ".pdf", ".xlsx", ".xlsm", ".xls", ".csv")


def _errores(fn):
    try:
        return fn()
    except servicio.RentaNoAplica as ex:
        raise HTTPException(409, {"codigo": "no_aplica", "mensaje": str(ex)}) from ex
    except parametros.RentaSinParametros as ex:
        raise HTTPException(409, {"codigo": "sin_parametros", "mensaje": str(ex)}) from ex
    except ErrorCliente as ex:
        raise HTTPException(404, {"codigo": "sin_cliente", "mensaje": str(ex)}) from ex
    except ValueError as ex:  # mensajes propios de la renta, escritos para el contador
        raise HTTPException(422, {"codigo": "dato_invalido", "mensaje": str(ex)}) from ex
    except (KeyError, TypeError, ArithmeticError) as ex:
        codigo = incidentes.nuevo_codigo()
        log.error("%s · renta", codigo, exc_info=ex)
        raise HTTPException(422, {"codigo": "dato_invalido", "incidente": codigo,
                                  "mensaje": f"Un dato no es válido. Código de incidente {codigo}."}) from ex


def _anio(anio: int) -> int:
    if anio not in parametros.anios():
        raise HTTPException(409, {"codigo": "sin_parametros", "mensaje":
                                  f"El año gravable {anio} todavía no está disponible en la aplicación."})
    return anio


@router.get("/anios")
def anios():
    return {"anios": parametros.anios(), "actual": servicio.ANIO_ACTUAL}


@router.get("/cartera")
def cartera(anio: int = servicio.ANIO_ACTUAL):
    return JSONResponse(a_json({"anio": _anio(anio), "declaraciones": servicio.cartera(anio)}))


@router.post("/subir-universal")
def subir_universal(anio: int = servicio.ANIO_ACTUAL, archivos: list[UploadFile] = File(...)):
    _anio(anio)
    if len(archivos) > MAXIMO_ARCHIVOS:
        raise HTTPException(413, {"codigo": "demasiados", "mensaje": f"Suba hasta {MAXIMO_ARCHIVOS} archivos a la vez."})
    leidos = []
    for a in archivos:
        contenido = a.file.read(TAMANO_MAXIMO + 1)
        if len(contenido) > TAMANO_MAXIMO:
            raise HTTPException(413, {"codigo": "muy_grande", "mensaje": f"«{a.filename}» pasa de 25 MB."})
        leidos.append((a.filename or "archivo", contenido))
    try:
        avisos = seg_archivos.validar_todos(leidos, PERMITIDAS)
    except seg_archivos.ArchivoRechazado as ex:
        raise HTTPException(400, {"codigo": ex.codigo, "mensaje": str(ex)}) from ex
    try:
        return JSONResponse(a_json(_errores(lambda: servicio.subir_universal(anio, leidos, avisos))))
    except aislado.ArchivoNoProcesable as ex:
        raise HTTPException(422, {"codigo": ex.codigo, "mensaje": str(ex)}) from ex


@router.get("/{cliente_id}/{anio}")
def ver(cliente_id: str, anio: int):
    _anio(anio)
    return JSONResponse(a_json(_errores(lambda: servicio.vista(cliente_id, anio))))


@router.post("/{cliente_id}/{anio}/documentos")
def documentos(cliente_id: str, anio: int, archivos: list[UploadFile] = File(...)):
    _anio(anio)
    if len(archivos) > MAXIMO_ARCHIVOS:
        raise HTTPException(413, {"codigo": "demasiados", "mensaje": f"Suba hasta {MAXIMO_ARCHIVOS} archivos a la vez."})
    leidos = []
    for a in archivos:
        contenido = a.file.read(TAMANO_MAXIMO + 1)
        if len(contenido) > TAMANO_MAXIMO:
            raise HTTPException(413, {"codigo": "muy_grande", "mensaje": f"«{a.filename}» pasa de 25 MB."})
        leidos.append((a.filename or "archivo", contenido))
    try:
        avisos = seg_archivos.validar_todos(leidos, PERMITIDAS)
    except seg_archivos.ArchivoRechazado as ex:
        raise HTTPException(400, {"codigo": ex.codigo, "mensaje": str(ex)}) from ex
    try:
        return JSONResponse(a_json(_errores(lambda: servicio.subir(cliente_id, anio, leidos, avisos))))
    except aislado.ArchivoNoProcesable as ex:
        raise HTTPException(422, {"codigo": ex.codigo, "mensaje": str(ex)}) from ex


class Cambio(BaseModel):
    tipo: str
    id: str | None = None
    valor: object | None = None
    extra: object | None = None
    linea: str | None = None
    lineas: list[str] | None = None
    categoria: str | None = None
    descripcion: str | None = None
    uno_por_ciento: object | None = None


@router.post("/{cliente_id}/{anio}/cambio")
def cambio(cliente_id: str, anio: int, c: Cambio):
    _anio(anio)
    datos = {k: v for k, v in c.model_dump().items() if v is not None}
    return JSONResponse(a_json(_errores(lambda: servicio.actualizar(cliente_id, anio, datos))))


class Estado(BaseModel):
    estado: str
    numero: str = ""
    fecha: str = ""


@router.post("/{cliente_id}/{anio}/estado")
def estado(cliente_id: str, anio: int, e: Estado):
    _anio(anio)
    if e.fecha:
        try:
            date.fromisoformat(e.fecha)
        except ValueError as ex:
            raise HTTPException(422, {"codigo": "fecha", "mensaje": "La fecha no es válida."}) from ex
    return JSONResponse(a_json(_errores(lambda: servicio.marcar(cliente_id, anio, e.estado, e.numero, e.fecha))))


@router.get("/{cliente_id}/{anio}/recorte/{recorte_id}")
def recorte(cliente_id: str, anio: int, recorte_id: str):
    decl = _errores(lambda: servicio.declaracion(cliente_id, anio))
    png = repo.recorte(decl["id"], recorte_id)
    if not png:
        raise HTTPException(404, {"codigo": "sin_recorte", "mensaje": "Ese recorte no existe."})
    return Response(png, media_type="image/png", headers={"Cache-Control": "private, max-age=600"})


class DigitarEsencial(BaseModel):
    topes: dict = {}
    esenciales: list[dict] = []
    anterior_saldo_favor: object | None = None
    anterior_patrimonio: object | None = None
    respuestas: dict = {}


@router.post("/{cliente_id}/{anio}/digitar-esencial")
def digitar_esencial(cliente_id: str, anio: int, d: DigitarEsencial):
    _anio(anio)
    datos = {k: v for k, v in d.model_dump().items() if v is not None}
    return JSONResponse(a_json(_errores(lambda: servicio.digitar_esencial(cliente_id, anio, datos))))


@router.get("/{cliente_id}/{anio}/descargar/{que}")
def descargar(request: Request, cliente_id: str, anio: int, que: str):
    _anio(anio)
    if que == "todo":
        sesion.exigir_reautenticacion(request)
    bitacora.registrar("descarga", cliente_id, que=f"renta-{anio}-{que}",
                       ip=request.client.host if request.client else "?")
    v = _errores(lambda: servicio.vista(cliente_id, anio))
    if not v.get("resultado"):
        raise HTTPException(409, {"codigo": "sin_datos", "mensaje": "Todavía no hay borrador: suba los documentos."})
    v = a_json(v)
    base = f"renta-{anio}-{(v['contribuyente']['nit'] or 'cliente')}"
    incompleto = bool(v.get("resultado", {}).get("incompleto"))

    if incompleto:
        # La regla de oro: nada se descarga con cifras mientras falten datos. Solo el borrador incompleto.
        return Response(exportar.borrador_pdf(v), media_type="application/pdf",
                        headers={"Content-Disposition": f'attachment; filename="{base}-borrador-incompleto.pdf"'})

    if que == "pdf":
        return Response(exportar.borrador_pdf(v), media_type="application/pdf",
                        headers={"Content-Disposition": f'attachment; filename="{base}-borrador-210.pdf"'})
    if que == "excel":
        return Response(exportar.papel_trabajo(v),
                        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        headers={"Content-Disposition": f'attachment; filename="{base}-papel-de-trabajo.xlsx"'})
    if que == "resumen":
        return Response(exportar.resumen_cliente(v), media_type="application/pdf",
                        headers={"Content-Disposition": f'attachment; filename="{base}-resumen.pdf"'})
    if que == "todo":
        # Un solo botón: el borrador, el papel de trabajo y el resumen para el cliente, juntos.
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr(f"{base}-borrador-210.pdf", exportar.borrador_pdf(v))
            z.writestr(f"{base}-papel-de-trabajo.xlsx", exportar.papel_trabajo(v))
            z.writestr(f"{base}-resumen-para-el-cliente.pdf", exportar.resumen_cliente(v))
        return Response(buf.getvalue(), media_type="application/zip",
                        headers={"Content-Disposition": f'attachment; filename="{base}.zip"'})
    raise HTTPException(404, {"codigo": "no_existe", "mensaje": "Esa descarga no existe."})
