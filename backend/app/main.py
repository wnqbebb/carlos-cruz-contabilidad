"""CARLOS CRUZ · servidor de la API y del frontend compilado."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from sqlalchemy.exc import DBAPIError

from . import db
from .api import ROUTERS
from .config import CORS_ORIGENES, FRONTEND_DIST, LEMA, MARCA, VERSION
from .repositorio import parametros as repo_parametros
from .repositorio import subidas as repo_subidas

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s · %(message)s")
log = logging.getLogger("carloscruz")


@asynccontextmanager
async def ciclo_de_vida(_app: FastAPI):
    """Al arrancar: comprobar la base y sembrar los parámetros legales si hace falta."""
    estado = db.diagnostico()
    if estado["conectado"]:
        log.info("Base de datos lista (%s).", estado["motor"])
        try:
            nuevos = repo_parametros.sembrar_si_vacio()
            if nuevos:
                log.info("Parámetros legales sembrados: %s año(s).", nuevos)
        except Exception as ex:
            log.warning("No se pudieron sembrar los parámetros legales: %s", ex)
    else:
        log.error("SIN BASE DE DATOS · %s", estado["error"])
    borradas = repo_subidas.limpiar()
    if borradas:
        log.info("Subidas vencidas borradas de la carpeta temporal: %s.", borradas)
    yield


app = FastAPI(
    title=f"{MARCA} — contabilidad",
    description=LEMA,
    version=VERSION,
    lifespan=ciclo_de_vida,
)


@app.exception_handler(db.BaseNoDisponible)
async def _sin_base(_req: Request, ex: db.BaseNoDisponible):
    """La base no respondió tras los reintentos (H20): 503 con un mensaje que el contador entiende."""
    return JSONResponse(status_code=503, content={"detail": {"codigo": "sin_base", "mensaje": str(ex)}})


@app.exception_handler(DBAPIError)
async def _error_de_base(_req: Request, ex: DBAPIError):
    if db.es_falla_de_conexion(ex):
        # La conexión se cayó a mitad de la consulta: la siguiente abre una nueva.
        return JSONResponse(status_code=503, content={"detail": {"codigo": "sin_base", "mensaje": str(db.BaseNoDisponible(ex))}})
    log.exception("Error de la base de datos")
    return JSONResponse(status_code=500, content={"detail": {"codigo": "error_base",
                                                             "mensaje": "La base de datos rechazó la operación. Nada se guardó a medias."}})

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGENES,
    allow_origin_regex=r"https://.*\.vercel\.app",  # despliegues de vista previa de Vercel
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for router in ROUTERS:
    app.include_router(router)


# ─────────────────────────────────────────────────────── frontend compilado
# En el despliegue partido (frontend en Vercel) esto no se usa, pero permite
# seguir corriendo todo en un solo puerto en local con iniciar.bat.
#
# index.html NUNCA se cachea: si el navegador guarda uno viejo, sigue pidiendo
# el JS viejo y los cambios de diseño «no aparecen» (causa hallada en la Fase 0).
SIN_CACHE = {"Cache-Control": "no-cache, must-revalidate"}
INMUTABLE = {"Cache-Control": "public, max-age=31536000, immutable"}


@app.get("/{ruta:path}", include_in_schema=False)
def spa(ruta: str):
    indice = FRONTEND_DIST / "index.html"
    archivo = (FRONTEND_DIST / ruta).resolve() if ruta else None
    if archivo and archivo.is_file() and FRONTEND_DIST.resolve() in archivo.parents:
        if archivo.name == "index.html":
            return FileResponse(archivo, headers=SIN_CACHE)
        # Los archivos de /assets llevan hash en el nombre: pueden cachearse para siempre.
        if "assets" in archivo.relative_to(FRONTEND_DIST.resolve()).parts:
            return FileResponse(archivo, headers=INMUTABLE)
        return FileResponse(archivo)
    if indice.exists():
        return FileResponse(indice, headers=SIN_CACHE)
    return HTMLResponse(
        f"<h1>{MARCA}</h1><p>{LEMA}</p>"
        "<p>El frontend no está compilado. Ejecute <code>iniciar.bat</code> "
        "o <code>npm run build</code> dentro de <code>frontend/</code>.</p>",
        status_code=200,
    )
