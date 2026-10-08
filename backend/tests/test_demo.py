"""Clientes de demostración (spec v2.2 · fase 9): generador, documentos y borrado en bloque."""
from __future__ import annotations

from decimal import Decimal

import pytest

from app.contabilidad.validaciones import disolucion
from app.importadores import clasificador as clas
from app.modelos import Empresa
from demo import generar_historicos as gen


@pytest.fixture
def api_demo(cliente_api, tmp_path, monkeypatch):
    """El generador habla con la API de pruebas (TestClient es un httpx.Client) y escribe en una carpeta temporal."""
    monkeypatch.setattr(gen, "SALIDA", tmp_path)
    api = gen.Api.__new__(gen.Api)
    api.c = cliente_api
    return api


def test_estatutos_y_rut_generados_llenan_la_ficha():
    c = gen.PANADERIA
    ficha = clas.leer([("Estatutos.docx", gen.estatutos_docx(c)), ("RUT.pdf", gen.rut_pdf(c))]).ficha().a_json()
    v = {k: d["valor"] for k, d in ficha["campos"].items()}
    assert v["razon_social"] == c["razon"] and v["nit"] == c["nit"] and v["sigla"] == c["sigla"]
    assert v["municipio"] == "Tuluá" and v["ciiu"] == "1081" and v["ciiu_secundarios"] == "4724"
    assert v["capital_suscrito"] == "65800000" and v["capital_autorizado"] == "100000000"
    assert v["rep_legal"] == "Luz Marina Ospina Rendon" and v["rep_legal_cc"] == "31456789"
    assert v["responsable_iva"] == "true"
    # La tabla de socios trae el porcentaje con el signo: 60% → 0,6.
    assert [Decimal(s["participacion"]) for s in ficha["socios"]] == [Decimal("0.6"), Decimal("0.4")]


def test_nit_ficticios_con_digito_valido_y_distintos():
    nits = [x["nit"] for x in (gen.PANADERIA, gen.FERRETERIA, gen.CLINICA, gen.TRANSPORTES, gen.MARIA)]
    assert len(set(nits)) == 5
    assert gen.digito_verificacion("901482317") == "5"


def test_maria_elena_bimestral_atrasada_y_cerrada(api_demo, cliente_api):
    """Registros auxiliares desordenados de un año y medio, procesados bimestre a bimestre."""
    cid = gen.maria_elena(api_demo)
    ficha = cliente_api.get(f"/api/clientes/{cid}").json()
    assert ficha["demo"] is True and ficha["etiquetas"] == ["Demostración"] and ficha["periodicidad"] == "bimestral"
    periodos = sorted(cliente_api.get(f"/api/clientes/{cid}/periodos").json()["periodos"], key=lambda p: p["desde"])
    assert [p["desde"][:7] for p in periodos][::4] == ["2025-01", "2025-09", "2026-05"]
    assert len(periodos) == 9 and periodos[-1]["hasta"] == "2026-06-30"
    assert all(p["estado"] == "cerrado" and p["cuadra"] for p in periodos)


def test_eliminar_demostracion_no_toca_clientes_reales(api_demo, cliente_api):
    real = cliente_api.post("/api/clientes", json={"nit": "900123457", "razon_social": "CLIENTE REAL S.A.S."}).json()
    cliente_api.post("/api/clientes", json={"nit": "900765431", "razon_social": "OTRA DEMO S.A.S.", "demo": True,
                                            "etiquetas": ["Demostración"]})
    gen.maria_elena(api_demo)
    lista = cliente_api.get("/api/clientes/demostracion").json()["clientes"]
    assert {c["razon_social"] for c in lista} == {"MARÍA ELENA ROJAS", "OTRA DEMO S.A.S."}

    r = cliente_api.post("/api/clientes/demostracion/eliminar").json()
    assert r["eliminados"] == 2
    assert cliente_api.get("/api/clientes/demostracion").json()["clientes"] == []
    assert cliente_api.get(f"/api/clientes/{real['id']}").status_code == 200
    # Su rastro en la bitácora también se va (no quedan actividades huérfanas en el tablero).
    from app.repositorio import bitacora

    assert "cuentas finca" not in str(bitacora.listar(None, 200))
    # Una segunda vez no hace nada.
    assert cliente_api.post("/api/clientes/demostracion/eliminar").json()["eliminados"] == 0


def test_causal_de_disolucion_cita_la_ley_no_los_estatutos_de_otro_cliente():
    e = Empresa(capital_suscrito=Decimal("100"), tipo_sociedad="S.A.S.")
    [a] = disolucion(Decimal("40"), e)
    assert "Ley 1258 de 2008" in a.mensaje and "estatutos" in a.mensaje and "art. 38" not in a.mensaje
    assert disolucion(Decimal("40"), Empresa(capital_suscrito=Decimal("100"), tipo_persona="natural")) == []
    [b] = disolucion(Decimal("40"), Empresa(capital_suscrito=Decimal("100"), tipo_sociedad="Ltda."))
    assert "art. 370" in b.mensaje


def test_atraso_cuenta_solo_meses_terminados():
    """María Elena (bimestral) cerró hasta junio; el 8 de octubre lleva 3 meses terminados sin contabilizar."""
    from datetime import date

    from app.inteligencia.sugerencias import _atraso

    [s] = _atraso({"periodicidad": "bimestral"}, [{"hasta": "2026-06-30"}], date(2026, 10, 8))
    assert s["codigo"] == "ATRASADO" and "3 meses" in s["titulo"]
    # Mensual con agosto hecho: septiembre acaba de terminar, todavía no es atraso.
    assert _atraso({"periodicidad": "mensual"}, [{"hasta": "2026-08-31"}], date(2026, 10, 8)) == []


def test_firmas_de_persona_natural_y_contador_por_defecto():
    from app import contador
    from app.repositorio.clientes import a_empresa

    e = a_empresa({"razon_social": "MARÍA ELENA ROJAS", "nit": "29874553", "tipo_persona": "natural"})
    assert (e.rep_legal, e.rep_legal_cc) == ("MARÍA ELENA ROJAS", "29874553")
    assert e.contador == contador.leer()["nombre"] and e.contador_tp == contador.leer()["tarjeta_profesional"]
    # Si la ficha trae su contador, ese manda.
    assert a_empresa({"razon_social": "X", "nit": "1", "contador": "OTRA PERSONA", "contador_tp": "1-T"}).contador == "OTRA PERSONA"
