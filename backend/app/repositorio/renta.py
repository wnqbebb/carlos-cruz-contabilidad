"""Declaraciones de renta (formulario 210): una por cliente y año gravable, con historial."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import delete, desc, insert, select, update

from ..db import conexion, lectura
from ..esquema import clientes as TC
from ..esquema import renta_declaraciones as T
from ..esquema import renta_recortes as TR
from ..esquema import renta_versiones as TV
from ..exactitud import a_json

ESTADOS = ("sin_informacion", "borrador", "revisada", "presentada")


def _fila(r) -> dict:
    d = dict(r._mapping)
    for k in ("creado", "actualizado"):
        if d.get(k) is not None:
            d[k] = d[k].isoformat()
    d["datos"] = d.get("datos") or {}
    return d


def obtener(cliente_id: str, anio: int) -> dict | None:
    with lectura() as cn:
        r = cn.execute(select(T).where(T.c.cliente_id == cliente_id, T.c.anio == anio)).first()
    return _fila(r) if r else None


def por_id(declaracion_id: str) -> dict | None:
    with lectura() as cn:
        r = cn.execute(select(T).where(T.c.id == declaracion_id)).first()
    return _fila(r) if r else None


def obtener_o_crear(cliente_id: str, anio: int) -> dict:
    actual = obtener(cliente_id, anio)
    if actual:
        return actual
    nuevo = str(uuid.uuid4())
    with conexion() as cn:
        cn.execute(insert(T).values(id=nuevo, cliente_id=cliente_id, anio=anio, estado="sin_informacion", datos={}))
    return obtener(cliente_id, anio)  # type: ignore[return-value]


def guardar(declaracion_id: str, *, datos: dict | None = None, resultado: dict | None = None,
            estado: str | None = None, presentada: dict | None = None, motivo: str = "") -> dict:
    """Guarda y deja la versión anterior en el historial."""
    with conexion() as cn:
        anterior = cn.execute(select(T).where(T.c.id == declaracion_id)).first()
        if anterior is None:
            raise KeyError("La declaración no existe.")
        if motivo:
            cn.execute(insert(TV).values(declaracion_id=declaracion_id, motivo=motivo,
                                         datos=anterior.datos or {}, resultado=anterior.resultado))
        valores: dict = {"actualizado": datetime.now(timezone.utc)}
        if datos is not None:
            valores["datos"] = a_json(datos)
        if resultado is not None:
            valores["resultado"] = a_json(resultado)
        if estado is not None:
            assert estado in ESTADOS
            valores["estado"] = estado
        if presentada is not None:
            valores["presentada"] = a_json(presentada)
        cn.execute(update(T).where(T.c.id == declaracion_id).values(**valores))
    return por_id(declaracion_id)  # type: ignore[return-value]


def versiones(declaracion_id: str) -> list[dict]:
    with lectura() as cn:
        filas = cn.execute(select(TV.c.id, TV.c.motivo, TV.c.creado).where(TV.c.declaracion_id == declaracion_id)
                           .order_by(desc(TV.c.creado), desc(TV.c.id))).all()
    return [{"id": f.id, "motivo": f.motivo, "creado": f.creado.isoformat() if f.creado else None} for f in filas]


def cartera(anio: int) -> list[dict]:
    """Personas naturales activas con su declaración del año (si la hay)."""
    with lectura() as cn:
        filas = cn.execute(
            select(TC.c.id, TC.c.razon_social, TC.c.nit, TC.c.dv, TC.c.estado.label("estado_cliente"),
                   T.c.id.label("declaracion_id"), T.c.estado, T.c.resultado, T.c.presentada, T.c.actualizado)
            .select_from(TC.outerjoin(T, (T.c.cliente_id == TC.c.id) & (T.c.anio == anio)))
            .where(TC.c.tipo_persona == "natural", TC.c.estado == "activo")
            .order_by(TC.c.razon_social)).all()
    out = []
    for f in filas:
        d = dict(f._mapping)
        d["actualizado"] = d["actualizado"].isoformat() if d.get("actualizado") else None
        d["estado"] = d.get("estado") or "sin_informacion"
        out.append(d)
    return out


def guardar_recortes(declaracion_id: str, recortes: dict[str, bytes]) -> None:
    if not recortes:
        return
    with conexion() as cn:
        ids = list(recortes)
        cn.execute(delete(TR).where(TR.c.id.in_(ids)))
        cn.execute(insert(TR), [{"id": k, "declaracion_id": declaracion_id, "png": v} for k, v in recortes.items()])


def recorte(declaracion_id: str, recorte_id: str) -> bytes | None:
    with lectura() as cn:
        r = cn.execute(select(TR.c.png).where(TR.c.declaracion_id == declaracion_id, TR.c.id == recorte_id)).first()
    return bytes(r.png) if r else None


def borrar_recortes(declaracion_id: str) -> None:
    with conexion() as cn:
        cn.execute(delete(TR).where(TR.c.declaracion_id == declaracion_id))
