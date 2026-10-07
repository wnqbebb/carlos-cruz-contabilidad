"""Que un recálculo no pueda volver a borrar el trabajo de un periodo (H01, H08, H19).

El 6 de octubre de 2026 un archivo sin cuentas reemplazó el cierre de enero
2025 de un cliente y no quedó copia ni rastro. Cada prueba de aquí cierra una
de las puertas por donde se fue ese trabajo.
"""
from __future__ import annotations

import pytest

from app.repositorio import bitacora as repo_bitacora
from app.repositorio import clientes as repo_clientes
from app.repositorio import importaciones as repo_importaciones
from app.repositorio import periodos as repo


def _cliente(**extra) -> dict:
    return repo_clientes.crear({"nit": "[NIT]", "razon_social": "ANTARES SAS", **extra})


def _resultado(desde="2025-01-01", hasta="2025-01-31", *, activo="0", utilidad="0",
               cuentas=10, movimientos=5) -> dict:
    return {
        "empresa": {"periodo_desde": desde, "periodo_hasta": hasta},
        "resumen": {
            "total_activo": activo, "total_pasivo": "0", "total_patrimonio": "0",
            "ingresos": "0", "total_gastos": "0", "utilidad_neta": utilidad,
            "descuadre_esf": "0", "cuentas": cuentas, "movimientos": movimientos,
        },
    }


def _movs(valor="100"):
    return [{"cuenta": "110505", "nombre_cuenta": "Caja general", "debito": valor, "credito": "0"},
            {"cuenta": "4135", "nombre_cuenta": "Comercio", "debito": "0", "credito": valor}]


# ── Guarda 1: periodo cerrado ───────────────────────────────────────────────
def test_un_periodo_cerrado_no_se_recalcula_por_accidente(base_limpia):
    c = _cliente()
    p = repo.guardar_resultado(c["id"], _resultado(activo="37144505", utilidad="-2857975.72"))
    repo.guardar_movimientos(c["id"], p["id"], _movs("37144505"))
    repo.cerrar(c["id"], p["id"], [{"codigo": "110505", "nombre": "Caja", "debito": "37144505", "credito": "0"}])

    with pytest.raises(repo.PeriodoCerrado) as ex:
        repo.guardar_resultado(c["id"], _resultado(activo="0", utilidad="0"))
    assert "cerrado" in str(ex.value).lower()

    # Nada se movió: ni los indicadores, ni los movimientos, ni el cierre.
    quedo = repo.listar(c["id"])[0]
    assert quedo["estado"] == "cerrado"
    assert quedo["total_activo"] == "37144505.00"
    assert repo.movimientos(c["id"])["total"] == 2
    assert repo.listar_cierres(c["id"])[0]["cuentas"] == 1


def test_tras_reabrir_si_se_puede_recalcular(base_limpia):
    c = _cliente()
    p = repo.guardar_resultado(c["id"], _resultado(activo="37144505"))
    repo.cerrar(c["id"], p["id"], [{"codigo": "110505", "nombre": "Caja", "debito": "1", "credito": "0"}])
    repo.reabrir(p["id"])
    nuevo = repo.guardar_resultado(c["id"], _resultado(activo="500"))
    assert nuevo["estado"] == "calculado"
    assert nuevo["total_activo"] == "500.00"


# ── Guarda 2: cálculo vacío ─────────────────────────────────────────────────
@pytest.mark.parametrize("cuentas,movimientos", [(0, 0), (0, 5), (10, 0)])
def test_un_calculo_vacio_no_reemplaza_nada(base_limpia, cuentas, movimientos):
    c = _cliente()
    repo.guardar_resultado(c["id"], _resultado(activo="37144505"))

    with pytest.raises(repo.ResultadoVacio):
        repo.guardar_resultado(c["id"], _resultado(activo="0", cuentas=cuentas, movimientos=movimientos))

    assert repo.listar(c["id"])[0]["total_activo"] == "37144505.00"


def test_un_calculo_vacio_no_crea_periodos_en_blanco(base_limpia):
    c = _cliente()
    with pytest.raises(repo.ResultadoVacio):
        repo.guardar_resultado(c["id"], _resultado("2025-03-01", "2025-03-31", cuentas=0, movimientos=0))
    assert repo.listar(c["id"]) == []


# ── Historial ───────────────────────────────────────────────────────────────
def test_recalcular_deja_la_version_anterior_en_el_historial(base_limpia):
    c = _cliente()
    p = repo.guardar_resultado(c["id"], _resultado(activo="37144505", utilidad="-2857975.72"))
    repo.guardar_movimientos(c["id"], p["id"], _movs("37144505"))
    repo.guardar_resultado(c["id"], _resultado(activo="500", utilidad="100"))

    versiones = repo.versiones(p["id"])
    assert len(versiones) == 1
    assert versiones[0]["motivo"] == "recalculo"
    assert versiones[0]["total_activo"] == "37144505.00"
    assert versiones[0]["movimientos"] == 2


def test_restaurar_devuelve_cifras_movimientos_y_cierre(base_limpia):
    c = _cliente()
    p = repo.guardar_resultado(c["id"], _resultado(activo="37144505", utilidad="-2857975.72"))
    repo.guardar_movimientos(c["id"], p["id"], _movs("37144505"))
    repo.cerrar(c["id"], p["id"], [
        {"codigo": "110505", "nombre": "Caja general", "debito": "37144505", "credito": "0"},
        {"codigo": "3105", "nombre": "Capital", "debito": "0", "credito": "37800000"},
    ])
    repo.reabrir(p["id"])                                   # versión 1: el cierre bueno
    repo.guardar_resultado(c["id"], _resultado(activo="1"))  # versión 2: lo que había tras reabrir
    repo.guardar_movimientos(c["id"], p["id"], _movs("1"))

    buena = [v for v in repo.versiones(p["id"]) if v["con_cierre"]][0]
    repo.restaurar_version(buena["id"])

    quedo = repo.listar(c["id"])[0]
    assert quedo["total_activo"] == "37144505.00"
    assert quedo["utilidad"] == "-2857975.72"
    assert quedo["estado"] == "cerrado"
    cierre = repo.listar_cierres(c["id"])[0]
    assert cierre["cuentas"] == 2
    pagina = repo.movimientos(c["id"])
    assert pagina["total"] == 2
    assert pagina["suma_debito"] == "37144505.00"


def test_restaurar_no_destruye_el_estado_actual(base_limpia):
    c = _cliente()
    p = repo.guardar_resultado(c["id"], _resultado(activo="100"))
    repo.guardar_resultado(c["id"], _resultado(activo="200"))
    vieja = repo.versiones(p["id"])[0]
    repo.restaurar_version(vieja["id"])
    # La de 200 quedó guardada a su vez, así que se puede volver a ella.
    assert any(v["total_activo"] == "200.00" for v in repo.versiones(p["id"]))


def test_reabrir_guarda_el_cierre_en_vez_de_borrarlo(base_limpia):
    c = _cliente()
    p = repo.guardar_resultado(c["id"], _resultado(activo="1"))
    repo.cerrar(c["id"], p["id"], [{"codigo": "110505", "nombre": "Caja", "debito": "9", "credito": "0"}])
    repo.reabrir(p["id"])

    assert repo.listar_cierres(c["id"]) == []
    v = repo.versiones(p["id"])[0]
    assert v["motivo"] == "reapertura" and v["con_cierre"]
    assert repo.version(v["id"])["cierre"]["saldos"][0]["debito"] == "9"


def test_un_periodo_nuevo_no_genera_version_vacia(base_limpia):
    c = _cliente()
    p = repo.guardar_resultado(c["id"], _resultado(activo="1"))
    assert repo.versiones(p["id"]) == []


# ── Bitácora e importaciones (H08) ──────────────────────────────────────────
def test_cada_accion_deja_su_linea_en_la_bitacora(base_limpia, cliente_api):
    c = cliente_api.post("/api/clientes", json={"nit": "[NIT]", "razon_social": "ANTARES SAS"}).json()
    cliente_api.patch(f"/api/clientes/{c['id']}", json={"honorarios_mes": "300000"})
    cliente_api.delete(f"/api/clientes/{c['id']}")
    cliente_api.post(f"/api/clientes/{c['id']}/restaurar")

    acciones = [x["accion"] for x in repo_bitacora.listar(c["id"])]
    assert acciones == ["cliente_restaurado", "cliente_archivado", "cliente_editado", "cliente_creado"]
    assert repo_bitacora.listar(c["id"])[0]["titulo"] == "Cliente restaurado"


def test_la_bitacora_nunca_tumba_la_operacion(base_limpia, monkeypatch):
    def explota(*_a, **_k):
        raise RuntimeError("base caída")

    monkeypatch.setattr("app.repositorio.bitacora.conexion", explota)
    repo_bitacora.registrar("periodo_calculado", None, x=1)   # no debe lanzar


def test_subir_un_archivo_queda_registrado(base_limpia, cliente_api):
    c = cliente_api.post("/api/clientes", json={"nit": "[NIT]", "razon_social": "ANTARES SAS"}).json()
    r = cliente_api.post(f"/api/importar/demo?cliente_id={c['id']}&caso=basico")
    assert r.status_code == 200

    subidas = repo_importaciones.listar(c["id"])
    assert len(subidas) == 1
    assert subidas[0]["archivo"].endswith(".xlsx")
    assert len(subidas[0]["sha256"]) == 64
    assert subidas[0]["bytes"] > 0
    assert "archivos_subidos" in [x["accion"] for x in repo_bitacora.listar(c["id"])]


def test_el_mismo_archivo_dos_veces_se_avisa(base_limpia, cliente_api):
    """La huella es del contenido: el mismo archivo subido otra vez se reconoce."""
    from app.config import FUENTES

    c = cliente_api.post("/api/clientes", json={"nit": "[NIT]", "razon_social": "ANTARES SAS"}).json()
    contenido = (FUENTES / "CONTABILIDAD.xls").read_bytes()
    subir = lambda: cliente_api.post(
        f"/api/importar?cliente_id={c['id']}",
        files=[("archivos", ("CONTABILIDAD.xls", contenido))],
    ).json()

    assert subir()["repetidos"] == []
    repetido = subir()["repetidos"]
    assert repetido and repetido[0]["archivo"] == "CONTABILIDAD.xls"


# ── La API traduce las guardas a códigos que la pantalla entiende ───────────
def test_la_api_responde_409_con_el_periodo_cerrado(base_limpia, cliente_api):
    c = cliente_api.post("/api/clientes", json={"nit": "[NIT]", "razon_social": "ANTARES SAS"}).json()
    imp = cliente_api.post(f"/api/importar/demo?cliente_id={c['id']}&caso=completo").json()
    peticion = {"sesion_id": imp["sesion_id"], "cliente_id": c["id"],
                "mapeo": {i["normalizado"]: i["codigo"] for i in imp["mapeo"] if i.get("codigo")},
                "incluir": {h["id"]: h["incluir"] for h in imp["hojas"]}}
    r = cliente_api.post("/api/calcular", json=peticion)
    assert r.status_code == 200 and r.json()["guardado"] is True
    cliente_api.post(f"/api/cierre/{imp['sesion_id']}")

    r2 = cliente_api.post("/api/calcular", json=peticion)
    assert r2.status_code == 409
    detalle = r2.json()["detail"]
    assert detalle["codigo"] == "periodo_cerrado"
    assert detalle["periodo_id"]


def test_la_api_responde_422_con_un_calculo_vacio(base_limpia, cliente_api):
    c = cliente_api.post("/api/clientes", json={"nit": "[NIT]", "razon_social": "ANTARES SAS"}).json()
    imp = cliente_api.post(f"/api/importar/demo?cliente_id={c['id']}&caso=completo").json()
    r = cliente_api.post("/api/calcular", json={
        "sesion_id": imp["sesion_id"], "cliente_id": c["id"], "mapeo": {},
        "incluir": {h["id"]: False for h in imp["hojas"]},   # nada marcado
    })
    assert r.status_code == 422
    assert r.json()["detail"]["codigo"] == "resultado_vacio"
    assert repo.listar(c["id"]) == []
