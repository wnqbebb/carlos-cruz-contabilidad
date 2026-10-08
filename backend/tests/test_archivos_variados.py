"""Banco de archivos variados: registros auxiliares, libro diario, balances, PDF y Word (spec v2.2 · 4.5).

Prueba ciega: la aplicación no conoce el archivo real del cliente, así que se
prueba con archivos desordenados a propósito (`archivos_variados/generar.py`).
Las cifras esperadas están calculadas A MANO en cada prueba, con la cuenta
escrita al lado: si el motor se equivoca, la prueba lo atrapa.

Todo pasa por la API, como lo haría el contador: subir → confirmar (crea el
cliente) → responder preguntas → calcular.
"""
from __future__ import annotations

from collections import defaultdict
from decimal import Decimal
from pathlib import Path

import pytest

from app.utils import nit as unit

D = Decimal
BANCO = Path(__file__).resolve().parent / "archivos_variados"
_nits = iter(range(900_100_001, 900_199_999))


@pytest.fixture(scope="module", autouse=True)
def _banco():
    """Los archivos se regeneran si faltan, así la prueba no depende de nada externo."""
    from tests.archivos_variados import generar

    if not all((BANCO / n).exists() for n in generar.ARCHIVOS):
        generar.generar()


def _subir(api, *nombres: str, crear: bool = True) -> dict:
    archivos = [("archivos", (n, (BANCO / n).read_bytes())) for n in nombres]
    r = api.post("/api/subir", files=archivos)
    assert r.status_code == 200, r.text
    p = r.json()
    cuerpo = {}
    if crear and not p.get("cliente"):
        nit = str(next(_nits))
        cuerpo["crear"] = {
            "nit": p["identidad"]["campos"].get("nit", {}).get("valor") or nit,
            "razon_social": p["identidad"]["campos"].get("razon_social", {}).get("valor") or f"CLIENTE PRUEBA {nit}",
        }
    c = api.post(f"/api/subir/{p['subida_id']}/confirmar", json=cuerpo)
    assert c.status_code == 200, c.text
    return {**c.json(), "propuesta": p}


def _calcular(api, imp: dict, respuestas: dict | None = None, periodizacion: str = "unico", **extra) -> dict:
    mapeo = {m["normalizado"]: m["codigo"] for m in imp["mapeo"] if m.get("codigo")}
    peticion = {
        "sesion_id": imp["sesion_id"], "cliente_id": imp["cliente_id"], "mapeo": mapeo, "incluir": {},
        "decisiones": {}, "config": {}, "empresa": {}, "respuestas": respuestas or {},
        "periodizacion": periodizacion, **extra,
    }
    r = api.post("/api/calcular", json=peticion)
    assert r.status_code == 200, r.text
    return r.json()


def _r(res: dict, campo: str) -> Decimal:
    return D(res["resumen"][campo])


def _comprobantes_cuadran(api, cliente_id: str) -> dict[str, tuple[Decimal, Decimal]]:
    """Partida doble comprobante por comprobante, leyendo el libro diario guardado."""
    movs = api.get(f"/api/clientes/{cliente_id}/movimientos?por_pagina=2000").json()["movimientos"]
    suma: dict[str, list[Decimal]] = defaultdict(lambda: [D(0), D(0)])
    for m in movs:
        suma[m["comprobante"]][0] += D(m["debito"])
        suma[m["comprobante"]][1] += D(m["credito"])
    for comp, (d, c) in suma.items():
        assert d == c, f"{comp}: débitos {d} ≠ créditos {c}"
    return {k: (v[0], v[1]) for k, v in suma.items()}


def _alertas(res: dict, codigo: str) -> list[dict]:
    return [a for a in res["alertas"] if a["codigo"] == codigo]


# 1 ─ listas mensuales en bloques ─────────────────────────────────────────────
def test_01_ventas_y_compras_en_bloques_un_solo_periodo(cliente_api):
    imp = _subir(cliente_api, "01_ventas_compras_bloques.xlsx")
    assert imp["periodo_sugerido"]["desde"] == "2026-01-01" and imp["periodo_sugerido"]["hasta"] == "2026-02-28"
    assert imp["periodizacion"]["posible"] and imp["periodizacion"]["defecto"] == "por_periodo"
    res = _calcular(cliente_api, imp)
    # Ventas: 30.000 + 40.000 (enero) + 45.000 (febrero, con encabezados en otro orden) = 115.000
    assert _r(res, "ingresos") == D("115000")
    # Costo promedio: arroz 10×2.000 + 15×2.000 = 50.000; fríjol 5×5.000 = 25.000
    assert _r(res, "costo_ventas") == D("75000")
    assert _r(res, "utilidad_neta") == D("40000")
    # Inventario final: arroz 15×2.000 + fríjol 5×5.000 = 55.000; caja 115.000 − 130.000 = −15.000
    assert _r(res, "inventario_final") == D("55000")
    assert _r(res, "efectivo") == D("-15000")
    assert res["resumen"]["esf_cuadra"] and res["resumen"]["bp_cuadra"]
    comps = _comprobantes_cuadran(cliente_api, imp["cliente_id"])
    assert {"VTA-0001", "VTA-0002", "VTA-0003", "CMP-0001", "CMP-0002"} <= set(comps)


def test_01_mes_a_mes_cierra_cada_mes_y_abre_el_siguiente(cliente_api):
    imp = _subir(cliente_api, "01_ventas_compras_bloques.xlsx")
    res = _calcular(cliente_api, imp, periodizacion="por_periodo")
    periodos = res["periodos_procesados"]
    assert [(p["desde"], p["estado"]) for p in periodos] == [("2026-01-01", "cerrado"), ("2026-02-01", "calculado")]
    # Enero: ventas 70.000 − costo (20.000 + 25.000) = 25.000. Febrero: 45.000 − 30.000 = 15.000.
    assert [D(p["utilidad"]) for p in periodos] == [D("25000"), D("15000")]
    # Febrero abre con lo que dejó enero: caja −60.000 (70.000 − 130.000) y termina en −15.000.
    assert _r(res, "efectivo") == D("-15000") and _r(res, "inventario_final") == D("55000")
    # El kardex de febrero arranca con el saldo de enero: no hay ajuste de costo.
    assert not [a for a in res["ajustes"] if a["id"] == "inventario_costo"]


# 2 ─ columnas mal rotuladas ──────────────────────────────────────────────────
def test_02_columnas_mal_rotuladas_se_interpretan_por_comportamiento(cliente_api):
    imp = _subir(cliente_api, "02_columnas_mal_rotuladas.xlsx")
    avisos = [a["mensaje"] for h in imp["hojas"] for a in h["alertas"] if a["codigo"] == "AUX-COLUMNAS"]
    assert any("«REFERENCIA» como cantidad" in m for m in avisos)          # total = referencia × precio
    assert any("parecen cruzadas" in m for m in avisos)                     # cantidad 12.500 a $ 2: cruzadas
    res = _calcular(cliente_api, imp)
    # 24.000 + 36.000 + 10.000 (marzo) + 25.000 + 13.000 (abril) = 108.000
    assert _r(res, "ingresos") == D("108000")


# 3 ─ fechas copiadas y fechas futuras ────────────────────────────────────────
def test_03_fechas_que_no_cuadran_con_el_titulo_preguntan_con_respuesta_sugerida(cliente_api):
    imp = _subir(cliente_api, "03_fechas_copiadas_y_futuras.xlsx")
    preguntas = {p["id"].split(":", 2)[-1]: p for p in imp["preguntas"]}
    assert preguntas["fechas:titulo"]["defecto"] == "titulo"
    assert preguntas["fechas:futuras"]["defecto"] == "cruzar"               # 2026-11-02 → 2026-02-11
    res = _calcular(cliente_api, imp, periodizacion="por_periodo")
    # Con las respuestas sugeridas: enero 150.000 − arriendo 80.000 = 70.000;
    # febrero 70.000 + 30.000 + 20.000 − servicios 15.000 = 105.000.
    assert [D(p["utilidad"]) for p in res["periodos_procesados"]] == [D("70000"), D("105000")]


def test_03_si_el_contador_responde_otra_cosa_se_respeta(cliente_api):
    imp = _subir(cliente_api, "03_fechas_copiadas_y_futuras.xlsx")
    ids = {p["id"].split(":", 2)[-1]: p["id"] for p in imp["preguntas"]}
    futuras = next(p for p in imp["preguntas"] if p["id"].endswith("fechas:futuras"))
    # B2: «mismo día del año anterior» inventaría 2025, que el archivo no menciona: ni se ofrece.
    assert "anio" not in {o["valor"] for o in futuras["opciones"]}
    res = _calcular(cliente_api, imp, respuestas={ids["fechas:titulo"]: "archivo", ids["fechas:futuras"]: "excluir"},
                    periodizacion="por_periodo")
    utilidades = {p["desde"]: D(p["utilidad"]) for p in res["periodos_procesados"] if p.get("utilidad") is not None}
    # Fechas del archivo: enero 100.000+50.000+70.000+30.000 − 80.000 = 170.000; febrero 20.000.
    # La fecha futura (servicios 15.000 en noviembre) queda fuera: no ha ocurrido.
    assert utilidades == {"2026-01-01": D("170000"), "2026-02-01": D("20000")}


# 4 ─ totales mezclados y números escritos como texto ─────────────────────────
def test_04_totales_filas_en_cero_y_numeros_como_texto(cliente_api):
    imp = _subir(cliente_api, "04_totales_mezclados.xlsx")
    hoja = imp["hojas"][0]
    assert hoja["formato"] == "auxiliares" and hoja["resumen"]["registros"] == 3
    res = _calcular(cliente_api, imp)
    # 1.200.000 + 350.000,50 + 800.000 = 2.350.000,50 (sin el subtotal, el total ni la fila en cero)
    assert _r(res, "inventario_final") == D("2350000.50")
    assert _r(res, "efectivo") == D("-2350000.50")


# 5 ─ hojas vacías ─────────────────────────────────────────────────────────────
def test_05_hojas_vacias_se_ignoran_con_aviso(cliente_api):
    imp = _subir(cliente_api, "05_hojas_vacias.xlsx")
    motivos = {h["hoja"]: h["motivo"] for h in imp["hojas"]}
    assert motivos["Hoja1"] == "Hoja vacía" and motivos["Hoja3"] == "Hoja vacía"
    assert "promete compras" in motivos["COMPRAS"]                          # 4.2 · 9
    res = _calcular(cliente_api, imp)
    assert _r(res, "ingresos") == D("12000")


# 6 ─ cartera y cuentas por pagar ──────────────────────────────────────────────
def test_06_cartera_con_terceros_desconocidos(cliente_api):
    imp = _subir(cliente_api, "06_cartera_terceros_desconocidos.xlsx")
    preguntas = [p for p in imp["preguntas"] if p["clase"] == "terceros"]
    assert len(preguntas) == 2 and all(p["defecto"] == "saldo_anterior" for p in preguntas)
    assert "DOÑA ROSA" in preguntas[0]["detalle"] or "DONA ROSA" in preguntas[0]["detalle"]
    res = _calcular(cliente_api, imp)
    # Caja: 50.000 + 30.000 (contado) + 40.000 (abono Tienda Azul) − 30.000 (Juan Ruiz no pagó)
    #       + 20.000 (abono Doña Rosa) − 50.000 (pago a Postobón) = 60.000
    assert _r(res, "efectivo") == D("60000")
    # Activo: caja 60.000 + clientes 150.000 (60.000 + 30.000 + 60.000) = 210.000
    assert _r(res, "total_activo") == D("210000")
    assert _r(res, "total_pasivo") == D("150000")                            # Postobón 200.000 − 50.000
    assert _r(res, "ingresos") == D("180000")
    assert res["resumen"]["esf_cuadra"]
    comps = _comprobantes_cuadran(cliente_api, imp["cliente_id"])
    assert any(c.startswith("REC-") for c in comps) and any(c.startswith("PAG-") for c in comps)
    assert any(c.startswith("RCL-") for c in comps)                          # Juan Ruiz: de caja a cartera


def test_06_un_tercero_de_la_lista_no_es_el_nombre_del_cliente(cliente_api):
    r = cliente_api.post("/api/subir", files=[("archivos", ("06_cartera_terceros_desconocidos.xlsx", (
        BANCO / "06_cartera_terceros_desconocidos.xlsx").read_bytes()))]).json()
    nombre = r["identidad"]["campos"].get("razon_social", {})
    # «POSTOBON SA | 200.000 | 50.000» es un proveedor, no el dueño del archivo.
    assert "POSTOBON" not in nombre.get("valor", "")
    assert nombre.get("confianza") in (None, "sugerido")


def test_06_terceros_como_ventas_a_credito_adicionales(cliente_api):
    imp = _subir(cliente_api, "06_cartera_terceros_desconocidos.xlsx")
    ids = {p["id"]: p for p in imp["preguntas"] if p["clase"] == "terceros"}
    cartera = next(i for i, p in ids.items() if "ventas" in p["titulo"])
    res = _calcular(cliente_api, imp, respuestas={cartera: "adicional"})
    # La deuda de Doña Rosa (80.000) es una venta a crédito más: ingresos 180.000 + 80.000.
    assert _r(res, "ingresos") == D("260000")


# 7 ─ CSV sin identidad ────────────────────────────────────────────────────────
def test_07_csv_de_gastos_sin_nit_pide_solo_el_nit(cliente_api):
    r = cliente_api.post("/api/subir", files=[("archivos", ("07_gastos_sin_nit.csv",
                                                            (BANCO / "07_gastos_sin_nit.csv").read_bytes()))]).json()
    assert r["clase"] == "contabilidad" and "nit" in r["falta"]
    imp = _subir(cliente_api, "07_gastos_sin_nit.csv")
    cuentas = {m["nombre"]: m["codigo"] for m in imp["mapeo"]}
    assert cuentas["Gasto: Arriendo local"] == "512010"
    assert cuentas["Gasto: Energía"] == "513530" and cuentas["Gasto: Agua"] == "513525"
    assert cuentas["Gasto: Pago empleado"] == "510506" and cuentas["Gasto: Papelería"] == "519530"
    res = _calcular(cliente_api, imp)
    # 900.000 + 120.500 + 45.300 + 1.300.000 + 23.000 = 2.388.800
    assert _r(res, "utilidad_neta") == D("-2388800")
    assert any("No hay saldos iniciales" in a["mensaje"] for a in res["alertas"])   # 4.2 · 8


# 8 ─ balance de prueba en PDF con texto ───────────────────────────────────────
def test_08_balance_de_prueba_en_pdf_entra_a_la_contabilidad(cliente_api):
    imp = _subir(cliente_api, "08_balance_de_prueba.pdf")
    hoja = next(h for h in imp["hojas"] if h["formato"] == "balance")
    assert hoja["resumen"]["subtotales_omitidos"] == 1                      # 1105 es padre de 110505
    assert imp["periodo_sugerido"]["desde"] == "2026-03-01"                  # «A 31 DE MARZO DE 2026»
    res = _calcular(cliente_api, imp)
    # Activo: caja 1.500.000 + mercancías 4.000.000; pasivo 2.000.000; utilidad 2.500.000 − 1.200.000 − 800.000
    assert _r(res, "total_activo") == D("5500000") and _r(res, "total_pasivo") == D("2000000")
    assert _r(res, "utilidad_neta") == D("500000") and _r(res, "total_patrimonio") == D("3500000")


def test_08b_listado_de_ventas_en_tabla_de_pdf(cliente_api):
    imp = _subir(cliente_api, "08b_ventas_tabla.pdf")
    res = _calcular(cliente_api, imp)
    assert _r(res, "ingresos") == D("60000")                                # 25.000 + 35.000


# 9 ─ Word: tabla de ventas e identidad en los párrafos ────────────────────────
def test_09_word_con_tabla_de_ventas(cliente_api):
    r = cliente_api.post("/api/subir", files=[("archivos", ("09_ventas_en_word.docx",
                                                            (BANCO / "09_ventas_en_word.docx").read_bytes()))]).json()
    assert r["clase"] == "contabilidad" and r["falta"] == []
    assert "TRIGAL" in r["identidad"]["campos"]["razon_social"]["valor"]
    assert unit.limpiar(r["identidad"]["campos"]["nit"]["valor"]) == "900555111"
    imp = _subir(cliente_api, "09_ventas_en_word.docx")
    res = _calcular(cliente_api, imp)
    assert _r(res, "ingresos") == D("160000")                               # 50.000 + 70.000 + 40.000


# 10 ─ PDF escaneado ──────────────────────────────────────────────────────────
def test_10_pdf_escaneado_no_inventa_nada(cliente_api):
    r = cliente_api.post("/api/subir", files=[("archivos", ("10_escaneado.pdf",
                                                            (BANCO / "10_escaneado.pdf").read_bytes()))])
    assert r.status_code == 400
    assert "imagen" in r.json()["detail"]["mensaje"]


# 11 ─ libro diario suelto (P01) ───────────────────────────────────────────────
def test_11_libro_diario_en_csv_con_encabezados_en_desorden(cliente_api):
    imp = _subir(cliente_api, "11_libro_diario.csv")
    assert imp["hojas"][0]["formato"] == "libro_diario"
    res = _calcular(cliente_api, imp)
    # Caja 5.000.000 + 1.190.000 − 600.000 = 5.590.000; IVA 190.000; utilidad 1.000.000 − 600.000
    assert _r(res, "total_activo") == D("5590000") and _r(res, "total_pasivo") == D("190000")
    assert _r(res, "utilidad_neta") == D("400000") and _r(res, "total_patrimonio") == D("5400000")
    comps = _comprobantes_cuadran(cliente_api, imp["cliente_id"])
    assert set(comps) == {"CE-1", "FV-1", "CE-2"}


def test_11_libro_diario_mes_a_mes(cliente_api):
    imp = _subir(cliente_api, "11_libro_diario.csv")
    res = _calcular(cliente_api, imp, periodizacion="por_periodo")
    assert [D(p["utilidad"]) for p in res["periodos_procesados"]] == [D("1000000"), D("-600000")]
    assert _r(res, "total_activo") == D("5590000")                          # febrero abre con el cierre de enero


# 12 ─ inventario insuficiente y márgenes absurdos ─────────────────────────────
def test_12_inventario_insuficiente_y_margen_anomalo(cliente_api):
    imp = _subir(cliente_api, "12_inventario_insuficiente.xlsx")
    res = _calcular(cliente_api, imp)
    falta = _alertas(res, "AUX-INVENTARIO")
    assert falta and "PAPA" in falta[0]["mensaje"] and "septiembre de 2026" in falta[0]["mensaje"]
    assert _alertas(res, "AUX-MARGEN") and "CEBOLLA" in _alertas(res, "AUX-MARGEN")[0]["mensaje"]
    # No se inventa costo: papa solo hasta las 2 unidades compradas (160.000) + cebolla 60.000
    assert _r(res, "costo_ventas") == D("220000")
    assert _r(res, "ingresos") == D("302500") and _r(res, "utilidad_neta") == D("82500")


# 13 ─ datos que solo están en la primera fila ─────────────────────────────────
def test_13_forma_de_pago_solo_en_la_primera_fila(cliente_api):
    imp = _subir(cliente_api, "13_datos_repetidos.xlsx")
    clases = {p["id"].rsplit(":", 1)[-1]: p for p in imp["preguntas"] if p["clase"] == "repetir"}
    assert clases["forma_pago"]["defecto"] == "si" and clases["tercero"]["defecto"] == "si"
    res = _calcular(cliente_api, imp)
    # Todo a crédito con Distri Norte: 20.000 + 30.000 + 12.000 + 10.000 = 72.000 en proveedores
    assert _r(res, "total_pasivo") == D("72000") and _r(res, "efectivo") == D("0")
    imp2 = _subir(cliente_api, "13_datos_repetidos.xlsx")
    pid = next(p["id"] for p in imp2["preguntas"] if p["id"].endswith("forma_pago"))
    res2 = _calcular(cliente_api, imp2, respuestas={pid: "no"})
    # Solo la primera fila a crédito: 20.000 en proveedores y 52.000 pagados de contado
    assert _r(res2, "total_pasivo") == D("20000") and _r(res2, "efectivo") == D("-52000")


# 14 ─ títulos con errores de escritura ────────────────────────────────────────
def test_14_titulos_mal_escritos_se_interpretan_y_se_avisa(cliente_api):
    imp = _subir(cliente_api, "14_titulos_mal_escritos.xlsx")
    avisos = [a["mensaje"] for h in imp["hojas"] for a in h["alertas"] if a["codigo"] == "AUX-TITULO"]
    assert any("«ENRO» se leyó como enero" in m and "«2O26» se leyó como 2026" in m for m in avisos)
    assert any("«FEBERO» se leyó como febrero" in m for m in avisos)
    res = _calcular(cliente_api, imp, periodizacion="por_periodo")
    # Solo el día en la columna: enero 10.000 + 20.000; febrero 30.000
    assert [D(p["utilidad"]) for p in res["periodos_procesados"]] == [D("30000"), D("30000")]


# 15 ─ inventario inicial y conteo físico ──────────────────────────────────────
def test_15_inventario_inicial_y_conteo_fisico(cliente_api):
    imp = _subir(cliente_api, "15_inventario_inicial_y_conteo.xlsx")
    res = _calcular(cliente_api, imp)
    # Tornillos: 100 a $ 200, se venden 30 (costo 6.000), quedan 70; el conteo dice 65 → faltan 5 ($ 1.000)
    assert _r(res, "costo_ventas") == D("6000")
    fisico = next(a for a in res["ajustes"] if a["id"] == "inventario_fisico")
    assert fisico["aceptado"] and D(fisico["total"]) == D("1000")
    # Utilidad 15.000 − 6.000 − 1.000; inventario 25.000 − 6.000 − 1.000
    assert _r(res, "utilidad_neta") == D("8000") and _r(res, "inventario_final") == D("18000")
    assert res["resumen"]["esf_cuadra"]


# 16 ─ balance en Excel con cuentas padre ──────────────────────────────────────
def test_16_balance_en_excel_con_saldo_anterior_y_movimientos(cliente_api):
    imp = _subir(cliente_api, "16_balance_excel.xlsx")
    assert imp["hojas"][0]["formato"] == "balance"
    res = _calcular(cliente_api, imp)
    # Caja: 1.000.000 + 500.000 − 300.000 = 1.200.000; utilidad 500.000 − 300.000
    assert _r(res, "efectivo") == D("1200000") and _r(res, "utilidad_neta") == D("200000")
    assert _r(res, "total_patrimonio") == D("1200000") and res["resumen"]["bp_cuadra"]


# 17 ─ una hoja por mes, tablas lado a lado ───────────────────────────────────
def test_17_hoja_por_mes_con_ventas_y_compras_lado_a_lado(cliente_api):
    imp = _subir(cliente_api, "17_hoja_por_mes_lado_a_lado.xlsx")
    bloques = [(b["tipo"], b["mes"]) for h in imp["hojas"] for b in h["resumen"].get("bloques", [])]
    assert bloques == [("ventas", "2026-01"), ("compras", "2026-01"), ("ventas", "2026-02"), ("compras", "2026-02")]
    assert imp["preguntas"] == []
    res = _calcular(cliente_api, imp)
    # Ventas 10.000 + 15.000 + 20.000; compras 8.000 + 5.000 + 3.000 (sin cantidades: al inventario)
    assert _r(res, "ingresos") == D("45000") and _r(res, "inventario_final") == D("16000")
    assert _r(res, "efectivo") == D("29000")


# 18 ─ listas sin tipo ─────────────────────────────────────────────────────────
def test_18_lista_sin_tipo_se_pregunta_en_vez_de_ignorarla(cliente_api):
    imp = _subir(cliente_api, "18_listas_sin_tipo.xlsx")
    tipos = {p["hoja"].split(" › ")[1]: p for p in imp["preguntas"] if p["clase"] == "tipo"}
    assert tipos["Hoja1"]["defecto"] == "gastos"                           # arriendo y energía son gastos
    assert tipos["Hoja2"]["defecto"] == "ignorar"                          # «mercancía varia»: no se adivina
    res = _calcular(cliente_api, imp)
    assert _r(res, "utilidad_neta") == D("-580000")
    imp2 = _subir(cliente_api, "18_listas_sin_tipo.xlsx")
    pid = next(p["id"] for p in imp2["preguntas"] if p["hoja"].endswith("Hoja2 › Hoja2 (bloque 1)"))
    res2 = _calcular(cliente_api, imp2, respuestas={pid: "ventas"})
    assert _r(res2, "ingresos") == D("100000") and _r(res2, "utilidad_neta") == D("-480000")


# ─ el libro diario lleva a la fila original ──────────────────────────────────
def test_cada_asiento_lleva_a_su_fila_original(cliente_api):
    imp = _subir(cliente_api, "01_ventas_compras_bloques.xlsx")
    res = _calcular(cliente_api, imp)
    movs = cliente_api.get(f"/api/clientes/{imp['cliente_id']}/movimientos").json()["movimientos"]
    venta = next(m for m in movs if m["comprobante"] == "VTA-0001")
    assert venta["origen"].endswith("› VENTAS › fila 3")
    assert res["origenes"][venta["origen"]][:3] == ["2026-01-10", "JUAN PEREZ", "ARROZ"]


# ── v2.3 · fallos de la prueba ciega (B1, B2, B3) ─────────────────────────────
def test_19_cuentas_por_pagar_aunque_la_columna_diga_cliente(cliente_api):
    """B1: la hoja y el título dicen «cuentas por pagar»; la columna dice «CLIENTE». Gana la hoja, y se pregunta."""
    imp = _subir(cliente_api, "19_cxp_con_columna_cliente.xlsx")
    duda = next(p for p in imp["preguntas"] if p["id"].endswith("cartera_o_cxp"))
    assert duda["defecto"] == "cxp" and "lo que el cliente debe" in duda["titulo"]
    terceros = next(p for p in imp["preguntas"] if p["clase"] == "terceros")
    assert "compras" in terceros["titulo"] and "ventas" not in terceros["titulo"]
    res = _calcular(cliente_api, imp)
    # Proveedores: 300.000 a crédito − abono 100.000 + saldo anterior de Granos del Sur 150.000 = 350.000.
    assert _r(res, "total_pasivo") == D("350000")
    # Caja: −100.000 (compra de contado) − 100.000 (abono) = −200.000.
    assert _r(res, "efectivo") == D("-200000")
    assert _r(res, "ingresos") == D("0")


def test_20_un_mes_que_no_ha_llegado_queda_fuera(cliente_api, monkeypatch):
    """B2: «VENTAS NOVIEMBRE 2026» visto el 8 de octubre de 2026: se deja fuera, no se mueve a 2025."""
    from datetime import date

    from app.importadores import auxiliares

    monkeypatch.setattr(auxiliares, "_hoy", lambda: date(2026, 10, 8))
    imp = _subir(cliente_api, "20_bloque_de_mes_futuro.xlsx")
    futuras = next(p for p in imp["preguntas"] if p["id"].endswith("fechas:futuras"))
    assert futuras["defecto"] == "excluir" and "anio" not in {o["valor"] for o in futuras["opciones"]}
    assert imp["periodo_sugerido"]["desde"] == "2026-09-01" and imp["periodo_sugerido"]["hasta"] == "2026-09-30"
    res = _calcular(cliente_api, imp, periodizacion="por_periodo")
    # Solo septiembre: 100.000 + 50.000 − arriendo 40.000 = 110.000. Nada en noviembre ni en 2025.
    assert _r(res, "ingresos") == D("150000") and _r(res, "utilidad_neta") == D("110000")
    assert not res.get("periodos_procesados") or {p["desde"] for p in res["periodos_procesados"]} == {"2026-09-01"}
    assert any("quedaron fuera" in a["mensaje"] for a in res["alertas"])


def test_21_la_misma_pregunta_en_once_bloques_se_hace_una_vez(cliente_api):
    """B3: 11 bloques con la forma de pago solo en la primera fila y 4 con una fecha copiada → 2 preguntas."""
    imp = _subir(cliente_api, "21_muchos_bloques_iguales.xlsx")
    assert len(imp["preguntas"]) <= 6
    repetir = next(p for p in imp["preguntas"] if p["clase"] == "repetir")
    assert repetir["id"].startswith("grupo:") and len(repetir["bloques"]) == 11
    assert repetir["titulo"].startswith("En 11 bloques la forma de pago")
    fechas = next(p for p in imp["preguntas"] if p["clase"] == "fechas")
    assert len(fechas["bloques"]) == 4
    res = _calcular(cliente_api, imp, periodizacion="por_periodo")
    # 11 meses × (100.000 + 50.000 + 30.000) = 1.980.000, cada mes 180.000 (la fecha copiada vuelve a su mes).
    utilidades = [D(p["utilidad"]) for p in res["periodos_procesados"]]
    assert len(utilidades) == 11 and set(utilidades) == {D("180000")}


def test_21_un_bloque_se_puede_responder_aparte(cliente_api):
    imp = _subir(cliente_api, "21_muchos_bloques_iguales.xlsx")
    fechas = next(p for p in imp["preguntas"] if p["clase"] == "fechas")
    # El grupo dice «título»; un bloque concreto (marzo) se deja con la fecha que trae la fila.
    marzo = next(b["id"] for b in fechas["bloques"] if "MARZO" in b["lugar"])
    res = _calcular(cliente_api, imp, respuestas={marzo: "archivo"}, periodizacion="por_periodo")
    por_mes = {p["desde"]: D(p["utilidad"]) for p in res["periodos_procesados"]}
    # La fila del 28 de febrero de marzo queda en febrero: febrero 280.000, marzo 80.000.
    assert por_mes["2025-02-01"] == D("280000") and por_mes["2025-03-01"] == D("80000")
