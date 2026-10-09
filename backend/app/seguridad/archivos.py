"""Archivos subidos y generados (controles C20–C23, C26 y C28).

`validar` se llama con los bytes de cada archivo ANTES de abrirlo con cualquier librería:
- el tipo se decide por la firma de bytes, no por la extensión;
- los `.xlsx`/`.docx` (que son ZIP) se revisan contra bombas de compresión y contra XML con
  `DOCTYPE`/entidades (los archivos de Office nunca los usan);
- las imágenes, por píxeles y proporción; los PDF, por tamaño y por su cabecera;
- los `.xlsm` se aceptan, pero las macros nunca se ejecutan y se avisa.

`texto_seguro` evita la inyección de fórmulas en los Excel y CSV que genera la aplicación.
"""
from __future__ import annotations

import io
import re
import zipfile
from pathlib import Path

from PIL import Image

# Una imagen de 60 megapíxeles ya es más grande que cualquier foto de celular.
Image.MAX_IMAGE_PIXELS = 60_000_000
MAX_PIXELES = 60_000_000
MAX_PROPORCION = 25
ZIP_MAX_ENTRADAS = 5000
ZIP_MAX_DESCOMPRIMIDO = 300 * 1024 * 1024
ZIP_MAX_PROPORCION = 200
PDF_MAX_BYTES = 25 * 1024 * 1024

FIRMAS = [
    (b"PK\x03\x04", "zip"),
    (b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1", "ole"),
    (b"%PDF-", "pdf"),
    (b"\x89PNG\r\n\x1a\n", "png"),
    (b"\xff\xd8\xff", "jpeg"),
    (b"GIF8", "gif"),
    (b"BM", "bmp"),
    (b"II*\x00", "tiff"),
    (b"MM\x00*", "tiff"),
]
IMAGENES = {"png", "jpeg", "gif", "bmp", "tiff", "webp"}
COMPATIBLES = {
    ".xlsx": {"zip"}, ".xlsm": {"zip"}, ".docx": {"zip"},
    ".xls": {"ole", "texto"},          # algunos «xls» son en realidad HTML o CSV exportados
    ".doc": {"ole"},
    ".pdf": {"pdf"},
    ".csv": {"texto"}, ".txt": {"texto"},
    ".png": {"png"}, ".jpg": {"jpeg"}, ".jpeg": {"jpeg"}, ".webp": {"webp"}, ".bmp": {"bmp"},
    ".tif": {"tiff"}, ".tiff": {"tiff"}, ".gif": {"gif"},
}


MENSAJE_NO_CORRESPONDE = {
    ".docx": "«{n}» no es un documento de Word (.docx) válido: puede estar dañado o tener otra extensión.",
    ".doc": "«{n}» es un Word antiguo (.doc) que no se puede leer: ábralo en Word y guárdelo como .docx.",
    ".xlsx": "«{n}» no es una hoja de Excel (.xlsx) válida: puede estar dañada o tener otra extensión.",
    ".xlsm": "«{n}» no es una hoja de Excel (.xlsm) válida: puede estar dañada o tener otra extensión.",
    ".xls": "«{n}» no es una hoja de Excel (.xls) válida: ábrala en Excel y guárdela como .xlsx.",
    ".pdf": "«{n}» no es un PDF válido: puede estar dañado.",
}


class ArchivoRechazado(Exception):
    def __init__(self, codigo: str, mensaje: str):
        super().__init__(mensaje)
        self.codigo = codigo


def tipo_por_contenido(contenido: bytes) -> str:
    cabeza = contenido[:16]
    for firma, tipo in FIRMAS:
        if cabeza.startswith(firma):
            return tipo
    if cabeza[:4] == b"RIFF" and contenido[8:12] == b"WEBP":
        return "webp"
    muestra = contenido[:8192]
    if b"\x00" not in muestra:
        try:
            muestra.decode("utf-8")
            return "texto"
        except UnicodeDecodeError:
            try:
                muestra.decode("latin-1")
                return "texto"
            except UnicodeDecodeError:  # pragma: no cover
                pass
    return "desconocido"


def _revisar_zip(nombre: str, contenido: bytes) -> list[str]:
    avisos: list[str] = []
    try:
        z = zipfile.ZipFile(io.BytesIO(contenido))
    except zipfile.BadZipFile as ex:
        raise ArchivoRechazado("archivo_danado", f"«{nombre}» está dañado o no es un archivo de Office.") from ex
    entradas = z.infolist()
    if len(entradas) > ZIP_MAX_ENTRADAS:
        raise ArchivoRechazado("archivo_sospechoso", f"«{nombre}» tiene una estructura sospechosa (demasiadas partes).")
    total = 0
    for e in entradas:
        total += e.file_size
        if e.file_size > 10 * 1024 * 1024 and e.compress_size and e.file_size / e.compress_size > ZIP_MAX_PROPORCION:
            raise ArchivoRechazado("archivo_sospechoso",
                                   f"«{nombre}» se descomprime a un tamaño desproporcionado: se rechazó por seguridad.")
    if total > ZIP_MAX_DESCOMPRIMIDO:
        raise ArchivoRechazado("archivo_sospechoso",
                               f"«{nombre}» se descomprime a más de {ZIP_MAX_DESCOMPRIMIDO // (1024 * 1024)} MB: se rechazó.")
    for e in entradas:
        if e.filename.lower().endswith((".xml", ".rels")) and e.file_size:
            with z.open(e) as parte:
                inicio = parte.read(4096)
            if re.search(rb"<!(DOCTYPE|ENTITY)", inicio, re.I):
                raise ArchivoRechazado("archivo_sospechoso",
                                       f"«{nombre}» trae definiciones XML que un archivo de Office no usa: se rechazó.")
        if e.filename.lower().endswith("vbaproject.bin"):
            avisos.append(f"«{nombre}» contiene macros. Las macros nunca se ejecutan aquí: solo se leen los datos.")
    return avisos


def _revisar_imagen(nombre: str, contenido: bytes) -> None:
    try:
        with Image.open(io.BytesIO(contenido)) as im:
            ancho, alto = im.size
    except Image.DecompressionBombError as ex:
        raise ArchivoRechazado("imagen_gigante", f"«{nombre}» es una imagen demasiado grande.") from ex
    except Exception as ex:
        raise ArchivoRechazado("archivo_danado", f"«{nombre}» no es una imagen válida.") from ex
    if ancho * alto > MAX_PIXELES:
        raise ArchivoRechazado("imagen_gigante", f"«{nombre}» es una imagen demasiado grande.")
    if min(ancho, alto) == 0 or max(ancho, alto) / min(ancho, alto) > MAX_PROPORCION:
        raise ArchivoRechazado("imagen_rara", f"«{nombre}» tiene unas proporciones que no son de una foto o un documento.")


def validar(nombre: str, contenido: bytes, permitidas: tuple[str, ...]) -> list[str]:
    """Revisa un archivo antes de abrirlo. Devuelve avisos; si es peligroso, lanza `ArchivoRechazado`."""
    nombre = Path(nombre or "archivo").name
    if not contenido:
        raise ArchivoRechazado("vacio", f"«{nombre}» llegó vacío.")
    ext = Path(nombre).suffix.lower()
    if ext not in permitidas:
        raise ArchivoRechazado("formato_no_admitido",
                               f"«{nombre}» no es un formato que se pueda leer. Se aceptan {', '.join(permitidas)}.")
    tipo = tipo_por_contenido(contenido)
    if tipo not in COMPATIBLES.get(ext, set()):
        raise ArchivoRechazado("contenido_no_corresponde", MENSAJE_NO_CORRESPONDE.get(ext, (
            "El contenido de «{n}» no corresponde a un archivo " + ext + ". Si lo renombró, súbalo con su "
            "extensión original.")).format(n=nombre))
    avisos: list[str] = []
    if tipo == "zip":
        avisos += _revisar_zip(nombre, contenido)
    elif tipo in IMAGENES:
        _revisar_imagen(nombre, contenido)
    elif tipo == "pdf" and len(contenido) > PDF_MAX_BYTES:
        raise ArchivoRechazado("archivo_grande", f"«{nombre}» pesa más de {PDF_MAX_BYTES // (1024 * 1024)} MB.")
    return avisos


def validar_todos(archivos: list[tuple[str, bytes]], permitidas: tuple[str, ...]) -> list[str]:
    avisos: list[str] = []
    for nombre, contenido in archivos:
        avisos += validar(nombre, contenido, permitidas)
    return avisos


# ── archivos que genera la aplicación ────────────────────────────────────
PELIGROSOS = ("=", "+", "-", "@", "\t", "\r")


def texto_seguro(valor):
    """Un texto de datos del usuario que empieza por = + - @ (o tab/retorno) se escribe como texto.

    Las cifras (int, float, Decimal) y las fórmulas propias de la aplicación no pasan por aquí.
    """
    if isinstance(valor, str) and valor[:1] in PELIGROSOS:
        return "'" + valor
    return valor


_REFERENCIA = re.compile(r"\$?[A-Z]{1,3}\$?\d+")
_FUNCIONES_PROPIAS = re.compile(r"\b(SUM|IF|ROUND)\(")
_LITERALES_PROPIOS = re.compile(r'"(CUADRA|NO CUADRA)"')


def es_formula_propia(texto: str) -> bool:
    """Las únicas fórmulas que escribe la aplicación: SUM, IF y ROUND sobre referencias de celda."""
    if not texto.startswith("="):
        return False
    resto = _LITERALES_PROPIOS.sub("", _FUNCIONES_PROPIAS.sub("(", _REFERENCIA.sub("", texto[1:])))
    return re.fullmatch(r"[0-9+\-*/(),:.=<> ]*", resto) is not None


def blindar_libro(libro) -> None:
    """Antes de guardar un Excel: todo texto que empiece por = + - @ (o tab/retorno) y no sea una
    fórmula propia queda como TEXTO, no como fórmula (control C28). No se ve ningún apóstrofo."""
    for hoja in libro.worksheets:
        for fila in hoja.iter_rows():
            for celda in fila:
                v = celda.value
                if isinstance(v, str) and v[:1] in PELIGROSOS and not es_formula_propia(v):
                    celda.data_type = "s"
