"""Hoja de trabajo de 12 columnas, asiento de cierre y balance definitivo."""
from __future__ import annotations

from collections import defaultdict
from decimal import Decimal

from ..modelos import Movimiento, SaldoInicial
from ..utils.numeros import CERO
from .mayor import CuentaMayor, construir_mayor
from .puc import NOMBRE_CLASE
from .reportes import Constructor, col, reporte


def hoja_trabajo(pre: dict[str, CuentaMayor], ajustado: dict[str, CuentaMayor], ajustes: list[Movimiento], subtitulo: str) -> dict:
    cols = [col("codigo", "Código", ancho=10), col("cuenta", "Cuenta", ancho=34),
            col("bp_d", "Balance de prueba D", "dinero"), col("bp_c", "Balance de prueba C", "dinero"),
            col("aj_d", "Ajustes D", "dinero"), col("aj_c", "Ajustes C", "dinero"),
            col("ba_d", "Balance ajustado D", "dinero"), col("ba_c", "Balance ajustado C", "dinero"),
            col("er_d", "Estado de resultados D", "dinero"), col("er_c", "Estado de resultados C", "dinero"),
            col("bg_d", "Balance general D", "dinero"), col("bg_c", "Balance general C", "dinero")]
    aj = defaultdict(lambda: [CERO, CERO])
    for m in ajustes:
        aj[m.cuenta][0] += m.debito
        aj[m.cuenta][1] += m.credito
    k = Constructor()
    idx = []
    tot = defaultdict(lambda: CERO)
    for codigo in sorted(set(pre) | set(ajustado)):
        c_pre, c_aj = pre.get(codigo), ajustado.get(codigo)
        bp_d = c_pre.fin_d if c_pre else CERO
        bp_c = c_pre.fin_c if c_pre else CERO
        ba_d = c_aj.fin_d if c_aj else CERO
        ba_c = c_aj.fin_c if c_aj else CERO
        a_d, a_c = aj[codigo]
        if not any((bp_d, bp_c, a_d, a_c, ba_d, ba_c)):
            continue
        es_resultado = codigo[:1] in ("4", "5", "6", "7")
        v = {"codigo": codigo, "cuenta": (c_aj or c_pre).nombre, "bp_d": bp_d, "bp_c": bp_c, "aj_d": a_d, "aj_c": a_c,
             "ba_d": ba_d, "ba_c": ba_c,
             "er_d": ba_d if es_resultado else CERO, "er_c": ba_c if es_resultado else CERO,
             "bg_d": CERO if es_resultado else ba_d, "bg_c": CERO if es_resultado else ba_c}
        for x in v:
            if x not in ("codigo", "cuenta"):
                tot[x] += v[x]
        idx.append(k.agregar("linea", v, 1))
    claves = ["bp_d", "bp_c", "aj_d", "aj_c", "ba_d", "ba_c", "er_d", "er_c", "bg_d", "bg_c"]
    t_sumas = k.agregar("subtotal", {"cuenta": "SUMAS", **{x: tot[x] for x in claves}}, suma=idx)
    utilidad = tot["er_c"] - tot["er_d"]
    fila_res = {"cuenta": "UTILIDAD DEL EJERCICIO" if utilidad >= 0 else "PÉRDIDA DEL EJERCICIO"}
    if utilidad >= 0:
        fila_res.update({"er_d": utilidad, "bg_c": utilidad})
    else:
        fila_res.update({"er_c": -utilidad, "bg_d": -utilidad})
    t_res = k.agregar("linea", fila_res)
    finales = {x: tot[x] + fila_res.get(x, CERO) for x in claves}
    k.agregar("total", {"cuenta": "SUMAS IGUALES", **finales}, suma=[t_sumas, t_res])
    cuadra = all(finales[a] == finales[b] for a, b in (("bp_d", "bp_c"), ("aj_d", "aj_c"), ("ba_d", "ba_c"), ("er_d", "er_c"), ("bg_d", "bg_c")))
    verif = {"cuadra": cuadra, "utilidad": utilidad}
    return reporte("hoja_trabajo", "HOJA DE TRABAJO", subtitulo, cols, k.filas, horizontal=True, verificacion=verif)


def asiento_cierre(ajustado: dict[str, CuentaMayor]) -> tuple[list[Movimiento], Decimal]:
    """Cancela clases 4-7 contra 5905 y traslada el resultado a 3605 / 3610."""
    lineas: list[Movimiento] = []
    neto_resultado = CERO  # positivo = débito acumulado en 5905
    for c in ajustado.values():
        if c.clase not in ("4", "5", "6", "7") or c.codigo.startswith("5905") or c.neto == 0:
            continue
        n = c.neto
        lineas.append(Movimiento(c.codigo, debito=-n if n < 0 else CERO, credito=n if n > 0 else CERO,
                                 comprobante="CIERRE", tipo="cierre", nombre_cuenta=c.nombre, descripcion=f"Cierre {c.nombre}"))
        neto_resultado += n
    if not lineas:
        return [], CERO
    utilidad = -neto_resultado
    if neto_resultado:
        lineas.append(Movimiento("5905", debito=neto_resultado if neto_resultado > 0 else CERO,
                                 credito=-neto_resultado if neto_resultado < 0 else CERO, comprobante="CIERRE", tipo="cierre",
                                 descripcion="Ganancias y pérdidas"))
        # 5905 → 3605 / 3610
        lineas.append(Movimiento("5905", debito=-neto_resultado if neto_resultado < 0 else CERO,
                                 credito=neto_resultado if neto_resultado > 0 else CERO, comprobante="CIERRE", tipo="cierre",
                                 descripcion="Traslado del resultado del ejercicio"))
        if utilidad > 0:
            lineas.append(Movimiento("3605", credito=utilidad, comprobante="CIERRE", tipo="cierre", descripcion="Utilidad del ejercicio"))
        else:
            lineas.append(Movimiento("3610", debito=-utilidad, comprobante="CIERRE", tipo="cierre", descripcion="Pérdida del ejercicio"))
    return lineas, utilidad


def mayor_despues_cierre(ajustado: dict[str, CuentaMayor], cierre: list[Movimiento]) -> dict[str, CuentaMayor]:
    saldos = [SaldoInicial(c.codigo, c.fin_d, c.fin_c, c.nombre) for c in ajustado.values() if c.neto != 0]
    return construir_mayor(saldos, cierre)


def reporte_asiento(lineas: list[Movimiento], titulo: str, subtitulo: str, id_: str) -> dict:
    cols = [col("codigo", "Código", ancho=10), col("cuenta", "Cuenta", ancho=40), col("descripcion", "Descripción", ancho=40),
            col("debito", "Débito", "dinero"), col("credito", "Crédito", "dinero")]
    from .puc import puc
    k = Constructor()
    idx = [k.agregar("linea", {"codigo": m.cuenta, "cuenta": puc().nombre(m.cuenta, m.nombre_cuenta), "descripcion": m.descripcion,
                               "debito": m.debito or None, "credito": m.credito or None}, 1) for m in lineas]
    k.agregar("total", {"cuenta": "SUMAS IGUALES", "debito": sum((m.debito for m in lineas), CERO),
                        "credito": sum((m.credito for m in lineas), CERO)}, suma=idx)
    return reporte(id_, titulo, subtitulo, cols, k.filas)


def reporte_balance_definitivo(despues: dict[str, CuentaMayor], subtitulo: str) -> dict:
    cols = [col("codigo", "Código", ancho=10), col("cuenta", "Cuenta", ancho=48),
            col("debito", "Saldo débito", "dinero"), col("credito", "Saldo crédito", "dinero")]
    k = Constructor()
    subt = []
    por_clase = defaultdict(list)
    for c in despues.values():
        if c.neto != 0:
            por_clase[c.clase].append(c)
    for clase in sorted(por_clase):
        k.seccion(f"{clase} {NOMBRE_CLASE.get(clase, 'SIN CLASIFICAR').upper()}")
        idx = [k.agregar("linea", {"codigo": c.codigo, "cuenta": c.nombre, "debito": c.fin_d or None, "credito": c.fin_c or None}, 1)
               for c in por_clase[clase]]
        subt.append(k.agregar("subtotal", {"cuenta": f"Total clase {clase}",
                                           "debito": sum((c.fin_d for c in por_clase[clase]), CERO),
                                           "credito": sum((c.fin_c for c in por_clase[clase]), CERO)}, suma=idx))
    td = sum((c.fin_d for c in despues.values()), CERO)
    tc = sum((c.fin_c for c in despues.values()), CERO)
    k.agregar("total", {"cuenta": "SUMAS IGUALES", "debito": td, "credito": tc}, suma=subt)
    return reporte("balance_definitivo", "BALANCE DEFINITIVO (DESPUÉS DEL CIERRE)", subtitulo, cols, k.filas, firmas=True,
                   verificacion={"debito": td, "credito": tc, "cuadra": td == tc},
                   notas=["Estos saldos (clases 1, 2 y 3) son los saldos iniciales del siguiente periodo."])
