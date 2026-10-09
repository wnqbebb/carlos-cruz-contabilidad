"""Bitácora: qué se hizo, cuándo y sobre qué cliente.

POR QUÉ EXISTE
El 6 de octubre de 2026 un cálculo reemplazó un periodo cerrado y no quedó
ningún rastro de quién lo había hecho ni con qué archivo. Reconstruirlo costó
leer la base entera. Desde la v2.2 cada acción que cambia datos deja una línea
aquí, y la ficha del cliente la muestra.

Registrar NUNCA puede tumbar la operación: si la bitácora falla, el trabajo del
contador sigue. Por eso todo va dentro de un try.
"""
from __future__ import annotations

import logging
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import desc, insert, select, update

from ..db import conexion, lectura
from ..esquema import bitacora as T

log = logging.getLogger("carloscruz.bitacora")

# Acciones conocidas. El texto se muestra tal cual en la pantalla «Actividad».
ACCIONES = {
    "cliente_creado": "Cliente creado",
    "cliente_editado": "Ficha editada",
    "cliente_archivado": "Cliente archivado",
    "cliente_restaurado": "Cliente restaurado",
    "cliente_eliminado": "Cliente eliminado",
    "ingreso_fallido": "Intento de ingreso fallido",
    "clientes_demo_eliminados": "Clientes de demostración eliminados",
    "clientes_importados": "Directorio importado",
    "archivos_subidos": "Archivos subidos",
    "periodo_calculado": "Periodo calculado",
    "periodo_cerrado": "Cierre guardado",
    "periodo_reabierto": "Periodo reabierto",
    "periodo_eliminado": "Periodo eliminado",
    "version_restaurada": "Versión restaurada",
    "calculo_rechazado": "Cálculo rechazado",
    "tarea_pospuesta": "Tarea pospuesta",
    "tarea_iniciada": "Tarea empezada",
    "nota_periodo": "Nota de revisión",
    "parametros_guardados": "Parámetros legales guardados",
    "demo_eliminada": "Clientes de demostración eliminados",
    "renta_documentos": "Documentos de renta leídos",
    "renta_presentada": "Declaración de renta presentada",
}


def _llano(v):
    """Deja el detalle listo para JSON sin perder exactitud en los importes."""
    if isinstance(v, Decimal):
        return format(v, "f")
    if isinstance(v, (date, datetime)):
        return v.isoformat()
    if isinstance(v, dict):
        return {k: _llano(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [_llano(x) for x in v]
    return v


def registrar(accion: str, cliente_id: str | None = None, **detalle) -> None:
    """Deja una línea en la bitácora. Nunca lanza."""
    try:
        with conexion() as cn:
            cn.execute(insert(T).values(
                cliente_id=cliente_id or None,
                accion=accion,
                detalle=_llano(detalle),
            ))
    except Exception as ex:  # pragma: no cover - la bitácora jamás frena el trabajo
        log.warning("No se pudo registrar «%s» en la bitácora: %s", accion, ex)


def asociar_subida(subida_id: str, cliente_id: str) -> None:
    """La subida que dio de alta a un cliente se registró antes de que él existiera: se le asigna ahora."""
    try:
        with conexion() as cn:
            filas = cn.execute(select(T.c.id, T.c.detalle).where(T.c.cliente_id.is_(None), T.c.accion == "archivos_subidos")
                               .order_by(desc(T.c.id)).limit(50)).all()
            ids = [f.id for f in filas if (f.detalle or {}).get("subida") == subida_id]
            if ids:
                cn.execute(update(T).where(T.c.id.in_(ids)).values(cliente_id=cliente_id))
    except Exception as ex:  # pragma: no cover
        log.warning("No se pudo asociar la subida %s al cliente: %s", subida_id, ex)


def listar(cliente_id: str | None = None, limite: int = 50) -> list[dict]:
    """Últimas acciones, de la más reciente a la más vieja."""
    consulta = select(T).order_by(desc(T.c.creado), desc(T.c.id)).limit(max(1, min(int(limite or 50), 500)))
    if cliente_id:
        consulta = consulta.where(T.c.cliente_id == cliente_id)
    with lectura() as cn:
        filas = cn.execute(consulta).all()
    return [{
        "id": int(f.id),
        "cliente_id": str(f.cliente_id) if f.cliente_id else None,
        "accion": f.accion,
        "titulo": ACCIONES.get(f.accion, f.accion.replace("_", " ").capitalize()),
        "detalle": f.detalle or {},
        "creado": f.creado.isoformat(),
    } for f in filas]


def listar_acciones(acciones: tuple[str, ...], limite: int = 200) -> list[dict]:
    """Últimas líneas de ciertas acciones, de la más reciente a la más vieja."""
    with lectura() as cn:
        filas = cn.execute(select(T).where(T.c.accion.in_(acciones))
                           .order_by(desc(T.c.creado), desc(T.c.id)).limit(max(1, int(limite)))).all()
    return [{"id": int(f.id), "cliente_id": str(f.cliente_id) if f.cliente_id else None, "accion": f.accion,
             "detalle": f.detalle or {}, "creado": f.creado.isoformat()} for f in filas]


