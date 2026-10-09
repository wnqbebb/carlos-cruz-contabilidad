"""Inicio de sesión del contador (A2, rehecho en la v2.3 · Fase 6: sesiones en el servidor)."""
from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import update

from app import sesion
from app.main import app
from tests.conftest import CLAVE_PRUEBA, USUARIO_PRUEBA, entrar


def rutas_protegidas():
    """Todas las rutas registradas de la API (el esquema se arma aunque no se publique)."""
    for ruta, metodos in app.openapi()["paths"].items():
        if ruta.startswith("/api/") and ruta.rstrip("/") not in sesion.PUBLICAS:
            for metodo in metodos:
                yield metodo.upper(), re.sub(r"\{[^}]+\}", "x", ruta)


def test_sin_sesion_toda_la_api_responde_401(cliente_sin_sesion):
    rutas = list(rutas_protegidas())
    assert len(rutas) > 60
    for metodo, ruta in rutas:
        r = cliente_sin_sesion.request(metodo, ruta)
        assert r.status_code == 401, f"{metodo} {ruta} → {r.status_code}"
        assert r.json()["detail"]["codigo"] == "sin_sesion"


def test_lo_publico_no_pide_sesion(cliente_sin_sesion):
    assert cliente_sin_sesion.get("/api/salud").json().keys() == {"ok", "version"}
    estado = cliente_sin_sesion.get("/api/sesion").json()
    assert estado["activa"] is False and estado["configurado"] is True and estado["csrf"] is None
    assert cliente_sin_sesion.get("/").status_code in (200, 404)


def test_entrar_usar_y_salir_la_cookie_vieja_ya_no_sirve(cliente_sin_sesion):
    c = cliente_sin_sesion
    sesion.olvidar_fallos()
    r = c.post("/api/sesion", json={"usuario": USUARIO_PRUEBA.upper(), "clave": CLAVE_PRUEBA})
    assert r.status_code == 200
    cookie = r.headers["set-cookie"].lower()
    assert "httponly" in cookie and "samesite=lax" in cookie and "max-age=43200" in cookie
    assert "secure" not in cookie                        # http://localhost: sin Secure
    vieja = c.cookies.get(sesion.COOKIE)
    c.headers[sesion.ENCABEZADO_CSRF] = r.json()["csrf"]
    assert c.get("/api/clientes").status_code == 200
    assert c.post("/api/sesion/salir").status_code == 200
    assert c.get("/api/clientes").status_code == 401
    # La cookie anterior, puesta a mano, tampoco sirve: la sesión se cerró en el servidor.
    c.cookies.set(sesion.COOKIE, vieja)
    assert c.get("/api/clientes").status_code == 401


def test_al_ingresar_se_rota_la_sesion(cliente_sin_sesion):
    c = cliente_sin_sesion
    entrar(c)
    primera = c.cookies.get(sesion.COOKIE)
    entrar(c)
    assert c.cookies.get(sesion.COOKIE) != primera
    assert sesion.leer(primera) is None


def test_cookie_secure_detras_de_https(cliente_sin_sesion):
    sesion.olvidar_fallos()
    r = cliente_sin_sesion.post("/api/sesion", json={"usuario": USUARIO_PRUEBA, "clave": CLAVE_PRUEBA},
                                headers={"x-forwarded-proto": "https"})
    assert "secure" in r.headers["set-cookie"].lower()


def test_clave_equivocada_y_limite_de_intentos(cliente_sin_sesion):
    c = cliente_sin_sesion
    sesion.olvidar_fallos()
    for _ in range(sesion.MAX_FALLOS):
        r = c.post("/api/sesion", json={"usuario": USUARIO_PRUEBA, "clave": "no-es"})
        assert r.status_code == 401 and r.json()["detail"]["mensaje"] == "Usuario o contraseña incorrectos."
    r = c.post("/api/sesion", json={"usuario": USUARIO_PRUEBA, "clave": CLAVE_PRUEBA})
    assert r.status_code == 429 and "Espere" in r.json()["detail"]["mensaje"]
    sesion.olvidar_fallos()
    assert c.post("/api/sesion", json={"usuario": USUARIO_PRUEBA, "clave": CLAVE_PRUEBA}).status_code == 200


def test_token_basura_no_sirve():
    assert sesion.leer("basura") is None and sesion.leer(None) is None and sesion.leer("x" * 43) is None


def _envejecer(token: str, **cambios):
    from app.db import conexion
    from app.esquema import sesiones_acceso as TS

    with conexion() as cn:
        cn.execute(update(TS).where(TS.c.id == sesion._hash(token)).values(**cambios))
    sesion.olvidar_fallos()  # también olvida lo recordado en memoria


def test_vence_por_inactividad(cliente_api):
    token = cliente_api.cookies.get(sesion.COOKIE)
    assert cliente_api.get("/api/tablero").status_code == 200
    _envejecer(token, ultima=datetime.now(timezone.utc) - timedelta(seconds=sesion.INACTIVIDAD + 5))
    assert cliente_api.get("/api/tablero").status_code == 401


def test_vence_a_las_12_horas_aunque_se_use(cliente_api):
    token = cliente_api.cookies.get(sesion.COOKIE)
    _envejecer(token, expira=datetime.now(timezone.utc) - timedelta(seconds=1))
    assert cliente_api.get("/api/tablero").status_code == 401


def test_cerrar_todas_las_sesiones(cliente_api):
    from fastapi.testclient import TestClient

    with TestClient(app) as otro:
        entrar(otro)
        assert otro.get("/api/tablero").status_code == 200
        r = cliente_api.post("/api/acceso/sesiones/cerrar-todas")
        assert r.status_code == 200 and r.json()["cerradas"] >= 1
        assert otro.get("/api/tablero").status_code == 401
    assert cliente_api.get("/api/tablero").status_code == 200   # la propia sigue


@pytest.mark.parametrize("ruta", ["/api/tablero", "/api/clientes/demostracion"])
def test_con_sesion_responde(cliente_api, ruta):
    assert cliente_api.get(ruta).status_code == 200


def test_entrar_helper_funciona_en_cliente_nuevo():
    from fastapi.testclient import TestClient

    with TestClient(app) as c:
        assert c.get("/api/tablero").status_code == 401
        entrar(c)
        assert c.get("/api/tablero").status_code == 200
