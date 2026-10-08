"""Libro diario suelto: fecha, comprobante, cuenta, tercero, descripción, débito y crédito (P01).

POR QUÉ EXISTE
Es el volcado típico de un programa contable o de un Excel llevado en partida
doble: una fila por línea de asiento. Los encabezados pueden venir en cualquier
orden y con otros nombres; se reconocen por su significado (`encabezados.py`),
no por su posición. La cuenta puede venir como código PUC o como nombre: si es
nombre, pasa por el mapeo como cualquier otra.
"""
from __future__ import annotations

from ..contabilidad.puc import puc
from ..modelos import Alerta, Movimiento, Paquete
from ..utils.numeros import CERO, D, es_numero, normalizar, parse_fecha, pesos
from . import encabezados as enc
from .base import Deteccion
from .lector import Hoja

FORMATO = "libro_diario"
_PERMITIDOS = {"fecha", "documento", "cuenta", "nombre_cuenta", "tercero", "tercero_id", "detalle", "debito", "credito"}


def _codigo(valor) -> str:
    if valor is None:
        return ""
    if isinstance(valor, float) and valor.is_integer():
        return str(int(valor))
    t = str(valor).strip().replace(" ", "")
    return t.split(".")[0] if t.replace(".", "").isdigit() else ""


def detectar(h: Hoja) -> tuple[int, dict[str, int]] | None:
    for r in range(min(h.nfilas, 15)):
        textos = [(c, t) for c, t in h.fila_textos(r) if not es_numero(h.v(r, c))]
        asignados = {rol: c for rol, (c, _) in enc.mapear_fila(textos, _PERMITIDOS).items()}
        if not {"debito", "credito"} <= set(asignados):
            continue
        if not ({"cuenta", "nombre_cuenta"} & set(asignados)):
            continue
        # Un libro diario dice CUÁNDO o EN QUÉ COMPROBANTE; un balance de prueba
        # también trae débitos y créditos por cuenta, pero no eso, y sí saldos.
        if not ({"fecha", "documento"} & set(asignados)):
            continue
        if any("SALDO" in t for _, t in textos):
            continue
        # La columna «cuenta» puede traer nombres en vez de códigos: se mira el contenido.
        if "cuenta" in asignados:
            vals = [h.v(rr, asignados["cuenta"]) for rr in range(r + 1, min(h.nfilas, r + 40))]
            vals = [v for v in vals if v is not None]
            codigos = sum(1 for v in vals if _codigo(v))
            if vals and codigos < len(vals) / 2 and "nombre_cuenta" not in asignados:
                asignados["nombre_cuenta"] = asignados.pop("cuenta")
        return r, asignados
    return None


def importar(h: Hoja, pos: tuple[int, dict[str, int]], id_: str) -> Deteccion:
    r0, cols = pos
    p = puc()
    paquete = Paquete()
    fechas = []

    def v(r, rol):
        return h.v(r, cols[rol]) if rol in cols else None

    for r in range(r0 + 1, h.nfilas):
        deb, cre = D(v(r, "debito")), D(v(r, "credito"))
        if not deb and not cre:
            continue
        codigo = _codigo(v(r, "cuenta"))
        nombre = str(v(r, "nombre_cuenta") or "").strip()
        textos = " ".join(normalizar(x) for x in (h.valores[r] if r < h.nfilas else []) if isinstance(x, str))
        if not codigo and not nombre and ("TOTAL" in textos or "SUMA" in textos):
            paquete.filas_ignoradas.append({"origen": h.origen(r), "motivo": "Fila de totales del archivo: se recalcula"})
            continue
        cuenta = codigo if codigo and p.valido(codigo) else ""
        if codigo and not cuenta:
            paquete.alertas.append(Alerta("PUC", "advertencia",
                                          f"Código «{codigo}» no existe en el PUC; se mapeará por nombre.", origen=h.origen(r)))
            nombre = nombre or codigo
        if not cuenta and not nombre:
            paquete.filas_ignoradas.append({"origen": h.origen(r), "motivo": "Línea sin cuenta"})
            continue
        fecha = parse_fecha(v(r, "fecha"))
        if fecha:
            fechas.append(fecha)
        comp = str(v(r, "documento") or "").strip()
        if isinstance(v(r, "documento"), float) and v(r, "documento").is_integer():
            comp = str(int(v(r, "documento")))
        paquete.movimientos.append(Movimiento(
            cuenta=cuenta, debito=deb, credito=cre, fecha=fecha,
            comprobante=comp or (f"LD {fecha.isoformat()}" if fecha else f"LD {h.nombre}"),
            tipo="diario", nombre_cuenta=nombre, tercero_id=_codigo(v(r, "tercero_id")) or str(v(r, "tercero_id") or ""),
            tercero_nombre=str(v(r, "tercero") or "").strip(), descripcion=str(v(r, "detalle") or "").strip(),
            origen=h.origen(r)))

    td = sum((m.debito for m in paquete.movimientos), CERO)
    tc = sum((m.credito for m in paquete.movimientos), CERO)
    if td != tc:
        paquete.alertas.append(Alerta("SUMAS-IGUALES", "error",
                                      f"El libro diario «{h.nombre}» no cuadra: débitos {pesos(td)} ≠ créditos {pesos(tc)}."))
    resumen = {
        "movimientos": len(paquete.movimientos), "total_debito": td, "total_credito": tc,
        "comprobantes": len({m.comprobante for m in paquete.movimientos}),
        "desde": min(fechas).isoformat() if fechas else None, "hasta": max(fechas).isoformat() if fechas else None,
    }
    motivo = "" if paquete.movimientos else "No trae líneas con valores."
    return Deteccion(id_, h.archivo, h.nombre, FORMATO, bool(paquete.movimientos), motivo, resumen, paquete)
