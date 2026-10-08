"""Parámetros legales laborales por año (v2.3 · Fase 2).

Viven DENTRO de la aplicación, en `data/parametros_legales.json`, versionados por
año y con la fuente oficial de cada valor (decreto o resolución). Ya no se editan
desde una pantalla: si falta un año, la aplicación no inventa nada, avisa en el
Tablero y bloquea el cálculo de nómina de ese año con un mensaje claro. Cómo se
agrega un año nuevo está en `docs/MANTENIMIENTO.md`.
"""
from __future__ import annotations

import json
from datetime import date
from decimal import Decimal
from functools import lru_cache

from ..config import DATA

ARCHIVO = DATA / "parametros_legales.json"

CAMPOS_DECIMALES = [
    "smmlv", "aux_transporte", "salud_empleado", "pension_empleado", "salud_empleador", "pension_empleador",
    "caja", "sena", "icbf", "cesantias", "intereses_cesantias_mensual", "prima", "vacaciones",
]


class ParametrosFaltantes(Exception):
    pass


def mensaje_faltan(año: int) -> str:
    return (f"Faltan los valores legales de {año} (salario mínimo y auxilio de transporte). La nómina de {año} no se "
            "calcula hasta que la aplicación los traiga: la aplicación no inventa estos valores.")


@lru_cache(maxsize=1)
def _leer() -> dict:
    return json.loads(ARCHIVO.read_text(encoding="utf-8"))


def todos() -> dict:
    return {k: v for k, v in _leer().items() if k.isdigit()}


def anios() -> list[int]:
    return sorted(int(a) for a in todos())


def hay(año: int) -> bool:
    return str(año) in todos()


def obtener(año: int) -> dict:
    datos = todos()
    if str(año) not in datos:
        raise ParametrosFaltantes(mensaje_faltan(año))
    p = dict(datos[str(año)])
    for campo in CAMPOS_DECIMALES:
        p[campo] = Decimal(str(p[campo]))
    p["arl"] = {int(k): Decimal(str(v)) for k, v in p["arl"].items()}
    p["fsp_tramos"] = [{"desde_smmlv": Decimal(str(t["desde_smmlv"])), "tasa": Decimal(str(t["tasa"]))} for t in p["fsp_tramos"]]
    p["tope_aux_transporte_smmlv"] = Decimal(str(p["tope_aux_transporte_smmlv"]))
    p["tope_exoneracion_smmlv"] = Decimal(str(p["tope_exoneracion_smmlv"]))
    if "uvt" in p:
        p["uvt"] = Decimal(str(p["uvt"]))
    return p


def horas_semana(p: dict, fecha: date) -> int:
    tramos = sorted(p["jornada_tramos"], key=lambda t: t["desde"])
    horas = tramos[0]["horas_semana"]
    for t in tramos:
        if date.fromisoformat(t["desde"]) <= fecha:
            horas = t["horas_semana"]
    return int(horas)
