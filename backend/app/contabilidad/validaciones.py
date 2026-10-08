"""Reglas de validación contable y societaria (mensajes en español)."""
from __future__ import annotations

from collections import defaultdict
from datetime import date
from decimal import Decimal

from rapidfuzz import fuzz

from ..modelos import Alerta, AporteSocio, Empleado, Empresa, Movimiento
from ..utils.numeros import CERO, años_en_texto, normalizar, pesos
from .mayor import CuentaMayor, es_sin_mapear, totales
from .puc import puc


def partida_doble(movs: list[Movimiento]) -> list[Alerta]:
    grupos: dict[str, list[Movimiento]] = defaultdict(list)
    for m in movs:
        grupos[m.comprobante or "(sin comprobante)"].append(m)
    alertas = []
    for comp, ls in grupos.items():
        d = sum((m.debito for m in ls), CERO)
        c = sum((m.credito for m in ls), CERO)
        if d != c:
            alertas.append(Alerta("PARTIDA-DOBLE", "error",
                                  f"El comprobante «{comp}» no cumple partida doble: débitos {pesos(d)} ≠ créditos {pesos(c)} "
                                  f"(diferencia {pesos(d - c)}).", origen=ls[0].origen))
    return alertas


def sumas_iguales(mayor: dict[str, CuentaMayor], etapa: str) -> list[Alerta]:
    t = totales(mayor)
    alertas = []
    for ini, fin, nombre in (("ini_d", "ini_c", "saldos iniciales"), ("mov_d", "mov_c", "movimientos"), ("fin_d", "fin_c", "saldos finales")):
        if t.get(ini, CERO) != t.get(fin, CERO):
            alertas.append(Alerta("SUMAS-IGUALES", "error",
                                  f"{etapa}: las sumas de {nombre} no son iguales — débito {pesos(t.get(ini, CERO))} vs crédito "
                                  f"{pesos(t.get(fin, CERO))} (diferencia {pesos(t.get(ini, CERO) - t.get(fin, CERO))})."))
    return alertas


def naturaleza(mayor: dict[str, CuentaMayor]) -> tuple[list[Alerta], list[tuple[str, Decimal]]]:
    alertas, contrarias = [], []
    for c in mayor.values():
        if es_sin_mapear(c.codigo) or c.saldo >= 0 or c.codigo.startswith("5905"):
            continue
        contrarias.append((c.codigo, -c.saldo))
        if c.codigo.startswith("11"):
            alertas.append(Alerta("DISPONIBLE-NEGATIVO", "error",
                                  f"{c.codigo} {c.nombre} queda con saldo negativo ({pesos(c.saldo)}): se pagó más de lo disponible "
                                  f"o falta registrar ingresos."))
        elif c.codigo.startswith("240805"):
            alertas.append(Alerta("E6", "advertencia",
                                  f"{c.codigo} {c.nombre} tiene saldo débito de {pesos(-c.saldo)}, contrario a su naturaleza. "
                                  f"Parece IVA pagado en compras: debe ir a 240810 IVA descontable (hay una reclasificación sugerida)."))
        else:
            lado = "débito" if c.naturaleza == "C" else "crédito"
            alertas.append(Alerta("E6", "advertencia",
                                  f"{c.codigo} {c.nombre} tiene saldo {lado} de {pesos(-c.saldo)}, contrario a su naturaleza."))
    return alertas, contrarias


def fuera_periodo(movs: list[Movimiento], desde: date, hasta: date) -> list[Alerta]:
    fuera = [m for m in movs if m.fecha and not (desde <= m.fecha <= hasta)]
    if not fuera:
        return []
    ejemplos = ", ".join(f"{m.fecha.isoformat()} ({m.comprobante})" for m in fuera[:5])
    return [Alerta("FUERA-PERIODO", "advertencia",
                   f"{len(fuera)} movimiento(s) con fecha fuera del periodo {desde.isoformat()} a {hasta.isoformat()}.",
                   detalle=f"Ejemplos: {ejemplos}", origen=fuera[0].origen)]


def sin_mapear(mayor: dict[str, CuentaMayor]) -> list[Alerta]:
    return [Alerta("E13", "error", f"Cuenta sin código PUC: «{c.nombre.replace('(sin mapear) ', '')}» — no entra en los estados financieros. "
                                   f"Asígnele un código en la vista previa.") for c in mayor.values() if es_sin_mapear(c.codigo)]


def ingreso_igual_aporte(movs: list[Movimiento], empresa: Empresa, aportes: list[AporteSocio]) -> list[Alerta]:
    candidatos = {m.credito for m in movs if m.cuenta.startswith("3105") and m.credito}
    candidatos |= {a.comprometido for a in aportes if a.comprometido}
    if empresa.accionistas and empresa.capital_suscrito:
        candidatos.add(empresa.capital_suscrito / len(empresa.accionistas))
    alertas = []
    for m in movs:
        if m.cuenta.startswith("4") and m.credito and m.credito in candidatos:
            alertas.append(Alerta("E3", "advertencia",
                                  f"Ingreso de {pesos(m.credito)} igual a un aporte de socio — verificar si es un aporte de capital "
                                  f"registrado como ingreso.", origen=m.origen))
    return alertas


def conciliacion_capital(mayor: dict[str, CuentaMayor], empresa: Empresa, aportes: list[AporteSocio]) -> list[Alerta]:
    capital_libros = sum((-c.neto for c in mayor.values() if c.codigo.startswith("31")), CERO)
    alertas = []
    if empresa.capital_suscrito and capital_libros != empresa.capital_suscrito:
        alertas.append(Alerta("E5", "advertencia",
                              f"Capital en libros (grupo 31) {pesos(capital_libros)} ≠ capital suscrito y pagado según estatutos "
                              f"{pesos(empresa.capital_suscrito)} (diferencia {pesos(capital_libros - empresa.capital_suscrito)}). "
                              f"Revise aportes registrados dos veces o capital no consignado."))
    if aportes:
        comprometido = sum((a.comprometido for a in aportes), CERO)
        pagado = sum((a.pagado for a in aportes), CERO)
        if comprometido and pagado < comprometido:
            alertas.append(Alerta("E18", "advertencia",
                                  f"El libro de aportes registra {pesos(pagado)} pagados de {pesos(comprometido)} comprometidos "
                                  f"(saldo por pagar {pesos(comprometido - pagado)}), pero los estatutos dicen capital pagado totalmente."))
        if comprometido and capital_libros and comprometido != capital_libros:
            alertas.append(Alerta("E5", "advertencia",
                                  f"Capital en libros (grupo 31) {pesos(capital_libros)} ≠ libro de aportes de socios "
                                  f"({pesos(comprometido)} comprometidos; diferencia {pesos(capital_libros - comprometido)}). "
                                  "Revise aportes registrados dos veces o capital no consignado."))
    return alertas


def gastos_personales(movs: list[Movimiento], banderas: dict[str, str]) -> tuple[list[Alerta], dict[str, Decimal]]:
    por_cuenta: dict[str, Decimal] = defaultdict(lambda: CERO)
    for m in movs:
        if banderas.get(normalizar(m.nombre_cuenta)) == "E14":
            por_cuenta[m.cuenta] += m.debito - m.credito
    alertas = [Alerta("E14", "advertencia",
                      f"«Gastos personales» por {pesos(v)} registrados como gasto de la empresa ({c}). No son deducibles ni propios "
                      f"de la actividad: deben llevarse a 1325 cuentas por cobrar a socios (reclasificación sugerida).")
               for c, v in por_cuenta.items() if v]
    return alertas, {c: v for c, v in por_cuenta.items() if v}


def honorarios_sin_retencion(movs: list[Movimiento]) -> list[Alerta]:
    por_comp: dict[str, list[Movimiento]] = defaultdict(list)
    for m in movs:
        if m.comprobante:
            por_comp[m.comprobante].append(m)
    alertas = []
    for comp, ls in por_comp.items():
        if any(m.cuenta.startswith("5110") and m.debito for m in ls) and not any(m.cuenta.startswith("2365") for m in ls):
            alertas.append(Alerta("RETENCION", "info",
                                  f"El comprobante «{comp}» registra honorarios sin retención en la fuente. La empresa es agente de "
                                  f"retención (responsabilidad 07): verifique si aplica.", origen=ls[0].origen))
    return alertas


def titulos_periodo(titulos: list[str], desde: date, hasta: date) -> list[Alerta]:
    alertas = []
    for t in titulos:
        años = años_en_texto(t)
        if años and not any(desde.year <= a <= hasta.year for a in años):
            alertas.append(Alerta("E19", "advertencia",
                                  f"El título «{t.strip()}» menciona {', '.join(map(str, años))}, pero el periodo es "
                                  f"{desde.isoformat()} a {hasta.isoformat()}: parece una plantilla reutilizada. Confirme el periodo real."))
    return alertas


# Norma que fija la causal de disolución por pérdidas, según el tipo de sociedad.
NORMA_DISOLUCION = {
    "SAS": ("Ley 1258 de 2008, art. 34 num. 7", "La asamblea puede enervarla dentro de los 18 meses siguientes a que "
               "reconozca su ocurrencia (art. 35)."),
    "SA": ("Código de Comercio, art. 457 num. 2", "Los administradores deben convocar a la asamblea; las medidas para "
             "restablecer el patrimonio se toman dentro de los 6 meses siguientes (art. 458)."),
    "LTDA": ("Código de Comercio, art. 370", ""),
}


def disolucion(total_patrimonio: Decimal, empresa: Empresa) -> list[Alerta]:
    if empresa.tipo_persona == "natural" or not empresa.capital_suscrito:
        return []
    if total_patrimonio < empresa.capital_suscrito * Decimal("0.5"):
        norma, plazo = NORMA_DISOLUCION.get(empresa.tipo_sociedad.upper().replace(" ", "").replace(".", ""),
                                            ("pérdidas que reducen el patrimonio neto por debajo del 50 % del capital", ""))
        return [Alerta("DISOLUCION", "error",
                       f"Causal de disolución ({norma}): el patrimonio neto {pesos(total_patrimonio)} es inferior "
                       f"al 50 % del capital suscrito ({pesos(empresa.capital_suscrito * Decimal('0.5'))}). "
                       f"{plazo} Confirme lo que dicen los estatutos de la sociedad.".replace("  ", " "))]
    return []


def rep_legal_en_nomina(empleados: list[Empleado], empresa: Empresa) -> list[Alerta]:
    alertas = []
    for e in empleados:
        if empresa.rep_legal and fuzz.token_set_ratio(normalizar(e.nombre), normalizar(empresa.rep_legal)) >= 90:
            alertas.append(Alerta("E17", "info",
                                  f"{e.nombre} es representante legal y figura en nómina: revise en los estatutos qué órgano aprueba "
                                  f"su remuneración y conserve el acta como soporte."))
    return alertas


def nombre(codigo: str) -> str:
    return puc().nombre(codigo)
