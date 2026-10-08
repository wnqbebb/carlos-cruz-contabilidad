"""La ficha del cliente, sacada de sus documentos (spec v2.2 · Fase 6).

POR QUÉ EXISTE
El camino normal para crear un cliente es subir sus papeles: estatutos o acta
de constitución, RUT, certificado de cámara de comercio, cartas. Digitar la
ficha a mano es el respaldo, no la regla.

QUÉ SALE DE CADA DOCUMENTO
  · Estatutos y actas → razón social, sigla, tipo de sociedad, domicilio,
    objeto y CIIU, fecha y documento de constitución, capital autorizado,
    suscrito y pagado, acciones y valor nominal, socios, representante legal
    y suplente con sus cédulas, revisor fiscal.
  · RUT → NIT y DV, razón social, dirección, municipio, departamento,
    teléfono, correo, CIIU principal y secundarios, tipo de persona,
    responsabilidades.
  · Cámara de comercio → matrícula, representantes, capital, renovación.
  · Cartas y certificaciones → contador con su T.P., composición accionaria.

CÓMO SE DECIDE
Cada dato sale con su valor, su origen (archivo y línea o tabla) y su
confianza: «seguro» si venía rotulado («Matrícula No. 1234»), «por confirmar»
si se dedujo de la redacción. Si dos documentos dicen cosas distintas, el dato
queda en conflicto para que el contador elija: nunca se escoge en silencio.
Lo que no aparezca queda vacío.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from ..utils import nit as unit
from ..utils.numeros import NOMBRE_MES, normalizar, parse_numero
from . import identidad as ident
from .lector import Hoja

SEGURO = "seguro"
POR_CONFIRMAR = "por confirmar"

MESES = {n.upper(): m for m, n in NOMBRE_MES.items()} | {"SETIEMBRE": 9}
DEPARTAMENTOS = {
    "VALLE": "Valle del Cauca", "VALLE DEL CAUCA": "Valle del Cauca", "ANTIOQUIA": "Antioquia", "CUNDINAMARCA": "Cundinamarca",
    "CAUCA": "Cauca", "NARINO": "Nariño", "RISARALDA": "Risaralda", "QUINDIO": "Quindío", "CALDAS": "Caldas",
    "TOLIMA": "Tolima", "HUILA": "Huila", "ATLANTICO": "Atlántico", "BOLIVAR": "Bolívar", "SANTANDER": "Santander",
    "BOYACA": "Boyacá", "META": "Meta", "CHOCO": "Chocó", "BOGOTA": "Bogotá D.C.",
}
TIPOS_SOCIEDAD = [
    ("SOCIEDAD POR ACCIONES SIMPLIFICADA", "S.A.S."), ("RESPONSABILIDAD LIMITADA", "LTDA"),
    ("SOCIEDAD ANONIMA", "S.A."), ("EN COMANDITA POR ACCIONES", "S.C.A."), ("EN COMANDITA SIMPLE", "S. en C."),
    ("EMPRESA UNIPERSONAL", "E.U."),
]

# Un nombre de persona va en un solo renglón: «PEDRO PEREZ\nCapital suscrito» son dos cosas.
_NOMBRE = r"([A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ]+(?:[ \t]+[A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ]+){1,5})"
_CC = r"([\d][\d.\s]{4,14}\d)"


@dataclass
class Ficha:
    """Lo extraído, con procedencia y confianza; más los socios y qué documentos se leyeron."""
    identidad: ident.Identidad = field(default_factory=ident.Identidad)
    socios: list[dict] = field(default_factory=list)
    socios_origen: str = ""
    documentos: list[dict] = field(default_factory=list)

    def poner(self, campo: str, valor, origen: str, confianza: str = POR_CONFIRMAR) -> None:
        if valor is None:
            return
        if isinstance(valor, Decimal):
            valor = format(valor, "f")
        elif isinstance(valor, date):
            valor = valor.isoformat()
        self.identidad.poner(campo, str(valor), origen, ident.SEGURO if confianza == SEGURO else ident.PROBABLE)

    def a_json(self) -> dict:
        datos = self.identidad.a_json()

        def conf(c: str) -> str:
            return SEGURO if c == ident.SEGURO else POR_CONFIRMAR

        return {
            "campos": {k: {**v, "confianza": conf(v["confianza"])} for k, v in datos["campos"].items()},
            "conflictos": {k: [{**d, "confianza": conf(d["confianza"])} for d in v] for k, v in datos["conflictos"].items()},
            "socios": self.socios,
            "socios_origen": self.socios_origen,
            "documentos": self.documentos,
        }

    def valores(self) -> dict:
        """Solo los valores, listos para crear o actualizar la ficha."""
        salida = {k: d.valor for k, d in self.identidad.campos.items()}
        if self.socios:
            salida["socios"] = self.socios
        return salida


# ── utilidades ──────────────────────────────────────────────────────────────
def _plano(t: str) -> str:
    return re.sub(r"[ \t]+", " ", t or "")


def _linea(texto: str, pos: int) -> int:
    return texto.count("\n", 0, pos) + 1


def _dinero(t: str) -> Decimal | None:
    v = parse_numero(t)
    return v if v is not None and v > 0 else None


def _cedula(t: str) -> str:
    return re.sub(r"\D", "", t or "")


def _titulo(nombre: str) -> str:
    """«ADRIANA DURAN JARAMILLO» → «Adriana Duran Jaramillo» (como se escribe una ficha)."""
    pequeñas = {"DE", "DEL", "LA", "LAS", "LOS", "Y"}
    return " ".join(p.capitalize() if p.upper() not in pequeñas else p.lower() for p in nombre.split())


def tipo_documento(texto: str, archivo: str) -> str:
    t = normalizar(texto[:4000]) + " " + normalizar(archivo)
    if "REGISTRO UNICO TRIBUTARIO" in t or ("DIAN" in t and "FORMULARIO" in t) or re.search(r"\bRUT\b", normalizar(archivo)):
        return "rut"
    if "CAMARA DE COMERCIO" in t and ("CERTIFICA" in t or "MATRICULA" in t):
        return "camara"
    if any(p in t for p in ("ESTATUTOS", "CONSTITUCION", "ACTA DE ASAMBLEA", "ASAMBLEA GENERAL", "DOCUMENTO PRIVADO")):
        return "estatutos"
    if any(p in t for p in ("HACE CONSTAR", "CERTIFICA", "SENORES", "CUENTA DE COBRO", "ATENTAMENTE")):
        return "carta"
    return "documento"


NOMBRE_DOCUMENTO = {"rut": "RUT", "camara": "Certificado de cámara de comercio", "estatutos": "Estatutos o acta",
                    "carta": "Carta o certificación", "documento": "Documento"}


# ── extractores ─────────────────────────────────────────────────────────────
def _razon_y_sigla(f: Ficha, texto: str, origen) -> None:
    m = re.search(r"(?:denominada|se denominar[aá],?|denominaci[oó]n social[:\s]+|raz[oó]n social[:\s]+)\s*"
                  r"((?:[A-ZÁÉÍÓÚÑ0-9&.\-]+\s+){1,8}(?:S\.?\s?A\.?\s?S|LTDA|S\.?\s?A|E\.?\s?U)\.?)", texto)
    if m:
        f.poner("razon_social", re.sub(r"\s+", " ", m.group(1)).strip(" ,"), origen(m), SEGURO)
    m = re.search(r"sigla\s*[“\"«']\s*([A-Z0-9][A-Z0-9 .&-]{1,24}?)\s*[”\"»']", texto, re.IGNORECASE)
    if m:
        f.poner("sigla", m.group(1).strip(), origen(m), SEGURO)
    t = normalizar(texto[:6000])
    for frase, sigla in TIPOS_SOCIEDAD:
        if frase in t:
            f.poner("tipo_sociedad", sigla, origen(None, f"«{frase.lower()}»"))
            f.poner("tipo_persona", "juridica", origen(None, f"«{frase.lower()}»"))
            break


def _domicilio(f: Ficha, texto: str, origen) -> None:
    m = re.search(r"domicilio(?: principal)?(?: de la sociedad)? ser[aá] (?:en )?\s*(?:la ciudad de|el municipio de)?\s*"
                  r"([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?: [A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)?)(?:\s+(Valle(?: del Cauca)?|[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+))?",
                  texto)
    if m:
        municipio, segundo = m.group(1), m.group(2) or ""
        # «Guacarí Valle»: la segunda palabra es el departamento, no parte del municipio.
        partes = municipio.split()
        if len(partes) == 2 and normalizar(partes[1]) in DEPARTAMENTOS:
            municipio, segundo = partes[0], partes[1]
        f.poner("municipio", municipio, origen(m))
        depto = DEPARTAMENTOS.get(normalizar(segundo))
        if depto:
            f.poner("departamento", depto, origen(m))
    m = re.search(r"direcci[oó]n (?:para notificaciones(?: judiciales)?|principal|comercial)\s*(?:ser[aá]|:)\s*"
                  r"([^;\n]{6,90}?)(?:;|(?<!No)(?<!N)\.\s|\n|$)", texto, re.IGNORECASE)
    if m:
        f.poner("direccion", m.group(1).strip(" ,."), origen(m))


def _objeto_y_ciiu(f: Ficha, texto: str, origen) -> None:
    m = re.search(r"objeto (?:social|principal)[^.:]{0,80}?(?:tendr[aá] como objeto principal|ser[aá]|:)\s*(.{20,600}?)\.",
                  texto, re.IGNORECASE | re.DOTALL)
    if m:
        f.poner("objeto_social", re.sub(r"\s+", " ", m.group(1)).strip()[:500], origen(m))
    m = re.search(r"CIIU[^0-9]{0,40}(\d{4}(?:\s*(?:,|\by\b|;)?\s*\d{4})*)", texto)
    if m:
        codigos = re.findall(r"\d{4}", m.group(1))
        if codigos:
            f.poner("ciiu", codigos[0], origen(m), SEGURO)
            if len(codigos) > 1:
                f.poner("ciiu_secundarios", ", ".join(codigos[1:]), origen(m), SEGURO)


def _constitucion(f: Ficha, texto: str, origen) -> None:
    m = re.search(r"\((\d{1,2})\)\s*d[ií]as? del mes de (\w+) del? a[ñn]o [^()]{0,60}\((\d{4})\)", texto, re.IGNORECASE)
    if not m:
        m = re.search(r"\b(\d{1,2}) de (\w+) de(?:l)? (\d{4})", texto, re.IGNORECASE)
    if m:
        mes = MESES.get(normalizar(m.group(2)))
        if mes:
            try:
                f.poner("fecha_constitucion", date(int(m.group(3)), mes, int(m.group(1))), origen(m))
            except ValueError:
                pass
    m = re.search(r"((?:DOCUMENTO PRIVADO|ESCRITURA P[UÚ]BLICA|ACTA)[^\n]{0,30}?No\.?\s*[\w-]+)", texto, re.IGNORECASE)
    if m:
        f.poner("documento_constitucion", re.sub(r"\s+", " ", m.group(1)).strip(), origen(m), SEGURO)


def _capital(f: Ficha, texto: str, origen) -> None:
    for campo, rotulo in (("capital_autorizado", "autorizado"), ("capital_suscrito", "suscrito"), ("capital_pagado", "pagado")):
        m = re.search(rf"capital {rotulo}\b[^$]{{0,90}}\$\s*([\d.,]+)", texto, re.IGNORECASE)
        if m and _dinero(m.group(1)):
            f.poner(campo, _dinero(m.group(1)), origen(m), SEGURO)
    m = re.search(r"capital suscrito y pagado[^$]{0,40}\$\s*([\d.,]+)", texto, re.IGNORECASE)
    if m and _dinero(m.group(1)):
        for campo in ("capital_suscrito", "capital_pagado"):
            f.poner(campo, _dinero(m.group(1)), origen(m), SEGURO)
    m = re.search(r"dividido en [A-ZÁÉÍÓÚÑa-záéíóúñ ]*\(?([\d.]+)\)?\s*acciones", texto, re.IGNORECASE)
    if m and _dinero(m.group(1)):
        f.poner("numero_acciones", _dinero(m.group(1)), origen(m), SEGURO)
    m = (re.search(r"valor nominal de[^$(]{0,60}\(?\$\s*([\d.,]+)", texto, re.IGNORECASE)
         or re.search(r"VALOR DE\s+([\d.,]+)\s+PESOS CADA ACCI[OÓ]N", texto, re.IGNORECASE))
    if m and _dinero(m.group(1)):
        f.poner("valor_nominal_accion", _dinero(m.group(1)), origen(m), SEGURO)


def _representantes(f: Ficha, texto: str, origen, cedulas: dict[str, str]) -> None:
    patrones = [
        rf"\ba\s+{_NOMBRE},?\s+identificad[oa] con (?:el documento de identidad|la c[eé]dula)[^\d]{{0,25}}{_CC}\s*,?\s*"
        rf"como representante legal\s+principal",
        rf"representante legal principal ser[aá] (?:la señora|el señor|la senora)\s+{_NOMBRE}",
        rf"representante legal(?: principal)?\s*[:\-]\s*{_NOMBRE}",
    ]
    for p in patrones:
        m = re.search(p, texto, re.IGNORECASE)
        if m:
            nombre = _limpiar_nombre(m.group(1))
            f.poner("rep_legal", _titulo(nombre), origen(m), SEGURO)
            cc = _cedula(m.group(2)) if m.lastindex and m.lastindex >= 2 else cedulas.get(normalizar(nombre), "")
            if cc:
                f.poner("rep_legal_cc", cc, origen(m), SEGURO if m.lastindex and m.lastindex >= 2 else POR_CONFIRMAR)
            break
    patrones = [
        rf"\by\s+{_NOMBRE}\s+como representante legal suplente(?: con c[eé]dula No\.?\s*{_CC})?",
        rf"SU SUPLENTE SER[AÁ] (?:LA SEÑORA|EL SEÑOR|LA SENORA)\s+{_NOMBRE}",
        rf"(?:representante legal )?suplente\s*[:\-]\s*{_NOMBRE}",
    ]
    for p in patrones:
        m = re.search(p, texto, re.IGNORECASE)
        if m:
            nombre = _limpiar_nombre(m.group(1))
            f.poner("rep_legal_suplente", _titulo(nombre), origen(m), SEGURO)
            cc = _cedula(m.group(2)) if m.lastindex and m.lastindex >= 2 and m.group(2) else cedulas.get(normalizar(nombre), "")
            if cc:
                f.poner("rep_legal_suplente_cc", cc, origen(m), SEGURO if m.lastindex and m.lastindex >= 2 and m.group(2)
                        else POR_CONFIRMAR)
            break
    # Revisor fiscal: solo si se NOMBRA a alguien («la revisoría fiscal solo será provista…» no nombra a nadie).
    m = re.search(rf"revisor(?:a)? fiscal(?: principal)?\s*(?:a|:|ser[aá])\s*(?:la señora|el señor)?\s*{_NOMBRE}", texto)
    if m and not re.search(r"\bSOLO\b|\bSER[AÁ] PROVISTA\b", m.group(0), re.IGNORECASE):
        f.poner("revisor_fiscal", _titulo(_limpiar_nombre(m.group(1))), origen(m))
        tp = re.search(r"T\.?\s*P\.?\s*(?:No\.?)?\s*([\d.]+-?T)", texto[m.end(): m.end() + 200])
        if tp:
            f.poner("revisor_fiscal_tp", tp.group(1), origen(m))


def _limpiar_nombre(n: str) -> str:
    n = re.sub(r"\s+", " ", n).strip()
    # «ADRIANA DURAN JARAMILLO Y SU SUPLENTE»: se corta en las palabras de redacción.
    return re.split(r"\s+(?:Y|COMO|IDENTIFICAD[OA]|CON|TITULAR|DE LA|DEL)\b", n, maxsplit=1)[0].strip()


def _cedulas_en_texto(texto: str) -> dict[str, str]:
    """Nombre → cédula, de frases como «ADRIANA DURAN JARAMILLO, titular de la cedula [CEDULA]»."""
    salida = {}
    for m in re.finditer(rf"{_NOMBRE}[,;]?\s+(?:titular de la|identificad[oa] con la|con)\s+c[eé]dula(?: de ciudadan[ií]a)?"
                         rf"(?: No\.?)?\s*{_CC}", texto, re.IGNORECASE):
        salida[normalizar(_limpiar_nombre(m.group(1)))] = _cedula(m.group(2))
    return salida


def _contador(f: Ficha, texto: str, origen) -> None:
    pos = re.search(r"CONTADOR(?:A)? P[UÚ]BLIC[OA]", texto, re.IGNORECASE)
    if not pos:
        return
    resto = texto[pos.end():]
    m = re.search(r"T\.?\s*P\.?\s*(?:No\.?)?\s*([\d.]{4,9}\s*-?\s*T)\b", resto, re.IGNORECASE)
    if not m:
        return
    f.poner("contador_tp", re.sub(r"\s+", "", m.group(1)).upper(), origen(None, "T.P."), SEGURO)
    antes = resto[:m.start()].strip().splitlines()[-4:]
    cc = next((_cedula(re.search(r"c\.?\s*c\.?\s*(?:No\.?)?\s*([\d.\s]{6,15})", l, re.I).group(1))
               for l in reversed(antes) if re.search(r"c\.?\s*c\.?\s*(?:No\.?)?\s*\d", l, re.I)), "")
    if cc:
        f.poner("contador_cc", cc, origen(None, "c.c. del contador"), SEGURO)
    nombre = next((l.strip() for l in reversed(antes)
                   if re.fullmatch(r"[A-ZÁÉÍÓÚÑ ]{8,60}", l.strip()) and len(l.split()) >= 2), "")
    if nombre:
        f.poner("contador", _titulo(nombre), origen(None, "firma del contador"))


def _contacto(f: Ficha, texto: str, origen) -> None:
    m = re.search(r"[\w.+-]+@[\w-]+\.[\w.]+", texto)
    if m:
        f.poner("email", m.group(0).strip("."), origen(m))
    m = re.search(r"tel[eé]fonos?(?: celulares?)?[^\d]{0,20}(3\d{9}|\d{7,10})", texto, re.IGNORECASE)
    if m:
        f.poner("telefono", m.group(1), origen(m))


def _responsabilidades(f: Ficha, texto: str, origen) -> None:
    m = re.search(r"responsabilidades(?: tributarias)?\s*:?\s*(.{5,400}?)(?:\.\s|\n)", texto, re.IGNORECASE | re.DOTALL)
    if not m:
        return
    codigos = re.findall(r"\b(\d{2})\b\s*[,\-–]?\s*[A-Za-zÁÉÍÓÚáéíóú]", m.group(1))
    if codigos:
        f.poner("responsabilidades", ", ".join(dict.fromkeys(codigos)), origen(m), SEGURO)
        # 48 = responsable del impuesto sobre las ventas (IVA); 49 = no responsable.
        if "48" in codigos:
            f.poner("responsable_iva", "true", origen(m), SEGURO)
        elif "49" in codigos:
            f.poner("responsable_iva", "false", origen(m), SEGURO)


def _rut(f: Ficha, texto: str, origen) -> None:
    """RUT: los datos van rotulados en el formulario; se toma lo que sigue al rótulo."""
    def tras(rotulo: str, patron: str = r"([^\n]{2,80})") -> re.Match | None:
        return re.search(rotulo + r"\s*:?\s*\n?\s*" + patron, texto, re.IGNORECASE)

    m = tras(r"(?:N[uú]mero de Identificaci[oó]n Tributaria|NIT)\s*(?:\(NIT\))?", r"([\d.\s]{8,15})\s*-?\s*(\d)?")
    if m:
        f.poner("nit", _cedula(m.group(1)), origen(m), SEGURO)
        if m.group(2):
            f.poner("dv", m.group(2), origen(m), SEGURO)
    for rotulo, campo in ((r"Raz[oó]n social", "razon_social"), (r"Direcci[oó]n principal", "direccion"),
                          (r"Municipio(?:\s*/\s*Ciudad)?", "municipio"), (r"Departamento", "departamento"),
                          (r"Correo electr[oó]nico", "email"), (r"Tel[eé]fono 1", "telefono")):
        m = tras(rotulo)
        if m:
            valor = re.split(r"\s{2,}|\s+\d{1,2}\.\s", m.group(1).strip())[0].strip(" :")
            if valor and not re.fullmatch(r"\d{1,3}", valor):
                f.poner(campo, valor, origen(m), SEGURO)
    m = re.search(r"Actividad principal[^\d]{0,60}(\d{4})", texto, re.IGNORECASE)
    if m:
        f.poner("ciiu", m.group(1), origen(m), SEGURO)
    secundarias = re.findall(r"Actividad secundaria[^\d]{0,60}(\d{4})", texto, re.IGNORECASE)
    if secundarias:
        f.poner("ciiu_secundarios", ", ".join(dict.fromkeys(secundarias)), origen(None, "Actividad secundaria"), SEGURO)
    m = re.search(r"Tipo de contribuyente\s*:?\s*(Persona (?:jur[ií]dica|natural))", texto, re.IGNORECASE)
    if m:
        f.poner("tipo_persona", "natural" if "natural" in m.group(1).lower() else "juridica", origen(m), SEGURO)
    m = re.search(r"Responsabilidades[^\n]*\n?((?:\s*\d{2}\s*-\s*[^\n]+\n?){1,15})", texto, re.IGNORECASE)
    if m:
        codigos = re.findall(r"(\d{2})\s*-", m.group(1))
        if codigos:
            f.poner("responsabilidades", ", ".join(dict.fromkeys(codigos)), origen(m), SEGURO)
            if "48" in codigos:
                f.poner("responsable_iva", "true", origen(m), SEGURO)
            elif "49" in codigos:
                f.poner("responsable_iva", "false", origen(m), SEGURO)


def _camara(f: Ficha, texto: str, origen) -> None:
    m = re.search(r"Matr[ií]cula(?: mercantil)?\s*(?:No\.?|N[uú]mero)?\s*:?\s*([\d-]{3,15})", texto, re.IGNORECASE)
    if m:
        f.poner("matricula_mercantil", m.group(1), origen(m), SEGURO)
    m = re.search(r"(?:fecha de )?renovaci[oó]n\s*:?\s*(\d{1,2})\s+de\s+(\w+)\s+de\s+(\d{4})", texto, re.IGNORECASE)
    if m and MESES.get(normalizar(m.group(2))):
        f.poner("fecha_renovacion", date(int(m.group(3)), MESES[normalizar(m.group(2))], int(m.group(1))), origen(m), SEGURO)
    else:
        m = re.search(r"renovaci[oó]n\s*:?\s*(\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{4})", texto, re.IGNORECASE)
        if m:
            from ..utils.numeros import parse_fecha

            if parse_fecha(m.group(1)):
                f.poner("fecha_renovacion", parse_fecha(m.group(1)), origen(m), SEGURO)


# ── socios desde tablas ─────────────────────────────────────────────────────
def socios_de_tabla(h: Hoja) -> list[dict]:
    """Socios de una tabla «NOMBRE | CÉDULA | … ACCIONES | VALOR | %»."""
    from .encabezados import parecido

    for r in range(min(h.nfilas, 5)):
        textos = {c: normalizar(t) for c, t in h.fila_textos(r)}
        c_nom = next((c for c, t in textos.items() if t.startswith("NOMBRE") or t in ("SOCIO", "ACCIONISTA", "SOCIOS")), None)
        c_ced = next((c for c, t in textos.items() if "CEDULA" in t or t in ("CC", "C C", "DOCUMENTO", "IDENTIFICACION")), None)
        if c_nom is None or c_ced is None:
            continue
        c_acc = next((c for c, t in textos.items() if ("ACC" in t and "VR" not in t and "VALOR" not in t)
                      or t in ("ACCIONES", "NO ACCIONES", "CUOTAS")), None)
        c_tot = next((c for c, t in textos.items() if any(parecido(tok, "TOTAL") >= 80 for tok in t.split())
                      or t in ("APORTE", "VALOR APORTE")), None)
        c_pct = next((c for c, t in textos.items() if t in ("", "PORCENTAJE", "PARTICIPACION") or "%" in str(h.v(r, c) or "")),
                     None)
        socios = []
        for rr in range(r + 1, h.nfilas):
            nombre = h.texto(rr, c_nom)
            if not nombre or normalizar(nombre).startswith(("TOTAL", "SUMA")):
                continue
            socio = {"nombre": _titulo(nombre) if nombre.isupper() else nombre, "cedula": _cedula(h.texto(rr, c_ced))}
            if c_acc is not None:
                socio["acciones"] = format(parse_numero(h.texto(rr, c_acc)) or Decimal(0), "f")
            if c_tot is not None:
                aporte = parse_numero(h.texto(rr, c_tot)) or Decimal(0)
                socio["comprometido"] = socio["pagado"] = format(aporte, "f")
            if c_pct is not None:
                pct = parse_numero(h.texto(rr, c_pct).replace("%", "").strip())
                if pct is not None:
                    socio["participacion"] = format(pct / 100 if pct > 1 else pct, "f")
            socios.append(socio)
        if socios:
            return socios
    return []


# ── entrada principal ───────────────────────────────────────────────────────
def extraer(hojas_por_archivo: dict[str, list[Hoja]]) -> Ficha:
    """Lee todos los documentos subidos y arma una sola ficha, con conflictos marcados."""
    f = Ficha()
    for archivo, hojas in hojas_por_archivo.items():
        texto_hoja = next((h for h in hojas if getattr(h, "es_texto", False)), None)
        texto = _plano(getattr(texto_hoja, "texto_plano", "") if texto_hoja else "")
        tipo = tipo_documento(texto, archivo)
        f.documentos.append({"archivo": archivo, "tipo": tipo, "nombre_tipo": NOMBRE_DOCUMENTO[tipo]})

        def origen(m: re.Match | None, detalle: str = "", _a=archivo, _t=texto) -> str:
            if m is not None:
                return f"{_a}, línea {_linea(_t, m.start())}"
            return f"{_a}" + (f" ({detalle})" if detalle else "")

        if texto:
            # Identidad básica (NIT y razón social) con las reglas de siempre.
            ident.de_texto(texto, archivo, f.identidad)
            cedulas = _cedulas_en_texto(texto)
            _razon_y_sigla(f, texto, origen)
            if tipo == "rut":
                _rut(f, texto, origen)
            if tipo in ("estatutos", "camara"):
                _domicilio(f, texto, origen)
                _objeto_y_ciiu(f, texto, origen)
                _constitucion(f, texto, origen)
                _capital(f, texto, origen)
                _representantes(f, texto, origen, cedulas)
                _responsabilidades(f, texto, origen)
            if tipo == "camara":
                _camara(f, texto, origen)
            if tipo in ("carta", "estatutos", "documento"):
                _contador(f, texto, origen)
            _contacto(f, texto, origen)
        # Los socios salen de las tablas de un documento (Word o PDF). Una hoja de
        # Excel con «NOMBRE | CÉDULA» suele ser una nómina, no la lista de socios.
        es_documento = archivo.lower().endswith((".docx", ".pdf"))
        for h in hojas:
            if getattr(h, "es_texto", False) or not es_documento:
                continue
            socios = socios_de_tabla(h)
            if socios and not f.socios:
                f.socios = socios
                f.socios_origen = f"{archivo} › {h.nombre}"
            elif socios and _firma_socios(socios) != _firma_socios(f.socios):
                f.identidad.conflictos.setdefault("socios", [ident.Dato(f"{len(f.socios)} socios", f.socios_origen)])
                f.identidad.conflictos["socios"].append(ident.Dato(f"{len(socios)} socios", f"{archivo} › {h.nombre}"))

    # La cédula del representante legal sale de la lista de socios si la redacción no la dio.
    por_nombre = {normalizar(s["nombre"]): s.get("cedula", "") for s in f.socios}
    for campo, cc in (("rep_legal", "rep_legal_cc"), ("rep_legal_suplente", "rep_legal_suplente_cc")):
        nombre = f.identidad.valor(campo)
        if nombre and cc not in f.identidad.campos and por_nombre.get(normalizar(nombre)):
            f.poner(cc, por_nombre[normalizar(nombre)], f"{f.socios_origen} (lista de socios)")
    if f.identidad.valor("nit") and "dv" not in f.identidad.campos:
        f.poner("dv", unit.digito_verificacion(f.identidad.valor("nit")), "calculado del NIT", SEGURO)
    return f


def _firma_socios(socios: list[dict]) -> tuple:
    return tuple(sorted((s.get("cedula") or normalizar(s.get("nombre"))) for s in socios))
