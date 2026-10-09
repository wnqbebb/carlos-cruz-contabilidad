"""Errores con código de incidente y registros sin datos sensibles (controles C16 y C18).

- Un error inesperado responde «Algo falló… Código de incidente INC-7F3A» y el detalle técnico
  (la traza) queda solo en el registro local, con ese mismo código para encontrarlo.
- Todo lo que se escribe en los registros pasa por `FiltroSensible`: quita contraseñas,
  cookies, tokens y cadenas de conexión, y enmascara cédulas y NIT (`****8740`).
"""
from __future__ import annotations

import atexit
import logging
import os
import queue
import re
import secrets
from logging.handlers import QueueHandler, QueueListener, TimedRotatingFileHandler
from pathlib import Path

from fastapi import Request
from fastapi.responses import JSONResponse

log = logging.getLogger("carloscruz.incidentes")

PATRONES = [
    # cadenas de conexión con usuario:clave@
    (re.compile(r"(?i)\b(postgres(?:ql)?(?:\+\w+)?|mysql|redis|https?)://[^\s:/@]+:[^\s@]+@"), r"\1://***:***@"),
    # clave=…, password: …, token=…, secret…
    (re.compile(r"(?i)\b(clave|contrase(?:ñ|n)a|password|passwd|pwd|token|secret[a-z_]*|api[_-]?key|csrf|"
                r"cc_clave_hash|clave_sesion|clave_datos|authorization)\b(\s*[:=]\s*|\"\s*:\s*\")([^\s,;\"&]+)"),
     r"\1\2***"),
    # cookies
    (re.compile(r"(?i)(cookie|set-cookie)(\s*[:=]\s*)[^\n]+"), r"\1\2***"),
    (re.compile(r"(?i)\bcc_sesion=[^;\s]+"), "cc_sesion=***"),
    # hashes argon2/bcrypt
    (re.compile(r"\$(argon2id?|2[aby])\$[^\s\"']+"), "$***"),
    # cédulas y NIT: 6 a 11 dígitos (con puntos o guion opcional) → ****1234
    (re.compile(r"(?<![\d$.,])(\d{1,3}(?:\.\d{3}){1,3}|\d{6,11})(?:-\d)?(?![\d,]|\.\d)"),
     lambda m: "****" + re.sub(r"\D", "", m.group(1))[-4:]),
]


def limpiar(texto: str) -> str:
    for patron, reemplazo in PATRONES:
        texto = patron.sub(reemplazo, texto)
    return texto


class FiltroSensible(logging.Filter):
    def filter(self, registro: logging.LogRecord) -> bool:
        if registro.name == "uvicorn.access" and isinstance(registro.args, tuple):
            # Su formateador necesita los argumentos originales: se limpia cada uno (la ruta trae la consulta).
            registro.args = tuple(limpiar(a) if isinstance(a, str) else a for a in registro.args)
        else:
            try:
                completo = registro.getMessage()
            except Exception:
                completo = str(registro.msg)
            limpio = limpiar(completo)
            if limpio != completo:
                registro.msg, registro.args = limpio, ()
        if registro.exc_info and registro.exc_info[1] is not None:
            registro.exc_text = limpiar(logging.Formatter().formatException(registro.exc_info))
            registro.exc_info = None
        return True


def instalar_filtro(carpeta: Path | None = None) -> None:
    """Pone el filtro en todos los registros y, si se da una carpeta, un archivo local con 30 días."""
    filtro = FiltroSensible()
    raiz = logging.getLogger()
    if carpeta is not None:
        carpeta.mkdir(parents=True, exist_ok=True)
        ya = any(isinstance(h, TimedRotatingFileHandler) for h in raiz.handlers)
        if not ya:
            archivo = TimedRotatingFileHandler(carpeta / "carloscruz.log", when="D", backupCount=30, encoding="utf-8")
            archivo.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s · %(message)s"))
            raiz.addHandler(archivo)
    for nombre in ("", "uvicorn", "uvicorn.error", "uvicorn.access", "carloscruz"):
        lg = logging.getLogger(nombre)
        for h in lg.handlers:
            if not any(isinstance(f, FiltroSensible) for f in h.filters):
                h.addFilter(filtro)
        if not any(isinstance(f, FiltroSensible) for f in lg.filters):
            lg.addFilter(filtro)
    desacoplar()


class _Encolar(QueueHandler):
    """Pasa el registro tal cual al hilo escritor. No se formatea aquí: el formateador de accesos de
    uvicorn necesita los argumentos originales. Los datos sensibles ya los quitó el filtro del registrador."""

    def prepare(self, record: logging.LogRecord) -> logging.LogRecord:
        return record


_escritores: list[QueueListener] = []


def desacoplar(nombres: tuple[str, ...] = ("", "uvicorn", "uvicorn.error", "uvicorn.access")) -> None:
    """Escribir un registro nunca frena al servidor.

    En Windows, escribir en la consola se detiene mientras alguien tiene texto seleccionado en la ventana
    de `iniciar.bat` (modo de edición rápida), y escribir en un archivo puede esperar al antivirus. Si eso
    pasa dentro del bucle del servidor, la aplicación entera se congela (se midieron esperas de ~30 s).
    Aquí los manejadores de cada registrador pasan a un hilo propio y el bucle solo deja el registro en
    una cola. `CC_REGISTRO_DIRECTO=1` lo desactiva (pruebas).
    """
    if os.getenv("CC_REGISTRO_DIRECTO") == "1":
        return
    for nombre in nombres:
        lg = logging.getLogger(nombre)
        propios = [h for h in lg.handlers if not isinstance(h, QueueHandler)]
        if not propios:
            continue
        cola: queue.SimpleQueue = queue.SimpleQueue()
        for h in propios:
            lg.removeHandler(h)
        lg.addHandler(_Encolar(cola))
        escritor = QueueListener(cola, *propios, respect_handler_level=True)
        escritor.start()
        _escritores.append(escritor)
    if _escritores:
        atexit.register(detener_escritores)


def detener_escritores() -> None:
    """Vacía las colas antes de salir (lo que quedaba por escribir se escribe)."""
    while _escritores:
        _escritores.pop().stop()


def nuevo_codigo() -> str:
    return "INC-" + secrets.token_hex(2).upper()


def respuesta_incidente(codigo: str, estado: int = 500) -> JSONResponse:
    return JSONResponse(status_code=estado, content={"detail": {
        "codigo": "incidente", "incidente": codigo,
        "mensaje": f"Algo falló de nuestro lado y no se guardó nada a medias. Si vuelve a pasar, comparta este "
                   f"código con soporte: {codigo}."}})


async def manejar_inesperado(request: Request, ex: Exception) -> JSONResponse:
    codigo = nuevo_codigo()
    log.error("%s · %s %s", codigo, request.method, request.url.path, exc_info=ex)
    return respuesta_incidente(codigo)
