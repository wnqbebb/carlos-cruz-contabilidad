"""Detección automática del formato de cada hoja."""
from __future__ import annotations

from ..contabilidad.puc import Mapeador
from ..modelos import Empresa
from ..utils.numeros import pesos
from . import aportes, cuenta_t, estados_existentes, hoja_trabajo, nomina, plantilla
from .base import Deteccion
from .lector import Hoja, leer_archivo


def detectar_hoja(h: Hoja, id_: str, mapeador: Mapeador, empresa: Empresa) -> Deteccion:
    if h.nfilas == 0:
        return Deteccion(id_, h.archivo, h.nombre, "desconocido", False, "Hoja vacía")
    if plantilla.normalizar(h.nombre) in ("INSTRUCCIONES", "PUC"):
        return Deteccion(id_, h.archivo, h.nombre, "plantilla", False, "Hoja de referencia de la plantilla (no contiene datos)")
    if plantilla.nombre_hoja(h):
        return plantilla.importar(h, id_)
    if estados_existentes.detectar(h):
        return estados_existentes.importar(h, id_, empresa)
    r = nomina.detectar(h)
    if r is not None:
        return nomina.importar(h, r, id_, empresa.periodo_desde.year)
    r = aportes.detectar(h)
    if r is not None:
        return aportes.importar(h, r, id_)
    pos = hoja_trabajo.detectar(h)
    if pos:
        return hoja_trabajo.importar(h, pos, id_)
    r = cuenta_t.detectar(h, mapeador)
    if r is not None:
        return cuenta_t.importar(h, r, id_)
    return Deteccion(id_, h.archivo, h.nombre, "desconocido", False,
                     "No se reconoció el formato. Use la plantilla oficial o uno de los formatos soportados.")


def detectar_archivos(archivos: list[tuple[str, bytes]], mapeador: Mapeador, empresa: Empresa) -> list[Deteccion]:
    dets: list[Deteccion] = []
    for i, (nombre, contenido) in enumerate(archivos):
        try:
            hojas = leer_archivo(contenido, nombre)
        except Exception as ex:  # archivo dañado o formato no soportado
            dets.append(Deteccion(f"{i}-0", nombre, "(archivo)", "desconocido", False, f"No se pudo leer: {ex}"))
            continue
        for j, h in enumerate(hojas):
            dets.append(detectar_hoja(h, f"{i}-{j}", mapeador, empresa))
    _marcar_duplicados(dets)
    return dets


def _marcar_duplicados(dets: list[Deteccion]) -> None:
    """Una hoja «cuenta T» con los mismos movimientos que una «hoja de trabajo» del mismo archivo se excluye por defecto."""
    hts = [d for d in dets if d.formato == "hoja_trabajo" and d.incluir]
    for d in dets:
        if d.formato != "cuenta_t":
            continue
        total = d.resumen.get("total_debito")
        for ht in hts:
            t_ht = sum((m.debito for m in ht.paquete.movimientos), start=type(total)(0)) if total is not None else None
            if ht.archivo == d.archivo and total and t_ht == total:
                d.incluir = False
                d.motivo = (f"Duplica los movimientos de la hoja «{ht.hoja}» (mismas sumas {pesos(total)}). Se usa la hoja de trabajo "
                            f"porque además trae los saldos iniciales. Márquela si prefiere usar esta.")
                break
