"""Parámetros legales laborales por año (editables; nada quemado en el código)."""
from __future__ import annotations

import json
from datetime import date
from decimal import Decimal

from ..config import DATA
from ..repositorio import parametros as repo

ARCHIVO = DATA / "parametros_legales.json"

CAMPOS_DECIMALES = [
    "smmlv", "aux_transporte", "salud_empleado", "pension_empleado", "salud_empleador", "pension_empleador",
    "caja", "sena", "icbf", "cesantias", "intereses_cesantias_mensual", "prima", "vacaciones",
]


class ParametrosFaltantes(Exception):
    pass


def _leer() -> dict:
    """Lee de la base (fuente de verdad). Si la base no responde, usa el JSON local."""
    try:
        return repo.todos()
    except Exception:  # sin base disponible la nómina igual debe poder calcularse
        return json.loads(ARCHIVO.read_text(encoding="utf-8"))


def todos() -> dict:
    return {k: v for k, v in _leer().items() if not k.startswith("_")}


def obtener(año: int) -> dict:
    datos = _leer()
    if str(año) not in datos:
        raise ParametrosFaltantes(
            f"No hay parámetros legales cargados para el año {año}. Ingrese el SMMLV y el auxilio de transporte "
            f"de {año} en la pantalla «Parámetros» (la aplicación no inventa estos valores)."
        )
    p = dict(datos[str(año)])
    for campo in CAMPOS_DECIMALES:
        p[campo] = Decimal(str(p[campo]))
    p["arl"] = {int(k): Decimal(str(v)) for k, v in p["arl"].items()}
    p["fsp_tramos"] = [{"desde_smmlv": Decimal(str(t["desde_smmlv"])), "tasa": Decimal(str(t["tasa"]))} for t in p["fsp_tramos"]]
    p["tope_aux_transporte_smmlv"] = Decimal(str(p["tope_aux_transporte_smmlv"]))
    p["tope_exoneracion_smmlv"] = Decimal(str(p["tope_exoneracion_smmlv"]))
    return p


def horas_semana(p: dict, fecha: date) -> int:
    tramos = sorted(p["jornada_tramos"], key=lambda t: t["desde"])
    horas = tramos[0]["horas_semana"]
    for t in tramos:
        if date.fromisoformat(t["desde"]) <= fecha:
            horas = t["horas_semana"]
    return int(horas)


def guardar(año: int, valores: dict) -> dict:
    """Crea o actualiza un año. Un año nuevo copia las tasas del año cargado más cercano y exige SMMLV y auxilio."""
    datos = _leer()
    clave = str(año)
    if clave not in datos:
        if not valores.get("smmlv") or not valores.get("aux_transporte"):
            raise ValueError("Para crear un año nuevo debe indicar el SMMLV y el auxilio de transporte.")
        años = sorted(int(k) for k in datos if k.isdigit())
        cercano = max((a for a in años if a < año), default=años[0])
        base = json.loads(json.dumps(datos[str(cercano)]))
        ultimo = sorted(base["jornada_tramos"], key=lambda t: t["desde"])[-1]
        base["jornada_tramos"] = [{"desde": f"{año}-01-01", "horas_semana": ultimo["horas_semana"]}]
        datos[clave] = base
    for k, v in valores.items():
        if k in CAMPOS_DECIMALES:
            datos[clave][k] = str(v)
        elif k in ("jornada_tramos", "arl", "fsp_tramos", "tope_aux_transporte_smmlv", "tope_exoneracion_smmlv"):
            datos[clave][k] = v
    repo.guardar(año, datos[clave])
    return datos[clave]
