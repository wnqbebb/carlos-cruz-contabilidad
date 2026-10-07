"""Asientos de ajuste propuestos para pasar del balance de prueba al balance definitivo."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from ..modelos import ActivoFijo, Movimiento
from ..utils.numeros import CERO, pesos, redondear
from .mayor import CuentaMayor
from .puc import puc

DEPRECIACION = {  # cuenta PPE → (gasto, depreciación acumulada)
    "1516": ("516005", "159205"), "1520": ("516010", "159210"), "1524": ("516015", "159215"),
    "1528": ("516020", "159220"), "1532": ("516025", "159225"), "1540": ("516035", "159235"),
}


@dataclass
class Ajuste:
    id: str
    titulo: str
    tipo: str  # automatico | sugerido | manual
    explicacion: str
    lineas: list[Movimiento] = field(default_factory=list)
    aceptado_defecto: bool = True
    aceptado: bool = True

    @property
    def cuadra(self) -> bool:
        return sum((m.debito for m in self.lineas), CERO) == sum((m.credito for m in self.lineas), CERO)


def mov(cuenta: str, debito: Decimal = CERO, credito: Decimal = CERO, comprobante: str = "AJ", descripcion: str = "") -> Movimiento:
    return Movimiento(cuenta=cuenta, debito=redondear(debito, 2), credito=redondear(credito, 2), comprobante=comprobante,
                      tipo="ajuste", descripcion=descripcion, origen="Ajuste propuesto")


def saldo_prefijo(mayor: dict[str, CuentaMayor], prefijo: str) -> Decimal:
    return sum((c.neto for c in mayor.values() if c.codigo.startswith(prefijo)), CERO)


def cuenta_inventario(mayor: dict[str, CuentaMayor]) -> str:
    usadas = [c.codigo for c in mayor.values() if c.codigo.startswith("1435")]
    return usadas[0] if usadas else "1435"


def ajuste_costo_ventas(mayor: dict[str, CuentaMayor], costo_kardex: Decimal) -> Ajuste | None:
    costo_libros = saldo_prefijo(mayor, "6135")
    dif = costo_kardex - costo_libros
    if dif == 0:
        return None
    inv = cuenta_inventario(mayor)
    lineas = [mov("6135", debito=dif, comprobante="AJ-INV", descripcion="Costo de ventas según kardex"),
              mov(inv, credito=dif, comprobante="AJ-INV", descripcion="Salida de inventario vendido")] if dif > 0 else \
             [mov(inv, debito=-dif, comprobante="AJ-INV", descripcion="Reversión costo de ventas"),
              mov("6135", credito=-dif, comprobante="AJ-INV", descripcion="Costo de ventas según kardex")]
    return Ajuste("inventario_costo", "Costo de ventas desde el kardex", "automatico",
                  f"El kardex calcula un costo de ventas de {pesos(costo_kardex)}; en libros hay {pesos(costo_libros)}. "
                  f"Se registra la diferencia de {pesos(dif)} contra el inventario (1435).", lineas)


def ajuste_fisico(mayor: dict[str, CuentaMayor], diferencias: list[dict]) -> Ajuste | None:
    faltante = -sum((d["valor"] for d in diferencias if d["valor"] < 0), CERO)
    sobrante = sum((d["valor"] for d in diferencias if d["valor"] > 0), CERO)
    if not faltante and not sobrante:
        return None
    inv = cuenta_inventario(mayor)
    lineas = []
    if faltante:
        lineas += [mov("519595", debito=faltante, comprobante="AJ-FIS", descripcion="Faltantes de inventario (conteo físico)"),
                   mov(inv, credito=faltante, comprobante="AJ-FIS", descripcion="Faltantes de inventario")]
    if sobrante:
        lineas += [mov(inv, debito=sobrante, comprobante="AJ-FIS", descripcion="Sobrantes de inventario"),
                   mov("429595", credito=sobrante, comprobante="AJ-FIS", descripcion="Sobrantes de inventario (conteo físico)")]
    return Ajuste("inventario_fisico", "Diferencias del conteo físico", "automatico",
                  f"Faltantes valorizados {pesos(faltante)} y sobrantes {pesos(sobrante)} al costo promedio del kardex.", lineas)


def ajuste_conciliacion_inventario(saldo_libros_ajustado: Decimal, saldo_kardex: Decimal, inv: str) -> Ajuste | None:
    dif = saldo_kardex - saldo_libros_ajustado
    if dif == 0:
        return None
    lineas = [mov(inv, debito=dif, comprobante="AJ-CONC", descripcion="Ajuste a saldo de kardex"),
              mov("6135", credito=dif, comprobante="AJ-CONC", descripcion="Ajuste a saldo de kardex")] if dif > 0 else \
             [mov("6135", debito=-dif, comprobante="AJ-CONC", descripcion="Ajuste a saldo de kardex"),
              mov(inv, credito=-dif, comprobante="AJ-CONC", descripcion="Ajuste a saldo de kardex")]
    return Ajuste("inventario_conciliacion", "Igualar la cuenta 1435 al saldo del kardex", "sugerido",
                  f"Después del costo de ventas la cuenta 1435 queda en {pesos(saldo_libros_ajustado)} y el kardex en "
                  f"{pesos(saldo_kardex)} (diferencia {pesos(dif)}). Revise primero si hay compras sin registrar en el diario; "
                  f"este ajuste lleva la diferencia al costo de ventas.", lineas, aceptado_defecto=False)


def _meses_entre(a: tuple[int, int], b: tuple[int, int]) -> int:
    return (b[0] - a[0]) * 12 + (b[1] - a[1])


def ajuste_depreciacion(activos: list[ActivoFijo], desde: date, hasta: date) -> tuple[Ajuste | None, list[dict]]:
    detalle, lineas = [], []
    for af in activos:
        if af.cuenta.startswith("1504") or af.vida_util_meses <= 0 or not af.fecha_compra:
            continue
        mensual = (af.costo - af.valor_residual) / Decimal(af.vida_util_meses)
        # se deprecia desde el mes siguiente a la compra (supuesto S-29)
        m_sig = af.fecha_compra.month % 12 + 1
        inicio = (af.fecha_compra.year + (1 if af.fecha_compra.month == 12 else 0), m_sig)
        d, h = (desde.year, desde.month), (hasta.year, hasta.month)
        previos = max(0, _meses_entre(inicio, d))
        arranque = max(inicio, d)
        meses = _meses_entre(arranque, h) + 1 if arranque <= h else 0
        meses = min(meses, max(af.vida_util_meses - previos, 0))
        valor = redondear(mensual * meses, 2)
        gasto, acum = DEPRECIACION.get(af.cuenta[:4], ("5160", "1592"))
        detalle.append({"descripcion": af.descripcion, "cuenta": af.cuenta, "costo": af.costo, "vida_util_meses": af.vida_util_meses,
                        "mensual": redondear(mensual, 2), "meses_periodo": meses, "depreciacion_periodo": valor,
                        "acumulada_previa": redondear(mensual * min(previos, af.vida_util_meses), 2)})
        if valor:
            lineas += [mov(gasto, debito=valor, comprobante="AJ-DEP", descripcion=f"Depreciación {af.descripcion}"),
                       mov(acum, credito=valor, comprobante="AJ-DEP", descripcion=f"Depreciación {af.descripcion}")]
    if not lineas:
        return None, detalle
    total = sum((m.debito for m in lineas), CERO)
    return Ajuste("depreciacion", "Depreciación del periodo (línea recta)", "automatico",
                  f"Depreciación de {len(detalle)} activo(s) por {pesos(total)}: (costo − residual) / vida útil × meses del periodo.",
                  lineas), detalle


def ajuste_nomina(lineas: list[Movimiento], id_: str, titulo: str, explicacion: str, defecto: bool) -> Ajuste | None:
    if not lineas:
        return None
    return Ajuste(id_, titulo, "automatico", explicacion, lineas, aceptado_defecto=defecto)


def ajuste_renta(utilidad_antes: Decimal, tarifa: Decimal) -> Ajuste | None:
    if utilidad_antes <= 0:
        return None
    valor = redondear(utilidad_antes * tarifa, 0)
    return Ajuste("renta", f"Impuesto de renta estimado ({tarifa * 100:.0f} %)", "automatico",
                  f"Provisión sobre la utilidad contable antes de impuestos de {pesos(utilidad_antes)}. Es una estimación: "
                  f"la renta líquida gravable puede diferir por partidas no deducibles.",
                  [mov("540505", debito=valor, comprobante="AJ-RENTA", descripcion="Provisión impuesto de renta"),
                   mov("240405", credito=valor, comprobante="AJ-RENTA", descripcion="Impuesto de renta por pagar")])


def reclasificacion(id_: str, titulo: str, explicacion: str, debito_cta: str, credito_cta: str, valor: Decimal) -> Ajuste:
    return Ajuste(id_, titulo, "sugerido", explicacion,
                  [mov(debito_cta, debito=valor, comprobante="AJ-RECL", descripcion=titulo),
                   mov(credito_cta, credito=valor, comprobante="AJ-RECL", descripcion=titulo)], aceptado_defecto=False)


def ajuste_manual(lineas: list[Movimiento]) -> list[Ajuste]:
    por_comp: dict[str, list[Movimiento]] = {}
    for m in lineas:
        por_comp.setdefault(m.comprobante or "AJ-MANUAL", []).append(m)
    return [Ajuste(f"manual_{i}", f"Ajuste manual {comp}", "manual",
                   f"Registrado por el usuario en la hoja AJUSTES ({len(ls)} líneas).", ls)
            for i, (comp, ls) in enumerate(por_comp.items(), 1)]


def nombre_cuenta(codigo: str) -> str:
    return puc().nombre(codigo)
