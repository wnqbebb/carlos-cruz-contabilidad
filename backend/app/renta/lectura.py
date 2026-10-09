"""Del documento al reporte: encabezado, topes y líneas de la información exógena.

Entradas posibles: filas leídas de una foto (OCR), texto o tablas de un PDF del
portal de la DIAN, o filas de un Excel. Todas terminan en `Reporte`.

Los importes leídos por OCR pueden traer errores típicos (el «$» leído como «5» o
«S», comas perdidas). Cada valor dudoso guarda sus **alternativas**; la validación
contra los topes del encabezado elige la que cuadra (`validar_sumas`).
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import asdict, dataclass, field
from decimal import Decimal
from itertools import combinations

CERO = Decimal("0")

TOPE_ENCABEZADO = re.compile(r"\bTope\s*([1-6])\s*[-–:.]?\s*([A-Za-zÁÉÍÓÚáéíóú ]+)?", re.I)
RENGLON = re.compile(r"(?<![A-Za-z0-9])[A-Za-z]?[Rr]\s?(\d{2,3})\b")
# El uso sugerido trae un texto fijo junto al renglón: sirve cuando el OCR pierde la «R».
RENGLON_POR_TEXTO = {"DEUDAS": 30, "RETENCIONES": 132, "PATRIMONIO": 29}
TOPE_USO = re.compile(r"\bTope\s*([1-6])\b", re.I)
DOCUMENTO = re.compile(r"\b(\d[\d.]{5,13}\d)\b")
IMPORTE_AL_FINAL = re.compile(r"(\$\s*[\d.,\s]*\d[.,]\d{2,3}|\d{1,3}(?:[.,]\d{3}){1,4}(?:[.,]\d{2})?)(?=\s*(?:$|Tope|R\d|[A-Za-z]))")


def sin_tildes(texto: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", texto or "") if unicodedata.category(c) != "Mn").upper()


@dataclass
class Linea:
    id: str
    entidad: str
    titular: str
    detalle: str
    valor: str                       # Decimal como texto
    uso: str = ""
    renglon: int | None = None       # «R29» → 29 (casilla del 210 que sugiere la DIAN)
    tope: int | None = None          # «Tope 4» → 4
    no_titular: bool = False         # «NO REGISTRA NO»: el contribuyente no es el titular principal
    confianza: float = 1.0
    resaltada: bool = False          # marcada en el papel por el contador
    encimada: bool = False           # texto superpuesto: confirmar
    alternativas: list[str] = field(default_factory=list)
    corregida: bool = False          # el valor se ajustó para cuadrar con el tope
    validada: bool = False           # su grupo cuadra con el tope del encabezado
    confirmada: bool = False         # el contador la vio y la confirmó
    documento: str = ""              # de qué archivo salió
    pagina: int = 1
    fila: int = 0
    recorte: str = ""                # id del recorte de imagen (verificación)
    origen: str = "exogena"          # exogena | contador

    def importe(self) -> Decimal:
        return Decimal(self.valor or "0")

    def a_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def desde_dict(cls, d: dict) -> "Linea":
        campos = {k: v for k, v in d.items() if k in cls.__dataclass_fields__}
        return cls(**campos)


@dataclass
class Reporte:
    documento: str = ""              # nombre del archivo
    tipo_doc: str = ""
    numero_doc: str = ""
    nombre: str = ""
    topes: dict[int, str] = field(default_factory=dict)
    topes_alternativas: dict[int, list[str]] = field(default_factory=dict)
    responsable_iva: bool = False
    lineas: list[Linea] = field(default_factory=list)
    pagina: int | None = None        # si el documento dice su número de página
    anotaciones_a_mano: bool = False
    credenciales_descartadas: int = 0
    sugerencias_a_mano: list[str] = field(default_factory=list)
    avisos: list[str] = field(default_factory=list)
    confianza_alta: float = 1.0      # fracción de filas leídas con confianza alta


# ── importes ─────────────────────────────────────────────────────────────
NUMERO = re.compile(r"\d[\d.,]*\d|\d")


def leer_importe(texto: str) -> tuple[Decimal | None, list[Decimal]]:
    """«$ 1,234,567.00» → 1234567. Devuelve (valor, alternativas plausibles).

    El OCR suele leer el «$» como «5» («$57,763,109» por «$ 7,763,109», o «54,932,351»
    sin «$»): en esos casos se ofrece el valor sin ese primer 5 como alternativa.
    """
    if not texto:
        return None, []
    t = re.sub(r"(?<=\d)[Oo]|[Oo](?=\d)", "0", texto)
    tokens = list(NUMERO.finditer(t))
    principal = next((m for m in tokens if len(re.sub(r"\D", "", m.group())) >= 4), None) or (tokens[0] if tokens else None)
    if not principal:
        return None, []
    num = re.sub(r"(?<=\d{3})[.,]\d{1,2}$", "", principal.group())
    digitos = re.sub(r"\D", "", num)
    if not digitos:
        return None, []
    valor = Decimal(digitos)
    antes = t[: principal.start()]
    pegado = re.search(r"\$\s*$", antes) is not None
    alternativas = []
    if len(digitos) > 1 and digitos[0] in "51" and ("$" not in antes or pegado):
        alternativas.append(Decimal(digitos[1:]))
    return valor, [a for a in alternativas if a != valor]


# ── filas → líneas ───────────────────────────────────────────────────────
ETIQUETAS_CABECERA = ("TIPO DE DOCUMENTO", "IDENTIFICACION", "NOMBRES", "RAZON SOCIAL", "DOCUMENTO")


def _es_titular_ausente(texto: str) -> bool:
    return "NO REGISTRA" in sin_tildes(texto)


def interpretar_filas(filas: list[list[str]], confianzas: list | None = None,
                      resaltadas: list[bool] | None = None, documento: str = "", pagina: int = 1,
                      recortes: list[str] | None = None) -> Reporte:
    """Filas de celdas (texto) → `Reporte`. Sirve para OCR, PDF y Excel."""
    rep = Reporte(documento=documento)
    confianzas = confianzas or [1.0] * len(filas)
    resaltadas = resaltadas or [False] * len(filas)
    recortes = recortes or [""] * len(filas)
    altas = 0
    contadas = 0
    for i, celdas in enumerate(filas):
        celdas = [str(c or "").strip() for c in celdas]
        texto = " ".join(c for c in celdas if c)
        if not texto:
            continue
        T = sin_tildes(texto)
        # Columna del valor: la primera celda con forma de importe que no sea el detalle.
        idx_valor = None
        for j, c in enumerate(celdas):
            if c and re.search(r"\d", c) and re.search(r"\$|\d[.,]\d{3}", c) and not TOPE_ENCABEZADO.search(c) \
                    and not RENGLON.search(c) and len(re.sub(r"[\d$.,\s]", "", c)) <= 3:
                idx_valor = j
                break
        if idx_valor is None:
            # Sin celda propia para el valor: se separa el importe del final de una celda de texto.
            for j in range(len(celdas) - 1, -1, -1):
                m = IMPORTE_AL_FINAL.search(celdas[j])
                if m and len(re.sub(r"\D", "", m.group(1))) >= 4:
                    celdas = celdas[:j] + [celdas[j][: m.start()].strip(), m.group(1), celdas[j][m.end():].strip()] + celdas[j + 1:]
                    idx_valor = j + 1
                    break
        if "RESPONSABLE IVA" in T or "DECLARACIONES IVA" in T:
            n, _ = leer_importe(celdas[idx_valor]) if idx_valor is not None else (None, [])
            rep.responsable_iva = rep.responsable_iva or (n is None or n > 0)
            continue
        if idx_valor is None:
            _cabecera(texto, rep)
            continue
        valor, alts = leer_importe(celdas[idx_valor])
        if valor is None:
            continue
        # Celdas con texto real (no restos de la rejilla ni marcas como «#»).
        izquierda = [c for c in celdas[:idx_valor] if len(re.sub(r"[^A-Za-zÁÉÍÓÚÑáéíóúñ]", "", c)) >= 3]
        derecha = " ".join(c for c in celdas[idx_valor + 1:] if c)
        tope_cab = TOPE_ENCABEZADO.search(" ".join(izquierda))
        if tope_cab and not TOPE_USO.search(derecha) and not RENGLON.search(derecha) and len(izquierda) <= 2 and not any(_parece_entidad(x) for x in izquierda[:-1]):
            n = int(tope_cab.group(1))
            rep.topes[n] = str(valor)
            if alts:
                rep.topes_alternativas[n] = [str(a) for a in alts]
            continue
        entidad, titular, detalle = _repartir(izquierda)
        renglones = [int(r) for r in RENGLON.findall(derecha) if 28 <= int(r) <= 141]
        if not renglones:
            D = sin_tildes(derecha)
            renglones = [n for clave, n in RENGLON_POR_TEXTO.items() if clave in D]
        topes_uso = [int(t) for t in TOPE_USO.findall(derecha)]
        conf = confianzas[i] if i < len(confianzas) else 1.0
        if isinstance(conf, (list, tuple)):  # confianza de cada celda: cuenta la del valor
            conf = conf[idx_valor] if idx_valor < len(conf) else min(conf, default=1.0)
        contadas += 1
        altas += conf >= 0.6
        rep.lineas.append(Linea(
            id=f"{documento}:{pagina}:{i}", entidad=entidad, titular=titular, detalle=detalle, valor=str(valor),
            uso=derecha, renglon=renglones[-1] if renglones else None, tope=topes_uso[0] if topes_uso else None,
            no_titular=_es_titular_ausente(titular), confianza=round(conf, 2),
            resaltada=resaltadas[i] if i < len(resaltadas) else False, encimada=bool(alts) or conf < 0.6,
            alternativas=[str(a) for a in alts], documento=documento, pagina=pagina, fila=i,
            recorte=recortes[i] if i < len(recortes) else ""))
    rep.confianza_alta = (altas / contadas) if contadas else 1.0
    return rep


def _parece_entidad(texto: str) -> bool:
    T = sin_tildes(texto)
    return any(k in T for k in ("BANCO", "S.A", "SAS", "FIDUCIARIA", "COMPANIA", "DIRECCION", "LTDA"))


def _repartir(izquierda: list[str]) -> tuple[str, str, str]:
    if len(izquierda) >= 3:
        return izquierda[0], izquierda[1], " ".join(izquierda[2:])
    if len(izquierda) == 2:
        if _es_titular_ausente(izquierda[1]):
            return izquierda[0], izquierda[1], ""
        return izquierda[0], "", izquierda[1]
    return "", "", izquierda[0] if izquierda else ""


def _cabecera(texto: str, rep: Reporte) -> None:
    T = sin_tildes(texto)
    if not rep.numero_doc:
        m = DOCUMENTO.search(texto)
        if m and ("IDENTIFICACION" in T or "DOCUMENTO" in T or "C.C" in T or "NIT" in T):
            rep.numero_doc = re.sub(r"\D", "", m.group(1))
    if not rep.tipo_doc:
        if re.search(r"\bC\.?\s?C\.?\b", T):
            rep.tipo_doc = "C.C."
        elif "NIT" in T:
            rep.tipo_doc = "NIT"
    if rep.numero_doc and not rep.tipo_doc and len(rep.numero_doc) <= 10:
        rep.tipo_doc = "C.C."
    m = re.search(r"PAGINA\s*(\d+)", T)
    if m:
        rep.pagina = int(m.group(1))


def nombre_desde_cabecera(lineas: list[str]) -> tuple[str, bool]:
    """Nombre impreso de la línea «Nombres / Razón social» (o la que sigue a «Identificación»).

    El nombre es la tira más larga de palabras en MAYÚSCULAS. Lo que quede después en la
    misma línea (cifras, símbolos, garabatos) se trata como **anotación a mano**: no se
    guarda; solo se avisa. Devuelve (nombre, hubo_anotaciones).
    """
    limpias = [l.strip() for l in lineas if l.strip()]
    candidatas = [l for l in limpias if re.search(r"NOMBRE|RAZON|SOCIAL", sin_tildes(l))]
    for k, l in enumerate(limpias):
        if "IDENTIFICACION" in sin_tildes(l) and k + 1 < len(limpias):
            candidatas.append(limpias[k + 1])
    candidatas += limpias
    excluidas = ("NOMBRES", "RAZON", "SOCIAL", "TIPO", "DOCUMENTO", "IDENTIFICACION")
    for linea in candidatas:
        palabras = linea.split()
        mejor = (0, 0)
        inicio = None
        for k, p in enumerate(palabras + [""]):
            es = bool(re.fullmatch(r"[A-ZÁÉÍÓÚÑ]{2,}|[A-ZÁÉÍÓÚÑ].?", p)) and sin_tildes(p) not in excluidas
            if es and inicio is None:
                inicio = k
            if not es and inicio is not None:
                if k - inicio > mejor[1] - mejor[0]:
                    mejor = (inicio, k)
                inicio = None
        if mejor[1] - mejor[0] >= 2:
            resto = [p for p in palabras[mejor[1]:] if p.strip(".,;:")]
            return " ".join(palabras[mejor[0]:mejor[1]]), bool(resto)
    return "", False


# ── validación contra los topes ─────────────────────────────────────────
GRUPOS_TOPE = {
    1: ("Ingresos", lambda l: l.tope == 1),
    2: ("Patrimonio", lambda l: l.tope == 2 or l.renglon == 29),
    3: ("Consumos con tarjeta", lambda l: l.tope == 3),
    4: ("Movimientos", lambda l: l.tope == 4 and "INVERSION" not in sin_tildes(l.detalle)),
    5: ("Compras", lambda l: l.tope == 5),
}
TOLERANCIA = Decimal("1000")


def validar_sumas(rep: Reporte) -> list[dict]:
    """Compara la suma de las líneas de cada tope con el encabezado.

    - Diferencia ≤ 1.000 pesos: redondeo de la propia fuente (aviso informativo).
    - Si no: se prueban las alternativas de lectura (un valor a la vez, y el propio
      tope) y se toma la que cuadra; la línea queda «corregida: verifique».
    - Si nada cuadra: se señala la fila más probable de estar mal leída (la que
      corrige la diferencia cambiando un solo dígito).
    """
    resultado = []
    for n, (nombre, filtro) in GRUPOS_TOPE.items():
        if n not in rep.topes:
            continue
        lineas = [l for l in rep.lineas if filtro(l)]
        if not lineas:
            continue
        encabezados = [Decimal(rep.topes[n])] + [Decimal(a) for a in rep.topes_alternativas.get(n, [])]
        suma = sum((l.importe() for l in lineas), CERO)
        estado = {"tope": n, "nombre": nombre, "encabezado": Decimal(rep.topes[n]), "suma": suma, "estado": "cuadra",
                  "texto": ""}
        cuadra = _cuadra(suma, encabezados[0])
        if not cuadra:
            arreglo = _probar_alternativas(lineas, encabezados)
            if arreglo:
                tope_ok, cambios = arreglo
                if tope_ok != encabezados[0]:
                    rep.topes[n] = str(tope_ok)
                for linea, nuevo in cambios:
                    linea.alternativas = [linea.valor] + [a for a in linea.alternativas if a != str(nuevo)]
                    linea.valor = str(nuevo)
                    linea.corregida = True
                suma = sum((l.importe() for l in lineas), CERO)
                for l in lineas:
                    l.validada, l.encimada = True, l.corregida
                estado.update(encabezado=tope_ok, suma=suma, estado="corregida",
                              texto=f"Se corrigió una lectura dudosa para que {nombre.lower()} cuadre con el Tope {n}: verifíquela.")
            else:
                sospechosa = _un_digito(lineas, encabezados[0] - suma)
                estado.update(estado="no_cuadra", texto=(
                    f"La suma de {nombre.lower()} ({suma:,.0f}) no cuadra con el Tope {n} ({encabezados[0]:,.0f})."
                    + (f" La fila más probable de estar mal leída: {sospechosa.entidad} {sospechosa.valor}." if sospechosa else "")))
                if sospechosa:
                    sospechosa.encimada = True
        if cuadra:
            for l in lineas:
                l.validada, l.encimada = True, False
        if cuadra and suma != encabezados[0]:
            estado.update(estado="redondeo", texto=(
                f"{nombre}: las filas suman {suma:,.0f} y el encabezado dice {encabezados[0]:,.0f}. "
                f"La diferencia de {abs(suma - encabezados[0]):,.0f} pesos es del propio reporte."))
        resultado.append(estado)
    # Filas que ningún tope valida (deudas, retenciones…): si se leyeron con poca confianza y la
    # alternativa es la del «$» tomado por un dígito, se propone esa y la fila queda por confirmar.
    for l in rep.lineas:
        if not l.validada and l.alternativas and l.confianza < 0.6 and not l.corregida:
            alterna = l.alternativas[0]
            if l.valor[1:] == alterna and l.valor[:1] in "51":
                l.alternativas = [l.valor] + l.alternativas[1:]
                l.valor = alterna
                l.corregida = l.encimada = True
    return resultado


def _cuadra(suma: Decimal, tope: Decimal) -> bool:
    return abs(suma - tope) <= TOLERANCIA


def _probar_alternativas(lineas: list[Linea], encabezados: list[Decimal]):
    con_alt = [l for l in lineas if l.alternativas]
    base = sum((l.importe() for l in lineas), CERO)
    for tope in encabezados:
        if _cuadra(base, tope):
            return tope, []
        for k in (1, 2):
            for grupo in combinations(con_alt, k):
                for elecciones in _productos([[Decimal(a) for a in l.alternativas] for l in grupo]):
                    suma = base - sum((l.importe() for l in grupo), CERO) + sum(elecciones, CERO)
                    if _cuadra(suma, tope):
                        return tope, list(zip(grupo, elecciones))
    return None


def _productos(listas):
    if not listas:
        yield []
        return
    for x in listas[0]:
        for resto in _productos(listas[1:]):
            yield [x] + resto


def _un_digito(lineas: list[Linea], diferencia: Decimal) -> Linea | None:
    """La línea que, cambiando UN dígito, explica la diferencia."""
    if diferencia == 0:
        return None
    for l in lineas:
        v = l.valor
        for pos in range(len(v)):
            peso = Decimal(10) ** (len(v) - pos - 1)
            d = int(v[pos])
            for nuevo in range(10):
                if nuevo != d and (nuevo - d) * peso == diferencia:
                    return l
    return None


def unir_paginas(reportes: list[Reporte]) -> tuple[Reporte, list[str]]:
    """Une las páginas de un mismo contribuyente en un solo reporte y quita filas repetidas."""
    avisos: list[str] = []
    ordenados = sorted(reportes, key=lambda r: (r.pagina is None, r.pagina or 0, -len(r.topes)))
    base = Reporte(documento=", ".join(r.documento for r in ordenados if r.documento))
    vistos: set[tuple] = set()
    for r in ordenados:
        base.tipo_doc = base.tipo_doc or r.tipo_doc
        base.numero_doc = base.numero_doc or r.numero_doc
        base.nombre = base.nombre or r.nombre
        for n, v in r.topes.items():
            base.topes.setdefault(n, v)
        for n, v in r.topes_alternativas.items():
            base.topes_alternativas.setdefault(n, v)
        base.responsable_iva = base.responsable_iva or r.responsable_iva
        base.anotaciones_a_mano = base.anotaciones_a_mano or r.anotaciones_a_mano
        base.credenciales_descartadas += r.credenciales_descartadas
        base.sugerencias_a_mano += r.sugerencias_a_mano
        base.avisos += r.avisos
        for l in r.lineas:
            clave = (sin_tildes(l.entidad)[:12], sin_tildes(l.detalle)[:30], l.valor)
            if clave in vistos:
                avisos.append(f"Fila repetida quitada: {l.entidad} · {l.detalle} · {Decimal(l.valor):,.0f}")
                continue
            vistos.add(clave)
            base.lineas.append(l)
    total = sum(1 for r in reportes for _ in r.lineas) or 1
    base.confianza_alta = sum(r.confianza_alta * len(r.lineas) for r in reportes) / total
    return base, avisos
