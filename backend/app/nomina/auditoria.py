"""Compara la nómina calculada por el cliente en su Excel contra la liquidación legal correcta."""
from __future__ import annotations

import re
from decimal import Decimal

from ..utils.numeros import CERO, normalizar
from .calculo import Liquidacion

TOLERANCIA = Decimal("1")
RE_QUEMADO = re.compile(r"[+\-]\s*\d{4,}(?![\d.]*%)")

EXPLICACION = {
    "E9": "Cesantías legales = 8,33 % de (salario + auxilio de transporte); intereses = 1 % mensual de esa base (12 % anual).",
    "E10": "El auxilio de transporte no es base de seguridad social: salud y pensión del empleado = 4 % del salario sin auxilio.",
    "E11": "La fórmula suma un valor fijo digitado en lugar de referenciar celdas.",
    "E12": "Los aportes del empleador se calculan sobre el salario (IBC) sin auxilio de transporte; la fórmula da 0.",
    "E15": "El valor hora se calculó incluyendo el auxilio de transporte; debe ser salario / horas mensuales.",
    "E16": "Los parafiscales se liquidan sobre el salario sin auxilio de transporte (y SENA/ICBF quedan exonerados si aplica el art. 114-1 E.T.).",
}

# concepto del bloque de apropiaciones → (atributo de la liquidación, código de error por defecto)
CONCEPTOS = {
    "cesantias": ("cesantias", "E9"),
    "intereses": ("intereses", "E9"),
    "prima": ("prima", "E9"),
    "vacaciones": ("vacaciones", "E9"),
    "caja": ("caja", "E16"),
    "sena": ("sena", "E16"),
    "icbf": ("icbf", "E16"),
    "arl": ("arl", "E12"),
    "salud_empr": ("salud_empr", "E12"),
    "pension_empr": ("pension_empr", "E12"),
}


def concepto_apropiacion(etiqueta: str) -> str | None:
    t = normalizar(etiqueta)
    if not t or t.startswith("TOTAL"):
        return None
    if t.startswith("I ") or "INTERES" in t:
        return "intereses"
    if "CESANT" in t:
        return "cesantias"
    for clave, concepto in (("PRIMA", "prima"), ("VACACION", "vacaciones"), ("CAJA", "caja"), ("SENA", "sena"),
                            ("ICBF", "icbf"), ("ICEBF", "icbf"), ("ARL", "arl"), ("SALUD", "salud_empr"),
                            ("PENSION", "pension_empr")):
        if clave in t:
            return concepto
    return None


def auditar(hoja: str, filas_cliente: list[dict], liqs: list[Liquidacion], apropiaciones: dict[str, dict],
            formulas: dict[str, str]) -> list[dict]:
    """filas_cliente: [{nombre, celda_fila, salud, pension, neto, valor_hora, devengado}]
    apropiaciones: {concepto: {valor, formula, celda}}; formulas: {celda: formula} de toda la hoja."""
    hallazgos: list[dict] = []

    def agregar(codigo, concepto, archivo, correcto, celda="", extra=""):
        if archivo is None:
            return
        if abs(Decimal(archivo) - correcto) <= TOLERANCIA:
            return
        hallazgos.append({
            "hoja": hoja, "codigo": codigo, "concepto": concepto, "celda": celda,
            "archivo": Decimal(archivo), "correcto": correcto, "diferencia": Decimal(archivo) - correcto,
            "explicacion": (EXPLICACION.get(codigo, "") + (" " + extra if extra else "")).strip(),
        })

    for fc, liq in zip(filas_cliente, liqs):
        nombre = liq.empleado.nombre
        agregar("E10", f"Salud empleado — {nombre}", fc.get("salud"), liq.salud_emp, fc.get("celda_salud", ""))
        agregar("E10", f"Pensión empleado — {nombre}", fc.get("pension"), liq.pension_emp + liq.fsp, fc.get("celda_pension", ""))
        err_ss = (fc.get("salud") is not None and abs(fc["salud"] - liq.salud_emp) > TOLERANCIA)
        agregar("E10" if err_ss else "AUX", f"Neto pagado — {nombre}", fc.get("neto"), liq.neto, fc.get("celda_neto", ""),
                "" if err_ss else "La diferencia proviene del auxilio de transporte no liquidado.")
        if fc.get("aux_archivo") is not None and liq.aux and abs(fc["aux_archivo"] - liq.aux) > TOLERANCIA:
            hallazgos.append({
                "hoja": hoja, "codigo": "AUX", "concepto": f"Auxilio de transporte — {nombre}", "celda": "",
                "archivo": fc["aux_archivo"], "correcto": liq.aux, "diferencia": fc["aux_archivo"] - liq.aux,
                "explicacion": "Trabajador con salario ≤ 2 SMMLV: tiene derecho a auxilio de transporte (proporcional al tiempo laborado).",
            })
        vh, salario = fc.get("valor_hora"), liq.empleado.salario_basico
        if vh and salario and liq.aux and abs(vh - (salario + liq.aux) / 240) < abs(vh - salario / 240):
            correcto = (salario / liq.horas_mes).quantize(Decimal("0.01"))
            hallazgos.append({
                "hoja": hoja, "codigo": "E15", "concepto": f"Valor hora — {nombre}", "celda": fc.get("celda_vh", ""),
                "archivo": vh, "correcto": correcto, "diferencia": vh - correcto,
                "explicacion": EXPLICACION["E15"] + f" Horas mensuales según la jornada legal vigente: {liq.horas_mes}.",
            })

    for concepto, dato in apropiaciones.items():
        if concepto not in CONCEPTOS:
            continue
        attr, codigo = CONCEPTOS[concepto]
        correcto = sum((getattr(l, attr) for l in liqs), CERO)
        formula = dato.get("formula") or ""
        cod = "E11" if RE_QUEMADO.search(formula) else codigo
        if cod == codigo and Decimal(dato["valor"]) == 0 and correcto > 0:
            cod = "E12"
        extra = f"Fórmula del archivo: {formula}" if formula else ""
        if concepto in ("sena", "icbf", "salud_empr") and correcto == 0:
            extra = ("Con la exoneración del art. 114-1 E.T. activa este aporte es 0. " + extra).strip()
        agregar(cod, _NOMBRE_CONCEPTO[concepto], dato["valor"], correcto, dato.get("celda", ""), extra)

    reportadas = {x["celda"] for x in hallazgos}
    for celda, formula in formulas.items():
        if celda not in reportadas and RE_QUEMADO.search(formula):
            hallazgos.append({
                "hoja": hoja, "codigo": "E11", "concepto": "Valor fijo dentro de una fórmula", "celda": celda,
                "archivo": None, "correcto": None, "diferencia": None,
                "explicacion": f"{EXPLICACION['E11']} Fórmula: {formula}",
            })
    return hallazgos


_NOMBRE_CONCEPTO = {
    "cesantias": "Provisión cesantías", "intereses": "Provisión intereses sobre cesantías", "prima": "Provisión prima",
    "vacaciones": "Provisión vacaciones", "caja": "Caja de compensación 4 %", "sena": "SENA 2 %", "icbf": "ICBF 3 %",
    "arl": "ARL empleador", "salud_empr": "Salud empleador 8,5 %", "pension_empr": "Pensión empleador 12 %",
}
