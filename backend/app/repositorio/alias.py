"""Alias de cuentas: el nombre que el cliente escribe en su Excel → código PUC.

Cada vez que el contador confirma un mapeo, queda guardado para ese cliente.
La próxima vez el sistema lo reconoce solo. Es la memoria que hace que el
trabajo del segundo mes sea mucho más rápido que el del primero.
"""
from __future__ import annotations

from sqlalchemy import func, insert, select, update

from ..db import conexion, lectura
from ..esquema import alias_cuenta as T
from ..utils import nit as unit
from ..utils.numeros import normalizar


def de_cliente(nit: str) -> dict[str, str]:
    """{nombre_normalizado: codigo} de un cliente, para alimentar el Mapeador."""
    base = unit.limpiar(nit)
    if not base:
        return {}
    with lectura() as cn:
        filas = cn.execute(
            select(T.c.nombre_norm, T.c.codigo).where(T.c.nit == base).order_by(T.c.id)
        ).all()
    return {f.nombre_norm: f.codigo for f in filas}


def guardar(nit: str, pares: dict[str, str], cliente_id: str | None = None) -> int:
    """Guarda o actualiza los mapeos confirmados. Devuelve cuántos cambiaron."""
    base = unit.limpiar(nit)
    if not base or not pares:
        return 0
    cambios = 0
    with conexion() as cn:
        for nombre, codigo in pares.items():
            nombre_norm = normalizar(nombre)
            codigo = str(codigo or "").strip()
            if not nombre_norm or not codigo:
                continue
            actual = cn.execute(
                select(T.c.id, T.c.codigo).where(
                    (T.c.nit == base) & (T.c.nombre_norm == nombre_norm)
                )
            ).first()
            if actual is None:
                cn.execute(insert(T).values(
                    cliente_id=cliente_id, nit=base, nombre_norm=nombre_norm, codigo=codigo, veces=1
                ))
                cambios += 1
            elif actual.codigo != codigo:
                cn.execute(update(T).where(T.c.id == actual.id).values(codigo=codigo, veces=1))
                cambios += 1
            else:
                cn.execute(update(T).where(T.c.id == actual.id).values(veces=T.c.veces + 1))
    return cambios


def listar(nit: str) -> list[dict]:
    """Diccionario aprendido de un cliente, para revisarlo o corregirlo a mano."""
    base = unit.limpiar(nit)
    if not base:
        return []
    with lectura() as cn:
        filas = cn.execute(
            select(T.c.id, T.c.nombre_norm, T.c.codigo, T.c.veces, T.c.creado)
            .where(T.c.nit == base).order_by(T.c.veces.desc(), T.c.nombre_norm)
        ).all()
    return [
        {"id": int(f.id), "nombre": f.nombre_norm, "codigo": f.codigo, "veces": int(f.veces),
         "creado": f.creado.isoformat(timespec="seconds") if f.creado else ""}
        for f in filas
    ]


def contar(nit: str) -> int:
    base = unit.limpiar(nit)
    if not base:
        return 0
    with lectura() as cn:
        return int(cn.execute(select(func.count()).select_from(T).where(T.c.nit == base)).scalar_one())
