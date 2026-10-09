"""Parámetros tributarios y diseño del formulario 210, versionados por año gravable.

Viven en `data/renta/parametros_ag{AAAA}.json` y `data/renta/210_ag{AAAA}.json`, cada
valor con su artículo del Estatuto Tributario y su fuente. Si falta un año, no se
inventa: se informa con `RentaSinParametros`.
"""
from __future__ import annotations

import json
from decimal import Decimal
from functools import lru_cache

from ..config import DATA

CARPETA = DATA / "renta"


class RentaSinParametros(Exception):
    pass


def anios() -> list[int]:
    return sorted(int(p.stem.removeprefix("parametros_ag")) for p in CARPETA.glob("parametros_ag*.json"))


@lru_cache(maxsize=8)
def obtener(anio: int) -> dict:
    archivo = CARPETA / f"parametros_ag{anio}.json"
    if not archivo.exists():
        raise RentaSinParametros(
            f"Todavía no están los valores tributarios del año gravable {anio}. La aplicación no los inventa: "
            "hay que agregarlos con su norma (ver docs/MANTENIMIENTO.md).")
    return json.loads(archivo.read_text(encoding="utf-8"))


@lru_cache(maxsize=8)
def formulario(anio: int) -> dict:
    archivo = CARPETA / f"210_ag{anio}.json"
    if not archivo.exists():
        raise RentaSinParametros(f"Todavía no está el diseño del formulario 210 del año gravable {anio}.")
    return json.loads(archivo.read_text(encoding="utf-8"))


def nombres_casillas(anio: int) -> dict[int, dict]:
    return {c["casilla"]: c for c in formulario(anio)["casillas"]}


def d(valor) -> Decimal:
    return Decimal(str(valor))


def uvt(anio: int) -> Decimal:
    return d(obtener(anio)["uvt"]["valor"])
