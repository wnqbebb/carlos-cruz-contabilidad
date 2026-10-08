"""Reconocer qué dice el encabezado de una columna, aunque esté mal escrito.

POR QUÉ EXISTE
Los registros de un negocio pequeño no siguen ningún formato: «CANT.», «Cantidad»,
«UNDS», «Vr. Unit», «V/R TOTAL», «Valor venta», «CLIENTE», «Comprador»… y con
errores de escritura («CANTIDA», «PROVEDOR»). Este módulo traduce cada encabezado
a un ROL (fecha, tercero, cantidad, valor unitario, total…) con un puntaje, para
que los importadores razonen sobre roles y no sobre textos.

El nombre del encabezado es solo la primera pista: los importadores comprueban
después que el CONTENIDO de la columna se comporte como dice su rótulo.
"""
from __future__ import annotations

import re
from functools import lru_cache

from ..utils.numeros import normalizar

# Rol → sinónimos (ya normalizados: mayúsculas, sin tildes ni puntuación).
SINONIMOS: dict[str, tuple[str, ...]] = {
    "fecha": ("FECHA", "FECHA VENTA", "FECHA DE VENTA", "FECHA COMPRA", "FECHA DE COMPRA", "FECHA FACTURA",
              "FECHA DE PAGO", "FECHA PAGO", "FECHA ABONO", "DIA", "FECHA GASTO", "FECHA MOVIMIENTO"),
    "documento": ("FACTURA", "NO FACTURA", "N FACTURA", "NRO FACTURA", "NUMERO FACTURA", "FACT", "DOCUMENTO",
                  "NO DOCUMENTO", "REMISION", "RECIBO", "NO RECIBO", "COMPROBANTE", "NUMERO", "NRO", "NO",
                  "CONSECUTIVO", "SOPORTE"),
    "tercero": ("CLIENTE", "NOMBRE CLIENTE", "NOMBRE DEL CLIENTE", "COMPRADOR", "PROVEEDOR", "NOMBRE PROVEEDOR",
                "NOMBRE DEL PROVEEDOR", "TERCERO", "NOMBRE TERCERO", "DEUDOR", "ACREEDOR", "BENEFICIARIO",
                "PAGADO A", "VENDIDO A", "COMPRADO A", "RAZON SOCIAL", "NOMBRE", "NOMBRES", "QUIEN DEBE",
                "A QUIEN SE DEBE", "EMPRESA", "ALMACEN"),
    "tercero_id": ("NIT", "CEDULA", "CC", "C C", "NIT CC", "NIT O CC", "NIT O CEDULA", "IDENTIFICACION",
                   "DOCUMENTO IDENTIDAD", "NIT CLIENTE", "NIT PROVEEDOR"),
    "detalle": ("PRODUCTO", "PRODUCTOS", "ARTICULO", "ARTICULOS", "REFERENCIA", "ITEM", "MERCANCIA", "MERCANCIAS",
                "DESCRIPCION", "DETALLE", "CONCEPTO", "SERVICIO", "SERVICIOS", "INSUMO", "INSUMOS", "GASTO",
                "TIPO DE GASTO", "RUBRO", "NOMBRE PRODUCTO", "DESCRIPCION PRODUCTO", "MATERIAL", "BIEN",
                "LO QUE SE VENDIO", "LO QUE SE COMPRO", "COSECHA"),
    "cantidad": ("CANTIDAD", "CANT", "CANTIDADES", "UNIDADES", "UND", "UNDS", "UNID", "KILOS", "KG", "KGS",
                 "BULTOS", "CAJAS", "PESO", "LIBRAS", "ARROBAS", "LITROS", "TONELADAS", "CANASTILLAS",
                 "NUMERO DE UNIDADES", "CANT VENDIDA", "CANTIDAD VENDIDA", "CANTIDAD COMPRADA"),
    "unitario": ("VALOR UNITARIO", "PRECIO UNITARIO", "PRECIO", "V UNITARIO", "VR UNITARIO", "V R UNITARIO",
                 "VR UNIT", "V UNIT", "P UNIT", "PRECIO UNIT", "VALOR UNIDAD", "PRECIO POR UNIDAD", "PRECIO VENTA",
                 "PRECIO DE VENTA", "PRECIO COMPRA", "PRECIO DE COMPRA", "COSTO UNITARIO", "COSTO", "COSTO UNIT",
                 "VALOR KILO", "PRECIO KILO", "VALOR X UNIDAD", "PRECIO X KILO", "VALOR POR KILO"),
    "base": ("SUBTOTAL", "SUB TOTAL", "BASE", "VALOR ANTES DE IVA", "VALOR SIN IVA", "BASE GRAVABLE",
             "VALOR NETO", "NETO"),
    "iva": ("IVA", "VALOR IVA", "VR IVA", "IMPUESTO", "IVA 19", "IVA 5"),
    "total": ("TOTAL", "VALOR TOTAL", "VR TOTAL", "V R TOTAL", "VALOR", "VR", "IMPORTE", "MONTO", "VALOR VENTA",
              "VALOR DE VENTA", "VALOR COMPRA", "VALOR DE LA COMPRA", "VALOR FACTURA", "TOTAL FACTURA",
              "TOTAL VENTA", "TOTAL COMPRA", "VALOR PAGADO", "VALOR GASTO", "TOTAL A PAGAR", "DEUDA",
              "VALOR DEUDA", "VALOR INICIAL", "VALOR CREDITO", "VALOR TOTAL VENTA", "VALOR TOTAL COMPRA",
              "PESOS", "VALOR EN PESOS"),
    "abono": ("ABONO", "ABONOS", "PAGO", "PAGOS", "PAGADO", "CANCELADO", "RECAUDO", "RECAUDADO", "ABONADO",
              "VALOR ABONO", "VALOR PAGO", "ABONO REALIZADO", "PAGOS REALIZADOS"),
    "saldo": ("SALDO", "SALDO PENDIENTE", "SALDO ACTUAL", "SALDO POR COBRAR", "SALDO POR PAGAR", "DEBE",
              "POR COBRAR", "POR PAGAR", "PENDIENTE", "QUEDA DEBIENDO", "SALDO FINAL", "RESTA"),
    "forma_pago": ("FORMA DE PAGO", "FORMA PAGO", "MEDIO DE PAGO", "MEDIO PAGO", "TIPO DE PAGO", "TIPO PAGO",
                   "CONTADO O CREDITO", "CONTADO CREDITO", "CONDICION", "CONDICION DE PAGO", "MODO DE PAGO",
                   "METODO DE PAGO", "PAGO", "COMO PAGO"),
    # Propios de la contabilidad en partida doble (libro diario, balances).
    "debito": ("DEBITO", "DEBITOS", "DEBE", "DB", "VALOR DEBITO", "MOVIMIENTO DEBITO", "CARGOS"),
    "credito": ("CREDITO", "CREDITOS", "HABER", "CR", "VALOR CREDITO", "MOVIMIENTO CREDITO", "ABONOS CONTABLES"),
    "cuenta": ("CUENTA", "CODIGO", "CODIGO CUENTA", "CODIGO PUC", "CUENTA PUC", "PUC", "COD", "COD CUENTA",
               "NO CUENTA", "CTA"),
    "nombre_cuenta": ("NOMBRE CUENTA", "NOMBRE DE LA CUENTA", "DESCRIPCION CUENTA", "NOMBRE CTA", "CUENTA CONTABLE"),
}

# Roles que llevan importes o cantidades: su columna debe ser numérica.
NUMERICOS = {"cantidad", "unitario", "base", "iva", "total", "abono", "saldo", "debito", "credito"}
# Roles que describen: su columna debe ser texto (o fecha).
DESCRIPTIVOS = {"tercero", "detalle", "forma_pago", "nombre_cuenta"}

UMBRAL = 85


def fonetico(palabra: str) -> str:
    """Cómo suena en español: «PROVEDOR», «CANTIDA», «VALOR UNITARIO» con V/B…"""
    p = palabra.upper()
    p = re.sub(r"C(?=[EI])", "S", p)
    for de, a in (("QU", "K"), ("Z", "S"), ("V", "B"), ("Y", "I"), ("LL", "I"), ("H", "")):
        p = p.replace(de, a)
    return re.sub(r"(.)\1+", r"\1", p)


def parecido(a: str, b: str) -> float:
    """Parecido 0–100 entre dos textos ya normalizados, por letra y por sonido."""
    from rapidfuzz import fuzz

    if a == b:
        return 100.0
    return max(fuzz.ratio(a, b), fuzz.ratio(fonetico(a), fonetico(b)))


@lru_cache(maxsize=4096)
def roles_de(texto: str) -> tuple[tuple[str, float], ...]:
    """Roles posibles de un encabezado, de mejor a peor puntaje.

    100 · igual a un sinónimo
     95 · contiene un sinónimo completo, como palabras («VALOR TOTAL VENTA»)
     ≥85 · se parece a un sinónimo («CANTIDA», «PROVEDOR»)
    """
    t = normalizar(texto)
    if not t or len(t) > 60:
        return ()
    puntajes: dict[str, float] = {}
    palabras = f" {t} "
    for rol, sinonimos in SINONIMOS.items():
        mejor = 0.0
        for s in sinonimos:
            if t == s:
                mejor = 100.0
                break
            if f" {s} " in palabras and len(s) >= 3:
                # Más largo el sinónimo contenido, más específico: «VALOR UNITARIO»
                # gana a «VALOR» dentro de «VALOR UNITARIO VENTA».
                mejor = max(mejor, 90.0 + min(len(s), 40) / 8)
            elif len(t) >= 4 and len(s) >= 4:
                p = parecido(t, s)
                if p >= UMBRAL:
                    mejor = max(mejor, min(p, 89.0))
        if mejor:
            puntajes[rol] = mejor
    return tuple(sorted(puntajes.items(), key=lambda kv: -kv[1]))


def mapear_fila(textos: list[tuple[int, str]], permitidos: set[str] | None = None) -> dict[str, tuple[int, float]]:
    """Asigna a cada rol la columna que mejor lo describe.

    Una columna tiene un solo rol y un rol una sola columna: si dos columnas
    compiten («VALOR» y «VALOR TOTAL»), gana la de mayor puntaje y la otra queda
    libre para que el importador la interprete por su comportamiento.
    """
    candidatos: list[tuple[float, int, str]] = []
    for c, t in textos:
        for rol, puntaje in roles_de(t):
            if permitidos is None or rol in permitidos:
                candidatos.append((puntaje, c, rol))
    candidatos.sort(key=lambda x: (-x[0], x[1]))
    asignados: dict[str, tuple[int, float]] = {}
    usadas: set[int] = set()
    for puntaje, c, rol in candidatos:
        if rol in asignados or c in usadas:
            continue
        asignados[rol] = (c, puntaje)
        usadas.add(c)
    return asignados


def contiene_palabra(texto: str, palabras: set[str] | tuple[str, ...], umbral: float = UMBRAL) -> str:
    """Primera palabra clave presente en el texto, tolerando errores de escritura."""
    t = normalizar(texto)
    if not t:
        return ""
    tokens = t.split()
    for p in palabras:
        if " " in p:
            if f" {p} " in f" {t} ":
                return p
            continue
        for tok in tokens:
            if tok == p or (len(tok) >= 5 and len(p) >= 5 and parecido(tok, p) >= umbral):
                return p
    return ""
