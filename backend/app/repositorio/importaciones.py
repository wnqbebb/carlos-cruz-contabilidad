"""Qué archivos se subieron, cuándo y qué se reconoció en ellos.

Sirve para dos cosas: rastrear de dónde salió una cifra meses después, y
detectar que el mismo archivo se subió dos veces (mismo sha256).
"""
from __future__ import annotations

import hashlib
import logging
import uuid

from sqlalchemy import desc, insert, select

from ..db import conexion, lectura
from ..esquema import importaciones as T

log = logging.getLogger("carloscruz.importaciones")


def huella(contenido: bytes) -> str:
    """sha256 del archivo: identifica el contenido, no el nombre."""
    return hashlib.sha256(contenido).hexdigest()


def registrar(cliente_id: str | None, archivo: str, contenido: bytes,
              hojas: list[dict] | None = None) -> str | None:
    """Guarda una fila por archivo subido. Nunca lanza."""
    hojas = hojas or []
    formatos = sorted({str(h.get("formato") or "") for h in hojas if h.get("formato")})
    try:
        nuevo = str(uuid.uuid4())
        with conexion() as cn:
            cn.execute(insert(T).values(
                id=nuevo,
                cliente_id=cliente_id or None,
                archivo=archivo[:300],
                hoja=", ".join(str(h.get("hoja") or "") for h in hojas)[:300],
                formato=", ".join(formatos)[:120],
                sha256=huella(contenido),
                bytes=len(contenido),
                filas=sum(int(h.get("filas") or 0) for h in hojas),
                alertas=sum(len(h.get("alertas") or []) for h in hojas),
            ))
        return nuevo
    except Exception as ex:  # pragma: no cover - no frena la subida
        log.warning("No se pudo registrar la importación de «%s»: %s", archivo, ex)
        return None


def listar(cliente_id: str | None = None, limite: int = 50) -> list[dict]:
    consulta = select(T).order_by(desc(T.c.creado)).limit(max(1, min(int(limite or 50), 500)))
    if cliente_id:
        consulta = consulta.where(T.c.cliente_id == cliente_id)
    with lectura() as cn:
        filas = cn.execute(consulta).all()
    return [{
        "id": str(f.id),
        "cliente_id": str(f.cliente_id) if f.cliente_id else None,
        "archivo": f.archivo,
        "hoja": f.hoja,
        "formato": f.formato,
        "sha256": f.sha256,
        "bytes": int(f.bytes or 0),
        "filas": int(f.filas or 0),
        "alertas": int(f.alertas or 0),
        "creado": f.creado.isoformat(),
    } for f in filas]


def ya_subido(cliente_id: str | None, contenido: bytes) -> dict | None:
    """¿Este mismo archivo ya se había subido para este cliente?"""
    if not cliente_id:
        return None
    with lectura() as cn:
        fila = cn.execute(
            select(T.c.archivo, T.c.creado)
            .where((T.c.cliente_id == cliente_id) & (T.c.sha256 == huella(contenido)))
            .order_by(desc(T.c.creado)).limit(1)
        ).first()
    return {"archivo": fila.archivo, "creado": fila.creado.isoformat()} if fila else None
