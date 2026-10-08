import os
import sys
import tempfile
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# Las pruebas trabajan SIEMPRE contra una base desechable, nunca contra la del
# usuario. Hay que fijarlo antes de importar `app.config`, que lee el entorno al
# cargarse. `ALMACENAMIENTO=local` evita además tocar Supabase por accidente.
_TEMPORAL = Path(tempfile.mkdtemp(prefix="carloscruz-pruebas-"))
os.environ["CC_SQLITE"] = str(_TEMPORAL / "pruebas.db")
os.environ["CC_DATOS_APP"] = str(_TEMPORAL / "datos")
os.environ["CC_TMP_SUBIDAS"] = str(_TEMPORAL / "subidas")
os.environ["ALMACENAMIENTO"] = "local"
os.environ.pop("DATABASE_URL", None)

# Usuario de prueba (A2). Se fija aquí para que nunca se lean las credenciales
# reales de backend/.env. Hash con pocas rondas: es solo para pruebas.
import bcrypt  # noqa: E402

USUARIO_PRUEBA, CLAVE_PRUEBA = "contador", "clave-de-prueba-123"
os.environ["CC_USUARIO"] = USUARIO_PRUEBA
os.environ["CC_CLAVE_HASH"] = bcrypt.hashpw(CLAVE_PRUEBA.encode(), bcrypt.gensalt(rounds=4)).decode()
os.environ["CLAVE_SESION"] = "clave-de-sesion-solo-para-pruebas-0123456789abcdef"

from app.config import EMPRESA_PRIVADA, FUENTES  # noqa: E402

# Los archivos reales de FANANT no se versionan (sección 4.3): viven en privado/.
# Sin ellos, las pruebas que los usan se saltan diciendo por qué.
PRIVADOS = FUENTES.exists() and EMPRESA_PRIVADA.exists()
AVISO_PRIVADOS = ("Faltan los archivos reales de FANANT en privado/ (no se versionan; "
                  "ver docs/PRIVADO.md). Esta prueba se salta.")
requiere_privados = pytest.mark.skipif(not PRIVADOS, reason=AVISO_PRIVADOS)
from app.contabilidad.puc import Mapeador  # noqa: E402
from app.importadores.detector import detectar_archivos  # noqa: E402
from app.modelos import empresa_por_defecto  # noqa: E402


@pytest.fixture
def empresa():
    e = empresa_por_defecto()
    if not e.razon_social:  # sin privado/: una empresa inventada para las pruebas generales
        from decimal import Decimal

        from app.modelos import Empresa

        e = Empresa(razon_social="EMPRESA DE PRUEBA S.A.S.", sigla="PRUEBA", nit="900123456-8",
                    municipio="Guacarí, Valle del Cauca", capital_suscrito=Decimal("30000000"))
    e.periodo_desde, e.periodo_hasta = date(2025, 1, 1), date(2025, 1, 31)
    return e


@pytest.fixture
def detectar(empresa):
    if not PRIVADOS:
        pytest.skip(AVISO_PRIVADOS)

    def _det(*nombres):
        return detectar_archivos([(n, (FUENTES / n).read_bytes()) for n in nombres], Mapeador(), empresa)
    return _det


@pytest.fixture
def base_limpia():
    """Vacía todas las tablas antes de cada prueba que toque la base."""
    from sqlalchemy import delete

    from app import db
    from app.esquema import metadatos

    db.preparar()
    with db.conexion() as cn:
        for tabla in reversed(metadatos.sorted_tables):
            cn.execute(delete(tabla))
    yield


@pytest.fixture
def cliente_api(base_limpia):
    """Cliente HTTP de pruebas contra la aplicación completa."""
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as c:
        entrar(c)
        yield c


def entrar(c) -> None:
    """Inicia la sesión del contador de prueba en un cliente HTTP."""
    from app import sesion

    sesion.olvidar_fallos()
    r = c.post("/api/sesion", json={"usuario": USUARIO_PRUEBA, "clave": CLAVE_PRUEBA})
    assert r.status_code == 200, r.text


@pytest.fixture
def cliente_sin_sesion(base_limpia):
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as c:
        yield c
