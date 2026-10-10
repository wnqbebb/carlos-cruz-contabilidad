"""Rutas HTTP, agrupadas por área de trabajo."""

from . import acceso, analisis, clientes, datos_periodo, renta, sesion, sistema, subir, trabajo  # noqa: F401

# `subir` va primero: es la puerta única de la v2.2.
# `datos_periodo` antes que `analisis`: «/periodos/{id}/datos/excel» si no lo atrapa «/periodos/{id}/{libro}/{formato}».
ROUTERS = (sesion.router, acceso.router, sistema.router, subir.router, clientes.router, trabajo.router,
           datos_periodo.router, analisis.router, renta.router)
