"""Word y PDF: sus tablas se leen como hojas, su texto sirve para la identidad.

POR QUÉ EXISTE
Muchos clientes pequeños no entregan un Excel: entregan un PDF del programa
contable, una tabla pegada en Word, o los estatutos y el RUT. Hasta la v2.1
todo eso se rechazaba o se leía a medias. Desde la v2.2:

  · las TABLAS de un .docx y de un PDF con texto entran al mismo detector de
    formatos que las hojas de Excel;
  · los PÁRRAFOS sirven para sacar la identidad y los datos de la ficha;
  · un PDF escaneado se rechaza con un mensaje claro, sin inventar nada.
"""
from __future__ import annotations

import io
import re

from .lector import Hoja, _recortar


class DocumentoSinTexto(ValueError):
    """El archivo es una imagen: no hay nada que leer sin OCR."""


def _celda(valor) -> object:
    """Celda de tabla: número si lo parece, si no texto limpio."""
    t = re.sub(r"\s+", " ", str(valor or "")).strip()
    return t or None


# ── Word ────────────────────────────────────────────────────────────────────
def leer_docx(contenido: bytes, archivo: str) -> list[Hoja]:
    """Una `Hoja` por tabla del documento, más una con el texto de los párrafos.

    La hoja de texto se llama «(texto)» y no trae rejilla de datos: existe para
    que la identidad y la ficha del cliente puedan leer los párrafos.
    """
    try:
        import docx
    except ImportError as ex:  # pragma: no cover - dependencia declarada
        raise ValueError("Falta la librería python-docx para leer archivos .docx.") from ex

    try:
        documento = docx.Document(io.BytesIO(contenido))
    except Exception as ex:
        raise ValueError(
            f"«{archivo}» no se pudo abrir como documento de Word. "
            "Si es un .doc antiguo, ábralo y guárdelo como .docx."
        ) from ex

    hojas: list[Hoja] = []
    for i, tabla in enumerate(documento.tables, start=1):
        filas = []
        for fila in tabla.rows:
            # `fila.cells` repite la celda en las combinadas: se deja igual,
            # porque el detector ya tolera valores repetidos.
            filas.append([_celda(c.text) for c in fila.cells])
        filas = _recortar(filas)
        if filas:
            hojas.append(Hoja(archivo, f"Tabla {i}", filas, {}))

    parrafos = [p.text.strip() for p in documento.paragraphs if p.text.strip()]
    # Las tablas también aportan texto para la identidad (p. ej. socios).
    for t in documento.tables:
        for fila in t.rows:
            linea = " · ".join(c.text.strip() for c in fila.cells if c.text.strip())
            if linea:
                parrafos.append(linea)

    if not hojas and not parrafos:
        raise DocumentoSinTexto(
            f"«{archivo}» no tiene texto ni tablas que se puedan leer. "
            "Si el contenido es una imagen pegada, pida el documento original."
        )

    hoja_texto = Hoja(archivo, "(texto)", [[p] for p in parrafos], {})
    hoja_texto.es_texto = True            # type: ignore[attr-defined]
    hoja_texto.texto_plano = "\n".join(parrafos)   # type: ignore[attr-defined]
    hojas.append(hoja_texto)
    return hojas


# ── PDF ─────────────────────────────────────────────────────────────────────
def _tablas_pdf(contenido: bytes) -> list[tuple[int, list[list]]]:
    """Tablas que pdfplumber reconoce, con el número de página de cada una."""
    try:
        import pdfplumber
    except ImportError:  # pragma: no cover - dependencia declarada
        return []
    salida: list[tuple[int, list[list]]] = []
    try:
        with pdfplumber.open(io.BytesIO(contenido)) as pdf:
            for n, pagina in enumerate(pdf.pages, start=1):
                for tabla in pagina.extract_tables() or []:
                    filas = _recortar([[_celda(c) for c in fila] for fila in tabla])
                    # Una «tabla» de una sola columna suele ser texto suelto.
                    if len(filas) >= 2 and max(len(f) for f in filas) >= 2:
                        salida.append((n, filas))
    except Exception:
        return []
    return salida


def texto_pdf(contenido: bytes) -> list[str]:
    """Texto de cada página. Vacío si el PDF es una imagen escaneada."""
    try:
        from pypdf import PdfReader
    except ImportError:  # pragma: no cover
        return []
    try:
        lector = PdfReader(io.BytesIO(contenido))
        return [(p.extract_text() or "") for p in lector.pages]
    except Exception:
        return []


def leer_pdf_completo(contenido: bytes, archivo: str) -> list[Hoja]:
    """Hojas de un PDF: una por tabla reconocida, más la hoja de texto.

    No lanza si no hay tablas: puede ser un RUT o unos estatutos, que solo
    aportan identidad. Sí lanza si no hay texto en absoluto.
    """
    paginas = texto_pdf(contenido)
    plano = "\n".join(paginas).strip()
    tablas = _tablas_pdf(contenido)

    if not plano and not tablas:
        raise DocumentoSinTexto(
            f"«{archivo}» es una imagen del papel (PDF escaneado): no tiene texto que leer. "
            "Pida el archivo original, o el PDF que genera el programa contable."
        )

    hojas = [Hoja(archivo, f"Tabla {i} (pág. {pag})", filas, {})
             for i, (pag, filas) in enumerate(tablas, start=1)]

    # Si no hubo tablas, se intenta la lectura por renglones del balance.
    if not hojas:
        from .pdf_lector import PdfSinTexto, leer_pdf

        try:
            hojas = list(leer_pdf(contenido, archivo))
        except PdfSinTexto:
            hojas = []

    hoja_texto = Hoja(archivo, "(texto)", [[p] for p in plano.splitlines() if p.strip()], {})
    hoja_texto.es_texto = True            # type: ignore[attr-defined]
    hoja_texto.texto_plano = plano        # type: ignore[attr-defined]
    hojas.append(hoja_texto)
    return hojas


def es_hoja_de_texto(hoja: Hoja) -> bool:
    return bool(getattr(hoja, "es_texto", False))
