"""Lectura de PDF: convierte un balance o un libro en PDF a una rejilla de celdas.

QUÉ ESPERAR, CON HONESTIDAD
---------------------------
Un PDF no es una hoja de cálculo: no tiene celdas, solo texto colocado en unas
coordenadas. Así que esto hace lo que se puede y lo dice:

  · PDF generado por un programa contable (texto real) → se leen las filas.
  · PDF escaneado (una foto del papel) → **no hay texto que leer**. Se avisa con
    claridad en vez de devolver una tabla vacía sin explicación.

EL CRITERIO ES SER ESTRICTO
---------------------------
Solo se acepta una línea que tenga la forma de un balance de prueba: un código
PUC de cuatro dígitos o más al inicio, un nombre con letras, y al menos un
importe con separador de miles o con decimales.

Una fila inventada a partir de un pie de página hace más daño que una fila que
no se leyó: lo primero ensucia los estados financieros en silencio, lo segundo
se nota de inmediato. Por eso se descarta todo lo dudoso, y lo que salga de aquí
pasa igual por la pantalla de revisión antes de entrar a la contabilidad.
"""
from __future__ import annotations

import io
import re

from ..utils.numeros import parse_numero
from .lector import Hoja

# Importe colombiano, EXIGENTE a propósito: o trae separador de miles completo
# (1.234.567) o trae decimales (1234,56) o tiene cuatro cifras o más. Un número
# suelto de tres dígitos NO cuenta, así un número de página o un dígito de
# verificación no pasa por plata.
_IMPORTE = re.compile(
    r"(?<![\d.,])"
    r"\(?-?\$?\s?"
    r"(?:\d{1,3}(?:\.\d{3})+(?:,\d{1,2})?"   # 1.234.567 · 1.234.567,89
    r"|\d{4,}(?:,\d{1,2})?"                  # 1234567 · 1234567,89
    r"|\d{1,3},\d{2})"                       # 123,45
    r"\)?"
    r"(?![\d.,]*\d)"
)

# Código PUC al inicio de la línea: una cuenta de verdad tiene 4 dígitos o más.
_CODIGO = re.compile(r"^(\d{4,8})(?!\d)")

# Líneas que NUNCA son datos contables, aunque traigan números.
_RUIDO = re.compile(
    r"\b(nit|p[áa]gina|c\.?\s?c\.?|t\.?\s?p\.?|tel[ée]fono|celular|direcci[óo]n|"
    r"fecha|generado|impreso|versi[óo]n|firma|representante|contador|"
    r"decreto|resoluci[óo]n|www|@)\b",
    re.IGNORECASE,
)


class PdfSinTexto(ValueError):
    """El PDF no tiene texto extraíble (probablemente es un escaneo)."""


def _paginas(contenido: bytes) -> list[str]:
    try:
        from pypdf import PdfReader
    except ImportError as ex:  # pragma: no cover - dependencia declarada
        raise ValueError(
            "Falta la librería para leer PDF. Ejecute: pip install -r backend/requirements.txt"
        ) from ex

    try:
        lector = PdfReader(io.BytesIO(contenido))
    except Exception as ex:
        raise ValueError(f"No se pudo abrir el PDF: {ex}") from ex

    if getattr(lector, "is_encrypted", False):
        try:
            lector.decrypt("")  # muchos PDF traen contraseña vacía
        except Exception as ex:
            raise ValueError(
                "El PDF está protegido con contraseña. Ábralo, quítele la protección "
                "y vuelva a subirlo."
            ) from ex

    return [(p.extract_text() or "") for p in lector.pages]


def _partir_linea(linea: str) -> list | None:
    """Convierte una línea de texto en una fila de celdas, si de verdad lo parece.

    Forma exigida:  CÓDIGO(4+ dígitos)  NOMBRE DE LA CUENTA  IMPORTE [IMPORTE…]
    """
    texto = " ".join(linea.split())
    if len(texto) < 10 or _RUIDO.search(texto):
        return None

    # Sin código de cuenta al inicio no se acepta la fila.
    m = _CODIGO.match(texto)
    if not m:
        return None
    codigo = m.group(1)
    resto = texto[len(codigo):]

    importes = list(_IMPORTE.finditer(resto))
    if not importes:
        return None

    nombre = resto[: importes[0].start()].strip(" .·—-\t:")
    # El nombre de una cuenta tiene letras; si no, era otra cosa.
    if len(re.sub(r"[^A-Za-zÁÉÍÓÚÑáéíóúñ]", "", nombre)) < 4:
        return None

    valores = []
    for cruda in importes:
        v = parse_numero(cruda.group(0))
        if v is not None:
            valores.append(v)          # Decimal: un importe nunca pasa por float
    if not valores:
        return None

    return [codigo, nombre, *valores]


def leer_pdf(contenido: bytes, archivo: str) -> list[Hoja]:
    """Devuelve una `Hoja` por PDF, con las filas que se pudieron reconocer."""
    paginas = _paginas(contenido)
    if not "".join(paginas).strip():
        raise PdfSinTexto(
            f"«{archivo}» no tiene texto que se pueda leer: parece un PDF escaneado "
            "(una imagen del papel). Pida el archivo en Excel, o el PDF que genera el "
            "programa contable, que sí trae el texto."
        )

    # Encabezado neutro a propósito: en el texto de un PDF las columnas vacías
    # desaparecen, así que el primer valor de una fila no es necesariamente el
    # débito. `balance.py` decide qué es cada valor (y lo avisa).
    filas: list[list] = [["Código", "Nombre", "Valor 1", "Valor 2", "Valor 3", "Valor 4"]]
    reconocidas = 0
    descartadas = 0
    for pagina in paginas:
        for linea in pagina.splitlines():
            fila = _partir_linea(linea)
            if fila:
                filas.append((fila + [None] * 6)[:6])
                reconocidas += 1
            elif linea.strip():
                descartadas += 1

    if reconocidas == 0:
        raise PdfSinTexto(
            f"«{archivo}» tiene texto, pero ninguna línea parece una cuenta contable. "
            "Se esperaba la forma «código PUC · nombre · importe», como en un balance de "
            "prueba. Si el PDF es un estado financiero con otro diseño, conviene pedir el "
            "archivo en Excel."
        )

    hoja = Hoja(archivo, "PDF", filas, {})
    hoja.sin_encabezado = True  # type: ignore[attr-defined]
    hoja.diagnostico_pdf = {  # type: ignore[attr-defined]
        "paginas": len(paginas),
        "filas_reconocidas": reconocidas,
        "lineas_descartadas": descartadas,
    }
    return [hoja]


def resumen_legible(hoja: Hoja) -> str:
    d = getattr(hoja, "diagnostico_pdf", None)
    if not d:
        return ""
    return (f"{d['paginas']} página(s), {d['filas_reconocidas']} fila(s) reconocida(s), "
            f"{d['lineas_descartadas']} línea(s) descartada(s) por no parecer datos")
