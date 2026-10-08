"""Inicio de sesión del contador (adición A2)."""
from __future__ import annotations

import re
import time

import pytest

from app import sesion
from app.main import app
from tests.conftest import CLAVE_PRUEBA, USUARIO_PRUEBA, entrar


def _rutas_protegidas():
    # Todas las rutas que publica la API (el esquema OpenAPI las lista todas, también las de routers incluidos).
    for ruta, metodos in app.openapi()["paths"].items():
        if ruta.startswith("/api/") and ruta not in sesion.PUBLICAS:
            for metodo in metodos:
                yield metodo.upper(), re.sub(r"\{[^}]+\}", "x", ruta)


def test_sin_sesion_toda_la_api_responde_401(cliente_sin_sesion):
    rutas = list(_rutas_protegidas())
    assert len(rutas) > 45
    for metodo, ruta in rutas:
        r = cliente_sin_sesion.request(metodo, ruta)
        assert r.status_code == 401, f"{metodo} {ruta} → {r.status_code}"
        assert r.json()["detail"]["codigo"] == "sin_sesion"


def test_lo_publico_no_pide_sesion(cliente_sin_sesion):
    assert cliente_sin_sesion.get("/api/salud").status_code == 200
    assert cliente_sin_sesion.get("/api/sesion").json() == {"activa": False, "usuario": None, "configurado": True}
    # La interfaz (la pantalla de ingreso) se sirve sin sesión.
    assert cliente_sin_sesion.get("/").status_code in (200, 404)


def test_entrar_usar_y_salir(cliente_sin_sesion):
    c = cliente_sin_sesion
    sesion.olvidar_fallos()
    r = c.post("/api/sesion", json={"usuario": USUARIO_PRUEBA.upper(), "clave": CLAVE_PRUEBA})
    assert r.status_code == 200
    cookie = r.headers["set-cookie"].lower()
    assert "httponly" in cookie and "samesite=lax" in cookie and "max-age=43200" in cookie
    assert "secure" not in cookie                        # http://localhost: sin Secure
    assert c.get("/api/sesion").json()["activa"] is True
    assert c.get("/api/clientes").status_code == 200
    assert c.post("/api/sesion/salir").status_code == 200
    assert c.get("/api/clientes").status_code == 401


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
    # Bloqueado aunque ahora ponga la clave buena.
    r = c.post("/api/sesion", json={"usuario": USUARIO_PRUEBA, "clave": CLAVE_PRUEBA})
    assert r.status_code == 429 and "Espere" in r.json()["detail"]["mensaje"]
    sesion.olvidar_fallos()
    assert c.post("/api/sesion", json={"usuario": USUARIO_PRUEBA, "clave": CLAVE_PRUEBA}).status_code == 200


def test_cookie_alterada_o_vencida_no_sirve(cliente_sin_sesion, monkeypatch):
    buena = sesion.emitir(USUARIO_PRUEBA)
    assert sesion.leer(buena) == USUARIO_PRUEBA
    carga, firma = buena.rsplit(".", 1)
    assert sesion.leer(carga + "." + firma[:-2] + "AA") is None
    assert sesion.leer("basura") is None and sesion.leer(None) is None
    otra = sesion.emitir("intruso")                     # firmada, pero de otro usuario
    assert sesion.leer(otra) is None
    real = time.time
    monkeypatch.setattr(sesion.time, "time", lambda: real() + sesion.DURACION + 5)
    assert sesion.leer(buena) is None


def test_sin_usuario_creado_lo_dice(cliente_sin_sesion, monkeypatch):
    monkeypatch.delenv("CC_CLAVE_HASH")
    r = cliente_sin_sesion.post("/api/sesion", json={"usuario": "x", "clave": "y"})
    assert r.status_code == 503 and "crear_usuario.py" in r.json()["detail"]["mensaje"]


def test_crear_usuario_guarda_hash_y_clave_de_sesion(tmp_path):
    import bcrypt

    import crear_usuario

    archivo = tmp_path / ".env"
    archivo.write_text("DATABASE_URL=algo\nCLAVE_SESION=\n", encoding="utf-8")
    assert crear_usuario.main(["--usuario", "carlos", "--clave", "corta", "--archivo", str(archivo)]) == 1
    assert crear_usuario.main(["--usuario", "carlos", "--clave", "una-clave-larga", "--archivo", str(archivo)]) == 0
    datos = dict(l.split("=", 1) for l in archivo.read_text(encoding="utf-8").splitlines() if "=" in l)
    assert datos["DATABASE_URL"] == "algo" and datos["CC_USUARIO"] == "carlos"
    assert bcrypt.checkpw(b"una-clave-larga", datos["CC_CLAVE_HASH"].encode())
    assert "una-clave-larga" not in archivo.read_text(encoding="utf-8")
    assert len(datos["CLAVE_SESION"]) >= 32 and datos["CLAVE_SESION"] != "cambie-esta-clave-por-una-larga-y-aleatoria"
    # Cambiar la contraseña no duplica líneas ni cambia la clave de sesión.
    firma = datos["CLAVE_SESION"]
    assert crear_usuario.main(["--usuario", "carlos", "--clave", "otra-clave-larga", "--archivo", str(archivo)]) == 0
    texto = archivo.read_text(encoding="utf-8")
    assert texto.count("CC_CLAVE_HASH=") == 1 and f"CLAVE_SESION={firma}" in texto


@pytest.mark.parametrize("ruta", ["/api/tablero", "/api/clientes/demostracion"])
def test_con_sesion_responde(cliente_api, ruta):
    assert cliente_api.get(ruta).status_code == 200


def test_entrar_helper_funciona_en_cliente_nuevo():
    from fastapi.testclient import TestClient

    with TestClient(app) as c:
        assert c.get("/api/tablero").status_code == 401
        entrar(c)
        assert c.get("/api/tablero").status_code == 200
