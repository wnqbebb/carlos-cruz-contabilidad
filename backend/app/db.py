"""Motor de base de datos: Supabase/Postgres en producción, SQLite en local.

El resto de la aplicación nunca habla con SQLAlchemy directamente: usa los
módulos de `app/repositorio/`. Aquí solo vive la conexión y su diagnóstico.
"""
from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Connection, Engine

from .config import DB_URL, ES_POSTGRES
from .esquema import metadatos

log = logging.getLogger("carloscruz.db")


def _crear_motor() -> Engine:
    if ES_POSTGRES:
        # Supabase recomienda el pooler de TRANSACCIONES (puerto 6543). Eso trae
        # dos consecuencias que hay que atender o la aplicación falla:
        #
        # 1. `prepare_threshold=None` es OBLIGATORIO. En modo transacción el
        #    pooler reparte cada consulta a un backend distinto, así que las
        #    sentencias preparadas del servidor que registra psycopg3 chocan
        #    entre sí: "prepared statement _pg3_0 already exists" y el cálculo
        #    se cae con error 500. Sin preparar en el servidor no hay colisión.
        #
        # 2. `pool_pre_ping` cuesta un viaje extra en CADA uso de la conexión.
        #    Con la base al otro lado del continente (~186 ms por viaje) eso se
        #    nota en todas las pantallas. Se cambia por reciclar la conexión a
        #    los 4 minutos, muy por debajo de lo que el pooler la mantiene viva.
        #
        # NO poner `pool_reset_on_return=None`: ahorra un viaje pero deja estado
        # de sesión colgando entre peticiones. Fue exactamente lo que destapó el
        # choque de sentencias preparadas.
        return create_engine(
            DB_URL,
            future=True,
            pool_pre_ping=False,
            pool_size=5,
            max_overflow=10,
            pool_recycle=240,
            connect_args={
                "connect_timeout": 10,
                "application_name": "carloscruz",
                "prepare_threshold": None,
            },
        )
    motor = create_engine(DB_URL, future=True, connect_args={"timeout": 30})

    @event.listens_for(motor, "connect")
    def _ajustes_sqlite(dbapi, _registro):  # pragma: no cover - configuración del driver
        cur = dbapi.cursor()
        cur.execute("PRAGMA journal_mode=WAL")
        cur.execute("PRAGMA foreign_keys=ON")
        cur.execute("PRAGMA synchronous=NORMAL")
        cur.close()

    return motor


motor_db: Engine = _crear_motor()

_tablas_listas = False


def preparar() -> None:
    """Crea las tablas si falta alguna.

    En SQLite se crean siempre (es la copia local de trabajo).
    En Postgres solo se crean las que falten: el esquema oficial es
    `supabase/migraciones/001_esquema.sql`, que trae además índices de
    búsqueda, vistas y restricciones que SQLAlchemy no reproduce.
    """
    global _tablas_listas
    if _tablas_listas:
        return
    metadatos.create_all(motor_db, checkfirst=True)
    _columnas_nuevas()
    _tablas_listas = True


def _columnas_nuevas() -> None:
    """Agrega las columnas que la versión nueva trae y la base todavía no tiene.

    `create_all` crea tablas, pero no agrega columnas a una tabla que ya existe.
    Las columnas nuevas son todas opcionales o con valor por defecto, así que
    agregarlas no cambia ningún dato guardado. El SQL equivalente para Supabase
    está en `supabase/migraciones/004_ficha_y_notas.sql`.
    """
    from sqlalchemy import inspect

    insp = inspect(motor_db)
    pendientes = []
    for tabla in metadatos.sorted_tables:
        if not insp.has_table(tabla.name):
            continue
        existentes = {c["name"] for c in insp.get_columns(tabla.name)}
        for col in tabla.columns:
            if col.name not in existentes:
                pendientes.append((tabla.name, col))
    if not pendientes:
        return
    with motor_db.begin() as cn:
        for nombre, col in pendientes:
            tipo = col.type.compile(dialect=motor_db.dialect)
            defecto = ""
            if col.default is not None and getattr(col.default, "is_scalar", False):
                valor = col.default.arg
                defecto = f" DEFAULT {int(valor) if isinstance(valor, bool) else repr(str(valor))}"
            nulo = " NOT NULL" if not col.nullable and defecto else ""
            cn.execute(text(f'ALTER TABLE {nombre} ADD COLUMN {col.name} {tipo}{defecto}{nulo}'))
            log.info("Columna agregada: %s.%s", nombre, col.name)


@contextmanager
def conexion() -> Iterator[Connection]:
    """Conexión con transacción: confirma al salir bien, revierte si hay error."""
    preparar()
    with motor_db.begin() as cn:
        yield cn


@contextmanager
def lectura() -> Iterator[Connection]:
    """Conexión de solo lectura.

    Va en AUTOCOMMIT a propósito. Sin eso, SQLAlchemy abre una transacción y
    hace ROLLBACK al devolver la conexión al pool: un viaje más a la base por
    cada bloque. Contra Supabase en São Paulo cada viaje cuesta ~186 ms, así
    que ese rollback inútil era medio segundo de más en cada pantalla.
    Aquí no se escribe nada, así que no hay nada que revertir.
    """
    preparar()
    with motor_db.connect().execution_options(isolation_level="AUTOCOMMIT") as cn:
        yield cn


def diagnostico() -> dict:
    """Comprueba la conexión. Se usa en /api/salud y en la pantalla de ajustes."""
    try:
        with motor_db.connect() as cn:
            cn.execute(text("select 1"))
        return {"conectado": True, "motor": "postgres" if ES_POSTGRES else "sqlite", "error": ""}
    except Exception as ex:  # la interfaz necesita el motivo en español, no un stacktrace
        log.warning("No se pudo conectar a la base: %s", ex)
        return {
            "conectado": False,
            "motor": "postgres" if ES_POSTGRES else "sqlite",
            "error": _mensaje_humano(ex),
        }


def _mensaje_humano(ex: Exception) -> str:
    t = str(ex).lower()
    if "password authentication failed" in t:
        return "La contraseña de la base de datos es incorrecta. Revise DATABASE_URL en backend/.env."
    if "could not translate host name" in t or "name or service not known" in t:
        return "No se encontró el servidor de Supabase. Revise que DATABASE_URL esté completa."
    if "timeout" in t or "timed out" in t:
        return "Supabase no respondió a tiempo. Revise su conexión a internet."
    if "no module named" in t and "psycopg" in t:
        return "Falta instalar psycopg. Ejecute: pip install -r backend/requirements.txt"
    if "does not exist" in t and "relation" in t:
        return "Las tablas no existen todavía. Ejecute supabase/migraciones/001_esquema.sql."
    return str(ex).splitlines()[0][:300]
