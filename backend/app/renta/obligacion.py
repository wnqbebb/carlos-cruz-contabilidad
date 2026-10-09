"""¿Debe declarar? Vencimiento según el NIT y sanción estimada por extemporaneidad."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from . import parametros as P
from .calculo import CERO, R

NOMBRES = {
    "ingresos": "ingresos brutos",
    "patrimonio": "patrimonio bruto",
    "consumos_tc": "consumos con tarjeta de crédito",
    "compras": "compras y consumos",
    "consignaciones": "consignaciones, depósitos o inversiones",
}


def evaluar(topes: dict, anio: int) -> dict:
    """`topes`: ingresos, patrimonio, consumos_tc, compras, consignaciones (pesos) y responsable_iva (bool).

    Art. 592 y ss. E.T.: ingresos ≥ 1.400 UVT; patrimonio > 4.500 UVT; consumos con
    tarjeta, compras y consignaciones > 1.400 UVT; o haber sido responsable de IVA.
    """
    p = P.obtener(anio)["topes_obligacion"]
    uvt = P.uvt(anio)
    umbrales = {
        "ingresos": P.d(p["ingresos_brutos_uvt"]) * uvt,
        "patrimonio": P.d(p["patrimonio_bruto_uvt"]) * uvt,
        "consumos_tc": P.d(p["consumos_tarjeta_uvt"]) * uvt,
        "compras": P.d(p["compras_consumos_uvt"]) * uvt,
        "consignaciones": P.d(p["consignaciones_uvt"]) * uvt,
    }
    motivos = []
    for clave, umbral in umbrales.items():
        valor = Decimal(str(topes.get(clave) or 0))
        supera = valor >= umbral if clave == "ingresos" else valor > umbral
        motivos.append({"tope": clave, "nombre": NOMBRES[clave], "valor": valor, "umbral": umbral, "supera": supera})
    iva = bool(topes.get("responsable_iva"))
    motivos.append({"tope": "responsable_iva", "nombre": "responsable de IVA", "valor": None, "umbral": None, "supera": iva})
    razones = [m for m in motivos if m["supera"]]
    obligado = bool(razones)
    if obligado:
        partes = [("fue responsable de IVA" if m["tope"] == "responsable_iva" else f"supera el tope de {m['nombre']}")
                  for m in razones]
        veredicto = "Debe declarar — " + _unir(partes)
    else:
        veredicto = "No está obligado a declarar: no supera ningún tope"
    return {"obligado": obligado, "veredicto": veredicto, "motivos": motivos, "norma": p["norma"]}


def _unir(partes: list[str]) -> str:
    if len(partes) <= 1:
        return "".join(partes)
    return ", ".join(partes[:-1]) + " y " + partes[-1]


def ultimos_digitos(nit: str) -> str:
    solo = "".join(ch for ch in str(nit or "") if ch.isdigit())
    return solo[-2:].rjust(2, "0") if solo else ""


def fecha_limite(nit: str, anio: int) -> date | None:
    dos = ultimos_digitos(nit)
    if not dos:
        return None
    tabla = P.obtener(anio)["vencimientos"]["por_ultimos_dos_digitos"]
    for rango, fecha in tabla.items():
        a, b = rango.split("-")
        if dos in (a, b):
            return date.fromisoformat(fecha)
    return None


def meses_de_retardo(limite: date, presentacion: date) -> int:
    """Meses o fracción de mes calendario de retardo (art. 641 E.T.)."""
    if presentacion <= limite:
        return 0
    meses = (presentacion.year - limite.year) * 12 + (presentacion.month - limite.month)
    if presentacion.day > limite.day:
        meses += 1
    return max(meses, 1)


def sancion_extemporaneidad(impuesto_cargo: Decimal, ingresos_brutos: Decimal, saldo_favor: Decimal,
                            limite: date, presentacion: date, anio: int) -> dict:
    """Estimación de la sanción del art. 641 E.T., con la mínima del art. 639 (UVT del año en que se impone)."""
    p = P.obtener(anio)
    s = p["sancion_extemporaneidad"]
    meses = meses_de_retardo(limite, presentacion)
    if meses == 0:
        return {"meses": 0, "valor": CERO, "texto": "", "norma": s["norma"]}
    uvt_s = P.d(p["uvt_sanciones"]["valor"])
    if impuesto_cargo > 0:
        valor = min(impuesto_cargo * P.d(s["por_mes_impuesto"]) * meses, impuesto_cargo * P.d(s["tope_impuesto"]))
        base = "5 % del impuesto a cargo por mes o fracción"
    else:
        tope = ingresos_brutos * P.d(s["tope_ingresos"])
        tope = min(tope, saldo_favor * Decimal("0.10")) if saldo_favor > 0 else min(tope, Decimal(2500) * uvt_s)
        valor = min(ingresos_brutos * P.d(s["por_mes_ingresos"]) * meses, tope)
        base = "0,5 % de los ingresos brutos por mes o fracción"
    minima = P.d(s["minima_uvt"]) * uvt_s
    valor = R(max(valor, minima))
    texto = (f"{meses} {'mes' if meses == 1 else 'meses'} de retardo: {base} ({s['norma']}), mínimo "
             f"{s['minima_uvt']} UVT ({s['norma_minima']}). {s['reduccion']}.")
    return {"meses": meses, "valor": valor, "texto": texto, "norma": s["norma"]}


def estado_vencimiento(nit: str, anio: int, hoy: date) -> dict:
    limite = fecha_limite(nit, anio)
    if not limite:
        return {"fecha": None, "dias": None, "texto": "Sin NIT: no se puede calcular el vencimiento"}
    dias = (limite - hoy).days
    if dias > 0:
        texto = f"Vence el {_fecha(limite)} · faltan {dias} {'día' if dias == 1 else 'días'}"
    elif dias == 0:
        texto = f"Vence hoy, {_fecha(limite)}"
    else:
        texto = f"Venció el {_fecha(limite)} · hace {-dias} {'día' if dias == -1 else 'días'}"
    return {"fecha": limite, "dias": dias, "texto": texto, "vencida": dias < 0}


MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre",
         "noviembre", "diciembre"]


def _fecha(f: date) -> str:
    return f"{f.day} de {MESES[f.month - 1]}"

