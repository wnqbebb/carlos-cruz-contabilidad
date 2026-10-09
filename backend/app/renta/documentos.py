"""«Suelte todo»: cada archivo (foto, PDF, Excel) → `Reporte`; luego se agrupan por contribuyente.

- Las fotos pasan por `ocr.leer_imagen` (enderezar, aplanar la tabla, leer por filas).
- Los PDF del portal traen texto: se leen sus tablas; si un PDF es escaneado, cada
  página se trata como foto.
- Los Excel y CSV se leen fila por fila.

De cada documento se sabe de quién es (número de documento y nombre impresos en
el encabezado). Un archivo de otro contribuyente se separa y se avisa.
"""
from __future__ import annotations

import io
import re
from dataclasses import dataclass, field
from pathlib import Path

from . import lectura as LT
from . import ocr

IMAGENES = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff", ".heic"}


@dataclass
class Leido:
    reporte: LT.Reporte
    recortes: dict[str, bytes] = field(default_factory=dict)   # id → PNG de la fila (verificación)
    paginas: int = 1
    tipo: str = ""                                             # foto | pdf | excel


def leer_lote(archivos: list[tuple[str, bytes]]) -> tuple[list[Leido], list[str]]:
    """Lee varios archivos; uno dañado no detiene a los demás. Corre aislado (ver `seguridad/aislado.py`)."""
    leidos, errores = [], []
    for nombre, contenido in archivos:
        try:
            leidos.append(leer_archivo(nombre, contenido))
        except ocr.OcrNoDisponible as ex:
            errores.append(f"«{nombre}»: {ex}")
        except Exception:
            errores.append(f"«{nombre}» no se pudo leer. Revise que no esté dañado.")
    return leidos, errores


def leer_archivo(nombre: str, contenido: bytes) -> Leido:
    ext = Path(nombre).suffix.lower()
    if ext in IMAGENES:
        return leer_foto(nombre, contenido)
    if ext == ".pdf":
        return leer_pdf(nombre, contenido)
    if ext in (".xlsx", ".xlsm", ".xls", ".csv"):
        return leer_hoja(nombre, contenido)
    raise ValueError(f"«{nombre}»: este tipo de archivo no se puede leer para la renta. Use fotos, PDF o Excel.")


def leer_foto(nombre: str, contenido: bytes, pagina: int = 1) -> Leido:
    lec = ocr.leer_imagen(contenido)
    filas, confs, resaltadas, ids, recortes = [], [], [], [], {}
    cabecera: list[str] = []
    for i, f in enumerate(lec.filas):
        textos = [c.texto for c in f.celdas]
        tiene_valor = any(re.search(r"\d[.,]\d{3}", t) for t in textos)
        if not tiene_valor and not filas:
            # Encabezado (antes de la primera fila con valores): se relee como texto corrido.
            cabecera += ocr.texto_de(lec, f.caja).splitlines()
            continue
        rid = f"{nombre}:{pagina}:{i}"
        filas.append(textos)
        confs.append([c.confianza if c.texto else 1.0 for c in f.celdas])
        resaltadas.append(f.resaltada)
        ids.append(rid)
        recortes[rid] = ocr.recorte_png(lec, f.caja)
    rep = LT.interpretar_filas(filas, confs, resaltadas, documento=nombre, pagina=pagina, recortes=ids)
    if not cabecera and lec.texto_arriba:
        cabecera = lec.texto_arriba.splitlines()
    for linea in cabecera:
        LT._cabecera(linea, rep)
    rep.nombre, anotado = LT.nombre_desde_cabecera(cabecera)
    credenciales = sum(1 for linea in cabecera for p in linea.split() if ocr.CREDENCIAL.fullmatch(p))
    rep.anotaciones_a_mano = anotado or lec.anotaciones or bool(lec.credenciales_descartadas) or credenciales > 0
    rep.credenciales_descartadas = lec.credenciales_descartadas + credenciales
    rep.sugerencias_a_mano = list(lec.notas_a_mano)
    if rep.lineas and rep.confianza_alta < 0.5:
        rep.avisos.append("Esta hoja se imprimió dos veces (texto encimado); para mayor seguridad descargue el reporte "
                          "en PDF o Excel del portal de la DIAN. Se siguió con lo que se pudo leer.")
    if not lec.tabla_encontrada:
        rep.avisos.append(f"En «{nombre}» no se encontró una tabla con líneas; se leyó el texto corrido.")
    return Leido(reporte=rep, recortes={k: v for k, v in recortes.items() if v}, tipo="foto")


def leer_pdf(nombre: str, contenido: bytes) -> Leido:
    import pdfplumber

    reportes, recortes, paginas = [], {}, 0
    with pdfplumber.open(io.BytesIO(contenido)) as pdf:
        for n, pagina in enumerate(pdf.pages, start=1):
            paginas += 1
            texto = pagina.extract_text() or ""
            if len(texto.strip()) < 20:
                # Escaneado: se trata la página como foto.
                imagen = pagina.to_image(resolution=200).original
                buf = io.BytesIO()
                imagen.save(buf, format="PNG")
                leido = leer_foto(nombre, buf.getvalue(), pagina=n)
                reportes.append(leido.reporte)
                recortes.update(leido.recortes)
                continue
            filas: list[list[str]] = []
            for tabla in pagina.extract_tables() or []:
                filas += [[c or "" for c in fila] for fila in tabla]
            if not filas:
                filas = [re.split(r"\s{2,}", l) for l in texto.splitlines()]
            rep = LT.interpretar_filas(filas, documento=nombre, pagina=n)
            for l in texto.splitlines():
                LT._cabecera(l, rep)
            rep.nombre = rep.nombre or LT.nombre_desde_cabecera(texto.splitlines())[0]
            reportes.append(rep)
    unido, _ = LT.unir_paginas(reportes) if reportes else (LT.Reporte(documento=nombre), [])
    return Leido(reporte=unido, recortes=recortes, paginas=paginas, tipo="pdf")


def leer_hoja(nombre: str, contenido: bytes) -> Leido:
    filas: list[list[str]] = []
    if nombre.lower().endswith(".csv"):
        import csv

        texto = contenido.decode("utf-8-sig", errors="replace")
        separador = ";" if texto.count(";") > texto.count(",") else ","
        filas = [fila for fila in csv.reader(io.StringIO(texto), delimiter=separador)]
    else:
        from openpyxl import load_workbook

        libro = load_workbook(io.BytesIO(contenido), read_only=True, data_only=True)
        for hoja in libro.worksheets:
            for fila in hoja.iter_rows(values_only=True):
                filas.append([_celda_excel(v) for v in fila])
    rep = LT.interpretar_filas(filas, documento=nombre)
    cabecera = [" ".join(c for c in f if c) for f in filas[:8]]
    for l in cabecera:
        LT._cabecera(l, rep)
    rep.nombre = LT.nombre_desde_cabecera(cabecera)[0]
    return Leido(reporte=rep, tipo="excel")


def _celda_excel(v) -> str:
    if v is None:
        return ""
    if isinstance(v, (int, float)):
        # Un importe numérico de Excel se escribe como lo imprime el reporte.
        return f"$ {v:,.2f}"
    return str(v)


def agrupar_por_contribuyente(leidos: list[Leido], documento_esperado: str = "") -> dict:
    """Separa los reportes por número de documento. Los que no dicen de quién son se
    asignan al contribuyente principal (el esperado o el más frecuente)."""
    por_doc: dict[str, list[Leido]] = {}
    sin_doc: list[Leido] = []
    for l in leidos:
        doc = l.reporte.numero_doc
        (por_doc.setdefault(doc, []) if doc else sin_doc).append(l)
    principal = documento_esperado if documento_esperado in por_doc else (
        max(por_doc, key=lambda d: len(por_doc[d])) if por_doc else "")
    if principal:
        por_doc.setdefault(principal, []).extend(sin_doc)
    else:
        por_doc[""] = sin_doc
    otros = {d: v for d, v in por_doc.items() if d != principal}
    return {"principal": principal, "leidos": por_doc.get(principal, []), "otros": otros}
