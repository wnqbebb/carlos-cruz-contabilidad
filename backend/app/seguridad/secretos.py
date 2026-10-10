"""Secretos del equipo en el Administrador de credenciales de Windows (DPAPI, librería `keyring`). Control C30.

Qué es secreto aquí: la conexión a la base en la nube (`DATABASE_URL`) y la clave con que se
cifran los archivos subidos y las copias de seguridad (`CLAVE_DATOS`). Ninguno queda en un
archivo de texto: si el archivo de configuración trae alguno, se mueve al almacén y se borra
del archivo (`migrar_archivo`).

Cada instalación usa su propio «servicio» en el almacén (según su archivo de configuración),
para que la copia aislada de pruebas, que tiene el suyo, nunca lea ni pise los secretos de la
aplicación real.

Sin almacén disponible (pruebas, un servidor Linux) se usa un archivo con permisos
restringidos dentro de la carpeta de datos de la aplicación.
"""
from __future__ import annotations

import base64
import hashlib
import logging
import os
import secrets
import stat
from pathlib import Path

log = logging.getLogger("carloscruz.secretos")

SECRETOS = ("DATABASE_URL", "CLAVE_SESION", "SUPABASE_SERVICE_KEY", "SUPABASE_SERVICE_ROLE_KEY", "SUPABASE_KEY")


def _ubicacion() -> str:
    """Lo que distingue a esta instalación: su archivo de configuración.

    Los secretos se migran desde ese archivo, así que el espacio del almacén va atado a él: una
    instancia que lee el mismo archivo es la misma instalación y nunca se lleva sus secretos a
    otro espacio. Sin archivo, la base local (o la carpeta del programa).
    """
    from ..config import archivo_env

    ruta = archivo_env()
    if ruta:
        return str(ruta.resolve())
    return os.getenv("CC_SQLITE") or str(Path(__file__).resolve().parents[3])


def servicio() -> str:
    return "CarlosCruz-" + hashlib.sha256(_ubicacion().encode("utf-8")).hexdigest()[:12]


def _almacen():
    if os.getenv("CC_SIN_LLAVERO") == "1":
        return None
    try:
        import keyring
        from keyring.backends.fail import Keyring as Falla

        k = keyring.get_keyring()
        if isinstance(k, Falla) or getattr(k, "priority", 0) <= 0:
            return None
        return keyring
    except Exception:  # pragma: no cover - sin keyring instalado
        return None


def disponible() -> bool:
    return _almacen() is not None


def _archivo_reserva() -> Path:
    base = Path(os.getenv("CC_DATOS_APP") or Path(__file__).resolve().parents[3] / "datos_app")
    carpeta = base / "secretos"
    carpeta.mkdir(parents=True, exist_ok=True)
    return carpeta / (servicio() + ".bin")


def _leer_reserva() -> dict[str, str]:
    ruta = _archivo_reserva()
    if not ruta.exists():
        return {}
    datos = {}
    for linea in ruta.read_text(encoding="utf-8").splitlines():
        if "=" in linea:
            k, v = linea.split("=", 1)
            datos[k] = base64.b64decode(v).decode("utf-8")
    return datos


def _escribir_reserva(datos: dict[str, str]) -> None:
    ruta = _archivo_reserva()
    ruta.write_text("\n".join(f"{k}={base64.b64encode(v.encode()).decode()}" for k, v in datos.items()), encoding="utf-8")
    try:
        os.chmod(ruta, stat.S_IRUSR | stat.S_IWUSR)
    except OSError:  # pragma: no cover
        pass


def leer(nombre: str) -> str | None:
    almacen = _almacen()
    if almacen is not None:
        try:
            return almacen.get_password(servicio(), nombre)
        except Exception as ex:  # pragma: no cover
            log.warning("No se pudo leer un secreto del almacén: %s", type(ex).__name__)  # nosemgrep: python-logger-credential-disclosure  (solo nombres, nunca valores)
            return None
    return _leer_reserva().get(nombre)


def guardar(nombre: str, valor: str) -> None:
    almacen = _almacen()
    if almacen is not None:
        almacen.set_password(servicio(), nombre, valor)
        return
    datos = _leer_reserva()
    datos[nombre] = valor
    _escribir_reserva(datos)


def borrar(nombre: str) -> None:
    almacen = _almacen()
    if almacen is not None:
        try:
            almacen.delete_password(servicio(), nombre)
        except Exception as ex:  # no estaba guardado: no hay nada que borrar
            log.debug("Secreto %s no estaba en el almacén: %s", nombre, type(ex).__name__)  # nosemgrep: python-logger-credential-disclosure  (solo nombres, nunca valores)
        return
    datos = _leer_reserva()
    if datos.pop(nombre, None) is not None:
        _escribir_reserva(datos)


def obtener_o_crear(nombre: str, generar=lambda: secrets.token_hex(32)) -> str:
    valor = leer(nombre)
    if not valor:
        valor = generar()
        guardar(nombre, valor)
    return valor


def clave_datos() -> bytes:
    """Clave AES-256 para cifrar archivos y copias. Se genera sola la primera vez."""
    propia = (os.getenv("CC_CLAVE_DATOS") or "").strip()
    if propia:
        # 64 hexadecimales = la clave tal cual. Cualquier otro texto (p. ej. el que genera Render
        # con `generateValue`) se convierte en 32 bytes con SHA-256: en la nube el disco se borra
        # en cada reinicio, así que la clave TIENE que venir del entorno o los datos cifrados se pierden.
        try:
            if len(propia) == 64:
                return bytes.fromhex(propia)
        except ValueError:
            pass
        import hashlib

        return hashlib.sha256(propia.encode("utf-8")).digest()
    return bytes.fromhex(obtener_o_crear("CLAVE_DATOS"))


def migrar_archivo(ruta: Path) -> list[str]:
    """Mueve los secretos del archivo de configuración al almacén y los borra del archivo.

    Solo borra una línea después de comprobar que el almacén devuelve el mismo valor.
    Devuelve los nombres que se movieron (nunca los valores).
    """
    if os.getenv("CC_MIGRAR_SECRETOS", "1") == "0" or not ruta or not ruta.exists():
        return []
    lineas = ruta.read_text(encoding="utf-8-sig").splitlines()
    movidos: list[str] = []
    salida: list[str] = []
    for linea in lineas:
        clave, _, valor = linea.partition("=")
        clave = clave.strip()
        valor = valor.strip().strip('"').strip("'")
        if clave in SECRETOS and valor and not linea.lstrip().startswith("#"):
            try:
                guardar(clave, valor)
                if leer(clave) == valor:
                    movidos.append(clave)
                    os.environ.setdefault(clave, valor)
                    salida.append(f"# {clave}: guardado en el Administrador de credenciales de Windows")
                    continue
            except Exception as ex:
                log.warning("No se pudo mover %s al almacén de credenciales: %s", clave, type(ex).__name__)
        salida.append(linea)
    if movidos:
        ruta.write_text("\n".join(salida) + "\n", encoding="utf-8")
        log.info("Secretos movidos al almacén de credenciales: %s.", ", ".join(movidos))  # nosemgrep: python-logger-credential-disclosure  (solo nombres, nunca valores)
    return movidos


def quitar_lineas(ruta: Path, nombres: tuple[str, ...]) -> list[str]:
    """Borra del archivo de configuración datos que ya viven en otro lugar (p. ej. el hash de la v2.2)."""
    if os.getenv("CC_MIGRAR_SECRETOS", "1") == "0" or not ruta or not ruta.exists():
        return []
    lineas = ruta.read_text(encoding="utf-8-sig").splitlines()
    quitadas = [l.split("=", 1)[0].strip() for l in lineas
                if l.split("=", 1)[0].strip() in nombres and not l.lstrip().startswith("#")]
    if quitadas:
        ruta.write_text("\n".join(l for l in lineas if l.split("=", 1)[0].strip() not in nombres) + "\n", encoding="utf-8")
    return quitadas
