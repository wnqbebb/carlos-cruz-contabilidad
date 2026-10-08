"""Orquestador: datos importados → balance de prueba → ajustes → balance definitivo → estados financieros."""
from __future__ import annotations

import dataclasses
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from .contabilidad import ajustes as aj
from .contabilidad import cierre as ci
from .contabilidad import estados as ef
from .contabilidad import validaciones as val
from .contabilidad.mayor import SIN_MAPEAR, CuentaMayor, construir_mayor, reporte_balance_prueba, reporte_libro_mayor
from .contabilidad.puc import Mapeador, puc
from .contabilidad.reportes import Constructor, col, reporte
from .importadores.base import Deteccion
from .inventario import kardex as kx
from .modelos import Alerta, Empleado, Empresa, Paquete
from .nomina import parametros
from .nomina.asiento import asiento_causacion, asiento_provisiones, reporte_nomina
from .nomina.calculo import liquidar
from .utils.numeros import CERO, fecha_larga, normalizar, pesos


@dataclass
class Config:
    exonerado_114_1: bool = True
    cuenta_provisiones: str = "25"
    metodo_inventario: str = "promedio"
    calcular_renta: bool = False
    pasivo_no_corriente: list[str] = field(default_factory=list)

    @classmethod
    def desde_dict(cls, d: dict | None) -> "Config":
        c = cls()
        for f in dataclasses.fields(cls):
            if d and f.name in d and d[f.name] is not None:
                setattr(c, f.name, d[f.name])
        return c


# ---------------------------------------------------------------- preparación

def items_mapeo(dets: list[Deteccion], mapeador: Mapeador, sugeridos: dict[str, str] | None = None) -> list[dict]:
    """Nombres de cuenta por mapear al PUC.

    `sugeridos` trae la cuenta que propone un importador que SABE qué es la línea
    (los registros auxiliares saben que «Gasto: arriendo» es un arrendamiento).
    Una confirmación anterior del contador para ese cliente pesa más.
    """
    sugeridos = sugeridos or {}
    p = puc()
    por_nombre: dict[str, dict] = {}
    for d in dets:
        for m in list(d.paquete.movimientos) + list(d.paquete.saldos_iniciales) + list(d.paquete.ajustes_manuales):
            if m.cuenta:
                continue
            n = normalizar(m.nombre_cuenta)
            if n not in por_nombre:
                resuelto = mapeador.resolver(m.nombre_cuenta)
                if n in sugeridos and resuelto.get("fuente") != "confirmado":
                    resuelto = {**resuelto, "codigo": sugeridos[n], "estado": "exacto", "fuente": "registros",
                                "candidatos": [{"codigo": sugeridos[n], "nombre": p.nombre(sugeridos[n]), "puntaje": 100}]}
                por_nombre[n] = {**resuelto, "veces": 0, "hojas": [], "valor": CERO, "por_hoja": {}}
            item = por_nombre[n]
            item["veces"] += 1
            item["valor"] += m.debito + m.credito
            ph = item["por_hoja"].setdefault(d.id, {"veces": 0, "valor": CERO})
            ph["veces"] += 1
            ph["valor"] += m.debito + m.credito
            if d.id not in item["hojas"]:
                item["hojas"].append(d.id)
    orden = {"sin": 0, "confirmar": 1, "exacto": 2}
    return sorted(por_nombre.values(), key=lambda x: (orden[x["estado"]], x["normalizado"]))


def preparar_paquete(dets: list[Deteccion], incluir: dict[str, bool], mapeo: dict[str, str]) -> tuple[Paquete, list[Alerta], list[dict], list[dict]]:
    """Une las hojas incluidas y resuelve códigos. Devuelve (paquete, alertas de importación, auditoría nómina, auditoría EF)."""
    paquete = Paquete()
    alertas: list[Alerta] = []
    aud_nom, aud_ef = [], []
    activos = {d.id for d in dets if incluir.get(d.id, d.incluir)}
    for d in dets:
        activo = d.id in activos
        aud_nom += d.paquete.auditoria_nomina
        aud_ef += d.paquete.auditoria_ef
        for a in d.paquete.alertas:
            alertas.append(a if activo else dataclasses.replace(a, mensaje=f"{a.mensaje} (hoja no incluida en el cálculo)"))
        if activo:
            copia = dataclasses.replace(d.paquete, auditoria_nomina=[], auditoria_ef=[], alertas=[])
            # H07: si la cuenta T con el detalle también entra, de la hoja de
            # trabajo solo se toman los saldos iniciales (sus movimientos son la
            # misma suma, agregada por cuenta).
            if d.resumen.get("detalle_de") in activos:
                copia = dataclasses.replace(copia, movimientos=[])
            paquete.unir(copia)

    def resolver(item):
        if item.cuenta:
            return item
        n = normalizar(item.nombre_cuenta)
        codigo = mapeo.get(n)
        return dataclasses.replace(item, cuenta=codigo if codigo else f"{SIN_MAPEAR}:{n}")

    paquete.movimientos = [resolver(m) for m in paquete.movimientos]
    paquete.saldos_iniciales = [resolver(s) for s in paquete.saldos_iniciales]
    paquete.ajustes_manuales = [resolver(m) for m in paquete.ajustes_manuales]
    return paquete, alertas, aud_nom, aud_ef


# ---------------------------------------------------------------- cálculo

def _en_periodo(e: Empleado, desde: date, hasta: date) -> bool:
    if not e.mes:
        return True
    año = e.año or desde.year
    return (desde.year, desde.month) <= (año, e.mes) <= (hasta.year, hasta.month)


def _ajuste_json(a: aj.Ajuste) -> dict:
    p = puc()
    return {"id": a.id, "titulo": a.titulo, "tipo": a.tipo, "explicacion": a.explicacion, "aceptado": a.aceptado,
            "aceptado_defecto": a.aceptado_defecto, "cuadra": a.cuadra,
            "total": sum((m.debito for m in a.lineas), CERO),
            "lineas": [{"codigo": m.cuenta, "cuenta": p.nombre(m.cuenta, m.nombre_cuenta), "debito": m.debito, "credito": m.credito,
                        "descripcion": m.descripcion} for m in a.lineas]}


def _cuentas_t(mayor: dict[str, CuentaMayor]) -> list[dict]:
    salida = []
    for c in mayor.values():
        if not c.movimientos and c.neto_inicial == 0:
            continue
        deb, cre = [], []
        if c.ini_d:
            deb.append({"valor": c.ini_d, "ref": "Saldo inicial"})
        if c.ini_c:
            cre.append({"valor": c.ini_c, "ref": "Saldo inicial"})
        for m in c.movimientos:
            if m.debito:
                deb.append({"valor": m.debito, "ref": m.comprobante})
            if m.credito:
                cre.append({"valor": m.credito, "ref": m.comprobante})
        salida.append({"codigo": c.codigo, "nombre": c.nombre, "naturaleza": c.naturaleza, "debitos": deb, "creditos": cre,
                       "total_d": c.ini_d + c.mov_d, "total_c": c.ini_c + c.mov_c, "saldo": c.saldo,
                       "contraria": c.saldo < 0})
    return salida


def _dedup(alertas: list[Alerta]) -> list[Alerta]:
    vistos, salida = set(), []
    for a in alertas:
        k = (a.codigo, a.mensaje)
        if k not in vistos:
            vistos.add(k)
            salida.append(a)
    orden = {"error": 0, "advertencia": 1, "info": 2}
    return sorted(salida, key=lambda a: orden.get(a.severidad, 3))


def calcular(paquete: Paquete, empresa: Empresa, config: Config, decisiones: dict[str, bool] | None = None,
             alertas_import: list[Alerta] | None = None, aud_nomina: list[dict] | None = None,
             aud_ef: list[dict] | None = None) -> dict:
    decisiones = decisiones or {}
    desde, hasta = empresa.periodo_desde, empresa.periodo_hasta
    periodo = f"Del {fecha_larga(desde)} al {fecha_larga(hasta)}"
    corte = f"A {fecha_larga(hasta)}"
    alertas: list[Alerta] = list(alertas_import or [])
    saldos, movs = paquete.saldos_iniciales, paquete.movimientos
    mapeador = Mapeador()

    # 1. Mayor y balance de prueba
    mayor_pre = construir_mayor(saldos, movs)
    alertas += val.partida_doble(movs)
    alertas += val.sumas_iguales(mayor_pre, "Balance de prueba")
    alertas += val.fuera_periodo(movs, desde, hasta)
    alertas += val.sin_mapear(mayor_pre)
    alertas += val.titulos_periodo(paquete.titulos, desde, hasta)
    alertas += val.ingreso_igual_aporte(movs, empresa, paquete.aportes_socios)
    alertas_e14, gastos_pers = val.gastos_personales(movs, mapeador.banderas)
    alertas += alertas_e14
    alertas += val.honorarios_sin_retencion([m for m in movs if not m.comprobante.startswith(("CT ", "HT ", "EF "))])
    alertas += val.rep_legal_en_nomina(paquete.empleados, empresa)

    propuestos: list[aj.Ajuste] = []

    # 2. Inventario
    productos, alertas_inv = kx.calcular(paquete.inventario_movs, config.metodo_inventario)
    alertas += alertas_inv
    fisico = kx.comparar_fisico(productos, paquete.inventario_fisico) if productos else []
    venc = kx.vencimientos(productos, hasta) if productos else []
    costo_kardex = sum((p.costo_ventas for p in productos.values()), CERO)
    saldo_kardex = sum((p.saldo_total for p in productos.values()), CERO)
    conciliacion_inv = None
    if productos:
        a1 = aj.ajuste_costo_ventas(mayor_pre, costo_kardex)
        a2 = aj.ajuste_fisico(mayor_pre, fisico)
        propuestos += [a for a in (a1, a2) if a]
        efecto = sum((m.debito - m.credito for a in (a1, a2) if a for m in a.lineas if m.cuenta.startswith("1435")), CERO)
        libros = aj.saldo_prefijo(mayor_pre, "1435")
        kardex_final = saldo_kardex + sum((d["valor"] for d in fisico), CERO)
        a3 = aj.ajuste_conciliacion_inventario(libros + efecto, kardex_final, aj.cuenta_inventario(mayor_pre))
        if a3:
            propuestos.append(a3)
        conciliacion_inv = {"libros_antes": libros, "efecto_ajustes": efecto, "libros_despues": libros + efecto,
                            "kardex": kardex_final, "diferencia": kardex_final - libros - efecto}
        for v in venc:
            if v["estado"] == "Vencido":
                alertas.append(Alerta("VENCIDO", "advertencia", f"Producto vencido: {v['codigo']} {v['descripcion']} lote {v['lote']} "
                                                                f"({v['cantidad']} u, {pesos(v['valor'])}). Evalúe su baja o deterioro."))

    # 3. Depreciación
    a_dep, detalle_dep = aj.ajuste_depreciacion(paquete.activos_fijos, desde, hasta)
    if a_dep:
        propuestos.append(a_dep)
    for cuenta4 in {af.cuenta[:4] for af in paquete.activos_fijos}:
        costo_af = sum((af.costo for af in paquete.activos_fijos if af.cuenta[:4] == cuenta4), CERO)
        libros_af = aj.saldo_prefijo(mayor_pre, cuenta4)
        if libros_af and libros_af != costo_af:
            alertas.append(Alerta("ACTIVOS", "info", f"Cuenta {cuenta4}: libros {pesos(libros_af)} vs relación de activos fijos {pesos(costo_af)}."))

    # 4. Nómina
    liqs = []
    empleados = [e for e in paquete.empleados if _en_periodo(e, desde, hasta)]
    fuera = len(paquete.empleados) - len(empleados)
    if fuera:
        alertas.append(Alerta("NOMINA-PERIODO", "advertencia", f"{fuera} registro(s) de nómina están fuera del periodo y no se causan. "
                                                                f"Ajuste el periodo si corresponde."))
    for e in empleados:
        try:
            liqs.append(liquidar(e, e.año or desde.year, config.exonerado_114_1, date(e.año or desde.year, e.mes or desde.month, 1)))
        except parametros.ParametrosFaltantes as ex:
            alertas.append(Alerta("PARAMETROS", "error", str(ex)))
            break
    if liqs:
        ya_registrado = sum((m.debito - m.credito for m in movs if m.cuenta.startswith("5105")), CERO)
        nota = (f" Ya hay {pesos(ya_registrado)} en gastos de personal (5105) en el diario: si corresponden a esta misma nómina, "
                f"NO acepte este ajuste para no duplicar." if ya_registrado else "")
        a = aj.ajuste_nomina(asiento_causacion(liqs), "nomina_causacion", "Causación de la nómina del periodo",
                             f"Sueldos, auxilio de transporte, deducciones y neto a pagar de {len(liqs)} empleado(s).{nota}", not ya_registrado)
        b = aj.ajuste_nomina(asiento_provisiones(liqs, config.cuenta_provisiones), "nomina_provisiones",
                             "Provisiones de prestaciones y aportes del empleador",
                             "Cesantías 8,33 %, intereses 1 %, prima 8,33 %, vacaciones 4,17 %, pensión 12 %, ARL, caja 4 %"
                             + (" (salud, SENA e ICBF exonerados por el art. 114-1 E.T.)." if config.exonerado_114_1 else ", salud 8,5 %, SENA 2 %, ICBF 3 %."),
                             True)
        propuestos += [x for x in (a, b) if x]

    # 5. Reclasificaciones sugeridas
    _, contrarias = val.naturaleza(mayor_pre)
    for codigo, valor in contrarias:
        if codigo.startswith("240805"):
            propuestos.append(aj.reclasificacion("recl_iva", "Reclasificar IVA pagado a IVA descontable (E6)",
                                                 f"La cuenta {codigo} quedó con saldo débito de {pesos(valor)}: es IVA pagado en compras.",
                                                 "240810", codigo, valor))
    for cuenta, valor in gastos_pers.items():
        propuestos.append(aj.reclasificacion(f"recl_personales_{cuenta}", "Reclasificar gastos personales a cuenta por cobrar a socios (E14)",
                                             f"{pesos(valor)} de gastos personales no son gasto de la empresa.", "132505", cuenta, valor))
    for i, a_e3 in enumerate(x for x in alertas if x.codigo == "E3" and "Ingreso de" in x.mensaje):
        m = next((m for m in movs if m.origen == a_e3.origen and m.cuenta.startswith("4")), None)
        if m:
            propuestos.append(aj.reclasificacion(f"recl_aporte_{i}", "Reclasificar ingreso a aporte de capital (E3)",
                                                 f"El ingreso de {pesos(m.credito)} coincide con un aporte de socio.", m.cuenta, "3105", m.credito))

    # 6. Ajustes manuales
    propuestos += aj.ajuste_manual(paquete.ajustes_manuales)

    for a in propuestos:
        a.aceptado = decisiones.get(a.id, a.aceptado_defecto)

    # A4 · Causación de nómina aceptada con sueldos ya registrados en el diario:
    # puede ser el mismo salario dos veces. No se impide (el contador sabe si son
    # pagos distintos), pero se dice con las dos cifras antes de cerrar.
    causacion = next((a for a in propuestos if a.id == "nomina_causacion" and a.aceptado), None)
    if causacion:
        en_diario = sum((m.debito - m.credito for m in movs if m.cuenta.startswith("5105")), CERO)
        en_ajuste = sum((m.debito - m.credito for m in causacion.lineas if m.cuenta.startswith("5105")), CERO)
        if en_diario:
            alertas.append(Alerta(
                "DOBLE-NOMINA", "advertencia",
                f"Posible doble registro del salario: el diario ya trae {pesos(en_diario)} en gastos de personal (5105) "
                f"y la causación de nómina aceptada agrega {pesos(en_ajuste)}. Si son la misma nómina, rechace la "
                "causación antes de cerrar.",
                detalle="Se aceptó el ajuste «Causación de la nómina del periodo» con sueldos ya contabilizados."))

    # 7. Impuesto de renta (sobre la utilidad con los demás ajustes aceptados)
    if config.calcular_renta:
        lineas_tmp = [m for a in propuestos if a.aceptado for m in a.lineas]
        res_tmp = ef.resultados(construir_mayor(saldos, movs + lineas_tmp))
        a_renta = aj.ajuste_renta(res_tmp["utilidad_antes_impuestos"], empresa.tarifa_renta)
        if a_renta:
            a_renta.aceptado = decisiones.get(a_renta.id, True)
            propuestos.append(a_renta)

    lineas_ajuste = [m for a in propuestos if a.aceptado for m in a.lineas]
    for a in propuestos:
        if not a.cuadra:
            alertas.append(Alerta("PARTIDA-DOBLE", "error", f"El ajuste «{a.titulo}» no cuadra."))
    mayor_aj = construir_mayor(saldos, movs + lineas_ajuste)
    if lineas_ajuste:
        alertas += val.sumas_iguales(mayor_aj, "Balance ajustado")
    alertas_nat, _ = val.naturaleza(mayor_aj)
    alertas += alertas_nat

    # 8. Estados financieros
    rep_esf, tot = ef.situacion_financiera(mayor_aj, empresa, corte, tuple(config.pasivo_no_corriente))
    rep_er, res = ef.estado_resultados(mayor_aj, periodo)
    if tot["diferencia"]:
        alertas.append(Alerta("E1", "error", f"El estado de situación financiera no cuadra: Activo − (Pasivo + Patrimonio) = {pesos(tot['diferencia'])}. "
                                             f"El capital sale del mayor (cuenta 31), nunca como diferencia."))
    alertas += val.conciliacion_capital(mayor_aj, empresa, paquete.aportes_socios)
    alertas_disol = val.disolucion(tot["total_patrimonio"], empresa)
    alertas += alertas_disol
    rep_cp = ef.cambios_patrimonio(mayor_aj, res["utilidad_neta"], empresa, periodo)
    rep_fe = ef.flujo_efectivo(mayor_aj, empresa, periodo)
    rep_ind = ef.indicadores(tot, res)
    alertas = _dedup(alertas)
    societarias = [a.mensaje for a in alertas if a.codigo in ("DISOLUCION", "E5", "E18", "E17", "E3")]
    notas = ef.notas(empresa, tot, res, config.metodo_inventario, periodo, societarias)

    # 9. Cierre y balance definitivo
    lineas_cierre, utilidad_cierre = ci.asiento_cierre(mayor_aj)
    despues = ci.mayor_despues_cierre(mayor_aj, lineas_cierre)
    saldos_siguiente = [{"codigo": c.codigo, "nombre": c.nombre, "debito": c.fin_d, "credito": c.fin_c}
                        for c in despues.values() if c.neto != 0 and c.clase in ("1", "2", "3")]

    reportes = {
        "balance_prueba": reporte_balance_prueba(mayor_pre, "BALANCE DE PRUEBA (ANTES DE AJUSTES)", periodo),
        "hoja_trabajo": ci.hoja_trabajo(mayor_pre, mayor_aj, lineas_ajuste, periodo),
        "balance_ajustado": reporte_balance_prueba(mayor_aj, "BALANCE DE PRUEBA AJUSTADO", periodo, "balance_ajustado"),
        "asiento_cierre": ci.reporte_asiento(lineas_cierre, "ASIENTO DE CIERRE", corte, "asiento_cierre"),
        "balance_definitivo": ci.reporte_balance_definitivo(despues, corte),
        "situacion_financiera": rep_esf,
        "estado_resultados": rep_er,
        "cambios_patrimonio": rep_cp,
        "flujo_efectivo": rep_fe,
        "indicadores": rep_ind,
        "libro_mayor": reporte_libro_mayor(mayor_aj, periodo),
    }
    if productos:
        reportes.update(_reportes_inventario(productos, venc, fisico, corte))
    if liqs:
        r1, r2 = reporte_nomina(liqs, periodo)
        reportes["nomina_devengados"], reportes["nomina_apropiaciones"] = r1, r2
    if detalle_dep:
        reportes["depreciacion"] = _reporte_depreciacion(detalle_dep, periodo)

    conteo = defaultdict(int)
    for a in alertas:
        conteo[a.severidad] += 1
    resumen = {
        "periodo": periodo, "corte": corte, "total_activo": tot["total_activo"], "total_pasivo": tot["total_pasivo"],
        "total_patrimonio": tot["total_patrimonio"], "ingresos": res["ingresos_netos"], "utilidad_neta": res["utilidad_neta"],
        "costo_ventas": res.get("costo_ventas", CERO), "inventario_final": tot["inventarios"], "efectivo": tot["efectivo"],
        "bp_cuadra": reportes["balance_prueba"]["verificacion"]["cuadra"],
        "ajustado_cuadra": reportes["balance_ajustado"]["verificacion"]["cuadra"],
        "esf_cuadra": tot["diferencia"] == 0, "hoja_trabajo_cuadra": reportes["hoja_trabajo"]["verificacion"]["cuadra"],
        "alertas": dict(conteo), "ajustes_propuestos": len(propuestos), "ajustes_aceptados": sum(1 for a in propuestos if a.aceptado),
        "movimientos": len(movs), "cuentas": len(mayor_aj), "utilidad_cierre": utilidad_cierre,
        "causal_disolucion": bool(alertas_disol),
        # Desglose del resultado: lo consume el panel de indicadores y el histórico por cliente.
        "gastos_admin": res.get("gastos_admin", CERO),
        "gastos_ventas": res.get("gastos_ventas", CERO),
        "gastos_no_op": res.get("gastos_no_op", CERO),
        "ingresos_no_op": res.get("ingresos_no_op", CERO),
        "utilidad_bruta": res.get("utilidad_bruta", CERO),
        "utilidad_operacional": res.get("utilidad_operacional", CERO),
        "impuesto_renta": res.get("impuesto_renta", CERO),
        "total_gastos": (res.get("gastos_admin", CERO) + res.get("gastos_ventas", CERO)
                         + res.get("gastos_no_op", CERO)),
        "descuadre_esf": tot["diferencia"],
        "pasivo_corriente": tot.get("pasivo_corriente", CERO),
        "activo_corriente": tot.get("activo_corriente", CERO),
    }
    return {
        "empresa": empresa, "resumen": resumen, "alertas": alertas, "ajustes": [_ajuste_json(a) for a in propuestos],
        "reportes": reportes, "notas": notas, "cuentas_t": _cuentas_t(mayor_pre), "saldos_siguiente": saldos_siguiente,
        "inventario": {
            "productos": [{"codigo": p.codigo, "descripcion": p.descripcion, "laboratorio": p.laboratorio, "saldo_cant": p.saldo_cant,
                           "costo_promedio": p.costo_promedio, "saldo_total": p.saldo_total, "costo_ventas": p.costo_ventas,
                           "filas": [dataclasses.asdict(f) for f in p.filas]} for p in productos.values()],
            "vencimientos": venc, "fisico": fisico, "conciliacion": conciliacion_inv, "metodo": config.metodo_inventario,
            "costo_ventas": costo_kardex, "saldo_total": saldo_kardex,
        },
        "nomina": {"liquidaciones": [dataclasses.asdict(l) | {"total_prestaciones": l.total_prestaciones,
                                                              "total_aportes_empresa": l.total_aportes_empresa,
                                                              "costo_total": l.costo_total} for l in liqs],
                   "auditoria": aud_nomina or []},
        "auditoria_ef": aud_ef or [],
        "depreciacion": detalle_dep,
        "mayor_ajustado": mayor_aj,
    }


def _reportes_inventario(productos: dict, venc: list[dict], fisico: list[dict], corte: str) -> dict:
    cols = [col("codigo", "Código", ancho=12), col("descripcion", "Producto", ancho=36), col("laboratorio", "Laboratorio"),
            col("saldo_cant", "Cantidad", "numero"), col("costo_promedio", "Costo promedio", "dinero"),
            col("saldo_total", "Saldo valorizado", "dinero"), col("costo_ventas", "Costo de ventas", "dinero")]
    k = Constructor()
    idx = [k.agregar("linea", {"codigo": p.codigo, "descripcion": p.descripcion, "laboratorio": p.laboratorio, "saldo_cant": p.saldo_cant,
                               "costo_promedio": p.costo_promedio, "saldo_total": p.saldo_total, "costo_ventas": p.costo_ventas}, 1)
           for p in productos.values()]
    k.agregar("total", {"descripcion": "TOTAL INVENTARIO", "saldo_total": sum((p.saldo_total for p in productos.values()), CERO),
                        "costo_ventas": sum((p.costo_ventas for p in productos.values()), CERO)}, suma=idx)
    salida = {"inventario_saldos": reporte("inventario_saldos", "SALDOS DE INVENTARIO", corte, cols, k.filas)}
    if venc:
        cv = [col("codigo", "Código"), col("descripcion", "Producto", ancho=34), col("lote", "Lote"), col("vencimiento", "Vence"),
              col("dias", "Días", "numero"), col("cantidad", "Cantidad", "numero"), col("valor", "Valor", "dinero"), col("estado", "Estado", ancho=20)]
        k2 = Constructor()
        for v in venc:
            k2.agregar("linea", {**v, "vencimiento": v["vencimiento"].isoformat()}, 1)
        salida["inventario_vencimientos"] = reporte("inventario_vencimientos", "PRODUCTOS VENCIDOS Y POR VENCER", corte, cv, k2.filas)
    if fisico:
        cf = [col("codigo", "Código"), col("descripcion", "Producto", ancho=34), col("kardex", "Kardex", "numero"), col("fisico", "Físico", "numero"),
              col("diferencia", "Diferencia", "numero"), col("costo_promedio", "Costo promedio", "dinero"), col("valor", "Valor", "dinero"),
              col("estado", "Estado")]
        k3 = Constructor()
        idx3 = [k3.agregar("linea", f, 1) for f in fisico]
        k3.agregar("total", {"descripcion": "TOTAL DIFERENCIAS", "valor": sum((f["valor"] for f in fisico), CERO)}, suma=idx3)
        salida["inventario_fisico"] = reporte("inventario_fisico", "KARDEX VS. CONTEO FÍSICO", corte, cf, k3.filas)
    return salida


def _reporte_depreciacion(detalle: list[dict], periodo: str) -> dict:
    cols = [col("descripcion", "Activo", ancho=34), col("cuenta", "Cuenta"), col("costo", "Costo", "dinero"),
            col("vida_util_meses", "Vida útil (meses)", "numero"), col("mensual", "Depreciación mensual", "dinero"),
            col("meses_periodo", "Meses en el periodo", "numero"), col("depreciacion_periodo", "Depreciación del periodo", "dinero"),
            col("acumulada_previa", "Acumulada previa", "dinero")]
    k = Constructor()
    idx = [k.agregar("linea", d, 1) for d in detalle]
    k.agregar("total", {"descripcion": "TOTAL", "depreciacion_periodo": sum((d["depreciacion_periodo"] for d in detalle), CERO)}, suma=idx)
    return reporte("depreciacion", "DEPRECIACIÓN DE PROPIEDADES, PLANTA Y EQUIPO", periodo, cols, k.filas)


def decimal_o_cero(v) -> Decimal:
    return v if isinstance(v, Decimal) else CERO
