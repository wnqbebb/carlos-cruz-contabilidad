"""Clasificación de las líneas del reporte, preguntas y armado de la declaración (spec v2.3 · 5.4).

- Primera señal: el renglón que sugiere la DIAN (`R29` = casilla 29 del 210…). Las
  reglas propias (por el texto del detalle) lo validan; si no coinciden, se marca.
- Los pagos de una misma empresa que pueden ser trabajo o venta («documentos
  soporte») son UNA pregunta por pagador, no una por documento.
- Máximo 5 preguntas «Por confirmar». Los beneficios van aparte («¿Podemos pagar menos?»).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from decimal import Decimal

from rapidfuzz import fuzz

from . import parametros as P
from .calculo import CERO, EntradaRenta, liquidar
from .lectura import Linea, sin_tildes

CATEGORIAS = {
    "patrimonio": "Patrimonio (bienes y saldos)",
    "deuda": "Deudas",
    "ingreso_trabajo": "Ingresos por salarios",
    "ingreso_honorarios": "Honorarios y servicios personales",
    "ingreso_por_definir": "Pagos recibidos: ¿trabajo o venta?",
    "ingreso_capital_financiero": "Rendimientos financieros",
    "ingreso_capital_otro": "Arrendamientos y otras rentas de capital",
    "ingreso_no_laboral": "Ventas y otras rentas no laborales",
    "pension": "Pensiones",
    "dividendo": "Dividendos",
    "ganancia_ocasional": "Ganancias ocasionales",
    "incr": "Aportes obligatorios (no constitutivos de renta)",
    "costo": "Costos y gastos con soporte",
    "retencion": "Retenciones en la fuente",
    "vivienda": "Intereses de vivienda",
    "prepagada": "Medicina prepagada",
    "aportes_voluntarios": "Aportes voluntarios y AFC",
    "gmf": "GMF (4 × 1.000)",
    "compras_fe": "Compras con factura electrónica",
    "facturacion_emitida": "Facturación electrónica emitida",
    "anterior_patrimonio": "Año anterior: patrimonio bruto declarado",
    "anterior_saldo_favor": "Año anterior: saldo a favor",
    "anterior_anticipo": "Año anterior: anticipo liquidado",
    "informativo": "Solo informativo (topes)",
}

RENGLON_A_CATEGORIA = {
    29: "patrimonio", 30: "deuda", 32: "ingreso_trabajo", 33: "incr", 38: "vivienda", 43: "ingreso_honorarios",
    58: "ingreso_capital_financiero", 74: "ingreso_no_laboral", 99: "pension", 104: "dividendo", 107: "dividendo",
    108: "dividendo", 109: "dividendo", 112: "ganancia_ocasional", 130: "anterior_anticipo", 131: "anterior_saldo_favor",
    132: "retencion",
}

# (categoría, palabras que deben aparecer TODAS, palabras que excluyen)
REGLAS: list[tuple[str, tuple[str, ...], tuple[str, ...]]] = [
    ("retencion", ("RETENCION",), ()),
    ("anterior_saldo_favor", ("SALDO A FAVOR",), ()),
    ("anterior_patrimonio", ("PATRIMONIO", "DECLARADO"), ()),
    ("anterior_anticipo", ("ANTICIPO",), ()),
    ("informativo", ("CONSUMOS",), ()),
    ("informativo", ("MOVIMIENTOS",), ()),
    ("informativo", ("CONSIGNACIONES",), ()),
    ("informativo", ("INVERSIONES EN FONDOS",), ("SALDO",)),
    ("compras_fe", ("FACTURAS", "AJUSTES"), ()),
    ("compras_fe", ("COMPRAS",), ("VENTAS",)),
    ("facturacion_emitida", ("FACTURACION ELECTRONICA",), ()),
    ("vivienda", ("INTERESES", "VIVIENDA"), ()),
    ("vivienda", ("INTERESES", "HIPOTEC"), ()),
    ("prepagada", ("PREPAGADA",), ()),
    ("prepagada", ("SEGURO", "SALUD"), ()),
    ("aportes_voluntarios", ("AFC",), ()),
    ("aportes_voluntarios", ("VOLUNTARI",), ()),
    ("gmf", ("GRAVAMEN",), ()),
    ("gmf", ("GMF",), ()),
    ("incr", ("APORTES", "OBLIGATORI"), ()),
    ("incr", ("FONDO DE SOLIDARIDAD",), ()),
    ("deuda", ("CUENTAS POR PAGAR",), ()),
    ("deuda", ("SALDO", "DEUDA"), ()),
    ("deuda", ("SALDO", "CREDITO"), ("TARJETA",)),
    ("deuda", ("OBLIGACION",), ()),
    ("patrimonio", ("AVALUO",), ()),
    ("patrimonio", ("VEHICULO",), ()),
    ("patrimonio", ("SALDO",), ()),
    ("patrimonio", ("CDT",), ()),
    ("ingreso_capital_financiero", ("RENDIMIENTOS",), ()),
    ("ingreso_capital_financiero", ("INTERESES",), ()),
    ("ingreso_capital_otro", ("ARRENDAMIENTO",), ()),
    ("ingreso_capital_otro", ("REGALIAS",), ()),
    ("dividendo", ("DIVIDENDO",), ()),
    ("dividendo", ("PARTICIPACIONES",), ()),
    ("pension", ("PENSION",), ("APORTE", "OBLIGATORI", "VOLUNTARI")),
    ("ingreso_trabajo", ("SALARIO",), ()),
    ("ingreso_trabajo", ("PAGOS LABORALES",), ()),
    ("ingreso_trabajo", ("RENTAS DE TRABAJO",), ()),
    ("ingreso_honorarios", ("HONORARIOS",), ()),
    ("ingreso_honorarios", ("COMISIONES",), ()),
    ("ingreso_por_definir", ("DOCUMENTO", "SOPORTE"), ()),
    ("ingreso_por_definir", ("SERVICIOS",), ()),
    ("ingreso_por_definir", ("OTROS INGRESOS",), ()),
    ("ganancia_ocasional", ("LOTERIA",), ()),
    ("ganancia_ocasional", ("PREMIO",), ()),
    ("ganancia_ocasional", ("HERENCIA",), ()),
    ("ingreso_no_laboral", ("VENTAS",), ()),
]


def clasificar(l: Linea) -> tuple[str, str, bool]:
    """(categoría, por qué, el renglón de la DIAN no coincide)."""
    D = sin_tildes(f"{l.detalle} {l.uso}" if not l.detalle else l.detalle)
    por_regla = None
    for cat, todas, excluye in REGLAS:
        if all(t in D for t in todas) and not any(e in D for e in excluye):
            por_regla = cat
            break
    if por_regla is None and len(D) >= 8:
        # Texto encimado o mal leído: se admite un parecido alto con las palabras de la regla.
        for cat, todas, excluye in REGLAS:
            if all(len(t) >= 5 and fuzz.partial_ratio(t, D) >= 88 for t in todas) and not any(e in D for e in excluye):
                por_regla = cat
                break
    por_renglon = RENGLON_A_CATEGORIA.get(l.renglon) if l.renglon else None
    if por_regla == "ingreso_capital_financiero" and por_renglon == "ingreso_capital_financiero":
        pass
    if por_regla:
        conflicto = bool(por_renglon) and por_renglon != por_regla and not (
            por_regla == "ingreso_capital_otro" and por_renglon == "ingreso_capital_financiero")
        motivo = f"Por el detalle «{l.detalle[:60]}»" + (f"; la DIAN sugiere R{l.renglon}" if l.renglon else "")
        return por_regla, motivo, conflicto
    if por_renglon:
        return por_renglon, f"Renglón sugerido por la DIAN: R{l.renglon}", False
    if l.tope == 1:
        return "ingreso_por_definir", "Marcado «Tope 1: ingresos» por la DIAN", False
    if l.tope == 2:
        return "patrimonio", "Marcado «Tope 2: patrimonio» por la DIAN", False
    if l.tope in (3, 4):
        return "informativo", f"Solo cuenta para el Tope {l.tope}", False
    if l.tope == 5:
        return "compras_fe", "Marcado «Tope 5: compras» por la DIAN", False
    return "informativo", "Sin renglón sugerido: solo informativo", False


@dataclass
class Clasificada:
    linea: Linea
    categoria: str
    motivo: str
    conflicto: bool = False
    incluida: bool = True
    pagador: str = ""


# Palabras de los reportes de exógena: sirven para saber si un detalle se leyó o es ruido.
VOCABULARIO = {
    "SALDO", "CUENTAS", "BANCARIAS", "TITULAR", "PRINCIPAL", "VALOR", "TOTAL", "MOVIMIENTOS", "INGRESOS",
    "DOCUMENTOS", "SOPORTE", "CONSUMOS", "GASTOS", "TARJETA", "CREDITO", "DEBITO", "RENDIMIENTOS", "RETENCION",
    "RETENCIONES", "INVERSION", "INVERSIONES", "FONDOS", "COLECTIVA", "PAGAR", "CLIENTES", "CONCEPTO",
    "FACTURACION", "ELECTRONICA", "FACTURAS", "AJUSTES", "NOTAS", "PATRIMONIO", "BRUTO", "DECLARADO", "AVALUO",
    "CATASTRAL", "VEHICULO", "OTROS", "PAGOS", "APORTES", "SALUD", "PENSION", "INTERESES", "VIVIENDA", "CARTERA",
    "PAGADOS", "PRACTICADA", "UTILIDADES", "SUMA", "MONTO", "SERVICIOS", "HONORARIOS", "SALARIOS", "FAVOR",
    "DIVIDENDOS", "PARTICIPACIONES", "ARRENDAMIENTOS", "COMPRAS", "VENTAS", "DEUDA", "OBLIGACIONES", "ACTIVOS",
    "PROVEEDORES", "TERCERO", "DISTRIBUIDO", "CDT", "AHORROS", "CORRIENTES", "DECLARACIONES", "IVA",
}


def legible(texto: str) -> bool:
    """¿El detalle se leyó? Al menos la mitad de sus palabras son del vocabulario del reporte."""
    palabras = [p for p in re.findall(r"[A-Za-zÁÉÍÓÚÑáéíóúñ]{3,}", sin_tildes(texto))]
    if not palabras:
        return False
    buenas = sum(1 for p in palabras if p in VOCABULARIO or any(fuzz.ratio(p, v) >= 85 for v in VOCABULARIO))
    return buenas / len(palabras) >= 0.5


def clave_pagador(entidad: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", sin_tildes(entidad))[:24] or "SIN-NOMBRE"


def es_entidad_financiera(entidad: str) -> bool:
    T = sin_tildes(entidad).upper()
    return any(k in T for k in ("BANCO", "BANCOLOMBIA", "DAVIVIENDA", "BBVA", "OCCIDENTE", "POPULAR",
                                "COLPATRIA", "FALABELLA", "SERFINANZA", "PICHINCHA", "COOPERATIVA",
                                "FIDUCIARIA", "FONDO DE EMPLEADOS", "COOP", "FINANCIERA"))


def clasificar_todas(lineas: list[Linea], ajustes: dict[str, str] | None = None) -> list[Clasificada]:
    """`ajustes`: id de línea → categoría elegida por el contador (reclasificar con un clic)."""
    ajustes = ajustes or {}
    out = []
    for l in lineas:
        cat, motivo, conflicto = clasificar(l)
        if l.id in ajustes and ajustes[l.id] in CATEGORIAS:
            cat, motivo, conflicto = ajustes[l.id], "Reclasificada por el contador", False
        out.append(Clasificada(linea=l, categoria=cat, motivo=motivo, conflicto=conflicto,
                                pagador=clave_pagador(l.entidad)))
    # Filas ilegibles de una entidad que en otras filas aparece pagando ingresos: se
    # asumen iguales a esas (se ve en pantalla y se reclasifica con un clic).
    ingresos_por_entidad: dict[str, str] = {}
    for c in out:
        if c.categoria.startswith("ingreso_") and c.linea.entidad and not es_entidad_financiera(c.linea.entidad):
            ingresos_por_entidad.setdefault(c.pagador, c.categoria)
    # Una entidad que se repite en varias filas ilegibles suele ser un mismo pagador
    # (pagos por documentos soporte): se pregunta UNA vez por todo, con opción «no es ingreso».
    repetidas: dict[str, int] = {}
    for c in out:
        if c.categoria == "informativo" and not legible(c.linea.detalle) and len(c.pagador) >= 6:
            repetidas[c.pagador] = repetidas.get(c.pagador, 0) + 1
    for c in out:
        if c.categoria != "informativo" or c.linea.id in ajustes or c.linea.tope or legible(c.linea.detalle):
            continue
        if c.pagador in ingresos_por_entidad:
            c.categoria = ingresos_por_entidad[c.pagador]
            c.motivo = "Texto ilegible: igual que las otras filas de la misma entidad"
        elif repetidas.get(c.pagador, 0) >= 3 and not es_entidad_financiera(c.linea.entidad):
            c.categoria = "ingreso_por_definir"
            c.motivo = "Texto ilegible; la misma entidad aparece en varias filas: confirme qué son"
        if not legible(c.linea.detalle):
            c.linea.encimada = True
    return out


# ── preguntas ───────────────────────────────────────────────────────────
def _p(v: Decimal) -> str:
    return "$ " + f"{v:,.0f}".replace(",", ".")


@dataclass
class Pregunta:
    id: str
    texto: str
    opciones: list[dict]
    defecto: str
    detalle: str = ""
    lineas: list[str] = field(default_factory=list)


def preguntas(clas: list[Clasificada], sugerencias_a_mano: list[str]) -> list[Pregunta]:
    qs: list[Pregunta] = []
    grupos: dict[str, list[Clasificada]] = {}
    for c in clas:
        if c.categoria == "ingreso_por_definir":
            grupos.setdefault(c.pagador, []).append(c)
    for clave, cs in sorted(grupos.items(), key=lambda kv: -sum(c.linea.importe() for c in kv[1])):
        if clave == "SIN-NOMBRE" or not re.search(r"[A-Z]{4,}", sin_tildes(cs[0].linea.entidad)) or es_entidad_financiera(cs[0].linea.entidad):
            continue  # entidad ilegible o financiera: no se pregunta como ingreso laboral
        total = sum((c.linea.importe() for c in cs), CERO)
        entidad = cs[0].linea.entidad or "un mismo pagador"
        qs.append(Pregunta(
            id=f"pagador:{clave}",
            texto=(f"Estos {_p(total)} que le pagó {entidad} en {len(cs)} "
                   f"{'documento' if len(cs) == 1 else 'documentos'}, ¿son por su trabajo personal o por venta de productos?"),
            opciones=[{"id": "trabajo", "texto": "Trabajo personal (con el 25 % exento)"},
                      {"id": "honorarios", "texto": "Servicios con costos y gastos propios"},
                      {"id": "venta", "texto": "Venta de productos"},
                      {"id": "no_ingreso", "texto": "No son ingresos del contribuyente"}],
            defecto="trabajo", detalle="Define la cédula y los beneficios que aplican.",
            lineas=[c.linea.id for c in cs]))
    ajenas = [c for c in clas if c.linea.no_titular and c.categoria not in ("informativo",)]
    if ajenas:
        qs.append(Pregunta(
            id="no_titular",
            texto=(f"{'Esta cuenta no está' if len(ajenas) == 1 else f'Estas {len(ajenas)} cuentas no están'} a nombre "
                   "del contribuyente como titular principal. ¿Las incluimos?"),
            opciones=[{"id": "incluir", "texto": "Sí, incluirlas"}, {"id": "excluir", "texto": "No, dejarlas fuera"}],
            defecto="incluir", lineas=[c.linea.id for c in ajenas]))
    saldo = sum((c.linea.importe() for c in clas if c.categoria == "anterior_saldo_favor"), CERO)
    sugerido = _cifra_a_mano(sugerencias_a_mano, ("SF", "SALDO"))
    if saldo or sugerido:
        valor = saldo or sugerido
        origen = "del reporte" if saldo else "escrito a mano en la foto (confírmelo con la declaración anterior)"
        qs.append(Pregunta(
            id="saldo_favor",
            texto=f"Hay un saldo a favor del año anterior de {_p(valor)}, {origen}. ¿Lo usamos?",
            opciones=[{"id": "si", "texto": "Sí, usarlo"}, {"id": "no", "texto": "No (ya se pidió en devolución)"}],
            defecto="si" if saldo else "no", detalle=str(valor)))
    # Máximo 5: las de saldo a favor y titularidad siempre entran; los pagadores, los de más valor.
    extras = [q for q in qs if not q.id.startswith("pagador:")]
    pagadores = [q for q in qs if q.id.startswith("pagador:")]
    return pagadores[: 5 - len(extras)] + extras


def _cifra_a_mano(sugerencias: list[str], claves: tuple[str, ...]) -> Decimal:
    for s in sugerencias:
        if any(sin_tildes(s).startswith(k) for k in claves):
            return Decimal(re.sub(r"\D", "", s.split(":")[-1]) or "0")
    return CERO


# ── beneficios («¿Podemos pagar menos?») ───────────────────────────────
BENEFICIOS = [
    ("dependientes", "¿Tiene hijos o personas a cargo?", "certificado o registro civil"),
    ("intereses_vivienda", "¿Paga crédito de vivienda?", "certificado de intereses del banco"),
    ("medicina_prepagada", "¿Paga medicina prepagada o seguro de salud?", "certificado de pagos"),
    ("aportes_voluntarios", "¿Hizo aportes voluntarios a pensión o AFC?", "certificado del fondo"),
    ("gmf_pagado", "¿Tiene el certificado del GMF (4 × 1.000) pagado?", "certificado del banco"),
    ("compras_fe", "¿Las compras con factura electrónica se pagaron con tarjeta o medio electrónico, a su nombre, "
                   "y no se pidieron como costo?", "relación de facturas"),
]


def beneficios_posibles(entrada: EntradaRenta, compras_fe: Decimal) -> list[dict]:
    """Cada beneficio con su ahorro estimado máximo (recalculando con el tope legal)."""
    p = P.obtener(entrada.anio)
    uvt = P.uvt(entrada.anio)
    base = liquidar(entrada).neto
    tiene_trabajo = entrada.trabajo_ingresos > 0 or entrada.honorarios_ingresos > 0
    ingresos = entrada.trabajo_ingresos + entrada.honorarios_ingresos + entrada.capital_rendimientos + \
        entrada.capital_otros + entrada.nolab_ingresos
    maximos = {
        "dependientes": 4 if tiene_trabajo else 0,
        "intereses_vivienda": P.d(p["intereses_vivienda"]["tope_uvt_anual"]) * uvt,
        "medicina_prepagada": P.d(p["medicina_prepagada"]["tope_uvt_mensual"]) * 12 * uvt,
        "aportes_voluntarios": min(ingresos * P.d(p["aportes_voluntarios"]["porcentaje_ingreso"]),
                                   P.d(p["aportes_voluntarios"]["tope_uvt_anual"]) * uvt),
        "gmf_pagado": ingresos * Decimal("0.004"),
        "compras_fe": compras_fe,
    }
    out = []
    for clave, texto, soporte in BENEFICIOS:
        maximo = maximos[clave]
        if not maximo:
            continue
        prueba = EntradaRenta(**{**entrada.__dict__, clave: maximo})
        ahorro = base - liquidar(prueba).neto
        out.append({"id": clave, "texto": texto, "soporte": soporte, "ahorro_hasta": max(ahorro, CERO),
                    "maximo": maximo})
    return out


# ── armado de la declaración ────────────────────────────────────────────
CAMPO_POR_CATEGORIA = {
    "patrimonio": "patrimonio_bruto", "deuda": "deudas", "ingreso_trabajo": "trabajo_ingresos",
    "ingreso_honorarios": "honorarios_ingresos", "ingreso_capital_financiero": "capital_rendimientos",
    "ingreso_capital_otro": "capital_otros", "ingreso_no_laboral": "nolab_ingresos", "pension": "pensiones_ingresos",
    "dividendo": "dividendos_1a", "ganancia_ocasional": "go_ingresos", "incr": "trabajo_incr",
    "retencion": "retenciones", "vivienda": "intereses_vivienda", "prepagada": "medicina_prepagada",
    "aportes_voluntarios": "aportes_voluntarios", "gmf": "gmf_pagado", "anterior_anticipo": "anticipo_anterior",
}
MANUALES = {
    "ingreso_no_laboral": "nolab_ingresos", "costo_no_laboral": "nolab_costos", "ingreso_trabajo": "trabajo_ingresos",
    "ingreso_honorarios": "honorarios_ingresos", "costo_honorarios": "honorarios_costos",
    "ingreso_capital_otro": "capital_otros", "costo_capital": "capital_costos", "incr_trabajo": "trabajo_incr",
    "patrimonio": "patrimonio_bruto", "deuda": "deudas", "retencion": "retenciones", "pension": "pensiones_ingresos",
    "dividendo": "dividendos_1a", "ganancia_ocasional": "go_ingresos",
}


def construir(clas: list[Clasificada], respuestas: dict[str, str], beneficios: dict, manuales: list[dict],
              anio: int, anios_declarando: int = 3) -> tuple[EntradaRenta, EntradaRenta, list[dict]]:
    """Devuelve (optimizada, propuesta DIAN, origen de cada peso por campo)."""
    excluir_ajenas = respuestas.get("no_titular") == "excluir"
    opt: dict[str, Decimal] = {}
    dian: dict[str, Decimal] = {}
    origen: list[dict] = []
    compras = CERO
    emitida = CERO
    relacion_laboral = False

    def sumar(d: dict, campo: str, v: Decimal):
        d[campo] = d.get(campo, CERO) + v

    for c in clas:
        l = c.linea
        if not c.incluida or (l.no_titular and excluir_ajenas):
            continue
        v = l.importe()
        cat = c.categoria
        campo = CAMPO_POR_CATEGORIA.get(cat)
        if cat == "ingreso_por_definir":
            resp = respuestas.get(f"pagador:{c.pagador}", "trabajo")
            if resp == "no_ingreso":
                continue
            campo = {"trabajo": "trabajo_ingresos", "honorarios": "honorarios_ingresos"}.get(resp, "nolab_ingresos")
            sumar(dian, "trabajo_ingresos", v)
        elif cat == "compras_fe":
            compras += v
        elif cat == "facturacion_emitida":
            emitida += v
        elif cat == "ingreso_trabajo":
            relacion_laboral = True
        if campo:
            sumar(opt, campo, v)
            if cat not in ("vivienda", "prepagada", "aportes_voluntarios", "gmf", "ingreso_por_definir"):
                sumar(dian, campo, v)
            origen.append({"campo": campo, "linea": l.id, "valor": v, "documento": l.documento, "pagina": l.pagina,
                           "fila": l.fila, "recorte": l.recorte})
    # La DIAN toma la facturación electrónica emitida como ingreso si no tiene otro.
    if emitida and not any(dian.get(k) for k in ("trabajo_ingresos", "honorarios_ingresos", "nolab_ingresos")):
        sumar(dian, "nolab_ingresos", emitida)
    for m in manuales or []:
        campo = MANUALES.get(m.get("categoria", ""))
        if campo and m.get("valor"):
            v = Decimal(str(m["valor"]))
            sumar(opt, campo, v)
            origen.append({"campo": campo, "linea": f"contador:{m.get('id', '')}", "valor": v,
                           "documento": "Agregado por el contador", "pagina": 0, "fila": 0, "recorte": "",
                           "descripcion": m.get("descripcion", "")})
    if respuestas.get("saldo_favor") == "si":
        saldo = sum((c.linea.importe() for c in clas if c.categoria == "anterior_saldo_favor"), CERO)
        if not saldo:
            try:
                saldo = Decimal(str(respuestas.get("saldo_favor_valor") or "0"))
            except Exception:
                saldo = CERO
        opt["saldo_favor_anterior"] = saldo
    for clave in ("intereses_vivienda", "medicina_prepagada", "aportes_voluntarios", "gmf_pagado"):
        if beneficios.get(clave):
            opt[clave] = opt.get(clave, CERO) + Decimal(str(beneficios[clave]))
    extras = {}
    if beneficios.get("dependientes"):
        extras["dependientes"] = int(beneficios["dependientes"])
    if beneficios.get("compras_fe") and compras:
        extras["compras_fe"] = compras
        if beneficios.get("uno_por_ciento") not in (None, ""):
            extras["uno_por_ciento_fe"] = Decimal(str(beneficios["uno_por_ciento"]))
    comunes = {"anio": anio, "anios_declarando": anios_declarando, "relacion_laboral": relacion_laboral}
    entrada_opt = EntradaRenta(**comunes, **{k: v for k, v in opt.items()}, **extras)
    entrada_dian = EntradaRenta(**comunes, **{k: v for k, v in dian.items()})
    return entrada_opt, entrada_dian, origen


def marcas(clas: list[Clasificada], topes: dict, entrada: EntradaRenta, anterior_patrimonio: Decimal,
           anio: int) -> list[dict]:
    """Avisos que la DIAN cruza o que piden un dato: no son errores, son cosas a mirar."""
    uvt = P.uvt(anio)
    out = []
    consignaciones = Decimal(str(topes.get(4) or topes.get("4") or 0))
    emitida = sum((c.linea.importe() for c in clas if c.categoria == "facturacion_emitida"), CERO)
    ingresos = entrada.trabajo_ingresos + entrada.honorarios_ingresos + entrada.nolab_ingresos + \
        entrada.capital_rendimientos + entrada.capital_otros + entrada.pensiones_ingresos
    if consignaciones > 1400 * uvt and emitida and consignaciones > 3 * emitida:
        out.append({"tipo": "cruce", "texto": (
            f"Las consignaciones ({_p(consignaciones)}) superan con mucho la facturación electrónica ({_p(emitida)}): "
            "la DIAN cruza este dato. Explique de dónde salen.")})
    if consignaciones > 1400 * uvt and consignaciones > 2 * max(ingresos, Decimal(1)):
        out.append({"tipo": "cruce", "texto": (
            f"Las consignaciones ({_p(consignaciones)}) son más del doble de los ingresos declarados ({_p(ingresos)}): "
            "la DIAN cruza este dato.")})
    declarado_venta = entrada.nolab_ingresos + entrada.honorarios_ingresos + entrada.trabajo_ingresos
    if emitida and emitida > declarado_venta:
        out.append({"tipo": "cruce", "texto": (
            f"Facturó electrónicamente {_p(emitida)} y declara {_p(declarado_venta)} de ingresos por trabajo o ventas.")})
    for c in clas:
        if "AVALUO" in sin_tildes(c.linea.detalle):
            out.append({"tipo": "dato", "texto": (
                f"{c.linea.entidad or 'Un bien'} trae avalúo de {_p(c.linea.importe())}: si tiene el costo fiscal "
                "(escritura más mejoras), úselo; suele ser distinto del avalúo."), "linea": c.linea.id})
    ajenas = [c for c in clas if c.linea.no_titular]
    if ajenas:
        out.append({"tipo": "dato", "texto": f"{len(ajenas)} línea(s) donde el contribuyente no es el titular principal "
                                             "(«NO REGISTRA NO»).", "lineas": [c.linea.id for c in ajenas]})
    for c in clas:
        if c.conflicto:
            out.append({"tipo": "renglon", "texto": (
                f"«{c.linea.detalle[:50]}»: la DIAN sugiere R{c.linea.renglon} y aquí se clasificó como "
                f"{CATEGORIAS[c.categoria].lower()}. Revise."), "linea": c.linea.id})
    if anterior_patrimonio:
        crecimiento = entrada.patrimonio_bruto - anterior_patrimonio
        if crecimiento > ingresos:
            out.append({"tipo": "cruce", "texto": (
                f"El patrimonio creció {_p(crecimiento)} frente al año anterior y los ingresos fueron {_p(ingresos)}: "
                "posible renta por comparación patrimonial (art. 236 E.T.). Justifique la diferencia.")})
    return out
