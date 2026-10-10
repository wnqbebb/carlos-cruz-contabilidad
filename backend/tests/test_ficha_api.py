"""Cliente: crear fácil, editar todo (spec v2.2 · Fase 6) y las adiciones A3 y A6."""
from __future__ import annotations

from decimal import Decimal

from tests.test_archivos_variados import _calcular, _subir
from tests.test_ficha import _docx

ACTA = _docx([
    "ACTA DE CONSTITUCIÓN",
    "Se constituye una sociedad por acciones simplificada denominada PANES DEL SUR S.A.S. distinguida con la sigla “PDS”.",
    "El domicilio principal de la sociedad será en la ciudad de Tuluá Valle.",
    "El capital suscrito y pagado es de $ 10.000.000, dividido en mil (1.000) acciones.",
    "El representante legal principal será el señor JUAN CAMILO RIOS VEGA y su suplente será la señora ANA LUCIA VEGA.",
    "NIT 900.777.111-5",
], [["NOMBRE", "CEDULA", "ACCIONES", "%"], ["Juan Camilo Rios Vega", "10.111.222", "600", "60"],
    ["Ana Lucia Vega", "20.333.444", "400", "40"]])


def test_crear_desde_documentos_guarda_toda_la_ficha_y_los_socios(cliente_api):
    p = cliente_api.post("/api/subir", files=[("archivos", ("acta.docx", ACTA))]).json()
    assert p["clase"] == "documentos"
    assert p["ficha"]["campos"]["capital_suscrito"]["valor"] == "10000000"
    # El acta trae un DV equivocado (-5; el correcto es 9): no bloquea, se usa el calculado.
    c = cliente_api.post(f"/api/subir/{p['subida_id']}/confirmar", json={
        "clase": "contabilidad", "crear": {"nit": "900777111", "razon_social": "PANES DEL SUR S.A.S.", "dv": "5"}})
    # Solo documentos, sin cifras: el cliente se crea igual con su ficha.
    assert c.status_code in (200, 422), c.text
    cliente = cliente_api.get("/api/clientes?q=900777111&estado=").json()["clientes"][0]
    ficha = cliente_api.get(f"/api/clientes/{cliente['id']}").json()
    assert ficha["sigla"] == "PDS" and ficha["municipio"] == "Tuluá"
    assert Decimal(ficha["capital_suscrito"]) == Decimal("10000000")
    assert ficha["rep_legal"] == "Juan Camilo Rios Vega" and ficha["rep_legal_cc"] == "10111222"
    assert len(ficha["socios"]) == 2


def test_comparar_documentos_nuevos_con_la_ficha(cliente_api):
    creado = cliente_api.post("/api/clientes", json={"nit": "900777111", "razon_social": "PANES DEL SUR S.A.S.",
                                                    "municipio": "Buga"}).json()
    r = cliente_api.post(f"/api/clientes/{creado['id']}/ficha/comparar",
                         files=[("archivos", ("acta.docx", ACTA))]).json()
    cambios = {c["campo"]: c for c in r["cambios"]}
    assert cambios["municipio"]["actual"] == "Buga" and cambios["municipio"]["nuevo"] == "Tuluá"
    assert "razon_social" not in cambios                                    # igual: no es un cambio
    assert cambios["capital_suscrito"]["nuevo"] == "10000000"
    assert r["socios"]["actual"] == 0 and len(r["socios"]["nuevo"]) == 2
    # Comparar no guarda nada.
    assert cliente_api.get(f"/api/clientes/{creado['id']}").json()["municipio"] == "Buga"


def test_editar_el_nit_avisa_si_ya_lo_usa_otro(cliente_api):
    a = cliente_api.post("/api/clientes", json={"nit": "900777111", "razon_social": "UNO"}).json()
    cliente_api.post("/api/clientes", json={"nit": "900888222", "razon_social": "DOS"})
    r = cliente_api.patch(f"/api/clientes/{a['id']}", json={"nit": "900888222"})
    assert r.status_code == 400 and "DOS" in r.json()["detail"]


def test_restaurar_un_cliente_archivado(cliente_api):
    a = cliente_api.post("/api/clientes", json={"nit": "900777111", "razon_social": "UNO"}).json()
    cliente_api.delete(f"/api/clientes/{a['id']}")
    assert cliente_api.get("/api/clientes?estado=archivado").json()["total"] == 1
    assert cliente_api.post(f"/api/clientes/{a['id']}/restaurar").json()["estado"] == "activo"


def test_la_tabla_de_clientes_trae_el_ultimo_periodo_y_ordena_por_sus_cifras(cliente_api):
    uno = _subir(cliente_api, "05_hojas_vacias.xlsx")            # ingresos 12.000, utilidad 12.000
    _calcular(cliente_api, uno)
    dos = _subir(cliente_api, "11_libro_diario.csv")             # ingresos 1.000.000, utilidad 400.000
    _calcular(cliente_api, dos)
    cliente_api.post("/api/clientes", json={"nit": "900999333", "razon_social": "SIN PERIODOS"})
    lista = cliente_api.get("/api/clientes?orden=ingresos&descendente=true").json()["clientes"]
    assert [c["id"] for c in lista[:2]] == [dos["cliente_id"], uno["cliente_id"]]
    assert lista[-1]["ultimo_periodo"] is None                   # sin periodos: al final
    u = lista[0]["ultimo_periodo"]
    assert Decimal(u["ingresos"]) == Decimal("1000000") and Decimal(u["margen"]) == Decimal("40.0")
    por_margen = cliente_api.get("/api/clientes?orden=margen&descendente=true").json()["clientes"]
    assert por_margen[0]["id"] == uno["cliente_id"]              # 100 % de margen


def test_nota_de_revision_del_periodo(cliente_api):
    imp = _subir(cliente_api, "11_libro_diario.csv")
    res = _calcular(cliente_api, imp)
    pid = res["periodo"]["id"]
    nota = "Pendiente de revisión del contador."
    assert cliente_api.patch(f"/api/periodos/{pid}", json={"nota": nota}).json()["nota"] == nota
    periodos = cliente_api.get(f"/api/clientes/{imp['cliente_id']}/periodos").json()["periodos"]
    assert periodos[0]["nota"] == nota
    # Las cifras de un periodo no se editan a mano.
    assert cliente_api.patch(f"/api/periodos/{pid}", json={"utilidad": "1"}).status_code == 400


def test_a3_capital_distinto_del_libro_de_aportes_es_advertencia():
    from app.contabilidad.mayor import construir_mayor
    from app.contabilidad.validaciones import conciliacion_capital
    from app.modelos import AporteSocio, Empresa, SaldoInicial

    mayor = construir_mayor([SaldoInicial("3105", Decimal(0), Decimal("37800000"))], [])
    alertas = conciliacion_capital(mayor, Empresa(), [AporteSocio("Socio", comprometido=Decimal("30000000"),
                                                                  pagado=Decimal("30000000"))])
    e5 = [a for a in alertas if a.codigo == "E5"]
    assert e5 and e5[0].severidad == "advertencia" and "7.800.000" in e5[0].mensaje


def test_a3_el_capital_que_no_cuadra_se_ve_en_la_ficha(cliente_api):
    from tests.test_archivos_variados import BANCO

    imp = _subir(cliente_api, "11_libro_diario.csv")                       # capital en libros 5.000.000
    cid = imp["cliente_id"]
    cliente_api.patch(f"/api/clientes/{cid}", json={"capital_suscrito": "3000000"})
    p = cliente_api.post(f"/api/subir?cliente_id={cid}", files=[(
        "archivos", ("11_libro_diario.csv", (BANCO / "11_libro_diario.csv").read_bytes()))]).json()
    imp2 = cliente_api.post(f"/api/subir/{p['subida_id']}/confirmar", json={"cliente_id": cid}).json()
    res = _calcular(cliente_api, imp2)
    assert any(a["codigo"] == "E5" and a["severidad"] == "advertencia" for a in res["alertas"])
    sug = cliente_api.get(f"/api/clientes/{imp['cliente_id']}/sugerencias").json()["sugerencias"]
    capital = [s for s in sug if s["codigo"] == "CAPITAL_ESTATUTOS"]
    assert capital and capital[0]["severidad"] == "alta"


def test_las_columnas_nuevas_se_agregan_solas_a_una_base_vieja():
    from sqlalchemy import inspect, text

    from app import db

    with db.motor_db.begin() as cn:
        cn.execute(text("ALTER TABLE periodos DROP COLUMN nota"))
    assert "nota" not in {c["name"] for c in inspect(db.motor_db).get_columns("periodos")}
    db._tablas_listas = False
    db.preparar()
    assert "nota" in {c["name"] for c in inspect(db.motor_db).get_columns("periodos")}


def test_panel_lateral_guarda_socios_con_todos_sus_campos(cliente_api):
    """Rescate H3: el panel manda los campos reales del socio y vuelven iguales al recargar."""
    a = cliente_api.post("/api/clientes", json={"nit": "900777111", "razon_social": "UNO"}).json()
    socio = {"nombre": "Ana Ruiz", "cedula": "20333444", "cargo": "Gerente", "acciones": "400",
             "participacion": "0.4", "comprometido": "4000000", "pagado": "3000000"}
    r = cliente_api.patch(f"/api/clientes/{a['id']}", json={"municipio": "Buga", "socios": [socio]})
    assert r.status_code == 200, r.text
    ficha = cliente_api.get(f"/api/clientes/{a['id']}").json()
    assert ficha["municipio"] == "Buga"
    s = ficha["socios"][0]
    assert (s["nombre"], s["cedula"], s["cargo"]) == ("Ana Ruiz", "20333444", "Gerente")
    assert Decimal(s["participacion"]) == Decimal("0.4") and Decimal(s["pagado"]) == Decimal("3000000")


def test_ficha_invalida_no_borra_los_socios(cliente_api):
    a = cliente_api.post("/api/clientes", json={"nit": "900777111", "razon_social": "UNO",
                                                "socios": [{"nombre": "Ana Ruiz"}]}).json()
    r = cliente_api.patch(f"/api/clientes/{a['id']}", json={"razon_social": "", "socios": []})
    assert r.status_code == 400
    assert len(cliente_api.get(f"/api/clientes/{a['id']}").json()["socios"]) == 1
