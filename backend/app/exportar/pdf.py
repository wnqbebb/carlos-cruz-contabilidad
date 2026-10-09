"""PDF de estados financieros y balances, listo para firmar."""
from __future__ import annotations

import io
import re
from decimal import Decimal

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (BaseDocTemplate, Frame, KeepTogether, NextPageTemplate, PageBreak, PageTemplate, Paragraph,
                                Spacer, Table, TableStyle)

from ..modelos import Empresa
from ..utils import nit as unit
from ..utils.numeros import redondear

_DECIMAL = re.compile(r"^-?\d+(\.\d+)?$")

# Los mismos tokens de la interfaz. El PDF es siempre en claro (se imprime).
AZUL = colors.HexColor("#141414")          # --tinta: títulos
FONDO_ENCABEZADO = colors.HexColor("#F7F5F0")  # --hoja-2
FONDO_SUBTOTAL = colors.HexColor("#FBFAF7")    # --hoja
FONDO_TOTAL = colors.HexColor("#E7ECFB")       # --azul-suave
LINEA = colors.HexColor("#DEDBD3")
estilos = getSampleStyleSheet()
E_TIT = ParagraphStyle("tit", parent=estilos["Title"], fontSize=12, leading=15, textColor=AZUL, spaceAfter=2)
E_SUB = ParagraphStyle("sub", parent=estilos["Normal"], fontSize=9, alignment=TA_CENTER)
E_CEL = ParagraphStyle("cel", parent=estilos["Normal"], fontSize=7.5, leading=9)
E_CEL_B = ParagraphStyle("celb", parent=E_CEL, fontName="Helvetica-Bold")
E_NOTA = ParagraphStyle("nota", parent=estilos["Normal"], fontSize=8.5, leading=11, spaceAfter=4)
E_H = ParagraphStyle("h", parent=estilos["Heading3"], fontSize=10, textColor=AZUL, spaceBefore=6, spaceAfter=2)

ORDEN_PDF = ["situacion_financiera", "estado_resultados", "cambios_patrimonio", "flujo_efectivo", "indicadores",
             "balance_prueba", "hoja_trabajo", "balance_definitivo", "libro_diario", "mayor_balances",
             "inventario_saldos"]


def miles(v) -> str:
    """Importe en formato colombiano. Acepta Decimal o la cadena con que se guarda en la base."""
    if v is None or v == "":
        return ""
    if isinstance(v, str):
        if not _DECIMAL.match(v.strip()):
            return v
        v = Decimal(v.strip())
    if not isinstance(v, (Decimal, int)):
        return str(v)
    d = redondear(Decimal(v), 2)
    if d == 0:
        return "—"
    entero = int(abs(d))
    dec = abs(d) - entero
    texto = f"{entero:,}".replace(",", ".") + ("," + f"{dec:.2f}"[2:] if dec else "")
    return f"({texto})" if d < 0 else texto


def _encabezado(empresa: Empresa, rep: dict) -> list:
    partes = [Paragraph(empresa.razon_social, E_TIT), Paragraph(f"NIT {_nit(empresa)}", E_SUB),
              Paragraph(f"<b>{rep['titulo']}</b>", E_SUB), Paragraph(rep["subtitulo"], E_SUB)]
    if empresa.demo:
        partes.append(Paragraph('<font color="#C21F17"><b>DATOS DE DEMOSTRACIÓN</b></font>', E_SUB))
    return partes + [Spacer(1, 6)]


def _nit(empresa: Empresa) -> str:
    return unit.formatear(empresa.nit) or empresa.nit


# Columnas que solo sirven en pantalla y en Excel (en carta no caben). Va por
# clave, además de la marca `pdf: False`, para los periodos guardados antes.
SOLO_PANTALLA = {"libro_diario": {"comprobante", "tipo", "origen"}}


def _tabla(rep: dict, ancho_total: float) -> Table:
    ocultas = SOLO_PANTALLA.get(rep.get("id", ""), set())
    cols = [c for c in rep["columnas"] if c.get("pdf", True) and c["clave"] not in ocultas]
    pesos_col = [(c.get("ancho") or (14 if c["tipo"] in ("dinero", "numero") else 12)) for c in cols]
    # Una fecha nunca se parte en dos renglones.
    pesos_col = [max(p, 12) if c["clave"] in ("fecha", "vencimiento") else p for p, c in zip(pesos_col, cols)]
    factor = ancho_total / sum(pesos_col)
    anchos = [p * factor for p in pesos_col]
    datos = [[Paragraph(f"<b>{c['titulo']}</b>", E_CEL) for c in cols]]
    estilo = [("BACKGROUND", (0, 0), (-1, 0), FONDO_ENCABEZADO), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
              ("GRID", (0, 0), (-1, -1), 0.25, LINEA), ("TOPPADDING", (0, 0), (-1, -1), 1.5),
              ("BOTTOMPADDING", (0, 0), (-1, -1), 1.5)]
    for i, f in enumerate(rep["filas"], 1):
        negrita = f["tipo"] in ("seccion", "subtotal", "total")
        fila = []
        for c in cols:
            v = f["valores"].get(c["clave"])
            if c["tipo"] in ("dinero", "numero"):
                fila.append(miles(v))
            else:
                texto = "" if v is None else str(v)
                if c["clave"] in ("fecha", "vencimiento") and re.fullmatch(r"\d{4}-\d{2}-\d{2}", texto):
                    texto = f"{texto[8:10]}/{texto[5:7]}/{texto[:4]}"
                sangria = "&nbsp;" * 3 * (f.get("nivel") or 0) if f["tipo"] == "linea" else ""
                fila.append(Paragraph(sangria + texto, E_CEL_B if negrita else E_CEL))
        datos.append(fila)
        if negrita:
            estilo.append(("FONTNAME", (0, i), (-1, i), "Helvetica-Bold"))
        if f["tipo"] == "total":
            estilo.append(("BACKGROUND", (0, i), (-1, i), FONDO_TOTAL))
        elif f["tipo"] == "subtotal":
            estilo.append(("BACKGROUND", (0, i), (-1, i), FONDO_SUBTOTAL))
    for j, c in enumerate(cols):
        if c["tipo"] in ("dinero", "numero"):
            estilo.append(("ALIGN", (j, 1), (j, -1), "RIGHT"))
    estilo.append(("FONTSIZE", (0, 0), (-1, -1), 7.5))
    t = Table(datos, colWidths=anchos, repeatRows=1)
    t.setStyle(TableStyle(estilo))
    return t


def _cargo_firma(empresa: Empresa) -> str:
    return "Titular" if empresa.tipo_persona == "natural" else "Representante legal"


def _firmas(empresa: Empresa) -> Table:
    t = Table([["_" * 34, "", "_" * 34],
               [empresa.rep_legal, "", empresa.contador],
               [f"{_cargo_firma(empresa)} — C.C. {empresa.rep_legal_cc}", "", f"Contador público — T.P. {empresa.contador_tp}"]],
              colWidths=[7.5 * cm, 2 * cm, 7.5 * cm])
    t.setStyle(TableStyle([("FONTSIZE", (0, 0), (-1, -1), 8.5), ("FONTNAME", (0, 1), (-1, 1), "Helvetica-Bold"),
                           ("ALIGN", (0, 0), (-1, -1), "CENTER"), ("TOPPADDING", (0, 0), (-1, 0), 28)]))
    return t


def generar(res: dict, empresa: Empresa, claves: list[str] | None = None) -> bytes:
    buf = io.BytesIO()
    vertical, horizontal = letter, landscape(letter)
    margen = 1.5 * cm
    doc = BaseDocTemplate(buf, pagesize=vertical, leftMargin=margen, rightMargin=margen, topMargin=margen, bottomMargin=margen,
                          title=f"Estados financieros {empresa.razon_social}", author=empresa.contador,
                          creator="Carlos Cruz", producer="Carlos Cruz", subject="", keywords="")

    def pie(canvas, d):
        canvas.saveState()
        canvas.setFont("Helvetica", 7)
        canvas.drawString(margen, 0.8 * cm, f"{empresa.razon_social} — NIT {_nit(empresa)}")
        canvas.drawRightString(d.pagesize[0] - margen, 0.8 * cm, f"Página {d.page}")
        canvas.restoreState()

    claves = claves or ORDEN_PDF
    reps = [res["reportes"][k] for k in claves if k in res["reportes"]]
    plantillas = [
        PageTemplate("V", [Frame(margen, margen, vertical[0] - 2 * margen, vertical[1] - 2 * margen)], onPage=pie, pagesize=vertical),
        PageTemplate("H", [Frame(margen, margen, horizontal[0] - 2 * margen, horizontal[1] - 2 * margen)], onPage=pie, pagesize=horizontal),
    ]
    if reps and reps[0].get("horizontal"):
        plantillas.reverse()
    doc.addPageTemplates(plantillas)
    historia = []
    for i, rep in enumerate(reps):
        plantilla = "H" if rep.get("horizontal") else "V"
        ancho = (horizontal if plantilla == "H" else vertical)[0] - 2 * margen
        if i > 0:
            historia += [NextPageTemplate(plantilla), PageBreak()]
        historia += _encabezado(empresa, rep)
        historia.append(_tabla(rep, ancho))
        verif = rep.get("verificacion")
        if verif and "cuadra" in verif:
            historia.append(Paragraph(f"<b>Verificación:</b> {'CUADRA' if verif['cuadra'] else 'NO CUADRA'}", E_NOTA))
        for n in rep.get("notas") or []:
            historia.append(Paragraph(n, E_NOTA))
        if rep.get("firmas"):
            historia.append(KeepTogether([Spacer(1, 10), _firmas(empresa)]))
        if rep["id"] == "flujo_efectivo" and res.get("notas"):
            historia += [NextPageTemplate("V"), PageBreak()]
            historia += _encabezado(empresa, {"titulo": "NOTAS A LOS ESTADOS FINANCIEROS", "subtitulo": res["resumen"]["periodo"]})
            for n in res["notas"]:
                historia.append(Paragraph(n["titulo"], E_H))
                for p in n["parrafos"]:
                    historia.append(Paragraph(p, E_NOTA))
            historia.append(KeepTogether([Spacer(1, 10), _firmas(empresa)]))
    doc.build(historia)
    return buf.getvalue()
