"""v2.3 · Fase 2: los valores legales viven en la aplicación; no hay pantalla ni endpoint para editarlos."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from app.modelos import Empleado
from app.nomina import calculo, parametros


def test_la_pantalla_y_el_endpoint_ya_no_existen(cliente_api):
    assert cliente_api.get("/api/parametros").status_code == 404
    assert cliente_api.put("/api/parametros/2026", json={"smmlv": "1"}).status_code in (404, 405)


@pytest.mark.parametrize("anio,smmlv,aux,uvt", [(2025, "1423500", "200000", "49799"), (2026, "1750905", "249095", "52374")])
def test_valores_oficiales_con_su_fuente(anio, smmlv, aux, uvt):
    p = parametros.obtener(anio)
    assert (p["smmlv"], p["aux_transporte"], p["uvt"]) == (Decimal(smmlv), Decimal(aux), Decimal(uvt))
    assert "Decreto" in parametros.todos()[str(anio)]["_fuente"] and "Resolución DIAN" in parametros.todos()[str(anio)]["_fuente"]


@pytest.mark.parametrize("anio,basico,aux", [(2025, "1423500", "200000"), (2026, "1750905", "249095")])
def test_nomina_de_cada_anio_con_sus_valores(anio, basico, aux):
    liq = calculo.liquidar(Empleado("PERSONA EJEMPLO", salario_basico=Decimal(basico), aux_transporte="si", mes=3, año=anio), anio)
    assert liq.basico == Decimal(basico) and liq.aux == Decimal(aux)


def test_un_anio_sin_valores_no_inventa_nada():
    with pytest.raises(parametros.ParametrosFaltantes) as ex:
        parametros.obtener(2027)
    assert "Faltan los valores legales de 2027" in str(ex.value) and "Parámetros" not in str(ex.value)


def test_el_tablero_avisa_si_falta_el_anio_en_curso(cliente_api, monkeypatch):
    from app.inteligencia import tablero

    t = tablero.armar(date(2027, 2, 1))
    tarea = next(x for x in t["tareas"] if x["codigo"] == "VALORES_LEGALES")
    assert tarea["que"] == "Faltan los valores legales de 2027" and tarea["prioridad"] == "critica"
    assert not any(x["codigo"] == "VALORES_LEGALES" for x in tablero.armar(date(2026, 10, 8))["tareas"])


def test_salud_publica_solo_dice_ok_y_version(cliente_sin_sesion):
    r = cliente_sin_sesion.get("/api/salud").json()
    assert set(r) == {"ok", "version"}


def test_panel_sistema_sin_datos_tecnicos(cliente_api):
    r = cliente_api.get("/api/sistema").json()
    assert set(r) == {"conectado", "en_la_nube", "version"}
    texto = str(r).lower()
    assert not any(p in texto for p in ("supabase", "sqlite", "postgres", "proyecto", ":\\\\", "/users/"))
