"""La declaración de un cliente, de punta a punta (spec v2.3 · 5.2).

Paso 1 «Suelte todo» → `subir`: lee cada archivo, separa lo de otros contribuyentes,
une las páginas, quita duplicados y valida las sumas contra los topes.
Paso 2 «Revise en una pantalla» → `vista`: veredicto, tres cifras, máximo 5 preguntas,
beneficios con su ahorro y el detalle plegado.
Paso 3 «Descargue» → `exportar.renta`.

Todo lo que el contador decide se guarda en `datos` y cada cambio deja una versión.
"""
from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

from ..repositorio import bitacora
from ..repositorio import clientes as repo_clientes
from ..repositorio import renta as repo
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
def subir(cliente_id: str, anio: int, archivos: list[tuple[str, bytes]]) -> dict:
    cliente = _cliente(cliente_id)
    decl = declaracion(cliente_id, anio)
    datos = dict(decl["datos"])
    leidos, errores = [], []
    for nombre, contenido in archivos:
        try:
            leidos.append(documentos.leer_archivo(nombre, contenido))
        except documentos.ocr.OcrNoDisponible as ex:
            errores.append(f"«{nombre}»: {ex}")
        except Exception as ex:  # un archivo dañado no detiene a los demás
            errores.append(f"«{nombre}» no se pudo leer: {ex}")
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
    return {
        "anio": anio,
        "obligacion": oblig,
        "cifras": {"neto": neto, "a_pagar": L.a_pagar, "a_favor": L.a_favor, "ahorro": comp["ahorro"],
                   "dian_neto": comp["dian"].neto},
        "vencimiento": venc,
        "sancion": sancion,
        "casillas": casillas,
        "diferencias": comp["diferencias"],
        "preguntas": [{"id": q.id, "texto": q.texto, "opciones": q.opciones, "defecto": q.defecto,
                       "respuesta": respuestas.get(q.id), "detalle": q.detalle, "lineas": q.lineas} for q in qs],
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
        out.append({
            "cliente_id": f["id"], "razon_social": f["razon_social"], "nit": f["nit"], "anio": anio,
            "estado": f["estado"], "obligado": None if oblig is None else oblig.get("obligado"),
            "veredicto": oblig.get("veredicto") if oblig else "Sin información",
            "motivos": [m["nombre"] for m in (oblig or {}).get("motivos", []) if m.get("supera")],
            "vencimiento": venc.get("fecha"), "dias": venc.get("dias"), "vencimiento_texto": venc.get("texto"),
            "neto": cifras.get("neto"), "ahorro": cifras.get("ahorro"),
        })
    return out


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
