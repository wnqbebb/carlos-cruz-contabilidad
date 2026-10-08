"""El tablero del contador (spec v2.2 · Fase 7) y sus agregados de cartera (H13)."""
from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal

from tests.test_archivos_variados import _calcular, _subir


def _tablero(api) -> dict:
    r = api.get("/api/tablero")
    assert r.status_code == 200, r.text
    return r.json()


def test_indicadores_de_la_cartera(cliente_api):
    cliente_api.post("/api/clientes", json={"nit": "900111001", "razon_social": "UNO", "honorarios_mes": "300000"})
    cliente_api.post("/api/clientes", json={"nit": "900111002", "razon_social": "DOS", "honorarios_mes": "450000.50"})
    archivado = cliente_api.post("/api/clientes", json={"nit": "900111003", "razon_social": "TRES",
                                                      "honorarios_mes": "999999"}).json()
    cliente_api.delete(f"/api/clientes/{archivado['id']}")
    t = _tablero(cliente_api)
    ind = t["indicadores"]
    assert ind["clientes_activos"] == 2
    assert Decimal(ind["honorarios_mensuales"]) == Decimal("750000.50")   # sin el archivado, exacto
    assert ind["al_dia"] + ind["atrasados"] == 2
    assert ind["atrasados"] == 2                                           # ninguno tiene periodos


def test_tareas_con_prioridad_cliente_que_por_que_y_accion(cliente_api):
    cliente_api.post("/api/clientes", json={"nit": "900111001", "razon_social": "SIN NADA"})
    imp = _subir(cliente_api, "11_libro_diario.csv")
    _calcular(cliente_api, imp)                                            # calculado, sin cerrar
    t = _tablero(cliente_api)
    codigos = {(x["codigo"], x["razon_social"]) for x in t["tareas"]}
    assert ("SIN_PERIODOS", "SIN NADA") in codigos
    cerrar = next(x for x in t["tareas"] if x["codigo"] == "SIN_CERRAR")
    assert cerrar["prioridad"] == "alta" and cerrar["que"] == "Cerrar el periodo calculado"
    assert cerrar["por_que"] and cerrar["accion"]["ruta"].endswith("?seccion=archivos")
    primera = next(x for x in t["tareas"] if x["codigo"] == "SIN_PERIODOS")
    assert primera["accion"]["tipo"] == "subir"
    # Ordenadas por prioridad.
    orden = {"critica": 0, "alta": 1, "media": 2}
    assert [orden[x["prioridad"]] for x in t["tareas"]] == sorted(orden[x["prioridad"]] for x in t["tareas"])


def test_posponer_hasta_manana_la_quita_y_queda_en_la_bitacora(cliente_api):
    c = cliente_api.post("/api/clientes", json={"nit": "900111001", "razon_social": "SIN NADA"}).json()
    clave = f"SIN_PERIODOS:{c['id']}"
    assert any(x["clave"] == clave for x in _tablero(cliente_api)["tareas"])
    r = cliente_api.post(f"/api/tareas/{clave}/posponer").json()
    assert r["hasta"] > date.today().isoformat()
    assert not any(x["clave"] == clave for x in _tablero(cliente_api)["tareas"])
    acciones = [a["accion"] for a in cliente_api.get(f"/api/clientes/{c['id']}/actividad").json()["actividad"]]
    assert "tarea_pospuesta" in acciones
    cliente_api.post(f"/api/tareas/{clave}/hacer")
    acciones = [a["accion"] for a in cliente_api.get(f"/api/clientes/{c['id']}/actividad").json()["actividad"]]
    assert "tarea_iniciada" in acciones


def test_preguntas_sin_responder_son_tarea(cliente_api):
    from tests.test_archivos_variados import BANCO

    p = cliente_api.post("/api/subir", files=[("archivos", ("03.xlsx", (BANCO / "03_fechas_copiadas_y_futuras.xlsx").read_bytes()))]).json()
    imp = cliente_api.post(f"/api/subir/{p['subida_id']}/confirmar",
                           json={"crear": {"nit": "900111009", "razon_social": "CON PREGUNTAS"}}).json()
    assert imp["preguntas"]
    tarea = next(x for x in _tablero(cliente_api)["tareas"] if x["codigo"] == "PREGUNTAS_PENDIENTES")
    assert imp["sesion_id"] in tarea["accion"]["ruta"]
    # La sesión se puede volver a abrir tal cual, con sus preguntas.
    reabierta = cliente_api.get(f"/api/importar/{imp['sesion_id']}").json()
    assert [q["id"] for q in reabierta["preguntas"]] == [q["id"] for q in imp["preguntas"]]
    _calcular(cliente_api, imp)
    assert not any(x["codigo"] == "PREGUNTAS_PENDIENTES" for x in _tablero(cliente_api)["tareas"])


def test_h13_meses_cerrados_abiertos_y_sin_contabilizar(cliente_api):
    imp = _subir(cliente_api, "11_libro_diario.csv")
    _calcular(cliente_api, imp, periodizacion="por_periodo")             # enero cerrado, febrero abierto
    t = _tablero(cliente_api)
    meses = {m["mes"]: m for m in t["meses"]}
    assert len(t["meses"]) == 12
    hoy = date.today()
    if "2026-01" in meses and "2026-02" in meses:
        # Aunque la ficha se creó hoy, los periodos de enero y febrero cuentan.
        assert meses["2026-01"]["cerrados"] == 1 and meses["2026-02"]["abiertos"] == 1
    actual = meses[f"{hoy.year}-{hoy.month:02d}"]
    assert actual["sin_contabilizar"] == 0                                 # el mes en curso no es atraso


def test_los_meses_cuentan_lo_guardado(cliente_api):
    """Con un cliente creado antes: enero cerrado, febrero abierto, marzo en adelante sin contabilizar."""
    from sqlalchemy import update

    from app.db import conexion
    from app.esquema import clientes as TC

    imp = _subir(cliente_api, "11_libro_diario.csv")
    with conexion() as cn:
        cn.execute(update(TC).where(TC.c.id == imp["cliente_id"]).values(creado=datetime(2025, 12, 1, tzinfo=timezone.utc)))
    _calcular(cliente_api, imp, periodizacion="por_periodo")
    meses = {m["mes"]: m for m in _tablero(cliente_api)["meses"]}
    if "2026-01" in meses:
        assert meses["2026-01"] == {"mes": "2026-01", "cerrados": 1, "abiertos": 0, "sin_contabilizar": 0}
    if "2026-02" in meses:
        assert meses["2026-02"] == {"mes": "2026-02", "cerrados": 0, "abiertos": 1, "sin_contabilizar": 0}
    if "2026-03" in meses:
        assert meses["2026-03"]["sin_contabilizar"] == 1


def test_recientes_y_actividad(cliente_api):
    for i in range(10):
        cliente_api.post("/api/clientes", json={"nit": f"90011100{i}", "razon_social": f"CLIENTE {i}"})
    t = _tablero(cliente_api)
    assert len(t["recientes"]) == 8
    assert len(t["actividad"]) == 8 and t["actividad"][0]["accion"] == "cliente_creado"
    assert t["actividad"][0]["razon_social"].startswith("CLIENTE")


def test_el_tablero_ya_no_trae_cifras_de_un_cliente_ni_nomina(cliente_api):
    t = _tablero(cliente_api)
    assert "serie" not in t and "pendientes" not in t


def test_h18_los_datos_del_contador_salen_de_la_configuracion(cliente_api):
    c = cliente_api.get("/api/contador").json()
    assert c["tarjeta_profesional"] and c["municipio"]
    # v2.3 · Fase 2: ya no se editan desde la interfaz.
    assert cliente_api.put("/api/contador", json={"municipio": "Buga"}).status_code in (404, 405)


def test_cerrar_un_periodo_guardado_sin_sesion_de_trabajo(cliente_api):
    """v2.3 · Fase 3: el expediente cierra el periodo con los saldos guardados, sin volver a subir nada."""
    from tests.test_archivos_variados import _calcular, _subir

    imp = _subir(cliente_api, "11_libro_diario.csv")
    res = _calcular(cliente_api, imp)
    pid = res["periodo"]["id"]
    r = cliente_api.post(f"/api/periodos/{pid}/cerrar")
    assert r.status_code == 200, r.text
    periodos = cliente_api.get(f"/api/clientes/{imp['cliente_id']}/periodos").json()
    assert periodos["periodos"][0]["estado"] == "cerrado" and periodos["cierres"]
    assert cliente_api.post(f"/api/periodos/{pid}/cerrar").status_code == 409
