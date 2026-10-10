"""La declaración de un cliente, de punta a punta (spec v2.3 · 5.2).

Paso 1 «Suelte todo» → `subir`: lee cada archivo, separa lo de otros contribuyentes,
une las páginas, quita duplicados y valida las sumas contra los topes.
Paso 2 «Revise en una pantalla» → `vista`: veredicto, tres cifras, máximo 5 preguntas,
beneficios con su ahorro y el detalle plegado.
Paso 3 «Descargue» → `exportar.renta`.

Todo lo que el contador decide se guarda en `datos` y cada cambio deja una versión.
"""
from __future__ import annotations

import secrets
import uuid
from datetime import date
from decimal import Decimal

from ..repositorio import bitacora
from ..repositorio import clientes as repo_clientes
from ..repositorio import renta as repo
from ..seguridad import aislado
from . import clasificacion as C
from . import documentos, obligacion
from . import parametros as P
from .calculo import CERO, comparar
from .lectura import Linea, Reporte, unir_paginas, validar_sumas

ANIO_ACTUAL = 2025   # año gravable que se declara en 2026


class RentaNoAplica(Exception):
    pass


def _cliente(cliente_id: str) -> dict:
    c = repo_clientes.obtener(cliente_id)
    if c.get("tipo_persona") == "juridica":
        raise RentaNoAplica("Las personas jurídicas declaran en el formulario 110, que todavía no se prepara aquí. "
                            "Está anotado en las propuestas para una próxima versión.")
    return c


def declaracion(cliente_id: str, anio: int) -> dict:
    _cliente(cliente_id)
    P.obtener(anio)
    return repo.obtener_o_crear(cliente_id, anio)


# ── paso 1 ─────────────────────────────────────────────────────────────
def subir(cliente_id: str, anio: int, archivos: list[tuple[str, bytes]], avisos_previos: list[str] | None = None) -> dict:
    cliente = _cliente(cliente_id)
    decl = declaracion(cliente_id, anio)
    datos = dict(decl["datos"])
    # La lectura (OCR incluido) corre en un proceso aparte con tiempo y memoria limitados (C24).
    leidos, errores = aislado.ejecutar("app.renta.documentos.leer_lote", archivos, tiempo=600)
    errores = list(avisos_previos or []) + errores
    esperado = "".join(ch for ch in str(cliente.get("nit") or "") if ch.isdigit())
    grupos = documentos.agrupar_por_contribuyente(leidos, esperado)
    avisos = list(errores)
    for doc, ls in grupos["otros"].items():
        nombres = ", ".join(l.reporte.documento for l in ls)
        avisos.append(f"{nombres}: {'es' if len(ls) == 1 else 'son'} de otro contribuyente (documento terminado en "
                      f"{doc[-3:]}); se separó y no se usó.")
    if grupos["principal"] and esperado and grupos["principal"] != esperado:
        avisos.append(f"Los documentos dicen el número {grupos['principal'][:-3]}***, distinto del NIT de la ficha. "
                      "Revise que sea el cliente correcto.")
    reportes = [l.reporte for l in grupos["leidos"]]
    previo = _reporte_guardado(datos)
    unido, quitadas = unir_paginas(([previo] if previo else []) + reportes)
    avisos += quitadas
    validacion = validar_sumas(unido)
    recortes = {}
    for l in grupos["leidos"]:
        recortes.update(l.recortes)
    # Los ids de recorte se vuelven opacos: no llevan el nombre del archivo.
    nuevos_ids = {}
    for linea in unido.lineas:
        if linea.recorte and linea.recorte in recortes:
            nuevo = uuid.uuid4().hex
            nuevos_ids[nuevo] = recortes[linea.recorte]
            linea.recorte = nuevo
    repo.guardar_recortes(decl["id"], nuevos_ids)
    credenciales = unido.credenciales_descartadas or any(r.anotaciones_a_mano for r in reportes)
    datos.update({
        "reporte": _reporte_a_dict(unido),
        "validacion": [{**v, "encabezado": str(v["encabezado"]), "suma": str(v["suma"])} for v in validacion],
        "avisos_lectura": avisos + unido.avisos,
        "anotaciones_a_mano": bool(credenciales),
        "documentos": sorted(set((datos.get("documentos") or []) + [l.reporte.documento for l in grupos["leidos"]])),
        "confianza_alta": round(unido.confianza_alta, 2),
    })
    tipos = {l.tipo for l in grupos["leidos"]}
    bitacora.registrar("renta_documentos", cliente_id, anio=anio, archivos=len(archivos),
                       lineas=len(unido.lineas), tipos=sorted(tipos))
    return recalcular(cliente_id, anio, datos, motivo="documentos", estado="borrador")


def _reporte_a_dict(r: Reporte) -> dict:
    return {
        "tipo_doc": r.tipo_doc, "numero_doc": r.numero_doc, "nombre": r.nombre,
        "topes": {str(k): v for k, v in r.topes.items()}, "responsable_iva": r.responsable_iva,
        "lineas": [l.a_dict() for l in r.lineas], "sugerencias_a_mano": r.sugerencias_a_mano,
        "credenciales_descartadas": r.credenciales_descartadas,
    }


def _reporte_guardado(datos: dict) -> Reporte | None:
    r = datos.get("reporte")
    if not r:
        return None
    return Reporte(tipo_doc=r.get("tipo_doc", ""), numero_doc=r.get("numero_doc", ""), nombre=r.get("nombre", ""),
                   topes={int(k): v for k, v in (r.get("topes") or {}).items()},
                   responsable_iva=bool(r.get("responsable_iva")),
                   lineas=[Linea.desde_dict(l) for l in r.get("lineas") or []],
                   sugerencias_a_mano=list(r.get("sugerencias_a_mano") or []),
                   credenciales_descartadas=int(r.get("credenciales_descartadas") or 0), pagina=0)


# ── decisiones del contador ────────────────────────────────────────────
def actualizar(cliente_id: str, anio: int, cambio: dict) -> dict:
    """Un cambio de la pantalla: respuesta, beneficio, reclasificación, valor, dato agregado, confirmación."""
    decl = declaracion(cliente_id, anio)
    datos = dict(decl["datos"])
    tipo = cambio.get("tipo")
    if tipo == "respuesta":
        datos.setdefault("respuestas", {})[cambio["id"]] = cambio["valor"]
        if cambio.get("extra") is not None:
            datos["respuestas"][f"{cambio['id']}_valor"] = cambio["extra"]
    elif tipo == "beneficio":
        b = datos.setdefault("beneficios", {})
        if cambio.get("valor") in (None, "", 0, "0", False):
            b.pop(cambio["id"], None)
        else:
            b[cambio["id"]] = cambio["valor"]
        if cambio["id"] == "compras_fe" and "uno_por_ciento" in cambio:
            b["uno_por_ciento"] = cambio["uno_por_ciento"]
    elif tipo == "reclasificar":
        if cambio["categoria"] not in C.CATEGORIAS:
            raise ValueError("Esa categoría no existe.")
        datos.setdefault("ajustes", {})[cambio["linea"]] = cambio["categoria"]
    elif tipo in ("valor", "excluir", "confirmar"):
        lineas = (datos.get("reporte") or {}).get("lineas") or []
        ids = set(cambio.get("lineas") or [cambio.get("linea")])
        for l in lineas:
            if l["id"] in ids:
                if tipo == "valor":
                    l["valor"] = str(Decimal(str(cambio["valor"])))
                    l["corregida"], l["encimada"], l["confianza"] = False, False, 1.0
                elif tipo == "excluir":
                    datos.setdefault("excluidas", [])
                    if l["id"] in datos["excluidas"]:
                        datos["excluidas"].remove(l["id"])
                    else:
                        datos["excluidas"].append(l["id"])
                else:
                    l["confirmada"] = True
    elif tipo == "agregar":
        datos.setdefault("manuales", []).append({
            "id": uuid.uuid4().hex[:8], "categoria": cambio["categoria"], "descripcion": cambio.get("descripcion", ""),
            "valor": str(Decimal(str(cambio["valor"])))})
    elif tipo == "quitar_agregado":
        datos["manuales"] = [m for m in datos.get("manuales", []) if m["id"] != cambio["id"]]
    elif tipo == "anios_declarando":
        datos["anios_declarando"] = int(cambio["valor"])
    else:
        raise ValueError("Cambio desconocido.")
    return recalcular(cliente_id, anio, datos, motivo=tipo or "cambio")


def recalcular(cliente_id: str, anio: int, datos: dict | None = None, motivo: str = "",
               estado: str | None = None) -> dict:
    cliente = _cliente(cliente_id)
    decl = declaracion(cliente_id, anio)
    datos = dict(datos if datos is not None else decl["datos"])
    resultado = calcular(cliente, anio, datos)
    nuevo_estado = estado or (decl["estado"] if decl["estado"] != "sin_informacion" else "borrador")
    if decl["estado"] == "revisada" and motivo not in ("", "revisada"):
        nuevo_estado = "borrador"  # cambió algo después de revisar
    if decl["estado"] == "presentada":
        nuevo_estado = "presentada"
    repo.guardar(decl["id"], datos=datos, resultado=resultado, estado=nuevo_estado, motivo=motivo)
    return vista(cliente_id, anio)


def calcular(cliente: dict, anio: int, datos: dict, hoy: date | None = None) -> dict:
    hoy = hoy or date.today()
    rep = _reporte_guardado(datos) or Reporte()
    excluidas = set(datos.get("excluidas") or [])
    clas = C.clasificar_todas(rep.lineas, datos.get("ajustes"))
    for c in clas:
        c.incluida = c.linea.id not in excluidas
    respuestas = dict(datos.get("respuestas") or {})
    qs = C.preguntas(clas, rep.sugerencias_a_mano)
    for q in qs:
        respuestas.setdefault(q.id, q.defecto)
        if q.id == "saldo_favor" and "saldo_favor_valor" not in respuestas:
            respuestas["saldo_favor_valor"] = q.detalle
    opt, dian, origen = C.construir(clas, respuestas, datos.get("beneficios") or {}, datos.get("manuales") or [],
                                    anio, int(datos.get("anios_declarando") or 3))
    comp = comparar(opt, dian)
    L = comp["optimizada"]
    topes = {"ingresos": rep.topes.get(1), "patrimonio": rep.topes.get(2), "consumos_tc": rep.topes.get(3),
             "consignaciones": rep.topes.get(4), "compras": rep.topes.get(5), "responsable_iva": rep.responsable_iva}
    if not any(topes.get(k) for k in ("ingresos", "patrimonio")):
        topes["ingresos"] = opt.trabajo_ingresos + opt.honorarios_ingresos + opt.nolab_ingresos + \
            opt.capital_rendimientos + opt.capital_otros + opt.pensiones_ingresos + opt.dividendos_1a
        topes["patrimonio"] = opt.patrimonio_bruto
    oblig = obligacion.evaluar(topes, anio) if rep.lineas or datos.get("manuales") else None
    nit = cliente.get("nit") or ""
    venc = obligacion.estado_vencimiento(nit, anio, hoy)
    sancion = None
    if venc.get("vencida") and venc.get("fecha"):
        ingresos_brutos = L[32] + L[43] + L[58] + L[74] + L[99] + L[112]
        sancion = obligacion.sancion_extemporaneidad(L[129], ingresos_brutos, L[137], venc["fecha"], hoy, anio)
    anterior_patrimonio = sum((c.linea.importe() for c in clas if c.categoria == "anterior_patrimonio"), CERO)
    marcas = C.marcas(clas, rep.topes, opt, anterior_patrimonio, anio)
    compras = sum((c.linea.importe() for c in clas if c.categoria == "compras_fe"), CERO)
    beneficios = C.beneficios_posibles(opt, compras)
    casillas = []
    nombres = P.nombres_casillas(anio)
    for n in sorted(L.casillas):
        if n not in nombres:
            continue
        casillas.append({"casilla": n, "nombre": nombres[n]["nombre"], "seccion": nombres[n]["seccion"],
                         "columna": nombres[n].get("columna", ""), "formula": nombres[n].get("formula", ""),
                         "dian": comp["dian"][n], "optimizada": L[n], "explicacion": L.explicacion.get(n, "")})
    neto = L.neto
    faltantes = [b["soporte"] for b in beneficios if b["id"] in (datos.get("beneficios") or {})]

    # ── Validación de confiabilidad (v2.4 Bloque 2.1) ──────────────────────
    motivos_bloqueo: list[str] = []
    TOLERANCIA_TOPES = Decimal(5000)

    # 1. Comprobar validación de topes
    for v in (datos.get("validacion") or []):
        if v.get("estado") == "no_cuadra":
            enc = Decimal(str(v.get("encabezado", 0)))
            sm = Decimal(str(v.get("suma", 0)))
            motivos_bloqueo.append(
                f"La suma de {v.get('nombre', 'filas').lower()} (${sm:,.0f}) no cuadra con el Tope {v.get('tope')} del reporte (${enc:,.0f}). Diferencia: ${abs(enc - sm):,.0f}."
            )

    # 2. Comprobar ingresos clasificados de la exógena vs Tope 1
    tope_1 = rep.topes.get(1)
    ingresos_exogena = sum(
        (c.linea.importe() for c in clas if c.incluida and (
            c.categoria.startswith("ingreso_") or c.categoria in ("pension", "dividendo")
        )), CERO
    )
    if tope_1 and Decimal(str(tope_1)) > 0:
        t1_val = Decimal(str(tope_1))
        if ingresos_exogena > t1_val + TOLERANCIA_TOPES:
            motivos_bloqueo.append(
                f"Los ingresos clasificados de la exógena (${ingresos_exogena:,.0f}) superan el Tope 1 de ingresos del reporte (${t1_val:,.0f}). Revise filas duplicadas o reclasifique."
            )

    # 3. Comprobar patrimonio de la exógena vs Tope 2
    tope_2 = rep.topes.get(2)
    patrimonio_exogena = sum(
        (c.linea.importe() for c in clas if c.incluida and c.categoria == "patrimonio"), CERO
    )
    if tope_2 and Decimal(str(tope_2)) > 0:
        t2_val = Decimal(str(tope_2))
        if abs(patrimonio_exogena - t2_val) > TOLERANCIA_TOPES:
            motivos_bloqueo.append(
                f"El patrimonio bruto de la exógena (${patrimonio_exogena:,.0f}) difiere del Tope 2 del reporte (${t2_val:,.0f})."
            )

    # 4. Líneas con baja confianza o dudosas que afectan casillas
    dudosas = [
        c for c in clas if c.incluida
        and C.CAMPO_POR_CATEGORIA.get(c.categoria) is not None
        and (c.linea.confianza < 0.6 or c.linea.encimada or (c.linea.tope is not None and not c.linea.validada))
        and not getattr(c.linea, "confirmada", False) and c.linea.importe() > Decimal(50000)
    ]
    if dudosas:
        motivos_bloqueo.append(
            f"Hay {len(dudosas)} fila(s) con lectura dudosa o baja confianza que afectan casillas y deben ser confirmadas."
        )

    # 5. Preguntas que cambian la cédula sin confirmar
    respuestas_guardadas = dict(datos.get("respuestas") or {})
    preguntas_pendientes = [
        q for q in qs if q.id not in respuestas_guardadas and q.id.startswith("pagador:")
    ]
    if preguntas_pendientes:
        motivos_bloqueo.append(
            f"Falta confirmar {len(preguntas_pendientes)} pregunta(s) sobre el origen de los ingresos."
        )

    total_lineas = len(rep.lineas)
    dudosas_total = sum(1 for l in rep.lineas if (l.confianza < 0.6 or l.encimada or (l.tope is not None and not l.validada)) and not getattr(l, "confirmada", False))
    porcentaje_por_verificar = round((dudosas_total / total_lineas), 2) if total_lineas > 0 else 0.0
    ofrecer_digitar_esencial = bool(porcentaje_por_verificar >= 0.30 or dudosas_total >= 5)

    incompleto = bool(motivos_bloqueo)

    if incompleto:
        cifras = {
            "bloqueado": True,
            "incompleto": True,
            "motivos": motivos_bloqueo,
            "neto": None,
            "a_pagar": None,
            "a_favor": None,
            "ahorro": None,
            "dian_neto": None,
        }
        sancion_final = None
    else:
        cifras = {
            "bloqueado": False,
            "incompleto": False,
            "motivos": [],
            "neto": neto,
            "a_pagar": L.a_pagar,
            "a_favor": L.a_favor,
            "ahorro": comp["ahorro"],
            "dian_neto": comp["dian"].neto,
        }
        sancion_final = sancion

    return {
        "anio": anio,
        "obligacion": oblig,
        "incompleto": incompleto,
        "motivos_incompleto": motivos_bloqueo,
        "cifras": cifras,
        "vencimiento": venc,
        "sancion": sancion_final,
        "casillas": casillas,
        "diferencias": comp["diferencias"],
        "preguntas": [{"id": q.id, "texto": q.texto, "opciones": q.opciones, "defecto": q.defecto,
                       "respuesta": respuestas.get(q.id), "confirmada": q.id in respuestas_guardadas,
                       "detalle": q.detalle, "lineas": q.lineas} for q in qs],
        "beneficios": [{**b, "valor": (datos.get("beneficios") or {}).get(b["id"])} for b in beneficios],
        "marcas": marcas,
        "lineas": [{**c.linea.a_dict(), "categoria": c.categoria, "categoria_texto": C.CATEGORIAS[c.categoria],
                    "motivo": c.motivo, "conflicto": c.conflicto, "incluida": c.incluida} for c in clas],
        "manuales": datos.get("manuales") or [],
        "origen": origen,
        "avisos": (datos.get("avisos_lectura") or []) + L.avisos,
        "validacion": datos.get("validacion") or [],
        "anotaciones_a_mano": bool(datos.get("anotaciones_a_mano")),
        "confianza_alta": datos.get("confianza_alta"),
        "documentos_faltantes": faltantes,
        "maximo_1pct": L.maximo_1pct,
        "ofrecer_digitar_esencial": ofrecer_digitar_esencial,
        "porcentaje_por_verificar": porcentaje_por_verificar,
    }


def vista(cliente_id: str, anio: int) -> dict:
    cliente = _cliente(cliente_id)
    decl = declaracion(cliente_id, anio)
    res = decl.get("resultado") or None
    if res is None:
        res = calcular(cliente, anio, decl["datos"]) if decl["datos"] else None
    return {
        "id": decl["id"], "cliente_id": cliente_id, "anio": anio, "estado": decl["estado"],
        "presentada": decl.get("presentada"), "resultado": res,
        "categorias": C.CATEGORIAS, "manuales_categorias": list(C.MANUALES),
        "actualizado": decl.get("actualizado"),
        "versiones": repo.versiones(decl["id"]),
        "contribuyente": {"nombre": cliente.get("razon_social"), "nit": cliente.get("nit")},
    }


def marcar(cliente_id: str, anio: int, estado: str, numero: str = "", fecha: str = "") -> dict:
    decl = declaracion(cliente_id, anio)
    if estado == "presentada":
        if not numero.strip() or not fecha:
            raise ValueError("Para marcarla como presentada escriba el número de formulario y la fecha.")
        presentada = {"numero": numero.strip(), "fecha": fecha, "resultado": decl.get("resultado")}
        repo.guardar(decl["id"], estado="presentada", presentada=presentada, motivo="presentada")
        bitacora.registrar("renta_presentada", cliente_id, anio=anio, formulario=numero.strip())
    elif estado in ("revisada", "borrador"):
        repo.guardar(decl["id"], estado=estado, presentada={} if decl["estado"] == "presentada" else None,
                     motivo=estado)
    else:
        raise ValueError("Estado no válido.")
    return vista(cliente_id, anio)


# ── cartera Renta⁰³ ─────────────────────────────────────────────────────
def cartera(anio: int, hoy: date | None = None) -> list[dict]:
    hoy = hoy or date.today()
    out = []
    for f in repo.cartera(anio):
        res = f.get("resultado") or {}
        oblig = res.get("obligacion") or None
        venc = obligacion.estado_vencimiento(f["nit"], anio, hoy)
        cifras = res.get("cifras") or {}
        incompleto = res.get("incompleto", False)
        out.append({
            "cliente_id": f["id"], "razon_social": f["razon_social"], "nit": f["nit"], "anio": anio,
            "estado": f["estado"] if f["estado"] in ("presentada", "revisada") else ("incompleto" if incompleto else f["estado"]),
            "incompleto": incompleto,
            "obligado": None if oblig is None else oblig.get("obligado"),
            "veredicto": "Borrador incompleto" if incompleto else (oblig.get("veredicto") if oblig else "Sin información"),
            "motivos": res.get("motivos_incompleto") if incompleto else [m["nombre"] for m in (oblig or {}).get("motivos", []) if m.get("supera")],
            "vencimiento": venc.get("fecha"), "dias": venc.get("dias"), "vencimiento_texto": venc.get("texto"),
            "neto": None if incompleto else cifras.get("neto"),
            "ahorro": None if incompleto else cifras.get("ahorro"),
        })
    return out


def digitar_esencial(cliente_id: str, anio: int, entrada: dict) -> dict:
    """Entrada rápida cuando la foto no sirve (spec v2.4 · 4.4):
    Guarda los 6 topes y las líneas esenciales digitadas por el contador con la foto al lado.
    """
    cliente = _cliente(cliente_id)
    decl = declaracion(cliente_id, anio)
    datos = dict(decl["datos"])

    topes_in = entrada.get("topes") or {}
    esenciales = entrada.get("esenciales") or []
    anterior_sf = entrada.get("anterior_saldo_favor")
    anterior_pat = entrada.get("anterior_patrimonio")

    rep = _reporte_guardado(datos) or Reporte(tipo_doc=cliente.get("tipo_doc") or "CC",
                                              numero_doc=cliente.get("nit") or "",
                                              nombre=cliente.get("razon_social") or "")
    for k, v in topes_in.items():
        if str(k) in ("1", "2", "3", "4", "5") and v is not None:
            rep.topes[int(k)] = str(Decimal(str(v)))
        elif str(k) == "6":
            rep.responsable_iva = bool(v)

    ajustes = dict(datos.get("ajustes") or {})
    lineas_nuevas: list[Linea] = []
    for i, it in enumerate(esenciales):
        lid = f"esencial_{i+1}"
        if it.get("categoria"):
            ajustes[lid] = it["categoria"]
        val = str(Decimal(str(it.get("valor", 0))))
        det = it.get("detalle", f"Línea esencial #{i+1}")
        renglon = it.get("renglon")
        tope_num = it.get("tope")
        lineas_nuevas.append(Linea(
            id=lid,
            entidad=it.get("entidad", "Digitado por el contador"),
            titular="TITULAR PRINCIPAL",
            detalle=det,
            valor=val,
            uso=it.get("uso", ""),
            renglon=renglon,
            tope=tope_num,
            confianza=1.0,
            validada=True,
            confirmada=True,
            encimada=False,
            origen="contador_esencial"
        ))

    if anterior_sf:
        lineas_nuevas.append(Linea(
            id="esencial_anterior_sf",
            entidad="DIAN",
            titular="TITULAR PRINCIPAL",
            detalle="Total saldo a favor",
            valor=str(Decimal(str(anterior_sf))),
            renglon=131,
            confianza=1.0,
            validada=True,
            confirmada=True,
            origen="contador_esencial"
        ))

    if anterior_pat:
        lineas_nuevas.append(Linea(
            id="esencial_anterior_pat",
            entidad="DIAN",
            titular="TITULAR PRINCIPAL",
            detalle="Total patrimonio bruto declarado",
            valor=str(Decimal(str(anterior_pat))),
            confianza=1.0,
            validada=True,
            confirmada=True,
            origen="contador_esencial"
        ))

    rep.lineas = lineas_nuevas
    val_sumas = validar_sumas(rep)

    datos["reporte"] = _reporte_a_dict(rep)
    datos["validacion"] = [{**v, "encabezado": str(v["encabezado"]), "suma": str(v["suma"])} for v in val_sumas]
    datos["digitado_esencial"] = True
    datos["ajustes"] = ajustes

    if entrada.get("respuestas"):
        datos.setdefault("respuestas", {}).update(entrada["respuestas"])

    return recalcular(cliente_id, anio, datos, motivo="digitar_esencial", estado="borrador")


def documento_provisional() -> str:
    """Número provisional cuando el reporte no deja leer la cédula.

    Antes era «CC» + 8 letras y números al azar: si salían menos de 5 dígitos el NIT no era
    válido y la creación fallaba de vez en cuando. Ahora son 12 dígitos que empiezan por «0000»
    (ninguna cédula ni NIT real empieza así) y el cliente queda marcado «documento_pendiente».
    """
    return "0000" + "".join(secrets.choice("0123456789") for _ in range(8))


def subir_universal(anio: int, archivos: list[tuple[str, bytes]], avisos_previos: list[str] | None = None) -> dict:
    """Sube la exógena de cualquier persona: crea el contribuyente si no existe y abre su renta."""
    P.obtener(anio)
    leidos, errores = aislado.ejecutar("app.renta.documentos.leer_lote", archivos, tiempo=600)
    avisos = list(avisos_previos or []) + errores
    if not leidos:
        raise ValueError("No se pudo extraer ningún dato de los archivos subidos. Verifique que sean legibles.")

    # Detectar el contribuyente principal
    rep_principal = next((l.reporte for l in leidos if l.reporte.numero_doc), leidos[0].reporte)
    nit = "".join(ch for ch in str(rep_principal.numero_doc or "") if ch.isdigit())
    nombre = (rep_principal.nombre or "").strip() or "CONTRIBUYENTE NUEVO"

    cliente = repo_clientes.por_nit(nit) if nit else None
    creado = False
    if not cliente:
        cliente_id = str(uuid.uuid4())
        nuevo_cliente = {
            "id": cliente_id,
            "nit": nit or documento_provisional(),
            "razon_social": nombre,
            "tipo_persona": "natural",
            "estado": "activo",
            "etiquetas": ["renta", "solo_renta"] + ([] if nit else ["documento_pendiente"]),
            "regimen": "ordinario",
            "responsable_iva": bool(rep_principal.responsable_iva),
        }
        cliente = repo_clientes.crear(nuevo_cliente)
        creado = True

    cliente_id = cliente["id"]
    if cliente.get("tipo_persona") == "juridica":
        raise RentaNoAplica("El documento corresponde a una persona jurídica, que declara en el formulario 110.")

    subir(cliente_id, anio, archivos, avisos)
    return {
        "cliente_id": cliente_id,
        "creado": creado,
        "razon_social": cliente["razon_social"],
        "nit": cliente["nit"],
        "anio": anio,
    }


def tareas(hoy: date | None = None) -> list[dict]:
    """Una tarea por declaración que vence en 15 días o menos (o ya venció) sin presentarse."""
    hoy = hoy or date.today()
    out = []
    try:
        filas = cartera(ANIO_ACTUAL, hoy)
    except Exception:
        return []
    for f in filas:
        if f["estado"] == "presentada" or f["obligado"] is False or f["dias"] is None or f["dias"] > 15:
            continue
        vencida = f["dias"] < 0
        out.append({
            "clave": f"RENTA:{f['cliente_id']}:{ANIO_ACTUAL}", "codigo": "RENTA_VENCE",
            "prioridad": "critica" if vencida or f["dias"] <= 3 else "alta",
            "cliente_id": f["cliente_id"], "razon_social": f["razon_social"], "nit": f["nit"],
            "que": "Declaración de renta vencida" if vencida else "Declaración de renta por vencer",
            "titulo": f["vencimiento_texto"],
            "por_que": ("Sin presentar. Cada mes de retardo suma sanción (art. 641 E.T.)." if vencida else
                        "Prepare el borrador con las fotos del reporte de exógena."),
            "accion": {"tipo": "ir", "etiqueta": "Abrir la renta",
                       "ruta": f"/clientes/{f['cliente_id']}?seccion=renta"},
        })
    return out
