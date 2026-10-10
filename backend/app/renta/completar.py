"""Renta: lo que solo el contador sabe, los ajustes por casilla y la lista de lo que falta (rescate H5 y H6).

POR QUÉ EXISTE
Con una comerciante (consignaciones de 93,1 millones y facturación electrónica de 4,8 millones) la
aplicación dejaba la columna «Su declaración» en 0 y la de la DIAN en 4,8 millones, sin pedir lo
esencial: los ingresos y los costos REALES del negocio. El usuario tampoco sabía qué le faltaba para
terminar. Aquí se decide:
  · cuándo hay que preguntar por el negocio y con qué comparación («Consignaciones 93,1 M ·
    Facturación 4,8 M · Ingresos que usted declara: ___»);
  · qué casillas del 210 se pueden ajustar a mano (las que son datos, no fórmulas) y con qué nota;
  · la caja «Para terminar faltan N cosas», con una acción por cada cosa.
"""
from __future__ import annotations

import dataclasses
from decimal import Decimal

from ..utils.numeros import CERO
from .calculo import EntradaRenta

# Casillas del 210 que son DATOS (las demás se calculan con otras): casilla → campo de la entrada.
CASILLA_A_CAMPO = {
    29: "patrimonio_bruto", 30: "deudas", 32: "trabajo_ingresos", 33: "trabajo_incr", 43: "honorarios_ingresos",
    44: "honorarios_incr", 45: "honorarios_costos", 58: "capital_rendimientos", 60: "capital_costos",
    74: "nolab_ingresos", 75: "nolab_devoluciones", 76: "nolab_incr", 77: "nolab_costos", 99: "pensiones_ingresos",
    107: "dividendos_1a", 112: "go_ingresos", 113: "go_costos", 114: "go_exentas", 130: "anticipo_anterior",
    131: "saldo_favor_anterior", 132: "retenciones", 135: "sanciones",
}
# Actividades de la persona natural que NO son un negocio (CIIU de asalariados, rentistas y pensionados).
CIIU_SIN_NEGOCIO = {"0010", "0020", "0081", "0082", "0090"}


def _m(v) -> str:
    """«93,1 M» para las comparaciones en una línea."""
    d = Decimal(str(v or 0))
    if abs(d) >= 1_000_000:
        return f"{(d / Decimal(1_000_000)).quantize(Decimal('0.1'))} M".replace(".", ",")
    return f"{int(d):,}".replace(",", ".")


def senales_negocio(cliente: dict, topes: dict, facturacion: Decimal, facturas: dict | None) -> dict | None:
    """¿Esta persona tiene un negocio cuyos ingresos y costos reales solo conoce el contador?

    Señales: un CIIU de actividad económica, facturación electrónica emitida (en la exógena o en el
    Excel de facturas de la DIAN) o consignaciones muy por encima de los ingresos reportados.
    """
    ciiu = "".join(ch for ch in str(cliente.get("ciiu") or "") if ch.isdigit())[:4]
    consign = Decimal(str(topes.get("consignaciones") or 0))
    ingresos_rep = Decimal(str(topes.get("ingresos") or 0))
    fact = facturacion + Decimal(str((facturas or {}).get("ventas_base") or 0))
    motivos = []
    if ciiu and ciiu not in CIIU_SIN_NEGOCIO:
        motivos.append(f"actividad económica {ciiu} en el RUT")
    if fact > 0:
        motivos.append(f"facturación electrónica emitida por {_m(fact)}")
    if consign > 0 and consign > 3 * max(ingresos_rep, Decimal(1)):
        motivos.append(f"consignaciones de {_m(consign)} frente a ingresos reportados de {_m(ingresos_rep)}")
    if not motivos:
        return None
    return {
        "motivos": motivos,
        "consignaciones": consign, "facturacion": fact, "ingresos_reportados": ingresos_rep,
        "compras_fe": Decimal(str((facturas or {}).get("compras_base") or 0)),
        "comparacion": f"Consignaciones {_m(consign)} · Facturación {_m(fact)} · Ingresos que usted declara: ____",
    }


def manuales_negocio(negocio: dict | None) -> list[dict]:
    """Los ingresos y costos del negocio que escribió el contador, como líneas agregadas."""
    if not negocio or negocio.get("sin_negocio"):
        return []
    out = []
    for clave, categoria, texto in (("ingresos", "ingreso_no_laboral", "Ingresos del negocio (los escribió el contador)"),
                                    ("costos", "costo_no_laboral", "Costos y gastos del negocio (los escribió el contador)")):
        v = negocio.get(clave)
        if v not in (None, "") and Decimal(str(v)) != 0:
            out.append({"id": f"negocio-{clave}", "categoria": categoria, "descripcion": texto, "valor": str(Decimal(str(v)))})
    return out


def aplicar_ajustes(opt: EntradaRenta, ajustes: dict) -> tuple[EntradaRenta, list[dict]]:
    """Ajustes manuales por casilla (con nota obligatoria): reemplazan el dato y quedan en el papel de trabajo."""
    cambios, lista = {}, []
    for clave, aj in (ajustes or {}).items():
        n = int(clave)
        campo = CASILLA_A_CAMPO.get(n)
        if not campo or not aj or aj.get("valor") in (None, ""):
            continue
        valor = Decimal(str(aj["valor"]))
        cambios[campo] = valor
        lista.append({"casilla": n, "campo": campo, "valor": valor, "antes": getattr(opt, campo), "nota": aj.get("nota", "")})
    return (dataclasses.replace(opt, **cambios) if cambios else opt), lista


def explicar_diferencia(n: int, dian: Decimal, opt: Decimal, negocio: dict | None, base: str) -> str:
    """Una línea que dice POR QUÉ la DIAN y la declaración no coinciden en esa casilla."""
    if n in (74, 78, 87, 90) and negocio and not negocio.get("sin_negocio"):
        return "La DIAN toma la facturación electrónica como ingreso; usted declaró los ingresos reales del negocio."
    if n in (77,):
        return "La DIAN no conoce los costos del negocio; usted los declara con sus soportes."
    if n in (28, 92) and opt > dian:
        return "El 1 % de las compras con factura electrónica es un beneficio que la DIAN no propone."
    if n in (131, 136, 137) and opt != dian:
        return "Se usa el saldo a favor del año anterior, que la propuesta de la DIAN no incluye."
    if base:
        return base
    return "La declaración usa datos que el contador agregó o confirmó; la DIAN solo usa lo que reportaron terceros."


def pendientes(dudosas: list, preguntas_pendientes: list, negocio_falta: dict | None, otros: list[str]) -> list[dict]:
    """La caja «Para terminar faltan N cosas»: una entrada por cosa, cada una con su acción."""
    out = []
    if dudosas:
        out.append({"tipo": "confirmar_filas", "texto": f"Confirmar {len(dudosas)} fila(s) leída(s) de la foto",
                    "accion": "Revisar y confirmar", "lineas": [c.linea.id for c in dudosas]})
    if preguntas_pendientes:
        n = len(preguntas_pendientes)
        out.append({"tipo": "preguntas", "texto": f"Responder {n} pregunta{'s' if n > 1 else ''}",
                    "accion": "Responder", "ids": [q.id for q in preguntas_pendientes]})
    if negocio_falta:
        out.append({"tipo": "negocio", "texto": "Ingresos y costos del negocio", "accion": "Escribirlos",
                    "comparacion": negocio_falta["comparacion"], "motivos": negocio_falta["motivos"]})
    for texto in otros:
        out.append({"tipo": "revisar", "texto": texto, "accion": "Revisar"})
    return out

