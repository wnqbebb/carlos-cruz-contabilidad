"""Estado del sistema, catálogo PUC y parámetros legales."""
from __future__ import annotations

from fastapi import APIRouter, Body, HTTPException

from .. import db
from ..config import LEMA, MARCA, VERSION, estado_almacenamiento
from ..contabilidad.puc import puc
from ..nomina import parametros
from ..repositorio import sesiones

router = APIRouter(prefix="/api", tags=["sistema"])


@router.get("/salud")
def salud():
    """Lo que la interfaz necesita para saber si puede trabajar."""
    base = db.diagnostico()
    return {
        "ok": base["conectado"],
        "marca": MARCA,
        "lema": LEMA,
        "version": VERSION,
        "almacenamiento": {**estado_almacenamiento(), **base},
        "sesiones_abiertas": sesiones.abiertas(),
    }


@router.get("/puc")
def listar_puc():
    """Catálogo de cuentas del Decreto 2650/1993."""
    return puc().listado()


@router.get("/parametros")
def ver_parametros():
    return parametros.todos()


@router.put("/parametros/{anio}")
def guardar_parametros(anio: int, valores: dict = Body(...)):
    try:
        salida = parametros.guardar(anio, valores)
    except ValueError as ex:
        raise HTTPException(400, str(ex)) from ex
    bitacora.registrar("parametros_guardados", None, anio=anio,
                       campos=sorted(k for k in valores if not k.startswith("_")))
    return salida
