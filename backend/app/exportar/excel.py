"""Exportación a Excel: un libro completo, ordenado y con las fórmulas a la vista.

CRITERIOS DE DISEÑO
-------------------
1. **Menos hojas, mejor agrupadas.** Los cuatro estados financieros y los
   indicadores van en UNA sola hoja, uno debajo del otro, como los revisa un
   contador. Lo mismo con los balances y con el inventario. Antes eran 18 hojas
   sueltas; ahora son unas 12 con secciones marcadas.
2. **Portada con índice navegable.** La primera hoja identifica al cliente, da
   las cifras clave, dice si todo cuadra y lleva enlaces a cada hoja.
3. **Los totales son fórmulas, no números pegados.** Quien audite puede ver de
   dónde sale cada suma y tocar una celda para recalcular.
4. **Color con significado, no decorativo.** Tinta para cabeceras, lima para
   totales, verde y rojo solo para "cuadra" y "no cuadra".
5. **Acepta las dos formas de los importes.** Del cálculo en vivo llegan como
   `Decimal`; de un periodo guardado en la base, como cadena decimal. `_d()`
   normaliza en la frontera, así que exportar un periodo viejo da exactamente
   el mismo libro.
"""
from __future__ import annotations

import io
import re
from decimal import Decimal, InvalidOperation

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.worksheet import Worksheet

from ..contabilidad.estados import resultados
from ..contabilidad.mayor import CuentaMayor
from ..modelos import Empresa
from ..utils.numeros import CERO
from ..seguridad.archivos import blindar_libro

# ── paleta: los mismos tokens de la interfaz (frontend/src/styles/tokens.css) ──
# H14: el Excel usaba índigo y verde del diseño viejo. En esta aplicación no
# existe el verde: lo positivo va en tinta o en azul, lo negativo en rojo.
TINTA = "141414"           # --tinta
TINTA_MEDIA = "3A3A38"     # --grafito
HUESO = "F7F5F0"           # --hoja-2: encabezados de columna y secciones
ACENTO = "E7ECFB"          # --azul-suave: totales y bandas (con texto en tinta)
ACENTO_PALIDO = "FBFAF7"   # --hoja: subtotales
AZUL_MARCA = "2347D6"      # --azul: «cuadra», positivo
POSITIVO = AZUL_MARCA
POSITIVO_PALIDO = "E7ECFB"
ROJO = "C21F17"            # --rojo
ROJO_PALIDO = "FBE9E7"     # --rojo-suave
AMBAR = "A84F06"           # --ambar
AMBAR_PALIDO = "FBF0E3"    # --ambar-suave
AZUL_PALIDO = "E7ECFB"
BLANCO = "FFFFFF"

FMT_DINERO = '#,##0.00;[Red]-#,##0.00;"—"'
FMT_NUM = '#,##0.##;[Red]-#,##0.##;"—"'
FMT_PCT = '0.0%'

_FINA = Side(style="thin", color="DEDBD3")
_MEDIA = Side(style="medium", color=TINTA)
BORDE = Border(left=_FINA, right=_FINA, top=_FINA, bottom=_FINA)
BORDE_SUP = Border(top=_MEDIA)

# Compatibilidad: el nombre viejo se mantiene porque pdf.py lo importaba.
AZUL = TINTA
GRIS = HUESO

_DECIMAL = re.compile(r"^-?\d+(\.\d+)?$")


def _d(v):
    """Normaliza un importe. Acepta Decimal, int, float y cadena decimal.

    Un periodo guardado en la base devuelve los importes como cadena (ver
    `app/exactitud.py`). Esta función los vuelve a Decimal para que el libro
    salga idéntico, venga del cálculo en vivo o de la base.
    """
    if v is None or isinstance(v, Decimal):
        return v
    if isinstance(v, bool):
        return v
    if isinstance(v, int):
        return Decimal(v)
    if isinstance(v, float):
        return Decimal(repr(v))
    if isinstance(v, str) and _DECIMAL.match(v.strip()):
        try:
            return Decimal(v.strip())
        except InvalidOperation:
            return v
    return v


def _num(v):
    """Valor listo para una celda de Excel."""
    v = _d(v)
    if isinstance(v, Decimal):
        return float(v)
    if hasattr(v, "isoformat"):
        return v.isoformat()
    if isinstance(v, (list, dict)):
        return str(v)
    return v


def _es_dinero(v) -> bool:
    return isinstance(_d(v), Decimal)


def _cuadra(v) -> bool:
    """¿El valor indica que algo cuadra? Acepta booleano o cadena."""
    if isinstance(v, bool):
        return v
    return str(v).strip().lower() in ("true", "1", "sí", "si")


# ════════════════════════════════════════════════════════════════════════════
#  Piezas de presentación
# ════════════════════════════════════════════════════════════════════════════
def _titulo_hoja(ws: Worksheet, empresa: Empresa, titulo: str, subtitulo: str, ncols: int) -> int:
    """Cabecera de hoja: cliente, NIT, título y periodo. Devuelve la fila siguiente."""
    ncols = max(ncols, 3)

    ws.cell(1, 1, empresa.razon_social).font = Font(bold=True, size=15, color=TINTA)
    ws.cell(2, 1, f"NIT {empresa.nit}" + (f"  ·  {empresa.municipio}" if empresa.municipio else "")).font = Font(
        size=10, color=TINTA_MEDIA)
    ws.cell(3, 1, titulo).font = Font(bold=True, size=12, color=TINTA)
    ws.cell(4, 1, subtitulo).font = Font(size=10, color=TINTA_MEDIA)

    for fila in (1, 2, 3, 4):
        ws.merge_cells(start_row=fila, start_column=1, end_row=fila, end_column=ncols)
        ws.cell(fila, 1).alignment = Alignment(horizontal="left", vertical="center")

    # Banda lima debajo del título: separa la cabecera del contenido.
    for j in range(1, ncols + 1):
        ws.cell(5, j).fill = PatternFill("solid", fgColor=ACENTO)
    ws.row_dimensions[5].height = 4

    fila = 6
    if getattr(empresa, "demo", False):
        c = ws.cell(fila, 1, "DATOS DE DEMOSTRACIÓN — NO CORRESPONDEN A LA CONTABILIDAD REAL")
        c.font = Font(bold=True, size=10, color=ROJO)
        c.fill = PatternFill("solid", fgColor=ROJO_PALIDO)
        ws.merge_cells(start_row=fila, start_column=1, end_row=fila, end_column=ncols)
        fila += 1

    ws.cell(fila, 1, "Carlos Cruz · contabilidad que cuadra · cálculo con precisión decimal exacta").font = Font(
        size=8, italic=True, color=TINTA_MEDIA)
    ws.merge_cells(start_row=fila, start_column=1, end_row=fila, end_column=ncols)
    return fila + 2


def _banda_seccion(ws: Worksheet, fila: int, texto: str, ncols: int) -> int:
    """Separador de sección dentro de una hoja que agrupa varios informes."""
    ncols = max(ncols, 3)
    for j in range(1, ncols + 1):
        c = ws.cell(fila, j)
        c.fill = PatternFill("solid", fgColor=TINTA)
        c.border = Border()
    c = ws.cell(fila, 1, texto.upper())
    c.font = Font(bold=True, size=11, color=BLANCO)
    c.alignment = Alignment(horizontal="left", vertical="center", indent=1)
    ws.row_dimensions[fila].height = 22
    return fila + 1


def _anchos(ws: Worksheet, cols: list[dict]) -> None:
    for j, c in enumerate(cols, 1):
        ancho = c.get("ancho") or (19 if c["tipo"] in ("dinero", "numero") else 15)
        letra = get_column_letter(j)
        actual = ws.column_dimensions[letra].width or 0
        if ancho > actual:
            ws.column_dimensions[letra].width = ancho


def bloque_reporte(ws: Worksheet, rep: dict, fila: int, *, con_banda: bool = True) -> int:
    """Escribe un informe del motor a partir de `fila`. Devuelve la fila siguiente.

    Es la pieza que permite poner varios informes en una misma hoja.
    """
    cols = rep["columnas"]
    n = len(cols)
    _anchos(ws, cols)

    if con_banda:
        fila = _banda_seccion(ws, fila, rep["titulo"], n)
        if rep.get("subtitulo"):
            c = ws.cell(fila, 1, rep["subtitulo"])
            c.font = Font(size=9, italic=True, color=TINTA_MEDIA)
            ws.merge_cells(start_row=fila, start_column=1, end_row=fila, end_column=max(n, 3))
            fila += 1

    # cabecera de columnas
    cabecera = fila
    for j, c in enumerate(cols, 1):
        celda = ws.cell(cabecera, j, c["titulo"])
        celda.font = Font(bold=True, size=9, color=TINTA)
        celda.fill = PatternFill("solid", fgColor=HUESO)
        celda.alignment = Alignment(
            horizontal="right" if c["tipo"] in ("dinero", "numero") else "left",
            vertical="center", wrap_text=True)
        celda.border = Border(bottom=_MEDIA)
    ws.row_dimensions[cabecera].height = 28

    primera = cabecera + 1
    for i, f in enumerate(rep["filas"]):
        r = primera + i
        tipo = f["tipo"]
        for j, c in enumerate(cols, 1):
            v = f["valores"].get(c["clave"])
            celda = ws.cell(r, j)

            # Los totales se escriben como FÓRMULA para que se puedan auditar.
            es_suma = (tipo in ("subtotal", "total") and f.get("suma")
                       and c["tipo"] in ("dinero", "numero") and v is not None)
            if es_suma:
                refs = [primera + k for k in f["suma"]]
                letra = get_column_letter(j)
                if refs == list(range(refs[0], refs[0] + len(refs))):
                    celda.value = f"=SUM({letra}{refs[0]}:{letra}{refs[-1]})"
                else:
                    celda.value = "=" + "+".join(f"{letra}{x}" for x in refs)
            else:
                celda.value = _num(v)

            if c["tipo"] == "dinero":
                celda.number_format = FMT_DINERO
            elif c["tipo"] == "numero":
                celda.number_format = FMT_NUM
            celda.border = BORDE

            if tipo == "seccion":
                celda.font = Font(bold=True, color=TINTA)
                celda.fill = PatternFill("solid", fgColor=HUESO)
            elif tipo == "subtotal":
                celda.font = Font(bold=True, color=TINTA)
                celda.fill = PatternFill("solid", fgColor=ACENTO_PALIDO)
            elif tipo == "total":
                celda.font = Font(bold=True, size=11, color=TINTA)
                celda.fill = PatternFill("solid", fgColor=ACENTO)
                celda.border = Border(left=_FINA, right=_FINA, top=_MEDIA, bottom=_MEDIA)
            elif tipo == "nota":
                celda.font = Font(italic=True, size=9, color=ROJO)

            # Sangría por nivel en la columna de concepto.
            if (c["tipo"] == "texto" and f.get("nivel") and j <= 2
                    and tipo == "linea" and isinstance(v, str)):
                celda.alignment = Alignment(indent=int(f["nivel"]))

    r = primera + len(rep["filas"])

    verif = rep.get("verificacion")
    if verif and "cuadra" in verif:
        ok = _cuadra(verif["cuadra"])
        c = ws.cell(r, 1, "VERIFICACIÓN: " + ("CUADRA" if ok else "NO CUADRA — REVISAR"))
        c.font = Font(bold=True, color=POSITIVO if ok else ROJO)
        c.fill = PatternFill("solid", fgColor=POSITIVO_PALIDO if ok else ROJO_PALIDO)
        ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=max(n, 3))
        r += 1
        # Detalle numérico de la verificación, cuando lo trae.
        detalle = [(k, v) for k, v in verif.items() if k != "cuadra" and _es_dinero(v)]
        for k, v in detalle:
            ws.cell(r, 1, k.replace("_", " ").capitalize()).font = Font(size=9, color=TINTA_MEDIA)
            cc = ws.cell(r, 2, _num(v))
            cc.number_format = FMT_DINERO
            cc.font = Font(size=9)
            r += 1

    for nota in rep.get("notas") or []:
        c = ws.cell(r, 1, nota)
        c.font = Font(italic=True, size=9, color=TINTA_MEDIA)
        c.alignment = Alignment(wrap_text=True, vertical="top")
        ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=max(n, 3))
        ws.row_dimensions[r].height = max(14, 12 * (len(nota) // 110 + 1))
        r += 1

    return r + 2


def escribir_reporte(ws: Worksheet, rep: dict, empresa: Empresa) -> None:
    """Un informe solo en su hoja. Se conserva por compatibilidad."""
    n = len(rep["columnas"])
    fila = _titulo_hoja(ws, empresa, rep["titulo"], rep["subtitulo"], n)
    ws.freeze_panes = ws.cell(fila + 1, 1)
    fila = bloque_reporte(ws, rep, fila, con_banda=False)
    if rep.get("firmas"):
        firmas(ws, fila, empresa, n)
    _imprimir(ws, horizontal=bool(rep.get("horizontal")))


def reporte_suelto(rep: dict, empresa: Empresa) -> bytes:
    """Un libro de Excel con un solo informe (el libro diario, el mayor y balances…)."""
    wb = Workbook()
    ws = wb.active
    ws.title = rep["titulo"][:31].title()
    escribir_reporte(ws, rep, empresa)
    buf = io.BytesIO()
    blindar_libro(wb)
    wb.save(buf)
    return buf.getvalue()


def _imprimir(ws: Worksheet, horizontal: bool = False, repetir_filas: str = "1:7") -> None:
    ws.page_setup.orientation = "landscape" if horizontal else "portrait"
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    ws.print_title_rows = repetir_filas
    ws.print_options.horizontalCentered = True
    ws.oddFooter.center.text = "Carlos Cruz · &A · página &P de &N"
    ws.oddFooter.center.size = 8


def firmas(ws: Worksheet, r: int, empresa: Empresa, ncols: int) -> None:
    c2 = max(4, ncols - 1)
    r += 2
    for col, lineas in (
        (1, [empresa.rep_legal or "", f"{'Titular' if empresa.tipo_persona == 'natural' else 'Representante legal'}"
                                      f" — C.C. {empresa.rep_legal_cc or ''}"]),
        (c2, [empresa.contador or "", f"Contador público — T.P. {empresa.contador_tp or ''}"]),
    ):
        ws.cell(r, col, "_______________________________").font = Font(color=TINTA_MEDIA)
        for k, texto in enumerate(lineas, 1):
            c = ws.cell(r + k, col, texto)
            c.font = Font(bold=k == 1, size=10 if k == 1 else 9,
                          color=TINTA if k == 1 else TINTA_MEDIA)


# ════════════════════════════════════════════════════════════════════════════
#  Portada con índice navegable
# ════════════════════════════════════════════════════════════════════════════
def _portada(ws: Worksheet, res: dict, empresa: Empresa, hojas: list[tuple[str, str]]) -> None:
    r = res["resumen"]
    ws.sheet_view.showGridLines = False
    for col, w in zip("ABCDE", (4, 42, 24, 4, 52)):
        ws.column_dimensions[col].width = w

    ws.cell(2, 2, "CARLOS CRUZ").font = Font(bold=True, size=20, color=TINTA)
    ws.cell(3, 2, "Contabilidad que cuadra").font = Font(size=10, italic=True, color=TINTA_MEDIA)
    for j in (2, 3, 4, 5):
        ws.cell(4, j).fill = PatternFill("solid", fgColor=ACENTO)
    ws.row_dimensions[4].height = 5

    ws.cell(6, 2, empresa.razon_social).font = Font(bold=True, size=14, color=TINTA)
    fila = 7
    ficha = [
        ("NIT", empresa.nit),
        ("Periodo", r.get("periodo", "")),
        ("Corte", r.get("corte", "")),
        ("Municipio", empresa.municipio),
        ("Actividad CIIU", empresa.ciiu),
        ("Representante legal", empresa.rep_legal),
        ("Contador", f"{empresa.contador or ''}"
                     + (f" — T.P. {empresa.contador_tp}" if empresa.contador_tp else "")),
        ("Grupo NIIF", str(empresa.grupo_niif)),
    ]
    for etiqueta, valor in ficha:
        if not valor:
            continue
        ws.cell(fila, 2, etiqueta).font = Font(size=9, color=TINTA_MEDIA)
        ws.cell(fila, 3, valor).font = Font(size=10, bold=True, color=TINTA)
        fila += 1

    # ── cifras clave ───────────────────────────────────────────────────────
    fila += 1
    fila = _banda_seccion(ws, fila, "Cifras del periodo", 3)
    claves = [
        ("Total activo", r.get("total_activo")),
        ("Total pasivo", r.get("total_pasivo")),
        ("Total patrimonio", r.get("total_patrimonio")),
        ("Ingresos operacionales netos", r.get("ingresos")),
        ("Costo de ventas", r.get("costo_ventas")),
        ("Total gastos", r.get("total_gastos")),
        ("Utilidad (pérdida) neta", r.get("utilidad_neta")),
        ("Efectivo al cierre", r.get("efectivo")),
        ("Inventario final", r.get("inventario_final")),
    ]
    for etiqueta, valor in claves:
        if valor is None:
            continue
        ws.cell(fila, 2, etiqueta).font = Font(size=10, color=TINTA)
        c = ws.cell(fila, 3, _num(valor))
        c.number_format = FMT_DINERO
        c.font = Font(size=10, bold=True)
        es_utilidad = "Utilidad" in etiqueta
        if es_utilidad:
            neg = isinstance(_d(valor), Decimal) and _d(valor) < CERO
            c.font = Font(size=11, bold=True, color=ROJO if neg else POSITIVO)
            c.fill = PatternFill("solid", fgColor=ROJO_PALIDO if neg else POSITIVO_PALIDO)
        ws.cell(fila, 2).border = Border(bottom=_FINA)
        ws.cell(fila, 3).border = Border(bottom=_FINA)
        fila += 1

    # ── verificaciones ─────────────────────────────────────────────────────
    fila += 1
    fila = _banda_seccion(ws, fila, "Verificaciones", 3)
    for etiqueta, clave in (
        ("Balance de prueba cuadra", "bp_cuadra"),
        ("Balance ajustado cuadra", "ajustado_cuadra"),
        ("Hoja de trabajo cuadra", "hoja_trabajo_cuadra"),
        ("Activo = Pasivo + Patrimonio", "esf_cuadra"),
    ):
        if clave not in r:
            continue
        ok = _cuadra(r[clave])
        ws.cell(fila, 2, etiqueta).font = Font(size=10)
        c = ws.cell(fila, 3, "CUADRA" if ok else "NO CUADRA")
        c.font = Font(bold=True, size=10, color=POSITIVO if ok else ROJO)
        c.fill = PatternFill("solid", fgColor=POSITIVO_PALIDO if ok else ROJO_PALIDO)
        c.alignment = Alignment(horizontal="center")
        fila += 1

    alertas = r.get("alertas") or {}
    ws.cell(fila, 2, "Alertas (error / advertencia / info)").font = Font(size=10)
    ws.cell(fila, 3, f"{alertas.get('error', 0)} / {alertas.get('advertencia', 0)} / {alertas.get('info', 0)}").font = Font(
        bold=True, size=10, color=ROJO if alertas.get("error") else TINTA)
    fila += 1
    ws.cell(fila, 2, "Ajustes aceptados / propuestos").font = Font(size=10)
    ws.cell(fila, 3, f"{r.get('ajustes_aceptados', 0)} / {r.get('ajustes_propuestos', 0)}").font = Font(bold=True, size=10)
    fila += 1
    if r.get("causal_disolucion"):
        c = ws.cell(fila, 2, "ATENCIÓN: el patrimonio quedó por debajo de la mitad del capital suscrito. "
                             "Hay que revelarlo en las notas e informar a los socios.")
        c.font = Font(bold=True, size=10, color=ROJO)
        c.alignment = Alignment(wrap_text=True, vertical="top")
        ws.merge_cells(start_row=fila, start_column=2, end_row=fila, end_column=3)
        ws.row_dimensions[fila].height = 30

    # ── índice navegable (columna E) ───────────────────────────────────────
    f = 6
    ws.cell(f, 5, "CONTENIDO DEL LIBRO").font = Font(bold=True, size=11, color=TINTA)
    ws.cell(f, 5).fill = PatternFill("solid", fgColor=ACENTO)
    f += 2
    for nombre, descripcion in hojas:
        c = ws.cell(f, 5, nombre)
        # Comillas simples por si el nombre de la hoja trae espacios.
        c.hyperlink = f"#'{nombre}'!A1"
        c.font = Font(bold=True, size=10, color="1A4FCC", underline="single")
        f += 1
        d = ws.cell(f, 5, descripcion)
        d.font = Font(size=9, color=TINTA_MEDIA)
        d.alignment = Alignment(wrap_text=True, vertical="top")
        ws.row_dimensions[f].height = max(13, 11 * (len(descripcion) // 60 + 1))
        f += 2

    ws.cell(max(fila, f) + 2, 2,
            "Los totales de este libro son fórmulas de Excel, no números pegados: "
            "puede auditar de dónde sale cada suma.").font = Font(size=9, italic=True, color=TINTA_MEDIA)
    _imprimir(ws, repetir_filas="1:4")


# ════════════════════════════════════════════════════════════════════════════
#  Hojas específicas
# ════════════════════════════════════════════════════════════════════════════
def hoja_alertas(ws: Worksheet, alertas: list, empresa: Empresa) -> None:
    def campo(a, nombre, defecto=""):
        return getattr(a, nombre, None) if not isinstance(a, dict) else a.get(nombre, defecto)

    fila = _titulo_hoja(ws, empresa, "ALERTAS Y VALIDACIONES", f"{len(alertas)} alerta(s)", 5)
    for j, (t, w) in enumerate((("Severidad", 13), ("Código", 12), ("Mensaje", 92),
                                ("Detalle", 48), ("Origen", 42)), 1):
        c = ws.cell(fila, j, t)
        c.font = Font(bold=True, size=9, color=TINTA)
        c.fill = PatternFill("solid", fgColor=HUESO)
        c.border = Border(bottom=_MEDIA)
        ws.column_dimensions[get_column_letter(j)].width = w
    ws.freeze_panes = ws.cell(fila + 1, 1)
    colores = {"error": ROJO_PALIDO, "advertencia": AMBAR_PALIDO, "info": AZUL_PALIDO}
    tintas = {"error": ROJO, "advertencia": "9C6200", "info": "1A4FCC"}
    for i, a in enumerate(alertas, fila + 1):
        sev = str(campo(a, "severidad") or "info")
        for j, v in enumerate((sev.upper(), campo(a, "codigo"), campo(a, "mensaje"),
                               campo(a, "detalle"), campo(a, "origen")), 1):
            c = ws.cell(i, j, v)
            c.alignment = Alignment(wrap_text=True, vertical="top")
            c.border = BORDE
            c.font = Font(size=9, bold=j == 1, color=tintas.get(sev, TINTA) if j == 1 else TINTA)
            if j == 1:
                c.fill = PatternFill("solid", fgColor=colores.get(sev, BLANCO))
    if alertas:
        ws.auto_filter.ref = f"A{fila}:E{fila + len(alertas)}"
    _imprimir(ws, horizontal=True)


def hoja_tabla(ws: Worksheet, titulo: str, encabezados: list[tuple[str, str, int]],
               filas: list[dict], empresa: Empresa, subtitulo: str = "",
               fila_inicio: int | None = None) -> int:
    """Tabla simple. Si se pasa `fila_inicio`, se agrega a una hoja ya empezada."""
    if fila_inicio is None:
        fila = _titulo_hoja(ws, empresa, titulo, subtitulo, len(encabezados))
        ws.freeze_panes = ws.cell(fila + 1, 1)
    else:
        fila = _banda_seccion(ws, fila_inicio, titulo, len(encabezados))
        if subtitulo:
            ws.cell(fila, 1, subtitulo).font = Font(size=9, italic=True, color=TINTA_MEDIA)
            fila += 1

    for j, (_, t, w) in enumerate(encabezados, 1):
        c = ws.cell(fila, j, t)
        c.font = Font(bold=True, size=9, color=TINTA)
        c.fill = PatternFill("solid", fgColor=HUESO)
        c.alignment = Alignment(wrap_text=True, horizontal="center", vertical="center")
        c.border = Border(bottom=_MEDIA)
        letra = get_column_letter(j)
        if (ws.column_dimensions[letra].width or 0) < w:
            ws.column_dimensions[letra].width = w
    ws.row_dimensions[fila].height = 26

    for i, f in enumerate(filas, fila + 1):
        for j, (k, _, _) in enumerate(encabezados, 1):
            v = f.get(k)
            c = ws.cell(i, j, _num(v))
            c.alignment = Alignment(wrap_text=True, vertical="top")
            c.border = BORDE
            c.font = Font(size=9)
            if _es_dinero(v):
                c.number_format = FMT_DINERO
    return fila + len(filas) + 2


def hoja_saldos(ws: Worksheet, saldos: list[dict]) -> None:
    """Formato de la hoja SALDOS_INICIALES, lista para pegar en el periodo siguiente."""
    ws.cell(1, 1, "Saldos iniciales del periodo siguiente").font = Font(bold=True, size=12, color=TINTA)
    ws.cell(2, 1, "Pegue estas filas en la hoja SALDOS_INICIALES de la plantilla, "
                  "o deje que la aplicación los tome del cierre guardado.").font = Font(size=9, italic=True, color=TINTA_MEDIA)
    ws.merge_cells("A2:D2")
    for j, t in enumerate(("Código PUC", "Nombre cuenta", "Saldo débito", "Saldo crédito"), 1):
        c = ws.cell(4, j, t)
        c.font = Font(bold=True, size=9, color=TINTA)
        c.fill = PatternFill("solid", fgColor=ACENTO)
        c.border = Border(bottom=_MEDIA)
    for i, s in enumerate(saldos, 5):
        ws.cell(i, 1, s["codigo"]).border = BORDE
        ws.cell(i, 2, s["nombre"]).border = BORDE
        for j, clave in ((3, "debito"), (4, "credito")):
            v = _d(s.get(clave))
            c = ws.cell(i, j, float(v) if isinstance(v, Decimal) and v != CERO else None)
            c.number_format = FMT_DINERO
            c.border = BORDE
    final = 4 + len(saldos)
    if saldos:
        ws.cell(final + 1, 2, "SUMAS").font = Font(bold=True)
        for col in ("C", "D"):
            c = ws[f"{col}{final + 1}"]
            c.value = f"=SUM({col}5:{col}{final})"
            c.number_format = FMT_DINERO
            c.font = Font(bold=True)
            c.fill = PatternFill("solid", fgColor=ACENTO)
        ws.cell(final + 2, 2, "Diferencia (debe ser cero)").font = Font(size=9, color=TINTA_MEDIA)
        c = ws[f"C{final + 2}"]
        c.value = f"=C{final + 1}-D{final + 1}"
        c.number_format = FMT_DINERO
    for col, w in zip("ABCD", (14, 46, 19, 19)):
        ws.column_dimensions[col].width = w
    ws.freeze_panes = "A5"


def saldos_xlsx(saldos: list[dict]) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = "SALDOS_INICIALES"
    hoja_saldos(ws, saldos)
    buf = io.BytesIO()
    blindar_libro(wb)
    wb.save(buf)
    return buf.getvalue()


def _hoja_ajustes(ws: Worksheet, ajustes: list[dict], empresa: Empresa, periodo: str) -> None:
    fila = _titulo_hoja(ws, empresa, "ASIENTOS DE AJUSTE", periodo, 6)
    for col, w in zip("ABCDEF", (13, 40, 46, 19, 19, 13)):
        ws.column_dimensions[col].width = w
    if not ajustes:
        ws.cell(fila, 1, "No se propusieron ajustes para este periodo.").font = Font(italic=True, color=TINTA_MEDIA)
        return

    for a in ajustes:
        aceptado = bool(a.get("aceptado"))
        c = ws.cell(fila, 1, f"{a['titulo']}  —  {'ACEPTADO' if aceptado else 'NO APLICADO'}  ({a['tipo']})")
        c.font = Font(bold=True, size=10, color=TINTA if aceptado else TINTA_MEDIA)
        c.fill = PatternFill("solid", fgColor=ACENTO_PALIDO if aceptado else HUESO)
        ws.merge_cells(start_row=fila, start_column=1, end_row=fila, end_column=6)
        fila += 1

        c = ws.cell(fila, 1, a.get("explicacion", ""))
        c.alignment = Alignment(wrap_text=True, vertical="top")
        c.font = Font(size=9, color=TINTA_MEDIA)
        ws.merge_cells(start_row=fila, start_column=1, end_row=fila, end_column=6)
        ws.row_dimensions[fila].height = 30
        fila += 1

        for j, t in enumerate(("Código", "Cuenta", "Descripción", "Débito", "Crédito"), 1):
            c = ws.cell(fila, j, t)
            c.font = Font(bold=True, size=9)
            c.fill = PatternFill("solid", fgColor=HUESO)
            c.border = Border(bottom=_MEDIA)
        fila += 1

        ini = fila
        for l in a.get("lineas", []):
            ws.cell(fila, 1, l["codigo"]).border = BORDE
            ws.cell(fila, 2, l["cuenta"]).border = BORDE
            ws.cell(fila, 3, l.get("descripcion", "")).border = BORDE
            for j, clave in ((4, "debito"), (5, "credito")):
                v = _d(l.get(clave))
                c = ws.cell(fila, j, float(v) if isinstance(v, Decimal) and v != CERO else None)
                c.number_format = FMT_DINERO
                c.border = BORDE
            fila += 1

        ws.cell(fila, 3, "Sumas iguales").font = Font(bold=True)
        for col in ("D", "E"):
            c = ws[f"{col}{fila}"]
            c.value = f"=SUM({col}{ini}:{col}{fila - 1})"
            c.number_format = FMT_DINERO
            c.font = Font(bold=True)
            c.fill = PatternFill("solid", fgColor=ACENTO)
        c = ws.cell(fila, 6)
        c.value = f"=IF(ROUND(D{fila}-E{fila},2)=0,\"CUADRA\",\"NO CUADRA\")"
        c.font = Font(bold=True, size=9, color=POSITIVO)
        fila += 3
    _imprimir(ws)


def _hoja_notas(ws: Worksheet, notas: list[dict], empresa: Empresa, periodo: str) -> None:
    fila = _titulo_hoja(ws, empresa, "NOTAS A LOS ESTADOS FINANCIEROS", periodo, 1)
    ws.column_dimensions["A"].width = 118
    for n in notas:
        c = ws.cell(fila, 1, n["titulo"])
        c.font = Font(bold=True, size=11, color=TINTA)
        c.fill = PatternFill("solid", fgColor=ACENTO_PALIDO)
        fila += 1
        for p in n.get("parrafos", []):
            c = ws.cell(fila, 1, p)
            c.alignment = Alignment(wrap_text=True, vertical="top")
            c.font = Font(size=10)
            ws.row_dimensions[fila].height = max(15, 14 * (len(p) // 105 + 1))
            fila += 1
        fila += 1
    firmas(ws, fila, empresa, 1)
    _imprimir(ws)


def _hoja_kardex(ws: Worksheet, productos: list[dict], empresa: Empresa,
                 periodo: str, metodo: str, fila_inicio: int | None = None) -> int:
    nombre = "PROMEDIO PONDERADO" if metodo == "promedio" else "PEPS"
    if fila_inicio is None:
        fila = _titulo_hoja(ws, empresa, f"KARDEX ({nombre})", periodo, 13)
    else:
        fila = _banda_seccion(ws, fila_inicio, f"Kardex por producto ({nombre})", 13)

    titulos = ("Fecha", "Documento", "Tipo", "Lote", "Ent. cant.", "Ent. c/u", "Ent. total",
               "Sal. cant.", "Sal. c/u", "Sal. total", "Saldo cant.", "Saldo c/u", "Saldo total")
    anchos = (11, 13, 17, 10, 11, 14, 16, 11, 14, 16, 11, 14, 16)
    claves = ("fecha", "documento", "tipo", "lote", "ent_cant", "ent_cu", "ent_total",
              "sal_cant", "sal_cu", "sal_total", "saldo_cant", "saldo_cu", "saldo_total")
    for j, w in enumerate(anchos, 1):
        letra = get_column_letter(j)
        if (ws.column_dimensions[letra].width or 0) < w:
            ws.column_dimensions[letra].width = w

    for p in productos:
        c = ws.cell(fila, 1, f"{p['codigo']} — {p['descripcion']}"
                             + (f" ({p['laboratorio']})" if p.get("laboratorio") else ""))
        c.font = Font(bold=True, size=10, color=TINTA)
        c.fill = PatternFill("solid", fgColor=ACENTO_PALIDO)
        ws.merge_cells(start_row=fila, start_column=1, end_row=fila, end_column=13)
        fila += 1
        for j, t in enumerate(titulos, 1):
            c = ws.cell(fila, j, t)
            c.font = Font(bold=True, size=8)
            c.fill = PatternFill("solid", fgColor=HUESO)
            c.alignment = Alignment(wrap_text=True, horizontal="center")
            c.border = Border(bottom=_MEDIA)
        fila += 1
        for f in p.get("filas", []):
            for j, k in enumerate(claves, 1):
                v = f.get(k)
                c = ws.cell(fila, j, _num(v))
                c.border = BORDE
                c.font = Font(size=9)
                if k.endswith(("cu", "total")):
                    c.number_format = FMT_DINERO
                elif k.endswith("cant"):
                    c.number_format = FMT_NUM
            fila += 1
        # Cierre del producto, con el saldo valorizado.
        ws.cell(fila, 10, "Saldo final").font = Font(bold=True, size=9)
        c = ws.cell(fila, 13, _num(p.get("saldo_total")))
        c.number_format = FMT_DINERO
        c.font = Font(bold=True, size=9)
        c.fill = PatternFill("solid", fgColor=ACENTO)
        fila += 2
    _imprimir(ws, horizontal=True)
    return fila


# ════════════════════════════════════════════════════════════════════════════
#  Formato del contador (réplica corregida de su propio Excel)
# ════════════════════════════════════════════════════════════════════════════
def _suma(mayor: dict[str, CuentaMayor], incluir: tuple[str, ...],
          excluir: tuple[str, ...] = (), signo: int = 1) -> Decimal:
    return sum((c.neto for c in mayor.values()
                if c.codigo.startswith(incluir) and not c.codigo.startswith(excluir)), CERO) * signo


def _cuentas4(mayor: dict[str, CuentaMayor], incluir: tuple[str, ...],
              excluir: tuple[str, ...] = ()) -> list[tuple[str, str]]:
    vistas: dict[str, str] = {}
    for c in mayor.values():
        if c.codigo.startswith(incluir) and not c.codigo.startswith(excluir) and len(c.codigo) >= 4:
            vistas.setdefault(c.codigo[:4], c.nombre)
    return sorted(vistas.items())


def hoja_formato_contador(ws: Worksheet, mayor: dict[str, CuentaMayor], empresa: Empresa,
                          corte: str, periodo: str) -> None:
    """Réplica corregida del formato ESTADOS FINANCIEROS.xlsx del contador."""
    res = resultados(mayor)
    negrita = Font(bold=True)
    ws.sheet_view.showGridLines = False
    for col, w in zip("ABCDEFGHIJK", (2, 36, 18, 2, 36, 18, 2, 40, 18, 18, 18)):
        ws.column_dimensions[col].width = w
    for c_ini, titulo, sub in (("B", "ESTADO DE SITUACIÓN FINANCIERA", corte),
                               ("H", "ESTADO DE RESULTADOS INTEGRAL", periodo)):
        for k, texto in enumerate((empresa.razon_social, f"NIT N. {empresa.nit}", titulo, sub), 1):
            ws[f"{c_ini}{k}"] = texto
            ws[f"{c_ini}{k}"].font = Font(bold=True, size=11 if k <= 2 else 10, color=TINTA)
    if getattr(empresa, "demo", False):
        ws["B5"] = "DATOS DE DEMOSTRACIÓN"
        ws["B5"].font = Font(bold=True, color=ROJO)
    ws["K6"] = "ANUAL"

    izq = [
        ("ACTIVOS", None), ("ACTIVOS CORRIENTES", None),
        ("Caja", ("1105",)), ("Bancos y cuentas de ahorro", ("1110", "1115", "1120", "1125")),
        ("Cuentas por cobrar clientes", ("1305",)), ("Otros deudores", ("13",), ("1305",)),
        ("Inventarios de mercancías", ("14",)), ("Inversiones", ("12",)),
        ("Total activo corriente", "SUMA"),
        ("ACTIVOS FIJOS", None),
        ("Maquinaria y equipo", ("1520",)), ("Vehículos", ("1540",)),
        ("Muebles, enseres y equipo de oficina", ("1524",)),
        ("Equipo de cómputo y comunicación", ("1528",)),
        ("Construcciones y edificaciones", ("1516",)),
        ("Semovientes", ("1584",)), ("Lote de terreno", ("1504",)),
        ("Otros activos fijos", ("15",), ("1504", "1516", "1520", "1524", "1528", "1540", "1584", "1592")),
        ("Depreciación acumulada", ("1592",)),
        ("Total activos fijos", "SUMA"),
        ("OTROS ACTIVOS", None),
        ("Gastos pagados por anticipado", ("17",)), ("Otros", ("16", "18", "19")),
        ("Total otros activos", "SUMA"),
    ]
    der = [
        ("PASIVOS", None), ("PASIVO CORRIENTE", None),
        ("Obligaciones bancarias", ("21",)), ("Proveedores nacionales", ("22",)),
        ("Cuentas por pagar", ("23",)), ("Impuestos por pagar", ("24",)),
        ("Obligaciones laborales y prestaciones", ("25", "26")),
        ("Otros pasivos", ("27", "28", "29")),
        ("Total pasivo corriente", "SUMA"),
        ("PATRIMONIO", None),
        ("Capital social", ("31",)), ("Reservas", ("33",)),
        ("Resultados de ejercicios anteriores", ("37",)),
        ("Otros componentes patrimoniales", ("32", "34", "36", "38")),
        ("Utilidad (pérdida) del ejercicio", "UTILIDAD"),
        ("Total patrimonio", "SUMA"),
    ]

    def bloque(col_lab: str, col_val: str, lineas, signo: int, fila: int) -> tuple[int, list[str]]:
        totales, inicio = [], None
        for item in lineas:
            etiqueta, regla = item[0], item[1]
            ws[f"{col_lab}{fila}"] = etiqueta
            if regla is None:
                ws[f"{col_lab}{fila}"].font = negrita
                ws[f"{col_lab}{fila}"].fill = PatternFill("solid", fgColor=HUESO)
                inicio = fila + 1
            elif regla == "SUMA":
                ws[f"{col_val}{fila}"] = f"=SUM({col_val}{inicio}:{col_val}{fila - 1})"
                ws[f"{col_lab}{fila}"].font = negrita
                ws[f"{col_val}{fila}"].font = negrita
                ws[f"{col_val}{fila}"].fill = PatternFill("solid", fgColor=ACENTO_PALIDO)
                totales.append(f"{col_val}{fila}")
            elif regla == "UTILIDAD":
                ws[f"{col_val}{fila}"] = float(res["utilidad_neta"])
            else:
                excl = item[2] if len(item) > 2 else ()
                ws[f"{col_val}{fila}"] = float(_suma(mayor, regla, excl, signo))
            ws[f"{col_val}{fila}"].number_format = FMT_DINERO
            fila += 1
        return fila, totales

    f_izq, t_izq = bloque("B", "C", izq, 1, 7)
    ws[f"B{f_izq}"] = "TOTAL ACTIVOS"
    ws[f"C{f_izq}"] = "=" + "+".join(t_izq)
    f_der, t_der = bloque("E", "F", der, -1, 7)
    ws[f"E{f_der}"] = "TOTAL PASIVO Y PATRIMONIO"
    ws[f"F{f_der}"] = "=" + "+".join(t_der)
    for celda in (f"B{f_izq}", f"C{f_izq}", f"E{f_der}", f"F{f_der}"):
        ws[celda].font = Font(bold=True, size=11)
        ws[celda].fill = PatternFill("solid", fgColor=ACENTO)
    ws[f"C{f_izq}"].number_format = ws[f"F{f_der}"].number_format = FMT_DINERO

    fila_total = max(f_izq, f_der)
    ws[f"B{fila_total + 2}"] = "Verificación (Activo − Pasivo − Patrimonio)"
    ws[f"B{fila_total + 2}"].font = Font(size=9, color=TINTA_MEDIA)
    ws[f"C{fila_total + 2}"] = f"=C{f_izq}-F{f_der}"
    ws[f"C{fila_total + 2}"].number_format = FMT_DINERO

    # Estado de resultados, columnas H a K
    f = 7
    ws[f"H{f}"] = "INGRESOS OPERACIONALES"
    ws[f"H{f}"].font = negrita
    ws[f"H{f}"].fill = PatternFill("solid", fgColor=HUESO)
    f += 1
    lineas_ing = []
    for c4, nombre in _cuentas4(mayor, ("41",), ("4175",)):
        ws[f"H{f}"], ws[f"J{f}"] = nombre, float(-_suma(mayor, (c4,)))
        ws[f"J{f}"].number_format = FMT_DINERO
        lineas_ing.append(f)
        f += 1
    ws[f"H{f}"], ws[f"J{f}"] = "Devoluciones en ventas", float(_suma(mayor, ("4175",)))
    ws[f"J{f}"].number_format = FMT_DINERO
    f_dev = f
    f += 1
    ws[f"H{f}"] = "TOTAL INGRESOS NETOS"
    ws[f"H{f}"].font = negrita
    ws[f"K{f}"] = (f"=SUM(J{lineas_ing[0]}:J{lineas_ing[-1]})-J{f_dev}" if lineas_ing else f"=-J{f_dev}")
    ws[f"K{f}"].number_format = FMT_DINERO
    ws[f"K{f}"].font = negrita
    ws[f"K{f}"].fill = PatternFill("solid", fgColor=ACENTO_PALIDO)
    f_ing = f
    f += 2

    def grupo(titulo: str, prefijos: tuple[str, ...], excluir: tuple[str, ...] = ()) -> tuple[int, int]:
        nonlocal f
        ws[f"H{f}"] = titulo
        ws[f"H{f}"].font = negrita
        ws[f"H{f}"].fill = PatternFill("solid", fgColor=HUESO)
        f += 1
        primera = f
        for c4, nombre in _cuentas4(mayor, prefijos, excluir):
            ws[f"H{f}"], ws[f"J{f}"] = nombre, float(_suma(mayor, (c4,)))
            ws[f"J{f}"].number_format = FMT_DINERO
            f += 1
        ultima = f - 1
        ws[f"H{f}"] = f"Total {titulo.lower()}"
        ws[f"H{f}"].font = negrita
        ws[f"K{f}"] = f"=SUM(J{primera}:J{ultima})" if ultima >= primera else 0
        ws[f"K{f}"].number_format = FMT_DINERO
        ws[f"K{f}"].font = negrita
        ws[f"K{f}"].fill = PatternFill("solid", fgColor=ACENTO_PALIDO)
        total = f
        f += 2
        return total, ultima

    f_costo, _ = grupo("COSTO DE VENTAS", ("6",))
    f_admin, _ = grupo("GASTOS DE ADMINISTRACIÓN", ("51",))
    f_ventas, _ = grupo("GASTOS DE VENTAS", ("52",))

    ws[f"H{f}"] = "UTILIDAD (PÉRDIDA) OPERACIONAL"
    ws[f"H{f}"].font = Font(bold=True, size=11)
    ws[f"K{f}"] = f"=K{f_ing}-K{f_costo}-K{f_admin}-K{f_ventas}"
    ws[f"K{f}"].number_format = FMT_DINERO
    ws[f"K{f}"].font = Font(bold=True, size=11)
    ws[f"K{f}"].fill = PatternFill("solid", fgColor=ACENTO)
    f_oper = f
    f += 2

    ws[f"H{f}"], ws[f"J{f}"] = "Ingresos no operacionales", float(-_suma(mayor, ("42",)))
    ws[f"J{f}"].number_format = FMT_DINERO
    f_no_ing = f
    f += 1
    ws[f"H{f}"], ws[f"J{f}"] = "Gastos no operacionales", float(_suma(mayor, ("53",)))
    ws[f"J{f}"].number_format = FMT_DINERO
    f_no_gas = f
    f += 1
    ws[f"H{f}"] = "UTILIDAD (PÉRDIDA) ANTES DE IMPUESTOS"
    ws[f"H{f}"].font = negrita
    ws[f"K{f}"] = f"=K{f_oper}+J{f_no_ing}-J{f_no_gas}"
    ws[f"K{f}"].number_format = FMT_DINERO
    ws[f"K{f}"].font = negrita
    f_antes = f
    f += 1
    ws[f"H{f}"], ws[f"J{f}"] = "Impuesto de renta", float(_suma(mayor, ("54",)))
    ws[f"J{f}"].number_format = FMT_DINERO
    f_imp = f
    f += 1
    ws[f"H{f}"] = "UTILIDAD (PÉRDIDA) NETA DEL EJERCICIO"
    ws[f"H{f}"].font = Font(bold=True, size=12)
    ws[f"K{f}"] = f"=K{f_antes}-J{f_imp}"
    ws[f"K{f}"].number_format = FMT_DINERO
    ws[f"K{f}"].font = Font(bold=True, size=12)
    ws[f"K{f}"].fill = PatternFill("solid", fgColor=ACENTO)

    firmas(ws, max(fila_total, f) + 2, empresa, 6)
    _imprimir(ws, horizontal=True, repetir_filas="1:6")


# ════════════════════════════════════════════════════════════════════════════
#  El libro completo
# ════════════════════════════════════════════════════════════════════════════
# Grupos de hojas consolidadas. Menos pestañas, más completas y ordenadas.
GRUPOS: list[tuple[str, str, tuple[str, ...], bool]] = [
    # (nombre de hoja, descripción para el índice, informes que incluye, horizontal)
    ("Estados financieros",
     "Los cuatro estados e indicadores en una sola hoja consolidada: situación financiera, "
     "resultados integrales, cambios en el patrimonio, flujo de efectivo y ratios financieros.",
     ("situacion_financiera", "estado_resultados", "cambios_patrimonio", "flujo_efectivo", "indicadores"), False),
    ("Balances",
     "Balance de prueba, balance ajustado, asiento de cierre y balance definitivo, "
     "uno debajo del otro, con fórmulas de verificación de sumas iguales.",
     ("balance_prueba", "balance_ajustado", "asiento_cierre", "balance_definitivo"), True),
    ("Hoja de trabajo",
     "Las 12 columnas oficiales: prueba, ajustes, ajustado, resultados y balance general.",
     ("hoja_trabajo",), True),
    ("Libro diario",
     "Libro diario oficial: cada comprobante en orden cronológico, con sus líneas, su total y el origen "
     "de cada registro en el archivo del cliente.",
     ("libro_diario",), True),
    ("Mayor y balances",
     "Libro mayor y balances oficial: por cuenta, saldo anterior, movimientos y nuevo saldo, con "
     "subtotales por grupo y por clase.",
     ("mayor_balances",), True),
    ("Libro mayor",
     "Movimiento detallado de cada cuenta, con saldo inicial, movimientos y saldo final.",
     ("libro_mayor",), True),
    ("Inventario",
     "Kardex valorizado, saldos por producto, vencimientos y depreciación de activos fijos.",
     ("inventario_saldos", "inventario_vencimientos", "inventario_fisico", "depreciacion"), True),
    ("Nómina",
     "Liquidación completa de devengados, deducciones y apropiaciones de ley del periodo.",
     ("nomina_devengados", "nomina_apropiaciones"), True),
]


def _grupo_en_hoja(wb: Workbook, nombre: str, claves: tuple[str, ...], res: dict,
                   empresa: Empresa, horizontal: bool) -> bool:
    """Escribe en una hoja todos los informes del grupo que existan. False si no había ninguno."""
    presentes = [res["reportes"][k] for k in claves if res["reportes"].get(k)]
    if not presentes:
        return False

    ws = wb.create_sheet(nombre[:31])
    ncols = max(len(r["columnas"]) for r in presentes)
    titulo = nombre.upper() if len(presentes) > 1 else presentes[0]["titulo"]
    fila = _titulo_hoja(ws, empresa, titulo, res["resumen"].get("periodo", ""), ncols)
    ws.freeze_panes = ws.cell(fila, 1)

    quiere_firmas = False
    for rep in presentes:
        fila = bloque_reporte(ws, rep, fila, con_banda=len(presentes) > 1)
        quiere_firmas = quiere_firmas or bool(rep.get("firmas"))

    if quiere_firmas:
        firmas(ws, fila, empresa, ncols)
    _imprimir(ws, horizontal=horizontal)
    return True


def libro_completo(res: dict, empresa: Empresa) -> bytes:
    """Un libro con todo el trabajo del periodo.

    Acepta el resultado del cálculo en vivo (importes `Decimal`) y el resultado
    guardado en la base (importes en cadena). La hoja «EF formato contador»
    solo se genera en el primer caso, porque necesita el libro mayor en memoria.
    """
    wb = Workbook()
    portada = wb.active
    portada.title = "Portada"
    indice: list[tuple[str, str]] = []

    for nombre, descripcion, claves, horizontal in GRUPOS:
        if _grupo_en_hoja(wb, nombre, claves, res, empresa, horizontal):
            indice.append((nombre[:31], descripcion))

    # Kardex detallado, dentro de la hoja de inventario si existe.
    productos = (res.get("inventario") or {}).get("productos") or []
    if productos:
        hoja_inv = wb["Inventario"] if "Inventario" in wb.sheetnames else wb.create_sheet("Inventario")
        if "Inventario" not in [n for n, _ in indice]:
            indice.append(("Inventario", "Kardex por producto."))
        fila = hoja_inv.max_row + 2
        _hoja_kardex(hoja_inv, productos, empresa, res["resumen"].get("periodo", ""),
                     (res.get("inventario") or {}).get("metodo", "promedio"), fila_inicio=fila)

    # Ajustes
    _hoja_ajustes(wb.create_sheet("Ajustes"), res.get("ajustes") or [], empresa,
                  res["resumen"].get("periodo", ""))
    indice.append(("Ajustes", "Cada asiento de ajuste propuesto, su explicación y si se aplicó o no."))

    # Notas
    if res.get("notas"):
        _hoja_notas(wb.create_sheet("Notas"), res["notas"], empresa, res["resumen"].get("periodo", ""))
        indice.append(("Notas", "Notas a los estados financieros, listas para firmar."))

    # Formato propio del contador (solo con el cálculo en vivo)
    if res.get("mayor_ajustado"):
        hoja_formato_contador(wb.create_sheet("EF formato contador"), res["mayor_ajustado"], empresa,
                              res["resumen"].get("corte", ""), res["resumen"].get("periodo", ""))
        indice.append(("EF formato contador",
                       "La misma información en el formato de dos columnas que usa el contador, corregido."))

    # Auditorías
    aud_nomina = (res.get("nomina") or {}).get("auditoria") or []
    aud_ef = res.get("auditoria_ef") or []
    if aud_nomina or aud_ef:
        ws = wb.create_sheet("Auditoría")
        fila = _titulo_hoja(ws, empresa, "AUDITORÍA DE LOS ARCHIVOS RECIBIDOS",
                            res["resumen"].get("periodo", ""), 8)
        if aud_nomina:
            fila = hoja_tabla(
                ws, "Nómina del archivo vs. liquidación legal",
                [("hoja", "Hoja", 10), ("codigo", "Código", 9), ("concepto", "Concepto", 38),
                 ("celda", "Celda", 9), ("archivo", "Valor en el archivo", 19),
                 ("correcto", "Valor correcto", 19), ("diferencia", "Diferencia", 17),
                 ("explicacion", "Explicación", 70)],
                aud_nomina, empresa, fila_inicio=fila)
        for a in aud_ef:
            fila = hoja_tabla(
                ws, f"Estados financieros — {a['hoja']}",
                [("codigo", "Código", 9), ("severidad", "Severidad", 13),
                 ("celda", "Celda", 9), ("hallazgo", "Hallazgo", 95)],
                a.get("hallazgos") or [], empresa, subtitulo=a.get("archivo", ""), fila_inicio=fila)
            fila = hoja_tabla(
                ws, f"Comparativo archivo vs. corregido — {a['hoja']}",
                [("concepto", "Concepto", 38), ("archivo", "Según el archivo", 20),
                 ("correcto", "Corregido", 20)],
                a.get("comparativo") or [], empresa, fila_inicio=fila)
        _imprimir(ws, horizontal=True)
        indice.append(("Auditoría", "Errores encontrados en los Excel del cliente, celda por celda, "
                                    "con el valor correcto al lado."))

    # Alertas
    hoja_alertas(wb.create_sheet("Alertas"), res.get("alertas") or [], empresa)
    indice.append(("Alertas", "Todas las validaciones del periodo, con su origen exacto en el archivo."))

    # Saldos del siguiente periodo
    hoja_saldos(wb.create_sheet("Saldos siguiente periodo"), res.get("saldos_siguiente") or [])
    indice.append(("Saldos siguiente periodo",
                   "Saldos de cierre listos para abrir el periodo siguiente."))

    # La portada se escribe al final, cuando ya se sabe qué hojas existen.
    _portada(portada, res, empresa, indice)

    # Color de pestaña por grupo, para ubicarse de un golpe.
    colores = {"Portada": AZUL_MARCA, "Estados financieros": TINTA, "Indicadores": TINTA,
               "Balances": TINTA_MEDIA, "Hoja de trabajo": TINTA_MEDIA, "Libro mayor": TINTA_MEDIA,
               "Libro diario": TINTA_MEDIA, "Mayor y balances": TINTA_MEDIA,
               "Alertas": ROJO, "Auditoría": ROJO, "Notas": AZUL_MARCA, "Ajustes": AMBAR}
    for hoja in wb.worksheets:
        hoja.sheet_properties.tabColor = colores.get(hoja.title, "BFBFBF")

    buf = io.BytesIO()
    blindar_libro(wb)
    wb.save(buf)
    return buf.getvalue()
