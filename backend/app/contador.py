"""Los datos del contador dueño de la aplicación (H18).

Se muestran en el logotipo, en el preloader, en el saludo del tablero y en las
firmas. Antes estaban escritos a mano en el código de la interfaz; ahora salen
de aquí y se pueden cambiar en Parámetros › Sistema.

Orden de precedencia: lo que el contador guardó (`DATOS_APP/contador.json`) →
variables de entorno `CONTADOR_*` → `data/contador.json` (valores de la
instalación).
"""
from __future__ import annotations

import json
import os

from .config import DATA, DATOS_APP

CAMPOS = ("nombre", "nombre_corto", "cargo", "tarjeta_profesional", "municipio", "departamento")
GUARDADO = DATOS_APP / "contador.json"


def leer() -> dict:
    datos = {c: "" for c in CAMPOS}
    base = DATA / "contador.json"
    if base.exists():
        datos.update({k: str(v) for k, v in json.loads(base.read_text(encoding="utf-8")).items() if k in CAMPOS})
    for c in CAMPOS:
        valor = (os.getenv(f"CONTADOR_{c.upper()}") or "").strip()
        if valor:
            datos[c] = valor
    if GUARDADO.exists():
        try:
            datos.update({k: str(v) for k, v in json.loads(GUARDADO.read_text(encoding="utf-8")).items() if k in CAMPOS})
        except (OSError, ValueError):
            pass
    return datos


def guardar(cambios: dict) -> dict:
    datos = leer()
    datos.update({k: str(v or "").strip() for k, v in cambios.items() if k in CAMPOS})
    GUARDADO.parent.mkdir(parents=True, exist_ok=True)
    GUARDADO.write_text(json.dumps(datos, ensure_ascii=False, indent=2), encoding="utf-8")
    return datos
