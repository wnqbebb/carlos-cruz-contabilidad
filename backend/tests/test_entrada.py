"""Rescate: cada periodo guarda su ENTRADA comprimida y el resultado se rearma igual.

Es la base de tres cosas: editar dentro de la aplicación, versiones livianas y caber
10.000 clientes en la base gratuita. Si el resultado rearmado difiriera en un centavo
del calculado al subir, nada de eso serviría: por eso se compara entero.
"""
from __future__ import annotations

import pytest
from sqlalchemy import func, select

from app import db
from app.esquema import historial_periodos as TH
from app.esquema import periodo_entradas as TE
from app.esquema import resultados as TR
from app.repositorio import periodos as repo
from tests.test_archivos_variados import _calcular, _subir

# Lo que cambia entre dos corridas sin que cambie la contabilidad.
VOLATIL = {"guardado", "periodo", "movimientos_guardados", "aviso_guardado", "periodos_procesados"}


def _sin_volatil(d: dict) -> dict:
    return {k: v for k, v in d.items() if k not in VOLATIL}


def _caso(cliente_api, caso: str, nit: str) -> tuple[dict, dict]:
    c = cliente_api.post("/api/clientes", json={"nit": nit, "razon_social": f"CASO {caso.upper()} SAS"}).json()
    imp = cliente_api.post(f"/api/importar/demo?cliente_id={c['id']}&caso={caso}").json()
    peticion = {"sesion_id": imp["sesion_id"], "cliente_id": c["id"],
                "mapeo": {i["normalizado"]: i["codigo"] for i in imp["mapeo"] if i.get("codigo")},
                "incluir": {h["id"]: h["incluir"] for h in imp["hojas"]}}
    r = cliente_api.post("/api/calcular", json=peticion)
    assert r.status_code == 200, r.text
    return c, r.json()


@pytest.mark.parametrize("caso,nit", [("completo", "900100158"), ("mediocre", "900200111"), ("basico", "900300222")])
def test_el_resultado_rearmado_es_identico_al_calculado(cliente_api, caso, nit):
    _, calculado = _caso(cliente_api, caso, nit)
    pid = calculado["periodo"]["id"]
    with db.lectura() as cn:
        payload = cn.execute(select(TR.c.payload).where(TR.c.periodo_id == pid)).scalar()
        bytes_entrada = cn.execute(select(TE.c.bytes).where(TE.c.periodo_id == pid)).scalar()
    assert payload.get("_derivados_fuera") is True and "reportes" not in payload and "inventario" not in payload
    assert bytes_entrada and bytes_entrada < 60_000
    repo._cache_resultado.clear()
    rearmado = cliente_api.get(f"/api/periodos/{pid}/resultado").json()["resultado"]
    assert _sin_volatil(rearmado) == _sin_volatil(calculado)


@pytest.mark.parametrize("archivo", ["01_ventas_compras_bloques.xlsx", "11_libro_diario.csv",
                                     "15_inventario_inicial_y_conteo.xlsx", "16_balance_excel.xlsx"])
def test_rearmado_identico_con_archivos_variados(cliente_api, archivo):
    imp = _subir(cliente_api, archivo)
    calculado = _calcular(cliente_api, imp)
    pid = calculado["periodo"]["id"]
    repo._cache_resultado.clear()
    rearmado = cliente_api.get(f"/api/periodos/{pid}/resultado").json()["resultado"]
    assert _sin_volatil(rearmado) == _sin_volatil(calculado)


def test_la_version_guarda_solo_la_entrada_y_se_restaura_igual(cliente_api):
    c, primero = _caso(cliente_api, "completo", "900100158")
    pid = primero["periodo"]["id"]
    # Recalcular el mismo periodo deja una versión: liviana (sin resultado ni movimientos copiados).
    imp = cliente_api.post(f"/api/importar/demo?cliente_id={c['id']}&caso=completo").json()
    peticion = {"sesion_id": imp["sesion_id"], "cliente_id": c["id"],
                "mapeo": {i["normalizado"]: i["codigo"] for i in imp["mapeo"] if i.get("codigo")},
                "incluir": {h["id"]: h["incluir"] for h in imp["hojas"]}}
    assert cliente_api.post("/api/calcular", json=peticion).status_code == 200
    with db.lectura() as cn:
        v = cn.execute(select(TH).where(TH.c.periodo_id == pid)).one()
    assert v.entrada and v.resultado is None and v.movimientos == []
    assert v.periodo["_movimientos_n"] > 0
    movs_antes = len(repo.movimientos_de_periodo(pid))
    repo.restaurar_version(int(v.id))
    repo._cache_resultado.clear()
    restaurado = cliente_api.get(f"/api/periodos/{pid}/resultado").json()["resultado"]
    assert _sin_volatil(restaurado) == _sin_volatil(primero)
    assert len(repo.movimientos_de_periodo(pid)) == movs_antes
    with db.lectura() as cn:
        assert cn.execute(select(func.count()).select_from(TE).where(TE.c.periodo_id == pid)).scalar_one() == 1


def test_descargas_de_un_periodo_ligero_traen_todo(cliente_api):
    _, calculado = _caso(cliente_api, "completo", "900100158")
    pid = calculado["periodo"]["id"]
    repo._cache_resultado.clear()
    r = cliente_api.get(f"/api/periodos/{pid}/excel")
    assert r.status_code == 200 and len(r.content) > 20_000
    r = cliente_api.get(f"/api/periodos/{pid}/pdf")
    assert r.status_code == 200 and r.content[:4] == b"%PDF"


def test_libro_diario_viejo_fila_por_fila_se_compacta_igual(cliente_api):
    """Periodos guardados antes del rescate (una fila por línea) pasan a un bloque comprimido
    y el libro diario consultable queda idéntico."""
    from sqlalchemy import delete, insert

    from app.esquema import movimientos as TM
    from app.esquema import periodo_diarios as TD
    from app.utils.numeros import D, parse_fecha

    c, calculado = _caso(cliente_api, "completo", "900100158")
    pid = calculado["periodo"]["id"]
    antes = cliente_api.get(f"/api/clientes/{c['id']}/movimientos?por_pagina=2000").json()
    assert antes["total"] > 10
    # Simula la base vieja: las líneas como filas sueltas y sin bloque.
    lineas = repo.movimientos_de_periodo(pid)
    with db.conexion() as cn:
        cn.execute(delete(TD).where(TD.c.periodo_id == pid))
        cn.execute(insert(TM), [{**{k: v for k, v in m.items()}, "cliente_id": c["id"], "periodo_id": pid,
                                 "fecha": parse_fecha(m["fecha"]), "debito": D(m["debito"]), "credito": D(m["credito"]),
                                 "base_retencion": None if m["base_retencion"] is None else D(m["base_retencion"])}
                                for m in lineas])
    viejo = cliente_api.get(f"/api/clientes/{c['id']}/movimientos?por_pagina=2000").json()
    assert viejo == antes
    assert repo.compactar_diarios() == 1
    assert repo.compactar_diarios() == 0
    with db.lectura() as cn:
        assert cn.execute(select(func.count()).select_from(TM)).scalar_one() == 0
    assert cliente_api.get(f"/api/clientes/{c['id']}/movimientos?por_pagina=2000").json() == antes
    filtrado = cliente_api.get(f"/api/clientes/{c['id']}/movimientos?cuenta=11&por_pagina=5").json()
    assert all(m["cuenta"].startswith("11") for m in filtrado["movimientos"]) and len(filtrado["movimientos"]) <= 5
