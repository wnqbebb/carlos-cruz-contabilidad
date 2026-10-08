"""Registros auxiliares: listas de ventas, compras, gastos, cartera, cuentas por pagar e inventario.

POR QUÉ EXISTE
Un negocio pequeño no lleva partida doble: lleva LISTAS. «Ventas de enero» con
fecha, cliente, producto y valor; «Compras» con el proveedor; «Cartera» con lo
que le deben; un conteo de la mercancía. Hasta la v2.1 eso caía en «No se
encontraron las columnas obligatorias». Desde la v2.2 se reconoce por su
CONTENIDO (no por el nombre del archivo) y se convierte en asientos.

CÓMO RAZONA
  1. Busca filas de encabezado: una fila con al menos un rol descriptivo
     (fecha, tercero, producto o concepto) y uno de valor (cantidad, precio,
     total, abono, saldo). Puede haber varias por hoja: un bloque por mes.
  2. Decide qué es cada bloque con el título, el nombre de la hoja y los
     encabezados, y lo confirma con la forma de los datos.
  3. Revisa la calidad SIN corregir en silencio: columnas mal rotuladas,
     fechas que no cuadran con el título o están en el futuro, títulos mal
     escritos, datos que solo aparecen en la primera fila, inventario que no
     alcanza, márgenes absurdos, terceros de cartera que no están en ventas.
     Lo que necesita una decisión se vuelve PREGUNTA con respuesta sugerida;
     lo demás, aviso.
  4. Convierte cada registro en un asiento con comprobante propio (VTA-0001,
     CMP-0001, GTO-0001, REC-0001, PAG-0001) y con el origen exacto (archivo,
     hoja y fila), para poder volver a la fila original desde el libro diario.

La conversión mira TODOS los bloques a la vez porque se necesitan entre sí: la
cartera se compara con las ventas, y el costo de lo vendido sale de las compras.
"""
from __future__ import annotations

import calendar
import re
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from decimal import Decimal

from ..modelos import Alerta, ConteoFisico, Empresa, Movimiento, MovInventario, Paquete, SaldoInicial
from ..utils.numeros import CERO, D, NOMBRE_MES, es_numero, normalizar, parse_fecha, pesos, redondear
from . import encabezados as enc
from .base import Deteccion
from .lector import Hoja

FORMATO = "auxiliares"

TIPOS = ("ventas", "compras", "gastos", "cartera", "cxp", "inventario")
NOMBRE_TIPO = {
    "ventas": "Ventas", "compras": "Compras", "gastos": "Gastos", "cartera": "Cartera (cuentas por cobrar)",
    "cxp": "Cuentas por pagar", "inventario": "Inventario",
}

# Palabras que delatan el tipo de una lista. Se buscan en el título del bloque,
# en el nombre de la hoja y en los encabezados, tolerando errores de escritura.
CLAVES = {
    "ventas": ("VENTA", "VENTAS", "VENDIDO", "VENDIDOS", "FACTURACION", "FACTURADO", "INGRESO", "INGRESOS"),
    "compras": ("COMPRA", "COMPRAS", "COMPRADO", "ADQUISICIONES", "PEDIDOS", "SURTIDO"),
    "gastos": ("GASTO", "GASTOS", "EGRESO", "EGRESOS", "COSTOS FIJOS", "OPERATIVOS", "SALIDAS DE CAJA"),
    "cartera": ("CARTERA", "POR COBRAR", "CXC", "DEUDORES", "FIADOS", "FIAO", "CREDITOS CLIENTES", "ME DEBEN"),
    "cxp": ("POR PAGAR", "CXP", "ACREEDORES", "DEUDAS", "OBLIGACIONES", "LE DEBO", "DEBEMOS", "PROVEEDORES",
            "LO QUE DEBO", "LO QUE DEBEMOS"),
    "inventario": ("INVENTARIO", "INVENTARIOS", "EXISTENCIAS", "STOCK", "CONTEO", "BODEGA"),
}

# Cuentas fijas de la conversión (spec v2.2 · 4.3).
CAJA, BANCOS, CLIENTES, PROVEEDORES, COSTOS_POR_PAGAR = "110505", "111005", "130505", "220505", "233595"
INVENTARIO, COSTO_VENTAS, IVA_GENERADO, IVA_DESCONTABLE = "1435", "6135", "240805", "240810"
APERTURA = "3705"   # contrapartida de los saldos de apertura que traen los registros
# Marca de los saldos de apertura que salen de los registros: si el cliente ya
# tiene un cierre anterior, esos saldos ya están en él y no se suman dos veces.
PREFIJO_APERTURA = "Apertura · "
NOMBRE_INGRESO = "Ventas (registros auxiliares)"
CUENTA_INGRESO = "4135"

# Gastos operativos: concepto → cuenta PUC sugerida. El contador la puede cambiar
# en el paso de mapeo, como cualquier otra cuenta.
GASTOS_PUC = [
    (("ARRIENDO", "ARRENDAMIENTO", "ALQUILER", "CANON"), "512010"),
    (("ENERGIA", "LUZ", "ELECTRICIDAD"), "513530"),
    (("AGUA", "ACUEDUCTO", "ALCANTARILLADO"), "513525"),
    (("TELEFONO", "INTERNET", "CELULAR", "PLAN DE DATOS", "MINUTOS"), "513535"),
    (("GAS",), "513555"),
    (("SERVICIOS PUBLICOS", "SERVICIOS"), "513595"),
    (("NOMINA", "SUELDO", "SUELDOS", "SALARIO", "SALARIOS", "JORNAL", "JORNALES", "PAGO EMPLEADOS", "PAGO EMPLEADO",
      "TRABAJADORES", "MANO DE OBRA"), "510506"),
    (("HONORARIOS", "CONTADOR", "ASESORIA", "ABOGADO"), "511095"),
    (("TAXI", "BUS", "PASAJE", "PASAJES"), "519545"),
    (("TRANSPORTE", "FLETE", "FLETES", "ACARREO", "ACARREOS", "ENVIO", "ENVIOS", "DOMICILIO", "DOMICILIOS"), "513550"),
    (("COMBUSTIBLE", "GASOLINA", "ACPM", "DIESEL"), "519535"),
    (("PAPELERIA", "UTILES", "FOTOCOPIAS", "IMPRESIONES"), "519530"),
    (("ASEO", "CAFETERIA", "LIMPIEZA"), "519525"),
    (("MANTENIMIENTO", "REPARACION", "REPARACIONES", "ARREGLO", "ARREGLOS"), "514595"),
    (("PUBLICIDAD", "PROPAGANDA", "VOLANTES"), "523560"),
    (("INDUSTRIA Y COMERCIO", "ICA", "PREDIAL", "IMPUESTO", "IMPUESTOS"), "511595"),
    (("SEGURO", "SEGUROS", "POLIZA"), "513095"),
    (("BANCARIOS", "COMISION BANCARIA", "COMISIONES BANCARIAS", "4X1000", "GMF", "CUOTA DE MANEJO"), "530505"),
    (("INTERESES",), "530520"),
    (("PARQUEADERO",), "519565"),
    (("RESTAURANTE", "ALIMENTACION", "ALMUERZO", "ALMUERZOS", "REFRIGERIOS"), "519560"),
    (("FUMIGACION", "ABONO", "ABONOS", "FERTILIZANTE", "FERTILIZANTES", "SEMILLAS", "AGROQUIMICOS"), "519595"),
]
OTROS_GASTOS = "519595"

# Formas de pago.
CREDITO_PALABRAS = ("CREDITO", "FIADO", "FIAO", "A CREDITO", "PENDIENTE", "DEBE", "POR COBRAR", "POR PAGAR", "PLAZO")
BANCO_PALABRAS = ("TRANSFERENCIA", "BANCO", "NEQUI", "DAVIPLATA", "CONSIGNACION", "TARJETA", "DATAFONO", "PSE",
                  "BANCOLOMBIA", "CHEQUE")

PALABRAS_TOTAL = ("TOTAL", "TOTALES", "SUBTOTAL", "SUMA", "SUMAS", "GRAN TOTAL", "TOTAL MES", "TOTAL GENERAL")

MESES = {n.upper(): m for m, n in NOMBRE_MES.items()} | {"SETIEMBRE": 9}
MESES_CORTOS = {"ENE": 1, "FEB": 2, "MAR": 3, "ABR": 4, "MAY": 5, "JUN": 6, "JUL": 7, "AGO": 8, "SEP": 9, "SET": 9,
                "OCT": 10, "NOV": 11, "DIC": 12}


# ─────────────────────────────────────────────────────────────── estructuras
@dataclass
class Registro:
    """Una fila de una lista, ya leída pero todavía sin asiento."""
    fila: int
    origen: str
    celdas: list[str]
    fecha: date | None = None
    fecha_archivo: date | None = None     # la que traía el archivo, antes de corregir
    documento: str = ""
    tercero: str = ""
    tercero_id: str = ""
    detalle: str = ""
    cantidad: Decimal | None = None
    unitario: Decimal | None = None
    base: Decimal | None = None
    iva: Decimal | None = None
    total: Decimal | None = None
    abono: Decimal | None = None
    saldo: Decimal | None = None
    forma_pago: str = ""
    excluido: bool = False                        # fecha futura que se deja fuera: todavía no ocurrió
    original: dict = field(default_factory=dict)   # lo leído, para recalcular con otras respuestas

    def guardar(self) -> None:
        self.original = {"fecha": self.fecha, "tercero": self.tercero, "forma_pago": self.forma_pago,
                         "excluido": False}

    def restaurar(self) -> None:
        for k, v in self.original.items():
            setattr(self, k, v)


@dataclass
class Bloque:
    hoja: Hoja
    indice: int                       # número del bloque dentro de la hoja (desde 1)
    fila_encabezado: int
    fin: int                          # fila siguiente a la última del bloque
    columnas: dict[str, int]
    titulo: str = ""
    tipo: str = ""
    c0: int = 0                       # columnas que ocupa el bloque (dos tablas lado a lado)
    c1: int = 10 ** 6
    tipo_leido: str = ""              # lo que se dedujo al leer; `tipo` puede cambiar con una respuesta
    tipo_dudoso: str = ""             # cartera ↔ cxp: el título dice una cosa y la columna otra
    subtipo: str = ""                 # inventario: inicial · fisico
    mes: tuple[int, int] | None = None   # (año, mes) del título
    registros: list[Registro] = field(default_factory=list)
    avisos: list[Alerta] = field(default_factory=list)
    vacios: dict[str, int] = field(default_factory=dict)   # rol → filas vacías bajo una primera llena
    total_archivo: Decimal | None = None
    interpretacion: list[str] = field(default_factory=list)

    @property
    def nombre(self) -> str:
        return self.titulo or f"{self.hoja.nombre} (bloque {self.indice})"


# ─────────────────────────────────────────────────────────────── utilidades
def _texto(v) -> str:
    if v is None:
        return ""
    if isinstance(v, datetime):
        return v.date().isoformat()
    if isinstance(v, date):
        return v.isoformat()
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    return str(v).strip()


def _num(v) -> Decimal | None:
    if v is None or isinstance(v, (date, datetime)) or isinstance(v, bool):
        return None
    if isinstance(v, str) and not v.strip():
        return None
    if not es_numero(v):
        return None
    return D(v)


def _es_texto(v) -> bool:
    return isinstance(v, str) and bool(v.strip()) and not es_numero(v) and parse_fecha(v) is None


def anio_en_texto(texto: str) -> tuple[int | None, str]:
    """Año del título, corrigiendo lo evidente: «2O26» → 2026, «20026» → 2026."""
    t = str(texto or "").upper()
    m = re.search(r"\b(19|20)\d{2}\b", t)
    if m:
        return int(m.group(0)), ""
    m = re.search(r"\b([12][0-9O]{3})\b", t)
    if m and "O" in m.group(1):
        corregido = m.group(1).replace("O", "0")
        if corregido.startswith(("19", "20")):
            return int(corregido), f"«{m.group(1)}» se leyó como {corregido}"
    m = re.search(r"\b(20)(\d)\2(\d{2})\b", t)          # 20026 → 2026 (dígito repetido)
    if m:
        corregido = f"20{m.group(2)}{m.group(3)}"
        return int(corregido), f"«{m.group(0)}» se leyó como {corregido}"
    return None, ""


def mes_en_texto(texto: str) -> tuple[int | None, str]:
    """Mes del título tolerando errores: «ENRO», «FEBERO», «SEPTIMBRE»."""
    t = normalizar(texto)
    for tok in t.split():
        if tok in MESES:
            return MESES[tok], ""
    for tok in t.split():
        if len(tok) >= 4:
            for nombre, n in MESES.items():
                if enc.parecido(tok, nombre) >= 80:
                    return n, f"«{tok}» se leyó como {NOMBRE_MES[n].lower()}"
    return None, ""


def _ultimo_dia(a: int, m: int) -> date:
    return date(a, m, calendar.monthrange(a, m)[1])


def _fecha_celda(v, mes: tuple[int, int] | None) -> date | None:
    """Fecha de una celda: fecha de Excel, texto «05/01/2026», «5-ene» o solo el día."""
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    if v is None:
        return None
    f = parse_fecha(v)
    if f:
        return f
    s = normalizar(v)
    m = re.fullmatch(r"(\d{1,2}) (ENE|FEB|MAR|ABR|MAY|JUN|JUL|AGO|SEP|SET|OCT|NOV|DIC)[A-Z]*(?: (\d{2,4}))?", s)
    if m:
        anio = int(m.group(3)) if m.group(3) else (mes[0] if mes else None)
        if anio and anio < 100:
            anio += 2000
        if anio:
            try:
                return date(anio, MESES_CORTOS[m.group(2)], int(m.group(1)))
            except ValueError:
                return None
    # Solo el día del mes («5»), que es como se lleva una lista mensual.
    if mes and es_numero(v):
        dia = D(v)
        if dia == dia.to_integral_value() and 1 <= dia <= 31:
            try:
                return date(mes[0], mes[1], int(dia))
            except ValueError:
                return None
    return None


def _clave_producto(nombre: str) -> str:
    return normalizar(nombre)


def _palabra_tipo(texto: str) -> dict[str, int]:
    """Cuántas pistas de cada tipo hay en un texto."""
    salida: dict[str, int] = {}
    for tipo, palabras in CLAVES.items():
        if enc.contiene_palabra(texto, palabras):
            salida[tipo] = salida.get(tipo, 0) + 1
    return salida


# ─────────────────────────────────────────────────────────────── detección
_PERMITIDOS = set(enc.SINONIMOS) - {"debito", "credito", "cuenta", "nombre_cuenta"}
_DESCRIPTORES = {"fecha", "tercero", "detalle", "documento"}
_VALORES = {"cantidad", "unitario", "base", "total", "abono", "saldo"}


def _fila_encabezado(h: Hoja, r: int, c0: int = 0, c1: int = 10 ** 6) -> dict[str, int] | None:
    textos = [(c, t) for c, t in h.fila_textos(r) if c0 <= c <= c1 and not es_numero(h.v(r, c))]
    if len(textos) < 2:
        return None
    asignados = enc.mapear_fila(textos, _PERMITIDOS)
    roles = set(asignados)
    # La partida doble tiene su propio importador: aquí no se mete.
    if {"debito", "credito"} & {rol for _, t in textos for rol, _ in enc.roles_de(t)[:1]} and not (_VALORES & roles):
        return None
    if not (roles & _DESCRIPTORES) or not (roles & _VALORES):
        return None
    return {rol: c for rol, (c, _) in asignados.items()}


def _corregir_roles(h: Hoja, cols: dict[str, int], desde: int, hasta: int) -> dict[str, int]:
    """Comprueba que cada columna se comporte como dice su rótulo.

    «PAGO» puede ser un importe (abono) o una forma de pago («contado»): decide
    el contenido. Una columna rotulada como importe que trae textos se suelta.
    """
    def muestra(c: int) -> list:
        return [h.v(r, c) for r in range(desde, min(hasta, desde + 60)) if h.v(r, c) is not None]

    salida = dict(cols)
    for rol, c in list(cols.items()):
        vals = muestra(c)
        if not vals:
            continue
        numericos = sum(1 for v in vals if _num(v) is not None)
        if rol in enc.NUMERICOS and numericos < len(vals) / 2:
            salida.pop(rol)
            if rol == "abono" and "forma_pago" not in salida:
                salida["forma_pago"] = c
        elif rol == "forma_pago" and numericos >= len(vals) / 2:
            salida.pop(rol)
            if "abono" not in salida:
                salida["abono"] = c
    return salida


def _titulo_de(h: Hoja, r_enc: int, tope: int, c0: int = 0, c1: int = 10 ** 6) -> tuple[str, int | None]:
    """Título del bloque: la fila de texto más cercana encima del encabezado."""
    for r in range(r_enc - 1, max(tope, r_enc - 4) - 1, -1):
        textos = [h.texto(r, c) for c, _ in h.fila_textos(r) if c0 <= c <= c1]
        numeros = [v for v in (h.valores[r][c0:c1 + 1] if r < h.nfilas else []) if _num(v) is not None]
        if textos and len(textos) <= 3 and not numeros:
            return " ".join(textos), r
    return "", None


def _segmentos(h: Hoja, r: int) -> list[tuple[int, int]]:
    """Grupos de celdas llenas separados por al menos una columna vacía."""
    cols = [c for c, _ in h.fila_textos(r)] + [c for c, v in enumerate(h.valores[r] if r < h.nfilas else [])
                                                 if v is not None and not isinstance(v, str)]
    cols = sorted(set(cols))
    grupos: list[tuple[int, int]] = []
    for c in cols:
        if grupos and c == grupos[-1][1] + 1:
            grupos[-1] = (grupos[-1][0], c)
        else:
            grupos.append((c, c))
    return grupos


def _encabezados_de_fila(h: Hoja, r: int) -> list[tuple[int, int, dict[str, int]]]:
    """Encabezados de una fila: uno, o varios si hay tablas lado a lado.

    Ventas en A:E y compras en G:K, con una columna vacía en medio, es una forma
    muy común de llevar el mes en una sola hoja. Se parte la fila solo si CADA
    parte es por sí sola un encabezado completo; si no, una columna vacía dentro
    de una misma tabla la partiría por error.
    """
    segs = _segmentos(h, r)
    if len(segs) >= 2:
        partes = []
        for c0, c1 in segs:
            cols = _fila_encabezado(h, r, c0, c1)
            if cols:
                partes.append((c0, c1, cols))
        if len(partes) >= 2:
            # Cada tabla llega hasta justo antes de la siguiente.
            salida = []
            for i, (c0, _c1, cols) in enumerate(partes):
                fin = partes[i + 1][0] - 1 if i + 1 < len(partes) else 10 ** 6
                salida.append((c0, fin, cols))
            return salida
    cols = _fila_encabezado(h, r)
    return [(0, 10 ** 6, cols)] if cols else []


def detectar(h: Hoja) -> list[Bloque]:
    """Bloques de registros auxiliares en una hoja. Vacío si no los hay."""
    encabezados: list[tuple[int, int, int, dict[str, int]]] = []
    for r in range(h.nfilas):
        for c0, c1, cols in _encabezados_de_fila(h, r):
            encabezados.append((r, c0, c1, cols))
    if not encabezados:
        return []

    def se_cruzan(a: tuple[int, int], b: tuple[int, int]) -> bool:
        return a[0] <= b[1] and b[0] <= a[1]

    bloques: list[Bloque] = []
    for i, (r_enc, c0, c1, cols) in enumerate(encabezados):
        # El bloque termina donde empieza el siguiente encabezado de SU carril de columnas.
        siguiente = next((e for e in encabezados[i + 1:] if e[0] > r_enc and se_cruzan((c0, c1), (e[1], e[2]))), None)
        fin = siguiente[0] if siguiente else h.nfilas
        previo = next((e for e in reversed(encabezados[:i]) if e[0] < r_enc and se_cruzan((c0, c1), (e[1], e[2]))), None)
        tope = previo[0] + 1 if previo else 0
        titulo, _ = _titulo_de(h, r_enc, tope, c0, c1)
        # El título del bloque siguiente no es una fila de datos de este.
        if siguiente:
            _, r_sig = _titulo_de(h, siguiente[0], r_enc + 1, siguiente[1], siguiente[2])
            if r_sig is not None:
                fin = r_sig
        cols = _corregir_roles(h, cols, r_enc + 1, fin)
        if not (set(cols) & _VALORES):
            continue
        bloques.append(Bloque(h, len(bloques) + 1, r_enc, fin, cols, titulo, c0=c0, c1=c1))
    return bloques


def _clasificar(b: Bloque, contexto_hoja: str, contexto_archivo: str = "") -> str:
    pistas: dict[str, float] = defaultdict(float)
    for tipo, n in _palabra_tipo(b.titulo).items():
        pistas[tipo] += 3 * n
    for tipo, n in _palabra_tipo(contexto_hoja).items():
        pistas[tipo] += 2 * n
    # El nombre del archivo es la pista más débil: «VENTAS ENERO.xlsx» con una
    # sola tabla «FECHA | DETALLE | VALOR» no dice más que eso.
    for tipo, n in _palabra_tipo(contexto_archivo).items():
        pistas[tipo] += 1 * n
    enc_tercero = normalizar(b.hoja.texto(b.fila_encabezado, b.columnas["tercero"])) if "tercero" in b.columnas else ""
    enc_detalle = normalizar(b.hoja.texto(b.fila_encabezado, b.columnas["detalle"])) if "detalle" in b.columnas else ""
    if enc.contiene_palabra(enc_tercero, ("CLIENTE", "COMPRADOR", "DEUDOR", "VENDIDO A", "QUIEN DEBE")):
        pistas["ventas"] += 1.5
        pistas["cartera"] += 1.5
    if enc.contiene_palabra(enc_tercero, ("PROVEEDOR", "ACREEDOR", "COMPRADO A", "A QUIEN SE DEBE", "BENEFICIARIO",
                                          "PAGADO A")):
        pistas["compras"] += 1.5
        pistas["cxp"] += 1.5
        pistas["gastos"] += 0.5
    if enc.contiene_palabra(enc_detalle, ("CONCEPTO", "GASTO", "TIPO DE GASTO", "RUBRO")):
        pistas["gastos"] += 1.5

    tiene = set(b.columnas)
    if tiene & {"abono", "saldo"} and not tiene & {"cantidad", "unitario"}:
        # Una lista con abonos o saldos es cartera o cuentas por pagar. El nombre de
        # la hoja y el título del bloque pesan más que el rótulo de una columna:
        # «CUENTAS POR PAGAR» con una columna «CLIENTE» sigue siendo por pagar.
        fuerte = {t: _palabra_tipo(b.titulo).get(t, 0) + _palabra_tipo(contexto_hoja).get(t, 0)
                  for t in ("cartera", "cxp")}
        col_cartera = enc.contiene_palabra(enc_tercero, ("CLIENTE", "COMPRADOR", "DEUDOR", "VENDIDO A", "QUIEN DEBE"))
        col_cxp = enc.contiene_palabra(enc_tercero, ("PROVEEDOR", "ACREEDOR", "COMPRADO A", "A QUIEN SE DEBE",
                                                     "BENEFICIARIO", "PAGADO A"))
        if fuerte["cxp"] and not fuerte["cartera"]:
            if col_cartera and not col_cxp:
                b.tipo_dudoso = "cartera"
            return "cxp"
        if fuerte["cartera"] and not fuerte["cxp"]:
            if col_cxp and not col_cartera:
                b.tipo_dudoso = "cxp"
            return "cartera"
        return "cxp" if pistas["cxp"] + pistas["compras"] > pistas["cartera"] + pistas["ventas"] else "cartera"
    if pistas.get("inventario", 0) >= 2 and "cantidad" in tiene and "tercero" not in tiene:
        return "inventario"
    if not ({"fecha", "tercero"} & tiene) and {"detalle", "cantidad"} <= tiene and tiene & {"unitario", "total"} \
            and max((pistas[t] for t in ("ventas", "compras", "gastos")), default=0) < 2:
        return "inventario"
    candidatos = {t: pistas[t] for t in ("ventas", "compras", "gastos") if pistas[t] > 0}
    if not candidatos:
        return ""
    return max(candidatos, key=lambda t: (candidatos[t], t == "ventas"))


def _comportamiento(b: Bloque, filas: list[int]) -> None:
    """Interpreta las columnas por cómo se comportan sus números (4.2 · 1).

    Si total = A × B en casi todas las filas, A y B son cantidad y valor
    unitario aunque el rótulo diga otra cosa. Se avisa siempre qué se hizo.
    """
    h = b.hoja
    numericas = []
    for c in range(b.c0, min(h.ncols, b.c1 + 1)):
        vals = [_num(h.v(r, c)) for r in filas]
        llenos = [v for v in vals if v is not None]
        if len(llenos) >= max(2, len(filas) * 0.6):
            numericas.append(c)
    if len(numericas) < 3 or len(filas) < 2:
        return

    def rotulo(c: int) -> str:
        return h.texto(b.fila_encabezado, c) or f"columna {c + 1}"

    def cumple(a: int, bb: int, t: int) -> int:
        n = 0
        for r in filas:
            x, y, z = _num(h.v(r, a)), _num(h.v(r, bb)), _num(h.v(r, t))
            if x is not None and y is not None and z is not None and z != 0 and abs(x * y - z) <= 1:
                n += 1
        return n

    def es_cantidad(c: int) -> float:
        """Qué tanto parece cantidad: enteros pequeños, no miles de pesos."""
        vals = [_num(h.v(r, c)) for r in filas]
        vals = [v for v in vals if v is not None]
        enteros = sum(1 for v in vals if v == v.to_integral_value())
        mediana = sorted(vals)[len(vals) // 2] if vals else CERO
        return enteros / max(len(vals), 1) - float(mediana > 1000)

    cols = b.columnas
    actual = (cols.get("cantidad"), cols.get("unitario"), cols.get("total"))
    if None not in actual and cumple(*actual) >= len(filas) * 0.8:
        # La multiplicación cuadra en los dos sentidos: el tamaño de los números
        # dice cuál es la cantidad. «CANTIDAD» = 12.500 y «VALOR UNITARIO» = 2
        # es una columna cruzada, no doce mil quinientas unidades.
        c_cant, c_unit, _ = actual
        if es_cantidad(c_unit) - es_cantidad(c_cant) >= 1:
            cols["cantidad"], cols["unitario"] = c_unit, c_cant
            texto = (f"«{b.nombre}»: las columnas «{rotulo(c_cant)}» y «{rotulo(c_unit)}» parecen cruzadas "
                     f"(«{rotulo(c_cant)}» trae valores en pesos y «{rotulo(c_unit)}» cantidades pequeñas): "
                     f"se tomó «{rotulo(c_unit)}» como cantidad y «{rotulo(c_cant)}» como valor unitario.")
            b.interpretacion.append(texto)
            b.avisos.append(Alerta("AUX-COLUMNAS", "advertencia", texto, origen=h.origen(b.fila_encabezado)))
        return
    mejor, mejor_n = None, 0
    for t in numericas:
        for i, a in enumerate(numericas):
            for bb in numericas[i + 1:]:
                if t in (a, bb):
                    continue
                n = cumple(a, bb, t)
                if n > mejor_n:
                    mejor, mejor_n = (a, bb, t), n
    if not mejor or mejor_n < len(filas) * 0.8:
        return
    a, bb, t = mejor
    cant, unit = (a, bb) if es_cantidad(a) >= es_cantidad(bb) else (bb, a)
    nuevas = {"cantidad": cant, "unitario": unit, "total": t}
    cambios = []
    for rol, c in nuevas.items():
        if cols.get(rol) != c:
            cambios.append(f"«{rotulo(c)}» como {({'cantidad': 'cantidad', 'unitario': 'valor unitario', 'total': 'total'})[rol]}")
    if not cambios:
        return
    for rol in list(cols):
        if cols[rol] in nuevas.values() and rol not in nuevas:
            cols.pop(rol)
    cols.update(nuevas)
    texto = (f"«{b.nombre}»: se interpretó " + ", ".join(cambios)
             + f", porque «{rotulo(t)}» = «{rotulo(cant)}» × «{rotulo(unit)}» en {mejor_n} de {len(filas)} filas.")
    b.interpretacion.append(texto)
    b.avisos.append(Alerta("AUX-COLUMNAS", "advertencia", texto, origen=h.origen(b.fila_encabezado)))


def _anio_de_fechas(b: Bloque) -> int | None:
    """Año más frecuente entre las fechas completas del bloque."""
    if "fecha" not in b.columnas:
        return None
    anios = [f.year for r in range(b.fila_encabezado + 1, b.fin)
             if (f := _fecha_celda(b.hoja.v(r, b.columnas["fecha"]), None))]
    return max(set(anios), key=anios.count) if anios else None


def leer_bloque(b: Bloque, contexto_hoja: str, anio_defecto: int | None, contexto_archivo: str = "") -> None:
    """Llena los registros del bloque, aplicando las tolerancias de 4.1."""
    h = b.hoja
    mes, aviso_mes = mes_en_texto(b.titulo)
    anio, aviso_anio = anio_en_texto(b.titulo)
    origen_mes = "título"
    if not mes:
        # Una hoja por mes («ENERO», «FEB 2026») sin título encima de la tabla.
        mes, _ = mes_en_texto(contexto_hoja)
        anio = anio or anio_en_texto(contexto_hoja)[0]
        origen_mes = "nombre de la hoja"
    if mes and not anio:
        anio = _anio_de_fechas(b) or anio_defecto
        if not anio:
            anio = date.today().year
            b.avisos.append(Alerta("AUX-TITULO", "info",
                                   f"«{b.titulo or h.nombre}» dice el mes pero no el año: se asumió {anio}.",
                                   origen=h.origen(b.fila_encabezado)))
    if mes and anio:
        b.mes = (anio, mes)
    if aviso_mes or aviso_anio:
        detalle = "; ".join(x for x in (aviso_mes, aviso_anio) if x)
        b.avisos.append(Alerta("AUX-TITULO", "info",
                               f"Título «{b.titulo}»: {detalle}. Si no es así, corrija el título y vuelva a subirlo.",
                               origen=h.origen(b.fila_encabezado)))
    if b.mes and origen_mes != "título":
        b.interpretacion.append(f"Mes tomado del {origen_mes}: {NOMBRE_MES[b.mes[1]].lower()} de {b.mes[0]}.")
    b.tipo = b.tipo_leido = _clasificar(b, contexto_hoja, contexto_archivo)
    if b.tipo == "inventario":
        t = normalizar(f"{b.titulo} {contexto_hoja}")
        if enc.contiene_palabra(t, ("INICIAL", "APERTURA", "ANTERIOR")):
            b.subtipo = "inicial"
        elif enc.contiene_palabra(t, ("FINAL", "FISICO", "CONTEO", "CIERRE", "CONTADO")):
            b.subtipo = "fisico"

    # Filas de datos (sin vacías, sin totales, sin filas en cero).
    datos: list[int] = []
    cols = b.columnas
    valor_cols = [c for rol, c in cols.items() if rol in _VALORES]
    suma = CERO
    for r in range(b.fila_encabezado + 1, b.fin):
        fila = (h.valores[r] if r < h.nfilas else [])[b.c0:b.c1 + 1]
        if not any(v is not None and str(v).strip() for v in fila):
            continue
        textos = " ".join(normalizar(v) for v in fila if isinstance(v, str))
        if any(re.search(rf"\b{p}\b", textos) for p in PALABRAS_TOTAL):
            t = _num(h.v(r, cols["total"])) if "total" in cols else None
            if t is not None:
                b.total_archivo = t
            continue
        nums = [_num(h.v(r, c)) for c in valor_cols]
        nums = [n for n in nums if n is not None]
        if not nums:
            continue
        if all(n == 0 for n in nums):
            continue                                   # fórmula en cero o fila sin valor
        descriptores = [h.v(r, cols[k]) for k in ("tercero", "detalle", "documento") if k in cols]
        sin_descripcion = not any(v is not None and str(v).strip() for v in descriptores) and \
            not ("fecha" in cols and h.v(r, cols["fecha"]) is not None)
        t = _num(h.v(r, cols["total"])) if "total" in cols else nums[-1]
        if sin_descripcion and t is not None and suma and t == suma:
            b.total_archivo = t                           # subtotal sin rótulo
            continue
        datos.append(r)
        suma += t or CERO

    if not datos:
        return
    _comportamiento(b, datos)
    cols = b.columnas

    # Datos que solo aparecen en la primera fila (4.2 · 4).
    for rol in ("forma_pago", "tercero", "fecha"):
        if rol in cols and len(datos) >= 3:
            primero = h.v(datos[0], cols[rol])
            vacios = sum(1 for r in datos[1:] if h.v(r, cols[rol]) is None)
            if primero is not None and vacios >= (len(datos) - 1) * 0.6 and vacios:
                b.vacios[rol] = vacios

    for r in datos:
        fila = (h.valores[r] if r < h.nfilas else [])[b.c0:b.c1 + 1]
        reg = Registro(r, h.origen(r), [_texto(v) for v in fila])
        g = lambda rol: h.v(r, cols[rol]) if rol in cols else None  # noqa: E731
        reg.fecha = reg.fecha_archivo = _fecha_celda(g("fecha"), b.mes)
        reg.documento = _texto(g("documento"))
        reg.tercero = _texto(g("tercero")) if not es_numero(g("tercero")) else ""
        reg.tercero_id = _texto(g("tercero_id"))
        reg.detalle = _texto(g("detalle"))
        reg.cantidad = _num(g("cantidad"))
        reg.unitario = _num(g("unitario"))
        reg.base = _num(g("base"))
        reg.iva = _num(g("iva"))
        reg.total = _num(g("total"))
        reg.abono = _num(g("abono"))
        reg.saldo = _num(g("saldo"))
        reg.forma_pago = normalizar(g("forma_pago"))
        if reg.total is None:
            if reg.base is not None:
                reg.total = reg.base + (reg.iva or CERO)
            elif reg.cantidad is not None and reg.unitario is not None:
                reg.total = redondear(reg.cantidad * reg.unitario, 2)
            elif b.tipo in ("cartera", "cxp") and (reg.abono is not None or reg.saldo is not None):
                reg.total = (reg.abono or CERO) + (reg.saldo or CERO)
            elif reg.unitario is not None and reg.cantidad is None and b.tipo != "inventario":
                reg.total = reg.unitario
        if b.tipo == "inventario" and reg.total is None and reg.cantidad is not None and reg.unitario is not None:
            reg.total = redondear(reg.cantidad * reg.unitario, 2)
        reg.guardar()
        b.registros.append(reg)

    calculado = sum((x.total or CERO for x in b.registros), CERO)
    if b.total_archivo is not None and b.total_archivo != calculado:
        b.avisos.append(Alerta(
            "AUX-TOTAL", "info",
            f"«{b.nombre}»: el total escrito en el archivo es {pesos(b.total_archivo)} y la suma de las filas da "
            f"{pesos(calculado)}. Se usan las filas, una por una.", origen=h.origen(b.fila_encabezado)))


# ─────────────────────────────────────────────────────────────── por hoja
def importar_hoja(h: Hoja, id_: str, anio_defecto: int | None = None) -> Deteccion | None:
    """Deteccion de una hoja con registros auxiliares, o None si no los tiene.

    Aquí solo se leen y se clasifican los bloques. Los asientos se arman en
    `convertir`, que ve todas las hojas a la vez.
    """
    bloques = detectar(h)
    if not bloques:
        return None
    contexto = h.nombre if h.nombre not in ("(texto)",) else ""
    archivo = re.sub(r"\.[A-Za-z0-9]{1,5}$", "", h.archivo or "").replace("_", " ")
    # Año por defecto: el de las fechas de la propia hoja, si no lo dice el título.
    if anio_defecto is None:
        for b in bloques:
            a, _ = anio_en_texto(b.titulo)
            if a:
                anio_defecto = a
                break
    for b in bloques:
        leer_bloque(b, contexto, anio_defecto, archivo)
    # Una lista sin tipo claro se conserva si es de movimientos (tiene fechas):
    # se pregunta qué es en vez de ignorarla. Una tabla sin fechas y sin tipo
    # (los socios de unos estatutos) no es contabilidad.
    utiles = [b for b in bloques if b.registros and (b.tipo or "fecha" in b.columnas)]
    if not utiles:
        return None
    tipos = sorted({b.tipo for b in utiles if b.tipo}, key=TIPOS.index)
    resumen = {
        "tipos": tipos,
        "bloques": [{"titulo": b.nombre, "tipo": b.tipo, "nombre_tipo": NOMBRE_TIPO.get(b.tipo, "Por definir"),
                     "filas": len(b.registros),
                     "mes": f"{b.mes[0]}-{b.mes[1]:02d}" if b.mes else None, "subtipo": b.subtipo,
                     "interpretacion": b.interpretacion} for b in utiles],
        "registros": sum(len(b.registros) for b in utiles),
        "movimientos": 0,
    }
    sin_tipo = sum(1 for b in utiles if not b.tipo)
    motivo = ("Registros auxiliares: " + ", ".join(NOMBRE_TIPO[t].lower() for t in tipos)) if tipos else "Registros auxiliares"
    if sin_tipo:
        motivo += f" · {sin_tipo} lista(s) sin tipo claro: se pregunta qué son"
    d = Deteccion(id_, h.archivo, h.nombre, FORMATO, True, motivo, resumen, Paquete())
    d.bloques = utiles                    # type: ignore[attr-defined]
    for b in bloques:
        if b not in utiles and b.registros == [] and b.tipo:
            d.paquete.alertas.append(Alerta("AUX-VACIO", "info", f"«{b.nombre}» tiene encabezados pero ninguna fila con valores."))
    return d


def hoja_promete(h: Hoja) -> str:
    """Tipo de registro que el nombre de la hoja promete («COMPRAS»), para avisar si no lo trae."""
    pistas = _palabra_tipo(h.nombre)
    return max(pistas, key=pistas.get) if pistas else ""


# ─────────────────────────────────────────────────────────────── preguntas
def _pregunta(id_: str, hoja: str, titulo: str, detalle: str, opciones: list[tuple[str, str]], defecto: str,
              clase: str) -> dict:
    return {"id": id_, "hoja": hoja, "clase": clase, "titulo": titulo, "detalle": detalle,
            "opciones": [{"valor": v, "etiqueta": e} for v, e in opciones], "defecto": defecto}


def _hoy() -> date:
    return date.today()


def _corregir_futura(f: date, rango: tuple[date, date] | None) -> date | None:
    """Candidata para una fecha futura: día y mes cruzados si así cae dentro del rango."""
    if f.day <= 12:
        try:
            cruzada = date(f.year, f.day, f.month)
        except ValueError:
            cruzada = None
        if cruzada and cruzada <= _hoy() and (not rango or rango[0] <= cruzada <= rango[1] + timedelta(days=31)):
            return cruzada
    return None


@dataclass
class Conversion:
    paquetes: dict[str, Paquete]
    preguntas: list[dict]
    meses: list[str]
    desde: date | None
    hasta: date | None
    origenes: dict[str, list[str]]
    mapeo_sugerido: dict[str, str]
    estado_inventario: dict = field(default_factory=dict)


def convertir(dets: list[Deteccion], respuestas: dict[str, str] | None, empresa: Empresa | None) -> Conversion | None:
    """Convierte todos los bloques auxiliares en asientos, con preguntas y avisos."""
    respuestas = respuestas or {}
    empresa = empresa or Empresa()
    propias = [d for d in dets if d.formato == FORMATO and getattr(d, "bloques", None)]
    if not propias:
        return None
    preguntas: list[dict] = []
    alertas: dict[str, list[Alerta]] = defaultdict(list)
    hoy = _hoy()
    # Cada conversión parte de lo leído: las respuestas anteriores no se acumulan.
    for d in propias:
        for b in d.bloques:
            b.tipo = b.tipo_leido
            for r in b.registros:
                r.restaurar()

    def responder(p: dict) -> str:
        preguntas.append(p)
        valor = respuestas.get(p["id"], p["defecto"])
        validos = {o["valor"] for o in p["opciones"]}
        return valor if valor in validos else p["defecto"]

    # La misma pregunta en muchos bloques se hace una sola vez (B3): «En 11 bloques
    # la forma de pago solo aparece en la primera fila». La respuesta de un bloque
    # concreto (su id de siempre) manda sobre la del grupo.
    grupos: dict[tuple, dict] = {}
    orden: list = []

    def responder_grupo(clave: tuple, p: dict, titulo_grupo: str) -> str:
        validos = {o["valor"] for o in p["opciones"]}
        llave = (clave, tuple(sorted(validos)), p["defecto"])
        if llave not in grupos:
            gid = "grupo:" + ":".join(str(x) for x in clave) + f":{p['defecto']}"
            grupos[llave] = {"id": gid, "titulo": titulo_grupo, "base": p, "bloques": []}
            orden.append(("grupo", llave))
        g = grupos[llave]
        g["bloques"].append({"id": p["id"], "lugar": p["hoja"], "titulo": p["titulo"], "detalle": p["detalle"]})
        valor = respuestas.get(p["id"]) or respuestas.get(g["id"]) or p["defecto"]
        return valor if valor in validos else p["defecto"]

    # 0 · Listas que no dicen qué son: se pregunta, con una sugerencia prudente.
    for d in propias:
        for b in d.bloques:
            if b.tipo:
                continue
            conceptos = [r.detalle for r in b.registros if r.detalle]
            de_gasto = sum(1 for c in conceptos if _cuenta_gasto(c) != OTROS_GASTOS)
            defecto = "gastos" if conceptos and de_gasto >= len(conceptos) / 2 else "ignorar"
            columnas = ", ".join(b.hoja.texto(b.fila_encabezado, c) for c in sorted(b.columnas.values()))
            b.tipo = responder(_pregunta(
                f"{d.id}:b{b.indice}:tipo", f"{d.archivo} › {d.hoja} › {b.nombre}",
                f"¿Qué es la lista «{b.nombre}»?",
                f"Tiene {len(b.registros)} filas con las columnas {columnas}, pero ni el título, ni la hoja, ni los "
                "encabezados dicen si son ventas, compras o gastos.",
                [("ventas", "Ventas"), ("compras", "Compras"), ("gastos", "Gastos"),
                 ("cartera", "Cartera (lo que le deben)"), ("cxp", "Cuentas por pagar (lo que debe)"),
                 ("ignorar", "No es contabilidad: no la use")], defecto, "tipo"))
            if b.tipo == "ignorar":
                b.tipo = ""

    for d in propias:
        for b in d.bloques:
            if b.tipo in ("cartera", "cxp") and b.tipo_dudoso:
                defecto = b.tipo
                b.tipo = responder(_pregunta(
                    f"{d.id}:b{b.indice}:cartera_o_cxp", f"{d.archivo} › {d.hoja} › {b.nombre}",
                    f"«{b.nombre}»: ¿es lo que le deben al cliente o lo que el cliente debe?",
                    f"El título o la hoja dicen {'cuentas por pagar' if defecto == 'cxp' else 'cartera'}, pero la "
                    f"columna de nombres dice «{b.hoja.texto(b.fila_encabezado, b.columnas.get('tercero', 0))}».",
                    [("cxp", "Lo que el cliente debe (cuentas por pagar a proveedores)"),
                     ("cartera", "Lo que le deben al cliente (cartera de clientes)")], defecto, "tipo"))

    # Rango de fechas que el propio archivo considera normal (sin las futuras).
    todas = [r.fecha_archivo for d in propias for b in d.bloques for r in b.registros
             if r.fecha_archivo and r.fecha_archivo <= hoy]
    rango = (min(todas), max(todas)) if todas else None

    # 1 · Fechas: datos repetidos hacia abajo, fechas que no cuadran con el título y fechas futuras.
    for d in propias:
        for b in d.bloques:
            base_id = f"{d.id}:b{b.indice}"
            lugar = f"{d.archivo} › {d.hoja} › {b.nombre}"
            alertas[d.id].extend(b.avisos)
            if not b.tipo:
                continue                      # lista descartada por el contador
            for rol, n in b.vacios.items():
                etiqueta = {"forma_pago": "la forma de pago", "tercero": "el nombre del tercero", "fecha": "la fecha"}[rol]
                primero = next((r for r in b.registros), None)
                valor = ""
                if primero:
                    valor = {"forma_pago": primero.forma_pago, "tercero": primero.tercero,
                             "fecha": primero.fecha.isoformat() if primero.fecha else ""}[rol]
                r_ = responder_grupo(("repetir", rol), _pregunta(
                    f"{base_id}:repetir:{rol}", lugar,
                    f"¿{etiqueta.capitalize()} «{valor}» aplica a todas las filas?",
                    f"En «{b.nombre}» {etiqueta} solo aparece en la primera fila; {n} filas de abajo la tienen vacía.",
                    [("si", "Sí, aplica a todas las filas de abajo"), ("no", "No, solo a la primera")], "si", "repetir"),
                    f"En {{n}} bloques {etiqueta} solo aparece en la primera fila. ¿Aplica a todas las filas de abajo?")
                if r_ == "si":
                    previo = None
                    for reg in b.registros:
                        actual = getattr(reg, rol) if rol != "fecha" else reg.fecha
                        if actual:
                            previo = actual
                        elif previo is not None:
                            if rol == "fecha":
                                reg.fecha = previo
                            else:
                                setattr(reg, rol, previo)

            titulo_futuro = bool(b.mes) and date(b.mes[0], b.mes[1], 1) > hoy
            if b.mes and not titulo_futuro:
                distintas = [r for r in b.registros if r.fecha and (r.fecha.year, r.fecha.month) != b.mes]
                if distintas:
                    meses_vistos = sorted({(r.fecha.year, r.fecha.month) for r in distintas})
                    texto_meses = ", ".join(f"{NOMBRE_MES[m].lower()} {a}" for a, m in meses_vistos[:4])
                    futuras = sum(1 for r in distintas if r.fecha > hoy)
                    r_ = responder_grupo(("fechas", "titulo"), _pregunta(
                        f"{base_id}:fechas:titulo", lugar,
                        f"¿Qué fecha uso en «{b.nombre}»?",
                        f"{len(distintas)} de {len(b.registros)} filas tienen fecha de {texto_meses}"
                        + (f" ({futuras} en el futuro)" if futuras else "")
                        + f", pero el título dice {NOMBRE_MES[b.mes[1]].lower()} de {b.mes[0]}. "
                          "Suele pasar al copiar las filas de otro mes.",
                        [("titulo", f"La del título: {NOMBRE_MES[b.mes[1]].lower()} de {b.mes[0]}, conservando el día"),
                         ("archivo", "La que trae cada fila")], "titulo", "fechas"),
                        "En {n} bloques hay filas con la fecha de otro mes (suele pasar al copiar filas). "
                        "¿Uso el mes que dice el título de cada bloque?")
                    if r_ == "titulo":
                        for reg in distintas:
                            dia = min(reg.fecha.day, calendar.monthrange(*b.mes)[1])
                            reg.fecha = date(b.mes[0], b.mes[1], dia)
            futuras = [r for r in b.registros if r.fecha and r.fecha > hoy]
            if futuras:
                cruzables = [r for r in futuras if _corregir_futura(r.fecha, rango)]
                opciones = []
                if cruzables and not titulo_futuro:
                    opciones.append(("cruzar", "Cruzar día y mes (por ejemplo 11/05 → 05/11)"))
                opciones.append(("excluir", "Dejar fuera: todavía no ha ocurrido"))
                # «Mismo día y mes del año anterior» solo se ofrece si ese año ya está en el
                # archivo: nunca se inventan periodos de un año que el archivo no menciona (B2).
                anios_archivo = {r.fecha_archivo.year for dd in propias for bb in dd.bloques
                                 for r in bb.registros if r.fecha_archivo and r.fecha_archivo <= hoy}
                if all(r.fecha.year - 1 in anios_archivo for r in futuras):
                    opciones.append(("anio", "Mismo día y mes, del año anterior"))
                opciones.append(("archivo", "Dejarlas como están"))
                defecto = "cruzar" if cruzables and len(cruzables) == len(futuras) and not titulo_futuro else "excluir"
                ejemplo = futuras[0].fecha.isoformat()
                motivo = (f"El título dice {NOMBRE_MES[b.mes[1]].lower()} de {b.mes[0]}, que todavía no ha llegado."
                          if titulo_futuro else "Una venta o una compra no puede tener fecha futura.")
                r_ = responder_grupo(("fechas", "futuras"), _pregunta(
                    f"{base_id}:fechas:futuras", lugar,
                    f"Hay {len(futuras)} fecha(s) en el futuro en «{b.nombre}»",
                    f"Por ejemplo {ejemplo} ({futuras[0].origen}). Hoy es {hoy.isoformat()}. {motivo}",
                    opciones, defecto, "fechas"),
                    "En {n} bloques hay filas con fecha en el futuro. ¿Qué hago con ellas?")
                for reg in futuras:
                    if r_ == "cruzar":
                        reg.fecha = _corregir_futura(reg.fecha, rango) or reg.fecha
                    elif r_ == "excluir":
                        reg.excluido = True
                    elif r_ == "anio":
                        try:
                            reg.fecha = reg.fecha.replace(year=reg.fecha.year - 1)
                        except ValueError:
                            reg.fecha = reg.fecha - timedelta(days=365)
                if r_ == "excluir":
                    alertas[d.id].append(Alerta(
                        "AUX-FECHAS", "info",
                        f"«{b.nombre}»: {len(futuras)} fila(s) con fecha futura quedaron fuera del cálculo "
                        f"(todavía no han ocurrido).", origen=futuras[0].origen))

    # Fecha por defecto de lo que no trae fecha: el mes del bloque o el final del rango.
    fechas = [r.fecha for d in propias for b in d.bloques for r in b.registros if r.fecha and not r.excluido]
    fin_rango = max(fechas) if fechas else None
    ini_rango = min(fechas) if fechas else None
    for d in propias:
        for b in d.bloques:
            sin = [r for r in b.registros if not r.fecha and not r.excluido]
            for reg in sin:
                if b.mes:
                    reg.fecha = date(b.mes[0], b.mes[1], 1) if b.tipo in ("compras", "inventario") \
                        else _ultimo_dia(*b.mes)
                elif b.tipo == "inventario" and b.subtipo != "fisico" and ini_rango:
                    reg.fecha = ini_rango
                else:
                    reg.fecha = fin_rango
            if sin and b.tipo not in ("inventario",):
                cuando = (f"{NOMBRE_MES[b.mes[1]].lower()} de {b.mes[0]}" if b.mes
                          else (fin_rango.isoformat() if fin_rango else "sin fecha"))
                alertas[d.id].append(Alerta("AUX-FECHAS", "info",
                                            f"«{b.nombre}»: {len(sin)} fila(s) sin fecha; se registran en {cuando}."))

    # 2 · Inventario: inicial o conteo físico, si el título no lo dice.
    tiene_ventas_productos = any(b.tipo == "ventas" and any(r.cantidad for r in b.registros)
                                 for d in propias for b in d.bloques)
    for d in propias:
        for b in d.bloques:
            if b.tipo == "inventario" and not b.subtipo:
                defecto = "inicial" if tiene_ventas_productos else "fisico"
                b.subtipo = responder(_pregunta(
                    f"{d.id}:b{b.indice}:inventario", f"{d.archivo} › {d.hoja} › {b.nombre}",
                    f"¿«{b.nombre}» es el inventario con el que se empezó o un conteo al final?",
                    "El título no lo dice. Si es el inicial, entra como saldo de apertura y alimenta el kardex; si es un "
                    "conteo físico, se compara con el kardex y se propone el ajuste por faltantes o sobrantes.",
                    [("inicial", "Inventario inicial (con lo que se empezó)"), ("fisico", "Conteo físico al cierre")],
                    defecto, "inventario"))

    # 3 · Terceros de cartera y cuentas por pagar que no aparecen en ventas o compras.
    def terceros_de(tipo: str) -> set[str]:
        return {normalizar(r.tercero) for d in propias for b in d.bloques if b.tipo == tipo for r in b.registros
                if r.tercero}

    def coincide(nombre: str, conjunto: set[str]) -> bool:
        from rapidfuzz import fuzz

        n = normalizar(nombre)
        return bool(n) and any(n == x or fuzz.token_set_ratio(n, x) >= 90 for x in conjunto)

    ventas_terc, compras_terc = terceros_de("ventas"), terceros_de("compras")
    credito_terc: set[str] = set()
    for d in propias:
        for b in d.bloques:
            for r in b.registros:
                if b.tipo in ("ventas", "compras") and _es_credito(r.forma_pago) and r.tercero:
                    credito_terc.add(normalizar(r.tercero))
    trato_tercero: dict[int, str] = {}         # id(registro) → saldo_anterior | adicional | incluidas | abonos
    for d in propias:
        for b in d.bloques:
            if b.tipo not in ("cartera", "cxp"):
                continue
            base = ventas_terc if b.tipo == "cartera" else compras_terc
            desconocidos = [r for r in b.registros if not coincide(r.tercero, base)]
            if desconocidos:
                nombres = sorted({r.tercero or "(sin nombre)" for r in desconocidos})
                que = "ventas" if b.tipo == "cartera" else "compras"
                r_ = responder_grupo(("terceros", b.tipo), _pregunta(
                    f"{d.id}:b{b.indice}:terceros", f"{d.archivo} › {d.hoja} › {b.nombre}",
                    f"{len(nombres)} tercero(s) de «{b.nombre}» no aparecen en las {que}",
                    "No encontré en las " + que + " a: " + ", ".join(nombres[:8]) + ("…" if len(nombres) > 8 else "")
                    + ". ¿Qué son esos saldos?",
                    [("saldo_anterior", "Saldos que venían de antes (entran como saldo inicial)"),
                     ("adicional", f"{'Ventas' if b.tipo == 'cartera' else 'Compras'} a crédito que no están en la lista (se registran)"),
                     ("incluidas", f"Ya están en las {que} como de contado (se pasan de caja a "
                                   f"{'cartera' if b.tipo == 'cartera' else 'proveedores'})")],
                    "saldo_anterior", "terceros"),
                    f"En {{n}} listas de {'cartera' if b.tipo == 'cartera' else 'cuentas por pagar'} hay terceros que no "
                    f"aparecen en las {que}. ¿Qué son esos saldos?")
                for r in desconocidos:
                    trato_tercero[id(r)] = r_
            for r in b.registros:
                if id(r) in trato_tercero:
                    continue
                trato_tercero[id(r)] = "abonos" if normalizar(r.tercero) in credito_terc or \
                    coincide(r.tercero, credito_terc) else "incluidas"

    for _, llave in orden:
        g = grupos[llave]
        base = g["base"]
        if len(g["bloques"]) == 1:
            preguntas.append(base)
            continue
        n = len(g["bloques"])
        preguntas.append({
            "id": g["id"], "hoja": f"{n} bloques", "clase": base["clase"],
            "titulo": g["titulo"].format(n=n),
            "detalle": "La misma pregunta se repite en varios bloques: se responde una vez. Si algún bloque es distinto, "
                       "respóndalo aparte.",
            "opciones": base["opciones"], "defecto": base["defecto"],
            "bloques": g["bloques"],
        })

    # 4 · IVA: solo se discrimina si el archivo lo trae y la empresa es responsable.
    hay_iva = any(r.iva for d in propias for b in d.bloques for r in b.registros)
    if hay_iva and not empresa.responsable_iva:
        alertas[propias[0].id].append(Alerta(
            "AUX-IVA", "info", "El archivo trae IVA, pero la ficha dice que el cliente no es responsable de IVA: "
                               "el IVA se deja dentro del valor del ingreso o del costo, sin discriminar."))
    elif not hay_iva and empresa.responsable_iva and any(b.tipo in ("ventas", "compras") for d in propias for b in d.bloques):
        alertas[propias[0].id].append(Alerta(
            "AUX-IVA", "info", "Las listas no traen columna de IVA: los valores se registran completos, sin discriminar "
                               "IVA. Si el cliente es responsable y los valores incluyen IVA, agregue la columna."))

    # 5 · Asientos, en orden cronológico.
    paquetes: dict[str, Paquete] = {d.id: Paquete() for d in propias}
    origenes: dict[str, list[str]] = {}
    consecutivo: dict[str, int] = defaultdict(int)

    def comprobante(prefijo: str) -> str:
        consecutivo[prefijo] += 1
        return f"{prefijo}-{consecutivo[prefijo]:04d}"

    items = [(d, b, r) for d in propias for b in d.bloques if b.tipo for r in b.registros if not r.excluido]
    orden_tipo = {"inventario": 0, "compras": 1, "ventas": 2, "gastos": 3, "cartera": 4, "cxp": 5}
    items.sort(key=lambda x: (x[2].fecha or date.min, orden_tipo[x[1].tipo], x[0].id, x[2].fila))

    # Kardex de la conversión: mismo método que el motor (promedio ponderado),
    # para que el costo de cada venta quede en su propio comprobante.
    productos_inv = {_clave_producto(r.detalle) for _, b, r in items
                     if b.tipo in ("compras", "inventario") and r.detalle and r.cantidad}
    estado: dict[str, list[Decimal]] = defaultdict(lambda: [CERO, CERO])     # clave → [cantidad, total]
    nombres_prod: dict[str, str] = {}
    faltantes: dict[tuple[str, int, int], list[Decimal]] = defaultdict(lambda: [CERO, CERO])
    precios: dict[str, list[Decimal]] = defaultdict(lambda: [CERO, CERO])    # ventas: [cantidad, valor]
    costos: dict[str, list[Decimal]] = defaultdict(lambda: [CERO, CERO])     # compras: [cantidad, valor]
    sin_compra: set[str] = set()
    mapeo_sugerido: dict[str, str] = {normalizar(NOMBRE_INGRESO): CUENTA_INGRESO}
    discrimina = empresa.responsable_iva

    def clave_prod(nombre: str) -> str:
        k = _clave_producto(nombre)
        if k in productos_inv:
            return k
        from rapidfuzz import fuzz

        for p in productos_inv:
            if fuzz.token_sort_ratio(k, p) >= 92:
                return p
        return k

    for d, b, reg in items:
        pq = paquetes[d.id]
        origenes[reg.origen] = reg.celdas
        f = reg.fecha
        terc = reg.tercero
        total = reg.total or CERO
        iva = (reg.iva or CERO) if discrimina else CERO
        base = (reg.base if reg.base is not None else total - (reg.iva or CERO)) if discrimina and reg.iva else total

        def mv(cuenta: str, deb: Decimal = CERO, cre: Decimal = CERO, comp: str = "", desc: str = "",
               nombre: str = "", tipo: str = "") -> None:
            if not deb and not cre:
                return
            pq.movimientos.append(Movimiento(cuenta=cuenta, debito=deb, credito=cre, fecha=f, comprobante=comp,
                                             tipo=tipo, nombre_cuenta=nombre, tercero_id=reg.tercero_id,
                                             tercero_nombre=terc, descripcion=desc, origen=reg.origen))

        if b.tipo == "ventas":
            if not total:
                continue
            comp = comprobante("VTA")
            credito = _es_credito(reg.forma_pago)
            contra = CLIENTES if credito else (BANCOS if _es_banco(reg.forma_pago) else CAJA)
            qué = f"{_cant(reg.cantidad)}{reg.detalle}".strip() or "venta"
            desc = f"Venta {'a crédito ' if credito else ''}{qué}" + (f" a {terc}" if terc else "")
            mv(contra, deb=total, comp=comp, desc=desc, tipo="venta")
            mv("", cre=base, comp=comp, desc=desc, nombre=NOMBRE_INGRESO, tipo="venta")
            mv(IVA_GENERADO, cre=iva, comp=comp, desc=f"IVA {desc}", tipo="venta")
            if reg.detalle and reg.cantidad and reg.cantidad > 0:
                k = clave_prod(reg.detalle)
                precios[k][0] += reg.cantidad
                precios[k][1] += base
                if k in productos_inv:
                    nombres_prod.setdefault(k, reg.detalle)
                    q, t = estado[k]
                    vend = min(reg.cantidad, q) if q > 0 else CERO
                    costo = CERO
                    if vend > 0:
                        costo = redondear(vend * (t / q), 2)
                        estado[k] = [q - vend, t - costo]
                        if estado[k][0] == 0 and estado[k][1] != 0:
                            costo += estado[k][1]
                            estado[k][1] = CERO
                        pq.inventario_movs.append(MovInventario(k, "venta", vend, f, comp, reg.detalle,
                                                                precio_venta=redondear(base / reg.cantidad, 2),
                                                                origen=reg.origen))
                        mv(COSTO_VENTAS, deb=costo, comp=comp, desc=f"Costo de {qué}", tipo="venta")
                        mv(INVENTARIO, cre=costo, comp=comp, desc=f"Salida de inventario: {qué}", tipo="venta")
                    if reg.cantidad > vend:
                        falta = faltantes[(k, f.year if f else 0, f.month if f else 0)]
                        falta[0] += reg.cantidad - vend
                        falta[1] += reg.cantidad
                else:
                    sin_compra.add(reg.detalle)

        elif b.tipo == "compras":
            if not total:
                continue
            comp = comprobante("CMP")
            credito = _es_credito(reg.forma_pago)
            contra = PROVEEDORES if credito else (BANCOS if _es_banco(reg.forma_pago) else CAJA)
            qué = f"{_cant(reg.cantidad)}{reg.detalle}".strip() or "compra"
            desc = f"Compra {'a crédito ' if credito else ''}{qué}" + (f" a {terc}" if terc else "")
            if reg.detalle and reg.cantidad and reg.cantidad > 0:
                k = clave_prod(reg.detalle)
                nombres_prod.setdefault(k, reg.detalle)
                cu = base / reg.cantidad
                entra = redondear(reg.cantidad * cu, 2)
                estado[k][0] += reg.cantidad
                estado[k][1] += entra
                costos[k][0] += reg.cantidad
                costos[k][1] += base
                pq.inventario_movs.append(MovInventario(k, "compra", reg.cantidad, f, comp, reg.detalle,
                                                        costo_unitario=cu, origen=reg.origen))
                mv(INVENTARIO, deb=entra, comp=comp, desc=desc, tipo="compra")
                if entra != base:      # el centavo que no cabe en el costo unitario
                    mv(COSTO_VENTAS, deb=base - entra, comp=comp, desc=f"Redondeo {desc}", tipo="compra")
            else:
                mv(INVENTARIO, deb=base, comp=comp, desc=desc, tipo="compra")
            mv(IVA_DESCONTABLE, deb=iva, comp=comp, desc=f"IVA {desc}", tipo="compra")
            mv(contra, cre=total, comp=comp, desc=desc, tipo="compra")

        elif b.tipo == "gastos":
            if not total:
                continue
            comp = comprobante("GTO")
            concepto = reg.detalle or terc or "Gasto"
            cuenta_sug = _cuenta_gasto(concepto)
            nombre = f"Gasto: {concepto}"
            mapeo_sugerido[normalizar(nombre)] = cuenta_sug
            credito = _es_credito(reg.forma_pago)
            contra = COSTOS_POR_PAGAR if credito else (BANCOS if _es_banco(reg.forma_pago) else CAJA)
            desc = f"{concepto}" + (f" · {terc}" if terc and terc != concepto else "")
            mv("", deb=base, comp=comp, desc=desc, nombre=nombre, tipo="gasto")
            mv(IVA_DESCONTABLE, deb=iva, comp=comp, desc=f"IVA {desc}", tipo="gasto")
            mv(contra, cre=total, comp=comp, desc=desc, tipo="gasto")

        elif b.tipo == "inventario":
            if not reg.detalle or reg.cantidad is None:
                continue
            k = clave_prod(reg.detalle)
            nombres_prod.setdefault(k, reg.detalle)
            if b.subtipo == "fisico":
                pq.inventario_fisico.append(ConteoFisico(k, reg.cantidad, f, reg.origen))
                continue
            valor = reg.total if reg.total is not None else CERO
            if not reg.cantidad or not valor:
                continue
            cu = valor / reg.cantidad
            entra = redondear(reg.cantidad * cu, 2)
            estado[k][0] += reg.cantidad
            estado[k][1] += entra
            pq.inventario_movs.append(MovInventario(k, "inventario_inicial", reg.cantidad, None, "INV-INICIAL",
                                                    reg.detalle, costo_unitario=cu, origen=reg.origen))
            pq.saldos_iniciales.append(SaldoInicial(INVENTARIO, entra, CERO, "", PREFIJO_APERTURA + reg.origen))
            pq.saldos_iniciales.append(SaldoInicial(APERTURA, CERO, entra, "", PREFIJO_APERTURA + reg.origen))

        elif b.tipo in ("cartera", "cxp"):
            es_cartera = b.tipo == "cartera"
            cuenta = CLIENTES if es_cartera else PROVEEDORES
            abono = reg.abono or CERO
            saldo = reg.saldo if reg.saldo is not None else (total - abono if reg.total is not None else CERO)
            deuda = reg.total if reg.total is not None else abono + saldo
            trato = trato_tercero.get(id(reg), "saldo_anterior")
            quien = terc or "tercero sin nombre"
            if trato == "saldo_anterior":
                if deuda:
                    lado = (deuda, CERO) if es_cartera else (CERO, deuda)
                    pq.saldos_iniciales.append(SaldoInicial(cuenta, lado[0], lado[1], "", PREFIJO_APERTURA + reg.origen))
                    pq.saldos_iniciales.append(SaldoInicial(APERTURA, lado[1], lado[0], "", PREFIJO_APERTURA + reg.origen))
                _abono(mv, comprobante, es_cartera, cuenta, abono, quien)
            elif trato == "adicional":
                if deuda:
                    if es_cartera:
                        comp = comprobante("VTA")
                        mv(CLIENTES, deb=deuda, comp=comp, desc=f"Venta a crédito a {quien} (según cartera)", tipo="venta")
                        mv("", cre=deuda, comp=comp, desc=f"Venta a crédito a {quien} (según cartera)",
                           nombre=NOMBRE_INGRESO, tipo="venta")
                    else:
                        comp = comprobante("CMP")
                        mv(INVENTARIO, deb=deuda, comp=comp, desc=f"Compra a crédito a {quien} (según cuentas por pagar)",
                           tipo="compra")
                        mv(PROVEEDORES, cre=deuda, comp=comp, desc=f"Compra a crédito a {quien} (según cuentas por pagar)",
                           tipo="compra")
                _abono(mv, comprobante, es_cartera, cuenta, abono, quien)
            elif trato == "incluidas":
                if saldo:
                    comp = comprobante("RCL")
                    if es_cartera:
                        mv(CLIENTES, deb=saldo, comp=comp, desc=f"Saldo por cobrar a {quien}: la venta no fue de contado",
                           tipo="reclasificacion")
                        mv(CAJA, cre=saldo, comp=comp, desc=f"Saldo por cobrar a {quien}", tipo="reclasificacion")
                    else:
                        mv(CAJA, deb=saldo, comp=comp, desc=f"Saldo por pagar a {quien}", tipo="reclasificacion")
                        mv(PROVEEDORES, cre=saldo, comp=comp, desc=f"Saldo por pagar a {quien}: la compra no fue de contado",
                           tipo="reclasificacion")
            else:   # abonos de una venta o compra a crédito que ya está en las listas
                _abono(mv, comprobante, es_cartera, cuenta, abono, quien)

    # 6 · Avisos que dependen del conjunto.
    primero = propias[0].id
    for (k, a, m), (falta, pedida) in sorted(faltantes.items()):
        cuando = f"{NOMBRE_MES[m].lower()} de {a}" if a else "el periodo"
        alertas[primero].append(Alerta(
            "AUX-INVENTARIO", "advertencia",
            f"Inventario insuficiente: en {cuando} se vendieron {_n(pedida)} de «{nombres_prod.get(k, k)}» y solo había "
            f"{_n(pedida - falta)} según las compras registradas. El costo de las {_n(falta)} unidades que faltan NO se "
            "inventó: cargue las compras que faltan o un conteo físico."))
    for nombre in sorted(sin_compra)[:10]:
        if productos_inv:
            alertas[primero].append(Alerta(
                "AUX-INVENTARIO", "info",
                f"«{nombre}» se vende pero no aparece en las compras ni en el inventario: se registra sin costo de ventas."))
    for k, (qv, vv) in precios.items():
        qc, vc = costos.get(k, (CERO, CERO))
        if qv and qc and vv and vc:
            precio, costo = vv / qv, vc / qc
            if costo and (precio / costo > 5 or precio / costo < Decimal("0.5")):
                razon = precio / costo
                cuanto = (f"{_n(redondear(razon, 1))} veces el costo" if razon > 1
                          else f"la {_n(redondear(1 / razon, 0))}.ª parte del costo")
                alertas[primero].append(Alerta(
                    "AUX-MARGEN", "advertencia",
                    f"«{nombres_prod.get(k, k)}»: se vende a {pesos(redondear(precio, 2))} por unidad y se compra a "
                    f"{pesos(redondear(costo, 2))}: el precio es {cuanto}. Puede que se venda por una unidad y se "
                    "compre por otra (kilo y bulto, unidad y caja). Confirme la unidad antes de cerrar."))

    meses = sorted({f"{r.fecha.year}-{r.fecha.month:02d}" for _, _, r in items if r.fecha})
    desde = min((r.fecha for _, _, r in items if r.fecha), default=None)
    hasta = max((r.fecha for _, _, r in items if r.fecha), default=None)
    if desde:
        desde = desde.replace(day=1)
    if hasta:
        hasta = _ultimo_dia(hasta.year, hasta.month)

    for d in propias:
        pq = paquetes[d.id]
        pq.alertas = alertas.get(d.id, []) + list(d.paquete.alertas)
        n = len({m.comprobante for m in pq.movimientos})
        d.resumen["movimientos"] = len(pq.movimientos)
        d.resumen["comprobantes"] = n
        d.paquete = pq
    return Conversion(paquetes, preguntas, meses, desde, hasta, origenes, mapeo_sugerido)


def _abono(mv, comprobante, es_cartera: bool, cuenta: str, abono: Decimal, quien: str) -> None:
    if not abono:
        return
    if es_cartera:
        comp = comprobante("REC")
        mv(CAJA, deb=abono, comp=comp, desc=f"Abono de {quien}", tipo="recaudo")
        mv(cuenta, cre=abono, comp=comp, desc=f"Abono de {quien}", tipo="recaudo")
    else:
        comp = comprobante("PAG")
        mv(cuenta, deb=abono, comp=comp, desc=f"Pago a {quien}", tipo="pago")
        mv(CAJA, cre=abono, comp=comp, desc=f"Pago a {quien}", tipo="pago")


def _es_credito(forma: str) -> bool:
    return bool(forma) and bool(enc.contiene_palabra(forma, CREDITO_PALABRAS))


def _es_banco(forma: str) -> bool:
    return bool(forma) and bool(enc.contiene_palabra(forma, BANCO_PALABRAS))


def _cuenta_gasto(concepto: str) -> str:
    t = normalizar(concepto)
    for palabras, cuenta in GASTOS_PUC:
        if enc.contiene_palabra(t, palabras, umbral=88):
            return cuenta
    return OTROS_GASTOS


def _n(v: Decimal) -> str:
    v = v.normalize()
    return f"{v:f}".replace(".", ",")


def _cant(v: Decimal | None) -> str:
    return f"{_n(v)} " if v else ""
