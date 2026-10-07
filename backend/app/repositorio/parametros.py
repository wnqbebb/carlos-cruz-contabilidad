"""Parámetros legales por año, guardados en la base.

Antes vivían solo en `data/parametros_legales.json`. En un servidor con disco
efímero (Render, Fly) ese archivo se pierde en cada despliegue, así que ahora la
base es la fuente de verdad y el JSON solo sirve de semilla la primera vez.
"""
from __future__ import annotations

import json

from sqlalchemy import delete, insert, select

from ..config import DATA
from ..db import conexion, lectura
from ..esquema import parametros_legales as T

SEMILLA = DATA / "parametros_legales.json"


def _semilla() -> dict:
    if not SEMILLA.exists():
        return {}
    datos = json.loads(SEMILLA.read_text(encoding="utf-8"))
    return {k: v for k, v in datos.items() if k.isdigit()}


def sembrar_si_vacio() -> int:
    """Carga el JSON de semilla si la tabla está vacía. Devuelve cuántos años insertó."""
    with conexion() as cn:
        if cn.execute(select(T.c.anio).limit(1)).first():
            return 0
        filas = [
            {"anio": int(anio), "valores": valores, "fuente": "data/parametros_legales.json"}
            for anio, valores in _semilla().items()
        ]
        if filas:
            cn.execute(insert(T), filas)
        return len(filas)


def todos() -> dict:
    """{'2025': {...}, '2026': {...}} igual que el JSON original."""
    sembrar_si_vacio()
    with lectura() as cn:
        filas = cn.execute(select(T.c.anio, T.c.valores).order_by(T.c.anio)).all()
    datos = {str(f.anio): f.valores for f in filas}
    return datos or _semilla()


def guardar(anio: int, valores: dict, fuente: str = "editado en la aplicación") -> dict:
    sembrar_si_vacio()
    with conexion() as cn:
        cn.execute(delete(T).where(T.c.anio == int(anio)))
        cn.execute(insert(T).values(anio=int(anio), valores=valores, fuente=fuente))
    return valores


def anios() -> list[int]:
    return sorted(int(a) for a in todos())
