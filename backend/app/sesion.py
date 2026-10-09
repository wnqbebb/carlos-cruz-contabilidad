"""Sesiones del contador (v2.3 · Fase 6, controles C5–C8).

La cookie `cc_sesion` lleva un token aleatorio de 256 bits. En la base queda solo su hash
(SHA-256) con el usuario, el token CSRF de la sesión, la última actividad y el vencimiento.
Así, al cerrar sesión la cookie deja de servir, y «cerrar todas las sesiones» corta los
demás navegadores al instante.

- Inactividad: 30 minutos. Absoluta: 12 horas. Al ingresar se crea una sesión nueva (rotación).
- Reautenticación: las acciones delicadas exigen haber confirmado la contraseña hace menos
  de 5 minutos (`exigir_reautenticacion`).
- Intentos fallidos: 5 en 15 minutos, por equipo y por usuario, bloquean el ingreso.

Para no consultar la base en cada petición, la validación se recuerda 15 segundos en
memoria; cerrar una sesión la olvida en el acto.
"""
from __future__ import annotations

import hashlib
import secrets
import threading
import time
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, Request
from sqlalchemy import insert, select, update

from .db import conexion, lectura
from .esquema import sesiones_acceso as TS

COOKIE = "cc_sesion"
ENCABEZADO_CSRF = "x-csrf"
DURACION = 12 * 3600          # absoluta: una jornada de trabajo
INACTIVIDAD = 30 * 60
REAUTENTICACION = 5 * 60
MAX_FALLOS = 5
VENTANA = 15 * 60
# Rutas de la API que no piden sesión: el estado del servidor, el ingreso, el primer uso y la recuperación.
PUBLICAS = {"/api/salud", "/api/sesion", "/api/acceso/primer-uso", "/api/acceso/recuperar", "/api/acceso/politica"}

_fallos: dict[str, list[float]] = {}
_candado = threading.Lock()
_memoria: dict[str, tuple[float, dict]] = {}
RECUERDO = 15.0


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode("ascii", "ignore")).hexdigest()


def _ahora() -> datetime:
    return datetime.now(timezone.utc)


def _utc(d: datetime | None) -> datetime | None:
    if d is None:
        return None
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def abrir(usuario_id: int, ip: str = "", agente: str = "") -> tuple[str, str]:
    """Nueva sesión: (token para la cookie, token CSRF)."""
    token = secrets.token_urlsafe(32)
    csrf = secrets.token_urlsafe(32)
    ahora = _ahora()
    with conexion() as cn:
        cn.execute(insert(TS).values(id=_hash(token), usuario_id=usuario_id, csrf=csrf, creada=ahora, ultima=ahora,
                                     expira=ahora + timedelta(seconds=DURACION), reautenticada=ahora,
                                     ip=ip[:60], agente=agente[:200], revocada=False))
    return token, csrf


def leer(token: str | None) -> dict | None:
    """La sesión vigente de una cookie, o None. Renueva la última actividad."""
    if not token or len(token) < 20:
        return None
    clave = _hash(token)
    ahora_s = time.time()
    with _candado:
        guardada = _memoria.get(clave)
    if guardada and ahora_s - guardada[0] < RECUERDO:
        info = guardada[1]
        if _utc(info["expira"]) > _ahora() and _ahora() - _utc(info["ultima"]) < timedelta(seconds=INACTIVIDAD):
            return info
    with lectura() as cn:
        f = cn.execute(select(TS).where(TS.c.id == clave)).first()
    if not f or f.revocada:
        return None
    ahora = _ahora()
    if _utc(f.expira) <= ahora or ahora - _utc(f.ultima) >= timedelta(seconds=INACTIVIDAD):
        return None
    info = dict(f._mapping)
    if ahora - _utc(f.ultima) > timedelta(seconds=60):
        with conexion() as cn:
            cn.execute(update(TS).where(TS.c.id == clave).values(ultima=ahora))
        info["ultima"] = ahora
    with _candado:
        _memoria[clave] = (ahora_s, info)
    return info


def cerrar(token: str | None) -> None:
    if not token:
        return
    clave = _hash(token)
    with conexion() as cn:
        cn.execute(update(TS).where(TS.c.id == clave).values(revocada=True))
    with _candado:
        _memoria.pop(clave, None)


def cerrar_todas(usuario_id: int, excepto: str | None = None) -> int:
    with conexion() as cn:
        cond = (TS.c.usuario_id == usuario_id) & (TS.c.revocada.is_(False))
        if excepto:
            cond = cond & (TS.c.id != excepto)
        n = cn.execute(update(TS).where(cond).values(revocada=True)).rowcount
    with _candado:
        _memoria.clear()
    return int(n or 0)


def abiertas(usuario_id: int) -> list[dict]:
    ahora = _ahora()
    with lectura() as cn:
        filas = cn.execute(select(TS.c.id, TS.c.creada, TS.c.ultima, TS.c.ip, TS.c.agente, TS.c.expira)
                           .where(TS.c.usuario_id == usuario_id, TS.c.revocada.is_(False))).all()
    return [dict(f._mapping) for f in filas
            if _utc(f.expira) > ahora and ahora - _utc(f.ultima) < timedelta(seconds=INACTIVIDAD)]


def marcar_reautenticada(sesion_id: str) -> None:
    with conexion() as cn:
        cn.execute(update(TS).where(TS.c.id == sesion_id).values(reautenticada=_ahora()))
    with _candado:
        for k in [k for k, (_, v) in _memoria.items() if v.get("id") == sesion_id]:
            _memoria.pop(k, None)


def exigir_reautenticacion(request: Request) -> None:
    """Para acciones delicadas: 403 `reautenticar` si la contraseña no se confirmó hace poco."""
    info = getattr(request.state, "sesion", None)
    if not info:
        raise HTTPException(401, {"codigo": "sin_sesion", "mensaje": "La sesión no está iniciada o venció."})
    ultima = _utc(info.get("reautenticada"))
    if not ultima or _ahora() - ultima > timedelta(seconds=REAUTENTICACION):
        raise HTTPException(403, {"codigo": "reautenticar",
                                  "mensaje": "Por seguridad, confirme su contraseña para continuar."})


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
        _memoria.clear()
