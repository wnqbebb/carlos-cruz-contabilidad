"""Rutas, constantes y configuración leída del entorno (.env)."""
from __future__ import annotations

import os
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]


def _ruta(variable: str, por_defecto: Path) -> Path:
    """Ruta configurable por entorno.

    Dentro del ejecutable empaquetado (PyInstaller) los archivos no están donde
    los dejó el código fuente: viajan comprimidos y se extraen en una carpeta
    temporal distinta en cada arranque. `empaquetar/lanzador.py` fija estas
    variables para indicar dónde quedaron.
    """
    valor = (os.getenv(variable) or "").strip()
    return Path(valor) if valor else por_defecto


DATA = _ruta("CC_DATA", RAIZ / "data")
# Datos reales de clientes: NO se versionan (sección 4.3). Viven en `privado/`,
# que está en .gitignore; si la carpeta no está, lo que depende de ella se oculta
# (y las pruebas que la necesitan se saltan con aviso). Ver docs/PRIVADO.md.
PRIVADO = _ruta("CC_PRIVADO", RAIZ / "privado")
FUENTES = _ruta("CC_FUENTES", PRIVADO / "fuentes")
EMPRESA_PRIVADA = PRIVADO / "empresa_fanant.json"
FRONTEND_DIST = _ruta("CC_FRONTEND", RAIZ / "frontend" / "dist")
DATOS_APP = _ruta("CC_DATOS_APP", RAIZ / "datos_app")
try:
    DATOS_APP.mkdir(parents=True, exist_ok=True)
except OSError:  # carpeta de solo lectura: la base se ubica con CC_SQLITE
    pass


def _candidatos_env() -> list[Path]:
    propio = (os.getenv("CC_ENV") or "").strip()
    return [Path(propio)] if propio else [RAIZ / "backend" / ".env", RAIZ / ".env"]


def _cargar_env() -> None:
    """Lee el archivo de configuración sin dependencias externas.

    No sobreescribe variables ya definidas en el entorno. `CC_ENV` apunta a otro
    archivo y entonces es el ÚNICO que se lee: así lo hace la versión instalada
    (configuración en «Documentos › Carlos Cruz») y así la copia aislada de pruebas
    nunca hereda la configuración ni los secretos de la aplicación real.
    """
    for ruta in _candidatos_env():
        if not ruta.exists():
            continue
        for linea in ruta.read_text(encoding="utf-8-sig").splitlines():
            linea = linea.strip()
            if not linea or linea.startswith("#") or "=" not in linea:
                continue
            clave, _, valor = linea.partition("=")
            clave, valor = clave.strip(), valor.strip().strip('"').strip("'")
            if clave and valor and clave not in os.environ:
                os.environ[clave] = valor


_cargar_env()


def archivo_env() -> Path | None:
    """El archivo de configuración en uso (para mover sus secretos al almacén de Windows)."""
    for ruta in _candidatos_env():
        if ruta.exists():
            return ruta
    return None


def _desde_almacen(nombre: str) -> str:
    """Un secreto que ya no está en el archivo de texto: se lee del Administrador de credenciales."""
    try:
        from .seguridad import secretos

        return secretos.leer(nombre) or ""
    except Exception:
        return ""

MARCA = "Carlos Cruz"
LEMA = "Contabilidad que cuadra."
LEMA_LARGO = "Cuadramos sus cuentas; usted atiende su negocio."
VERSION = "2.4.0"

# Ruta del archivo SQLite local. `CC_SQLITE` permite apuntarla a otro sitio,
# que es como las pruebas trabajan contra una base desechable.
SQLITE_ARCHIVO = Path(os.getenv("CC_SQLITE") or (DATOS_APP / "carloscruz.db"))
SQLITE_ARCHIVO.parent.mkdir(parents=True, exist_ok=True)
SQLITE_URL = f"sqlite:///{SQLITE_ARCHIVO.as_posix()}"


def _normalizar_postgres(url: str) -> str:
    """Supabase entrega 'postgresql://'; SQLAlchemy necesita el driver psycopg explícito.

    v2.3 · C31: la conexión verifica el certificado del servidor (`sslmode=verify-full`). Supabase
    firma con su propia autoridad: su certificado raíz público va en `data/seguridad/`.
    """
    from urllib.parse import parse_qsl, quote, urlencode, urlsplit, urlunsplit

    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    if url.startswith("postgresql://"):
        url = "postgresql+psycopg://" + url[len("postgresql://"):]
    if os.getenv("CC_SSL") == "require":  # solo para diagnosticar; no se usa en producción
        return url
    partes = urlsplit(url)
    consulta = dict(parse_qsl(partes.query))
    raiz = os.getenv("CC_SSL_RAIZ") or (str(DATA / "seguridad" / "supabase-ca-2021.crt")
                                       if "supabase" in (partes.hostname or "") else "system")
    consulta.update({"sslmode": "verify-full", "sslrootcert": raiz})
    return urlunsplit((partes.scheme, partes.netloc, partes.path, urlencode(consulta, quote_via=quote), partes.fragment))


_env_url = (os.getenv("DATABASE_URL") or "").strip()
if not _env_url and (os.getenv("ALMACENAMIENTO") or "").strip().lower() != "local":
    _env_url = _desde_almacen("DATABASE_URL")
ALMACENAMIENTO = (os.getenv("ALMACENAMIENTO") or "").strip().lower() or ("supabase" if _env_url else "local")

if ALMACENAMIENTO == "supabase" and _env_url:
    DB_URL = _normalizar_postgres(_env_url)
    ES_POSTGRES = True
else:
    ALMACENAMIENTO = "local"
    DB_URL = SQLITE_URL
    ES_POSTGRES = False

SUPABASE_URL = (os.getenv("SUPABASE_URL") or "").strip().rstrip("/")
SUPABASE_ANON_KEY = (os.getenv("SUPABASE_ANON_KEY") or "").strip()
SUPABASE_SERVICE_KEY = (os.getenv("SUPABASE_SERVICE_KEY") or (_desde_almacen("SUPABASE_SERVICE_KEY") if ALMACENAMIENTO != "local" else "")).strip()

CORS_ORIGENES = [o.strip() for o in (os.getenv("CORS_ORIGENES") or "").split(",") if o.strip()] or [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

# Legado: el motor conserva compatibilidad con la ruta antigua de la base local.
DB_LEGADO = DATOS_APP / "fanant.db"


def estado_almacenamiento() -> dict:
    """Resumen seguro (sin claves) para mostrar en la interfaz."""
    return {
        "modo": ALMACENAMIENTO,
        "es_postgres": ES_POSTGRES,
        "supabase_configurado": bool(_env_url),
        "proyecto": SUPABASE_URL.replace("https://", "").split(".")[0] if SUPABASE_URL else "",
    }
