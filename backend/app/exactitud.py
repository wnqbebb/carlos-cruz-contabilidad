"""Serialización exacta de importes hacia la interfaz.

EL PROBLEMA
-----------
Todo el motor contable trabaja con `Decimal`, que es exacto. Pero si al mandar
la respuesta se convierte a `float`, la exactitud se pierde ahí mismo:

    >>> float(Decimal("1423500.10")) * 3
    4270500.299999999      ← ya no cuadra

Un `float` IEEE-754 no puede representar `0.1`. En un balance con miles de
líneas esos errores se acumulan y aparecen descuadres de centavos que el
contador no puede explicar.

LA SOLUCIÓN
-----------
Los importes viajan como CADENA con el valor decimal literal ("1423500.10").
JSON no tiene tipo decimal, pero una cadena sí es exacta. El frontend la
formatea sin convertirla a número (ver `frontend/src/formato.ts`).

Regla para quien siga este código: si va a mostrar o transportar un importe,
use `a_json`. Si va a calcular con él, use `Decimal`. Nunca `float`.
"""
from __future__ import annotations

import dataclasses
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path


def dec_a_texto(valor: Decimal) -> str:
    """Decimal → cadena decimal plana, sin notación científica ni ceros raros.

    `format(v, "f")` evita que Decimal("1E+7") salga como "1E+7".
    """
    return format(valor.normalize() if valor == valor.to_integral_value() else valor, "f")


def a_json(obj):
    """Convierte dataclasses, Decimal, fechas y Path a tipos JSON **sin perder exactitud**.

    Los `Decimal` salen como cadena. Los `int` y `bool` se dejan como están.
    """
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        return {f.name: a_json(getattr(obj, f.name)) for f in dataclasses.fields(obj)}
    if isinstance(obj, Decimal):
        return dec_a_texto(obj)
    if isinstance(obj, bool):  # antes que int: bool es subclase de int
        return obj
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, dict):
        return {str(k): a_json(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return [a_json(v) for v in obj]
    if isinstance(obj, Path):
        return str(obj)
    return obj


def suma(valores) -> Decimal:
    """Suma exacta de un iterable de importes. Punto único para auditar totales."""
    total = Decimal("0")
    for v in valores:
        if v is None or v == "":
            continue
        total += v if isinstance(v, Decimal) else Decimal(str(v))
    return total


def cuadra(izquierda: Decimal, derecha: Decimal, tolerancia: Decimal = Decimal("0")) -> bool:
    """¿Dos lados de una ecuación contable son iguales?

    La tolerancia es 0 por defecto a propósito: en contabilidad un peso de
    diferencia es un error, no un redondeo aceptable.
    """
    return abs(izquierda - derecha) <= tolerancia
