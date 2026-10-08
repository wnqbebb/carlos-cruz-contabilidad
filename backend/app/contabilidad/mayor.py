"""Libro mayor y balance de prueba."""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from decimal import Decimal

from ..modelos import Movimiento, SaldoInicial
from ..utils.numeros import CERO
from .puc import NOMBRE_CLASE, puc
from .reportes import Constructor, col, reporte

SIN_MAPEAR = "SIN-MAPEAR"


@dataclass
class CuentaMayor:
    codigo: str
    nombre: str
    naturaleza: str
    ini_d: Decimal = CERO
    ini_c: Decimal = CERO
    mov_d: Decimal = CERO
    mov_c: Decimal = CERO
    movimientos: list[Movimiento] = field(default_factory=list)

    @property
    def neto_inicial(self) -> Decimal:
        return self.ini_d - self.ini_c

    @property
    def neto(self) -> Decimal:
        """Saldo final con signo: positivo = débito."""
        return self.ini_d - self.ini_c + self.mov_d - self.mov_c

    @property
    def fin_d(self) -> Decimal:
        return self.neto if self.neto > 0 else CERO

    @property
    def fin_c(self) -> Decimal:
        return -self.neto if self.neto < 0 else CERO

    @property
    def saldo(self) -> Decimal:
        """Saldo según naturaleza (positivo = normal)."""
        return self.neto if self.naturaleza == "D" else -self.neto

    @property
    def clase(self) -> str:
        return self.codigo[:1] if self.codigo[:1].isdigit() else "?"


def es_sin_mapear(codigo: str) -> bool:
    return codigo.startswith(SIN_MAPEAR)


def construir_mayor(saldos: list[SaldoInicial], movimientos: list[Movimiento]) -> dict[str, CuentaMayor]:
    p = puc()
    nombres: dict[str, str] = {}
    for s in saldos:
        nombres.setdefault(s.cuenta, s.nombre_cuenta)
    for m in movimientos:
        nombres.setdefault(m.cuenta, m.nombre_cuenta)

    cuentas: dict[str, CuentaMayor] = {}

    def obtener(codigo: str) -> CuentaMayor:
        if codigo not in cuentas:
            if es_sin_mapear(codigo):
                cuentas[codigo] = CuentaMayor(codigo, f"(sin mapear) {nombres.get(codigo, '')}", "D")
            else:
                cuentas[codigo] = CuentaMayor(codigo, p.nombre(codigo, nombres.get(codigo, "")), p.naturaleza(codigo))
        return cuentas[codigo]

    for s in saldos:
        c = obtener(s.cuenta)
        c.ini_d += s.debito
        c.ini_c += s.credito
    for m in movimientos:
        c = obtener(m.cuenta)
        c.mov_d += m.debito
        c.mov_c += m.credito
        c.movimientos.append(m)
    return dict(sorted(cuentas.items()))


def totales(mayor: dict[str, CuentaMayor]) -> dict[str, Decimal]:
    t = defaultdict(lambda: CERO)
    for c in mayor.values():
        t["ini_d"] += c.ini_d
        t["ini_c"] += c.ini_c
        t["mov_d"] += c.mov_d
        t["mov_c"] += c.mov_c
        t["fin_d"] += c.fin_d
        t["fin_c"] += c.fin_c
    return dict(t)


def reporte_balance_prueba(mayor: dict[str, CuentaMayor], titulo: str, subtitulo: str, id_: str = "balance_prueba") -> dict:
    columnas = [
        col("codigo", "Código", ancho=10), col("cuenta", "Cuenta", ancho=40),
        col("ini_d", "Saldo inicial débito", "dinero"), col("ini_c", "Saldo inicial crédito", "dinero"),
        col("mov_d", "Movimiento débito", "dinero"), col("mov_c", "Movimiento crédito", "dinero"),
        col("fin_d", "Saldo final débito", "dinero"), col("fin_c", "Saldo final crédito", "dinero"),
    ]
    claves = ["ini_d", "ini_c", "mov_d", "mov_c", "fin_d", "fin_c"]
    k = Constructor()
    subtotales: list[int] = []
    por_clase: dict[str, list[CuentaMayor]] = defaultdict(list)
    for c in mayor.values():
        if any(getattr(c, x) != 0 for x in claves):
            por_clase[c.clase].append(c)
    for clase in sorted(por_clase):
        k.seccion(f"{clase} {NOMBRE_CLASE.get(clase, 'SIN CLASIFICAR').upper()}", "cuenta")
        idx = [k.agregar("linea", {"codigo": c.codigo, "cuenta": c.nombre, **{x: getattr(c, x) for x in claves}}, 1)
               for c in por_clase[clase]]
        vals = {x: sum((getattr(c, x) for c in por_clase[clase]), CERO) for x in claves}
        subtotales.append(k.agregar("subtotal", {"cuenta": f"Total clase {clase}", **vals}, suma=idx))
    t = totales(mayor)
    k.agregar("total", {"cuenta": "SUMAS IGUALES", **t}, suma=subtotales)
    verif = {
        "saldos_iniciales": {"debito": t.get("ini_d", CERO), "credito": t.get("ini_c", CERO)},
        "movimientos": {"debito": t.get("mov_d", CERO), "credito": t.get("mov_c", CERO)},
        "saldos_finales": {"debito": t.get("fin_d", CERO), "credito": t.get("fin_c", CERO)},
        "cuadra": t.get("ini_d", CERO) == t.get("ini_c", CERO) and t.get("mov_d", CERO) == t.get("mov_c", CERO)
                  and t.get("fin_d", CERO) == t.get("fin_c", CERO),
    }
    return reporte(id_, titulo, subtitulo, columnas, k.filas, verificacion=verif, horizontal=True)


def reporte_libro_mayor(mayor: dict[str, CuentaMayor], subtitulo: str) -> dict:
    columnas = [
        col("codigo", "Código", ancho=10), col("fecha", "Fecha"), col("comprobante", "Comprobante"),
        col("descripcion", "Descripción / origen", ancho=45), col("debito", "Débito", "dinero"),
        col("credito", "Crédito", "dinero"), col("saldo", "Saldo", "dinero"),
    ]
    k = Constructor()
    for c in mayor.values():
        if not c.movimientos and c.neto_inicial == 0:
            continue
        k.seccion(f"{c.codigo} {c.nombre}", "descripcion")
        saldo = c.neto_inicial if c.naturaleza == "D" else -c.neto_inicial
        k.agregar("linea", {"descripcion": "Saldo inicial", "saldo": saldo}, 1)
        for m in c.movimientos:
            saldo += (m.debito - m.credito) if c.naturaleza == "D" else (m.credito - m.debito)
            k.agregar("linea", {
                "codigo": c.codigo, "fecha": m.fecha.isoformat() if m.fecha else "", "comprobante": m.comprobante,
                "descripcion": m.descripcion or m.origen, "debito": m.debito or None, "credito": m.credito or None,
                "saldo": saldo,
            }, 1)
        k.agregar("subtotal", {"descripcion": f"Total {c.nombre}", "debito": c.mov_d, "credito": c.mov_c, "saldo": c.saldo})
    return reporte("libro_mayor", "LIBRO MAYOR", subtitulo, columnas, k.filas, horizontal=True)
