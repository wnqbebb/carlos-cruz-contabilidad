"""Conversión de números en formato colombiano, fechas y normalización de textos."""
from __future__ import annotations

import re
import unicodedata
from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

CERO = Decimal("0")
UNO = Decimal("1")

_MESES = {
    "ENERO": 1, "FEBRERO": 2, "MARZO": 3, "ABRIL": 4, "MAYO": 5, "JUNIO": 6, "JULIO": 7,
    "AGOSTO": 8, "SEPTIEMBRE": 9, "SETIEMBRE": 9, "OCTUBRE": 10, "NOVIEMBRE": 11, "DICIEMBRE": 12,
}
NOMBRE_MES = {v: k.capitalize() for k, v in _MESES.items() if k != "SETIEMBRE"}


def parse_numero(texto: str) -> Decimal | None:
    """Convierte '1.423.500,00', '$ 300.000,oo', '(2.280)', '1423500.5' a Decimal."""
    if texto is None:
        return None
    s = str(texto).strip()
    if not s:
        return None
    negativo = False
    if s.startswith("(") and s.endswith(")"):
        negativo, s = True, s[1:-1]
    s = s.replace("$", "").replace("COP", "").replace(" ", "").replace(" ", "")
    s = re.sub(r",o+$", ",00", s, flags=re.IGNORECASE)
    if s.startswith("-"):
        negativo, s = True, s[1:]
    if not re.fullmatch(r"[\d.,]+", s):
        return None
    if "." in s and "," in s:
        if s.rfind(",") > s.rfind("."):
            s = s.replace(".", "").replace(",", ".")
        else:
            s = s.replace(",", "")
    elif "," in s:
        s = s.replace(",", "") if re.fullmatch(r"\d{1,3}(,\d{3})+", s) else s.replace(",", ".")
    elif "." in s:
        if re.fullmatch(r"\d{1,3}(\.\d{3})+", s):
            s = s.replace(".", "")
    try:
        valor = Decimal(s)
    except InvalidOperation:
        return None
    return -valor if negativo else valor


def D(valor) -> Decimal:
    """Convierte cualquier valor de celda a Decimal (vacíos y textos no numéricos → 0)."""
    if valor is None or isinstance(valor, bool):
        return CERO
    if isinstance(valor, Decimal):
        return valor
    if isinstance(valor, int):
        return Decimal(valor)
    if isinstance(valor, float):
        return Decimal(repr(valor))
    if isinstance(valor, (datetime, date)):
        return CERO
    return parse_numero(str(valor)) or CERO


def es_numero(valor) -> bool:
    if isinstance(valor, bool):
        return False
    if isinstance(valor, (int, float, Decimal)):
        return True
    if isinstance(valor, str):
        return parse_numero(valor) is not None
    return False


def redondear(valor: Decimal, decimales: int = 0) -> Decimal:
    return valor.quantize(Decimal(1).scaleb(-decimales), rounding=ROUND_HALF_UP)


def normalizar(texto) -> str:
    """Mayúsculas, sin tildes, sin puntuación y espacios colapsados."""
    if texto is None:
        return ""
    s = unicodedata.normalize("NFKD", str(texto))
    s = "".join(c for c in s if not unicodedata.combining(c)).upper()
    s = re.sub(r"[^A-Z0-9Ñ ]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def parse_fecha(valor) -> date | None:
    if valor is None or valor == "":
        return None
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    s = str(valor).strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d/%m/%y", "%Y/%m/%d", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def años_en_texto(texto: str) -> list[int]:
    return [int(a) for a in re.findall(r"\b(19\d{2}|20\d{2})\b", str(texto or ""))]


def mes_año_en_texto(texto: str) -> tuple[int | None, int | None]:
    t = normalizar(texto)
    mes = next((n for nombre, n in _MESES.items() if re.search(rf"\b{nombre}\b", t)), None)
    años = años_en_texto(t)
    return mes, (años[0] if años else None)


def fecha_larga(f: date) -> str:
    return f"{f.day} de {NOMBRE_MES[f.month].lower()} de {f.year}"


def pesos(valor: Decimal) -> str:
    """Formato colombiano: $ 1.423.500 (con decimales solo si existen)."""
    v = redondear(valor, 2)
    entero = int(abs(v))
    dec = abs(v) - entero
    texto = f"{entero:,}".replace(",", ".")
    if dec:
        texto += "," + f"{dec:.2f}"[2:]
    return ("-$ " if v < 0 else "$ ") + texto
