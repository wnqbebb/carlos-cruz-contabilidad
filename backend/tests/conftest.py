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

from app.config import FUENTES  # noqa: E402
from app.contabilidad.puc import Mapeador  # noqa: E402
from app.importadores.detector import detectar_archivos  # noqa: E402
from app.modelos import empresa_por_defecto  # noqa: E402


@pytest.fixture
def empresa():
    e = empresa_por_defecto()
    e.periodo_desde, e.periodo_hasta = date(2025, 1, 1), date(2025, 1, 31)
    return e


@pytest.fixture
def detectar(empresa):
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
        yield c
