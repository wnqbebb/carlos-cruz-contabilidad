"""Asientos contables de nómina (causación, provisiones y aportes) y reportes."""
from __future__ import annotations

from decimal import Decimal

from ..contabilidad.reportes import Constructor, col, reporte
from ..modelos import Movimiento
from ..utils.numeros import CERO
from .calculo import Liquidacion

CUENTAS_PROVISION = {
    "25": {"cesantias": "2510", "intereses": "2515", "prima": "2520", "vacaciones": "2525"},
    "26": {"cesantias": "261005", "intereses": "261010", "prima": "261020", "vacaciones": "261015"},
}


def _suma(liqs: list[Liquidacion], attr: str) -> Decimal:
    return sum((getattr(l, attr) for l in liqs), CERO)


def _lineas(pares: list[tuple[str, str, Decimal, str]], comprobante: str, descripcion: str) -> list[Movimiento]:
    movs = []
    for cuenta, lado, valor, detalle in pares:
        if valor == 0:
            continue
        movs.append(Movimiento(
            cuenta=cuenta, debito=valor if lado == "D" else CERO, credito=valor if lado == "C" else CERO,
            comprobante=comprobante, tipo="nota", descripcion=f"{descripcion}: {detalle}", origen="Módulo de nómina",
        ))
    return movs


def asiento_causacion(liqs: list[Liquidacion]) -> list[Movimiento]:
    s = lambda a: _suma(liqs, a)
    return _lineas([
        ("510506", "D", s("basico"), "sueldos"),
        ("510515", "D", s("extras"), "horas extras y recargos"),
        ("510518", "D", s("comisiones"), "comisiones"),
        ("510527", "D", s("aux"), "auxilio de transporte"),
        ("237005", "C", s("salud_emp"), "salud empleado 4 %"),
        ("238030", "C", s("pension_emp") + s("fsp"), "pensión empleado 4 % y FSP"),
        ("2505", "C", s("neto"), "neto a pagar"),
    ], "NOM-CAUSACION", "Causación nómina")


def asiento_provisiones(liqs: list[Liquidacion], cuenta_provisiones: str = "25") -> list[Movimiento]:
    s = lambda a: _suma(liqs, a)
    cp = CUENTAS_PROVISION.get(cuenta_provisiones, CUENTAS_PROVISION["25"])
    return _lineas([
        ("510530", "D", s("cesantias"), "cesantías 8,33 %"),
        ("510533", "D", s("intereses"), "intereses sobre cesantías 1 %"),
        ("510536", "D", s("prima"), "prima de servicios 8,33 %"),
        ("510539", "D", s("vacaciones"), "vacaciones 4,17 %"),
        ("510569", "D", s("salud_empr"), "salud empleador 8,5 %"),
        ("510570", "D", s("pension_empr"), "pensión empleador 12 %"),
        ("510568", "D", s("arl"), "ARL"),
        ("510572", "D", s("caja"), "caja de compensación 4 %"),
        ("510575", "D", s("icbf"), "ICBF 3 %"),
        ("510578", "D", s("sena"), "SENA 2 %"),
        (cp["cesantias"], "C", s("cesantias"), "cesantías"),
        (cp["intereses"], "C", s("intereses"), "intereses sobre cesantías"),
        (cp["prima"], "C", s("prima"), "prima de servicios"),
        (cp["vacaciones"], "C", s("vacaciones"), "vacaciones"),
        ("237005", "C", s("salud_empr"), "salud empleador"),
        ("238030", "C", s("pension_empr"), "pensión empleador"),
        ("237006", "C", s("arl"), "ARL"),
        ("237010", "C", s("caja") + s("icbf") + s("sena"), "parafiscales"),
    ], "NOM-PROVISIONES", "Provisiones y aportes de nómina")


def reporte_nomina(liqs: list[Liquidacion], subtitulo: str) -> list[dict]:
    col_dev = [
        col("nombre", "Empleado", ancho=28), col("cargo", "Cargo"), col("basico", "Básico", "dinero"),
        col("aux", "Aux. transporte", "dinero"), col("otros", "Extras y comisiones", "dinero"),
        col("devengado", "Total devengado", "dinero"), col("salud_emp", "Salud 4 %", "dinero"),
        col("pension_emp", "Pensión 4 %", "dinero"), col("fsp", "FSP", "dinero"),
        col("descuentos", "Total descuentos", "dinero"), col("neto", "Neto a pagar", "dinero"),
    ]
    k = Constructor()
    idx = []
    for l in liqs:
        idx.append(k.agregar("linea", {
            "nombre": l.empleado.nombre, "cargo": l.empleado.cargo, "basico": l.basico, "aux": l.aux,
            "otros": l.extras + l.comisiones, "devengado": l.devengado, "salud_emp": l.salud_emp,
            "pension_emp": l.pension_emp, "fsp": l.fsp, "descuentos": l.descuentos, "neto": l.neto,
        }))
    claves = ["basico", "aux", "otros", "devengado", "salud_emp", "pension_emp", "fsp", "descuentos", "neto"]
    k.agregar("total", {"nombre": "TOTAL NÓMINA", **{c: sum((k.filas[i]["valores"][c] for i in idx), CERO) for c in claves}}, suma=idx)
    r1 = reporte("nomina_devengados", "NÓMINA — DEVENGADOS Y DEDUCCIONES", subtitulo, col_dev, k.filas, horizontal=True)

    col_ap = [
        col("nombre", "Empleado", ancho=28), col("cesantias", "Cesantías", "dinero"), col("intereses", "Int. cesantías", "dinero"),
        col("prima", "Prima", "dinero"), col("vacaciones", "Vacaciones", "dinero"), col("salud_empr", "Salud 8,5 %", "dinero"),
        col("pension_empr", "Pensión 12 %", "dinero"), col("arl", "ARL", "dinero"), col("caja", "Caja 4 %", "dinero"),
        col("sena", "SENA 2 %", "dinero"), col("icbf", "ICBF 3 %", "dinero"), col("total", "Total apropiaciones", "dinero"),
    ]
    k2 = Constructor()
    idx2 = []
    for l in liqs:
        idx2.append(k2.agregar("linea", {
            "nombre": l.empleado.nombre + (" (exonerado art. 114-1)" if l.exonerado else ""),
            "cesantias": l.cesantias, "intereses": l.intereses, "prima": l.prima, "vacaciones": l.vacaciones,
            "salud_empr": l.salud_empr, "pension_empr": l.pension_empr, "arl": l.arl, "caja": l.caja,
            "sena": l.sena, "icbf": l.icbf, "total": l.total_prestaciones + l.total_aportes_empresa,
        }))
    claves2 = [c["clave"] for c in col_ap[1:]]
    k2.agregar("total", {"nombre": "TOTAL APROPIACIONES", **{c: sum((k2.filas[i]["valores"][c] for i in idx2), CERO) for c in claves2}}, suma=idx2)
    notas = sorted({n for l in liqs for n in l.notas})
    r2 = reporte("nomina_apropiaciones", "NÓMINA — PRESTACIONES SOCIALES Y APORTES DEL EMPLEADOR", subtitulo, col_ap, k2.filas,
                 horizontal=True, notas=notas)
    return [r1, r2]
