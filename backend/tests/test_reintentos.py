"""Reintentos con espera creciente cuando la base no responde (H20)."""
from __future__ import annotations

import pytest
from sqlalchemy.exc import IntegrityError, OperationalError

from app import db


def _caida() -> OperationalError:
    return OperationalError("SELECT 1", {}, Exception("could not connect to server: Connection timed out"))


def test_reintenta_y_sigue_si_la_base_vuelve(monkeypatch):
    esperas = []
    monkeypatch.setattr(db.time, "sleep", esperas.append)
    intentos = iter([_caida(), _caida(), "conectado"])

    def abrir():
        r = next(intentos)
        if isinstance(r, Exception):
            raise r
        return r

    assert db.con_reintentos(abrir) == "conectado"
    assert esperas == [0.5, 1.5]          # espera creciente


def test_si_no_vuelve_dice_que_pasa_en_espanol(monkeypatch):
    esperas = []
    monkeypatch.setattr(db.time, "sleep", esperas.append)

    def abrir():
        raise _caida()

    with pytest.raises(db.BaseNoDisponible) as ex:
        db.con_reintentos(abrir)
    assert esperas == list(db.ESPERAS)
    assert "No hay conexión" in str(ex.value) and "no se perdió" in str(ex.value)


def test_un_error_que_no_es_de_conexion_no_se_reintenta(monkeypatch):
    esperas = []
    monkeypatch.setattr(db.time, "sleep", esperas.append)

    def abrir():
        raise IntegrityError("INSERT", {}, Exception("duplicate key"))

    with pytest.raises(IntegrityError):
        db.con_reintentos(abrir)
    assert esperas == []


def test_la_api_responde_503_con_mensaje_claro(cliente_api, monkeypatch):
    from app.repositorio import clientes as repo

    def sin_base(*_a, **_k):
        raise db.BaseNoDisponible(_caida())

    monkeypatch.setattr(repo, "listar", sin_base)
    r = cliente_api.get("/api/clientes")
    assert r.status_code == 503
    assert r.json()["detail"]["codigo"] == "sin_base"
    assert "Revise el internet" in r.json()["detail"]["mensaje"]
