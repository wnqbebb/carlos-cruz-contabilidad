"""Facturas electrónicas de la DIAN (emitidas y recibidas): se reconocen solas y cuadran (rescate).

Datos 100 % ficticios: `demo/dian_ficticio.py`. Cifras calculadas a mano en ese archivo.
"""
from __future__ import annotations

from collections import defaultdict
from decimal import Decimal

from demo import dian_ficticio as F
from app.importadores import facturas_dian as FE
from app.importadores.lector import leer_archivo
from app.modelos import Empresa

D = Decimal


def _det(nombre: str, datos: bytes, nit: str = F.CLIENTE["nit"]):
    hoja = leer_archivo(datos, nombre)[0]
    pos = FE.detectar(hoja)
    assert pos is not None, "no reconoció el reporte de la DIAN"
    return FE.importar(hoja, pos, "0-0", Empresa(nit=nit))


def _saldos(det) -> dict[str, Decimal]:
    s = defaultdict(Decimal)
    for m in det.paquete.movimientos:
        s[m.cuenta] += m.debito - m.credito
    return s


def test_todas_juntas_cifras_a_mano():
    det = _det("facturas_todas.xlsx", F.libro(F.emitidas() + F.recibidas()))
    r = det.resumen
    assert (r["emitidas"], r["recibidas"]) == (4, 3)
    assert r["ventas_base"] == D("3300000") and r["ventas_iva"] == D("532000")
    assert r["compras_base"] == D("1250000") and r["compras_iva"] == D("152000")
    s = _saldos(det)
    assert s["413595"] == D("-3500000")            # ventas brutas
    assert s["417505"] == D("200000")              # devolución por la nota crédito
    assert s["240805"] == D("-532000")             # IVA generado neto
    assert s["240810"] == D("152000")              # IVA descontable
    assert s["135515"] == D("50000") and s["135517"] == D("57000")
    assert s["143501"] == D("1250000")
    assert s["236540"] == D("-20000")
    # Cartera: 2.380.000 − 107.000 de retenciones − 238.000 de la nota crédito
    assert s["130505"] == D("2035000")
    assert s["110505"] == D("1690000") - D("450000")   # cobros de contado − pagos de contado
    assert s["220505"] == D("-932000")
    # Partida doble documento por documento
    por = defaultdict(Decimal)
    for m in det.paquete.movimientos:
        por[m.comprobante] += m.debito - m.credito
    assert all(v == 0 for v in por.values()), por
    assert all(m.debito >= 0 and m.credito >= 0 for m in det.paquete.movimientos)
    motivos = " ".join(f["motivo"] for f in det.paquete.filas_ignoradas)
    assert "rechazado" in motivos and "repetido" in motivos


def test_sin_columna_grupo_usa_el_nit_del_cliente():
    filas = [f[:-1] for f in F.emitidas() + F.recibidas()]
    hoja = leer_archivo(_sin_grupo(filas), "sin_grupo.xlsx")[0]
    pos = FE.detectar(hoja)
    det = FE.importar(hoja, pos, "0-0", Empresa(nit=f"{F.CLIENTE['nit']}-{F.CLIENTE['dv']}"))
    assert (det.resumen["emitidas"], det.resumen["recibidas"]) == (4, 3)
    # Y sin saber el NIT del cliente: el que se repite en todo el archivo.
    det2 = FE.importar(hoja, pos, "0-0", Empresa())
    assert det2.resumen["dueno"] == F.CLIENTE["nit"] and det2.resumen["emitidas"] == 4
    assert any(a.codigo == "FE-DUENO" for a in det2.paquete.alertas)


def _sin_grupo(filas) -> bytes:
    import io

    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    ws.append(F.ENCABEZADOS[:-1])
    for f in filas:
        ws.append(f)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def test_un_documento_de_otro_contribuyente_se_deja_fuera():
    ajena = F._fila("Factura electrónica", "X", 1, "05-01-2025", ("800999111", "OTRA SAS"), ("700111222", "TERCERO"),
                    total=100000)
    hoja = leer_archivo(_sin_grupo([f[:-1] for f in F.emitidas()] + [ajena[:-1]]), "x.xlsx")[0]
    det = FE.importar(hoja, FE.detectar(hoja), "0-0", Empresa(nit=F.CLIENTE["nit"]))
    assert det.resumen["emitidas"] == 4
    assert any(a.codigo == "FE-AJENO" for a in det.paquete.alertas)


def test_subir_calcular_y_cuadrar_por_la_api(cliente_api):
    """Recorrido simple: subir el Excel del portal → la app lo reconoce → calcula y cuadra."""
    datos = F.archivos()["facturas_todas_enero_2025.xlsx"]
    p = cliente_api.post("/api/subir", files=[("archivos", ("facturas_todas_enero_2025.xlsx", datos))]).json()
    assert p["clase"] == "contabilidad", p
    c = cliente_api.post(f"/api/subir/{p['subida_id']}/confirmar", json={
        "crear": {"nit": F.CLIENTE["nit"], "razon_social": F.CLIENTE["razon_social"]}}).json()
    hojas = c["hojas"]
    assert any(h["formato"] == "facturas_dian" for h in hojas), hojas
    peticion = {"sesion_id": c["sesion_id"], "cliente_id": c["cliente_id"],
                "mapeo": {m["normalizado"]: m["codigo"] for m in c["mapeo"] if m.get("codigo")}}
    r = cliente_api.post("/api/calcular", json=peticion)
    assert r.status_code == 200, r.text
    res = r.json()
    assert res["guardado"] is True
    assert D(res["resumen"]["descuadre_esf"]) == 0
    assert D(res["resumen"]["ingresos"]) == D("3300000")
    assert res["periodo"]["desde"] == "2025-01-01" and res["periodo"]["hasta"] == "2025-01-31"


def test_la_subida_sabe_de_quien_es_el_reporte(cliente_api):
    """J2: el Excel de la DIAN trae el NIT del dueño en todos los documentos: no hay que digitarlo."""
    datos = F.archivos()["facturas_todas_enero_2025.xlsx"]
    p = cliente_api.post("/api/subir", files=[("archivos", ("facturas_todas_enero_2025.xlsx", datos))]).json()
    campos = p["identidad"]["campos"]
    assert campos["nit"]["valor"] == F.CLIENTE["nit"]
    assert campos["razon_social"]["valor"] == F.CLIENTE["razon_social"]
