"""Análisis aislado de archivos (control C24).

Leer un archivo del cliente es lo más expuesto de la aplicación: un PDF diseñado para colgar
el lector o una hoja que infla la memoria no deben tumbar el servidor. Por eso cada lote se lee
en un **proceso aparte** con tiempo límite y memoria limitada; si se pasa, se termina ese
proceso y el contador recibe un mensaje claro.

`CC_AISLAR=0` lo desactiva (las pruebas generales lo apagan por velocidad; las de seguridad
lo prueban encendido).
"""
from __future__ import annotations

import importlib
import multiprocessing as mp
import os
import queue
import time

TIEMPO = int(os.getenv("CC_AISLADO_SEGUNDOS") or 180)
# En el equipo del contador sobra memoria; en Render gratis hay 512 MB para TODO el servidor,
# así que allá se fija CC_AISLADO_MB=300 (render.yaml) para que un archivo enorme pare solo al lector.
MEMORIA_MB = int(os.getenv("CC_AISLADO_MB") or 2048)


class ArchivoNoProcesable(Exception):
    def __init__(self, codigo: str, mensaje: str):
        super().__init__(mensaje)
        self.codigo = codigo


def _trabajador(cola, ruta: str, args: tuple, kwargs: dict, rutas_python: list[str]) -> None:
    import sys

    for r in rutas_python:
        if r not in sys.path:
            sys.path.insert(0, r)
    try:
        modulo, funcion = ruta.rsplit(".", 1)
        resultado = getattr(importlib.import_module(modulo), funcion)(*args, **kwargs)
        cola.put(("ok", resultado))
    except BaseException as ex:  # noqa: BLE001 - se devuelve al proceso principal
        cola.put(("error", ex))


def _memoria(pid: int) -> int:
    try:
        import psutil

        return psutil.Process(pid).memory_info().rss
    except Exception:
        return 0


def ejecutar(ruta: str, *args, tiempo: int = TIEMPO, memoria_mb: int = MEMORIA_MB, **kwargs):
    """Ejecuta `paquete.modulo.funcion(*args)` en otro proceso y devuelve su resultado."""
    if os.getenv("CC_AISLAR", "1") == "0":
        modulo, funcion = ruta.rsplit(".", 1)
        return getattr(importlib.import_module(modulo), funcion)(*args, **kwargs)
    import sys

    ctx = mp.get_context("spawn")
    cola = ctx.Queue()
    proceso = ctx.Process(target=_trabajador, args=(cola, ruta, args, kwargs, list(sys.path)), daemon=True)
    proceso.start()
    limite = time.monotonic() + tiempo
    tope = memoria_mb * 1024 * 1024
    try:
        while True:
            try:
                estado, valor = cola.get(timeout=0.2)
                break
            except queue.Empty:
                pass
            if not proceso.is_alive():
                # El lector pudo terminar BIEN justo después de la última espera: su resultado ya está
                # en la cola. Sin esta última lectura se avisaba «el lector se detuvo» con un archivo
                # bueno (pasaba con el equipo ocupado; en la nube gratuita, con CPU lenta, a menudo).
                try:
                    estado, valor = cola.get(timeout=2)
                    break
                except queue.Empty:
                    raise ArchivoNoProcesable("archivo_no_procesable",
                                              "El archivo no se pudo leer: el lector se detuvo. Revise que no esté dañado.")
            if time.monotonic() > limite:
                raise ArchivoNoProcesable("tiempo_agotado",
                                          "Leer el archivo tardó demasiado y se detuvo por seguridad. Revise que no "
                                          "esté dañado o súbalo en partes.")
            if _memoria(proceso.pid) > tope:
                raise ArchivoNoProcesable("memoria_agotada",
                                          "El archivo pide demasiada memoria para leerse y se detuvo por seguridad.")
    finally:
        if proceso.is_alive():
            proceso.kill()
        proceso.join(timeout=5)
    if estado == "error":
        raise valor
    return valor
