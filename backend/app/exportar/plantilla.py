"""Genera la plantilla oficial de carga y un archivo de demostración."""
from __future__ import annotations

import io
from datetime import date, timedelta

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

from ..contabilidad.puc import puc
from . import casos
from ..modelos import Empresa

AZUL = "1F4E79"

HOJAS = {
    "SALDOS_INICIALES": ["Código PUC", "Nombre cuenta", "Saldo débito", "Saldo crédito"],
    "MOVIMIENTOS": ["Fecha", "No. comprobante", "Tipo", "Código PUC", "Nombre cuenta", "NIT tercero", "Nombre tercero",
                    "Descripción", "Débito", "Crédito", "Base retención"],
    "AJUSTES": ["Fecha", "No. comprobante", "Tipo", "Código PUC", "Nombre cuenta", "NIT tercero", "Nombre tercero",
                "Descripción", "Débito", "Crédito", "Base retención"],
    "INVENTARIO_MOVS": ["Fecha", "Documento", "Código producto", "Descripción", "Laboratorio", "Lote", "Fecha vencimiento",
                        "Tipo", "Cantidad", "Costo unitario", "Precio venta"],
    "INVENTARIO_FISICO": ["Código producto", "Cantidad contada", "Fecha de conteo"],
    "ACTIVOS_FIJOS": ["Descripción", "Cuenta PUC", "Fecha compra", "Costo", "Vida útil meses", "Valor residual", "Método"],
    "NOMINA": ["Mes", "Nombre", "Cédula", "Cargo", "Salario básico", "Valor hora", "Horas", "Días trabajados",
               "Aux. transporte", "Horas extra", "Comisiones", "Clase riesgo ARL"],
}

INSTRUCCIONES = [
    "PLANTILLA CONTABLE FANANT — INSTRUCCIONES",
    "",
    "1. EMPRESA: revise los datos de la empresa y escriba el periodo (desde / hasta) en formato AAAA-MM-DD.",
    "2. SALDOS_INICIALES: saldos de las cuentas al inicio del periodo (clases 1, 2 y 3). Débitos = créditos. Si la deja vacía, la aplicación "
    "usa el último cierre guardado.",
    "3. MOVIMIENTOS: libro diario. Cada comprobante debe cumplir partida doble (suma débitos = suma créditos). Use el código PUC "
    "(lista desplegable) o escriba el nombre de la cuenta: la aplicación lo mapea y le pide confirmación.",
    "4. AJUSTES (opcional): ajustes manuales con las mismas columnas del diario. La aplicación propone además los ajustes "
    "automáticos (costo de ventas, depreciación, nómina).",
    "5. INVENTARIO_MOVS: tipos permitidos: Inventario inicial, Compra, Venta, Devolución compra, Devolución venta, Ajuste. "
    "Las entradas llevan costo unitario; las salidas se valoran con el método elegido (promedio ponderado o PEPS).",
    "6. INVENTARIO_FISICO (opcional): cantidades contadas al cierre para comparar con el kardex.",
    "7. ACTIVOS_FIJOS (opcional): la depreciación se calcula por línea recta desde el mes siguiente a la compra.",
    "8. NOMINA (opcional): un renglón por empleado y mes. Salario mensual, o valor hora + horas. Aux. transporte: SI / NO / AUTO.",
    "",
    "Números: puede escribirlos como 1423500 o 1.423.500,00. Fechas: AAAA-MM-DD o DD/MM/AAAA.",
    "Los encabezados pueden estar en otro orden: la aplicación los reconoce por su nombre.",
]


def _encabezar(ws, titulos: list[str]) -> None:
    for j, t in enumerate(titulos, 1):
        c = ws.cell(1, j, t)
        c.font = Font(bold=True, color="FFFFFF")
        c.fill = PatternFill("solid", fgColor=AZUL)
        c.alignment = Alignment(horizontal="center", wrap_text=True)
        ws.column_dimensions[get_column_letter(j)].width = max(14, len(t) + 4)
    ws.freeze_panes = "A2"


def construir(demo: bool = False, caso: str = "") -> bytes:
    """Genera la plantilla de carga, vacía o con uno de los casos de ejemplo.

    `caso` puede ser "completo", "mediocre" o "basico" (ver `casos.py`).
    `demo=True` sin caso equivale a "completo", por compatibilidad.
    """
    datos_caso = casos.obtener(caso) if (caso or demo) else None
    demo = bool(datos_caso)
    meta = (datos_caso or {}).get("_meta", {})
    # La plantilla en blanco va VACÍA: antes venía con los datos reales de un
    # cliente, que acababan en el archivo de cualquier otro.
    emp = Empresa()
    wb = Workbook()
    ws = wb.active
    ws.title = "INSTRUCCIONES"
    for i, linea in enumerate(INSTRUCCIONES, 1):
        ws.cell(i, 1, linea).font = Font(bold=i == 1, size=13 if i == 1 else 11, color=AZUL if i == 1 else "000000")
    ws.column_dimensions["A"].width = 140
    if demo:
        fila_aviso = len(INSTRUCCIONES) + 2
        ws.cell(fila_aviso, 1, f"EJEMPLO: {meta.get('nombre', 'demostración')} — TODOS LOS DATOS SON FICTICIOS").font = Font(
            bold=True, size=12, color="C00000")
        ws.cell(fila_aviso + 1, 1, meta.get("descripcion", "")).font = Font(italic=True)

    ws = wb.create_sheet("EMPRESA")
    if datos_caso:
        d, h = meta.get("periodo", ("2025-01-01", "2025-01-31"))
        desde, hasta = date.fromisoformat(d), date.fromisoformat(h)
        razon = meta.get("empresa", "")
        nit = meta.get("nit", "")
    else:
        hoy = date.today()
        desde = hoy.replace(day=1)
        hasta = (desde + timedelta(days=32)).replace(day=1) - timedelta(days=1)
        razon, nit = "", ""
    datos = [("Razón social", razon), ("Sigla", emp.sigla), ("NIT", nit), ("Dirección", emp.direccion),
             ("Municipio", emp.municipio), ("Periodo desde", desde.isoformat()), ("Periodo hasta", hasta.isoformat()),
             ("Representante legal", emp.rep_legal), ("CC representante legal", emp.rep_legal_cc), ("Contador", emp.contador),
             ("CC contador", emp.contador_cc), ("Tarjeta profesional contador", emp.contador_tp),
             ("Grupo NIIF", emp.grupo_niif), ("Responsable de IVA", "SI" if emp.responsable_iva else "NO"),
             ("Tarifa renta", float(emp.tarifa_renta)), ("Capital suscrito", float(emp.capital_suscrito)), ("Demo", "SI" if demo else "NO")]
    _encabezar(ws, ["Campo", "Valor"])
    for i, (k, v) in enumerate(datos, 2):
        ws.cell(i, 1, k).font = Font(bold=True)
        ws.cell(i, 2, v)
    ws.column_dimensions["A"].width, ws.column_dimensions["B"].width = 32, 48

    ws_puc = wb.create_sheet("PUC")
    ws_puc.append(["Código", "Nombre"])
    lista = puc().listado()
    for c in lista:
        ws_puc.append([c["codigo"], c["nombre"]])
    ws_puc.column_dimensions["B"].width = 60
    ws_puc.sheet_state = "hidden"
    rango_puc = f"PUC!$A$2:$A${len(lista) + 1}"

    for nombre, titulos in HOJAS.items():
        h = wb.create_sheet(nombre)
        _encabezar(h, titulos)
        if nombre in ("MOVIMIENTOS", "AJUSTES", "SALDOS_INICIALES"):
            col = get_column_letter(titulos.index("Código PUC") + 1)
            dv = DataValidation(type="list", formula1=rango_puc, allow_blank=True, showErrorMessage=False)
            h.add_data_validation(dv)
            dv.add(f"{col}2:{col}5000")
        if nombre in ("MOVIMIENTOS", "AJUSTES"):
            dv = DataValidation(type="list", formula1='"Ingreso,Egreso,Nota,Compra,Venta"', allow_blank=True)
            h.add_data_validation(dv)
            dv.add("C2:C5000")
        if nombre == "INVENTARIO_MOVS":
            dv = DataValidation(type="list", formula1='"Inventario inicial,Compra,Venta,Devolución compra,Devolución venta,Ajuste"', allow_blank=True)
            h.add_data_validation(dv)
            dv.add("H2:H5000")
        if nombre == "NOMINA":
            dv = DataValidation(type="list", formula1='"SI,NO,AUTO"', allow_blank=True)
            h.add_data_validation(dv)
            dv.add("I2:I500")
        if datos_caso:
            for fila in datos_caso.get(nombre, []):
                h.append(list(fila))
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


# ---------------------------------------------------------------- datos de demostración (enero 2025)
_PROV = ("900111222-3", "Distribuidora Naturista Demo S.A.S.")
DEMO = {
    "SALDOS_INICIALES": [
        ("110505", "Caja general", 1500000, None), ("111005", "Bancos", 20000000, None),
        ("1435", "Mercancías no fabricadas por la empresa", 6500000, None), ("152405", "Muebles y enseres", 2000000, None),
        ("3105", "Capital suscrito y pagado", None, 30000000),
    ],
    "MOVIMIENTOS": [
        ("2025-01-05", "CE-001", "Egreso", "5120", "Arrendamientos", "", "Arrendador local (demo)", "Arriendo local enero", 1200000, None, None),
        ("2025-01-05", "CE-001", "Egreso", "111005", "Bancos", "", "", "Pago arriendo enero", None, 1200000, None),
        ("2025-01-08", "FC-001", "Compra", "1435", "Mercancías", *_PROV, "Compra mercancía P001 y P005", 1600000, None, None),
        ("2025-01-08", "FC-001", "Compra", "240810", "IVA descontable", *_PROV, "IVA 19 % compra", 304000, None, None),
        ("2025-01-08", "FC-001", "Compra", "2205", "Proveedores nacionales", *_PROV, "Factura a crédito", None, 1904000, None),
        ("2025-01-10", "CE-002", "Egreso", "5135", "Servicios", "", "Empresa de servicios públicos (demo)", "Energía y agua", 180000, None, None),
        ("2025-01-10", "CE-002", "Egreso", "110505", "Caja general", "", "", "Pago servicios", None, 180000, None),
        ("2025-01-15", "RC-001", "Venta", "110505", "Caja general", "", "Clientes varios", "Ventas de contado 1 al 15", 6188000, None, None),
        ("2025-01-15", "RC-001", "Venta", "4135", "Comercio al por mayor y al por menor", "", "Clientes varios", "Ventas 1 al 15", None, 5200000, None),
        ("2025-01-15", "RC-001", "Venta", "240805", "IVA generado", "", "Clientes varios", "IVA 19 % ventas", None, 988000, None),
        ("2025-01-20", "FC-002", "Compra", "1435", "Mercancías", *_PROV, "Compra mercancía P002", 960000, None, None),
        ("2025-01-20", "FC-002", "Compra", "240810", "IVA descontable", *_PROV, "IVA 19 % compra", 182400, None, None),
        ("2025-01-20", "FC-002", "Compra", "111005", "Bancos", *_PROV, "Pago de contado", None, 1142400, None),
        ("2025-01-25", "CE-003", "Egreso", "519530", "Útiles, papelería y fotocopias", "", "Papelería (demo)", "Papelería", 85000, None, None),
        ("2025-01-25", "CE-003", "Egreso", "110505", "Caja general", "", "", "Pago papelería", None, 85000, None),
        ("2025-01-31", "RC-002", "Venta", "110505", "Caja general", "", "Clientes varios", "Ventas de contado 16 al 31", 6902000, None, None),
        ("2025-01-31", "RC-002", "Venta", "4135", "Comercio al por mayor y al por menor", "", "Clientes varios", "Ventas 16 al 31", None, 5800000, None),
        ("2025-01-31", "RC-002", "Venta", "240805", "IVA generado", "", "Clientes varios", "IVA 19 % ventas", None, 1102000, None),
        ("2025-01-31", "CE-004", "Egreso", "5110", "Honorarios", "900000001-2", "ASESORÍA CONTABLE EJEMPLO (demo)", "Asesoría contable y tributaria enero", 300000, None, 300000),
        ("2025-01-31", "CE-004", "Egreso", "236515", "Retención honorarios", "900000001-2", "ASESORÍA CONTABLE EJEMPLO (demo)", "Retención en la fuente 10 % (demo)", None, 30000, 300000),
        ("2025-01-31", "CE-004", "Egreso", "111005", "Bancos", "900000001-2", "ASESORÍA CONTABLE EJEMPLO (demo)", "Pago honorarios", None, 270000, None),
        ("2025-01-31", "NC-001", "Nota", "111005", "Bancos", "", "", "Consignación del efectivo", 5000000, None, None),
        ("2025-01-31", "NC-001", "Nota", "110505", "Caja general", "", "", "Consignación del efectivo", None, 5000000, None),
        ("2025-01-31", "NC-002", "Nota", "530505", "Gastos bancarios", "", "Banco (demo)", "Comisiones bancarias", 15000, None, None),
        ("2025-01-31", "NC-002", "Nota", "111005", "Bancos", "", "Banco (demo)", "Comisiones bancarias", None, 15000, None),
    ],
    "INVENTARIO_MOVS": [
        ("2024-12-31", "SI", "P001", "Moringa cápsulas x60 (demo)", "Laboratorio Demo", "M-2401", "2026-06-30", "Inventario inicial", 100, 18000, None),
        ("2024-12-31", "SI", "P002", "Omega 3 x100 cápsulas (demo)", "Laboratorio Demo", "O-2402", "2025-03-15", "Inventario inicial", 80, 25000, None),
        ("2024-12-31", "SI", "P003", "Aceite de coco 500 ml (demo)", "Laboratorio Demo", "C-2310", "2025-01-20", "Inventario inicial", 20, 15000, None),
        ("2024-12-31", "SI", "P003", "Aceite de coco 500 ml (demo)", "Laboratorio Demo", "C-2412", "2026-01-31", "Inventario inicial", 40, 15000, None),
        ("2024-12-31", "SI", "P004", "Gel de sábila 250 g (demo)", "Laboratorio Demo", "S-2404", "2025-04-10", "Inventario inicial", 90, 10000, None),
        ("2024-12-31", "SI", "P005", "Té verde x20 sobres (demo)", "Laboratorio Demo", "T-2411", "2027-02-28", "Inventario inicial", 150, 6000, None),
        ("2025-01-08", "FC-001", "P001", "Moringa cápsulas x60 (demo)", "Laboratorio Demo", "M-2501", "2027-01-31", "Compra", 50, 19000, None),
        ("2025-01-08", "FC-001", "P005", "Té verde x20 sobres (demo)", "Laboratorio Demo", "T-2501", "2027-06-30", "Compra", 100, 6500, None),
        ("2025-01-15", "RC-001", "P001", "Moringa cápsulas x60 (demo)", "", "", None, "Venta", 40, None, 45000),
        ("2025-01-15", "RC-001", "P002", "Omega 3 x100 cápsulas (demo)", "", "", None, "Venta", 30, None, 60000),
        ("2025-01-15", "RC-001", "P004", "Gel de sábila 250 g (demo)", "", "", None, "Venta", 20, None, 28000),
        ("2025-01-15", "RC-001", "P005", "Té verde x20 sobres (demo)", "", "", None, "Venta", 60, None, 14000),
        ("2025-01-20", "FC-002", "P002", "Omega 3 x100 cápsulas (demo)", "Laboratorio Demo", "O-2501", "2026-12-31", "Compra", 40, 24000, None),
        ("2025-01-31", "RC-002", "P001", "Moringa cápsulas x60 (demo)", "", "", None, "Venta", 30, None, 45000),
        ("2025-01-31", "RC-002", "P002", "Omega 3 x100 cápsulas (demo)", "", "", None, "Venta", 30, None, 60000),
        ("2025-01-31", "RC-002", "P003", "Aceite de coco 500 ml (demo)", "", "C-2412", None, "Venta", 25, None, 38000),
        ("2025-01-31", "RC-002", "P004", "Gel de sábila 250 g (demo)", "", "", None, "Venta", 20, None, 28000),
        ("2025-01-31", "RC-002", "P005", "Té verde x20 sobres (demo)", "", "", None, "Venta", 60, None, 14000),
    ],
    "INVENTARIO_FISICO": [("P001", 80, "2025-01-31"), ("P002", 58, "2025-01-31"), ("P003", 35, "2025-01-31"),
                          ("P004", 50, "2025-01-31"), ("P005", 131, "2025-01-31")],
    "ACTIVOS_FIJOS": [("Muebles y estantería de exhibición (demo)", "152405", "2024-12-20", 2000000, 120, 0, "Línea recta")],
    "NOMINA": [("2025-01-01", "LAURA PATRICIA GOMEZ RUIZ (demo)", "1000000003", "Representante legal / administradora", 1423500, None, None, 30,
                "SI", 0, 0, 1)],
}
