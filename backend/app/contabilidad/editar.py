"""«Datos del periodo»: editar dentro de la aplicación lo que entró al cálculo (rescate H7).

El contador abre un periodo, cambia el valor o la cuenta de un movimiento, agrega o borra
filas, corrige un saldo inicial, el inventario, la nómina o un activo fijo, y guarda. La
aplicación valida, recalcula todo con el mismo motor, deja la versión anterior en el
historial (para «Deshacer» o «Restaurar versión») y los estados, libros y el Excel quedan
al día. Un periodo cerrado no se edita: hay que reabrirlo (protección de la v2.2).

Las tablas que ve la pantalla son las listas del paquete de entrada (`contabilidad/entrada.py`)
con los nombres de campo del modelo (`modelos.py`). Los importes van como texto decimal.
"""
from __future__ import annotations

from collections import defaultdict
from decimal import Decimal

from ..modelos import Empresa, Paquete
from ..utils.numeros import CERO, D, parse_fecha, pesos
from . import entrada as E

# Pestaña → lista del paquete.
TABLAS = {
    "movimientos": "movimientos",
    "ajustes": "ajustes_manuales",
    "saldos_iniciales": "saldos_iniciales",
    "inventario": "inventario_movs",
    "conteo": "inventario_fisico",
    "activos_fijos": "activos_fijos",
    "nomina": "empleados",
}


class ErrorEdicion(ValueError):
    """Lo que se mandó no se puede guardar; el mensaje va tal cual al contador."""


def tablas(entrada: dict) -> dict[str, list[dict]]:
    paquete = entrada.get("paquete") or {}
    return {pestana: list(paquete.get(lista) or []) for pestana, lista in TABLAS.items()}


def validar(paquete: Paquete) -> dict:
    """Errores (no deja guardar) y avisos (deja guardar) en lenguaje sencillo."""
    from .puc import puc

    p = puc()
    errores: list[dict] = []
    avisos: list[dict] = []
    por_comp: dict[str, list[Decimal]] = defaultdict(lambda: [CERO, CERO])
    for i, m in enumerate(paquete.movimientos):
        if not (m.cuenta or m.nombre_cuenta):
            errores.append({"tabla": "movimientos", "fila": i, "campo": "cuenta", "mensaje": "Falta la cuenta."})
        elif m.cuenta and not p.valido(m.cuenta):
            errores.append({"tabla": "movimientos", "fila": i, "campo": "cuenta",
                            "mensaje": f"La cuenta «{m.cuenta}» no existe en el PUC."})
        if m.debito < 0 or m.credito < 0:
            errores.append({"tabla": "movimientos", "fila": i, "campo": "debito",
                            "mensaje": "Los valores no pueden ser negativos: use la otra columna."})
        if m.debito and m.credito:
            avisos.append({"tabla": "movimientos", "fila": i, "campo": "debito",
                           "mensaje": "La fila tiene débito y crédito a la vez."})
        por_comp[m.comprobante or "(sin comprobante)"][0] += m.debito
        por_comp[m.comprobante or "(sin comprobante)"][1] += m.credito
    descuadres = [{"comprobante": c, "debito": format(d, "f"), "credito": format(cr, "f"),
                   "diferencia": format(d - cr, "f")} for c, (d, cr) in por_comp.items() if d != cr]
    for d in descuadres:
        avisos.append({"tabla": "movimientos", "comprobante": d["comprobante"], "mensaje":
                       f"El comprobante {d['comprobante']} no cumple partida doble: diferencia "
                       f"{pesos(Decimal(d['diferencia']))}."})
    for i, s in enumerate(paquete.saldos_iniciales):
        if s.cuenta and not p.valido(s.cuenta):
            errores.append({"tabla": "saldos_iniciales", "fila": i, "campo": "cuenta",
                            "mensaje": f"La cuenta «{s.cuenta}» no existe en el PUC."})
    td = sum((m.debito for m in paquete.movimientos), CERO)
    tc = sum((m.credito for m in paquete.movimientos), CERO)
    sd = sum((s.debito for s in paquete.saldos_iniciales), CERO)
    sc = sum((s.credito for s in paquete.saldos_iniciales), CERO)
    return {
        "errores": errores, "avisos": avisos, "descuadres": descuadres,
        "totales": {"debito": format(td, "f"), "credito": format(tc, "f"),
                    "saldos_debito": format(sd, "f"), "saldos_credito": format(sc, "f")},
        "cuadra": td == tc and not descuadres,
    }


def aplicar(entrada: dict, cambios: dict[str, list[dict]]) -> dict:
    """Entrada nueva con las tablas que mandó la pantalla (las que no mandó quedan igual)."""
    paquete_json = dict(entrada.get("paquete") or {})
    for pestana, filas in (cambios or {}).items():
        if pestana not in TABLAS:
            raise ErrorEdicion(f"No conozco la tabla «{pestana}».")
        if not isinstance(filas, list):
            raise ErrorEdicion(f"La tabla «{pestana}» debe ser una lista de filas.")
        limpias = []
        for f in filas:
            if not isinstance(f, dict):
                raise ErrorEdicion(f"Una fila de «{pestana}» no tiene el formato esperado.")
            limpias.append({k: (v if v != "" or k in ("cuenta", "nombre_cuenta") else None)
                            for k, v in f.items() if not k.startswith("_")})
        paquete_json[TABLAS[pestana]] = limpias
    nueva = dict(entrada)
    # Ida y vuelta por el modelo: convierte y descarta campos que no existen; los importes quedan exactos.
    try:
        nueva["paquete"] = E.a_json(E.paquete_desde_json(paquete_json))
    except (ArithmeticError, ValueError, TypeError) as ex:
        raise ErrorEdicion("Hay un valor que no es un número o una fecha válida. Revise las celdas marcadas.") from ex
    return nueva


def entrada_desde_guardado(periodo: dict, resultado: dict | None, diario: list[dict],
                           saldos: list | None) -> dict:
    """Periodos calculados antes del rescate no tienen entrada: se arma con lo guardado.

    El libro diario guardado ya trae los ajustes del motor (depreciación, nómina, costo de
    ventas), así que se edita tal cual, como movimientos, sin volver a proponer ajustes.
    """
    from ..contabilidad.libros import movimientos_desde_guardados

    empresa = Empresa.desde_dict({**((resultado or {}).get("empresa") or {}),
                                  "periodo_desde": periodo["desde"], "periodo_hasta": periodo["hasta"]})
    paquete = Paquete(movimientos=movimientos_desde_guardados(diario), saldos_iniciales=list(saldos or []))
    return E.empaquetar(paquete, empresa, {}, {}, [], [], [], (resultado or {}).get("origenes") or {})


def quitar_archivo(entrada: dict, archivo: str) -> dict:
    """Saca del periodo todo lo que aportó un archivo (las filas cuyo origen empieza por su nombre)."""
    paquete = dict(entrada.get("paquete") or {})
    quitadas = 0
    for lista in TABLAS.values():
        filas = paquete.get(lista) or []
        quedan = [f for f in filas if not str(f.get("origen") or "").startswith(archivo)]
        quitadas += len(filas) - len(quedan)
        paquete[lista] = quedan
    if not quitadas:
        raise ErrorEdicion(f"Ninguna fila del periodo viene de «{archivo}».")
    return {**entrada, "paquete": paquete}


def archivos(entrada: dict) -> list[dict]:
    """Los archivos que aportaron filas a este periodo, con cuántas filas y cuánto suma cada uno."""
    por: dict[str, dict] = {}
    paquete = entrada.get("paquete") or {}
    for pestana, lista in TABLAS.items():
        for f in paquete.get(lista) or []:
            origen = str(f.get("origen") or "")
            nombre = origen.split(" › ")[0].strip() if origen else "(digitado en la aplicación)"
            a = por.setdefault(nombre, {"archivo": nombre, "filas": 0, "tablas": {}, "debito": CERO})
            a["filas"] += 1
            a["tablas"][pestana] = a["tablas"].get(pestana, 0) + 1
            if pestana == "movimientos":
                a["debito"] += D(f.get("debito"))
    return [{**a, "debito": format(a["debito"], "f")} for a in sorted(por.values(), key=lambda x: x["archivo"])]


def resumen_periodo(salida: dict) -> dict:
    r = salida.get("resumen") or {}
    return {k: r.get(k) for k in ("total_activo", "total_pasivo", "total_patrimonio", "ingresos", "utilidad_neta",
                                  "descuadre_esf", "movimientos", "cuentas")}


def normalizar_fecha(v):
    f = parse_fecha(v)
    return f.isoformat() if f else None
