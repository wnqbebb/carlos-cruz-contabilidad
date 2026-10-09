"""Declaración de renta de punta a punta por la API (v2.3 · Fase 5), con el caso A anonimizado."""
import io
import json
from datetime import date
from decimal import Decimal as D
from pathlib import Path

from openpyxl import Workbook, load_workbook

from app.renta.lectura import interpretar_filas, validar_sumas

CASO_A = json.loads((Path(__file__).parent / "renta" / "caso_a.json").read_text(encoding="utf-8"))


def excel_exogena(caso: dict) -> bytes:
    """El reporte de exógena del caso como lo descarga el portal (Excel)."""
    wb = Workbook()
    ws = wb.active
    d = caso["documento"]
    ws.append(["Tipo de documento:", d["tipo"]])
    ws.append(["Identificación:", d["numero"]])
    ws.append(["Nombres / Razón social:", d["nombre"]])
    nombres = {1: "Ingresos", 2: "Patrimonio", 3: "Consumo TC", 4: "Movimiento", 5: "Compras"}
    for n, v in caso["topes"].items():
        ws.append(["", "", f"Tope {n} - {nombres[int(n)]}", int(v), ""])
    for l in caso["lineas"]:
        ws.append([l["entidad"], l["titular"], l["detalle"], int(l["valor"]), l["uso"]])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _cliente_natural(api, nit="10000001", nombre="CONTRIBUYENTE A"):
    r = api.post("/api/clientes", json={"nit": nit, "razon_social": nombre, "tipo_persona": "natural",
                                       "regimen": "no_responsable_iva"})
    assert r.status_code in (200, 201), r.text
    return r.json()["id"]


def _subir(api, cid, nombre="exogena.xlsx", contenido=None):
    contenido = contenido or excel_exogena(CASO_A)
    r = api.post(f"/api/renta/{cid}/2025/documentos", files=[("archivos", (nombre, contenido, "application/octet-stream"))])
    assert r.status_code == 200, r.text
    return r.json()


def test_caso_a_de_punta_a_punta(cliente_api):
    cid = _cliente_natural(cliente_api)
    v = _subir(cliente_api, cid)
    res = v["resultado"]
    assert v["estado"] == "borrador"
    assert len(res["lineas"]) == 23
    # Obligada solo por el Tope 4 (consignaciones).
    assert res["obligacion"]["obligado"]
    assert [m["tope"] for m in res["obligacion"]["motivos"] if m["supera"]] == ["consignaciones"]
    # Las sumas: todo cuadra; el Tope 4 trae 3 pesos de diferencia de la propia fuente.
    estados = {x["tope"]: x["estado"] for x in res["validacion"]}
    assert estados[2] == "cuadra" and estados[3] == "cuadra" and estados[4] == "redondeo"
    # Las 2 líneas «NO REGISTRA NO» quedan marcadas y hay pregunta para ellas.
    assert sum(1 for l in res["lineas"] if l["no_titular"]) == 2
    assert any(q["id"] == "no_titular" for q in res["preguntas"])
    assert len(res["preguntas"]) <= 5
    # Aviso: consignaciones (≈ 93 M) muy por encima de la facturación electrónica (≈ 4,8 M).
    assert any("consignaciones" in m["texto"].lower() and "facturación electrónica" in m["texto"] for m in res["marcas"])

    # Lo que agregó el contador por conocer el negocio.
    for categoria, valor in (("ingreso_no_laboral", "65400000"), ("costo_no_laboral", "32800000")):
        r = cliente_api.post(f"/api/renta/{cid}/2025/cambio",
                             json={"tipo": "agregar", "categoria": categoria, "valor": valor, "descripcion": "Negocio"})
        assert r.status_code == 200, r.text
    # La app propone el máximo legal del 1 % y deja ajustarlo: el contador declaró 48.000.
    r = cliente_api.post(f"/api/renta/{cid}/2025/cambio",
                         json={"tipo": "beneficio", "id": "compras_fe", "valor": True, "uno_por_ciento": "48000"})
    res = r.json()["resultado"]
    assert D(res["maximo_1pct"]) == D("78000")
    casillas = {c["casilla"]: D(c["optimizada"]) for c in res["casillas"]}
    for n, valor in CASO_A["esperado_210"].items():
        assert casillas[int(n)] == D(valor), f"casilla {n}: {casillas[int(n)]} ≠ {valor}"
    assert D(res["cifras"]["a_favor"]) == D("5000")


def test_reclasificar_y_excluir_recalculan(cliente_api):
    cid = _cliente_natural(cliente_api)
    res = _subir(cliente_api, cid)["resultado"]
    deuda = next(l for l in res["lineas"] if l["categoria"] == "deuda")
    r = cliente_api.post(f"/api/renta/{cid}/2025/cambio", json={"tipo": "excluir", "linea": deuda["id"]})
    casillas = {c["casilla"]: D(c["optimizada"]) for c in r.json()["resultado"]["casillas"]}
    # 52.201.487 − 22.900 (la primera deuda) = 52.178.587 → 52.179.000
    assert deuda["valor"] == "22900" and casillas[30] == D("52179000")
    r = cliente_api.post(f"/api/renta/{cid}/2025/cambio", json={"tipo": "reclasificar", "linea": deuda["id"],
                                                                 "categoria": "informativo"})
    assert r.status_code == 200
    r = cliente_api.post(f"/api/renta/{cid}/2025/cambio", json={"tipo": "reclasificar", "linea": deuda["id"],
                                                                 "categoria": "no_existe"})
    assert r.status_code == 422


def test_persona_juridica_no_aplica(cliente_api):
    cid = cliente_api.post("/api/clientes", json={"nit": "900123456", "razon_social": "EMPRESA S.A.S."}).json()["id"]
    r = cliente_api.get(f"/api/renta/{cid}/2025")
    assert r.status_code == 409
    assert "110" in r.json()["detail"]["mensaje"]


def test_descargas(cliente_api):
    cid = _cliente_natural(cliente_api)
    _subir(cliente_api, cid)
    pdf = cliente_api.get(f"/api/renta/{cid}/2025/descargar/pdf")
    assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF")
    resumen = cliente_api.get(f"/api/renta/{cid}/2025/descargar/resumen")
    assert resumen.status_code == 200 and resumen.content.startswith(b"%PDF")
    xls = cliente_api.get(f"/api/renta/{cid}/2025/descargar/excel")
    assert xls.status_code == 200
    wb = load_workbook(io.BytesIO(xls.content))
    assert wb.sheetnames == ["Formulario 210", "Líneas del reporte", "De dónde sale cada peso", "Avisos"]
    ws = wb["Formulario 210"]
    assert ws["A1"].value.endswith("BORRADOR")
    # Ninguna celda de texto empieza por «=»: no hay inyección de fórmulas.
    for hoja in wb.worksheets:
        for fila in hoja.iter_rows(values_only=True):
            assert not any(isinstance(c, str) and c.startswith("=") for c in fila)


def test_marcar_presentada_y_cartera(cliente_api):
    cid = _cliente_natural(cliente_api)
    _subir(cliente_api, cid)
    r = cliente_api.post(f"/api/renta/{cid}/2025/estado", json={"estado": "presentada"})
    assert r.status_code == 422
    r = cliente_api.post(f"/api/renta/{cid}/2025/estado",
                         json={"estado": "presentada", "numero": "2118000000001", "fecha": "2026-09-07"})
    assert r.status_code == 200 and r.json()["estado"] == "presentada"
    c = cliente_api.get("/api/renta/cartera?anio=2025").json()
    fila = next(x for x in c["declaraciones"] if x["cliente_id"] == cid)
    assert fila["estado"] == "presentada" and fila["obligado"] is True


def test_tarea_en_el_tablero_si_vence(cliente_api):
    from app.inteligencia import tablero

    cid = _cliente_natural(cliente_api, nit="10000020", nombre="CONTRIBUYENTE VENCIDO")   # 19-20 → 26 de agosto
    t = tablero.armar(date(2026, 10, 8))
    tarea = next(x for x in t["tareas"] if x["codigo"] == "RENTA_VENCE" and x["cliente_id"] == cid)
    assert tarea["prioridad"] == "critica" and "hace 43 días" in tarea["titulo"]
    assert tarea["accion"]["ruta"] == f"/clientes/{cid}?seccion=renta"
    # Lejos del vencimiento no hay tarea.
    t = tablero.armar(date(2026, 7, 1))
    assert not any(x["codigo"] == "RENTA_VENCE" and x["cliente_id"] == cid for x in t["tareas"])


def test_sin_sesion_no_hay_renta(cliente_sin_sesion):
    assert cliente_sin_sesion.get("/api/renta/cartera").status_code == 401


def test_lectura_ruidosa_se_corrige_con_los_topes():
    """Errores típicos del OCR («$» leído como «5») se resuelven cuadrando con el encabezado."""
    filas = [["", "", "Tope 3 - Consumo TC", "$14,536,332.00", ""],
             ["", "", "Tope 5 - Compras", "$57,763,109.00", ""],
             ["BANCO A", "CONTRIBUYENTE A", "Total consumos o gastos con tarjeta", "$ 1,170,568.00", "Tope 3: Consumos TC"],
             ["COMPAÑIA", "CONTRIBUYENTE A", "Total consumos o gastos con tarjeta", "54,932,351.00", "Tope 3: Consumos TC"],
             ["BANCO A", "CONTRIBUYENTE A", "Total consumos o gastos con tarjeta", "$ 8,413,792.00", "Tope 3: Consumos TC"],
             ["BANCO A", "CONTRIBUYENTE A", "Total consumos o gastos con tarjeta", "$ 19,621.00", "Tope 3: Consumos TC"],
             ["DIAN", "CONTRIBUYENTE A", "Suma valor total facturas tras ajustes por notas", "$ 7,763,109.00",
              "Tope 5: Compras registradas"]]
    rep = interpretar_filas(filas, documento="foto.jpg")
    assert rep.topes[5] == "57763109"
    val = {v["tope"]: v for v in validar_sumas(rep)}
    assert val[3]["estado"] == "corregida" and val[5]["estado"] == "corregida"
    assert rep.topes[5] == "7763109"
    corregida = next(l for l in rep.lineas if l.corregida)
    assert corregida.valor == "4932351" and "54932351" in corregida.alternativas


def test_un_boton_descarga_los_tres(cliente_api):
    import zipfile

    cid = _cliente_natural(cliente_api)
    _subir(cliente_api, cid)
    r = cliente_api.get(f"/api/renta/{cid}/2025/descargar/todo")
    assert r.status_code == 200
    nombres = zipfile.ZipFile(io.BytesIO(r.content)).namelist()
    assert len(nombres) == 3 and any(n.endswith("borrador-210.pdf") for n in nombres)
