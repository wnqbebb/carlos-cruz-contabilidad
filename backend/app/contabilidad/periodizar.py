"""Partir un archivo que cubre varios meses en periodos, para procesarlos uno por uno.

POR QUÉ EXISTE
Un cliente pequeño entrega de una vez las ventas de enero a septiembre. Calcular
eso como un solo periodo da unos estados financieros de nueve meses que nadie
pidió: el contador lleva la contabilidad mes a mes (o bimestre a bimestre) y
cierra cada uno. Aquí se reparte el paquete por fechas; el cierre de cada
periodo abre el siguiente (`repositorio/periodos.saldos_previos`).

El inventario necesita un cuidado especial: el kardex de marzo empieza con lo
que quedó en febrero. Se recalcula el kardex de todo lo anterior y se abre el
periodo con un «inventario inicial» por producto, al costo promedio que traía.
"""
from __future__ import annotations

import calendar
import dataclasses
from datetime import date

from ..inventario import kardex as kx
from ..modelos import MovInventario, Paquete

MESES_POR_PERIODICIDAD = {"mensual": 1, "bimestral": 2, "trimestral": 3, "cuatrimestral": 4, "semestral": 6, "anual": 12}


def _fin_de_mes(a: int, m: int) -> date:
    return date(a, m, calendar.monthrange(a, m)[1])


def dividir(desde: date, hasta: date, meses: int) -> list[tuple[date, date]]:
    """Periodos consecutivos de `meses` meses, alineados al año calendario.

    Bimestral = ene-feb, mar-abr…; trimestral = ene-mar…; así coinciden con los
    periodos de IVA y con lo que el contador espera ver.
    """
    meses = max(1, int(meses))
    salida = []
    a, m = desde.year, desde.month
    # Alinear el inicio al bloque calendario que contiene `desde`.
    m = ((m - 1) // meses) * meses + 1
    while date(a, m, 1) <= hasta:
        fin_m = m + meses - 1
        fin_a = a + (fin_m - 1) // 12
        fin_m = (fin_m - 1) % 12 + 1
        ini = max(date(a, m, 1), desde.replace(day=1))
        salida.append((ini, _fin_de_mes(fin_a, fin_m)))
        m += meses
        a += (m - 1) // 12
        m = (m - 1) % 12 + 1
    return salida


def todo_con_fecha(paquete: Paquete) -> bool:
    """Solo se puede repartir por meses lo que dice en qué fecha ocurrió."""
    return bool(paquete.movimientos) and all(m.fecha for m in paquete.movimientos)


def recortar(paquete: Paquete, desde: date, hasta: date, primero: bool, metodo: str = "promedio") -> Paquete:
    """El paquete de un solo periodo.

    · movimientos y ajustes manuales: los de sus fechas;
    · saldos iniciales: solo en el primero (los demás los abre el cierre anterior);
    · inventario: lo anterior se resume en un inventario inicial por producto.
    """
    def dentro(f: date | None) -> bool:
        return f is not None and desde <= f <= hasta

    previos = [m for m in paquete.inventario_movs if m.fecha is None or m.fecha < desde]
    propios = [m for m in paquete.inventario_movs if m.fecha is not None and desde <= m.fecha <= hasta]
    inv: list[MovInventario] = []
    if primero:
        inv = [m for m in paquete.inventario_movs if m.fecha is None] + propios
    else:
        productos, _ = kx.calcular(previos, metodo)
        for p in productos.values():
            if p.saldo_cant > 0:
                inv.append(MovInventario(p.codigo, "inventario_inicial", p.saldo_cant, None, "SALDO ANTERIOR",
                                         p.descripcion, p.laboratorio, costo_unitario=p.saldo_total / p.saldo_cant,
                                         origen=f"Saldo del kardex al {desde.isoformat()}"))
        inv += propios
    ultimo_fisico = [c for c in paquete.inventario_fisico if dentro(c.fecha)]
    return dataclasses.replace(
        paquete,
        saldos_iniciales=list(paquete.saldos_iniciales) if primero else [],
        movimientos=[m for m in paquete.movimientos if dentro(m.fecha)],
        ajustes_manuales=[m for m in paquete.ajustes_manuales if dentro(m.fecha)],
        inventario_movs=inv,
        inventario_fisico=ultimo_fisico,
        alertas=[],
        titulos=[],
    )
