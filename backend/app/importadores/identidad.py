"""De quién es este archivo: NIT y razón social sacados de lo que haya.

POR QUÉ EXISTE
Hasta la v2.1 el contador tenía que crear la ficha del cliente a mano antes de
poder subir su contabilidad, y si no elegía cliente el sistema asumía que era
FANANT. Desde la v2.2 la identidad se busca en los propios archivos, en este
orden de confianza (spec v2.2 · Fase 3):

  1. hoja EMPRESA de la plantilla oficial  → seguro
  2. documentos Word o PDF (estatutos, RUT, cámara, cartas) → seguro/probable
  3. celdas con NIT o razón social en cualquier hoja de Excel → probable
  4. nombre del archivo → sugerido
  5. coincidencia con un cliente que ya existe → lo resuelve el llamador

Cada dato sabe de dónde salió, porque el contador tiene que poder revisarlo
antes de crear una ficha.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field

from ..utils import nit as unit

# ── confianza ───────────────────────────────────────────────────────────────
SEGURO = "seguro"        # venía rotulado como tal («NIT: [NIT]»)
PROBABLE = "probable"    # la forma del dato lo delata (una razón social con S.A.S.)
SUGERIDO = "sugerido"    # deducido del nombre del archivo; hay que confirmarlo

_ORDEN = {SEGURO: 3, PROBABLE: 2, SUGERIDO: 1}


@dataclass
class Dato:
    """Un valor y de dónde salió, para poder mostrarlo y discutirlo."""
    valor: str
    origen: str
    confianza: str = PROBABLE

    def mejor_que(self, otro: "Dato | None") -> bool:
        if otro is None:
            return True
        return _ORDEN[self.confianza] > _ORDEN[otro.confianza]


@dataclass
class Identidad:
    """Lo que se pudo averiguar del dueño de los archivos."""
    campos: dict[str, Dato] = field(default_factory=dict)
    conflictos: dict[str, list[Dato]] = field(default_factory=dict)

    def poner(self, campo: str, valor: str | None, origen: str, confianza: str = PROBABLE) -> None:
        valor = (valor or "").strip()
        if not valor:
            return
        nuevo = Dato(valor, origen, confianza)
        actual = self.campos.get(campo)
        if actual and _normalizar(actual.valor) != _normalizar(valor):
            # Dos documentos dicen cosas distintas: se guarda para que el
            # contador elija, en vez de quedarse con el último en llegar.
            self.conflictos.setdefault(campo, [actual])
            if not any(_normalizar(d.valor) == _normalizar(valor) for d in self.conflictos[campo]):
                self.conflictos[campo].append(nuevo)
        if nuevo.mejor_que(actual):
            self.campos[campo] = nuevo

    def valor(self, campo: str) -> str:
        d = self.campos.get(campo)
        return d.valor if d else ""

    def a_json(self) -> dict:
        return {
            "campos": {k: {"valor": d.valor, "origen": d.origen, "confianza": d.confianza}
                       for k, d in self.campos.items()},
            "conflictos": {k: [{"valor": d.valor, "origen": d.origen, "confianza": d.confianza} for d in v]
                           for k, v in self.conflictos.items()},
        }


def _normalizar(t: str) -> str:
    t = unicodedata.normalize("NFD", str(t or "")).encode("ascii", "ignore").decode()
    return re.sub(r"[^A-Z0-9]+", " ", t.upper()).strip()


# ── NIT y cédula ────────────────────────────────────────────────────────────
# Distinguir una cosa de la otra importa: unos estatutos traen el NIT de la
# sociedad y, debajo, la cédula de cada socio. Confundirlos crea el cliente
# equivocado. La etiqueta es la que manda.
_NUM = r"([0-9][0-9\.\, ]{4,15}[0-9])(?:\s*[-–]\s*(\d)\b)?"
_ETIQUETA = r"\s*\.?\s*(?:N[oº°]?\.?)?\s*[:\-–]?\s*"
_RE_NIT = re.compile(r"(?:N\.?\s*I\.?\s*T\.?|NIT|RUT)" + _ETIQUETA + _NUM, re.IGNORECASE)
_RE_CEDULA = re.compile(r"(?:C\.?\s*C\.?|C[EÉ]DULA(?:\s+DE\s+CIUDADAN[IÍ]A)?)" + _ETIQUETA + _NUM,
                        re.IGNORECASE)
# Un número suelto con forma de NIT: solo se acepta si su dígito de
# verificación cuadra, que es una comprobación fuerte.
_RE_NIT_SUELTO = re.compile(r"\b(\d{1,3}(?:\.\d{3}){2,3})\s*[-–]\s*(\d)\b")

# Sufijos societarios, ya normalizados (sin puntos ni tildes).
_SUFIJOS = {"SAS", "SA", "LTDA", "LIMITADA", "EU", "SCA", "ESP", "SCS", "SENC", "CIA"}
# Solo valen como PRIMERA palabra: «FUNDACION MI CASA» sí; «… a favor de la
# sociedad» no.
_PALABRAS_ENTIDAD = {"CORPORACION", "FUNDACION", "ASOCIACION", "COOPERATIVA"}


def _digitos(v: str) -> str:
    return re.sub(r"\D", "", v or "")


def documento_en_texto(texto: str) -> tuple[str, str, str] | None:
    """Primer documento reconocible del texto: (clase, numero, dv).

    `clase` es «nit» o «cedula». Se devuelve el primero que aparezca etiquetado;
    si no hay ninguno etiquetado, se acepta un número suelto cuyo dígito de
    verificación cuadre.
    """
    texto = texto or ""
    candidatos = []
    for clase, patron in (("nit", _RE_NIT), ("cedula", _RE_CEDULA)):
        for m in patron.finditer(texto):
            numero = _digitos(m.group(1))
            if 6 <= len(numero) <= 11:
                candidatos.append((m.start(), clase, numero, m.group(2) or ""))
    if candidatos:
        candidatos.sort()
        _, clase, numero, dv = candidatos[0]
        return clase, numero, dv
    for m in _RE_NIT_SUELTO.finditer(texto):
        numero = _digitos(m.group(1))
        if 8 <= len(numero) <= 10 and unit.digito_verificacion(numero) == m.group(2):
            return "nit", numero, m.group(2)
    return None


def nit_en_texto(texto: str) -> tuple[str, str] | None:
    """Solo el NIT de una empresa (no la cédula de una persona)."""
    hallado = documento_en_texto(texto)
    if hallado and hallado[0] == "nit":
        return hallado[1], hallado[2]
    return None


# Primeras palabras que delatan un TÍTULO de documento, no un nombre de empresa:
# «ESTATUTOS DE SOCIEDAD POR ACCIONES SIMPLIFICADA S.A.S.» no es un cliente.
_TITULOS = {
    "ESTATUTOS", "ACTA", "ACTAS", "CERTIFICADO", "CERTIFICACION", "CONTRATO", "CUENTA",
    "CAMARA", "CONSTITUCION", "DOCUMENTO", "ANEXO", "FORMULARIO", "REGISTRO", "NOTA",
    "NOTAS", "INFORME", "DICTAMEN", "BALANCE", "ESTADO", "ESTADOS", "LIBRO", "CAPITULO",
    "ARTICULO", "PARAGRAFO", "PAR", "ASAMBLEA", "REUNION", "CLAUSULA",
}


# Palabras en MAYÚSCULA seguidas de un sufijo societario, en cualquier punto de
# la frase. Las mayúsculas son la señal: en estos documentos el nombre de la
# sociedad va en mayúsculas y el resto de la redacción no.
_RE_NOMBRE = re.compile(
    r"((?:[A-ZÁÉÍÓÚÑ&][A-ZÁÉÍÓÚÑ0-9&.''’·-]*\s+){1,7}"
    r"(?:S\.?\s?A\.?\s?S|LTDA|LIMITADA|S\.?\s?A|E\.?\s?U|S\.?\s?C\.?\s?A|S\.?\s?E\.?\s?N\.?\s?C)\.?)"
    r"(?![A-ZÁÉÍÓÚÑ])"
)


def razones_sociales_en_texto(texto: str) -> list[str]:
    """Nombres de empresa que aparecen dentro de una frase, en orden."""
    salida: list[str] = []
    for m in _RE_NOMBRE.finditer(texto or ""):
        nombre = re.sub(r"\s+", " ", m.group(1)).strip(" .,;:-–")
        # «LA SOCIEDAD X S.A.S.» → quitar el arrastre de artículos en mayúscula.
        nombre = re.sub(r"^(?:LA|EL|DE|DEL|Y|A)\s+", "", nombre)
        palabras = _normalizar(nombre).split()
        if not palabras or palabras[0] in _TITULOS:
            continue   # «ESTATUTOS DE SOCIEDAD POR ACCIONES SIMPLIFICADA S.A.S.» es el título
        if len(nombre) >= 6 and nombre.upper() not in {"S A S", "LTDA"}:
            salida.append(nombre)
    return salida


def parece_razon_social(texto: str) -> bool:
    """¿Esta línea parece el nombre de una empresa?

    Tres condiciones, todas necesarias para no confundirse:
      · un sufijo societario como PALABRA («… S.A.S.», «… LTDA»), no como trozo
        suelto, porque si no cualquier nombre con «s» y «a» parecería sociedad;
      · ese sufijo al final, que es donde va en el nombre de una empresa;
      · que la línea no empiece como el título de un documento ni como una
        cláusula de unos estatutos.
    """
    # «FARMACIA X S.A.S.   RUT. [NIT]-9»: el nombre es lo que va antes del NIT.
    t = _normalizar(_limpiar_nombre(texto))
    if not (4 <= len(t) <= 120):
        return False
    if re.fullmatch(r"[\d\s]+", t):
        return False
    palabras = t.split()
    if len(palabras) < 2 or palabras[0] in _TITULOS:
        return False
    if palabras[0] in _PALABRAS_ENTIDAD:
        return True
    # «S.A.S.» normaliza a «S A S»: se vuelven a pegar las iniciales sueltas.
    pegado = re.sub(r"\b(?:([A-Z])\s)+([A-Z])\b", lambda m: m.group(0).replace(" ", ""), t).split()
    # El sufijo tiene que ir al final, que es donde va en el nombre de una empresa.
    return bool(set(pegado[-2:]) & _SUFIJOS)


# Palabras que describen QUÉ es el archivo, no DE QUIÉN es. Se quitan del nombre
# antes de proponerlo como razón social. Solo son tipos de documento, meses y
# ruido ofimático: nunca palabras que puedan formar parte del nombre de un
# negocio («TIENDA», «DROGUERÍA», «FERRETERÍA» se conservan a propósito).
_RUIDO_ARCHIVO = {
    # qué contiene
    "CONTABILIDAD", "CONTABLE", "CONTA", "BALANCE", "BALANCES", "PRUEBA", "DEFINITIVO",
    "LIBRO", "LIBROS", "DIARIO", "MAYOR", "AUXILIAR", "AUXILIARES", "MOVIMIENTO",
    "MOVIMIENTOS", "COMPROBANTE", "COMPROBANTES", "ASIENTO", "ASIENTOS", "SALDO",
    "SALDOS", "ESTADO", "ESTADOS", "FINANCIERO", "FINANCIEROS", "RESULTADOS",
    "SITUACION", "INFORME", "REPORTE", "RELACION", "LISTADO", "LISTA", "RESUMEN",
    "VENTAS", "COMPRAS", "GASTOS", "INGRESOS", "EGRESOS", "CARTERA", "NOMINA",
    "INVENTARIO", "INVENTARIOS", "KARDEX", "FACTURACION", "PAGOS", "COBROS",
    # tipo de documento
    "RUT", "CAMARA", "COMERCIO", "ESTATUTOS", "ACTA", "ACTAS", "CERTIFICADO",
    "CERTIFICACION", "CONSTITUCION", "CEDULA", "CARTA", "CARTAS", "ANEXO", "SOPORTE",
    "SOPORTES", "FORMATO", "FORMULARIO", "PLANTILLA", "DECLARACION",
    # tiempo
    "ENERO", "FEBRERO", "MARZO", "ABRIL", "MAYO", "JUNIO", "JULIO", "AGOSTO",
    "SEPTIEMBRE", "SETIEMBRE", "OCTUBRE", "NOVIEMBRE", "DICIEMBRE", "TRIMESTRE",
    "SEMESTRE", "BIMESTRE", "PERIODO", "PERIODOS", "ANUAL", "MENSUAL", "VIGENCIA",
    # ruido de escritorio
    "COPIA", "COPY", "FINAL", "NUEVO", "NUEVA", "VERSION", "ULTIMO", "ULTIMA",
    "REVISADO", "CORREGIDO", "ORIGINAL", "BORRADOR", "ARCHIVO", "DATOS", "EXCEL",
    "DOCUMENTO", "DOCUMENTOS", "SCAN", "ESCANEADO", "IMG", "DOC", "PDF", "XLS", "XLSX",
}


def nombre_desde_archivo(archivo: str) -> str:
    """«CONTABILIDAD_TIENDA_JUAN_PEREZ_2026.xlsx» → «JUAN PEREZ».

    Es una SUGERENCIA: siempre se muestra para que el contador la confirme.
    """
    base = re.sub(r"\.[A-Za-z0-9]{1,5}$", "", archivo or "")
    base = _normalizar(base.replace("_", " ").replace("-", " "))
    palabras = [p for p in base.split() if p]
    utiles = [
        p for p in palabras
        if p not in _RUIDO_ARCHIVO
        and not re.fullmatch(r"(19|20)\d{2}", p)       # años
        and not re.fullmatch(r"V?\d{1,3}", p)          # v1, 02, 2
    ]
    # Conectores que quedan sueltos al quitar el ruido («ventas y compras JUAN» → «Y JUAN»).
    conectores = {"Y", "E", "O", "DE", "DEL", "A", "EN", "CON", "PARA", "POR"}
    while utiles and utiles[0] in conectores:
        utiles.pop(0)
    while utiles and utiles[-1] in conectores:
        utiles.pop()

    limpio = " ".join(utiles).strip()
    if len(limpio) < 3:
        # Si todo era ruido, se devuelve el nombre entero menos la extensión.
        limpio = " ".join(palabras).strip()
    if re.fullmatch(r"[\d\s]+", limpio):
        return ""   # «RUT_900123456.pdf»: eso es un número, no un nombre
    return limpio[:120]


# ── lectura de hojas de cálculo ─────────────────────────────────────────────
_ETIQUETAS_NOMBRE = ("RAZON SOCIAL", "NOMBRE O RAZON SOCIAL", "RAZON SOCIAL O NOMBRE",
                     "EMPRESA", "NOMBRE DE LA EMPRESA", "CLIENTE", "NOMBRE", "CONTRIBUYENTE")

# Nombres de COLUMNA. Si a la derecha de «NOMBRE» hay uno de estos, la fila es el
# encabezado de una tabla («NOMBRE | CÉDULA | CARGO»), no «etiqueta: valor».
_ETIQUETAS_CAMPO = {
    "CEDULA", "C C", "CC", "NIT", "DOCUMENTO", "IDENTIFICACION", "CARGO", "SALARIO",
    "SUELDO", "DIAS", "VALOR", "TOTAL", "FECHA", "DIRECCION", "TELEFONO", "CORREO",
    "EMAIL", "CIUDAD", "MUNICIPIO", "CODIGO", "CUENTA", "DEBITO", "CREDITO", "SALDO",
    "CANTIDAD", "PRECIO", "CONCEPTO", "DETALLE", "DESCRIPCION", "TIPO", "ESTADO",
    "IVA", "SUBTOTAL", "RETENCION", "FACTURA", "DOCUMENTO SOPORTE", "VENCIMIENTO",
}


def de_hoja(hoja, identidad: Identidad, *, filas_max: int = 25) -> None:
    """Busca NIT y razón social en las primeras filas de una hoja de cálculo.

    Se miran pocas filas a propósito: la identidad vive en el encabezado del
    documento, no entre los movimientos.
    """
    alto = min(hoja.nfilas, filas_max)
    for r in range(alto):
        textos = hoja.fila_textos(r)
        linea = " ".join(t for _, t in textos)
        if not linea.strip():
            continue

        hallado = documento_en_texto(linea)
        if hallado and hallado[0] == "nit":
            identidad.poner("nit", hallado[1], hoja.origen(r), SEGURO)
            if hallado[2]:
                identidad.poner("dv", hallado[2], hoja.origen(r), SEGURO)

        # Una fila ANCHA es una fila de tabla, no una línea de identidad:
        #   · «NOMBRE | CÉDULA | CARGO | SALARIO» titula columnas de una nómina;
        #   · «05/01 | 110505 | CLIENTE EJEMPLO S.A.S. | 500.000» es un
        #     movimiento, y ese nombre es el de un tercero, no el de la empresa.
        # La identidad va sola en su renglón, con la etiqueta y poco más.
        llenas = sum(1 for _, t in textos if t.strip())
        if llenas > 3:
            continue

        for c, texto in textos:
            etiqueta = _normalizar(texto)
            if etiqueta in _ETIQUETAS_NOMBRE:
                # El valor está a la derecha de la etiqueta, o debajo.
                for cc in range(c + 1, min(c + 4, hoja.ncols)):
                    valor = hoja.texto(r, cc).strip()
                    normal = _normalizar(valor)
                    if not valor or normal in _ETIQUETAS_NOMBRE or normal in _ETIQUETAS_CAMPO:
                        continue
                    identidad.poner("razon_social", valor, hoja.origen(r, cc), SEGURO)
                    break
            elif parece_razon_social(texto):
                identidad.poner("razon_social", _limpiar_nombre(texto), hoja.origen(r, c), PROBABLE)


def de_texto(texto: str, origen: str, identidad: Identidad) -> None:
    """Busca identidad en texto plano (párrafos de Word, páginas de PDF).

    Se recorre línea por línea para poder decir en cuál estaba el dato, y
    porque el NIT de la sociedad suele ir junto a su nombre, arriba del todo.
    """
    nombres: list[tuple[int, str, str]] = []      # (línea, valor, origen)
    nits: list[tuple[int, str, str, str]] = []     # (línea, numero, dv, origen)
    cedulas: list[tuple[int, str, str, str]] = []

    for n, linea in enumerate((texto or "").splitlines(), start=1):
        linea = linea.strip()
        if not linea:
            continue
        donde = f"{origen}, línea {n}"
        hallado = documento_en_texto(linea)
        if hallado:
            clase, numero, dv = hallado
            (nits if clase == "nit" else cedulas).append((n, numero, dv, donde))
        if parece_razon_social(linea) and len(linea) <= 120:
            nombres.append((n, _limpiar_nombre(linea), donde))
        else:
            # El nombre puede ir embebido en la redacción del documento.
            for encontrado in razones_sociales_en_texto(linea)[:1]:
                nombres.append((n, encontrado, donde))

    if not nombres and not nits and not cedulas:
        return

    # El nombre de la sociedad y su NIT suelen ir juntos o a un par de líneas.
    # Se elige la pareja más cercana; si no hay nombre, el primer NIT.
    if nombres and nits:
        linea_n, nombre, donde_n = min(
            ((ln, v, o) for ln, v, o in nombres),
            key=lambda x: (min(abs(x[0] - ln2) for ln2, *_ in nits), x[0]),
        )
        linea_i, numero, dv, donde_i = min(nits, key=lambda x: (abs(x[0] - linea_n), x[0]))
        identidad.poner("razon_social", nombre, donde_n, PROBABLE)
        identidad.poner("nit", numero, donde_i, SEGURO)
        if dv:
            identidad.poner("dv", dv, donde_i, SEGURO)
        return

    if nombres:
        linea_n, nombre, donde_n = nombres[0]
        identidad.poner("razon_social", nombre, donde_n, PROBABLE)
    if nits:
        _, numero, dv, donde_i = nits[0]
        identidad.poner("nit", numero, donde_i, SEGURO)
        if dv:
            identidad.poner("dv", dv, donde_i, SEGURO)
    elif cedulas and "nit" not in identidad.campos and not nombres:
        # Una cédula solo identifica al cliente si no hay NIT ni razón social:
        # es el caso de la persona natural. En unos estatutos, las cédulas que
        # abundan son las de los socios, y esas no son el cliente.
        _, numero, dv, donde = cedulas[0]
        identidad.poner("nit", numero, donde, SUGERIDO)
        identidad.poner("tipo_persona", "natural", donde, SUGERIDO)


def _limpiar_nombre(linea: str) -> str:
    """Quita lo que acompaña al nombre en la misma línea («… - NIT 900…»)."""
    sin_nit = re.split(r"(?:N\.?\s*I\.?\s*T\.?|NIT|RUT|C\.?\s*C\.?)\b", linea, maxsplit=1,
                       flags=re.IGNORECASE)[0]
    return re.sub(r"\s+", " ", sin_nit).strip(" -–·,;:\t")
