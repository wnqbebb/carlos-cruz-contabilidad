"""Los datos de ENTRADA de un periodo: lo que el motor recibió para calcularlo.

POR QUÉ EXISTE (rescate)
Hasta la v2.4 cada periodo guardaba solo el resultado del motor (≈140 KB de JSON, 82 % de
reportes ya formateados) y los archivos subidos se borraban a las 8 horas. Eso tenía tres
consecuencias:
  · no se podía editar nada dentro de la aplicación: no quedaba de dónde recalcular;
  · el historial copiaba el resultado entero en cada recálculo;
  · 10.000 clientes no cabían en la base gratuita (500 MB).

Ahora se guarda el paquete de entrada (movimientos, saldos iniciales, inventario, nómina,
activos fijos…), la empresa, la configuración y las decisiones, en JSON comprimido con zlib.
Con eso:
  · `recalcular()` reproduce el resultado completo cuando se necesita;
  · el editor «Datos del periodo» cambia el paquete y recalcula;
  · cada versión del historial pesa unos pocos KB.

Los importes viajan como texto decimal (ver `exactitud.py`): nunca pasan por float.
"""
from __future__ import annotations

import dataclasses
import json
import typing
import zlib
from datetime import date
from decimal import Decimal
from functools import lru_cache

from ..exactitud import a_json
from ..modelos import (ActivoFijo, Alerta, AporteSocio, ConteoFisico, Empleado, Empresa, MovInventario, Movimiento,
                       Paquete, SaldoInicial)
from ..utils.numeros import parse_fecha

FORMATO = 1
# Qué clase lleva cada lista del paquete.
CLASES = {
    "saldos_iniciales": SaldoInicial, "movimientos": Movimiento, "ajustes_manuales": Movimiento,
    "inventario_movs": MovInventario, "inventario_fisico": ConteoFisico, "activos_fijos": ActivoFijo,
    "empleados": Empleado, "aportes_socios": AporteSocio, "alertas": Alerta,
}


@lru_cache(maxsize=None)
def _tipos(cls) -> dict[str, typing.Any]:
    return typing.get_type_hints(cls)


def _valor(tipo, v):
    """Convierte un valor JSON al tipo del campo (Decimal, date, int…)."""
    if v is None:
        return None
    base = {a for a in typing.get_args(tipo) if a is not type(None)} or {tipo}
    if Decimal in base:
        return v if isinstance(v, Decimal) else Decimal(str(v))
    if date in base:
        return parse_fecha(v)
    if int in base and not isinstance(v, bool):
        try:
            return int(v)
        except (TypeError, ValueError):
            return v
    return v


def _objeto(cls, datos: dict):
    tipos = _tipos(cls)
    campos = {f.name for f in dataclasses.fields(cls)}
    return cls(**{k: _valor(tipos.get(k), v) for k, v in (datos or {}).items() if k in campos})


def paquete_desde_json(datos: dict) -> Paquete:
    p = Paquete()
    p.empresa = datos.get("empresa")
    for nombre, cls in CLASES.items():
        setattr(p, nombre, [_objeto(cls, x) for x in datos.get(nombre) or []])
    for nombre in ("filas_ignoradas", "auditoria_nomina", "auditoria_ef", "titulos"):
        setattr(p, nombre, list(datos.get(nombre) or []))
    return p


def empaquetar(paquete: Paquete, empresa: Empresa, config: dict | None = None, decisiones: dict | None = None,
               alertas: list | None = None, aud_nomina: list | None = None, aud_ef: list | None = None,
               origenes: dict | None = None) -> dict:
    """La entrada completa como dict JSON (importes en texto)."""
    return {
        "formato": FORMATO,
        "paquete": a_json(paquete),
        "empresa": a_json(empresa),
        "config": a_json(config or {}),
        "decisiones": dict(decisiones or {}),
        "alertas": a_json(list(alertas or [])),
        "aud_nomina": a_json(list(aud_nomina or [])),
        "aud_ef": a_json(list(aud_ef or [])),
        "origenes": dict(origenes or {}),
    }


def comprimir(entrada: dict) -> bytes:
    crudo = json.dumps(entrada, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return zlib.compress(crudo, 9)


def descomprimir(contenido: bytes) -> dict:
    return json.loads(zlib.decompress(bytes(contenido)).decode("utf-8"))


def piezas(entrada: dict):
    """(paquete, empresa, config, decisiones, alertas, aud_nomina, aud_ef, origenes) listos para el motor."""
    from ..motor import Config

    return (
        paquete_desde_json(entrada.get("paquete") or {}),
        Empresa.desde_dict(entrada.get("empresa") or {}),
        Config.desde_dict(entrada.get("config") or {}),
        dict(entrada.get("decisiones") or {}),
        [_objeto(Alerta, a) for a in entrada.get("alertas") or []],
        list(entrada.get("aud_nomina") or []),
        list(entrada.get("aud_ef") or []),
        dict(entrada.get("origenes") or {}),
    )


def recalcular(entrada: dict) -> dict:
    """Corre el motor con la entrada guardada. Devuelve el resultado crudo del motor."""
    from .. import motor

    paquete, empresa, config, decisiones, alertas, aud_nom, aud_ef, _ = piezas(entrada)
    return motor.calcular(paquete, empresa, config, decisiones, alertas, aud_nom, aud_ef)


# ── salida del motor ───────────────────────────────────────────────────────
# Lo pesado del resultado que se puede volver a armar desde la entrada: no se guarda.
DERIVADOS = ("reportes", "cuentas_t")


def movimientos_del_resultado(resultado: dict) -> list[dict]:
    """Movimientos del libro mayor ajustado, para guardarlos como libro diario."""
    mayor = resultado.get("mayor_ajustado") or {}
    filas = []
    for cuenta in mayor.values():
        for m in getattr(cuenta, "movimientos", []) or []:
            filas.append({
                "cuenta": getattr(m, "cuenta", ""),
                "nombre_cuenta": getattr(m, "nombre_cuenta", ""),
                "debito": getattr(m, "debito", 0), "credito": getattr(m, "credito", 0),
                "fecha": getattr(m, "fecha", None), "comprobante": getattr(m, "comprobante", ""),
                "tipo": getattr(m, "tipo", ""), "tercero_id": getattr(m, "tercero_id", ""),
                "tercero_nombre": getattr(m, "tercero_nombre", ""),
                "descripcion": getattr(m, "descripcion", ""), "origen": getattr(m, "origen", ""),
            })
    return a_json(filas)


def salida(resultado: dict, origenes: dict[str, list[str]]) -> dict:
    """El resultado del motor en JSON, tal como lo pinta la pantalla."""
    out = a_json({k: v for k, v in resultado.items() if k != "mayor_ajustado"})
    usados = {m["origen"] for m in movimientos_del_resultado(resultado) if m.get("origen")}
    out["origenes"] = {k: v for k, v in (origenes or {}).items() if k in usados}
    return out


# Lo único que se guarda del resultado: lo que leen el tablero y las sugerencias sin abrir el
# periodo. Todo lo demás (reportes, inventario, nómina, ajustes, notas…) se rearma desde la entrada.
CONSERVAR = ("empresa", "resumen", "alertas", "origenes")


def ligera(salida_json: dict) -> dict:
    """La salida reducida a lo que se consulta sin abrir el periodo (≈1 KB). Es lo que se guarda."""
    out = {k: v for k, v in salida_json.items() if k in CONSERVAR}
    out["_derivados_fuera"] = True
    return out
