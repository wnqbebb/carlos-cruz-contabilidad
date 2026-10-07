"""Sesión de trabajo: lo que está abierto en pantalla entre «subir archivos» y «calcular».

POR QUÉ VIVE EN MEMORIA Y NO EN LA BASE
---------------------------------------
Una sesión contiene los objetos ya interpretados de los Excel (`Deteccion`,
`Paquete`, `Movimiento`...). Serializarlos a JSON y reconstruirlos añadiría una
capa de conversión por la que pasarían TODOS los importes: justo donde no
queremos riesgo. Como el backend es un servicio siempre encendido (Render/Fly),
la memoria es segura y exacta.

Lo que sí es valioso a largo plazo —el resultado ya calculado— se guarda en
Supabase (`repositorio/periodos.guardar_resultado`). Si el servidor se reinicia
con una sesión abierta, el contador vuelve a subir el archivo; nada calculado
se pierde.

La tabla `sesiones` de la base se usa solo para dejar rastro de qué se trabajó
y cuándo (trazabilidad), no para reconstruir el estado.
"""
from __future__ import annotations

import threading
import uuid
from datetime import datetime, timedelta, timezone

VIDA = timedelta(hours=8)
MAXIMO = 60  # sesiones abiertas a la vez; por encima se descarta la más vieja

_datos: dict[str, dict] = {}
_candado = threading.RLock()


class SesionExpirada(KeyError):
    """La sesión ya no existe. El mensaje se muestra tal cual al contador."""

    def __str__(self) -> str:  # pragma: no cover - texto fijo
        return "La sesión de trabajo expiró. Vuelva a subir los archivos del cliente."


def _ahora() -> datetime:
    return datetime.now(timezone.utc)


def _purgar() -> None:
    """Quita expiradas y, si aún sobran, las más antiguas."""
    limite = _ahora()
    for sid in [s for s, v in _datos.items() if v["expira"] < limite]:
        _datos.pop(sid, None)
    if len(_datos) > MAXIMO:
        sobrantes = sorted(_datos.items(), key=lambda kv: kv[1]["creada"])[: len(_datos) - MAXIMO]
        for sid, _ in sobrantes:
            _datos.pop(sid, None)


def crear(contenido: dict, cliente_id: str | None = None) -> str:
    sid = uuid.uuid4().hex
    with _candado:
        _purgar()
        _datos[sid] = {
            **contenido,
            "cliente_id": cliente_id,
            "creada": _ahora(),
            "expira": _ahora() + VIDA,
        }
    return sid


def obtener(sid: str) -> dict:
    with _candado:
        _purgar()
        sesion = _datos.get(sid or "")
        if not sesion:
            raise SesionExpirada(sid)
        sesion["expira"] = _ahora() + VIDA  # cada uso renueva la vida
        return sesion


def actualizar(sid: str, **campos) -> dict:
    with _candado:
        sesion = obtener(sid)
        sesion.update(campos)
        return sesion


def cerrar(sid: str) -> None:
    with _candado:
        _datos.pop(sid or "", None)


def abiertas() -> int:
    with _candado:
        _purgar()
        return len(_datos)
