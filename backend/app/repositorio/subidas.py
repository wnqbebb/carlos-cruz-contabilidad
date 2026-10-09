"""Archivos subidos que esperan confirmación: en disco, no en memoria (adición A5).

Entre «subir» y «confirmar» el contador puede tardar (revisa la propuesta, va
por un café). Hasta la v2.2 los bytes de cada archivo vivían en la memoria del
servidor durante las 8 horas de la sesión: diez archivos de 20 MB eran 200 MB
retenidos. Ahora se escriben en una carpeta temporal y la sesión guarda solo la
ruta. Cada carpeta vive 8 horas desde su último uso; las vencidas se borran al
arrancar el servidor y cada vez que se sube algo.

La carpeta se elige con `CC_TMP_SUBIDAS` (la copia aislada la fija); por
defecto, `carloscruz-subidas` dentro de la carpeta temporal del sistema.
"""
from __future__ import annotations

import logging
import os
import re
import secrets
import shutil
import tempfile
import time
from pathlib import Path

from ..seguridad import cifrado
from .sesiones import VIDA

log = logging.getLogger(__name__)


def carpeta() -> Path:
    valor = (os.getenv("CC_TMP_SUBIDAS") or "").strip()
    raiz = Path(valor) if valor else Path(tempfile.gettempdir()) / "carloscruz-subidas"
    raiz.mkdir(parents=True, exist_ok=True)
    return raiz


def _segura(nombre: str) -> str:
    """Nombre de archivo sin rutas ni caracteres que Windows no acepta."""
    base = re.sub(r'[\\/:*?"<>|\x00-\x1f]', "_", Path(nombre or "archivo").name).strip(" .")
    return base[:150] or "archivo"


def guardar(subida_id: str, archivos: list[tuple[str, bytes]]) -> list[dict]:
    """Escribe los archivos y devuelve las referencias que guarda la sesión."""
    limpiar()
    destino = carpeta() / subida_id
    destino.mkdir(parents=True, exist_ok=True)
    refs = []
    for nombre, contenido in archivos:
        # v2.3 · C25: nombre aleatorio (el original nunca es una ruta) y contenido cifrado (AES-256-GCM).
        ruta = destino / f"{secrets.token_hex(12)}.cc"
        ruta.write_bytes(cifrado.cifrar(contenido, contexto=b"subida"))
        try:
            os.chmod(ruta, 0o600)
        except OSError:  # pragma: no cover
            pass
        refs.append({"nombre": _segura(nombre), "ruta": str(ruta), "bytes": len(contenido)})
    return refs


def leer(refs: list[dict]) -> list[tuple[str, bytes]]:
    """Vuelve a leer los archivos. Si ya no están (se limpiaron), devuelve lo que quede."""
    salida = []
    for r in refs or []:
        ruta = Path(r["ruta"])
        if ruta.exists():
            os.utime(ruta.parent)  # usar la subida renueva su vida
            try:
                salida.append((r["nombre"], cifrado.descifrar(ruta.read_bytes(), contexto=b"subida")))
            except cifrado.CifradoInvalido:
                log.warning("Una subida temporal no se pudo descifrar y se ignoró.")
    return salida


def borrar(subida_id: str) -> None:
    shutil.rmtree(carpeta() / subida_id, ignore_errors=True)


def limpiar(vida_segundos: float | None = None) -> int:
    """Borra las subidas que llevan más de 8 horas sin usarse. Devuelve cuántas borró."""
    vida = VIDA.total_seconds() if vida_segundos is None else vida_segundos
    limite = time.time() - vida
    borradas = 0
    try:
        for d in carpeta().iterdir():
            try:
                if d.is_dir() and d.stat().st_mtime < limite:
                    shutil.rmtree(d, ignore_errors=True)
                    borradas += 1
            except OSError:
                continue
    except OSError as ex:  # pragma: no cover - carpeta temporal inaccesible
        log.warning("No se pudo limpiar la carpeta de subidas: %s", ex)
    return borradas
