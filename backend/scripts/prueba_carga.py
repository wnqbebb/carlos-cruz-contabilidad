"""Prueba de carga: ¿aguanta la aplicación 10.000 clientes? (rescate · prioridad del usuario)

Copia, dentro de una base Postgres DE PRUEBAS, los clientes de demostración ya cargados
(con sus periodos, resultados, entradas, cierres y movimientos) hasta llegar a N clientes,
y mide cuánto tardan las pantallas que recorren toda la cartera.

    CC_SSL=require DATABASE_URL=postgresql://postgres@127.0.0.1:54329/cc \\
        python backend/scripts/prueba_carga.py --clientes 10000 --periodos 3

Nunca se corre contra la base real: exige que el nombre de la base contenga «cc», «carga» o «prueba»
y que ya existan los clientes de demostración (generar_historicos.py).
"""
from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
import time
from pathlib import Path
from urllib.parse import urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("ALMACENAMIENTO", "supabase")
os.environ.setdefault("CC_SIN_LLAVERO", "1")
os.environ.setdefault("CC_SIN_RESPALDO", "1")
os.environ.setdefault("CC_LIMITE_GENERAL", "1000000")
os.environ.setdefault("CC_LIMITE_COSTOSAS", "1000000")

from sqlalchemy import text  # noqa: E402

from app.db import motor_db  # noqa: E402

SEMBRAR = """
-- Plantilla: los periodos de los clientes de demostración (los N más recientes de cada uno).
create temp table plantilla as
select p.*, row_number() over (partition by p.cliente_id order by p.desde desc) as n
from periodos p join clientes c on c.id = p.cliente_id where c.demo;
delete from plantilla where n > :periodos;

create temp table nuevos as
select gen_random_uuid() as id, g as i,
       (select id from clientes where demo order by razon_social offset (g % (select count(*) from clientes where demo)) limit 1) as origen
from generate_series(1, :faltan) g;

insert into clientes (id, nit, dv, razon_social, sigla, tipo_persona, regimen, grupo_niif, responsable_iva, tarifa_renta,
                      municipio, departamento, capital_suscrito, valor_nominal_accion, honorarios_mes, periodicidad, estado,
                      etiquetas, notas, capital_autorizado, capital_pagado, numero_acciones, demo, buscable)
select n.id, (800000000 + n.i)::text, '0', c.razon_social || ' ' || n.i, c.sigla, c.tipo_persona, c.regimen, c.grupo_niif,
       c.responsable_iva, c.tarifa_renta, c.municipio, c.departamento, c.capital_suscrito, c.valor_nominal_accion,
       c.honorarios_mes, c.periodicidad, 'activo',
       case when n.i % 3 = 0 then array['solo_renta','renta']::text[] else array['Carga']::text[] end,
       '', c.capital_autorizado, c.capital_pagado, c.numero_acciones, false,
       upper(c.buscable || ' ' || n.i || ' ' || (800000000 + n.i))
from nuevos n join clientes c on c.id = n.origen;

create temp table mapa as
select n.id as cliente_nuevo, p.id as periodo_viejo, gen_random_uuid() as periodo_nuevo
from nuevos n join plantilla p on p.cliente_id = n.origen;

insert into periodos (id, cliente_id, desde, hasta, etiqueta, estado, total_activo, total_pasivo, total_patrimonio,
                      total_ingresos, total_gastos, utilidad, descuadre, cuadra, cuentas, calculado_en, cerrado_en, nota)
select m.periodo_nuevo, m.cliente_nuevo, p.desde, p.hasta, p.etiqueta, p.estado, p.total_activo, p.total_pasivo,
       p.total_patrimonio, p.total_ingresos, p.total_gastos, p.utilidad, p.descuadre, p.cuadra, p.cuentas,
       p.calculado_en, p.cerrado_en, p.nota
from mapa m join periodos p on p.id = m.periodo_viejo;

insert into resultados (periodo_id, cliente_id, payload, peticion, version)
select m.periodo_nuevo, m.cliente_nuevo, r.payload, r.peticion, r.version
from mapa m join resultados r on r.periodo_id = m.periodo_viejo;

insert into periodo_entradas (periodo_id, cliente_id, contenido, bytes)
select m.periodo_nuevo, m.cliente_nuevo, e.contenido, e.bytes
from mapa m join periodo_entradas e on e.periodo_id = m.periodo_viejo;

insert into cierres (cliente_id, periodo_id, fecha_corte, saldos, cuentas)
select m.cliente_nuevo, m.periodo_nuevo, c.fecha_corte, c.saldos, c.cuentas
from mapa m join cierres c on c.periodo_id = m.periodo_viejo;

insert into movimientos (cliente_id, periodo_id, fecha, cuenta, nombre_cuenta, debito, credito, comprobante, tipo,
                         tercero_id, tercero_nombre, descripcion, origen, base_retencion)
select m.cliente_nuevo, m.periodo_nuevo, x.fecha, x.cuenta, x.nombre_cuenta, x.debito, x.credito, x.comprobante, x.tipo,
       x.tercero_id, x.tercero_nombre, x.descripcion, x.origen, x.base_retencion
from mapa m join movimientos x on x.periodo_id = m.periodo_viejo;
analyze;
"""


def sembrar(clientes: int, periodos: int) -> None:
    with motor_db.begin() as cn:
        hay = cn.execute(text("select count(*) from clientes")).scalar_one()
        demos = cn.execute(text("select count(*) from clientes where demo")).scalar_one()
        if not demos:
            raise SystemExit("Primero cargue la demostración (backend/demo/generar_historicos.py).")
        faltan = clientes - hay
        if faltan <= 0:
            print(f"Ya hay {hay} clientes: no se siembra nada.")
            return
        t = time.time()
        for sentencia in [s for s in SEMBRAR.split(";\n") if s.strip()]:
            cn.execute(text(sentencia), {"faltan": faltan, "periodos": periodos})
        print(f"Sembrados {faltan} clientes en {time.time() - t:.0f} s.")


def medir(repeticiones: int = 3) -> list[dict]:
    from fastapi.testclient import TestClient

    from app.main import app

    salida = []
    with TestClient(app) as c:
        usuario, clave = os.environ["CC_USUARIO_CARGA"], os.environ["CC_CLAVE_CARGA"]
        r = c.post("/api/sesion", json={"usuario": usuario, "clave": clave})
        r.raise_for_status()
        c.headers["x-csrf"] = r.json()["csrf"]
        un_cliente = c.get("/api/clientes?por_pagina=1&orden=razon_social").json()["clientes"][0]["id"]
        periodos = c.get(f"/api/clientes/{un_cliente}/periodos").json()
        un_periodo = (periodos.get("periodos") if isinstance(periodos, dict) else periodos)[0]["id"]
        rutas = [
            ("Lista de clientes (página 1)", "/api/clientes?por_pagina=50"),
            ("Lista ordenada por utilidad", "/api/clientes?por_pagina=50&orden=utilidad&descendente=true"),
            ("Buscar «panader»", "/api/buscar?q=panader"),
            ("Buscar por NIT", "/api/buscar?q=800004321"),
            ("Tablero del contador", "/api/tablero"),
            ("Cartera de renta 2025", "/api/renta/cartera?anio=2025"),
            ("Ficha de un cliente", f"/api/clientes/{un_cliente}"),
            ("Periodos de un cliente", f"/api/clientes/{un_cliente}/periodos"),
            ("Resultado de un periodo (rearmado)", f"/api/periodos/{un_periodo}/resultado"),
        ]
        for nombre, ruta in rutas:
            tiempos, estado, peso = [], 0, 0
            for _ in range(repeticiones):
                t = time.time()
                r = c.get(ruta)
                tiempos.append(time.time() - t)
                estado, peso = r.status_code, len(r.content)
            salida.append({"pantalla": nombre, "ruta": ruta, "estado": estado, "kb": round(peso / 1024),
                           "primera_s": round(tiempos[0], 2), "mediana_s": round(statistics.median(tiempos), 2)})
            print(f"{nombre:40s} {estado}  {salida[-1]['primera_s']:6.2f} s  mediana {salida[-1]['mediana_s']:6.2f} s  "
                  f"{salida[-1]['kb']:6d} KB", flush=True)
    return salida


def tamano() -> dict:
    with motor_db.connect() as cn:
        total = cn.execute(text("select pg_database_size(current_database())")).scalar_one()
        filas = cn.execute(text(
            "select relname, pg_total_relation_size(relid) from pg_statio_user_tables order by 2 desc limit 8")).all()
        n = {t: cn.execute(text(f"select count(*) from {t}")).scalar_one()  # nosemgrep: nombres fijos
             for t in ("clientes", "periodos", "movimientos")}
    return {"base_mb": round(total / 1e6, 1), "tablas_mb": {r[0]: round(r[1] / 1e6, 1) for r in filas}, **n}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--clientes", type=int, default=10000)
    ap.add_argument("--periodos", type=int, default=3)
    ap.add_argument("--solo-medir", action="store_true")
    ap.add_argument("--salida", default="")
    a = ap.parse_args()
    base = urlsplit(os.environ.get("DATABASE_URL", "")).path.strip("/")
    if not any(p in base for p in ("cc", "carga", "prueba")):
        raise SystemExit("Por seguridad, esta prueba solo corre contra una base de pruebas.")
    if not a.solo_medir:
        sembrar(a.clientes, a.periodos)
    t = tamano()
    print(json.dumps(t, ensure_ascii=False))
    resultados = medir()
    if a.salida:
        Path(a.salida).write_text(json.dumps({"tamano": t, "tiempos": resultados}, ensure_ascii=False, indent=2),
                                  encoding="utf-8")


if __name__ == "__main__":
    main()
