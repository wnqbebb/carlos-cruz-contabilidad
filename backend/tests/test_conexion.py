"""Configuración del motor de base de datos.

Son pruebas de configuración, no de lógica: fijan decisiones que costaron caro
descubrir y que, si alguien revierte, rompen la aplicación en producción pero
no en local (las pruebas corren sobre SQLite).
"""
from __future__ import annotations

import inspect

from app import db


def _fuente_del_motor() -> str:
    """Código de `_crear_motor` SIN comentarios.

    Los comentarios nombran las opciones que NO hay que usar, así que si se
    dejaran dentro, la comprobación daría un falso positivo.
    """
    lineas = []
    for linea in inspect.getsource(db._crear_motor).splitlines():
        sin_comentario = linea.split("#", 1)[0]
        if sin_comentario.strip():
            lineas.append(sin_comentario)
    return chr(10).join(lineas)


def test_postgres_no_prepara_sentencias_en_el_servidor():
    """`prepare_threshold=None` es obligatorio con el pooler de Supabase.

    El pooler de transacciones reparte cada consulta a un backend distinto, así
    que las sentencias preparadas que registra psycopg3 chocan entre sí:
    «prepared statement "_pg3_0" already exists» y el cálculo responde 500.
    Pasó de verdad; no se quita sin cambiar de modo de pooler.
    """
    fuente = _fuente_del_motor()
    assert '"prepare_threshold": None' in fuente, (
        "Falta prepare_threshold=None en connect_args. Sin eso, calcular un "
        "periodo contra Supabase falla con DuplicatePreparedStatement."
    )


def test_la_conexion_se_limpia_al_devolverla_al_pool():
    """`pool_reset_on_return=None` ahorra un viaje pero deja estado colgando.

    Se probó para ganar velocidad y fue justo lo que destapó el choque de
    sentencias preparadas. La limpieza por defecto se queda.
    """
    assert "pool_reset_on_return" not in _fuente_del_motor(), (
        "No desactive la limpieza de la conexión al devolverla al pool: deja "
        "estado de sesión entre peticiones."
    )


def test_la_lectura_va_en_autocommit():
    """Sin AUTOCOMMIT cada lectura hace un ROLLBACK inútil.

    Contra una base remota eso es un viaje de más (~186 ms) en cada bloque de
    lectura, y hay varios por pantalla.
    """
    assert 'isolation_level="AUTOCOMMIT"' in inspect.getsource(db.lectura)


def test_el_diagnostico_traduce_los_errores_a_espanol():
    """El contador tiene que poder leer qué falló sin ver un stacktrace."""
    casos = {
        "password authentication failed for user": "contraseña",
        "could not translate host name": "servidor",
        "connection timeout expired": "tiempo",
        'relation "clientes" does not exist': "tablas",
    }
    for crudo, esperado in casos.items():
        mensaje = db._mensaje_humano(Exception(crudo))
        assert esperado in mensaje.lower(), f"«{crudo}» no se tradujo bien: {mensaje}"
