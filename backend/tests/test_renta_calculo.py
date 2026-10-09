"""Formulario 210 AG 2025: cálculo con valores hechos a mano (v2.3 · Fase 5).

UVT 2025 = 49.799. Cada caso lleva su cuenta en el comentario; los valores
del formulario se aproximan a miles (art. 577 E.T.).
"""
import json
from datetime import date
from decimal import Decimal as D
from pathlib import Path

import pytest

from app.renta import obligacion, parametros
from app.renta.calculo import EntradaRenta, R, comparar, impuesto_241, liquidar

CASO_A = json.loads((Path(__file__).parent / "renta" / "caso_a.json").read_text(encoding="utf-8"))


def test_parametros_ag2025_con_norma():
    p = parametros.obtener(2025)
    assert p["uvt"]["valor"] == "49799"
    assert p["componente_inflacionario"]["rendimientos"] == "0.5543"
    assert "898" in p["componente_inflacionario"]["fuente"]
    assert p["compras_factura_electronica"]["tope_uvt"] == "240"
    assert p["limite_exentas_deducciones"]["tope_uvt"] == "1340"
    for clave in ("tabla_241", "renta_exenta_laboral", "dependientes", "intereses_vivienda", "medicina_prepagada",
                  "aportes_voluntarios", "gmf", "ganancias_ocasionales", "anticipo", "aproximacion"):
        assert p[clave].get("norma"), clave
    assert len(p["vencimientos"]["por_ultimos_dos_digitos"]) == 50


def test_formulario_210_casillas_del_oficial():
    casillas = parametros.nombres_casillas(2025)
    assert casillas[28]["nombre"].startswith("Uno por ciento")
    assert casillas[29]["nombre"] == "Total patrimonio bruto"
    assert casillas[92]["formula"] == "28 + 41 + 53 + 69 + 86 + 139"
    assert casillas[132]["nombre"] == "Retenciones año gravable a declarar"
    assert casillas[137]["nombre"] == "Total saldo a favor"
    assert min(casillas) == 28 and max(casillas) == 141


def test_aproximacion_a_miles():
    assert R("117144") == D("117000")
    assert R("64932.9") == D("65000")
    assert R("4920") == D("5000")
    assert R("1500") == D("2000")


def test_tabla_241():
    assert impuesto_241(D("54280000"), 2025) == 0                     # 1.090 UVT ≈ 54.280.910
    # 58.349.000 / 49.799 = 1.171,6902 UVT → (81,6902 × 19 %) = 15,5211 UVT × 49.799 = 772.937 → 773.000
    assert impuesto_241(D("58349000"), 2025) == D("773000")
    # 99.014.000 → 1.988,2729 UVT → 288,2729 × 28 % + 116 = 196,7164 UVT → 9.796.280 → 9.796.000
    assert impuesto_241(D("99014000"), 2025) == D("9796000")


def _caso_a() -> EntradaRenta:
    return EntradaRenta(
        patrimonio_bruto=D("4600014"), deudas=D("52201487"), capital_rendimientos=D("117144"),
        nolab_ingresos=D(CASO_A["contador"]["no_laborales_ingresos"]),
        nolab_costos=D(CASO_A["contador"]["no_laborales_costos"]), retenciones=D("4920"),
        compras_fe=D("7763109"), uno_por_ciento_fe=D(CASO_A["contador"]["compras_fe_1pct_declarado"]))


def test_caso_a_coincide_con_el_210_presentado():
    L = liquidar(_caso_a())
    for casilla, valor in CASO_A["esperado_210"].items():
        assert L[int(casilla)] == D(valor), f"casilla {casilla}: {L[int(casilla)]} ≠ {valor}"
    # La app propone el máximo legal del 1 % (7.763.109 × 1 % = 77.631 → 78.000) y deja ajustarlo.
    assert L.maximo_1pct == D("78000")
    assert liquidar(EntradaRenta(**{**_caso_a().__dict__, "uno_por_ciento_fe": None}))[28] == D("78000")


def test_caso_a_obligada_por_tope_4():
    t = CASO_A["topes"]
    o = obligacion.evaluar({"ingresos": t["1"], "patrimonio": t["2"], "consumos_tc": t["3"],
                            "consignaciones": t["4"], "compras": t["5"]}, 2025)
    assert o["obligado"]
    assert [m["tope"] for m in o["motivos"] if m["supera"]] == ["consignaciones"]


def test_asalariado_con_dependientes_y_vivienda():
    """Salario 120 M; aportes 10,8 M; 2 dependientes; vivienda 12 M; prepagada 3 M; retenciones 4 M.

    34 = 109.200.000 · dependientes 10 % = 12.000.000 (tope 384 UVT = 19.122.816)
    38 = 12.000.000 · 39 = 12.000.000 + 3.000.000 = 15.000.000 · 40 = 27.000.000
    25 % de (109,2 M − 27 M) = 20.550.000 (tope 790 UVT = 39.341.210) → 37 = 20.550.000
    Pedido 47.550.000; límite 40 % de 109,2 M = 43.680.000 (1.340 UVT = 66.730.660) → 41 = 43.680.000
    42 = 65.520.000 · 139 = 72 × 2 × 49.799 = 7.171.056 → 7.171.000
    92 = 50.851.000 · 93 = 58.349.000 → impuesto 773.000 · saldo a favor 4.000.000 − 773.000 = 3.227.000
    """
    L = liquidar(EntradaRenta(
        trabajo_ingresos=D("120000000"), trabajo_incr=D("10800000"), dependientes=2,
        intereses_vivienda=D("12000000"), medicina_prepagada=D("3000000"), retenciones=D("4000000"),
        patrimonio_bruto=D("300000000"), deudas=D("100000000")))
    assert (L[34], L[38], L[39], L[40], L[37]) == (D("109200000"), D("12000000"), D("15000000"), D("27000000"), D("20550000"))
    assert (L[41], L[42], L[139], L[92], L[93]) == (D("43680000"), D("65520000"), D("7171000"), D("50851000"), D("58349000"))
    assert (L[116], L[133], L[136], L[137]) == (D("773000"), 0, 0, D("3227000"))
    assert L.avisos  # pidió más de lo que permite el límite


def test_independiente_con_honorarios():
    """Honorarios 150 M con costos 30 M; aportes 17,1 M; GMF 600.000; 1 dependiente; retenciones 16,5 M.

    46 = 150 − 17,1 − 30 = 102.900.000 · GMF 50 % = 300.000 → 53 = 300.000 · 57 = 102.600.000
    139 = 72 UVT = 3.585.528 → 3.586.000 · 92 = 3.886.000 · 93 = 99.014.000 → impuesto 9.796.000
    Saldo a favor: 16.500.000 − 9.796.000 = 6.704.000 (anticipo 0: retenciones > 75 % del impuesto)
    """
    L = liquidar(EntradaRenta(
        honorarios_ingresos=D("150000000"), honorarios_incr=D("17100000"), honorarios_costos=D("30000000"),
        gmf_pagado=D("600000"), dependientes=1, relacion_laboral=False, retenciones=D("16500000"),
        patrimonio_bruto=D("80000000")))
    assert (L[46], L[53], L[57], L[139], L[92], L[93]) == (
        D("102900000"), D("300000"), D("102600000"), D("3586000"), D("3886000"), D("99014000"))
    assert (L[126], L[133], L[137]) == (D("9796000"), 0, D("6704000"))


def test_pensionado():
    """Pensión 60 M (aporte salud 7,2 M) exenta hasta 1.000 UVT/mes; CDT 5 M (componente 55,43 %).

    103 = 0 · 59 = 5.000.000 × 55,43 % = 2.771.500 → 2.772.000 · 61 = 2.228.000 · impuesto 0
    """
    L = liquidar(EntradaRenta(pensiones_ingresos=D("60000000"), pensiones_incr=D("7200000"),
                              capital_rendimientos=D("5000000"), retenciones=D("350000")))
    assert (L[101], L[102], L[103]) == (D("52800000"), D("52800000"), 0)
    assert (L[58], L[59], L[61], L[97]) == (D("5000000"), D("2772000"), D("2228000"), D("2228000"))
    assert (L[126], L[137]) == (0, D("350000"))


def test_rentista_de_capital_con_dividendos():
    """Arriendos 96 M con costos 14 M; GMF 1 M; dividendos 1a subcédula 80 M; retenciones 7 M.

    61 = 82.000.000 · 69 = 500.000 · 97 = 81.500.000 · 111 = 81,5 + 80 = 161.500.000
    161.500.000 / 49.799 = 3.243,0370 UVT → (1.543,0370 × 28 %) + 116 = 548,0504 UVT → 27.292.360 → 27.292.000
    Descuento art. 254-1: (80.000.000 − 54.280.910) × 19 % = 4.886.627 → 4.887.000 · 126 = 22.405.000
    Anticipo (75 %): 22.405.000 × 75 % − 7.000.000 = 9.803.750 → 9.804.000
    A pagar: 22.405.000 + 9.804.000 − 7.000.000 = 25.209.000
    """
    L = liquidar(EntradaRenta(capital_otros=D("96000000"), capital_costos=D("14000000"), gmf_pagado=D("1000000"),
                              dividendos_1a=D("80000000"), retenciones=D("7000000"),
                              patrimonio_bruto=D("1200000000")))
    assert (L[61], L[69], L[97], L[111]) == (D("82000000"), D("500000"), D("81500000"), D("161500000"))
    assert (L[116], L[124], L[126], L[133], L[136]) == (
        D("27292000"), D("4887000"), D("22405000"), D("9804000"), D("25209000"))


def test_no_obligado():
    o = obligacion.evaluar({"ingresos": "40000000", "patrimonio": "50000000", "consumos_tc": "10000000",
                            "consignaciones": "45000000", "compras": "20000000"}, 2025)
    assert not o["obligado"]
    assert o["veredicto"].startswith("No está obligado")


def test_topes_en_el_limite():
    # 1.400 UVT = 69.718.600: los ingresos IGUALES ya obligan; los consumos deben SUPERARLO.
    assert obligacion.evaluar({"ingresos": "69718600"}, 2025)["obligado"]
    assert not obligacion.evaluar({"consumos_tc": "69718600"}, 2025)["obligado"]
    assert obligacion.evaluar({"patrimonio": "224095501"}, 2025)["obligado"]
    assert not obligacion.evaluar({"patrimonio": "224095500"}, 2025)["obligado"]
    assert obligacion.evaluar({"responsable_iva": True}, 2025)["veredicto"].endswith("fue responsable de IVA")


@pytest.mark.parametrize("nit,fecha", [("10000001", "2026-08-12"), ("123456700", "2026-10-26"),
                                       ("9001", "2026-08-12"), ("31587466", "2026-09-28"), ("1", "2026-08-12")])
def test_vencimiento_por_ultimos_digitos(nit, fecha):
    assert obligacion.fecha_limite(nit, 2025) == date.fromisoformat(fecha)


def test_estado_de_vencimiento():
    e = obligacion.estado_vencimiento("10000020", 2025, date(2026, 10, 8))      # 19-20 → 26 de agosto
    assert e["vencida"] and e["dias"] == -43 and "hace 43 días" in e["texto"]
    e = obligacion.estado_vencimiento("10000099", 2025, date(2026, 10, 20))     # 99-00 → 26 de octubre
    assert not e["vencida"] and "faltan 6 días" in e["texto"]


def test_sancion_extemporaneidad():
    # Con impuesto: 2 meses (26-ago → 8-oct) × 5 % × 10.000.000 = 1.000.000
    s = obligacion.sancion_extemporaneidad(D("10000000"), D("0"), D("0"), date(2026, 8, 26), date(2026, 10, 8), 2025)
    assert (s["meses"], s["valor"]) == (2, D("1000000"))
    # Sin impuesto: 0,5 % × 2 × 65.517.144 = 655.171; tope 10 % del saldo a favor (5.000) → mínima 10 UVT 2026 = 523.740 → 524.000
    s = obligacion.sancion_extemporaneidad(D("0"), D("65517144"), D("5000"), date(2026, 8, 26), date(2026, 10, 8), 2025)
    assert s["valor"] == D("524000")
    assert obligacion.sancion_extemporaneidad(D("1"), D("1"), D("0"), date(2026, 9, 1), date(2026, 9, 1), 2025)["valor"] == 0


def test_comparacion_dian_y_ahorro():
    """Asalariado: la DIAN no conoce dependientes, vivienda ni prepagada."""
    e = EntradaRenta(trabajo_ingresos=D("120000000"), trabajo_incr=D("10800000"), dependientes=2,
                     intereses_vivienda=D("12000000"), medicina_prepagada=D("3000000"), retenciones=D("4000000"))
    r = comparar(e)
    assert r["optimizada"][137] == D("3227000")
    assert r["dian"].neto > r["optimizada"].neto
    assert r["ahorro"] == r["dian"].neto - r["optimizada"].neto
    assert any(d["casilla"] == 139 and d["motivo"] for d in r["diferencias"])


def test_sin_parametros_de_otro_anio():
    with pytest.raises(parametros.RentaSinParametros):
        parametros.obtener(2019)
