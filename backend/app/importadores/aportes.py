"""Libro de aportes de socios."""
from __future__ import annotations

from ..modelos import Alerta, AporteSocio, Paquete
from ..utils.numeros import CERO, D, pesos
from .base import Deteccion
from .lector import Hoja


def detectar(h: Hoja) -> int | None:
    for r in range(min(h.nfilas, 10)):
        textos = [t for _, t in h.fila_textos(r)]
        if "NOMBRE" in textos and any(t.startswith("APORTE") for t in textos) and any("SALDO" in t or "TOTAL" in t for t in textos):
            return r
    return None


def importar(h: Hoja, r_h: int, id_: str) -> Deteccion:
    cols = dict(h.fila_textos(r_h))
    c_nom = next(c for c, t in cols.items() if t == "NOMBRE")
    c_ced = next((c for c, t in cols.items() if "CEDULA" in t), None)
    c_ap = next(c for c, t in cols.items() if t.startswith("APORTE"))
    c_tot = next((c for c, t in cols.items() if t == "TOTAL"), None)
    c_sal = next((c for c, t in cols.items() if "SALDO" in t), None)
    c_val = [c for c, t in cols.items() if t == "VALOR"]
    paquete = Paquete()
    sin_nombre = 0
    for r in range(r_h + 1, h.nfilas):
        comprometido = D(h.v(r, c_ap))
        if not comprometido and not h.texto(r, c_nom):
            continue
        pagado = D(h.v(r, c_tot)) if c_tot is not None else sum((D(h.v(r, c)) for c in c_val), CERO)
        if not pagado and c_val:
            pagado = sum((D(h.v(r, c)) for c in c_val), CERO)
        saldo = D(h.v(r, c_sal)) if c_sal is not None else comprometido - pagado
        nombre = h.texto(r, c_nom)
        if not nombre:
            sin_nombre += 1
            nombre = f"(socio sin nombre, fila {r + 1})"
        paquete.aportes_socios.append(AporteSocio(nombre, h.texto(r, c_ced) if c_ced is not None else "", comprometido, pagado, saldo, h.origen(r)))
    comp = sum((a.comprometido for a in paquete.aportes_socios), CERO)
    pag = sum((a.pagado for a in paquete.aportes_socios), CERO)
    if sin_nombre:
        paquete.alertas.append(Alerta("APORTES", "advertencia",
                                      f"Libro de aportes: {sin_nombre} fila(s) con aporte pero sin nombre ni cédula del socio."))
    resumen = {"socios": len(paquete.aportes_socios), "comprometido": comp, "pagado": pag, "saldo_por_pagar": comp - pag}
    return Deteccion(id_, h.archivo, h.nombre, "aportes", True,
                     "Se usa para conciliar el capital (no genera movimientos contables).", resumen, paquete)


def total_texto(v) -> str:
    return pesos(v)
