"""Libros oficiales: libro diario y libro mayor y balances (H05, H06).

POR QUÉ EXISTE
El cliente pidió «el libro diario y el libro mayor» además de los balances. Hasta
la v2.1 el diario era una lista en pantalla y el mayor y balances no existía.
Aquí se arman con el formato de los libros de comercio, y salen igual en
pantalla, en Excel y en PDF porque los tres consumen la misma estructura
(`contabilidad/reportes.py`).

  · Libro diario: cada comprobante con sus líneas en orden cronológico, el total
    del comprobante (que debe cuadrar) y el total del periodo.
  · Libro mayor y balances: por cuenta, saldo anterior, movimientos y nuevo
    saldo (débito y crédito), con subtotales por grupo y por clase.
"""
from __future__ import annotations

from collections import OrderedDict, defaultdict
from datetime import date

from ..modelos import Movimiento
from ..utils.numeros import CERO
from .mayor import CuentaMayor
from .puc import NOMBRE_CLASE, puc
from .reportes import Constructor, col, reporte

# Clase de comprobante según el prefijo del número (los que arma la aplicación)
# o el tipo del movimiento (los que vienen del archivo).
TIPOS_COMPROBANTE = OrderedDict([
    ("VTA", "Factura de venta"), ("CMP", "Factura de compra"), ("GTO", "Comprobante de egreso (gasto)"),
    ("REC", "Recibo de caja"), ("PAG", "Comprobante de egreso"), ("RCL", "Nota de contabilidad (reclasificación)"),
    ("AJ", "Nota de contabilidad (ajuste)"), ("CT", "Movimiento de la cuenta T"), ("HT", "Movimiento de la hoja de trabajo"),
    ("BAL", "Saldo según balance recibido"), ("LD", "Comprobante del libro diario"), ("EF", "Estados financieros recibidos"),
])
TIPO_MOVIMIENTO = {"ajuste": "Nota de contabilidad (ajuste)", "venta": "Factura de venta", "compra": "Factura de compra",
                   "gasto": "Comprobante de egreso (gasto)", "recaudo": "Recibo de caja", "pago": "Comprobante de egreso",
                   "reclasificacion": "Nota de contabilidad (reclasificación)", "diario": "Comprobante de diario",
                   "balance": "Saldo según balance recibido"}


def tipo_comprobante(comprobante: str, tipo: str = "") -> str:
    if tipo in TIPO_MOVIMIENTO:
        return TIPO_MOVIMIENTO[tipo]
    pref = (comprobante or "").split("-")[0].split(" ")[0].upper()
    for clave, nombre in TIPOS_COMPROBANTE.items():
        if pref == clave or pref.startswith(clave):
            return nombre
    return "Comprobante"


def _orden(m: Movimiento, i: int) -> tuple:
    # Lo que no trae fecha (cuentas T, hojas de trabajo) va al final del periodo.
    return (m.fecha or date.max, i)


def reporte_libro_diario(movimientos: list[Movimiento], subtitulo: str, origenes: bool = True) -> dict:
    """Libro diario oficial: comprobantes en orden cronológico, cada uno cuadrado."""
    p = puc()
    # En el PDF, el comprobante y su tipo ya van en la cabecera de cada asiento y
    # el origen no cabe en una hoja carta: se dejan para la pantalla y el Excel.
    solo_pantalla = {"pdf": False}
    columnas = [
        col("fecha", "Fecha", ancho=11), {**col("comprobante", "Comprobante", ancho=13), **solo_pantalla},
        {**col("tipo", "Tipo", ancho=20), **solo_pantalla},
        col("codigo", "Código", ancho=10), col("cuenta", "Cuenta", ancho=30), col("tercero", "Tercero", ancho=22),
        col("descripcion", "Descripción", ancho=40), col("debito", "Débito", "dinero"), col("credito", "Crédito", "dinero"),
    ]
    if origenes:
        columnas.append({**col("origen", "Origen", ancho=30), **solo_pantalla})

    # Agrupar por comprobante conservando el orden cronológico de su primera línea.
    grupos: dict[str, list[tuple[int, Movimiento]]] = OrderedDict()
    for i, m in sorted(enumerate(movimientos), key=lambda t: _orden(t[1], t[0])):
        clave = m.comprobante or f"SIN NÚMERO {m.fecha.isoformat() if m.fecha else ''}".strip()
        grupos.setdefault(clave, []).append((i, m))

    k = Constructor()
    subtotales: list[int] = []
    descuadrados: list[dict] = []
    total_d = total_c = CERO
    for comp, lineas in grupos.items():
        primera = lineas[0][1]
        fecha = primera.fecha.isoformat() if primera.fecha else ""
        tipo = tipo_comprobante(comp, primera.tipo)
        k.seccion(f"{comp} · {tipo}" + (f" · {fecha}" if fecha else ""), "descripcion")
        idx = []
        for _, m in lineas:
            idx.append(k.agregar("linea", {
                "fecha": m.fecha.isoformat() if m.fecha else "", "comprobante": comp, "tipo": tipo,
                "codigo": m.cuenta, "cuenta": p.nombre(m.cuenta, m.nombre_cuenta),
                "tercero": m.tercero_nombre or m.tercero_id, "descripcion": m.descripcion,
                "debito": m.debito or None, "credito": m.credito or None, "origen": m.origen,
            }, 1))
        d = sum((m.debito for _, m in lineas), CERO)
        c = sum((m.credito for _, m in lineas), CERO)
        total_d, total_c = total_d + d, total_c + c
        cuadra = d == c
        if not cuadra:
            descuadrados.append({"comprobante": comp, "debito": d, "credito": c, "diferencia": d - c})
        subtotales.append(k.agregar("subtotal", {
            "descripcion": f"Total {comp}" + ("" if cuadra else f" — NO CUADRA (diferencia {d - c})"),
            "debito": d, "credito": c}, suma=idx))
    k.agregar("total", {"descripcion": "TOTAL DEL PERIODO", "debito": total_d, "credito": total_c}, suma=subtotales)
    if not grupos:
        k.agregar("nota", {"descripcion": "El periodo no tiene movimientos registrados."})
    verificacion = {
        "cuadra": total_d == total_c and not descuadrados,
        "comprobantes": len(grupos), "lineas": len(movimientos),
        "debito": total_d, "credito": total_c, "descuadrados": descuadrados,
    }
    return reporte("libro_diario", "LIBRO DIARIO", subtitulo, columnas, k.filas, horizontal=True,
                   verificacion=verificacion,
                   notas=["Cada comprobante debe cumplir partida doble: la suma de sus débitos es igual a la de sus créditos."])


def reporte_mayor_balances(mayor: dict[str, CuentaMayor], subtitulo: str) -> dict:
    """Libro mayor y balances: saldo anterior, movimientos y nuevo saldo, con subtotales por grupo y clase."""
    p = puc()
    claves = ["ini_d", "ini_c", "mov_d", "mov_c", "fin_d", "fin_c"]
    columnas = [
        col("codigo", "Código", ancho=10), col("cuenta", "Cuenta", ancho=38),
        col("ini_d", "Saldo anterior débito", "dinero"), col("ini_c", "Saldo anterior crédito", "dinero"),
        col("mov_d", "Movimientos débito", "dinero"), col("mov_c", "Movimientos crédito", "dinero"),
        col("fin_d", "Nuevo saldo débito", "dinero"), col("fin_c", "Nuevo saldo crédito", "dinero"),
    ]
    cuentas = [c for c in mayor.values() if any(getattr(c, x) != 0 for x in claves)]
    por_clase: dict[str, dict[str, list[CuentaMayor]]] = defaultdict(lambda: defaultdict(list))
    for c in cuentas:
        por_clase[c.clase][c.codigo[:2] if c.codigo[:1].isdigit() else "??"].append(c)

    k = Constructor()
    subtotales_clase: list[int] = []
    for clase in sorted(por_clase):
        k.seccion(f"{clase} {NOMBRE_CLASE.get(clase, 'SIN CLASIFICAR').upper()}", "cuenta")
        idx_grupos = []
        for grupo in sorted(por_clase[clase]):
            lista = por_clase[clase][grupo]
            k.seccion(f"{grupo} {p.nombre(grupo, '').upper() if grupo != '??' else 'SIN MAPEAR'}", "cuenta", 1)
            idx = [k.agregar("linea", {"codigo": c.codigo, "cuenta": c.nombre, **{x: getattr(c, x) for x in claves}}, 2)
                   for c in lista]
            vals = {x: sum((getattr(c, x) for c in lista), CERO) for x in claves}
            idx_grupos.append(k.agregar("subtotal", {"codigo": grupo, "cuenta": f"Total grupo {grupo}", **vals}, 1, suma=idx))
        vals = {x: sum((getattr(c, x) for g in por_clase[clase].values() for c in g), CERO) for x in claves}
        subtotales_clase.append(k.agregar("subtotal", {"codigo": clase, "cuenta": f"Total clase {clase}", **vals},
                                          suma=idx_grupos))
    tot = {x: sum((getattr(c, x) for c in cuentas), CERO) for x in claves}
    k.agregar("total", {"cuenta": "SUMAS IGUALES", **tot}, suma=subtotales_clase)
    if not cuentas:
        k.agregar("nota", {"cuenta": "No hay cuentas con saldo ni movimiento en el periodo."})
    cuadra = tot["ini_d"] == tot["ini_c"] and tot["mov_d"] == tot["mov_c"] and tot["fin_d"] == tot["fin_c"]
    return reporte("mayor_balances", "LIBRO MAYOR Y BALANCES", subtitulo, columnas, k.filas, horizontal=True,
                   verificacion={"cuadra": cuadra, "cuentas": len(cuentas)})


def mayor_balances_desde_balance(rep_balance: dict, subtitulo: str) -> dict:
    """Mayor y balances de un periodo guardado antes de que existiera el libro.

    El balance de prueba ajustado ya trae, por cuenta, saldo inicial,
    movimiento y saldo final: es la misma información, solo hay que agruparla.
    """
    from decimal import Decimal

    mayor: dict[str, CuentaMayor] = {}
    for f in rep_balance.get("filas") or []:
        v = f.get("valores") or {}
        if f.get("tipo") != "linea" or not v.get("codigo"):
            continue
        c = CuentaMayor(str(v["codigo"]), str(v.get("cuenta") or ""), puc().naturaleza(str(v["codigo"])))
        c.ini_d, c.ini_c = Decimal(str(v.get("ini_d") or 0)), Decimal(str(v.get("ini_c") or 0))
        c.mov_d, c.mov_c = Decimal(str(v.get("mov_d") or 0)), Decimal(str(v.get("mov_c") or 0))
        mayor[c.codigo] = c
    return reporte_mayor_balances(dict(sorted(mayor.items())), subtitulo)


def movimientos_desde_guardados(filas: list[dict]) -> list[Movimiento]:
    """Movimientos del libro diario guardado en la base, como objetos del motor."""
    from ..utils.numeros import D, parse_fecha

    return [Movimiento(cuenta=f.get("cuenta") or "", debito=D(f.get("debito")), credito=D(f.get("credito")),
                       fecha=parse_fecha(f.get("fecha")), comprobante=f.get("comprobante") or "", tipo=f.get("tipo") or "",
                       nombre_cuenta=f.get("nombre_cuenta") or "", tercero_id=f.get("tercero_id") or "",
                       tercero_nombre=f.get("tercero_nombre") or "", descripcion=f.get("descripcion") or "",
                       origen=f.get("origen") or "") for f in filas]
