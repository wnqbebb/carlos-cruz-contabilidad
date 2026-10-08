"""Estados financieros a partir del mayor ajustado (antes del asiento de cierre)."""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal

from ..modelos import Empresa
from ..utils.numeros import CERO, pesos, redondear
from .mayor import CuentaMayor
from .puc import puc
from .reportes import Constructor, col, reporte

CORRECTORAS = ("1299", "1399", "1499", "1592", "1597", "1598", "1599", "1698", "1699", "1798", "1899")
GRUPOS_CORRIENTE = ("11", "12", "13", "14", "17")
GRUPOS_NO_CORRIENTE = ("15", "16", "18", "19")


@dataclass
class Linea:
    codigo: str
    nombre: str
    inicial: Decimal
    final: Decimal


def agrupar_cuentas(mayor: dict[str, CuentaMayor], clases: tuple[str, ...], signo: int = 1) -> list[Linea]:
    """Agrupa a 4 dígitos. signo=1 muestra saldo débito positivo; -1 muestra saldo crédito positivo."""
    p = puc()
    grupos: dict[str, list[CuentaMayor]] = defaultdict(list)
    for c in mayor.values():
        if c.clase in clases:
            grupos[p.cuenta4(c.codigo)].append(c)
    lineas = []
    for cod4, cuentas in sorted(grupos.items()):
        ini = sum((c.neto_inicial for c in cuentas), CERO) * signo
        fin = sum((c.neto for c in cuentas), CERO) * signo
        if ini == 0 and fin == 0:
            continue
        nombre = p.nombre(cod4, cuentas[0].nombre if len(cuentas) == 1 else "")
        lineas.append(Linea(cod4, nombre, ini, fin))
    return lineas


def resultados(mayor: dict[str, CuentaMayor]) -> dict[str, Decimal]:
    """Cifras del estado de resultados (valores positivos en su sentido natural)."""
    r = defaultdict(lambda: CERO)
    for c in mayor.values():
        g, n = c.codigo[:2], c.neto
        if c.codigo.startswith("5905"):
            continue
        if c.codigo.startswith("4175"):
            r["devoluciones"] += n
        elif g == "41":
            r["ingresos_op"] += -n
        elif c.clase == "4":
            r["ingresos_no_op"] += -n
        elif c.clase in ("6", "7"):
            r["costo_ventas"] += n
        elif g == "51":
            r["gastos_admin"] += n
        elif g == "52":
            r["gastos_ventas"] += n
        elif g == "54":
            r["impuesto_renta"] += n
        elif c.clase == "5":
            r["gastos_no_op"] += n
    r["ingresos_netos"] = r["ingresos_op"] - r["devoluciones"]
    r["utilidad_bruta"] = r["ingresos_netos"] - r["costo_ventas"]
    r["utilidad_operacional"] = r["utilidad_bruta"] - r["gastos_admin"] - r["gastos_ventas"]
    r["utilidad_antes_impuestos"] = r["utilidad_operacional"] + r["ingresos_no_op"] - r["gastos_no_op"]
    r["utilidad_neta"] = r["utilidad_antes_impuestos"] - r["impuesto_renta"]
    return dict(r)


def _cols_valor() -> list[dict]:
    return [col("codigo", "Código", ancho=10), col("cuenta", "Cuenta", ancho=48),
            col("valor", "Periodo actual", "dinero"), col("inicial", "Saldo al inicio", "dinero")]


def situacion_financiera(mayor: dict[str, CuentaMayor], empresa: Empresa, subtitulo: str,
                         pasivo_no_corriente: tuple[str, ...] = ()) -> tuple[dict, dict]:
    res = resultados(mayor)
    k = Constructor()
    totales: dict[str, Decimal] = {}

    def bloque(titulo: str, lineas: list[Linea], nombre_total: str) -> int:
        k.seccion(titulo, "cuenta", 1)
        idx = [k.agregar("linea", {"codigo": l.codigo, "cuenta": l.nombre, "valor": l.final, "inicial": l.inicial}, 2)
               for l in lineas]
        v = sum((l.final for l in lineas), CERO)
        i = sum((l.inicial for l in lineas), CERO)
        return k.agregar("subtotal", {"cuenta": nombre_total, "valor": v, "inicial": i}, 1, suma=idx)

    activos = agrupar_cuentas(mayor, ("1",))
    ac = [l for l in activos if l.codigo[:2] in GRUPOS_CORRIENTE]
    anc = [l for l in activos if l.codigo[:2] not in GRUPOS_CORRIENTE]
    k.seccion("ACTIVO")
    t_ac = bloque("Activo corriente", ac, "Total activo corriente")
    t_anc = bloque("Activo no corriente", anc, "Total activo no corriente")
    t_act = k.agregar("total", {"cuenta": "TOTAL ACTIVO", "valor": k.filas[t_ac]["valores"]["valor"] + k.filas[t_anc]["valores"]["valor"],
                                "inicial": k.filas[t_ac]["valores"]["inicial"] + k.filas[t_anc]["valores"]["inicial"]}, suma=[t_ac, t_anc])
    k.vacia()

    pasivos = agrupar_cuentas(mayor, ("2",), -1)
    pnc = [l for l in pasivos if l.codigo in pasivo_no_corriente or l.codigo[:2] in pasivo_no_corriente]
    pc = [l for l in pasivos if l not in pnc]
    k.seccion("PASIVO")
    t_pc = bloque("Pasivo corriente", pc, "Total pasivo corriente")
    t_pnc = bloque("Pasivo no corriente", pnc, "Total pasivo no corriente")
    t_pas = k.agregar("total", {"cuenta": "TOTAL PASIVO", "valor": k.filas[t_pc]["valores"]["valor"] + k.filas[t_pnc]["valores"]["valor"],
                                "inicial": k.filas[t_pc]["valores"]["inicial"] + k.filas[t_pnc]["valores"]["inicial"]}, suma=[t_pc, t_pnc])
    k.vacia()

    patrimonio = agrupar_cuentas(mayor, ("3",), -1)
    k.seccion("PATRIMONIO")
    idx = [k.agregar("linea", {"codigo": l.codigo, "cuenta": l.nombre, "valor": l.final, "inicial": l.inicial}, 2) for l in patrimonio]
    ini_resultado = sum((-c.neto_inicial for c in mayor.values() if c.clase in ("4", "5", "6", "7")), CERO)
    idx.append(k.agregar("linea", {"codigo": "", "cuenta": "Resultado del ejercicio (utilidad / pérdida)",
                                   "valor": res.get("utilidad_neta", CERO), "inicial": ini_resultado}, 2))
    v_pat = sum((k.filas[i]["valores"]["valor"] for i in idx), CERO)
    i_pat = sum((k.filas[i]["valores"]["inicial"] for i in idx), CERO)
    t_pat = k.agregar("total", {"cuenta": "TOTAL PATRIMONIO", "valor": v_pat, "inicial": i_pat}, suma=idx)
    k.vacia()
    v_pp = k.filas[t_pas]["valores"]["valor"] + v_pat
    k.agregar("total", {"cuenta": "TOTAL PASIVO + PATRIMONIO", "valor": v_pp,
                        "inicial": k.filas[t_pas]["valores"]["inicial"] + i_pat}, suma=[t_pas, t_pat])

    total_activo = k.filas[t_act]["valores"]["valor"]
    diferencia = total_activo - v_pp
    if diferencia != 0:
        k.agregar("nota", {"cuenta": f"DESCUADRE: Activo − (Pasivo + Patrimonio) = {pesos(diferencia)}", "valor": diferencia})
    totales = {
        "activo_corriente": k.filas[t_ac]["valores"]["valor"], "activo_no_corriente": k.filas[t_anc]["valores"]["valor"],
        "total_activo": total_activo, "pasivo_corriente": k.filas[t_pc]["valores"]["valor"],
        "pasivo_no_corriente": k.filas[t_pnc]["valores"]["valor"], "total_pasivo": k.filas[t_pas]["valores"]["valor"],
        "total_patrimonio": v_pat, "total_pasivo_patrimonio": v_pp, "diferencia": diferencia,
        "inventarios": sum((l.final for l in activos if l.codigo.startswith("14")), CERO),
        "efectivo": sum((l.final for l in activos if l.codigo.startswith("11")), CERO),
        "capital": sum((l.final for l in patrimonio if l.codigo.startswith("31")), CERO),
    }
    verif = {"activo": total_activo, "pasivo_mas_patrimonio": v_pp, "diferencia": diferencia, "cuadra": diferencia == 0}
    rep = reporte("situacion_financiera", "ESTADO DE SITUACIÓN FINANCIERA", subtitulo, _cols_valor(), k.filas,
                  firmas=True, verificacion=verif)
    return rep, totales


def estado_resultados(mayor: dict[str, CuentaMayor], subtitulo: str) -> tuple[dict, dict]:
    r = resultados(mayor)
    k = Constructor()
    cols = [col("codigo", "Código", ancho=10), col("cuenta", "Concepto", ancho=52), col("valor", "Valor", "dinero")]

    def lineas_de(filtro) -> list[int]:
        idx = []
        for l in agrupar_cuentas(mayor, ("4", "5", "6", "7")):
            if filtro(l.codigo):
                valor = -l.final if l.codigo[0] == "4" and not l.codigo.startswith("4175") else l.final
                idx.append(k.agregar("linea", {"codigo": l.codigo, "cuenta": l.nombre, "valor": valor}, 2))
        return idx

    k.seccion("INGRESOS OPERACIONALES")
    i1 = lineas_de(lambda c: c.startswith("41") and not c.startswith("4175"))
    s_ing = k.agregar("subtotal", {"cuenta": "Total ingresos operacionales", "valor": r.get("ingresos_op", CERO)}, 1, suma=i1)
    i_dev = lineas_de(lambda c: c.startswith("4175"))
    s_net = k.agregar("subtotal", {"cuenta": "INGRESOS OPERACIONALES NETOS", "valor": r["ingresos_netos"]}, 1)
    k.seccion("COSTO DE VENTAS")
    i2 = lineas_de(lambda c: c[0] in "67")
    s_cv = k.agregar("subtotal", {"cuenta": "Total costo de ventas", "valor": r.get("costo_ventas", CERO)}, 1, suma=i2)
    k.agregar("total", {"cuenta": "UTILIDAD BRUTA", "valor": r["utilidad_bruta"]})
    k.seccion("GASTOS OPERACIONALES DE ADMINISTRACIÓN")
    i3 = lineas_de(lambda c: c.startswith("51"))
    k.agregar("subtotal", {"cuenta": "Total gastos de administración", "valor": r.get("gastos_admin", CERO)}, 1, suma=i3)
    k.seccion("GASTOS OPERACIONALES DE VENTAS")
    i4 = lineas_de(lambda c: c.startswith("52"))
    k.agregar("subtotal", {"cuenta": "Total gastos de ventas", "valor": r.get("gastos_ventas", CERO)}, 1, suma=i4)
    k.agregar("total", {"cuenta": "UTILIDAD (PÉRDIDA) OPERACIONAL", "valor": r["utilidad_operacional"]})
    k.seccion("INGRESOS NO OPERACIONALES")
    i5 = lineas_de(lambda c: c[0] == "4" and not c.startswith("41"))
    k.agregar("subtotal", {"cuenta": "Total ingresos no operacionales", "valor": r.get("ingresos_no_op", CERO)}, 1, suma=i5)
    k.seccion("GASTOS NO OPERACIONALES")
    i6 = lineas_de(lambda c: c[0] == "5" and c[:2] not in ("51", "52", "54", "59"))
    k.agregar("subtotal", {"cuenta": "Total gastos no operacionales", "valor": r.get("gastos_no_op", CERO)}, 1, suma=i6)
    k.agregar("total", {"cuenta": "UTILIDAD (PÉRDIDA) ANTES DE IMPUESTOS", "valor": r["utilidad_antes_impuestos"]})
    i7 = lineas_de(lambda c: c.startswith("54"))
    k.agregar("subtotal", {"cuenta": "Impuesto de renta y complementarios", "valor": r.get("impuesto_renta", CERO)}, 1, suma=i7)
    k.agregar("total", {"cuenta": "UTILIDAD (PÉRDIDA) NETA DEL EJERCICIO", "valor": r["utilidad_neta"]})
    del s_ing, s_net, s_cv, i_dev
    return reporte("estado_resultados", "ESTADO DE RESULTADOS INTEGRAL", subtitulo, cols, k.filas, firmas=True), r


NOMBRE_COMPONENTE = {
    "31": "Capital social", "32": "Superávit de capital", "33": "Reservas", "34": "Revalorización del patrimonio",
    "36": "Resultados del ejercicio", "37": "Resultados de ejercicios anteriores", "38": "Superávit por valorizaciones",
}


def cambios_patrimonio(mayor: dict[str, CuentaMayor], utilidad: Decimal, empresa: Empresa, subtitulo: str) -> dict:
    cols = [col("cuenta", "Componente", ancho=38), col("inicial", "Saldo inicial", "dinero"), col("aumentos", "Aumentos", "dinero"),
            col("disminuciones", "Disminuciones", "dinero"), col("resultado", "Resultado del ejercicio", "dinero"),
            col("final", "Saldo final", "dinero")]
    k = Constructor()
    datos = defaultdict(lambda: defaultdict(lambda: CERO))
    for c in mayor.values():
        if c.clase != "3":
            continue
        g = c.codigo[:2]
        datos[g]["inicial"] += -c.neto_inicial
        datos[g]["aumentos"] += c.mov_c
        datos[g]["disminuciones"] += c.mov_d
    datos["36"]["resultado"] += utilidad
    idx = []
    for g in sorted(set(datos) | {"31", "36"}):
        d = datos[g]
        final = d["inicial"] + d["aumentos"] - d["disminuciones"] + d["resultado"]
        idx.append(k.agregar("linea", {"cuenta": NOMBRE_COMPONENTE.get(g, g), "inicial": d["inicial"], "aumentos": d["aumentos"],
                                       "disminuciones": d["disminuciones"], "resultado": d["resultado"], "final": final}, 1))
    claves = ["inicial", "aumentos", "disminuciones", "resultado", "final"]
    k.agregar("total", {"cuenta": "TOTAL PATRIMONIO", **{x: sum((k.filas[i]["valores"][x] for i in idx), CERO) for x in claves}}, suma=idx)
    notas = []
    if utilidad > 0 and empresa.tipo_persona != "natural":
        reserva_actual = sum((-c.neto for c in mayor.values() if c.codigo.startswith("3305")), CERO)
        tope = empresa.capital_suscrito * Decimal("0.5")
        propuesta = min(redondear(utilidad * Decimal("0.10"), 2), max(tope - reserva_actual, CERO))
        notas.append(
            f"Proyecto de distribución (sugerido): reserva legal del 10 % de la utilidad líquida = {pesos(propuesta)} "
            f"(reserva actual {pesos(reserva_actual)}, tope 50 % del capital suscrito {pesos(tope)}; art. 452 del Código de "
            f"Comercio, confirme en los estatutos si aplica). Utilidad a disposición de la asamblea: "
            f"{pesos(utilidad - propuesta)}, a repartir en proporción a las acciones o cuotas.")
    return reporte("cambios_patrimonio", "ESTADO DE CAMBIOS EN EL PATRIMONIO", subtitulo, cols, k.filas, firmas=True, notas=notas)


def flujo_efectivo(mayor: dict[str, CuentaMayor], empresa: Empresa, subtitulo: str) -> dict:
    cols = [col("cuenta", "Concepto", ancho=60), col("valor", "Valor", "dinero")]
    delta = defaultdict(lambda: CERO)
    efectivo_ini = efectivo_fin = CERO
    for c in mayor.values():
        d = c.neto - c.neto_inicial
        if c.clase == "1" and c.codigo.startswith("11"):
            efectivo_ini += c.neto_inicial
            efectivo_fin += c.neto
            continue
        if c.codigo.startswith(CORRECTORAS):
            delta["correctoras"] += -d
        elif c.clase in ("4", "5", "6", "7"):
            delta["resultado"] += -d
        elif c.clase in ("1", "2", "3"):
            delta[c.codigo[:2]] += -d
        else:
            delta["otros"] += -d
    k = Constructor()
    k.seccion("ACTIVIDADES DE OPERACIÓN")
    op = [k.agregar("linea", {"cuenta": "Utilidad (pérdida) del periodo", "valor": delta["resultado"]}, 1),
          k.agregar("linea", {"cuenta": "Más: depreciaciones, amortizaciones y provisiones", "valor": delta["correctoras"]}, 1)]
    for g, nombre in (("13", "(Aumento) disminución en deudores"), ("14", "(Aumento) disminución en inventarios"),
                      ("17", "(Aumento) disminución en diferidos"), ("22", "Aumento (disminución) en proveedores"),
                      ("23", "Aumento (disminución) en cuentas por pagar"), ("24", "Aumento (disminución) en impuestos por pagar"),
                      ("25", "Aumento (disminución) en obligaciones laborales"), ("26", "Aumento (disminución) en pasivos estimados"),
                      ("27", "Aumento (disminución) en ingresos diferidos"), ("28", "Aumento (disminución) en otros pasivos")):
        if delta[g]:
            op.append(k.agregar("linea", {"cuenta": nombre, "valor": delta[g]}, 1))
    if delta["otros"]:
        op.append(k.agregar("linea", {"cuenta": "Otras partidas (cuentas sin clasificar)", "valor": delta["otros"]}, 1))
    t_op = k.agregar("subtotal", {"cuenta": "Efectivo neto de actividades de operación", "valor": sum((k.filas[i]["valores"]["valor"] for i in op), CERO)}, suma=op)
    k.seccion("ACTIVIDADES DE INVERSIÓN")
    inv = []
    for g, nombre in (("12", "Inversiones"), ("15", "Adquisición (venta) de propiedades, planta y equipo"),
                      ("16", "Intangibles"), ("18", "Otros activos"), ("19", "Valorizaciones")):
        if delta[g]:
            inv.append(k.agregar("linea", {"cuenta": nombre, "valor": delta[g]}, 1))
    t_inv = k.agregar("subtotal", {"cuenta": "Efectivo neto de actividades de inversión", "valor": sum((k.filas[i]["valores"]["valor"] for i in inv), CERO)}, suma=inv or None)
    k.seccion("ACTIVIDADES DE FINANCIACIÓN")
    fin = []
    for grupos, nombre in ((("21", "29"), "Obligaciones financieras"), (("31", "32"), "Aportes de capital"),
                           (("33", "34", "36", "37", "38"), "Distribuciones y otros movimientos patrimoniales")):
        v = sum((delta[g] for g in grupos), CERO)
        if v:
            fin.append(k.agregar("linea", {"cuenta": nombre, "valor": v}, 1))
    t_fin = k.agregar("subtotal", {"cuenta": "Efectivo neto de actividades de financiación", "valor": sum((k.filas[i]["valores"]["valor"] for i in fin), CERO)}, suma=fin or None)
    aumento = sum((k.filas[i]["valores"]["valor"] for i in (t_op, t_inv, t_fin)), CERO)
    k.agregar("total", {"cuenta": "AUMENTO (DISMINUCIÓN) NETO DEL EFECTIVO", "valor": aumento}, suma=[t_op, t_inv, t_fin])
    k.agregar("linea", {"cuenta": "Efectivo y equivalentes al inicio del periodo", "valor": efectivo_ini})
    k.agregar("total", {"cuenta": "EFECTIVO Y EQUIVALENTES AL FINAL DEL PERIODO", "valor": efectivo_ini + aumento})
    dif = efectivo_ini + aumento - efectivo_fin
    notas = [] if empresa.grupo_niif == 2 else ["Para el Grupo 3 (microempresas) este estado es opcional; se presenta como información adicional."]
    if dif:
        notas.append(f"Diferencia frente al saldo contable del disponible: {pesos(dif)} (revisar cuentas sin clasificar o descuadres).")
    verif = {"efectivo_final_calculado": efectivo_ini + aumento, "efectivo_final_libros": efectivo_fin, "diferencia": dif, "cuadra": dif == 0}
    return reporte("flujo_efectivo", "ESTADO DE FLUJOS DE EFECTIVO (MÉTODO INDIRECTO)", subtitulo, cols, k.filas, firmas=True,
                   notas=notas, verificacion=verif)


def indicadores(tot: dict, res: dict) -> dict:
    def div(a, b):
        return redondear(a / b, 4) if b else None
    ingresos = res.get("ingresos_netos", CERO)
    cols = [col("indicador", "Indicador", ancho=34), col("formula", "Fórmula", ancho=44), col("valor", "Resultado"), col("lectura", "Interpretación", ancho=50)]
    k = Constructor()
    datos = [
        ("Razón corriente", "Activo corriente / Pasivo corriente", div(tot["activo_corriente"], tot["pasivo_corriente"]), "veces",
         "Pesos de activo corriente por cada peso de deuda de corto plazo."),
        ("Prueba ácida", "(Activo corriente − Inventarios) / Pasivo corriente",
         div(tot["activo_corriente"] - tot["inventarios"], tot["pasivo_corriente"]), "veces", "Liquidez sin depender de vender inventario."),
        ("Capital de trabajo", "Activo corriente − Pasivo corriente", tot["activo_corriente"] - tot["pasivo_corriente"], "pesos",
         "Recursos de corto plazo disponibles para operar."),
        ("Endeudamiento", "Pasivo total / Activo total", div(tot["total_pasivo"], tot["total_activo"]), "porcentaje",
         "Parte de los activos financiada con terceros."),
        ("Margen bruto", "Utilidad bruta / Ingresos netos", div(res.get("utilidad_bruta", CERO), ingresos), "porcentaje", ""),
        ("Margen operacional", "Utilidad operacional / Ingresos netos", div(res.get("utilidad_operacional", CERO), ingresos), "porcentaje", ""),
        ("Margen neto", "Utilidad neta / Ingresos netos", div(res.get("utilidad_neta", CERO), ingresos), "porcentaje", ""),
    ]
    for nombre, formula, valor, unidad, lectura in datos:
        if valor is None:
            texto = "N/A (divisor en cero)"
        elif unidad == "veces":
            texto = f"{valor:.2f} veces".replace(".", ",")
        elif unidad == "porcentaje":
            texto = f"{valor * 100:.2f} %".replace(".", ",")
        else:
            texto = pesos(valor)
        k.agregar("linea", {"indicador": nombre, "formula": formula, "valor": texto, "lectura": lectura})
    return reporte("indicadores", "INDICADORES FINANCIEROS", "", cols, k.filas)


def notas(empresa: Empresa, tot: dict, res: dict, metodo_inventario: str, subtitulo: str, alertas_societarias: list[str]) -> list[dict]:
    marco = ("Grupo 2 — NIIF para las Pymes (Anexo 2 del Decreto 2420 de 2015)" if empresa.grupo_niif == 2
             else "Grupo 3 — Microempresas (Anexo 3 del Decreto 2420 de 2015)")
    accionistas = "; ".join(f"{a['nombre']} ({a.get('acciones', '')} acciones)" for a in empresa.accionistas) or "—"
    return [
        {"titulo": "Nota 1. Entidad que reporta", "parrafos": [
            f"{empresa.razon_social} ({empresa.sigla}), NIT {empresa.nit}, sociedad por acciones simplificada constituida por "
            f"{empresa.constitucion or 'documento privado'}, con domicilio en {empresa.direccion}, {empresa.municipio}. "
            f"Actividades económicas CIIU {empresa.ciiu}."]},
        {"titulo": "Nota 2. Bases de preparación", "parrafos": [
            f"Los estados financieros se preparan conforme al marco técnico normativo del {marco}. "
            f"Moneda funcional y de presentación: peso colombiano (COP). Periodo: {subtitulo}."]},
        {"titulo": "Nota 3. Políticas contables significativas", "parrafos": [
            f"Inventarios: se miden al costo por el método de {'promedio ponderado' if metodo_inventario == 'promedio' else 'primeras en entrar, primeras en salir (PEPS)'}.",
            "Propiedades, planta y equipo: al costo menos depreciación acumulada, por el método de línea recta según su vida útil.",
            "Ingresos: se reconocen cuando se transfieren los riesgos y beneficios de los bienes vendidos.",
            "Beneficios a empleados: se provisionan mensualmente las prestaciones sociales y los aportes de ley."]},
        {"titulo": "Nota 4. Efectivo y equivalentes", "parrafos": [f"Saldo al cierre: {pesos(tot['efectivo'])}."]},
        {"titulo": "Nota 5. Inventarios", "parrafos": [f"Saldo de inventarios al cierre: {pesos(tot['inventarios'])}. Costo de ventas del periodo: {pesos(res.get('costo_ventas', CERO))}."]},
        {"titulo": "Nota 6. Patrimonio", "parrafos": [
            f"Capital suscrito según estatutos: {pesos(empresa.capital_suscrito)}, representado en acciones de valor nominal "
            f"{pesos(empresa.valor_nominal_accion)}. Capital registrado en libros (cuenta 31): {pesos(tot['capital'])}. Accionistas: {accionistas}.",
            f"Resultado del ejercicio: {pesos(res.get('utilidad_neta', CERO))}."]},
        {"titulo": "Nota 7. Hechos relevantes y alertas societarias", "parrafos": alertas_societarias or ["No se identificaron causales societarias de alerta."]},
    ]
