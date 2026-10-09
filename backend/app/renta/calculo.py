"""Liquidación del formulario 210 (personas naturales residentes).

Todo con `Decimal`. Cada valor que va al formulario se aproxima al múltiplo de mil
más cercano (art. 577 E.T.); las fórmulas operan sobre los valores ya aproximados,
igual que el formulario oficial. Las casillas y sus fórmulas son las del instructivo
del 210 (ver `data/renta/210_ag2025.json`).

Dos columnas (spec v2.3 · 5.6):
- **propuesta DIAN**: solo lo que reportaron terceros (`EntradaRenta.solo_terceros`);
- **optimizada**: además, los beneficios con soporte que el contador confirmó.

La función principal es pura: `liquidar(entrada) -> Liquidacion`.
"""
from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal

from . import parametros as P

CERO = Decimal("0")
MIL = Decimal("1000")


def R(valor) -> Decimal:
    """Aproxima al múltiplo de mil más cercano (art. 577 E.T.)."""
    v = Decimal(str(valor or 0))
    return (v / MIL).quantize(Decimal("1"), rounding=ROUND_HALF_UP) * MIL


def _pos(v: Decimal) -> Decimal:
    return v if v > 0 else CERO


@dataclass
class EntradaRenta:
    """Lo que se sabe del contribuyente, ya clasificado. Montos en pesos, sin aproximar."""
    anio: int = 2025
    # Patrimonio
    patrimonio_bruto: Decimal = CERO
    deudas: Decimal = CERO
    # Rentas de trabajo (casillas 32 a 42): salarios y honorarios sin costos
    trabajo_ingresos: Decimal = CERO
    trabajo_incr: Decimal = CERO          # aportes obligatorios a pensión, salud y FSP
    trabajo_meses: int = 12
    relacion_laboral: bool = True         # permite las dos deducciones por un mismo dependiente
    aplicar_25: bool = True               # renta exenta del 25 % (art. 206 num. 10)
    otras_exentas_trabajo: Decimal = CERO
    # Rentas de trabajo que no provienen de relación laboral, con costos (43 a 57)
    honorarios_ingresos: Decimal = CERO
    honorarios_incr: Decimal = CERO
    honorarios_costos: Decimal = CERO
    # Rentas de capital (58 a 73)
    capital_rendimientos: Decimal = CERO  # rendimientos financieros: llevan componente inflacionario
    capital_otros: Decimal = CERO         # arrendamientos, regalías…
    capital_incr_otros: Decimal = CERO
    capital_costos: Decimal = CERO
    # Rentas no laborales (74 a 90)
    nolab_ingresos: Decimal = CERO
    nolab_devoluciones: Decimal = CERO
    nolab_incr: Decimal = CERO
    nolab_costos: Decimal = CERO
    # Beneficios con soporte
    dependientes: int = 0
    intereses_vivienda: Decimal = CERO
    medicina_prepagada: Decimal = CERO
    aportes_voluntarios: Decimal = CERO
    gmf_pagado: Decimal = CERO
    compras_fe: Decimal = CERO            # compras con factura electrónica que cumplen requisitos
    uno_por_ciento_fe: Decimal | None = None  # valor que decide el contador (≤ máximo legal)
    # Pensiones (99 a 103)
    pensiones_ingresos: Decimal = CERO
    pensiones_incr: Decimal = CERO
    pensiones_meses: int = 12
    # Dividendos 2017 y siguientes, 1a subcédula (107)
    dividendos_1a: Decimal = CERO
    # Ganancias ocasionales (112 a 115)
    go_ingresos: Decimal = CERO
    go_costos: Decimal = CERO
    go_exentas: Decimal = CERO
    # Liquidación privada
    retenciones: Decimal = CERO
    anticipo_anterior: Decimal = CERO
    saldo_favor_anterior: Decimal = CERO
    anios_declarando: int = 3             # 1 = primera vez (anticipo 25 %), 2 = 50 %, 3+ = 75 %
    impuesto_neto_anterior: Decimal | None = None
    sanciones: Decimal = CERO

    def solo_terceros(self) -> "EntradaRenta":
        """La propuesta de la DIAN: sin los beneficios que requieren soportes que ella no tiene."""
        return dataclasses.replace(
            self, honorarios_costos=CERO, capital_costos=CERO, nolab_costos=CERO, nolab_devoluciones=CERO,
            dependientes=0, intereses_vivienda=CERO, medicina_prepagada=CERO, aportes_voluntarios=CERO,
            gmf_pagado=CERO, compras_fe=CERO, uno_por_ciento_fe=None, otras_exentas_trabajo=CERO,
            saldo_favor_anterior=CERO)

    @classmethod
    def desde_dict(cls, datos: dict) -> "EntradaRenta":
        campos = {f.name: f for f in dataclasses.fields(cls)}
        limpio = {}
        for k, v in (datos or {}).items():
            if k not in campos or v is None or v == "":
                continue
            tipo = campos[k].type
            if "int" in str(tipo) and "Decimal" not in str(tipo):
                limpio[k] = int(v)
            elif "bool" in str(tipo):
                limpio[k] = bool(v)
            else:
                limpio[k] = Decimal(str(v))
        return cls(**limpio)


@dataclass
class Liquidacion:
    casillas: dict[int, Decimal] = field(default_factory=dict)
    explicacion: dict[int, str] = field(default_factory=dict)
    avisos: list[str] = field(default_factory=list)
    maximo_1pct: Decimal = CERO

    def __getitem__(self, n: int) -> Decimal:
        return self.casillas.get(n, CERO)

    @property
    def a_pagar(self) -> Decimal:
        return self[136]

    @property
    def a_favor(self) -> Decimal:
        return self[137]

    @property
    def neto(self) -> Decimal:
        """Positivo: paga. Negativo: le devuelven."""
        return self[136] - self[137]


def impuesto_241(base: Decimal, anio: int) -> Decimal:
    """Tabla del art. 241 E.T. sobre una base en pesos; devuelve pesos aproximados a mil."""
    p = P.obtener(anio)
    uvt = P.uvt(anio)
    base_uvt = base / uvt
    for r in p["tabla_241"]["rangos"]:
        hasta = r["hasta_uvt"]
        if hasta is None or base_uvt <= P.d(hasta):
            if base_uvt <= P.d(r["desde_uvt"]):
                continue
            imp_uvt = (base_uvt - P.d(r["base_uvt"])) * P.d(r["tarifa"]) + P.d(r["fijo_uvt"])
            return R(imp_uvt * uvt)
    return CERO


def liquidar(e: EntradaRenta) -> Liquidacion:
    p = P.obtener(e.anio)
    uvt = P.uvt(e.anio)
    L = Liquidacion()
    c = L.casillas
    x = L.explicacion

    # ── patrimonio ────────────────────────────────────────────────────────
    c[29] = R(e.patrimonio_bruto)
    c[30] = R(e.deudas)
    c[31] = _pos(c[29] - c[30])

    # ── ingresos y rentas líquidas por columna ────────────────────────────
    c[32] = R(e.trabajo_ingresos)
    c[33] = min(R(e.trabajo_incr), c[32])
    c[34] = _pos(c[32] - c[33])

    c[43] = R(e.honorarios_ingresos)
    c[44] = min(R(e.honorarios_incr), c[43])
    c[45] = R(e.honorarios_costos)
    c[46] = _pos(c[43] - c[44] - c[45])
    c[55] = _pos(c[44] + c[45] - c[43])

    ci = p["componente_inflacionario"]
    incr_inflacion = R(e.capital_rendimientos * P.d(ci["rendimientos"]))
    c[58] = R(e.capital_rendimientos + e.capital_otros)
    c[59] = min(incr_inflacion + R(e.capital_incr_otros), c[58])
    if incr_inflacion:
        x[59] = (f"Componente inflacionario: {Decimal(ci['rendimientos']) * 100}% de los rendimientos financieros "
                 f"({ci['fuente']}).")
    c[60] = R(e.capital_costos)
    c[61] = _pos(c[58] - c[59] - c[60])
    c[62] = CERO
    c[71] = _pos(c[59] + c[60] - c[58])

    c[74] = R(e.nolab_ingresos)
    c[75] = R(e.nolab_devoluciones)
    c[76] = R(e.nolab_incr)
    c[77] = R(e.nolab_costos)
    c[78] = _pos(c[74] - c[75] - c[76] - c[77])
    c[79] = CERO
    c[88] = _pos(c[75] + c[76] + c[77] - c[74])

    # ── beneficios: a qué columna van ─────────────────────────────────────
    columnas = [("trabajo", 34), ("honorarios", 46), ("capital", 61), ("nolab", 78)]
    destino = next((nombre for nombre, casilla in columnas if c[casilla] > 0), "trabajo")
    renta_total_ingresos = c[32] + c[43] + c[58] + c[74]

    aportes = CERO
    if e.aportes_voluntarios:
        ap = p["aportes_voluntarios"]
        aportes = R(min(e.aportes_voluntarios, renta_total_ingresos * P.d(ap["porcentaje_ingreso"]),
                        P.d(ap["tope_uvt_anual"]) * uvt))
    vivienda = R(min(e.intereses_vivienda, P.d(p["intereses_vivienda"]["tope_uvt_anual"]) * uvt))
    prepagada = R(min(e.medicina_prepagada, P.d(p["medicina_prepagada"]["tope_uvt_mensual"]) * 12 * uvt))
    gmf = R(e.gmf_pagado * P.d(p["gmf"]["porcentaje"]))
    dep10 = CERO
    dp = p["dependientes"]
    if e.dependientes > 0 and c[32] > 0 and e.relacion_laboral:
        dep10 = R(min(c[32] * P.d(dp["porcentaje_ingreso"]), P.d(dp["tope_uvt_mensual"]) * e.trabajo_meses * uvt))

    exentas: dict[str, Decimal] = {k: CERO for k, _ in columnas}
    deducciones: dict[str, Decimal] = {k: CERO for k, _ in columnas}
    deducciones[destino] += vivienda + prepagada + gmf
    deducciones["trabajo"] += dep10
    exentas[destino] += aportes

    # Trabajo: AFC (35), otras exentas incluido el 25 % (36), vivienda (38), otras deducciones (39)
    c[35] = aportes if destino == "trabajo" else CERO
    c[38] = vivienda if destino == "trabajo" else CERO
    c[39] = deducciones["trabajo"] - c[38]
    c[40] = c[38] + c[39]
    veinticinco = CERO
    if e.aplicar_25 and c[34] > 0:
        r25 = p["renta_exenta_laboral"]
        base25 = _pos(c[34] - c[40] - c[35] - R(e.otras_exentas_trabajo))
        veinticinco = R(min(base25 * P.d(r25["porcentaje"]), P.d(r25["tope_uvt_anual"]) * uvt))
        if veinticinco:
            x[36] = f"Incluye la renta exenta del 25 % ({r25['norma']}), con tope de {r25['tope_uvt_anual']} UVT."
    c[36] = veinticinco + R(e.otras_exentas_trabajo)
    c[37] = c[35] + c[36]
    exentas["trabajo"] = c[37]

    def columna(nombre: str, afc: int, otras: int, tot_e: int, viv: int, otras_d: int, tot_d: int):
        c[afc] = exentas[nombre] if nombre != "trabajo" else c[afc]
        c[otras] = CERO
        c[tot_e] = c[afc] + c[otras]
        c[viv] = vivienda if destino == nombre else CERO
        c[otras_d] = deducciones[nombre] - c[viv]
        c[tot_d] = c[viv] + c[otras_d]

    columna("honorarios", 47, 48, 49, 50, 51, 52)
    columna("capital", 63, 64, 65, 66, 67, 68)
    columna("nolab", 80, 81, 82, 83, 84, 85)

    # ── límite del 40 % y 1.340 UVT, repartido en orden (instructivo, casilla 41) ──
    lim = p["limite_exentas_deducciones"]
    base_limite = _pos(renta_total_ingresos - (c[33] + c[44] + c[59] + c[76]))
    limite = min(base_limite * P.d(lim["porcentaje"]), P.d(lim["tope_uvt"]) * uvt)
    pedidas = {"trabajo": (c[37] + c[40], 34, 41), "honorarios": (c[49] + c[52], 46, 53),
               "capital": (c[65] + c[68], 61, 69), "nolab": (c[82] + c[85], 78, 86)}
    restante = limite
    total_pedido = sum(v[0] for v in pedidas.values())
    for nombre, (pedido, rl, casilla) in pedidas.items():
        valor = R(max(CERO, min(pedido, c[rl], restante)))
        c[casilla] = valor
        restante -= valor
    if total_pedido > limite:
        L.avisos.append(f"Las rentas exentas y deducciones pedidas ({total_pedido:,.0f}) superan el límite del 40 % "
                        f"o {lim['tope_uvt']} UVT ({limite:,.0f}); se tomó el límite ({lim['norma']}).")

    c[42] = _pos(c[34] - c[41])
    c[54] = _pos(c[46] - c[53]); c[56] = CERO; c[57] = _pos(c[54] - c[56])
    c[70] = _pos(c[61] + c[62] - c[69]); c[72] = CERO; c[73] = _pos(c[70] - c[72])
    c[87] = _pos(c[78] + c[79] - c[86]); c[89] = CERO; c[90] = _pos(c[87] - c[89])

    # ── dependientes fuera del límite (139) ──────────────────────────────
    c[138] = Decimal(e.dependientes)
    c[139] = CERO
    if e.dependientes > 0 and (c[32] > 0 or c[43] > 0):
        adicional = P.d(dp["adicional_uvt_por_dependiente"]) * min(e.dependientes, dp["maximo_dependientes_adicional"]) * uvt
        c[139] = R(min(adicional, c[42] + c[57]))
        x[139] = f"72 UVT por dependiente, hasta 4 ({dp['norma_adicional']})."

    # ── 1 % de compras con factura electrónica (28) ──────────────────────
    fe = p["compras_factura_electronica"]
    maximo = R(min(e.compras_fe * P.d(fe["porcentaje"]), P.d(fe["tope_uvt"]) * uvt))
    L.maximo_1pct = maximo
    c[91] = c[41] + c[42] + c[53] + c[57] + c[69] + c[73] + c[86] + c[90]
    pedido_1pct = maximo if e.uno_por_ciento_fe is None else min(R(e.uno_por_ciento_fe), maximo)
    sin_perdida = _pos(c[91] - (c[41] + c[53] + c[69] + c[86] + c[139]))
    c[28] = min(pedido_1pct, sin_perdida)
    if c[28]:
        x[28] = f"1 % de las compras con factura electrónica que cumplen requisitos, máximo {fe['tope_uvt']} UVT ({fe['norma']})."

    # ── cédula general ───────────────────────────────────────────────────
    c[92] = c[28] + c[41] + c[53] + c[69] + c[86] + c[139]
    c[93] = _pos(c[91] - c[92])
    c[94] = c[95] = c[96] = CERO
    c[97] = _pos(c[93] + c[96] - c[94] - c[95])
    c[98] = CERO

    # ── pensiones ────────────────────────────────────────────────────────
    c[99] = R(e.pensiones_ingresos)
    c[100] = min(R(e.pensiones_incr), c[99])
    c[101] = _pos(c[99] - c[100])
    c[102] = R(min(c[101], P.d(p["pensiones"]["exenta_uvt_mensual"]) * e.pensiones_meses * uvt))
    c[103] = _pos(c[101] - c[102])

    # ── dividendos ───────────────────────────────────────────────────────
    for n in (104, 105, 106, 108, 109, 110):
        c[n] = CERO
    c[107] = R(e.dividendos_1a)

    c[118] = CERO
    c[111] = max(c[97], c[98]) + c[103] + c[107] + c[108] - c[118]

    # ── ganancias ocasionales ────────────────────────────────────────────
    c[112] = R(e.go_ingresos)
    c[113] = R(e.go_costos)
    c[114] = R(e.go_exentas)
    c[115] = _pos(c[112] - c[113] - c[114])

    # ── liquidación privada ──────────────────────────────────────────────
    c[116] = impuesto_241(c[111], e.anio) if c[97] >= c[98] else CERO
    c[117] = impuesto_241(c[111], e.anio) if c[98] > c[97] else CERO
    c[119] = c[120] = CERO
    c[121] = c[116] + c[117] + c[118] + c[119] + c[120]
    dv = p["dividendos"]
    exceso = _pos(c[107] - P.d(dv["descuento_desde_uvt"]) * uvt)
    c[122] = c[123] = CERO
    c[124] = min(R(exceso * P.d(dv["descuento_tarifa"])), c[121])
    c[125] = c[122] + c[123] + c[124]
    c[126] = _pos(c[121] - c[125])
    c[127] = R(c[115] * P.d(p["ganancias_ocasionales"]["tarifa"]))
    c[128] = CERO
    c[129] = _pos(c[126] + c[127] - c[128])
    c[130] = R(e.anticipo_anterior)
    c[131] = R(e.saldo_favor_anterior)
    c[132] = R(e.retenciones)
    c[133] = _anticipo(e, c[126], c[132], p)
    c[135] = R(e.sanciones)
    c[134] = _pos(c[129] + c[133] - c[130] - c[131] - c[132])
    c[136] = _pos(c[129] + c[133] + c[135] - c[130] - c[131] - c[132])
    c[137] = _pos(c[130] + c[131] + c[132] - c[129] - c[133] - c[135])
    c[140] = CERO
    c[141] = CERO
    return L


def _anticipo(e: EntradaRenta, impuesto_neto: Decimal, retenciones: Decimal, p: dict) -> Decimal:
    """Art. 807 E.T.: el menor de los dos procedimientos, menos las retenciones."""
    if impuesto_neto <= 0:
        return CERO
    a = p["anticipo"]
    pct = P.d(a["porcentaje_primer_anio"] if e.anios_declarando <= 1 else
              a["porcentaje_segundo_anio"] if e.anios_declarando == 2 else a["porcentaje_siguientes"])
    metodo1 = impuesto_neto * pct - retenciones
    candidatos = [metodo1]
    if e.impuesto_neto_anterior is not None and e.anios_declarando > 1:
        candidatos.append((impuesto_neto + R(e.impuesto_neto_anterior)) / 2 * pct - retenciones)
    return R(_pos(min(candidatos)))


# Por qué una casilla cambia entre la propuesta DIAN y la optimizada.
MOTIVOS = {
    28: "1 % de las compras con factura electrónica (art. 336 num. 5 E.T.)",
    45: "Costos y gastos con soporte de las rentas de trabajo no laborales",
    60: "Costos y gastos con soporte de las rentas de capital",
    77: "Costos y gastos con soporte de las rentas no laborales",
    41: "Rentas exentas y deducciones con soporte (límite del 40 %, art. 336 E.T.)",
    53: "Rentas exentas y deducciones con soporte (límite del 40 %, art. 336 E.T.)",
    69: "Rentas exentas y deducciones con soporte (límite del 40 %, art. 336 E.T.)",
    86: "Rentas exentas y deducciones con soporte (límite del 40 %, art. 336 E.T.)",
    92: "Total de beneficios aplicados",
    131: "Saldo a favor del año anterior sin devolver",
    139: "Dependientes económicos: 72 UVT por cada uno (Ley 2277 de 2022)",
}


def comparar(e: EntradaRenta, terceros: EntradaRenta | None = None) -> dict:
    """Propuesta DIAN frente a optimizada, casilla por casilla.

    `terceros` es lo que la DIAN conoce (la exógena). Si no se da, se toma la
    entrada sin los beneficios que requieren soporte.
    """
    dian = liquidar(terceros if terceros is not None else e.solo_terceros())
    opt = liquidar(e)
    diferencias = []
    for n in sorted(opt.casillas):
        a, b = dian[n], opt[n]
        if a != b:
            diferencias.append({"casilla": n, "dian": a, "optimizada": b, "motivo": MOTIVOS.get(n, "")})
    return {"dian": dian, "optimizada": opt, "diferencias": diferencias, "ahorro": _pos(dian.neto - opt.neto)}
