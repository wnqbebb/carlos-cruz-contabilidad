"""Periodos contables por cliente: indicadores, resultado completo, cierres y movimientos.

Cada periodo guarda dos cosas:
  1. Indicadores resumidos en columnas NUMERIC (para listar, ordenar y graficar
     miles de periodos sin abrir nada grande).
  2. El resultado completo del motor en `resultados.payload` (JSONB), que es lo
     que la pantalla de resultados vuelve a pintar tal cual se calculó.

Los importes viajan como CADENA decimal, nunca como float. Ver `exactitud.py`.
"""
from __future__ import annotations

import uuid
from collections import OrderedDict
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Iterable

from sqlalchemy import and_, case, delete, func, insert, select, update

from ..db import conexion, lectura
from ..esquema import cierres as TC
from ..esquema import historial_periodos as TH
from ..esquema import movimientos as TM
from ..esquema import periodo_entradas as TE
from ..esquema import periodos as TP
from ..esquema import resultados as TR
from ..modelos import SaldoInicial
from ..utils.numeros import CERO, D, parse_fecha

INDICADORES = (
    "total_activo", "total_pasivo", "total_patrimonio",
    "total_ingresos", "total_gastos", "utilidad", "descuadre",
)


class ErrorPeriodo(ValueError):
    """Periodo inválido; el mensaje se muestra tal cual al contador."""


class PeriodoCerrado(ErrorPeriodo):
    """Se intentó escribir sobre un periodo ya cerrado. La API lo traduce a 409."""


class ResultadoVacio(ErrorPeriodo):
    """El cálculo no aportó ninguna cuenta: guardarlo borraría el trabajo anterior."""


def _txt(v) -> str | None:
    if v is None:
        return None
    return format(v if isinstance(v, Decimal) else D(v), "f")


def _a_dict(fila) -> dict:
    d = dict(fila._mapping)
    d["id"] = str(d["id"])
    d["cliente_id"] = str(d["cliente_id"])
    for k, v in list(d.items()):
        if isinstance(v, Decimal):
            d[k] = format(v, "f")
        elif isinstance(v, (date, datetime)):
            d[k] = v.isoformat()
    return d


def _indicadores(resumen: dict) -> dict:
    """Extrae del resumen del motor las columnas del periodo. Todo en Decimal."""
    return {
        "total_activo": D(resumen.get("total_activo")),
        "total_pasivo": D(resumen.get("total_pasivo")),
        "total_patrimonio": D(resumen.get("total_patrimonio")),
        "total_ingresos": D(resumen.get("ingresos")),
        "total_gastos": D(resumen.get("total_gastos")),
        "utilidad": D(resumen.get("utilidad_neta")),
        "descuadre": D(resumen.get("descuadre_esf")),
        "cuadra": D(resumen.get("descuadre_esf")) == CERO,
        "cuentas": int(resumen.get("cuentas") or 0),
    }


def _json_llano(v):
    """Decimal → texto exacto, fecha → ISO. Para guardar en JSON sin perder un centavo."""
    if isinstance(v, Decimal):
        return format(v, "f")
    if isinstance(v, (date, datetime)):
        return v.isoformat()
    if isinstance(v, uuid.UUID):
        return str(v)
    return v


def _instantanea(cn, periodo_id: str, motivo: str) -> int | None:
    """Copia al historial todo lo que hay hoy en el periodo, antes de reemplazarlo.

    Devuelve el id de la versión, o None si no había nada que guardar (periodo
    recién creado). Se llama SIEMPRE dentro de la misma transacción que borra.
    """
    fila = cn.execute(select(TP).where(TP.c.id == periodo_id)).first()
    if not fila:
        return None
    res = cn.execute(select(TR.c.payload, TR.c.peticion).where(TR.c.periodo_id == periodo_id)).first()
    ent = cn.execute(select(TE.c.contenido).where(TE.c.periodo_id == periodo_id)).scalar()
    cie = cn.execute(select(TC.c.fecha_corte, TC.c.saldos, TC.c.cuentas)
                     .where(TC.c.periodo_id == periodo_id)).first()
    n_movs = cn.execute(select(func.count()).select_from(TM).where(TM.c.periodo_id == periodo_id)).scalar_one()
    if not res and not n_movs and not cie and not ent:
        return None   # nada que preservar

    if ent:
        # Con la entrada basta: el resultado y el libro diario se rearman al restaurar (pocos KB por versión).
        movimientos = []
    else:
        movs = cn.execute(select(TM).where(TM.c.periodo_id == periodo_id).order_by(TM.c.id)).all()
        movimientos = [{k: _json_llano(v) for k, v in dict(m._mapping).items()} for m in movs]
    periodo = {k: _json_llano(v) for k, v in dict(fila._mapping).items()}
    periodo["_movimientos_n"] = int(n_movs)   # para listar versiones sin abrir el JSON
    cierre = None
    if cie:
        cierre = {"fecha_corte": cie.fecha_corte.isoformat(), "saldos": cie.saldos, "cuentas": cie.cuentas}

    nuevo = cn.execute(insert(TH).values(
        periodo_id=periodo_id,
        cliente_id=str(fila.cliente_id),
        motivo=motivo,
        periodo=periodo,
        resultado=(res.payload if res else None) if not ent else None,
        peticion=res.peticion if res else None,
        movimientos=movimientos,
        cierre=cierre,
        cuentas=int(fila.cuentas or 0),
        entrada=ent,
    ).returning(TH.c.id)).scalar()
    return int(nuevo) if nuevo is not None else None


def versiones(periodo_id: str) -> list[dict]:
    """Versiones anteriores de un periodo, de la más nueva a la más vieja."""
    with lectura() as cn:
        filas = cn.execute(
            select(TH.c.id, TH.c.motivo, TH.c.cuentas, TH.c.creado, TH.c.periodo, TH.c.cierre)
            .where(TH.c.periodo_id == periodo_id)
            .order_by(TH.c.creado.desc(), TH.c.id.desc())
        ).all()
    salida = []
    for f in filas:
        datos = dict(f._mapping)
        periodo = datos.get("periodo") or {}
        salida.append({
            "id": int(datos["id"]),
            "motivo": datos["motivo"],
            "cuentas": int(datos["cuentas"] or 0),
            "creado": datos["creado"].isoformat(),
            "movimientos": int(periodo.get("_movimientos_n") or 0),
            "estado": periodo.get("estado", ""),
            "total_activo": periodo.get("total_activo"),
            "utilidad": periodo.get("utilidad"),
            # El tipo Json guarda None como «null», no como NULL: hay que mirar el valor.
            "con_cierre": bool(datos.get("cierre")),
        })
    return salida


def version(version_id: int) -> dict:
    """Una versión completa del historial, tal como se guardó."""
    with lectura() as cn:
        fila = cn.execute(select(TH).where(TH.c.id == int(version_id))).first()
    if not fila:
        raise ErrorPeriodo("Esa versión del periodo no existe.")
    d = dict(fila._mapping)
    d["id"] = int(d["id"])
    d["periodo_id"] = str(d["periodo_id"])
    d["cliente_id"] = str(d["cliente_id"])
    d["creado"] = d["creado"].isoformat()
    return d


def restaurar_version(version_id: int) -> dict:
    """Devuelve el periodo al estado exacto de una versión guardada.

    Antes de pisar lo que hay ahora, se guarda otra versión: restaurar nunca
    destruye el estado actual, solo lo deja atrás.
    """
    with conexion() as cn:
        v = cn.execute(select(TH).where(TH.c.id == int(version_id))).first()
        if not v:
            raise ErrorPeriodo("Esa versión del periodo no existe.")
        periodo_id = str(v.periodo_id)
        actual = cn.execute(select(TP.c.id).where(TP.c.id == periodo_id)).first()
        if not actual:
            raise ErrorPeriodo("El periodo de esa versión ya no existe.")

        _instantanea(cn, periodo_id, "restauracion")

        guardado = v.periodo or {}
        valores = {k: D(guardado.get(k)) for k in INDICADORES}
        valores.update({
            "estado": guardado.get("estado") or "calculado",
            "cuadra": bool(guardado.get("cuadra", True)),
            "cuentas": int(guardado.get("cuentas") or 0),
            "calculado_en": datetime.now(timezone.utc),
            "cerrado_en": datetime.now(timezone.utc) if guardado.get("estado") == "cerrado" else None,
        })
        cn.execute(update(TP).where(TP.c.id == periodo_id).values(**valores))

        cn.execute(delete(TR).where(TR.c.periodo_id == periodo_id))
        cn.execute(delete(TE).where(TE.c.periodo_id == periodo_id))
        movs_version = list(v.movimientos or [])
        if v.entrada:
            from ..contabilidad import entrada as E

            datos_ent = E.descomprimir(v.entrada)
            crudo = E.recalcular(datos_ent)
            salida_v = E.salida(crudo, datos_ent.get("origenes") or {})
            cn.execute(insert(TR).values(periodo_id=periodo_id, cliente_id=str(v.cliente_id),
                                         payload=E.ligera(salida_v), peticion=v.peticion or {}))
            cn.execute(insert(TE).values(periodo_id=periodo_id, cliente_id=str(v.cliente_id),
                                         contenido=v.entrada, bytes=len(v.entrada)))
            movs_version = E.movimientos_del_resultado(crudo)
        elif v.resultado:
            cn.execute(insert(TR).values(
                periodo_id=periodo_id, cliente_id=str(v.cliente_id),
                payload=v.resultado, peticion=v.peticion or {},
            ))

        cn.execute(delete(TM).where(TM.c.periodo_id == periodo_id))
        for m in movs_version:
            datos = {k: m.get(k) for k in (
                "fecha", "cuenta", "nombre_cuenta", "debito", "credito", "comprobante",
                "tipo", "tercero_id", "tercero_nombre", "descripcion", "origen", "base_retencion")}
            datos["fecha"] = parse_fecha(datos.get("fecha"))
            datos["debito"] = D(datos.get("debito"))
            datos["credito"] = D(datos.get("credito"))
            datos["base_retencion"] = None if datos.get("base_retencion") in (None, "") else D(datos["base_retencion"])
            cn.execute(insert(TM).values(cliente_id=str(v.cliente_id), periodo_id=periodo_id, **datos))

        cn.execute(delete(TC).where(TC.c.periodo_id == periodo_id))
        if v.cierre:
            cn.execute(insert(TC).values(
                cliente_id=str(v.cliente_id), periodo_id=periodo_id,
                fecha_corte=parse_fecha(v.cierre.get("fecha_corte")),
                saldos=v.cierre.get("saldos") or [], cuentas=int(v.cierre.get("cuentas") or 0),
            ))
        fila = cn.execute(select(TP).where(TP.c.id == periodo_id)).one()
    _cache_resultado.pop(periodo_id, None)
    return _a_dict(fila)


# ── alta y consulta ─────────────────────────────────────────────────────────
def buscar(cliente_id: str, desde: date, hasta: date) -> dict | None:
    """El periodo con esas fechas, si existe. No crea nada."""
    with lectura() as cn:
        fila = cn.execute(
            select(TP).where(and_(TP.c.cliente_id == cliente_id, TP.c.desde == desde, TP.c.hasta == hasta))
        ).first()
    return _a_dict(fila) if fila else None


def asegurar(cliente_id: str, desde: date, hasta: date, etiqueta: str = "") -> dict:
    """Devuelve el periodo (lo crea si no existía). Idempotente."""
    desde, hasta = parse_fecha(desde), parse_fecha(hasta)
    if not desde or not hasta:
        raise ErrorPeriodo("Las fechas del periodo son obligatorias.")
    if hasta < desde:
        raise ErrorPeriodo("El periodo es inválido: la fecha final es anterior a la inicial.")
    with conexion() as cn:
        fila = cn.execute(
            select(TP).where(and_(TP.c.cliente_id == cliente_id, TP.c.desde == desde, TP.c.hasta == hasta))
        ).first()
        if fila:
            return _a_dict(fila)
        nuevo = str(uuid.uuid4())
        cn.execute(insert(TP).values(
            id=nuevo, cliente_id=cliente_id, desde=desde, hasta=hasta,
            etiqueta=etiqueta or "", estado="borrador", descuadre=Decimal("0"),
            cuadra=True, cuentas=0,
        ))
        return _a_dict(cn.execute(select(TP).where(TP.c.id == nuevo)).one())


def listar(cliente_id: str, limite: int = 120) -> list[dict]:
    with lectura() as cn:
        filas = cn.execute(
            select(TP).where(TP.c.cliente_id == cliente_id)
            .order_by(TP.c.hasta.desc(), TP.c.desde.desc())
            .limit(max(1, min(int(limite or 120), 1000)))
        ).all()
        # Cuántas versiones guardadas tiene cada periodo, en una sola consulta.
        ids = [f.id for f in filas]
        conteo = dict(cn.execute(
            select(TH.c.periodo_id, func.count()).where(TH.c.periodo_id.in_(ids)).group_by(TH.c.periodo_id)
        ).all()) if ids else {}
    salida = []
    for f in filas:
        d = _a_dict(f)
        d["versiones_n"] = int(conteo.get(f.id, 0))
        salida.append(d)
    return salida


def obtener(periodo_id: str) -> dict:
    with lectura() as cn:
        fila = cn.execute(select(TP).where(TP.c.id == periodo_id)).first()
        if not fila:
            raise ErrorPeriodo("El periodo no existe.")
        return _a_dict(fila)


def ultimo(cliente_id: str) -> dict | None:
    with lectura() as cn:
        fila = cn.execute(
            select(TP).where(TP.c.cliente_id == cliente_id).order_by(TP.c.hasta.desc()).limit(1)
        ).first()
    return _a_dict(fila) if fila else None


def eliminar(periodo_id: str) -> dict:
    with conexion() as cn:
        fila = cn.execute(select(TP.c.desde, TP.c.hasta, TP.c.estado).where(TP.c.id == periodo_id)).first()
        if not fila:
            raise ErrorPeriodo("El periodo no existe o ya fue eliminado.")
        if fila.estado == "cerrado":
            raise ErrorPeriodo(
                "No se puede eliminar un periodo cerrado. Reabra el cierre primero para no romper "
                "los saldos iniciales del periodo siguiente."
            )
        cn.execute(delete(TP).where(TP.c.id == periodo_id))
        return {"ok": True, "desde": fila.desde.isoformat(), "hasta": fila.hasta.isoformat()}


# ── resultado del motor ─────────────────────────────────────────────────────
def guardar_resultado(cliente_id: str, resultado_json: dict, peticion: dict | None = None,
                      entrada: bytes | None = None, motivo: str = "recalculo") -> dict:
    """Guarda (o reemplaza) el resultado calculado y actualiza los indicadores.

    `resultado_json` debe ser la salida de `motor.calcular` ya pasada por
    `exactitud.a_json` (importes como cadena decimal).
    """
    empresa = resultado_json.get("empresa") or {}
    desde = parse_fecha(empresa.get("periodo_desde"))
    hasta = parse_fecha(empresa.get("periodo_hasta"))
    if not desde or not hasta:
        raise ErrorPeriodo("El resultado no trae el periodo de la empresa; no se puede guardar.")

    resumen = resultado_json.get("resumen") or {}
    ind = _indicadores(resumen)

    # ── Guarda 1: un cálculo vacío no reemplaza trabajo bueno (H19) ─────────
    # Se comprueba ANTES de tocar la base para no dejar periodos en blanco.
    if int(ind["cuentas"]) == 0 or int(resumen.get("movimientos") or 0) == 0:
        raise ResultadoVacio(
            "El archivo no aportó ninguna cuenta ni movimiento, así que no se guardó nada. "
            "Revise que haya marcado las hojas con la contabilidad en el paso de revisión."
        )

    periodo = asegurar(cliente_id, desde, hasta)

    # ── Guarda 2: un periodo cerrado no se pisa (H01) ────────────────────────
    # Un cierre es un documento firmado: para recalcular hay que reabrirlo a
    # propósito. Antes esto reemplazaba el periodo en silencio.
    if periodo["estado"] == "cerrado":
        raise PeriodoCerrado(
            f"El periodo {desde.isoformat()} a {hasta.isoformat()} está cerrado. "
            "Reábralo para recalcular: el cierre actual quedará guardado en el historial."
        )

    with conexion() as cn:
        # Antes de reemplazar: copia completa de lo que había (resultado,
        # movimientos y cierre) para poder volver a ella desde la ficha.
        _instantanea(cn, periodo["id"], motivo)
        cn.execute(update(TP).where(TP.c.id == periodo["id"]).values(
            **ind,
            estado="cerrado" if periodo["estado"] == "cerrado" else "calculado",
            calculado_en=datetime.now(timezone.utc),
        ))
        cn.execute(delete(TR).where(TR.c.periodo_id == periodo["id"]))
        cn.execute(delete(TE).where(TE.c.periodo_id == periodo["id"]))
        if entrada:
            from ..contabilidad.entrada import ligera

            cn.execute(insert(TE).values(periodo_id=periodo["id"], cliente_id=cliente_id,
                                         contenido=entrada, bytes=len(entrada)))
        cn.execute(insert(TR).values(
            periodo_id=periodo["id"], cliente_id=cliente_id,
            payload=ligera(resultado_json) if entrada else resultado_json, peticion=peticion or {},
        ))
        fila = cn.execute(select(TP).where(TP.c.id == periodo["id"])).one()
    _cache_resultado.pop(periodo["id"], None)
    return _a_dict(fila)


# Los últimos resultados rearmados, para no recalcular al cambiar de pestaña. Se vacía al guardar.
_cache_resultado: OrderedDict = OrderedDict()
_CACHE_MAX = 24


def entrada(periodo_id: str) -> dict | None:
    """La entrada guardada del periodo (descomprimida), o None si es de antes del rescate."""
    from ..contabilidad import entrada as E

    with lectura() as cn:
        contenido = cn.execute(select(TE.c.contenido).where(TE.c.periodo_id == periodo_id)).scalar()
    return E.descomprimir(contenido) if contenido else None


def resultado(periodo_id: str) -> dict | None:
    """El resultado COMPLETO del periodo. Si se guardó ligero, se rearma desde la entrada."""
    with lectura() as cn:
        fila = cn.execute(select(TR.c.payload, TR.c.peticion, TR.c.creado)
                          .where(TR.c.periodo_id == periodo_id)).first()
    if not fila:
        return None
    payload = fila.payload
    creado = fila.creado.isoformat()
    if isinstance(payload, dict) and payload.get("_derivados_fuera"):
        guardado = _cache_resultado.get(periodo_id)
        if guardado and guardado[0] == creado:
            _cache_resultado.move_to_end(periodo_id)
            payload = guardado[1]
        else:
            from ..contabilidad import entrada as E

            datos = entrada(periodo_id)
            if datos:
                completo = E.salida(E.recalcular(datos), datos.get("origenes") or {})
                payload = {**completo, **{k: v for k, v in payload.items() if k not in E.DERIVADOS}}
                payload.pop("_derivados_fuera", None)
                _cache_resultado[periodo_id] = (creado, payload)
                while len(_cache_resultado) > _CACHE_MAX:
                    _cache_resultado.popitem(last=False)
    return {"resultado": payload, "peticion": fila.peticion, "creado": creado}


# ── movimientos ─────────────────────────────────────────────────────────────
def guardar_movimientos(cliente_id: str, periodo_id: str, movs: Iterable[dict], lote: int = 1000) -> int:
    """Reemplaza los movimientos del periodo. Inserta por lotes para no reventar memoria."""
    with conexion() as cn:
        cn.execute(delete(TM).where(TM.c.periodo_id == periodo_id))
        buffer: list[dict] = []
        total = 0
        for m in movs or []:
            cuenta = str(m.get("cuenta") or "").strip()
            if not cuenta:
                continue
            buffer.append({
                "cliente_id": cliente_id, "periodo_id": periodo_id,
                "fecha": parse_fecha(m.get("fecha")),
                "cuenta": cuenta,
                "nombre_cuenta": str(m.get("nombre_cuenta") or "")[:300],
                "debito": D(m.get("debito")), "credito": D(m.get("credito")),
                "comprobante": str(m.get("comprobante") or "")[:80],
                "tipo": str(m.get("tipo") or "")[:40],
                "tercero_id": str(m.get("tercero_id") or "")[:40],
                "tercero_nombre": str(m.get("tercero_nombre") or "")[:200],
                "descripcion": str(m.get("descripcion") or "")[:500],
                "origen": str(m.get("origen") or "")[:200],
                "base_retencion": None if m.get("base_retencion") in (None, "") else D(m.get("base_retencion")),
            })
            if len(buffer) >= lote:
                cn.execute(insert(TM), buffer)
                total += len(buffer)
                buffer = []
        if buffer:
            cn.execute(insert(TM), buffer)
            total += len(buffer)
    return total


def movimientos(cliente_id: str, cuenta: str = "", desde: date | None = None,
                hasta: date | None = None, pagina: int = 1, por_pagina: int = 200,
                periodo_id: str = "") -> dict:
    """Libro diario consultable por cuenta y fecha, siempre paginado."""
    por_pagina = max(1, min(int(por_pagina or 200), 2000))
    pagina = max(1, int(pagina or 1))
    filtros = [TM.c.cliente_id == cliente_id]
    if cuenta:
        filtros.append(TM.c.cuenta.like(f"{cuenta}%"))
    if desde:
        filtros.append(TM.c.fecha >= desde)
    if hasta:
        filtros.append(TM.c.fecha <= hasta)
    if periodo_id:
        filtros.append(TM.c.periodo_id == periodo_id)
    donde = and_(*filtros)
    with lectura() as cn:
        total = int(cn.execute(select(func.count()).select_from(TM).where(donde)).scalar_one())
        # Las sumas se hacen en Python con Decimal: en SQLite el dinero es texto y
        # SUM() lo convierte a float (la regla de exactitud lo prohíbe).
        importes = cn.execute(select(TM.c.debito, TM.c.credito).where(donde)).all()
        sumas = (sum((D(a) for a, _ in importes), Decimal("0")), sum((D(b) for _, b in importes), Decimal("0")))
        filas = cn.execute(
            select(TM).where(donde)
            .order_by(TM.c.fecha.asc().nullslast(), TM.c.id.asc())
            .limit(por_pagina).offset((pagina - 1) * por_pagina)
        ).all()
    lineas = []
    for f in filas:
        d = dict(f._mapping)
        d["id"] = int(d["id"])
        d["cliente_id"] = str(d["cliente_id"])
        d["periodo_id"] = str(d["periodo_id"]) if d["periodo_id"] else None
        for k, v in list(d.items()):
            if isinstance(v, Decimal):
                d[k] = format(v, "f")
            elif isinstance(v, (date, datetime)):
                d[k] = v.isoformat()
        lineas.append(d)
    return {
        "total": total,
        "pagina": pagina,
        "por_pagina": por_pagina,
        "paginas": max(1, -(-total // por_pagina)),
        "suma_debito": _txt(sumas[0]) or "0",
        "suma_credito": _txt(sumas[1]) or "0",
        "movimientos": lineas,
    }


def poner_nota(periodo_id: str, nota: str) -> dict:
    """Nota de revisión del contador sobre el periodo. No toca ninguna cifra."""
    with conexion() as cn:
        if not cn.execute(select(TP.c.id).where(TP.c.id == periodo_id)).first():
            raise ErrorPeriodo("El periodo no existe.")
        cn.execute(update(TP).where(TP.c.id == periodo_id).values(nota=(nota or "").strip()))
        return _a_dict(cn.execute(select(TP).where(TP.c.id == periodo_id)).one())


def movimientos_de_periodo(periodo_id: str) -> list[dict]:
    """Todo el libro diario guardado de un periodo, en el orden en que se registró."""
    with lectura() as cn:
        filas = cn.execute(select(TM).where(TM.c.periodo_id == periodo_id).order_by(TM.c.id.asc())).all()
    return [dict(f._mapping) for f in filas]


# ── cierres ─────────────────────────────────────────────────────────────────
def cerrar(cliente_id: str, periodo_id: str, saldos_siguiente: list[dict]) -> dict:
    """Marca el periodo como cerrado y graba los saldos que abren el siguiente."""
    with conexion() as cn:
        periodo = cn.execute(select(TP).where(TP.c.id == periodo_id)).first()
        if not periodo:
            raise ErrorPeriodo("El periodo no existe.")
        saldos = [
            {"codigo": str(s.get("codigo") or ""), "nombre": str(s.get("nombre") or ""),
             "debito": _txt(s.get("debito")) or "0", "credito": _txt(s.get("credito")) or "0"}
            for s in (saldos_siguiente or []) if s.get("codigo")
        ]
        # Si ya había un cierre para este periodo, queda en el historial.
        if cn.execute(select(TC.c.id).where(TC.c.periodo_id == periodo_id)).first():
            _instantanea(cn, periodo_id, "cierre")
        cn.execute(delete(TC).where(and_(TC.c.cliente_id == cliente_id, TC.c.periodo_id == periodo_id)))
        cn.execute(insert(TC).values(
            cliente_id=cliente_id, periodo_id=periodo_id, fecha_corte=periodo.hasta,
            saldos=saldos, cuentas=len(saldos),
        ))
        cn.execute(update(TP).where(TP.c.id == periodo_id).values(
            estado="cerrado", cerrado_en=datetime.now(timezone.utc)
        ))
    return {
        "ok": True,
        "fecha_corte": periodo.hasta.isoformat(),
        "cuentas": len(saldos),
        "mensaje": (f"Cierre al {periodo.hasta.isoformat()} guardado con {len(saldos)} cuentas: "
                    "serán los saldos iniciales del periodo siguiente."),
    }


def reabrir(periodo_id: str) -> dict:
    with conexion() as cn:
        periodo = cn.execute(select(TP).where(TP.c.id == periodo_id)).first()
        if not periodo:
            raise ErrorPeriodo("El periodo no existe.")
        # El cierre no se pierde: queda como versión restaurable.
        _instantanea(cn, periodo_id, "reapertura")
        cn.execute(delete(TC).where(TC.c.periodo_id == periodo_id))
        cn.execute(update(TP).where(TP.c.id == periodo_id).values(estado="calculado", cerrado_en=None))
    return {"ok": True,
            "mensaje": (f"Periodo al {periodo.hasta.isoformat()} reabierto. El cierre quedó guardado "
                        "en el historial del periodo y se puede restaurar.")}


def listar_cierres(cliente_id: str) -> list[dict]:
    with lectura() as cn:
        filas = cn.execute(
            select(TC.c.id, TC.c.fecha_corte, TC.c.cuentas, TC.c.creado, TC.c.periodo_id)
            .where(TC.c.cliente_id == cliente_id)
            .order_by(TC.c.fecha_corte.desc(), TC.c.id.desc())
        ).all()
    return [
        {"id": int(f.id), "fecha_corte": f.fecha_corte.isoformat(), "cuentas": int(f.cuentas),
         "creado": f.creado.isoformat(timespec="seconds") if f.creado else "",
         "periodo_id": str(f.periodo_id) if f.periodo_id else None}
        for f in filas
    ]


def saldos_previos(cliente_id: str, antes_de: date) -> tuple[date, list[SaldoInicial]] | None:
    """Cierre más reciente anterior a `antes_de`, convertido a saldos iniciales."""
    with lectura() as cn:
        fila = cn.execute(
            select(TC.c.fecha_corte, TC.c.saldos)
            .where(and_(TC.c.cliente_id == cliente_id, TC.c.fecha_corte < antes_de))
            .order_by(TC.c.fecha_corte.desc(), TC.c.id.desc())
            .limit(1)
        ).first()
    if not fila:
        return None
    saldos = [
        SaldoInicial(
            s["codigo"], D(s.get("debito")), D(s.get("credito")),
            s.get("nombre", ""), f"Cierre guardado al {fila.fecha_corte.isoformat()}",
        )
        for s in (fila.saldos or [])
    ]
    return fila.fecha_corte, saldos


# ── histórico para gráficas y comparativos ──────────────────────────────────
def serie(cliente_id: str, limite: int = 24) -> list[dict]:
    """Últimos periodos en orden cronológico, listos para graficar."""
    with lectura() as cn:
        filas = cn.execute(
            select(TP.c.id, TP.c.desde, TP.c.hasta, TP.c.estado, TP.c.total_activo, TP.c.total_pasivo,
                   TP.c.total_patrimonio, TP.c.total_ingresos, TP.c.total_gastos, TP.c.utilidad,
                   TP.c.descuadre, TP.c.cuadra)
            .where(and_(TP.c.cliente_id == cliente_id, TP.c.estado != "borrador"))
            .order_by(TP.c.hasta.desc())
            .limit(max(2, min(int(limite or 24), 120)))
        ).all()
    datos = [
        {
            "id": str(f.id), "desde": f.desde.isoformat(), "hasta": f.hasta.isoformat(), "estado": f.estado,
            "total_activo": _txt(f.total_activo), "total_pasivo": _txt(f.total_pasivo),
            "total_patrimonio": _txt(f.total_patrimonio), "total_ingresos": _txt(f.total_ingresos),
            "total_gastos": _txt(f.total_gastos), "utilidad": _txt(f.utilidad),
            "descuadre": _txt(f.descuadre), "cuadra": bool(f.cuadra),
        }
        for f in filas
    ]
    return list(reversed(datos))


def resumen_global() -> dict:
    """Totales de toda la cartera para el tablero.

    Es UNA sola consulta con agregados condicionales. Antes eran cinco
    consultas separadas; contra Supabase, con ~190 ms de ida y vuelta cada una,
    solo esta función costaba más de un segundo.
    """
    with lectura() as cn:
        f = cn.execute(
            select(
                func.count(),
                func.sum(case((TP.c.estado == "cerrado", 1), else_=0)),
                func.sum(case((TP.c.estado != "cerrado", 1), else_=0)),
                func.sum(case((TP.c.cuadra.is_(False), 1), else_=0)),
                func.max(TP.c.hasta),
            ).select_from(TP)
        ).one()
    return {
        "periodos": int(f[0] or 0),
        "cerrados": int(f[1] or 0),
        "pendientes": int(f[2] or 0),
        "descuadrados": int(f[3] or 0),
        "ultimo_corte": f[4].isoformat() if f[4] else "",
    }


def series_de_varios(cliente_ids: list[str], limite_por_cliente: int = 36) -> dict[str, list[dict]]:
    """Histórico de VARIOS clientes en una sola consulta.

    El tablero necesita la serie de cada cliente activo. Pedirlas una por una
    eran 4 viajes a la base por cliente: contra Supabase en São Paulo eso son
    ~6 s con un solo cliente y minutos con cien. Aquí se trae todo de un golpe
    y se agrupa en Python.
    """
    if not cliente_ids:
        return {}
    salida: dict[str, list[dict]] = {cid: [] for cid in cliente_ids}
    with lectura() as cn:
        filas = cn.execute(
            select(TP.c.id, TP.c.cliente_id, TP.c.desde, TP.c.hasta, TP.c.estado,
                   TP.c.total_activo, TP.c.total_pasivo, TP.c.total_patrimonio,
                   TP.c.total_ingresos, TP.c.total_gastos, TP.c.utilidad,
                   TP.c.descuadre, TP.c.cuadra, TP.c.cuentas)
            .where(TP.c.cliente_id.in_(cliente_ids))
            .order_by(TP.c.cliente_id, TP.c.hasta.asc())
        ).all()
    for f in filas:
        cid = str(f.cliente_id)
        if cid not in salida:
            continue
        salida[cid].append({
            "id": str(f.id), "cliente_id": cid,
            "desde": f.desde.isoformat(), "hasta": f.hasta.isoformat(), "estado": f.estado,
            "total_activo": _txt(f.total_activo), "total_pasivo": _txt(f.total_pasivo),
            "total_patrimonio": _txt(f.total_patrimonio), "total_ingresos": _txt(f.total_ingresos),
            "total_gastos": _txt(f.total_gastos), "utilidad": _txt(f.utilidad),
            "descuadre": _txt(f.descuadre), "cuadra": bool(f.cuadra), "cuentas": int(f.cuentas or 0),
        })
    for cid in salida:
        salida[cid] = salida[cid][-max(2, limite_por_cliente):]
    return salida


def cierres_de_varios(cliente_ids: list[str]) -> dict[str, int]:
    """Cuántos cierres tiene cada cliente, en una sola consulta."""
    if not cliente_ids:
        return {}
    conteo = {cid: 0 for cid in cliente_ids}
    with lectura() as cn:
        filas = cn.execute(
            select(TC.c.cliente_id, func.count())
            .where(TC.c.cliente_id.in_(cliente_ids))
            .group_by(TC.c.cliente_id)
        ).all()
    for cid, n in filas:
        conteo[str(cid)] = int(n)
    return conteo
