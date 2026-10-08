"""Inicio de sesión del contador (adición A2).

La aplicación tiene un solo usuario: el contador. Su nombre y el hash bcrypt de
su contraseña viven en el archivo de configuración (`backend/.env`, o el que
indique `CC_ENV`) como `CC_USUARIO` y `CC_CLAVE_HASH`. Se crean o se cambian con

    python backend/crear_usuario.py

La sesión es una cookie firmada con HMAC-SHA256 usando `CLAVE_SESION`:
HttpOnly (el JavaScript no la ve), SameSite=Lax y Secure cuando la conexión es
HTTPS. No se guarda nada en el servidor: la firma basta para saber que la
emitió esta aplicación y que no venció.

Contra los intentos repetidos: 5 fallos en 15 minutos, desde el mismo equipo o
para el mismo usuario, bloquean el ingreso hasta que pase la ventana.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import os
import secrets
import threading
import time

import bcrypt

log = logging.getLogger("carloscruz.sesion")

COOKIE = "cc_sesion"
DURACION = 12 * 3600          # una jornada de trabajo
MAX_FALLOS = 5
VENTANA = 15 * 60
# Rutas de la API que no piden sesión: el estado del servidor y el propio ingreso.
PUBLICAS = {"/api/salud", "/api/sesion"}
CLAVE_DE_EJEMPLO = "cambie-esta-clave-por-una-larga-y-aleatoria"

_fallos: dict[str, list[float]] = {}
_candado = threading.Lock()
_clave_temporal = secrets.token_bytes(32)
_avisado = False


def usuario() -> str:
    return (os.getenv("CC_USUARIO") or "").strip()


def configurado() -> bool:
    return bool(usuario() and (os.getenv("CC_CLAVE_HASH") or "").strip())


def _clave() -> bytes:
    """Clave de firma. Sin una clave propia, una al azar (las sesiones mueren al reiniciar)."""
    global _avisado
    valor = (os.getenv("CLAVE_SESION") or "").strip()
    if len(valor) >= 32 and valor != CLAVE_DE_EJEMPLO:
        return valor.encode("utf-8")
    if not _avisado:
        log.warning("CLAVE_SESION falta o es la de ejemplo: se usa una clave temporal. "
                    "Ejecute python backend/crear_usuario.py para fijar una.")
        _avisado = True
    return _clave_temporal


def hash_de(clave: str, rondas: int = 12) -> str:
    return bcrypt.hashpw(clave.encode("utf-8"), bcrypt.gensalt(rounds=rondas)).decode("ascii")


def verificar(nombre: str, clave: str) -> bool:
    guardado = (os.getenv("CC_CLAVE_HASH") or "").strip().encode("ascii", "ignore")
    if not configurado() or not guardado:
        return False
    mismo_usuario = hmac.compare_digest(nombre.strip().lower().encode(), usuario().lower().encode())
    try:
        clave_ok = bcrypt.checkpw(clave.encode("utf-8"), guardado)
    except ValueError:  # hash mal copiado en el archivo de configuración
        log.error("CC_CLAVE_HASH no es un hash bcrypt válido.")
        return False
    return mismo_usuario and clave_ok


def _b64(datos: bytes) -> str:
    return base64.urlsafe_b64encode(datos).decode("ascii").rstrip("=")


def _desde_b64(texto: str) -> bytes:
    return base64.urlsafe_b64decode(texto + "=" * (-len(texto) % 4))


def emitir(nombre: str) -> str:
    carga = _b64(json.dumps({"u": nombre, "exp": int(time.time()) + DURACION}).encode("utf-8"))
    firma = _b64(hmac.new(_clave(), carga.encode("ascii"), hashlib.sha256).digest())
    return f"{carga}.{firma}"


def leer(cookie: str | None) -> str | None:
    """Usuario de una cookie válida y vigente; None si no lo es."""
    if not cookie or "." not in cookie:
        return None
    carga, firma = cookie.rsplit(".", 1)
    esperada = _b64(hmac.new(_clave(), carga.encode("ascii"), hashlib.sha256).digest())
    if not hmac.compare_digest(firma, esperada):
        return None
    try:
        datos = json.loads(_desde_b64(carga))
    except (ValueError, UnicodeDecodeError):
        return None
    if int(datos.get("exp", 0)) < time.time() or str(datos.get("u", "")).lower() != usuario().lower():
        return None
    return str(datos["u"])


# ── intentos fallidos ───────────────────────────────────────────────────────
def _recientes(clave: str, ahora: float) -> list[float]:
    vigentes = [t for t in _fallos.get(clave, []) if ahora - t < VENTANA]
    _fallos[clave] = vigentes
    return vigentes


def espera(ip: str, nombre: str) -> int:
    """Segundos que faltan para poder intentar de nuevo (0 si puede)."""
    ahora = time.time()
    with _candado:
        peor = 0.0
        for clave in (f"ip:{ip}", f"u:{nombre.strip().lower()}"):
            v = _recientes(clave, ahora)
            if len(v) >= MAX_FALLOS:
                peor = max(peor, VENTANA - (ahora - v[-MAX_FALLOS]))
        return int(peor) + (1 if peor else 0)


def fallo(ip: str, nombre: str) -> None:
    ahora = time.time()
    with _candado:
        for clave in (f"ip:{ip}", f"u:{nombre.strip().lower()}"):
            _recientes(clave, ahora).append(ahora)


def acierto(ip: str, nombre: str) -> None:
    with _candado:
        _fallos.pop(f"ip:{ip}", None)
        _fallos.pop(f"u:{nombre.strip().lower()}", None)


def olvidar_fallos() -> None:
    """Para las pruebas."""
    with _candado:
        _fallos.clear()
