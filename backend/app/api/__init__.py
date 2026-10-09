"""Rutas HTTP, agrupadas por área de trabajo."""

from . import acceso, analisis, clientes, renta, sesion, sistema, subir, trabajo  # noqa: F401

# `subir` va primero: es la puerta única de la v2.2.
ROUTERS = (sesion.router, acceso.router, sistema.router, subir.router, clientes.router, trabajo.router, analisis.router,
           renta.router)
