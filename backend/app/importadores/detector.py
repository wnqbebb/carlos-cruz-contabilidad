"""Detección automática del formato de cada hoja."""
from __future__ import annotations

from collections import defaultdict
from decimal import Decimal

from ..contabilidad.puc import Mapeador
from ..modelos import Alerta, Empresa
from ..utils.numeros import CERO, normalizar, pesos
from . import aportes, auxiliares, balance, cuenta_t, estados_existentes, hoja_trabajo, libro_diario, nomina, plantilla
from .base import Deteccion
from .lector import Hoja, leer_archivo


def detectar_hoja(h: Hoja, id_: str, mapeador: Mapeador, empresa: Empresa) -> Deteccion:
    if h.nfilas == 0:
        return Deteccion(id_, h.archivo, h.nombre, "desconocido", False, "Hoja vacía")
    if getattr(h, "es_texto", False):
        return Deteccion(id_, h.archivo, h.nombre, "desconocido", False,
                         "Texto del documento: sirve para identificar al cliente, no trae cifras.")
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
    ld = libro_diario.detectar(h)
    if ld is not None:
        return libro_diario.importar(h, ld, id_)
    bal = balance.detectar(h)
    if bal is not None:
        return balance.importar(h, bal, id_)
    aux = auxiliares.importar_hoja(h, id_)
    if aux is not None:
        return aux
    promete = auxiliares.hoja_promete(h)
    if promete:
        # 4.2 · 9: la hoja se llama «COMPRAS» pero no trae compras que se puedan leer.
        d = Deteccion(id_, h.archivo, h.nombre, "desconocido", False,
                      f"El nombre de la hoja promete {auxiliares.NOMBRE_TIPO[promete].lower()}, pero no encontré "
                      "filas con encabezados y valores que se puedan leer.")
        d.paquete.alertas.append(Alerta("AUX-HOJA", "info", f"«{h.nombre}»: {d.motivo}"))
        return d
    return Deteccion(id_, h.archivo, h.nombre, "desconocido", False,
                     "No se reconoció el formato. Use la plantilla oficial o uno de los formatos soportados.")


def detectar_conjunto(archivos: list[tuple[str, bytes]], mapeador: Mapeador, empresa: Empresa,
                      respuestas: dict[str, str] | None = None) -> tuple[list[Deteccion], auxiliares.Conversion | None]:
    """Detecta cada hoja y convierte en asientos los registros auxiliares de todo el conjunto."""
    dets: list[Deteccion] = []
    for i, (nombre, contenido) in enumerate(archivos):
        try:
            hojas = leer_archivo(contenido, nombre)
        except Exception as ex:  # archivo dañado o formato no soportado
            dets.append(Deteccion(f"{i}-0", nombre, "(archivo)", "desconocido", False, f"No se pudo leer: {ex}"))
            continue
        for j, h in enumerate(hojas):
            dets.append(detectar_hoja(h, f"{i}-{j}", mapeador, empresa))
    _marcar_duplicados(dets, mapeador)
    conversion = auxiliares.convertir(dets, respuestas, empresa)
    return dets, conversion


def detectar_archivos(archivos: list[tuple[str, bytes]], mapeador: Mapeador, empresa: Empresa) -> list[Deteccion]:
    return detectar_conjunto(archivos, mapeador, empresa)[0]


def _por_cuenta(movs, mapeador: Mapeador) -> dict[str, tuple[Decimal, Decimal]]:
    """Sumas por cuenta PUC (o por nombre, si el nombre no se reconoce)."""
    acum: dict[str, list[Decimal]] = defaultdict(lambda: [CERO, CERO])
    for m in movs:
        k = m.cuenta
        if not k:
            r = mapeador.resolver(m.nombre_cuenta)
            k = r["codigo"] if r.get("codigo") and r["estado"] == "exacto" else normalizar(m.nombre_cuenta)
        acum[k][0] += m.debito
        acum[k][1] += m.credito
    return {k: (d, c) for k, (d, c) in acum.items()}


def _marcar_duplicados(dets: list[Deteccion], mapeador: Mapeador | None = None) -> None:
    """Hoja de trabajo y cuenta T del mismo archivo con los mismos movimientos (H07).

    Si coinciden cuenta por cuenta, se usan las dos: los SALDOS INICIALES de la
    hoja de trabajo y el DETALLE de la cuenta T (cada movimiento, no la suma por
    cuenta). Si solo coinciden en el total, la cuenta T se excluye por defecto,
    como antes, porque no se puede saber cuál de las dos tiene razón.
    """
    mapeador = mapeador or Mapeador()
    hts = [d for d in dets if d.formato == "hoja_trabajo" and d.incluir]
    for d in dets:
        if d.formato != "cuenta_t":
            continue
        total = d.resumen.get("total_debito")
        for ht in hts:
            t_ht = sum((m.debito for m in ht.paquete.movimientos), start=type(total)(0)) if total is not None else None
            if ht.archivo != d.archivo or not total or t_ht != total:
                continue
            if _por_cuenta(ht.paquete.movimientos, mapeador) == _por_cuenta(d.paquete.movimientos, mapeador):
                ht.resumen["detalle_de"] = d.id
                d.resumen["saldos_de"] = ht.id
                d.motivo = (f"Coincide cuenta por cuenta con «{ht.hoja}» ({pesos(total)}): se usan los saldos iniciales de "
                            f"la hoja de trabajo y el detalle de cada movimiento de esta cuenta T.")
                ht.motivo = (f"Aporta los saldos iniciales; el movimiento del periodo se toma, en detalle, de «{d.hoja}».")
            else:
                d.incluir = False
                d.motivo = (f"Duplica los movimientos de la hoja «{ht.hoja}» (mismas sumas {pesos(total)}). Se usa la hoja "
                            f"de trabajo porque además trae los saldos iniciales. Márquela si prefiere usar esta.")
            break
