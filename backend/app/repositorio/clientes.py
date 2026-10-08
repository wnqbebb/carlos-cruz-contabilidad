"""Registro de clientes: alta, edición, búsqueda paginada e importación masiva.

Pensado para decenas de miles de fichas:
  · la búsqueda va contra la columna `buscable` (ya normalizada) con índice
    GIN/trigram en Postgres, así que no degrada con el volumen;
  · la lista siempre es paginada; nunca se trae la tabla completa a memoria;
  · la importación de Excel trabaja por lotes y resume el resultado.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any, Iterable

from sqlalchemy import Text, and_, delete, func, insert, or_, select, update

from ..config import ES_POSTGRES
from ..db import conexion, lectura
from ..esquema import clientes as T
from ..esquema import periodos as TP
from ..esquema import socios as TS
from ..modelos import Empresa
from ..utils import nit as unit
from ..utils.numeros import D, normalizar, parse_fecha

# Campos editables desde la interfaz, con su conversión.
TEXTOS = (
    "dv", "razon_social", "sigla", "tipo_persona", "regimen", "ciiu", "direccion",
    "municipio", "departamento", "telefono", "email", "rep_legal", "rep_legal_cc",
    "rep_legal_suplente", "contador", "contador_cc", "contador_tp", "periodicidad",
    "estado", "notas", "tipo_sociedad", "objeto_social", "documento_constitucion",
    "rep_legal_suplente_cc", "revisor_fiscal", "revisor_fiscal_tp", "matricula_mercantil",
    "ciiu_secundarios", "responsabilidades",
)
DINEROS = ("capital_suscrito", "valor_nominal_accion", "honorarios_mes", "capital_autorizado",
           "capital_pagado", "numero_acciones")
TASAS = ("tarifa_renta",)
ENTEROS = ("grupo_niif",)
BOOLEANOS = ("responsable_iva", "demo")
FECHAS = ("fecha_constitucion", "fecha_renovacion")
# Todo lo que se puede llenar desde los documentos del cliente.
CAMPOS_FICHA = set(TEXTOS + DINEROS + FECHAS) | {"nit", "responsable_iva"}

ORDENES = {
    "razon_social": T.c.razon_social,
    "nit": T.c.nit,
    "creado": T.c.creado,
    "actualizado": T.c.actualizado,
    "honorarios_mes": T.c.honorarios_mes,
    "municipio": T.c.municipio,
}


class ErrorCliente(ValueError):
    """Dato de cliente inválido; el mensaje se muestra tal cual al contador."""


# ── normalización de entrada ────────────────────────────────────────────────
def _texto_buscable(d: dict) -> str:
    partes = [d.get("nit", ""), d.get("razon_social", ""), d.get("sigla", ""),
              d.get("municipio", ""), d.get("rep_legal", ""), d.get("email", "")]
    return normalizar(" ".join(str(p or "") for p in partes))


def _bool(valor: Any, por_defecto: bool) -> bool:
    if valor is None or valor == "":
        return por_defecto
    if isinstance(valor, bool):
        return valor
    return str(valor).strip().upper() in ("SI", "SÍ", "TRUE", "1", "S", "X", "VERDADERO")


def normalizar_entrada(datos: dict, *, parcial: bool = False) -> dict:
    """Valida y convierte lo que llega de la interfaz o de un Excel."""
    fila: dict[str, Any] = {}

    if "nit" in datos or not parcial:
        base = unit.limpiar(datos.get("nit"))
        if not base:
            raise ErrorCliente("El NIT es obligatorio.")
        if not unit.valido(base):
            raise ErrorCliente(f"El NIT «{datos.get('nit')}» no es válido: debe tener entre 5 y 15 dígitos.")
        fila["nit"] = base
        dv_dado = str(datos.get("dv") or "").strip()
        dv_real = unit.digito_verificacion(base)
        if dv_dado and dv_dado != dv_real:
            raise ErrorCliente(
                f"El dígito de verificación del NIT {unit.formatear(base)} es {dv_real}, no {dv_dado}."
            )
        fila["dv"] = dv_real

    if "razon_social" in datos or not parcial:
        razon = str(datos.get("razon_social") or "").strip()
        if not razon:
            raise ErrorCliente("La razón social es obligatoria.")
        fila["razon_social"] = razon

    for campo in TEXTOS:
        if campo in ("dv", "razon_social"):
            continue
        if campo in datos:
            fila[campo] = str(datos[campo] or "").strip()
    for campo in DINEROS + TASAS:
        if campo in datos:
            fila[campo] = D(datos[campo])
    for campo in ENTEROS:
        if campo in datos:
            try:
                fila[campo] = int(datos[campo])
            except (TypeError, ValueError):
                raise ErrorCliente(f"«{campo}» debe ser un número entero.") from None
    for campo in BOOLEANOS:
        if campo in datos:
            fila[campo] = _bool(datos[campo], campo == "responsable_iva")
    for campo in FECHAS:
        if campo in datos:
            fila[campo] = parse_fecha(datos[campo])
    if "etiquetas" in datos:
        etiquetas = datos["etiquetas"]
        if isinstance(etiquetas, str):
            etiquetas = [e.strip() for e in etiquetas.split(",")]
        fila["etiquetas"] = [str(e).strip() for e in (etiquetas or []) if str(e).strip()]

    if fila.get("tipo_persona") and fila["tipo_persona"] not in ("juridica", "natural"):
        raise ErrorCliente("«tipo_persona» debe ser 'juridica' o 'natural'.")
    if fila.get("estado") and fila["estado"] not in ("activo", "inactivo", "archivado"):
        raise ErrorCliente("«estado» debe ser 'activo', 'inactivo' o 'archivado'.")
    if fila.get("grupo_niif") and fila["grupo_niif"] not in (1, 2, 3):
        raise ErrorCliente("El grupo NIIF debe ser 1, 2 o 3.")
    return fila


def _defectos() -> dict:
    return {
        "dv": "", "sigla": "", "tipo_persona": "juridica", "regimen": "responsable_iva",
        "grupo_niif": 3, "responsable_iva": True, "tarifa_renta": Decimal("0.35"),
        "ciiu": "", "direccion": "", "municipio": "", "departamento": "", "telefono": "",
        "email": "", "rep_legal": "", "rep_legal_cc": "", "rep_legal_suplente": "",
        "contador": "", "contador_cc": "", "contador_tp": "", "fecha_constitucion": None,
        "capital_suscrito": Decimal("0"), "valor_nominal_accion": Decimal("0"),
        "honorarios_mes": Decimal("0"), "periodicidad": "mensual", "estado": "activo",
        "etiquetas": [], "notas": "", "demo": False,
        "tipo_sociedad": "", "objeto_social": "", "documento_constitucion": "",
        "capital_autorizado": Decimal("0"), "capital_pagado": Decimal("0"), "numero_acciones": Decimal("0"),
        "rep_legal_suplente_cc": "", "revisor_fiscal": "", "revisor_fiscal_tp": "", "matricula_mercantil": "",
        "fecha_renovacion": None, "ciiu_secundarios": "", "responsabilidades": "",
    }


def _a_dict(fila) -> dict:
    d = dict(fila._mapping)
    d["id"] = str(d["id"])
    d["nit_formateado"] = unit.formatear(d.get("nit"), d.get("dv"))
    d["turno_dian"] = unit.turno_dian(d.get("nit"))
    for k, v in list(d.items()):
        if isinstance(v, Decimal):
            d[k] = format(v, "f")  # cadena exacta: el frontend no hace aritmética con esto
        elif isinstance(v, (date, datetime)):
            d[k] = v.isoformat()
    d.pop("buscable", None)
    if d.get("etiquetas") is None:
        d["etiquetas"] = []
    return d


# ── escritura ───────────────────────────────────────────────────────────────
def crear(datos: dict) -> dict:
    fila = {**_defectos(), **normalizar_entrada(datos)}
    fila["id"] = str(uuid.uuid4())
    fila["buscable"] = _texto_buscable(fila)
    with conexion() as cn:
        existe = cn.execute(select(T.c.id, T.c.razon_social).where(T.c.nit == fila["nit"])).first()
        if existe:
            raise ErrorCliente(
                f"Ya existe un cliente con NIT {unit.formatear(fila['nit'])}: «{existe.razon_social}»."
            )
        cn.execute(insert(T).values(**fila))
        creado = cn.execute(select(T).where(T.c.id == fila["id"])).one()
        return _a_dict(creado)


def actualizar(cliente_id: str, datos: dict) -> dict:
    cambios = normalizar_entrada(datos, parcial=True)
    if not cambios:
        return obtener(cliente_id)
    with conexion() as cn:
        actual = cn.execute(select(T).where(T.c.id == cliente_id)).first()
        if not actual:
            raise ErrorCliente("El cliente no existe o fue eliminado.")
        if "nit" in cambios and cambios["nit"] != actual.nit:
            choque = cn.execute(
                select(T.c.razon_social).where(and_(T.c.nit == cambios["nit"], T.c.id != cliente_id))
            ).first()
            if choque:
                raise ErrorCliente(f"Otro cliente ya usa ese NIT: «{choque.razon_social}».")
        mezcla = {**dict(actual._mapping), **cambios}
        cambios["buscable"] = _texto_buscable(mezcla)
        cambios["actualizado"] = datetime.now(timezone.utc)
        cn.execute(update(T).where(T.c.id == cliente_id).values(**cambios))
        return _a_dict(cn.execute(select(T).where(T.c.id == cliente_id)).one())


def eliminar(cliente_id: str) -> dict:
    """Borra el cliente y, en cascada, todos sus periodos y movimientos."""
    with conexion() as cn:
        fila = cn.execute(select(T.c.razon_social, T.c.nit).where(T.c.id == cliente_id)).first()
        if not fila:
            raise ErrorCliente("El cliente no existe o ya fue eliminado.")
        periodos_borrados = cn.execute(
            select(func.count()).select_from(TP).where(TP.c.cliente_id == cliente_id)
        ).scalar_one()
        cn.execute(delete(T).where(T.c.id == cliente_id))
        return {"ok": True, "razon_social": fila.razon_social, "periodos_borrados": int(periodos_borrados)}


def archivar(cliente_id: str, archivado: bool = True) -> dict:
    return actualizar(cliente_id, {"estado": "archivado" if archivado else "activo"})


# ── lectura ─────────────────────────────────────────────────────────────────
def obtener(cliente_id: str) -> dict:
    with lectura() as cn:
        fila = cn.execute(select(T).where(T.c.id == cliente_id)).first()
        if not fila:
            raise ErrorCliente("El cliente no existe.")
        datos = _a_dict(fila)
        datos["socios"] = [
            {k: (format(v, "f") if isinstance(v, Decimal) else v)
             for k, v in dict(s._mapping).items() if k != "cliente_id"}
            for s in cn.execute(select(TS).where(TS.c.cliente_id == cliente_id).order_by(TS.c.id))
        ]
        for s in datos["socios"]:
            s["id"] = int(s["id"])
            s.pop("creado", None)
        return datos


def por_nit(nit: str) -> dict | None:
    base = unit.limpiar(nit)
    if not base:
        return None
    with lectura() as cn:
        fila = cn.execute(select(T).where(T.c.nit == base)).first()
        return _a_dict(fila) if fila else None


def _condicion_busqueda(q: str):
    """Búsqueda tolerante: cada palabra debe aparecer en `buscable` o en el NIT."""
    palabras = [p for p in normalizar(q).split() if p]
    if not palabras:
        return None
    condiciones = []
    for p in palabras:
        condiciones.append(or_(T.c.buscable.like(f"%{p}%"), T.c.nit.like(f"{p}%")))
    return and_(*condiciones)


def listar(
    q: str = "",
    estado: str = "activo",
    etiqueta: str = "",
    orden: str = "razon_social",
    descendente: bool = False,
    pagina: int = 1,
    por_pagina: int = 50,
) -> dict:
    """Página de clientes + total. `estado=''` incluye archivados."""
    por_pagina = max(1, min(int(por_pagina or 50), 500))
    pagina = max(1, int(pagina or 1))

    filtros = []
    if estado:
        filtros.append(T.c.estado == estado)
    if etiqueta:
        if ES_POSTGRES:
            filtros.append(T.c.etiquetas.any(etiqueta))
        else:
            filtros.append(T.c.etiquetas.cast(Text).like(f'%"{etiqueta}"%'))
    cond = _condicion_busqueda(q)
    if cond is not None:
        filtros.append(cond)
    donde = and_(*filtros) if filtros else None

    # Orden por las cifras del último periodo: se hace en Python con Decimal,
    # porque en SQLite el dinero es texto y ordenarlo en SQL es alfabético.
    if orden in ORDENES_ULTIMO:
        return _listar_por_ultimo(donde, orden, descendente, pagina, por_pagina)

    columna = ORDENES.get(orden, T.c.razon_social)
    orden_sql = columna.desc() if descendente else columna.asc()

    with lectura() as cn:
        consulta_total = select(func.count()).select_from(T)
        consulta = select(T)
        if donde is not None:
            consulta_total = consulta_total.where(donde)
            consulta = consulta.where(donde)
        total = int(cn.execute(consulta_total).scalar_one())
        filas = cn.execute(
            consulta.order_by(orden_sql, T.c.id).limit(por_pagina).offset((pagina - 1) * por_pagina)
        ).all()
    clientes = [_a_dict(f) for f in filas]
    ultimos = ultimos_periodos([c["id"] for c in clientes])
    for c in clientes:
        c["ultimo_periodo"] = ultimos.get(c["id"])
    return {
        "total": total,
        "pagina": pagina,
        "por_pagina": por_pagina,
        "paginas": max(1, -(-total // por_pagina)),
        "clientes": clientes,
    }


ORDENES_ULTIMO = {"ingresos", "utilidad", "margen", "estado_periodo"}
_ESTADO_ORDEN = {"cerrado": 0, "calculado": 1, "borrador": 2}


def ultimos_periodos(ids: list[str]) -> dict[str, dict]:
    """Último periodo calculado de cada cliente: ingresos, utilidad, margen y estado."""
    if not ids:
        return {}
    with lectura() as cn:
        filas = cn.execute(
            select(TP.c.cliente_id, TP.c.id, TP.c.desde, TP.c.hasta, TP.c.estado, TP.c.total_ingresos,
                   TP.c.utilidad, TP.c.cuadra)
            .where(and_(TP.c.cliente_id.in_(ids), TP.c.estado != "borrador"))
        ).all()
    salida: dict[str, dict] = {}
    for f in filas:
        cid = str(f.cliente_id)
        previo = salida.get(cid)
        if previo and previo["hasta"] >= f.hasta.isoformat():
            continue
        ingresos = D(f.total_ingresos)
        utilidad = D(f.utilidad)
        margen = (utilidad / ingresos * 100).quantize(Decimal("0.1")) if ingresos else None
        salida[cid] = {"id": str(f.id), "desde": f.desde.isoformat(), "hasta": f.hasta.isoformat(),
                       "estado": f.estado, "ingresos": format(ingresos, "f"), "utilidad": format(utilidad, "f"),
                       "margen": format(margen, "f") if margen is not None else None, "cuadra": bool(f.cuadra)}
    return salida


def _listar_por_ultimo(donde, orden: str, descendente: bool, pagina: int, por_pagina: int) -> dict:
    with lectura() as cn:
        consulta = select(T.c.id, T.c.razon_social)
        if donde is not None:
            consulta = consulta.where(donde)
        ids = [(str(f.id), f.razon_social) for f in cn.execute(consulta).all()]
    ultimos = ultimos_periodos([i for i, _ in ids])

    def clave(par):
        u = ultimos.get(par[0])
        if not u:
            return (1, Decimal(0), par[1])          # sin periodos: siempre al final
        if orden == "estado_periodo":
            valor = Decimal(_ESTADO_ORDEN.get(u["estado"], 9))
        else:
            valor = D(u.get(orden)) if u.get(orden) is not None else Decimal("-1e30")
        return (0, -valor if descendente else valor, par[1])

    ordenados = sorted(ids, key=clave)
    total = len(ordenados)
    tramo = [i for i, _ in ordenados[(pagina - 1) * por_pagina: pagina * por_pagina]]
    with lectura() as cn:
        filas = {str(f.id): f for f in cn.execute(select(T).where(T.c.id.in_(tramo))).all()} if tramo else {}
    clientes = []
    for i in tramo:
        c = _a_dict(filas[i])
        c["ultimo_periodo"] = ultimos.get(i)
        clientes.append(c)
    return {"total": total, "pagina": pagina, "por_pagina": por_pagina,
            "paginas": max(1, -(-total // por_pagina)), "clientes": clientes}


def sugerencias_busqueda(q: str, limite: int = 8) -> list[dict]:
    """Resultados para el buscador rápido (Ctrl+K): pocos campos, respuesta inmediata."""
    cond = _condicion_busqueda(q)
    if cond is None:
        return []
    with lectura() as cn:
        filas = cn.execute(
            select(T.c.id, T.c.nit, T.c.dv, T.c.razon_social, T.c.sigla, T.c.municipio, T.c.estado)
            .where(cond)
            .order_by(T.c.razon_social)
            .limit(max(1, min(int(limite or 8), 25)))
        ).all()
    return [
        {
            "id": str(f.id),
            "nit": f.nit,
            "nit_formateado": unit.formatear(f.nit, f.dv),
            "razon_social": f.razon_social,
            "sigla": f.sigla or "",
            "municipio": f.municipio or "",
            "estado": f.estado,
        }
        for f in filas
    ]


def activos(limite: int = 5000) -> list[dict]:
    """Todos los clientes activos (para el tablero), en una consulta."""
    with lectura() as cn:
        filas = cn.execute(select(T).where(T.c.estado == "activo").order_by(T.c.razon_social)
                           .limit(max(1, int(limite or 5000)))).all()
    return [_a_dict(f) for f in filas]


def contar() -> dict:
    with lectura() as cn:
        filas = cn.execute(select(T.c.estado, func.count()).group_by(T.c.estado)).all()
    por_estado = {e: int(n) for e, n in filas}
    return {
        "total": sum(por_estado.values()),
        "activos": por_estado.get("activo", 0),
        "inactivos": por_estado.get("inactivo", 0),
        "archivados": por_estado.get("archivado", 0),
    }


# ── puente con el motor contable ────────────────────────────────────────────
def a_empresa(cliente: dict, desde: date | None = None, hasta: date | None = None) -> Empresa:
    """Convierte una ficha de cliente en el `Empresa` que consume el motor."""
    datos = {
        "razon_social": cliente.get("razon_social", ""),
        "sigla": cliente.get("sigla", ""),
        "nit": cliente.get("nit", ""),
        "direccion": cliente.get("direccion", ""),
        "municipio": cliente.get("municipio", ""),
        "constitucion": cliente.get("fecha_constitucion") or "",
        "ciiu": cliente.get("ciiu", ""),
        "rep_legal": cliente.get("rep_legal", ""),
        "rep_legal_cc": cliente.get("rep_legal_cc", ""),
        "rep_legal_suplente": cliente.get("rep_legal_suplente", ""),
        "contador": cliente.get("contador", ""),
        "contador_cc": cliente.get("contador_cc", ""),
        "contador_tp": cliente.get("contador_tp", ""),
        "grupo_niif": cliente.get("grupo_niif", 3),
        "responsable_iva": cliente.get("responsable_iva", True),
        "tarifa_renta": cliente.get("tarifa_renta", "0.35"),
        "capital_suscrito": cliente.get("capital_suscrito", "0"),
        "valor_nominal_accion": cliente.get("valor_nominal_accion", "0"),
        "accionistas": cliente.get("socios", []),
        "demo": cliente.get("demo", False),
    }
    if desde:
        datos["periodo_desde"] = desde
    if hasta:
        datos["periodo_hasta"] = hasta
    return Empresa.desde_dict(datos)


def guardar_socios(cliente_id: str, socios: Iterable[dict]) -> int:
    """Reemplaza la lista de socios del cliente. Devuelve cuántos quedaron."""
    filas = []
    for s in socios or []:
        nombre = str(s.get("nombre") or "").strip()
        if not nombre:
            continue
        filas.append({
            "cliente_id": cliente_id,
            "nombre": nombre,
            "cedula": str(s.get("cedula") or "").strip(),
            "cargo": str(s.get("cargo") or "").strip(),
            "acciones": D(s.get("acciones")),
            "participacion": D(s.get("participacion")),
            "comprometido": D(s.get("comprometido")),
            "pagado": D(s.get("pagado")),
        })
    with conexion() as cn:
        cn.execute(delete(TS).where(TS.c.cliente_id == cliente_id))
        if filas:
            cn.execute(insert(TS), filas)
    return len(filas)


def socios_de_varios(cliente_ids: list[str]) -> dict[str, list[dict]]:
    """Socios de VARIOS clientes en una sola consulta (para el tablero)."""
    if not cliente_ids:
        return {}
    salida: dict[str, list[dict]] = {cid: [] for cid in cliente_ids}
    with lectura() as cn:
        filas = cn.execute(
            select(TS.c.cliente_id, TS.c.nombre, TS.c.comprometido, TS.c.pagado)
            .where(TS.c.cliente_id.in_(cliente_ids))
        ).all()
    for f in filas:
        cid = str(f.cliente_id)
        if cid in salida:
            salida[cid].append({
                "nombre": f.nombre,
                "comprometido": format(f.comprometido, "f") if f.comprometido is not None else "0",
                "pagado": format(f.pagado, "f") if f.pagado is not None else "0",
            })
    return salida
