"""Sugerencias sobre el trabajo pendiente de cada cliente.

PRINCIPIO
---------
Cada sugerencia nace de un dato **que ya está guardado** y trae ese dato a la
vista. Ninguna es una estimación ni una opinión. Si no hay dato, no hay
sugerencia: preferimos quedarnos callados antes que decirle al contador algo
que no podemos sustentar.

Por eso tampoco se inventan fechas del calendario tributario: los plazos los
fija un decreto cada año, así que el sistema calcula el TURNO del cliente por
el último dígito del NIT (eso sí es una regla fija) y el contador registra las
fechas del año en la pantalla de parámetros.

Cada sugerencia devuelve:
  codigo    identificador estable, para no duplicar ni perder el hilo
  severidad critica | alta | media | informativa
  titulo    lo que pasa, en una línea
  detalle   el dato exacto que lo sustenta
  accion    qué hacer, concreto
  dato      valores crudos para que la interfaz los pinte
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from ..repositorio import clientes as repo_clientes
from ..repositorio import periodos as repo_periodos
from ..utils import nit as unit
from ..utils.numeros import pesos

CERO = Decimal("0")

# ── Umbrales. Están aquí arriba y nombrados para que se puedan discutir y
#    cambiar sin bucear en el código. No son leyes: son criterios de revisión.
UMBRAL_VARIACION = Decimal("0.40")        # 40% de salto contra el periodo anterior
UMBRAL_ENDEUDAMIENTO = Decimal("0.70")    # pasivo / activo
UMBRAL_LIQUIDEZ = Decimal("1.00")         # activo corriente / pasivo corriente
PERDIDAS_SEGUIDAS = 3                      # periodos con pérdida que encienden la alarma
MESES_SIN_TRABAJO = {                      # tolerancia antes de avisar, según periodicidad
    "mensual": 2, "bimestral": 3, "trimestral": 4, "cuatrimestral": 5, "anual": 14,
}


def _d(valor) -> Decimal:
    """Texto decimal → Decimal. Los importes guardados vienen como cadena exacta."""
    if valor is None or valor == "":
        return CERO
    return valor if isinstance(valor, Decimal) else Decimal(str(valor))


def _meses_entre(desde: date, hasta: date) -> int:
    return (hasta.year - desde.year) * 12 + (hasta.month - desde.month)


def _porcentaje(valor: Decimal) -> str:
    return f"{(valor * 100).quantize(Decimal('0.1'))}%"


def _sug(codigo: str, severidad: str, titulo: str, detalle: str, accion: str, **dato) -> dict:
    return {"codigo": codigo, "severidad": severidad, "titulo": titulo,
            "detalle": detalle, "accion": accion, "dato": dato}


ORDEN_SEVERIDAD = {"critica": 0, "alta": 1, "media": 2, "informativa": 3}


# ════════════════════════════════════════════════════════════════════════════
#  Sugerencias de UN cliente
# ════════════════════════════════════════════════════════════════════════════
def de_cliente(cliente_id: str, hoy: date | None = None) -> dict:
    hoy = hoy or date.today()
    cliente = repo_clientes.obtener(cliente_id)
    historia = repo_periodos.serie(cliente_id, limite=36)   # cronológico ascendente
    todos = repo_periodos.listar(cliente_id, limite=200)
    cierres = repo_periodos.listar_cierres(cliente_id)

    salida: list[dict] = []
    salida += _ficha_incompleta(cliente)
    salida += _descuadres(historia)
    salida += _sin_cerrar(todos, cierres)
    salida += _huecos(historia)
    salida += _atraso(cliente, historia, hoy)
    salida += _variaciones(historia)
    salida += _perdidas(historia)
    salida += _estructura_financiera(historia)
    salida += _capital_por_pagar(cliente)
    salida += _capital_vs_estatutos(todos)
    salida += _causal_disolucion(cliente, historia)
    salida += _turno_tributario(cliente)

    salida.sort(key=lambda s: ORDEN_SEVERIDAD.get(s["severidad"], 9))
    return {
        "cliente_id": cliente_id,
        "razon_social": cliente["razon_social"],
        "generado": hoy.isoformat(),
        "periodos_analizados": len(historia),
        "sugerencias": salida,
        "conteo": {
            sev: sum(1 for s in salida if s["severidad"] == sev)
            for sev in ("critica", "alta", "media", "informativa")
        },
    }


# ── reglas ──────────────────────────────────────────────────────────────────
def _capital_vs_estatutos(periodos: list[dict]) -> list[dict]:
    """A3 · El capital en libros no coincide con los estatutos o con el libro de aportes.

    El aviso sale del cálculo (código E5) y se muestra en la ficha como
    advertencia, no como dato informativo: un capital que no cuadra con los
    estatutos es lo primero que pregunta una revisión.
    """
    calculados = [p for p in periodos if p.get("estado") in ("calculado", "cerrado")]
    if not calculados:
        return []
    ultimo = max(calculados, key=lambda p: str(p.get("hasta")))
    datos = repo_periodos.resultado(ultimo["id"])
    if not datos:
        return []
    alertas = [a for a in (datos["resultado"].get("alertas") or []) if a.get("codigo") == "E5"]
    if not alertas:
        return []
    return [_sug(
        "CAPITAL_ESTATUTOS", "alta",
        "El capital en libros no coincide con los estatutos",
        " ".join(a["mensaje"] for a in alertas[:2]),
        "Revise el registro de los aportes antes de firmar: puede haber un aporte contabilizado dos veces o capital no consignado.",
        periodo_id=ultimo["id"],
    )]



def _ficha_incompleta(cliente: dict) -> list[dict]:
    """Datos de la ficha que harán falta al momento de firmar los estados."""
    faltantes = [
        etiqueta for campo, etiqueta in (
            ("direccion", "dirección"), ("municipio", "municipio"), ("ciiu", "actividad CIIU"),
            ("rep_legal", "representante legal"), ("email", "correo electrónico"),
        ) if not str(cliente.get(campo) or "").strip()
    ]
    if not faltantes:
        return []
    return [_sug(
        "FICHA_INCOMPLETA", "media",
        f"Faltan {len(faltantes)} dato(s) en la ficha del cliente",
        "Sin registrar: " + ", ".join(faltantes) + ".",
        "Complete la ficha ahora: estos datos van impresos en los estados financieros y en las cuentas de cobro.",
        faltantes=faltantes,
    )]


def _descuadres(historia: list[dict]) -> list[dict]:
    """Activo ≠ Pasivo + Patrimonio. Es lo más grave que puede pasar."""
    malos = [p for p in historia if _d(p.get("descuadre")) != CERO]
    if not malos:
        return []
    peor = max(malos, key=lambda p: abs(_d(p["descuadre"])))
    return [_sug(
        "DESCUADRE", "critica",
        f"{len(malos)} periodo(s) con el balance descuadrado",
        (f"El peor es el corte al {peor['hasta']}: el activo difiere del pasivo más patrimonio en "
         f"{pesos(abs(_d(peor['descuadre'])))}."),
        "Abra ese periodo y revise el balance de prueba. No firme estados financieros con descuadre.",
        periodos=[{"hasta": p["hasta"], "descuadre": p["descuadre"]} for p in malos],
        peor_corte=peor["hasta"],
    )]


def _sin_cerrar(todos: list[dict], cierres: list[dict]) -> list[dict]:
    """Periodos calculados que nunca se cerraron: el siguiente arrancará sin saldos iniciales."""
    calculados = [p for p in todos if p["estado"] == "calculado"]
    if not calculados:
        return []
    ultimo = max(calculados, key=lambda p: p["hasta"])
    return [_sug(
        "SIN_CERRAR", "alta",
        f"{len(calculados)} periodo(s) calculados pero sin cerrar",
        (f"El más reciente es el corte al {ultimo['hasta']}. "
         f"Hay {len(cierres)} cierre(s) guardado(s) en total."),
        "Cierre el periodo para que sus saldos finales abran automáticamente el periodo siguiente.",
        periodo_id=ultimo["id"], hasta=ultimo["hasta"], cantidad=len(calculados),
    )]


def _huecos(historia: list[dict]) -> list[dict]:
    """Meses sin contabilizar entre dos periodos consecutivos."""
    if len(historia) < 2:
        return []
    huecos = []
    for anterior, siguiente in zip(historia, historia[1:]):
        fin_anterior = date.fromisoformat(anterior["hasta"])
        inicio_siguiente = date.fromisoformat(siguiente["desde"])
        brecha = (inicio_siguiente - fin_anterior).days
        if brecha > 1:
            huecos.append({"desde": fin_anterior.isoformat(), "hasta": inicio_siguiente.isoformat(),
                           "dias": brecha - 1})
    if not huecos:
        return []
    return [_sug(
        "HUECOS", "alta",
        f"Hay {len(huecos)} salto(s) en la secuencia de periodos",
        "; ".join(f"entre {h['desde']} y {h['hasta']} quedan {h['dias']} día(s) sin contabilizar"
                  for h in huecos[:4]) + ".",
        "Cargue los periodos faltantes: sin ellos los saldos iniciales arrastran error hacia adelante.",
        huecos=huecos,
    )]


def _atraso(cliente: dict, historia: list[dict], hoy: date) -> list[dict]:
    """¿Cuánto llevamos sin tocar este cliente, dada su periodicidad?"""
    periodicidad = cliente.get("periodicidad") or "mensual"
    tolerancia = MESES_SIN_TRABAJO.get(periodicidad, 2)
    if not historia:
        return [_sug(
            "SIN_PERIODOS", "alta",
            "Este cliente no tiene ningún periodo contabilizado",
            "No hay balances ni estados financieros guardados.",
            "Suba el primer archivo del cliente para arrancar su historia contable.",
        )]
    ultimo = historia[-1]
    atraso = _meses_entre(date.fromisoformat(ultimo["hasta"]), hoy)
    if atraso <= tolerancia:
        return []
    return [_sug(
        "ATRASADO", "alta" if atraso <= tolerancia * 3 else "critica",
        f"Lleva {atraso} meses sin contabilizar",
        (f"El último corte es al {ultimo['hasta']} y la periodicidad pactada es {periodicidad} "
         f"(se avisa a partir de {tolerancia} meses)."),
        "Póngalo al día antes de que el atraso obligue a reconstruir varios meses de una vez.",
        meses_atraso=atraso, ultimo_corte=ultimo["hasta"], periodicidad=periodicidad,
    )]


def _variaciones(historia: list[dict]) -> list[dict]:
    """Saltos fuertes contra el periodo anterior. No es un error: es algo que hay que poder explicar."""
    if len(historia) < 2:
        return []
    anterior, actual = historia[-2], historia[-1]
    salida = []
    for campo, nombre in (("total_ingresos", "los ingresos"), ("total_gastos", "los gastos"),
                          ("total_activo", "el activo total")):
        base, nuevo = _d(anterior.get(campo)), _d(actual.get(campo))
        if base == CERO:
            continue
        variacion = (nuevo - base) / abs(base)
        if abs(variacion) < UMBRAL_VARIACION:
            continue
        sentido = "subieron" if variacion > 0 else "bajaron"
        if campo == "total_activo":
            sentido = "subió" if variacion > 0 else "bajó"
        salida.append(_sug(
            f"VARIACION_{campo.upper()}", "media",
            f"En el último periodo {nombre} {sentido} {_porcentaje(abs(variacion))}",
            (f"Corte al {anterior['hasta']}: {pesos(base)} → corte al {actual['hasta']}: {pesos(nuevo)}. "
             f"Se avisa por encima de {_porcentaje(UMBRAL_VARIACION)}."),
            "Verifique que el movimiento sea real y no un archivo cargado dos veces o una cuenta mal mapeada.",
            campo=campo, anterior=anterior.get(campo), actual=actual.get(campo),
            variacion=format(variacion, "f"),
        ))
    return salida


def _perdidas(historia: list[dict]) -> list[dict]:
    """Rachas de pérdidas consecutivas."""
    racha = 0
    for p in reversed(historia):
        if _d(p.get("utilidad")) < CERO:
            racha += 1
        else:
            break
    if racha < PERDIDAS_SEGUIDAS:
        return []
    afectados = historia[-racha:]
    acumulada = sum((_d(p.get("utilidad")) for p in afectados), CERO)
    return [_sug(
        "PERDIDAS_SEGUIDAS", "alta",
        f"{racha} periodos seguidos con pérdida",
        (f"Pérdida acumulada en esos periodos: {pesos(abs(acumulada))} "
         f"(desde el corte al {afectados[0]['hasta']})."),
        "Avise al cliente por escrito: las pérdidas sostenidas erosionan el patrimonio y pueden "
        "configurar causal de disolución.",
        periodos=racha, acumulada=format(acumulada, "f"),
    )]


def _estructura_financiera(historia: list[dict]) -> list[dict]:
    """Endeudamiento sobre el último periodo. Se calcula con lo guardado, sin estimar."""
    if not historia:
        return []
    ultimo = historia[-1]
    activo, pasivo = _d(ultimo.get("total_activo")), _d(ultimo.get("total_pasivo"))
    if activo <= CERO:
        return []
    endeudamiento = pasivo / activo
    if endeudamiento < UMBRAL_ENDEUDAMIENTO:
        return []
    return [_sug(
        "ENDEUDAMIENTO", "media",
        f"El endeudamiento llegó a {_porcentaje(endeudamiento)} del activo",
        (f"Corte al {ultimo['hasta']}: pasivo {pesos(pasivo)} sobre activo {pesos(activo)}. "
         f"Se avisa por encima de {_porcentaje(UMBRAL_ENDEUDAMIENTO)}."),
        "Revise con el cliente el plan de pago de los pasivos y mencione el indicador en las notas.",
        endeudamiento=format(endeudamiento, "f"), activo=ultimo.get("total_activo"),
        pasivo=ultimo.get("total_pasivo"),
    )]


def _capital_por_pagar(cliente: dict) -> list[dict]:
    """Socios con aportes comprometidos pero no pagados."""
    pendientes = []
    for s in cliente.get("socios") or []:
        saldo = _d(s.get("comprometido")) - _d(s.get("pagado"))
        if saldo > CERO:
            pendientes.append({"nombre": s.get("nombre", ""), "saldo": format(saldo, "f")})
    if not pendientes:
        return []
    total = sum((_d(p["saldo"]) for p in pendientes), CERO)
    return [_sug(
        "CAPITAL_POR_PAGAR", "media",
        f"{len(pendientes)} socio(s) con capital suscrito sin pagar",
        f"Saldo total por cobrar a los socios: {pesos(total)}.",
        "Registre los pagos recibidos o deje la cuenta por cobrar a socios documentada en las notas.",
        socios=pendientes, total=format(total, "f"),
    )]


def _causal_disolucion(cliente: dict, historia: list[dict]) -> list[dict]:
    """Patrimonio por debajo del 50% del capital suscrito.

    Es la hipótesis de deterioro patrimonial que la ley colombiana obliga a
    revelar. Solo se evalúa si hay capital suscrito registrado en la ficha.
    """
    capital = _d(cliente.get("capital_suscrito"))
    if capital <= CERO or not historia:
        return []
    ultimo = historia[-1]
    patrimonio = _d(ultimo.get("total_patrimonio"))
    mitad = capital / Decimal("2")
    if patrimonio >= mitad:
        return []
    return [_sug(
        "CAUSAL_DISOLUCION", "critica",
        "El patrimonio quedó por debajo de la mitad del capital suscrito",
        (f"Corte al {ultimo['hasta']}: patrimonio {pesos(patrimonio)} frente a un capital suscrito de "
         f"{pesos(capital)} (la mitad son {pesos(mitad)})."),
        "Revele la situación en las notas y notifique por escrito a los socios y al representante legal: "
        "es un hecho de deterioro patrimonial que exige decisión del máximo órgano social.",
        patrimonio=ultimo.get("total_patrimonio"), capital=format(capital, "f"), mitad=format(mitad, "f"),
    )]


def _turno_tributario(cliente: dict) -> list[dict]:
    """Turno del cliente en el calendario DIAN. Las fechas las fija un decreto cada año."""
    turno = unit.turno_dian(cliente.get("nit"))
    if not turno:
        return []
    base = unit.limpiar(cliente.get("nit"))
    return [_sug(
        "TURNO_DIAN", "informativa",
        f"Turno {turno} en el calendario tributario",
        (f"El NIT termina en {base[-1]}, que corresponde al turno {turno} de 10. "
         "Las fechas exactas las fija el decreto de plazos de cada año."),
        "Cargue las fechas del año en la pantalla de parámetros para ver el vencimiento exacto aquí.",
        turno=turno, ultimo_digito=int(base[-1]),
    )]


# ════════════════════════════════════════════════════════════════════════════
#  Panorama de TODA la cartera (tablero de inicio)
# ════════════════════════════════════════════════════════════════════════════
def _informe_en_memoria(cliente: dict, historia: list[dict], cierres: int, hoy: date) -> dict:
    """Aplica TODAS las reglas sobre datos ya cargados, sin tocar la base.

    `de_cliente` consulta y luego evalúa; esto solo evalúa. El tablero carga los
    datos de todos los clientes de un golpe y llama aquí una vez por cliente.
    """
    calculados = [p for p in historia if p["estado"] != "borrador"]
    salida: list[dict] = []
    salida += _ficha_incompleta(cliente)
    salida += _descuadres(calculados)
    salida += _sin_cerrar(historia, [None] * cierres)
    salida += _huecos(calculados)
    salida += _atraso(cliente, calculados, hoy)
    salida += _variaciones(calculados)
    salida += _perdidas(calculados)
    salida += _estructura_financiera(calculados)
    salida += _capital_por_pagar(cliente)
    salida += _causal_disolucion(cliente, calculados)
    salida += _turno_tributario(cliente)
    salida.sort(key=lambda x: ORDEN_SEVERIDAD.get(x["severidad"], 9))
    return {
        "cliente_id": cliente["id"],
        "razon_social": cliente["razon_social"],
        "generado": hoy.isoformat(),
        "periodos_analizados": len(calculados),
        "sugerencias": salida,
        "conteo": {
            sev: sum(1 for x in salida if x["severidad"] == sev)
            for sev in ("critica", "alta", "media", "informativa")
        },
    }


def de_cartera(hoy: date | None = None, limite_clientes: int = 500) -> dict:
    """Revisa los clientes activos y devuelve lo urgente primero.

    RENDIMIENTO: esto se carga en TRES consultas (clientes, periodos, socios),
    no en cuatro por cliente. La versión anterior tardaba ~6 s contra Supabase
    con un solo cliente, y el tiempo crecía en línea recta con la cartera: con
    cien clientes eran minutos. Ahora el costo es casi plano.
    """
    hoy = hoy or date.today()

    pagina = repo_clientes.listar(
        estado="activo", orden="actualizado", descendente=True,
        pagina=1, por_pagina=min(limite_clientes, 500),
    )
    fichas = pagina["clientes"]
    ids = [c["id"] for c in fichas]

    historias = repo_periodos.series_de_varios(ids)
    socios = repo_clientes.socios_de_varios(ids)
    cierres = repo_periodos.cierres_de_varios(ids)

    pendientes: list[dict] = []
    for cliente in fichas:
        datos = {**cliente, "socios": socios.get(cliente["id"], [])}
        try:
            informe = _informe_en_memoria(datos, historias.get(cliente["id"], []),
                                          cierres.get(cliente["id"], 0), hoy)
        except Exception:  # un cliente con datos raros no puede tumbar el tablero
            continue
        urgentes = [x for x in informe["sugerencias"] if x["severidad"] in ("critica", "alta")]
        if not urgentes:
            continue
        pendientes.append({
            "cliente_id": cliente["id"],
            "razon_social": cliente["razon_social"],
            "nit_formateado": cliente["nit_formateado"],
            "municipio": cliente.get("municipio", ""),
            "criticas": sum(1 for x in urgentes if x["severidad"] == "critica"),
            "altas": sum(1 for x in urgentes if x["severidad"] == "alta"),
            "principal": urgentes[0],
        })

    pendientes.sort(key=lambda c: (-c["criticas"], -c["altas"], c["razon_social"]))
    return {
        "generado": hoy.isoformat(),
        "clientes_revisados": len(fichas),
        "clientes_totales": pagina["total"],
        "truncado": pagina["total"] > len(fichas),
        "con_pendientes": len(pendientes),
        "criticas": sum(c["criticas"] for c in pendientes),
        "altas": sum(c["altas"] for c in pendientes),
        "clientes": pendientes[:60],
    }
