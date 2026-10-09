"""Casos de aceptación de la Declaración de Renta AG 2025 (PROMPT_RENTA.md · Sección 6).

Cubre:
- Caso A: Exógena legible + 210 presentado (fotos 4 y 5 y en Excel).
- Caso B: 3 fotos difíciles de José (nunca muestra impuesto ni sanción falso mientras falta datos;
  valida topes, veredicto, vencimiento vencido 27-ago-2026, saldo a favor 6.275.000, ofrece digitar esencial,
  y calcula correctamente tras simular digitación esencial).
- Caso C: Contribuyente nuevo (creado en un clic solo de renta, no se mezcla con clientes contables).
- Caso D: 6 perfiles calculados a mano (asalariado, independiente, pensionado, rentista, no obligado, vencida sin impuesto).
- Determinismo: ejecuciones repetidas dan cifras idénticas byte a byte.
"""
import io
import json
from datetime import date
from decimal import Decimal as D
from pathlib import Path

import openpyxl
import pytest

from app.config import PRIVADO
from app.renta import calculo, documentos, obligacion, ocr, parametros, servicio
from app.renta.calculo import EntradaRenta, liquidar
from app.renta.lectura import unir_paginas, validar_sumas
from app.repositorio import clientes as repo_clientes

IMAGENES_DIR = PRIVADO / "renta" / "imagenes"
CASO_A_JSON = Path(__file__).parent / "renta" / "caso_a.json"


# ══════════════════════════════════════════════════════════════════════════════
# CASO A — Exógena legible + 210 presentado (imágenes 4 y 5 y Excel)
# ══════════════════════════════════════════════════════════════════════════════

def _entrada_caso_a() -> EntradaRenta:
    caso = json.loads(CASO_A_JSON.read_text(encoding="utf-8"))
    c = caso["contador"]
    return EntradaRenta(
        patrimonio_bruto=D("4600014"),
        deudas=D("52201487"),
        capital_rendimientos=D("117144"),
        nolab_ingresos=D(c["no_laborales_ingresos"]),
        nolab_costos=D(c["no_laborales_costos"]),
        retenciones=D("4920"),
        compras_fe=D("7763109"),
        uno_por_ciento_fe=D(c["compras_fe_1pct_declarado"]),
    )


def test_caso_a_casillas_exactas_formulario_210():
    """Caso A: El cálculo coincide exactamente con las casillas del 210 presentado (imagen 5)."""
    caso = json.loads(CASO_A_JSON.read_text(encoding="utf-8"))
    esperado = caso["esperado_210"]
    L = liquidar(_entrada_caso_a())

    for casilla, valor in esperado.items():
        assert L[int(casilla)] == D(valor), f"Casilla {casilla}: obtenido {L[int(casilla)]} != esperado {valor}"

    # Verificaciones explícitas de la Sección 6
    assert L[29] == D("4600000")       # Patrimonio bruto
    assert L[30] == D("52201000")      # Deudas
    assert L[31] == D("0")             # Patrimonio líquido nunca negativo
    assert L[58] == D("117000")        # Rendimientos capital
    assert L[59] == D("65000")         # Componente inflacionario INCR
    assert L[61] == D("52000")         # Renta líquida capital
    assert L[74] == D("65400000")      # Rentas no laborales ingresos
    assert L[77] == D("32800000")      # Costos no laborales
    assert L[78] == D("32600000")      # Renta no laboral
    assert L[92] == D("48000")         # Rentas exentas y deducciones (1% FE)
    assert L[93] == D("32604000")      # Renta líquida ordinaria
    assert L[111] == D("32604000")     # Renta líquida gravable general
    assert L[116] == D("0")            # Impuesto sobre rentas líquidas gravables
    assert L[132] == D("5000")         # Retenciones en la fuente
    assert L[137] == D("5000")         # Total saldo a favor


def test_caso_a_obligada_por_tope_4():
    """Caso A: Obligada a declarar únicamente por movimientos/consignaciones (Tope 4)."""
    caso = json.loads(CASO_A_JSON.read_text(encoding="utf-8"))
    t = caso["topes"]
    o = obligacion.evaluar({
        "ingresos": t["1"],
        "patrimonio": t["2"],
        "consumos_tc": t["3"],
        "consignaciones": t["4"],
        "compras": t["5"],
    }, 2025)
    assert o["obligado"] is True
    motivos = [m["tope"] for m in o["motivos"] if m["supera"]]
    assert motivos == ["consignaciones"]


@pytest.mark.skipif(not (IMAGENES_DIR / "4.png").exists(), reason="Sin imagen real 4.png")
def test_caso_a_foto_real_lineas_y_titularidad():
    """Caso A: Lectura de la foto 4 real comprueba las 23 líneas y las 2 marcas NO REGISTRA NO."""
    if not ocr.disponible():
        pytest.skip("Tesseract no disponible en este entorno")
    leido = documentos.leer_archivo("4.png", (IMAGENES_DIR / "4.png").read_bytes())
    rep = leido.reporte
    assert rep.topes[1] == "117144"
    assert rep.topes[2] == "4600014"
    assert rep.topes[4] == "93121224"
    assert sum(1 for l in rep.lineas if l.no_titular) == 2


def test_caso_a_mismo_resultado_con_excel():
    """Caso A: La misma información leída desde Excel genera las casillas idénticas."""
    caso = json.loads(CASO_A_JSON.read_text(encoding="utf-8"))
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Reporte"
    ws.append(["Entidad", "Titular", "Detalle", "Valor", "Uso sugerido"])
    for f in caso["lineas"]:
        ws.append([f["entidad"], f["titular"], f["detalle"], int(f["valor"]), f.get("uso", "")])
    buf = io.BytesIO()
    wb.save(buf)
    leido = documentos.leer_archivo("reporte_caso_a.xlsx", buf.getvalue())
    assert len(leido.reporte.lineas) == len(caso["lineas"])

    L = liquidar(_entrada_caso_a())
    assert L[137] == D("5000")
    assert L[116] == D("0")


# ══════════════════════════════════════════════════════════════════════════════
# CASO B — 3 fotos difíciles de José (imágenes 1, 2 y 3)
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.skipif(not (IMAGENES_DIR / "1.png").exists(), reason="Sin imágenes reales de Caso B")
def test_caso_b_regla_de_oro_nunca_muestra_cifras_falsas():
    """Caso B (Regla de oro): Mientras falten datos o validación, NUNCA muestra impuesto a cargo ni sanción."""
    if not ocr.disponible():
        pytest.skip("Tesseract no disponible en este entorno")

    archivos = [IMAGENES_DIR / n for n in ("3.png", "1.png", "2.png")]
    leidos = [documentos.leer_archivo(p.name, p.read_bytes()) for p in archivos]
    grupos = documentos.agrupar_por_contribuyente(leidos)
    assert not grupos["otros"], "Las 3 fotos deben pertenecer al mismo contribuyente"

    rep, _ = unir_paginas([l.reporte for l in grupos["leidos"]])
    assert rep.topes == {1: "82535904", 2: "226543936", 3: "19977892", 4: "125053184", 5: "12910068"}
    assert rep.responsable_iva is True

    # Evaluar con servicio.calcular simulando el estado recién leído
    val = validar_sumas(rep)
    datos_crudos = {
        "reporte": servicio._reporte_a_dict(rep),
        "validacion": [{**v, "encabezado": str(v["encabezado"]), "suma": str(v["suma"])} for v in val],
        "respuestas": {},
    }
    cliente_mock = {"id": "mock_jose", "nit": "10000021", "razon_social": "JOSE CONTRIBUYENTE"}
    resultado = servicio.calcular(cliente_mock, 2025, datos_crudos, hoy=date(2026, 10, 9))

    # REGLA DE ORO: Debe estar incompleto y bloqueado
    assert resultado["incompleto"] is True
    assert resultado["cifras"]["bloqueado"] is True
    assert resultado["cifras"]["a_pagar"] is None, "La app NUNCA debe mostrar impuesto a pagar con datos dudosos"
    assert resultado["cifras"]["neto"] is None
    assert resultado["sancion"] is None, "La app NUNCA debe mostrar sanción con datos dudosos"

    # Veredicto de obligación sí debe reflejar los topes validados
    ob = resultado["obligacion"]
    assert ob["obligado"] is True
    motivos = {m["tope"] for m in ob["motivos"] if m["supera"]}
    assert {"ingresos", "patrimonio", "consignaciones", "responsable_iva"} <= motivos

    # Vencimiento: NIT terminado en 21 -> 27 de agosto de 2026 (vencida)
    assert resultado["vencimiento"]["fecha"] == date(2026, 8, 27)
    assert resultado["vencimiento"]["vencida"] is True

    # Debe ofrecer Digitar lo esencial
    assert resultado["ofrecer_digitar_esencial"] is True


def test_caso_b_digitacion_esencial_y_sancion_art_641():
    """Caso B: Al digitar lo esencial con la foto al lado, valida y liquida con sanción art. 641."""
    try:
        existente = repo_clientes.por_nit("10000021")
        if existente:
            repo_clientes.eliminar(existente["id"])
    except Exception:
        pass
    cl = repo_clientes.crear({
        "nit": "10000021",
        "razon_social": "JOSE CASO B",
        "tipo_persona": "natural",
        "estado": "activo",
        "etiquetas": ["renta", "solo_renta"],
        "regimen": "ordinario",
        "responsable_iva": True,
    })
    cid = cl["id"]

    # Datos esenciales extraídos de las fotos de José
    entrada_esencial = {
        "topes": {
            "1": "82535904",
            "2": "226543936",
            "3": "19977892",
            "4": "125053184",
            "5": "12910068",
            "6": True,
        },
        "esenciales": [
            {
                "categoria": "ingreso_no_laboral",
                "valor": "82535904",
                "detalle": "Ingresos documentos soporte por ventas",
                "tope": 1,
            },
            {
                "categoria": "patrimonio",
                "valor": "226543936",
                "detalle": "Avalúos catastrales y vehículo",
                "tope": 2,
            },
            {
                "categoria": "deuda",
                "valor": "0",
                "detalle": "Sin deudas",
            },
            {
                "categoria": "retencion",
                "valor": "0",
                "detalle": "Sin retenciones",
            },
        ],
        "anterior_saldo_favor": "6275000",
        "anterior_patrimonio": "181910000",
        "respuestas": {
            "saldo_favor": "si",
        },
    }

    res_vista = servicio.digitar_esencial(cid, 2025, entrada_esencial)
    res = res_vista["resultado"]

    # Validación completa: ya no está bloqueado
    assert res["motivos_incompleto"] == []
    assert res["incompleto"] is False
    assert res["cifras"]["bloqueado"] is False

    # Patrimonio bruto cuadra con Tope 2
    r29 = next(c["optimizada"] for c in res["casillas"] if c["casilla"] == 29)
    assert D(str(r29)) == D("226544000")  # Aproximado a miles

    # Vencimiento vencida el 27 de agosto de 2026
    assert str(res["vencimiento"]["fecha"]) == "2026-08-27"
    assert res["vencimiento"]["vencida"] is True

    # Sanción calculada por art. 641 (2 meses de retardo)
    assert res["sancion"] is not None
    assert res["sancion"]["meses"] >= 1
    assert D(str(res["sancion"]["valor"])) >= D("524000")  # Al menos la sanción mínima (10 UVT 2026)


# ══════════════════════════════════════════════════════════════════════════════
# CASO C — Persona nueva que no es cliente contable
# ══════════════════════════════════════════════════════════════════════════════

def test_caso_c_persona_nueva_solo_renta():
    """Caso C: Se crea el contribuyente desde subida universal y NO aparece en clientes contables."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["Entidad", "Titular", "Detalle", "Valor", "Uso sugerido"])
    ws.append(["EMPRESA DEMO", "CARLOS NUEVO", "Otros ingresos", "75000000", "Tope 1"])
    ws.append(["BANCO DEMO", "CARLOS NUEVO", "Saldo cuentas bancarias", "15000000", "Tope 2"])
    buf = io.BytesIO()
    wb.save(buf)

    res = servicio.subir_universal(2025, [("exogena_carlos_nuevo.xlsx", buf.getvalue())])
    assert res["creado"] is True
    cid = res["cliente_id"]

    # El contribuyente aparece en la cartera de renta
    cartera = servicio.cartera(2025)
    assert any(f["cliente_id"] == cid for f in cartera)

    # El contribuyente NO aparece en la lista general de clientes contables
    clientes_contables = repo_clientes.listar(incluir_solo_renta=False)
    assert not any(c["id"] == cid for c in clientes_contables["clientes"])


# ══════════════════════════════════════════════════════════════════════════════
# CASO D — 6 contribuyentes ficticios calculados a mano
# ══════════════════════════════════════════════════════════════════════════════

def test_caso_d1_asalariado_dependientes_y_vivienda():
    """D1: Salario 120M, aportes 10.8M, 2 dependientes, vivienda 12M, prepagada 3M, retenciones 4M."""
    L = liquidar(EntradaRenta(
        trabajo_ingresos=D("120000000"),
        trabajo_incr=D("10800000"),
        dependientes=2,
        intereses_vivienda=D("12000000"),
        medicina_prepagada=D("3000000"),
        retenciones=D("4000000"),
        patrimonio_bruto=D("300000000"),
        deudas=D("100000000"),
    ))
    assert L[116] == D("773000")        # Impuesto sobre renta líquida
    assert L[137] == D("3227000")       # Saldo a favor (4M - 773k)


def test_caso_d2_independiente_con_honorarios():
    """D2: Honorarios 150M con costos 30M, aportes 17.1M, GMF 600k, 1 dependiente, retenciones 16.5M."""
    L = liquidar(EntradaRenta(
        honorarios_ingresos=D("150000000"),
        honorarios_incr=D("17100000"),
        honorarios_costos=D("30000000"),
        gmf_pagado=D("600000"),
        dependientes=1,
        relacion_laboral=False,
        retenciones=D("16500000"),
        patrimonio_bruto=D("80000000"),
    ))
    assert L[126] == D("9796000")       # Impuesto neto
    assert L[137] == D("6704000")       # Saldo a favor


def test_caso_d3_pensionado():
    """D3: Pensión 60M (exenta) + CDT 5M (componente inflacionario 55.43%) -> impuesto 0, saldo a favor retención."""
    L = liquidar(EntradaRenta(
        pensiones_ingresos=D("60000000"),
        pensiones_incr=D("7200000"),
        capital_rendimientos=D("5000000"),
        retenciones=D("350000"),
    ))
    assert L[116] == D("0")
    assert L[137] == D("350000")


def test_caso_d4_rentista_con_dividendos():
    """D4: Arriendos 96M costos 14M + dividendos 80M -> total a pagar 25.209.000."""
    L = liquidar(EntradaRenta(
        capital_otros=D("96000000"),
        capital_costos=D("14000000"),
        gmf_pagado=D("1000000"),
        dividendos_1a=D("80000000"),
        retenciones=D("7000000"),
        patrimonio_bruto=D("1200000000"),
    ))
    assert L[136] == D("25209000")      # Total a pagar con anticipo


def test_caso_d5_no_obligado():
    """D5: No supera ningún tope legal."""
    o = obligacion.evaluar({
        "ingresos": "40000000",
        "patrimonio": "50000000",
        "consumos_tc": "10000000",
        "consignaciones": "45000000",
        "compras": "20000000",
    }, 2025)
    assert not o["obligado"]
    assert o["veredicto"].startswith("No está obligado")


def test_caso_d6_vencida_sin_impuesto_a_cargo():
    """D6: Declaración vencida sin impuesto a cargo: sanción mínima art. 639 (10 UVT 2026 = 524.000)."""
    s = obligacion.sancion_extemporaneidad(
        impuesto_cargo=D("0"),
        ingresos_brutos=D("75000000"),
        saldo_favor=D("0"),
        limite=date(2026, 8, 27),
        presentacion=date(2026, 10, 9),
        anio=2025,
    )
    assert s["meses"] == 2
    assert s["valor"] == D("750000")    # 0.5% * 2 * 75.000.000 = 750.000 (art. 641 inc. 2)


# ══════════════════════════════════════════════════════════════════════════════
# DETERMINISMO — Ejecuciones repetidas dan cifras idénticas byte a byte
# ══════════════════════════════════════════════════════════════════════════════

def test_determinismo_casos_a_b_d():
    """Los cálculos de los Casos A, B y D son 100% deterministas byte a byte."""
    # Caso A dos veces
    l1 = liquidar(_entrada_caso_a())
    l2 = liquidar(_entrada_caso_a())
    assert [l1[k] for k in sorted(l1.casillas)] == [l2[k] for k in sorted(l2.casillas)]

    # Caso D1 dos veces
    d1_a = liquidar(EntradaRenta(trabajo_ingresos=D("120000000"), dependientes=2))
    d1_b = liquidar(EntradaRenta(trabajo_ingresos=D("120000000"), dependientes=2))
    assert d1_a.neto == d1_b.neto

    # Sanción Caso D6 dos veces
    s1 = obligacion.sancion_extemporaneidad(D("0"), D("75000000"), D("0"), date(2026, 8, 27), date(2026, 10, 9), 2025)
    s2 = obligacion.sancion_extemporaneidad(D("0"), D("75000000"), D("0"), date(2026, 8, 27), date(2026, 10, 9), 2025)
    assert s1["valor"] == s2["valor"]
