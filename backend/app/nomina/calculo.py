"""Liquidación de nómina con bases diferenciadas (seguridad social, prestaciones, vacaciones)."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from ..modelos import Empleado
from ..utils.numeros import CERO, UNO, redondear
from . import parametros

TREINTA = Decimal("30")
CINCO = Decimal("5")


@dataclass
class Liquidacion:
    empleado: Empleado
    año: int
    basico: Decimal = CERO
    aux: Decimal = CERO
    extras: Decimal = CERO
    comisiones: Decimal = CERO
    devengado: Decimal = CERO
    ibc: Decimal = CERO
    salud_emp: Decimal = CERO
    pension_emp: Decimal = CERO
    fsp: Decimal = CERO
    descuentos: Decimal = CERO
    neto: Decimal = CERO
    cesantias: Decimal = CERO
    intereses: Decimal = CERO
    prima: Decimal = CERO
    vacaciones: Decimal = CERO
    salud_empr: Decimal = CERO
    pension_empr: Decimal = CERO
    arl: Decimal = CERO
    caja: Decimal = CERO
    sena: Decimal = CERO
    icbf: Decimal = CERO
    horas_mes: Decimal = CERO
    valor_hora_legal: Decimal = CERO
    exonerado: bool = False
    notas: list[str] = field(default_factory=list)

    @property
    def total_prestaciones(self) -> Decimal:
        return self.cesantias + self.intereses + self.prima + self.vacaciones

    @property
    def total_aportes_empresa(self) -> Decimal:
        return self.salud_empr + self.pension_empr + self.arl + self.caja + self.sena + self.icbf

    @property
    def costo_total(self) -> Decimal:
        return self.devengado + self.total_prestaciones + self.total_aportes_empresa


def _r(v: Decimal) -> Decimal:
    return redondear(v, 2)


def liquidar(e: Empleado, año: int, exonerado: bool = True, fecha_ref: date | None = None) -> Liquidacion:
    p = parametros.obtener(año)
    fecha_ref = fecha_ref or date(año, e.mes or 1, 1)
    smmlv = p["smmlv"]
    liq = Liquidacion(e, año)
    liq.horas_mes = Decimal(parametros.horas_semana(p, fecha_ref)) * CINCO
    liq.valor_hora_legal = _r(smmlv / liq.horas_mes)

    if e.salario_basico is not None and e.salario_basico > 0:
        liq.basico = _r(e.salario_basico * e.dias / TREINTA)
        mensual = e.salario_basico
        proporcion = min(e.dias / TREINTA, UNO)
        if e.salario_basico < smmlv and e.dias >= TREINTA:
            liq.notas.append(f"Salario mensual inferior al SMMLV {año} ({smmlv:,.0f}).".replace(",", "."))
    elif e.valor_hora and e.horas:
        liq.basico = _r(e.valor_hora * e.horas)
        mensual = e.valor_hora * liq.horas_mes
        proporcion = min(e.horas / liq.horas_mes, UNO)
        if e.valor_hora < liq.valor_hora_legal:
            liq.notas.append(
                f"Valor hora {e.valor_hora:,.0f} inferior al mínimo legal {liq.valor_hora_legal:,.2f} "
                f"(SMMLV / {liq.horas_mes} h).".replace(",", "."))
    else:
        mensual, proporcion = CERO, CERO
        liq.notas.append("Sin salario ni horas: no se liquida.")

    tope_aux = p["tope_aux_transporte_smmlv"] * smmlv
    if e.aux_transporte == "si" or (e.aux_transporte == "auto" and 0 < mensual <= tope_aux):
        liq.aux = _r(p["aux_transporte"] * proporcion)

    liq.extras, liq.comisiones = e.horas_extra, e.comisiones
    liq.ibc = liq.basico + liq.extras + liq.comisiones
    liq.devengado = liq.ibc + liq.aux

    liq.salud_emp = _r(liq.ibc * p["salud_empleado"])
    liq.pension_emp = _r(liq.ibc * p["pension_empleado"])
    tasa_fsp = CERO
    for t in p["fsp_tramos"]:
        if liq.ibc >= t["desde_smmlv"] * smmlv:
            tasa_fsp = t["tasa"]
    liq.fsp = _r(liq.ibc * tasa_fsp)
    liq.descuentos = liq.salud_emp + liq.pension_emp + liq.fsp
    liq.neto = liq.devengado - liq.descuentos

    base_prest = liq.ibc + liq.aux
    liq.cesantias = _r(base_prest * p["cesantias"])
    liq.intereses = _r(base_prest * p["intereses_cesantias_mensual"])
    liq.prima = _r(base_prest * p["prima"])
    liq.vacaciones = _r((liq.basico + liq.comisiones) * p["vacaciones"])

    liq.pension_empr = _r(liq.ibc * p["pension_empleador"])
    liq.arl = _r(liq.ibc * p["arl"].get(e.clase_riesgo, p["arl"][1]))
    liq.caja = _r(liq.ibc * p["caja"])
    liq.exonerado = exonerado and liq.ibc < p["tope_exoneracion_smmlv"] * smmlv
    if not liq.exonerado:
        liq.salud_empr = _r(liq.ibc * p["salud_empleador"])
        liq.sena = _r(liq.ibc * p["sena"])
        liq.icbf = _r(liq.ibc * p["icbf"])
    return liq
