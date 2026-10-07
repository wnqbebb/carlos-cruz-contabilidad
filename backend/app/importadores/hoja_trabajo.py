"""Formato "hoja de trabajo": Cuenta | Balance inicial D/H | Movimiento D/H | G y P D/H | Balance general D/H."""
from __future__ import annotations

from ..modelos import Alerta, Movimiento, Paquete, SaldoInicial
from ..utils.numeros import CERO, D, años_en_texto, pesos
from .base import Deteccion
from .lector import Hoja


def detectar(h: Hoja) -> dict | None:
    for r in range(min(h.nfilas, 12)):
        textos = dict((c, t) for c, t in h.fila_textos(r))
        c_cta = next((c for c, t in textos.items() if t in ("CUENTAS", "CUENTA", "NOMBRE DE LA CUENTA")), None)
        c_ini = next((c for c, t in textos.items() if "BALANCE INICIAL" in t or "SALDO INICIAL" in t), None)
        c_mov = next((c for c, t in textos.items() if "MOVIMIENTO" in t), None)
        if c_cta is not None and c_ini is not None and c_mov is not None:
            c_gyp = next((c for c, t in textos.items() if t.startswith("G Y P") or "PERDIDAS Y GANANCIAS" in t or "RESULTADOS" in t), None)
            c_bg = next((c for c, t in textos.items() if "BALANCE GENERAL" in t), None)
            return {"fila": r, "cta": c_cta, "ini": c_ini, "mov": c_mov, "gyp": c_gyp, "bg": c_bg}
    return None


def importar(h: Hoja, pos: dict, id_: str) -> Deteccion:
    paquete = Paquete()
    r0 = pos["fila"] + 1
    if any("DEBE" in t for _, t in h.fila_textos(r0)):
        r0 += 1
    totales_archivo = None
    comparacion = []
    for r in range(r0, h.nfilas):
        nombre = h.texto(r, pos["cta"])
        if not nombre:
            continue
        if nombre.strip().upper().startswith("TOTAL"):
            totales_archivo = {
                "ini_d": D(h.v(r, pos["ini"])), "ini_c": D(h.v(r, pos["ini"] + 1)),
                "mov_d": D(h.v(r, pos["mov"])), "mov_c": D(h.v(r, pos["mov"] + 1)),
                "gyp_d": D(h.v(r, pos["gyp"])) if pos["gyp"] is not None else CERO,
                "gyp_c": D(h.v(r, pos["gyp"] + 1)) if pos["gyp"] is not None else CERO,
                "bg_d": D(h.v(r, pos["bg"])) if pos["bg"] is not None else CERO,
                "bg_c": D(h.v(r, pos["bg"] + 1)) if pos["bg"] is not None else CERO,
            }
            break
        ini = D(h.v(r, pos["ini"])) - D(h.v(r, pos["ini"] + 1))
        mov_d, mov_c = D(h.v(r, pos["mov"])), D(h.v(r, pos["mov"] + 1))
        if ini:
            paquete.saldos_iniciales.append(SaldoInicial("", ini if ini > 0 else CERO, -ini if ini < 0 else CERO, nombre, h.origen(r, pos["ini"])))
        if mov_d or mov_c:
            paquete.movimientos.append(Movimiento(cuenta="", nombre_cuenta=nombre, debito=mov_d, credito=mov_c,
                                                  comprobante=f"HT {h.nombre}", descripcion=f"Movimiento del periodo ({nombre})",
                                                  origen=h.origen(r, pos["mov"])))
        if pos["bg"] is not None:
            neto_archivo = sum((D(h.v(r, pos[k])) - D(h.v(r, pos[k] + 1)) for k in ("gyp", "bg") if pos[k] is not None), CERO)
            neto_calc = ini + mov_d - mov_c
            if neto_archivo != neto_calc:
                comparacion.append({"cuenta": nombre, "archivo": neto_archivo, "recalculado": neto_calc, "diferencia": neto_archivo - neto_calc})

    titulo = next((h.texto(r, c) for r in range(pos["fila"]) for c, _ in h.fila_textos(r)), "")
    if titulo:
        paquete.titulos.append(titulo)
    resumen = {"titulo": titulo, "años_titulo": años_en_texto(titulo), "cuentas": len({m.nombre_cuenta for m in paquete.movimientos} |
               {s.nombre_cuenta for s in paquete.saldos_iniciales}), "saldos_iniciales": len(paquete.saldos_iniciales),
               "movimientos": len(paquete.movimientos), "diferencias_por_cuenta": comparacion[:20]}
    incluir, motivo = True, ""
    if totales_archivo:
        resumen["totales_archivo"] = totales_archivo
        t = totales_archivo
        if t["ini_d"] != t["ini_c"]:
            paquete.alertas.append(Alerta("E8", "error", f"«{h.nombre}»: saldos iniciales no cuadran ({pesos(t['ini_d'])} vs {pesos(t['ini_c'])})."))
        if t["mov_d"] != t["mov_c"]:
            paquete.alertas.append(Alerta("E8", "error", f"«{h.nombre}»: movimientos no cuadran ({pesos(t['mov_d'])} vs {pesos(t['mov_c'])})."))
        descuadre = (t["bg_d"] - t["bg_c"]) - (t["gyp_c"] - t["gyp_d"])
        resumen["descuadre_archivo"] = descuadre
        if pos["bg"] is not None and descuadre != 0:
            incluir = False
            motivo = f"La hoja de trabajo del archivo no cuadra: diferencia de {pesos(descuadre)} en el balance general."
            paquete.alertas.append(Alerta(
                "E8", "error", f"«{h.nombre}»: {motivo}",
                detalle=f"Balance general D {pesos(t['bg_d'])} / C {pesos(t['bg_c'])}; resultado en G y P {pesos(t['gyp_c'] - t['gyp_d'])}. "
                        f"{len(comparacion)} cuenta(s) con saldo distinto al recalculado.", origen=h.origen(pos['fila'])))
    return Deteccion(id_, h.archivo, h.nombre, "hoja_trabajo", incluir, motivo, resumen, paquete)
