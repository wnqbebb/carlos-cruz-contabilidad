"""Reportes de la DIAN FICTICIOS para pruebas, demostración y recorridos (rescate).

Todo es inventado: nombres, NIT (con dígito de verificación válido), CUFE y cifras. Las columnas
siguen el Excel que exporta el portal de facturación de la DIAN (ver
`app/importadores/facturas_dian.py`, donde están las fuentes).

    python -m demo.dian_ficticio            # escribe los archivos en docs/demo/dian/

Cifras calculadas a mano (las pruebas las comparan):
  Emitidas  · base 3.300.000 · IVA 532.000 · 4 documentos válidos (3 facturas y 1 nota crédito)
  Recibidas · base 1.250.000 · IVA 152.000 · 3 documentos (2 facturas y 1 documento soporte)
  Fuera     · 1 repetido (mismo CUFE) y 1 rechazado
"""
from __future__ import annotations

import hashlib
import io
from pathlib import Path

from openpyxl import Workbook

from app.utils.nit import digito_verificacion

RAIZ = Path(__file__).resolve().parents[2]
SALIDA = RAIZ / "docs" / "demo" / "dian"

ENCABEZADOS = ["Tipo de documento", "CUFE/CUDE", "Folio", "Prefijo", "Divisa", "Forma de Pago", "Medio de Pago",
               "Fecha Emisión", "Fecha Recepción", "NIT Emisor", "Nombre Emisor", "NIT Receptor", "Nombre Receptor",
               "IVA", "ICA", "IC", "INC", "Timbre", "INC Bolsas", "IN Carbono", "IN Combustibles", "IC Datos", "ICL",
               "INPP", "IBUA", "ICUI", "Rete IVA", "Rete Renta", "Rete ICA", "Total", "Estado", "Grupo"]

CLIENTE = {"nit": "901234567", "razon_social": "DROGUERÍA SAN ROQUE S.A.S."}
CLIENTE["dv"] = digito_verificacion(CLIENTE["nit"])
TERCEROS = {
    "cli1": ("900111222", "CLÍNICA LOS ÁLAMOS S.A.S."),
    "cli2": ("1112223334", "MARTA LUCÍA PÉREZ"),
    "pro1": ("800333444", "DISTRIBUIDORA FARMA DEL VALLE S.A.S."),
    "pro2": ("890555666", "LABORATORIOS NATURA LTDA."),
    "pro3": ("16777888", "JOSÉ ARMANDO CRUZ"),          # no obligado a facturar → documento soporte
}


def _cufe(*partes) -> str:
    return hashlib.sha384("|".join(str(p) for p in partes).encode()).hexdigest()


def _fila(tipo, prefijo, folio, fecha, emisor, receptor, *, iva=0, total, forma="Crédito", rete_iva=0, rete_renta=0,
          rete_ica=0, estado="Aprobado", grupo="Emitido", cufe=None) -> list:
    fila = {k: "" for k in ENCABEZADOS}
    fila.update({
        "Tipo de documento": tipo, "CUFE/CUDE": cufe or _cufe(tipo, prefijo, folio, emisor[0]), "Folio": folio,
        "Prefijo": prefijo, "Divisa": "COP", "Forma de Pago": forma,
        "Medio de Pago": "Efectivo" if forma == "Contado" else "Instrumento no definido",
        "Fecha Emisión": fecha, "Fecha Recepción": fecha, "NIT Emisor": emisor[0], "Nombre Emisor": emisor[1],
        "NIT Receptor": receptor[0], "Nombre Receptor": receptor[1], "IVA": iva, "Rete IVA": rete_iva,
        "Rete Renta": rete_renta, "Rete ICA": rete_ica, "Total": total, "Estado": estado, "Grupo": grupo,
    })
    for k in ("ICA", "IC", "INC", "Timbre", "INC Bolsas", "IN Carbono", "IN Combustibles", "IC Datos", "ICL", "INPP",
              "IBUA", "ICUI"):
        fila[k] = 0
    return [fila[k] for k in ENCABEZADOS]


def emitidas() -> list[list]:
    yo = (CLIENTE["nit"], CLIENTE["razon_social"])
    c1, c2 = TERCEROS["cli1"], TERCEROS["cli2"]
    filas = [
        _fila("Factura electrónica", "SR", 1001, "15-01-2025", yo, c2, iva=190000, total=1190000, forma="Contado"),
        _fila("Factura electrónica", "SR", 1002, "20-01-2025", yo, c1, iva=380000, total=2380000,
              rete_iva=57000, rete_renta=50000),
        _fila("Factura electrónica", "SR", 1003, "25-01-2025", yo, c2, total=500000, forma="Contado"),
        _fila("Nota crédito electrónica", "NCSR", 15, "28-01-2025", yo, c1, iva=38000, total=238000),
        _fila("Factura electrónica", "SR", 1004, "29-01-2025", yo, c1, iva=19000, total=119000, estado="Rechazado"),
    ]
    filas.append(list(filas[1]))   # el portal a veces repite un documento: mismo CUFE
    return filas


def recibidas() -> list[list]:
    yo = (CLIENTE["nit"], CLIENTE["razon_social"])
    p1, p2, p3 = TERCEROS["pro1"], TERCEROS["pro2"], TERCEROS["pro3"]
    return [
        _fila("Factura electrónica", "FDV", 55871, "10-01-2025", p1, yo, iva=152000, total=952000, rete_renta=20000,
              grupo="Recibido"),
        _fila("Factura electrónica", "LN", 3302, "18-01-2025", p2, yo, total=300000, forma="Contado", grupo="Recibido"),
        # El documento soporte lo emite el comprador (nuestro cliente) al proveedor no obligado.
        _fila("Documento soporte con no obligados", "DS", 12, "22-01-2025", yo, p3, total=150000, forma="Contado",
              grupo="Emitido"),
    ]


def libro(filas: list[list], hoja: str = "Documentos") -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = hoja
    ws.append(ENCABEZADOS)
    for f in filas:
        ws.append(f)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def archivos() -> dict[str, bytes]:
    return {
        "facturas_emitidas_enero_2025.xlsx": libro(emitidas()),
        "facturas_recibidas_enero_2025.xlsx": libro(recibidas()),
        "facturas_todas_enero_2025.xlsx": libro(emitidas() + recibidas()),
    }


def main() -> None:
    SALIDA.mkdir(parents=True, exist_ok=True)
    for nombre, datos in archivos().items():
        (SALIDA / nombre).write_bytes(datos)
        print("escrito", SALIDA / nombre)


if __name__ == "__main__":
    main()
