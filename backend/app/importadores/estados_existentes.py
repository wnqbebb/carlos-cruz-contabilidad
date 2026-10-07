"""Auditoría de estados financieros existentes (formato ESTADOS FINANCIEROS.xlsx del contador)."""
from __future__ import annotations

import re
from decimal import Decimal

from ..modelos import Alerta, Empresa, Movimiento, Paquete
from ..utils.numeros import CERO, D, es_numero, normalizar, pesos
from .base import Deteccion
from .lector import Hoja

RE_QUEMADO = re.compile(r"^=\+?\s*\d|[+\-]\s*\d{4,}")
RE_DIFERENCIA = re.compile(r"^=\+?\s*[A-Z]{1,2}\d+\s*-")
ENCABEZADOS = ("ACTIVOS CORRIENTES", "ACTIVOS FIJOS", "OTROS ACTIVOS", "PASIVOS CORRIENTE", "PASIVO A LARGO PLAZO", "OTROS PASIVOS",
               "PATRIMONIO", "ACTIVOS", "PASIVOS", "GASTOS", "OBLIGACIONES BANCARIAS", "PROVEEDORES")


def detectar(h: Hoja) -> bool:
    return bool(h.buscar_texto("ESTADO DE LA SITUACION FINANCIERA", 10) or
                (h.buscar_texto("BALANCE GENERAL", 10) and h.buscar_texto("ESTADO DE RESULTADOS", 10)))


def _bloque(h: Hoja, r0: int, c_lab: int, fin: str) -> list[dict]:
    lineas = []
    for r in range(r0 + 1, h.nfilas):
        etiqueta = h.texto(r, c_lab)
        if not etiqueta:
            continue
        valores = {c: D(h.v(r, c)) for c in range(c_lab + 1, c_lab + 4) if es_numero(h.v(r, c)) and not isinstance(h.v(r, c), str)}
        formulas = {c: h.formula(r, c) for c in valores if h.formula(r, c)}
        lineas.append({"fila": r, "etiqueta": etiqueta, "norm": normalizar(etiqueta), "valores": valores, "formulas": formulas})
        if normalizar(etiqueta).startswith(fin):
            break
    return lineas


def _primero(linea: dict) -> Decimal:
    for c in sorted(linea["valores"]):
        if linea["valores"][c] != 0:
            return linea["valores"][c]
    return CERO


def _ultimo(linea: dict) -> Decimal:
    for c in sorted(linea["valores"], reverse=True):
        if linea["valores"][c] != 0:
            return linea["valores"][c]
    return CERO


def importar(h: Hoja, id_: str, empresa: Empresa) -> Deteccion:
    paquete = Paquete()
    hallazgos: list[dict] = []
    pos_a = h.buscar_texto("ACTIVOS", 12)
    pos_p = h.buscar_texto("PASIVOS", 12)
    pos_i = h.buscar_texto("INGRESOS OPERACIONALES", 15)
    activos = _bloque(h, pos_a[0], pos_a[1], "TOTAL ACTIVOS") if pos_a else []
    pasivos = _bloque(h, pos_p[0], pos_p[1], "TOTAL PASIVO Y PATRIMONIO") if pos_p else []
    er = _bloque(h, pos_i[0] - 1, pos_i[1], "UTILIDAD OPERACIONAL") if pos_i else []

    def celda(linea, c):
        return h.origen(linea["fila"], c).split(" › ")[-1]

    def es_total(l):
        return l["norm"].startswith("TOTAL") or l["norm"] in ENCABEZADOS

    lin_activos = [l for l in activos if not es_total(l) and _primero(l)]
    total_activos = sum((_primero(l) for l in lin_activos), CERO)
    capital_l = next((l for l in pasivos if l["norm"].startswith("CAPITAL")), None)
    utilidad_l = next((l for l in pasivos if l["norm"].startswith("UTILIDAD")), None)
    lin_pasivos = [l for l in pasivos if not es_total(l) and l is not capital_l and l is not utilidad_l
                   and l["norm"] not in ("RESERVAS", "REVALORIZACIONES") and _primero(l)]
    total_pasivos = sum((_primero(l) for l in lin_pasivos), CERO)

    # Estado de resultados
    def entre(inicio: str, fin: str) -> list[dict]:
        dentro, res = False, []
        for l in er:
            if l["norm"].startswith(fin) and dentro:
                break
            if dentro:
                res.append(l)
            if l["norm"].startswith(inicio):
                dentro = True
        return res

    ingresos_l = [l for l in entre("INGRESOS OPERACIONALES", "TOTAL INGRESOS") if _primero(l)]
    costo_l = next((l for l in er if l["norm"].startswith("COSTO DE VENTAS")), None)
    comp_gastos = [l for l in entre("GASTOS", "TOTAL GASTOS")
                   if _primero(l) and not any(f.upper().startswith("=SUM") for f in l["formulas"].values())]
    subtotales_gastos = [l for l in entre("GASTOS", "TOTAL GASTOS") if any(f.upper().startswith("=SUM") for f in l["formulas"].values())]
    total_gastos_l = next((l for l in er if l["norm"].startswith("TOTAL GASTOS")), None)
    utilidad_er_l = next((l for l in er if l["norm"].startswith("UTILIDAD OPERACIONAL") or l["norm"].startswith("UTILIDAD NETA")), None)

    ingresos = sum((_primero(l) for l in ingresos_l), CERO)
    costo = _primero(costo_l) if costo_l else CERO
    gastos_ok = sum((_primero(l) for l in comp_gastos), CERO)
    gastos_archivo = _ultimo(total_gastos_l) if total_gastos_l else CERO
    utilidad_archivo = _ultimo(utilidad_er_l) if utilidad_er_l else CERO
    utilidad_ok = ingresos - costo - gastos_ok
    capital_archivo = _primero(capital_l) if capital_l else CERO
    capital_ok = empresa.capital_suscrito or capital_archivo
    patrimonio_ok = capital_ok + utilidad_ok
    descuadre = total_activos - total_pasivos - patrimonio_ok

    def hallazgo(codigo, severidad, texto, celda_=""):
        hallazgos.append({"hoja": h.nombre, "codigo": codigo, "severidad": severidad, "hallazgo": texto, "celda": celda_})

    if capital_l:
        c_cap = min(capital_l["valores"]) if capital_l["valores"] else None
        f_cap = capital_l["formulas"].get(c_cap, "") if c_cap is not None else ""
        if f_cap and RE_DIFERENCIA.search(f_cap.replace(" ", "")):
            if capital_archivo != capital_ok:
                hallazgo("E1", "error", f"Capital social calculado como cuadre ({f_cap} = Activos − Pasivos − Utilidad): muestra "
                                        f"{pesos(capital_archivo)} cuando el capital suscrito y pagado es {pesos(capital_ok)}. "
                                        f"El balance «cuadra» a la fuerza.", celda(capital_l, c_cap))
            else:
                hallazgo("E1", "advertencia", f"El capital social es una fórmula de cuadre ({f_cap}). Hoy coincide con el capital "
                                              f"estatutario, pero dejará de hacerlo en cuanto haya movimientos.", celda(capital_l, c_cap))
    if total_gastos_l and gastos_archivo != gastos_ok:
        omitidos = gastos_ok - gastos_archivo
        c_tg = max(total_gastos_l["valores"]) if total_gastos_l["valores"] else None
        hallazgo("E2", "error", f"Total gastos del archivo {pesos(gastos_archivo)} ({total_gastos_l['formulas'].get(c_tg, '')}) omite "
                                f"{pesos(omitidos)}: la suma de todos los gastos es {pesos(gastos_ok)}. La utilidad queda sobrestimada: "
                                f"dice {pesos(utilidad_archivo)}, debería ser {pesos(utilidad_ok)}.", celda(total_gastos_l, c_tg) if c_tg is not None else "")
    for l in ingresos_l:
        v = _primero(l)
        if empresa.accionistas and empresa.capital_suscrito and v == empresa.capital_suscrito / len(empresa.accionistas):
            hallazgo("E3", "advertencia", f"Ingreso «{l['etiqueta'].strip()}» de {pesos(v)} es exactamente el aporte de un socio: "
                                          f"verificar si es un aporte de capital registrado como ingreso.", celda(l, min(l['valores'])))
    inventario_l = next((l for l in activos if "INVENTARIO" in l["norm"]), None)
    if costo and (not inventario_l or _primero(inventario_l) == 0):
        hallazgo("E4", "advertencia", f"Costo de ventas {pesos(costo)} sin inventario en el balance: no hay soporte (kardex) para ese costo.")
    if descuadre:
        hallazgo("E1", "error", f"Con el capital estatutario ({pesos(capital_ok)}) y la utilidad corregida ({pesos(utilidad_ok)}) el "
                                f"patrimonio debería ser {pesos(patrimonio_ok)}; los activos son {pesos(total_activos)} → faltan "
                                f"{pesos(-descuadre) if descuadre < 0 else pesos(descuadre)} por explicar (capital no consignado o activos sin registrar).")
    titulo = " ".join(t for r in range(min(6, h.nfilas)) for _, t in h.fila_textos(r))
    if "INICIAL" in titulo and (ingresos or gastos_ok):
        hallazgo("E19", "advertencia", "El título dice «situación financiera INICIAL» pero el estado ya tiene ingresos y gastos.")
    pos_nit = h.buscar_texto("NIT", 6)
    if pos_nit and not re.search(r"\d{6,}", h.texto(*pos_nit).replace(".", "")):
        hallazgo("E19", "advertencia", "El NIT está en blanco en el encabezado.", h.origen(*pos_nit).split(" › ")[-1])
    for linea in activos + pasivos + er:
        for c, f in linea["formulas"].items():
            if RE_QUEMADO.search(f.replace(" ", "")):
                hallazgo("E20", "advertencia", f"«{linea['etiqueta'].strip()}» usa valores digitados dentro de la fórmula {f}: no hay soporte "
                                               f"ni trazabilidad.", celda(linea, c))
    for l in subtotales_gastos:
        if "VENTA" in l["norm"]:
            hallazgo("E21", "advertencia", f"El subtotal «{l['etiqueta'].strip()}» suma gastos de administración, no de ventas.",
                     celda(l, min(l['valores'])))

    comparativo = [
        {"concepto": "Total activos", "archivo": total_activos, "correcto": total_activos},
        {"concepto": "Total pasivos", "archivo": total_pasivos, "correcto": total_pasivos},
        {"concepto": "Capital social", "archivo": capital_archivo, "correcto": capital_ok},
        {"concepto": "Ingresos operacionales", "archivo": ingresos, "correcto": ingresos},
        {"concepto": "Costo de ventas", "archivo": costo, "correcto": costo},
        {"concepto": "Total gastos", "archivo": gastos_archivo, "correcto": gastos_ok},
        {"concepto": "Utilidad del ejercicio", "archivo": utilidad_archivo, "correcto": utilidad_ok},
        {"concepto": "Total patrimonio", "archivo": capital_archivo + (_primero(utilidad_l) if utilidad_l else CERO), "correcto": patrimonio_ok},
        {"concepto": "Activo − (Pasivo + Patrimonio)", "archivo": total_activos - total_pasivos - capital_archivo - (_primero(utilidad_l) if utilidad_l else CERO),
         "correcto": descuadre},
    ]
    paquete.auditoria_ef = [{"archivo": h.archivo, "hoja": h.nombre, "hallazgos": hallazgos, "comparativo": comparativo,
                             "utilidad_corregida": utilidad_ok}]
    for x in hallazgos:
        paquete.alertas.append(Alerta(x["codigo"], x["severidad"], f"EF «{h.nombre}»: {x['hallazgo']}", origen=f"{h.archivo} › {h.nombre} › {x['celda']}"))

    # Reconstrucción como movimientos (solo si el usuario incluye la hoja)
    comp = f"EF {h.nombre}"
    for l in lin_activos:
        paquete.movimientos.append(Movimiento("", debito=_primero(l), nombre_cuenta=l["etiqueta"].strip(), comprobante=comp,
                                              descripcion="Reconstruido del estado financiero", origen=h.origen(l["fila"])))
    for l in lin_pasivos:
        paquete.movimientos.append(Movimiento("", credito=_primero(l), nombre_cuenta=l["etiqueta"].strip(), comprobante=comp,
                                              descripcion="Reconstruido del estado financiero", origen=h.origen(l["fila"])))
    if capital_ok:
        paquete.movimientos.append(Movimiento("3105", credito=capital_ok, nombre_cuenta="Capital social (según estatutos)", comprobante=comp,
                                              descripcion="Capital suscrito y pagado según estatutos"))
    for l in ingresos_l:
        paquete.movimientos.append(Movimiento("", credito=_primero(l), nombre_cuenta=l["etiqueta"].strip(), comprobante=comp,
                                              descripcion="Reconstruido del estado de resultados", origen=h.origen(l["fila"])))
    if costo:
        paquete.movimientos.append(Movimiento("", debito=costo, nombre_cuenta=costo_l["etiqueta"].strip(), comprobante=comp,
                                              descripcion="Reconstruido del estado de resultados", origen=h.origen(costo_l["fila"])))
    for l in comp_gastos:
        paquete.movimientos.append(Movimiento("", debito=_primero(l), nombre_cuenta=l["etiqueta"].strip(), comprobante=comp,
                                              descripcion="Reconstruido del estado de resultados", origen=h.origen(l["fila"])))
    resumen = {"hallazgos": len(hallazgos), "utilidad_archivo": utilidad_archivo, "utilidad_corregida": utilidad_ok,
               "total_activos": total_activos}
    return Deteccion(id_, h.archivo, h.nombre, "estados_existentes", False,
                     "Solo auditoría: sus cifras no se suman a la contabilidad (márquela para reconstruir este estado financiero).",
                     resumen, paquete, solo_auditoria=True)
