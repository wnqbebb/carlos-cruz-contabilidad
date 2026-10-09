"""El tablero del contador: qué hay que hacer hoy en toda la cartera (spec v2.2 · Fase 7, H13).

POR QUÉ EXISTE
El tablero anterior mostraba el resultado del mes de la cartera y la ecuación
contable de un cliente: cifras bonitas que no le dicen al contador qué hacer.
Este responde a cuatro preguntas, todas con datos guardados:

  · ¿Cuántos clientes tengo y cuánto me pagan al mes?
  · ¿Cuántos están al día y cuántos atrasados?
  · ¿Qué tengo que hacer, en qué orden y por qué? (tareas sugeridas)
  · ¿Cómo va cada mes de la cartera? (cerrados, abiertos, sin contabilizar)

Todo se calcula aquí, en el servidor, para que la pantalla no tenga que
deducir nada (H13). Se carga en pocas consultas masivas, no una por cliente:
contra Supabase cada viaje cuesta ~190 ms.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from ..repositorio import bitacora
from ..repositorio import clientes as repo_clientes
from ..repositorio import periodos as repo_periodos
from . import sugerencias as sug
from ..nomina import parametros as parametros_legales

CERO = Decimal("0")
MESES_SERIE = 12

# Qué sugerencias se vuelven tarea, con qué prioridad y qué acción directa llevan.
# Las demás (variaciones, turno DIAN…) son información de la ficha, no trabajo de hoy.
TAREAS = {
    "DESCUADRE": ("critica", "Revisar el descuadre", "estados"),
    "CAUSAL_DISOLUCION": ("critica", "Revisar la causal de disolución", "resumen"),
    "ATRASADO": ("alta", "Contabilizar los meses atrasados", "subir"),
    "SIN_PERIODOS": ("alta", "Contabilizar el primer periodo", "subir"),
    "SIN_CERRAR": ("alta", "Cerrar el periodo calculado", "periodos"),
    "PERIODO_EN_CERO": ("alta", "Revisar un periodo en cero", "periodos"),
    "PREGUNTAS_PENDIENTES": ("alta", "Responder las preguntas del archivo", "preguntas"),
    "HUECOS": ("media", "Llenar los meses que faltan", "subir"),
    "FICHA_PARA_FIRMAR": ("media", "Completar la ficha para poder firmar", "editar"),
}
ORDEN = {"critica": 0, "alta": 1, "media": 2}


def _mes(d: date) -> str:
    return f"{d.year}-{d.month:02d}"


def _meses_atras(hoy: date, n: int) -> list[str]:
    a, m = hoy.year, hoy.month
    salida = []
    for _ in range(n):
        salida.append(f"{a}-{m:02d}")
        m -= 1
        if m == 0:
            a, m = a - 1, 12
    return list(reversed(salida))


def _cubre(p: dict, mes: str) -> bool:
    return p["desde"][:7] <= mes <= p["hasta"][:7]


def _en_cero(p: dict) -> bool:
    if p["estado"] == "borrador":
        return False
    valores = [p.get(k) for k in ("total_activo", "total_pasivo", "total_ingresos", "total_gastos")]
    return int(p.get("cuentas") or 0) == 0 or all(not v or Decimal(str(v)) == 0 for v in valores)


def _accion(tipo: str, cliente_id: str, dato: dict) -> dict:
    """La acción directa de cada tarea: a dónde lleva el botón «Hacer ahora»."""
    base = f"/clientes/{cliente_id}"
    if tipo == "subir":
        return {"tipo": "subir", "etiqueta": "Subir el archivo", "ruta": f"{base}?seccion=contabilidad"}
    if tipo == "preguntas":
        return {"tipo": "ir", "etiqueta": "Responder ahora",
                "ruta": f"{base}?seccion=contabilidad&sesion={dato.get('sesion', '')}"}
    if tipo == "editar":
        return {"tipo": "ir", "etiqueta": "Completar la ficha", "ruta": f"{base}/editar"}
    if tipo == "estados":
        return {"tipo": "ir", "etiqueta": "Ver el periodo", "ruta": f"{base}?seccion=contabilidad"}
    if tipo == "periodos":
        return {"tipo": "ir", "etiqueta": "Ir a los periodos", "ruta": f"{base}?seccion=archivos"}
    return {"tipo": "ir", "etiqueta": "Ver el detalle", "ruta": f"{base}?seccion=resumen"}


def _pospuestas(hoy: date) -> set[str]:
    """Tareas que el contador pospuso hasta una fecha que todavía no llega."""
    vigentes = set()
    for linea in bitacora.listar_acciones(("tarea_pospuesta",), 500):
        hasta = str((linea.get("detalle") or {}).get("hasta") or "")
        if hasta and hasta > hoy.isoformat():
            vigentes.add(str(linea["detalle"].get("clave")))
    return vigentes


def _preguntas_pendientes() -> dict[str, dict]:
    """Subidas con preguntas sin responder: el archivo se leyó pero no se calculó después."""
    lineas = bitacora.listar_acciones(("archivos_subidos", "periodo_calculado"), 400)
    pendientes: dict[str, dict] = {}
    calculados: set[str] = set()
    for linea in lineas:                     # de la más reciente a la más vieja
        cid = linea.get("cliente_id")
        if not cid:
            continue
        if linea["accion"] == "periodo_calculado":
            calculados.add(cid)
            continue
        n = int((linea.get("detalle") or {}).get("preguntas") or 0)
        if n and cid not in calculados and cid not in pendientes:
            pendientes[cid] = {"preguntas": n, "sesion": linea["detalle"].get("sesion", ""),
                               "archivos": linea["detalle"].get("archivos", []), "creado": linea["creado"]}
    return pendientes


def armar(hoy: date | None = None) -> dict:
    hoy = hoy or date.today()
    fichas = repo_clientes.activos(limite=5000)
    ids = [c["id"] for c in fichas]
    historias = repo_periodos.series_de_varios(ids)
    cierres = repo_periodos.cierres_de_varios(ids)
    socios = repo_clientes.socios_de_varios(ids)
    pospuestas = _pospuestas(hoy)
    preguntas = _preguntas_pendientes()

    tareas: list[dict] = []
    al_dia = atrasados = 0
    honorarios = CERO
    estado_cliente: dict[str, str] = {}
    for c in fichas:
        honorarios += Decimal(str(c.get("honorarios_mes") or 0))
        historia = historias.get(c["id"], [])
        informe = sug._informe_en_memoria({**c, "socios": socios.get(c["id"], [])}, historia,
                                           cierres.get(c["id"], 0), hoy)
        codigos = {s["codigo"] for s in informe["sugerencias"]}
        atrasado = bool(codigos & {"ATRASADO", "SIN_PERIODOS"})
        atrasados += atrasado
        al_dia += not atrasado
        estado_cliente[c["id"]] = "atrasado" if atrasado else "al_dia"

        candidatas = [s for s in informe["sugerencias"] if s["codigo"] in TAREAS]
        en_cero = [p for p in historia if _en_cero(p)]
        if en_cero:
            ultimo = en_cero[-1]
            candidatas.append(sug._sug("PERIODO_EN_CERO", "alta", f"El periodo al {ultimo['hasta']} quedó en cero",
                                       "Tiene cero cuentas o todas sus cifras en cero: puede ser un archivo que no aportó nada.",
                                       "Revíselo y recalcúlelo con el archivo correcto, o restaure una versión anterior.",
                                       periodo_id=ultimo["id"]))
        if c["id"] in preguntas:
            q = preguntas[c["id"]]
            candidatas.append(sug._sug("PREGUNTAS_PENDIENTES", "alta",
                                       f"{q['preguntas']} pregunta(s) sin responder sobre {', '.join(q['archivos'][:2])}",
                                       "El archivo se leyó, pero no se ha calculado con las respuestas.",
                                       "Responda las preguntas y calcule.", sesion=q["sesion"]))
        # La ficha incompleta solo es tarea si ya hay algo que firmar.
        if "FICHA_INCOMPLETA" in codigos and any(p["estado"] != "borrador" for p in historia):
            base = next(s for s in informe["sugerencias"] if s["codigo"] == "FICHA_INCOMPLETA")
            candidatas.append({**base, "codigo": "FICHA_PARA_FIRMAR"})

        for s in candidatas:
            prioridad, que, tipo = TAREAS[s["codigo"]]
            if s["severidad"] == "critica":
                prioridad = "critica"
            clave = f"{s['codigo']}:{c['id']}"
            if clave in pospuestas:
                continue
            tareas.append({
                "clave": clave, "codigo": s["codigo"], "prioridad": prioridad,
                "cliente_id": c["id"], "razon_social": c["razon_social"], "nit": c["nit"],
                "que": que, "titulo": s["titulo"], "por_que": s["detalle"],
                "accion": _accion(tipo, c["id"], s.get("dato") or {}),
            })
    # v2.3 · Fase 2: los valores legales viven en la aplicación. Si falta el año en
    # curso, no se inventan: se avisa aquí y la nómina de ese año queda bloqueada.
    if not parametros_legales.hay(hoy.year) and f"VALORES_LEGALES:{hoy.year}" not in pospuestas:
        tareas.append({
            "clave": f"VALORES_LEGALES:{hoy.year}", "codigo": "VALORES_LEGALES", "prioridad": "critica",
            "cliente_id": None, "razon_social": "Toda la cartera", "nit": "",
            "que": f"Faltan los valores legales de {hoy.year}",
            "titulo": f"La aplicación no tiene el salario mínimo ni el auxilio de transporte de {hoy.year}",
            "por_que": f"La nómina de {hoy.year} no se calcula hasta que se actualice la aplicación con los valores "
                       "oficiales. No se inventa ninguno.",
            "accion": {"tipo": "informar"},
        })
    # v2.3 · Fase 5: declaraciones de renta que vencen en 15 días o menos, o ya vencieron.
    from ..renta import servicio as renta
    tareas += [t for t in renta.tareas(hoy) if t["clave"] not in pospuestas]
    tareas.sort(key=lambda t: (ORDEN[t["prioridad"]], t["razon_social"], t["codigo"]))

    # H13 · cómo va cada mes de la cartera, contado en el servidor.
    meses = []
    for mes in _meses_atras(hoy, MESES_SERIE):
        cerrados = abiertos = sin = 0
        for c in fichas:
            historia = historias.get(c["id"], [])
            cubre = [p for p in historia if p["estado"] != "borrador" and _cubre(p, mes)]
            if any(p["estado"] == "cerrado" for p in cubre):
                cerrados += 1
            elif cubre:
                abiertos += 1
            elif mes < _mes(hoy):
                # Solo es atraso desde que se lleva al cliente: desde su primer
                # periodo o, si no tiene ninguno, desde que se creó su ficha.
                desde = min([p["desde"][:7] for p in historia] + [(c.get("creado") or "")[:7]])
                if desde and mes >= desde:
                    sin += 1
        meses.append({"mes": mes, "cerrados": cerrados, "abiertos": abiertos, "sin_contabilizar": sin})

    recientes = sorted(fichas, key=lambda c: c.get("actualizado") or "", reverse=True)[:8]
    nombres = {c["id"]: c["razon_social"] for c in fichas}
    actividad = []
    for linea in bitacora.listar(None, 8):
        cid = linea.get("cliente_id")
        detalle = linea.get("detalle") or {}
        quien = nombres.get(cid) or detalle.get("razon_social", "")
        if not quien and detalle.get("archivos"):
            quien = ", ".join(detalle["archivos"][:2])       # una subida antes de saber de quién es
        actividad.append({**linea, "razon_social": quien})

    return {
        "generado": datetime.now(timezone.utc).isoformat(),
        "hoy": hoy.isoformat(),
        "indicadores": {
            "clientes_activos": len(fichas),
            "honorarios_mensuales": format(honorarios, "f"),
            "al_dia": al_dia,
            "atrasados": atrasados,
        },
        "tareas": tareas[:80],
        "tareas_total": len(tareas),
        "meses": meses,
        "recientes": [{**c, "estado_trabajo": estado_cliente.get(c["id"], "al_dia"),
                       "ultimo_periodo": (historias.get(c["id"]) or [None])[-1]} for c in recientes],
        "actividad": actividad,
        "clientes": repo_clientes.contar(),
        "trabajo": repo_periodos.resumen_global(),
    }


def manana(hoy: date | None = None) -> str:
    return ((hoy or date.today()) + timedelta(days=1)).isoformat()
