"""CARLOS CRUZ · servidor de la API y del frontend compilado."""
from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from sqlalchemy.exc import DBAPIError

from . import db
from .api import ROUTERS
from .config import CORS_ORIGENES, DATOS_APP, FRONTEND_DIST, LEMA, MARCA, VERSION, archivo_env
from .repositorio import subidas as repo_subidas
from .seguridad import cuentas, incidentes, respaldo, secretos
from .seguridad import http as seguridad_http

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s · %(message)s")
incidentes.instalar_filtro(None if os.getenv("CC_SIN_REGISTRO_LOCAL") == "1" else DATOS_APP / "registro")
log = logging.getLogger("carloscruz")


@asynccontextmanager
async def ciclo_de_vida(_app: FastAPI):
    """Al arrancar: comprobar la base y limpiar las subidas vencidas."""
    estado = db.diagnostico()
    if estado["conectado"]:
        log.info("Base de datos lista (%s).", estado["motor"])
    else:
        log.error("SIN BASE DE DATOS · %s", estado["error"])
    borradas = repo_subidas.limpiar()
    if borradas:
        log.info("Subidas vencidas borradas de la carpeta temporal: %s.", borradas)
    # Secretos fuera de los archivos de texto (C30) y el usuario de la v2.2 a la tabla de usuarios.
    env = archivo_env()
    if env:
        secretos.migrar_archivo(env)
    try:
        cuentas.asegurar_desde_entorno()
        if env and cuentas.hay_usuario():
            # El usuario ya está en la base (Argon2id): el hash de la v2.2 no se deja en el archivo.
            secretos.quitar_lineas(env, ("CC_CLAVE_HASH",))
    except Exception:
        log.exception("No se pudo revisar el usuario")
    respaldo.programar()
    yield


# La documentación de la API no se publica (C15): solo con CC_DOCS=1 en desarrollo.
_DOCS = os.getenv("CC_DOCS") == "1"
app = FastAPI(
    title=f"{MARCA} — contabilidad",
    description=LEMA,
    version=VERSION,
    lifespan=ciclo_de_vida,
    docs_url="/docs" if _DOCS else None,
    redoc_url="/redoc" if _DOCS else None,
    openapi_url="/openapi.json" if _DOCS else None,
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

# v2.3 · Fase 6: host, límite de solicitudes, sesión, CSRF y encabezados (ver seguridad/http.py).
app.middleware("http")(seguridad_http.proteger)
app.add_exception_handler(Exception, incidentes.manejar_inesperado)


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
    # Una ruta de la API que no existe responde 404, no la página de la aplicación.
    if ruta == "api" or ruta.startswith("api/") or ruta.strip("/") in ("docs", "redoc", "openapi.json"):
        return JSONResponse(status_code=404, content={"detail": {"codigo": "no_existe", "mensaje": "Eso no existe."}})
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
    # Sin interfaz compilada: un mensaje humano, sin comandos ni rutas (v2.3 · 6.1).
    log.error("Falta la interfaz compilada en %s", FRONTEND_DIST)
    return HTMLResponse(f"<h1>{MARCA}</h1><p>{LEMA}</p><p>La aplicación se está actualizando. "
                        "Ciérrela y vuelva a abrirla en un momento.</p>", status_code=503)
