"""Copias de seguridad cifradas (control C32).

Una vez al día, toda la base (local o en la nube) se exporta, se comprime y se cifra con
AES-256-GCM. Se guardan 30 días. Después de cada copia se prueba restaurarla en una base
desechable y se comparan las filas: una copia que no se restaura no sirve de nada.
"""
from __future__ import annotations

import base64
import gzip
import json
import logging
import os
import tempfile
import threading
import time
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

from sqlalchemy import Date, DateTime, LargeBinary, create_engine, func, insert, select

from ..config import DATOS_APP
from ..db import lectura
from ..esquema import metadatos
from . import cifrado

log = logging.getLogger("carloscruz.respaldo")
RETENCION_DIAS = 30
EXTENSION = ".ccr"


def carpeta() -> Path:
    destino = Path(os.getenv("CC_RESPALDOS") or (DATOS_APP / "respaldos"))
    destino.mkdir(parents=True, exist_ok=True)
    return destino


def _a_json(v):
    if isinstance(v, Decimal):
        return {"$d": str(v)}
    if isinstance(v, datetime):
        return {"$t": v.isoformat()}
    if isinstance(v, date):
        return {"$f": v.isoformat()}
    if isinstance(v, (bytes, bytearray, memoryview)):
        return {"$b": base64.b64encode(bytes(v)).decode("ascii")}
    return v


def _desde_json(v, tipo):
    if isinstance(v, dict) and len(v) == 1:
        (k, x), = v.items()
        if k == "$d":
            return Decimal(x)
        if k == "$t":
            return datetime.fromisoformat(x)
        if k == "$f":
            return date.fromisoformat(x)
        if k == "$b":
            return base64.b64decode(x)
    if isinstance(tipo, DateTime) and isinstance(v, str):
        return datetime.fromisoformat(v)
    if isinstance(tipo, Date) and isinstance(v, str):
        return date.fromisoformat(v)
    if isinstance(tipo, LargeBinary) and isinstance(v, str):
        return base64.b64decode(v)
    return v


def exportar() -> dict:
    datos: dict[str, list[dict]] = {}
    with lectura() as cn:
        for tabla in metadatos.sorted_tables:
            try:
                filas = cn.execute(select(tabla)).all()
            except Exception as ex:  # una tabla que aún no existe en esta base
                log.debug("Tabla %s sin respaldar: %s", tabla.name, type(ex).__name__)
                continue
            datos[tabla.name] = [{k: _a_json(v) for k, v in f._mapping.items()} for f in filas]
    return {"version": 1, "creado": datetime.now(timezone.utc).isoformat(), "tablas": datos}


def crear() -> Path:
    contenido = json.dumps(exportar(), ensure_ascii=False, default=str).encode("utf-8")
    sellado = cifrado.cifrar(gzip.compress(contenido), contexto=b"respaldo")
    ruta = carpeta() / f"respaldo-{datetime.now().strftime('%Y-%m-%d_%Hh%Mm%Ss')}{EXTENSION}"
    ruta.write_bytes(sellado)
    limpiar()
    return ruta


def leer(ruta: Path) -> dict:
    return json.loads(gzip.decompress(cifrado.descifrar(ruta.read_bytes(), contexto=b"respaldo")).decode("utf-8"))


def restaurar_en(ruta: Path, url_destino: str) -> dict[str, int]:
    """Restaura una copia en otra base (vacía). Devuelve las filas por tabla."""
    datos = leer(ruta)["tablas"]
    motor = create_engine(url_destino)
    metadatos.create_all(motor)
    conteo = {}
    with motor.begin() as cn:
        for tabla in metadatos.sorted_tables:
            filas = datos.get(tabla.name) or []
            if filas:
                tipos = {c.name: c.type for c in tabla.columns}
                cn.execute(insert(tabla), [{k: _desde_json(v, tipos.get(k)) for k, v in f.items() if k in tipos}
                                           for f in filas])
            conteo[tabla.name] = cn.execute(select(func.count()).select_from(tabla)).scalar() or 0
    motor.dispose()
    return conteo


def probar(ruta: Path) -> bool:
    """La copia se restaura en una base desechable y las filas coinciden con lo exportado."""
    esperado = {t: len(f) for t, f in leer(ruta)["tablas"].items()}
    with tempfile.TemporaryDirectory(prefix="cc-prueba-respaldo-") as tmp:
        url = f"sqlite:///{(Path(tmp) / 'prueba.db').as_posix()}"
        obtenido = restaurar_en(ruta, url)
    return all(obtenido.get(t, 0) == n for t, n in esperado.items())


def limpiar(dias: int = RETENCION_DIAS) -> int:
    limite = time.time() - dias * 86400
    borrados = 0
    for f in carpeta().glob(f"respaldo-*{EXTENSION}"):
        if f.stat().st_mtime < limite:
            f.unlink(missing_ok=True)
            borrados += 1
    return borrados


def ultimo() -> Path | None:
    copias = sorted(carpeta().glob(f"respaldo-*{EXTENSION}"))
    return copias[-1] if copias else None


def _tarea() -> None:
    while True:
        try:
            u = ultimo()
            if not u or datetime.now() - datetime.fromtimestamp(u.stat().st_mtime) > timedelta(hours=24):
                ruta = crear()
                ok = probar(ruta)
                (log.info if ok else log.error)("Copia de seguridad cifrada %s · restauración de prueba: %s",
                                                ruta.name, "correcta" if ok else "FALLÓ")
        except Exception:
            log.exception("No se pudo hacer la copia de seguridad")
        time.sleep(3600)


def programar() -> None:
    if os.getenv("CC_SIN_RESPALDO") == "1":
        return
    threading.Thread(target=_tarea, name="respaldo-diario", daemon=True).start()
