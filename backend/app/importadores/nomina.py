"""Formato de nómina del cliente (como NOMINA enero 2025.xlsx): liquidación por empleado + apropiaciones de ley."""
from __future__ import annotations

from ..modelos import Alerta, Empleado, Paquete
from ..nomina import auditoria, parametros
from ..nomina.calculo import liquidar
from ..utils.numeros import CERO, D, es_numero, mes_año_en_texto, normalizar
from .base import Deteccion
from .lector import Hoja

REGLAS = [
    ("valor_hora", ["S B X HORAS", "VR HORA", "VALOR HORA", "V HORA"]),
    ("horas_extra", ["H EXTRAS", "HORAS EXTRA", "HORAS EXTRAS", "EXTRAS"]),
    ("horas", ["HORAS TRABAJADAS", "HORASLAB", "HORAS LAB", "HORAS"]),
    ("devengado", ["TOTAL DEVENGADO", "DEVENGADO"]),
    ("descuentos", ["TOTAL DESCONTADO", "TT DESCUENTOS", "TOTAL DESCUENTOS", "DESCUENTOS"]),
    ("neto", ["TOTAL PAGADO", "NETO PAGADO", "NETO", "TOTAL A PAGAR"]),
    ("basico", ["BASICO", "SALARIO BASICO", "SALARIO"]),
    ("aux", ["TRANSPORTE", "A T", "AUX TRANSPORTE", "AUXILIO DE TRANSPORTE"]),
    ("comisiones", ["COMISIONES"]),
    ("salud", ["SALUD"]),
    ("pension", ["PENSION"]),
    ("nombre", ["NOMBRE", "EMPLEADO"]),
    ("cargo", ["CARGO"]),
    ("cedula", ["CEDULA", "DOCUMENTO"]),
    ("mes", ["MES"]),
]


def _campo(texto: str) -> str | None:
    for campo, patrones in REGLAS:
        if any(texto == p or texto.startswith(p + " ") or texto.startswith(p) and len(p) > 4 for p in patrones):
            return campo
    return None


def detectar(h: Hoja) -> int | None:
    for r in range(min(h.nfilas, 12)):
        campos = {_campo(t) for _, t in h.fila_textos(r)}
        if {"nombre", "basico"} <= campos and ({"devengado", "salud"} & campos):
            return r
    return None


def importar(h: Hoja, r_h: int, id_: str, año_defecto: int, exonerado: bool = True) -> Deteccion:
    cols: dict[str, int] = {}
    for c, t in h.fila_textos(r_h):
        campo = _campo(t)
        if campo and campo not in cols:
            cols[campo] = c
    titulo = " ".join(h.texto(r, c) for r in range(r_h) for c, _ in h.fila_textos(r))
    mes_t, año_t = mes_año_en_texto(titulo)
    año = año_t or año_defecto
    paquete = Paquete()
    filas_cliente, r_aprop = [], None

    def val(r, campo):
        return h.v(r, cols[campo]) if campo in cols else None

    def celda(r, campo):
        return h.origen(r, cols[campo]).split(" › ")[-1] if campo in cols else ""

    for r in range(r_h + 1, h.nfilas):
        if any("APROPIACIONES" in t for _, t in h.fila_textos(r)):
            r_aprop = r
            break
        basico = D(val(r, "basico"))
        if basico <= 0:
            continue
        nombre_raw, cargo = val(r, "nombre"), h.texto(r, cols["cargo"]) if "cargo" in cols else ""
        if (nombre_raw is None or str(nombre_raw).strip() == "") and not cargo:
            paquete.filas_ignoradas.append({"origen": h.origen(r), "motivo": "Fila de subtotal (sin nombre ni cargo)"})
            continue
        if es_numero(nombre_raw) and not isinstance(nombre_raw, str):
            nombre = f"{cargo.title() or 'Empleado'} {int(D(nombre_raw))} (sin nombre)"
        else:
            nombre = str(nombre_raw).strip() if nombre_raw is not None else cargo.title()
        horas, vh = D(val(r, "horas")), D(val(r, "valor_hora"))
        mes = mes_año_en_texto(str(val(r, "mes") or ""))[0] or mes_t
        aux_val = D(val(r, "aux"))
        e = Empleado(nombre=nombre, cargo=cargo, cedula=str(val(r, "cedula") or ""), mes=mes, año=año,
                     aux_transporte="si" if aux_val > 0 else "auto", horas_extra=D(val(r, "horas_extra")),
                     comisiones=D(val(r, "comisiones")), origen=h.origen(r))
        if horas > 31 and vh > 0:
            e.valor_hora, e.horas = vh, horas
        else:
            e.salario_basico = basico
        paquete.empleados.append(e)
        filas_cliente.append({
            "salud": D(val(r, "salud")) if "salud" in cols else None, "celda_salud": celda(r, "salud"),
            "pension": D(val(r, "pension")) if "pension" in cols else None, "celda_pension": celda(r, "pension"),
            "neto": D(val(r, "neto")) if "neto" in cols else None, "celda_neto": celda(r, "neto"),
            "valor_hora": vh or None, "celda_vh": celda(r, "valor_hora"), "aux_archivo": aux_val,
        })

    apropiaciones: dict[str, dict] = {}
    if r_aprop is not None:
        for r in range(r_aprop + 1, h.nfilas):
            textos = h.fila_textos(r)
            if not textos:
                continue
            c_lab = textos[0][0]
            numericos = [c for c in (c_lab + 1, c_lab + 2) if es_numero(h.v(r, c)) and not isinstance(h.v(r, c), str)]
            if not numericos:
                continue
            c_val = numericos[-1]
            concepto = auditoria.concepto_apropiacion(h.texto(r, c_lab))
            if concepto and concepto not in apropiaciones:
                apropiaciones[concepto] = {"valor": D(h.v(r, c_val)), "formula": h.formula(r, c_val),
                                           "celda": h.origen(r, c_val).split(" › ")[-1], "etiqueta": h.texto(r, c_lab)}

    formulas = {h.origen(r, c).split(" › ")[-1]: f for (r, c), f in h.formulas.items()}
    resumen = {"empleados": len(paquete.empleados), "año": año, "mes": mes_t, "titulo": titulo.strip()}
    try:
        liqs = [liquidar(e, e.año or año, exonerado) for e in paquete.empleados]
        hallazgos = auditoria.auditar(h.nombre, filas_cliente, liqs, apropiaciones, formulas)
        paquete.auditoria_nomina = [{**x, "libro": h.archivo} for x in hallazgos]
        resumen["diferencias"] = len(hallazgos)
        codigos = sorted({x["codigo"] for x in hallazgos})
        if hallazgos:
            paquete.alertas.append(Alerta("NOMINA", "advertencia",
                                          f"Nómina «{h.nombre}»: {len(hallazgos)} diferencia(s) frente a la liquidación legal ({', '.join(codigos)}). "
                                          f"Ver pestaña Nómina → Auditoría del archivo."))
    except parametros.ParametrosFaltantes as ex:
        paquete.alertas.append(Alerta("PARAMETROS", "advertencia", str(ex)))

    con_nombre = [e for e in paquete.empleados if "(sin nombre)" not in e.nombre]
    incluir = bool(con_nombre)
    motivo = "" if incluir else "Hoja de ejemplo sin nombres de empleados: se audita pero no se causa en la contabilidad."
    return Deteccion(id_, h.archivo, h.nombre, "nomina", incluir, motivo, resumen, paquete)


def total(paquete: Paquete):
    return sum((e.salario_basico or CERO for e in paquete.empleados), CERO)


def normal(texto: str) -> str:
    return normalizar(texto)
