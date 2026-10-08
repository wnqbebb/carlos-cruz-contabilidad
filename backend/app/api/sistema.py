"""Estado del sistema, datos del contador y catálogo PUC."""
from __future__ import annotations

from fastapi import APIRouter

from .. import contador as datos_contador
from .. import db
from ..config import VERSION, estado_almacenamiento
from ..contabilidad.puc import puc

router = APIRouter(prefix="/api", tags=["sistema"])


@router.get("/salud")
def salud():
    """Pública: solo si el servidor responde y su versión. El diagnóstico va en /api/sistema, con sesión."""
    return {"ok": True, "version": VERSION}


@router.get("/sistema")
def sistema():
    """Lo que muestra el panel «Sistema»: conectado o no, en la nube o en este equipo, y la versión.

    Nada técnico: ni el proyecto, ni el motor, ni rutas, ni variables de entorno.
    """
    base = db.diagnostico()
    return {"conectado": bool(base["conectado"]), "en_la_nube": bool(estado_almacenamiento().get("es_postgres")),
            "version": VERSION}


@router.get("/contador")
def ver_contador():
    """Nombre, tarjeta profesional y municipio del contador (logotipo, preloader, saludo)."""
    return datos_contador.leer()


@router.get("/puc")
def listar_puc():
    """Catálogo de cuentas del Decreto 2650/1993."""
    return puc().listado()
