"""Facturas electrónicas descargadas del portal de la DIAN (emitidas = ventas, recibidas = compras).

POR QUÉ EXISTE (rescate)
La idea central de la aplicación: el contador o el cliente descarga sus reportes del portal de la
DIAN y la aplicación organiza todo sola. No hay conexión pública con la DIAN para descargarlos:
el usuario entra al portal (catalogo-vpfe.dian.gov.co → «Descargar listados» o «Documentos» →
Exportar Excel) y suelta aquí el archivo.

DE DÓNDE SALEN LAS COLUMNAS
El Excel del portal trae una fila por documento con estas columnas (los nombres se comparan sin
tildes ni mayúsculas, en cualquier orden):
    Tipo de documento · CUFE/CUDE · Folio · Prefijo · Divisa · Forma de Pago · Medio de Pago ·
    Fecha Emisión · Fecha Recepción · NIT Emisor · Nombre Emisor · NIT Receptor · Nombre Receptor ·
    IVA · ICA · IC · INC · Timbre · INC Bolsas · IN Carbono · IN Combustibles · IC Datos · ICL ·
    INPP · IBUA · ICUI · Rete IVA · Rete Renta · Rete ICA · Total · Estado · Grupo
Fuentes consultadas (octubre de 2026):
  · github.com/Villamil21/amd-herramientas, versión 1.17.0: «Tipo de documento, CUFE/CUDE, Folio,
    Prefijo, Fecha Emisión, NIT Emisor, Nombre Emisor, NIT Receptor, IVA, ICA, IC, INC, Timbre,
    INC Bolsas, IN Carbono, IN Combustibles, IC Datos, ICL, INPP, IBUA, ICUI», además de Total,
    Estado y Grupo; la base de cada documento es Total menos esos impuestos.
  · github.com/ImplementacionesCofinet/Sistema-de-facturas: NIT Emisor, Nombre Emisor, Prefijo,
    Folio, Estado, CUFE/CUDE, Divisa; distingue NIT Emisor de NIT Receptor.
  · ayuda.alegra.com/col/descargar-listados-en-la-dian: menú Histórico → Descarga de listados,
    filtro por grupo (todos, emitidos, recibidos) y «Exportar Excel».
Divisa, Forma de Pago, Medio de Pago, Fecha Recepción y las tres retenciones se tratan como
opcionales: si no vienen, no pasa nada.

QUÉ HACE
  · Emitidas (ventas): débito a clientes (o caja si es de contado) por lo que falta cobrar,
    retenciones que le practicaron al cliente como anticipo, crédito a ingresos, IVA generado y
    otros impuestos.
  · Recibidas (compras y gastos): débito a mercancías (1435) más IVA descontable; crédito a
    proveedores (o caja) y a las retenciones practicadas. El contador cambia la cuenta de cualquier
    compra que sea un gasto en «Datos del periodo».
  · Notas crédito: al revés. Documentos rechazados, duplicados (mismo CUFE) y eventos: fuera.
  · Quién es emisor o receptor se sabe por la columna «Grupo» o comparando con el NIT del cliente;
    si no hay ninguna de las dos, por el NIT que se repite en todo el archivo.
"""
from __future__ import annotations

from collections import Counter
from decimal import Decimal

from ..modelos import Alerta, Empresa, Movimiento, Paquete
from ..utils.numeros import CERO, D, normalizar, parse_fecha, pesos
from .base import Deteccion
from .lector import Hoja

FORMATO = "facturas_dian"

# Nombre normalizado de la columna → rol. Varias formas por si el portal cambia el rótulo.
COLUMNAS = {
    "tipo": ("TIPO DE DOCUMENTO", "TIPO DOCUMENTO", "TIPO"),
    "cufe": ("CUFE CUDE", "CUFE", "CUDE"),
    "folio": ("FOLIO", "NUMERO", "NUMERO DOCUMENTO", "CONSECUTIVO"),
    "prefijo": ("PREFIJO",),
    "divisa": ("DIVISA", "MONEDA"),
    "forma_pago": ("FORMA DE PAGO", "FORMA PAGO"),
    "medio_pago": ("MEDIO DE PAGO", "MEDIO PAGO"),
    "fecha": ("FECHA EMISION", "FECHA DE EMISION"),
    "fecha_recepcion": ("FECHA RECEPCION", "FECHA DE RECEPCION"),
    "nit_emisor": ("NIT EMISOR", "NIT DEL EMISOR"),
    "nombre_emisor": ("NOMBRE EMISOR", "NOMBRE DEL EMISOR", "RAZON SOCIAL EMISOR"),
    "nit_receptor": ("NIT RECEPTOR", "NIT DEL RECEPTOR", "NIT ADQUIRENTE"),
    "nombre_receptor": ("NOMBRE RECEPTOR", "NOMBRE DEL RECEPTOR", "RAZON SOCIAL RECEPTOR", "NOMBRE ADQUIRENTE"),
    "iva": ("IVA",),
    "rete_iva": ("RETE IVA", "RETEIVA", "RETENCION IVA"),
    "rete_renta": ("RETE RENTA", "RETEFUENTE", "RETENCION RENTA", "RETE FUENTE"),
    "rete_ica": ("RETE ICA", "RETEICA", "RETENCION ICA"),
    "total": ("TOTAL", "VALOR TOTAL"),
    "estado": ("ESTADO",),
    "grupo": ("GRUPO",),
}
# Otros impuestos del documento (todos menos el IVA): se restan del total para hallar la base.
OTROS_IMPUESTOS = ("ICA", "IC", "INC", "TIMBRE", "INC BOLSAS", "IN CARBONO", "IN COMBUSTIBLES", "IC DATOS", "ICL",
                   "INPP", "IBUA", "ICUI")

# Cuentas PUC (Decreto 2650 de 1993).
CLIENTES, CAJA, PROVEEDORES = "130505", "110505", "220505"
INGRESOS, DEVOLUCIONES_VENTAS = "413595", "417505"
IVA_GENERADO, IVA_DESCONTABLE, OTROS_IMP = "240805", "240810", "249595"
ANT_RETE_RENTA, ANT_RETE_IVA, ANT_RETE_ICA = "135515", "135517", "135518"
MERCANCIAS = "143501"
RET_RENTA, RET_IVA, RET_ICA = "236540", "236701", "236801"


def _digitos(v) -> str:
    if isinstance(v, float) and v.is_integer():
        v = int(v)
    return "".join(ch for ch in str(v or "") if ch.isdigit())


def _nit_base(v) -> str:
    """NIT sin dígito de verificación: «900123456-8» → «900123456»."""
    t = str(v or "").strip()
    if "-" in t:
        t = t.split("-")[0]
    return _digitos(t)


def detectar(h: Hoja) -> tuple[int, dict[str, int], dict[str, int]] | None:
    """Fila de encabezados del reporte de facturas. Exige CUFE/CUDE, NIT emisor, NIT receptor y total."""
    for r in range(min(h.nfilas, 12)):
        textos = {c: t for c, t in h.fila_textos(r)}
        cols: dict[str, int] = {}
        otros: dict[str, int] = {}
        for c, t in textos.items():
            for rol, nombres in COLUMNAS.items():
                if rol not in cols and t in nombres:
                    cols[rol] = c
                    break
            else:
                if t in OTROS_IMPUESTOS:
                    otros[t] = c
        if {"cufe", "nit_emisor", "nit_receptor", "total"} <= set(cols):
            return r, cols, otros
    return None


def duenos(h: Hoja, r0: int, cols: dict[str, int]) -> tuple[str, str]:
    """(NIT, nombre) que se repite en todo el archivo: el contribuyente dueño del reporte."""
    nombres: dict[str, str] = {}
    veces: Counter = Counter()
    for r in range(r0 + 1, h.nfilas):
        for nit_col, nombre_col in (("nit_emisor", "nombre_emisor"), ("nit_receptor", "nombre_receptor")):
            nit = _nit_base(h.v(r, cols[nit_col])) if nit_col in cols else ""
            if nit:
                veces[nit] += 1
                if nombre_col in cols and h.v(r, cols[nombre_col]):
                    nombres.setdefault(nit, str(h.v(r, cols[nombre_col])).strip())
    if not veces:
        return "", ""
    nit = veces.most_common(1)[0][0]
    return nit, nombres.get(nit, "")


def _direcciones(h: Hoja, r0: int, cols: dict[str, int], nit_cliente: str) -> tuple[str, str]:
    """(cómo se decidió, NIT del dueño del archivo)."""
    if "grupo" in cols:
        return "grupo", nit_cliente or duenos(h, r0, cols)[0]
    if nit_cliente:
        return "nit", nit_cliente
    return "frecuente", duenos(h, r0, cols)[0]


def importar(h: Hoja, pos: tuple[int, dict[str, int], dict[str, int]], id_: str,
             empresa: Empresa | None = None) -> Deteccion:
    r0, cols, otros_cols = pos
    paquete = Paquete()
    nit_cliente = _nit_base(getattr(empresa, "nit", "") if empresa else "")
    como, dueno = _direcciones(h, r0, cols, nit_cliente)

    def v(r, rol):
        return h.v(r, cols[rol]) if rol in cols else None

    vistos: set[str] = set()
    cuenta = Counter()
    sumas = {"ventas_base": CERO, "ventas_iva": CERO, "ventas_total": CERO,
             "compras_base": CERO, "compras_iva": CERO, "compras_total": CERO}
    fechas = []
    terceros: set[str] = set()

    for r in range(r0 + 1, h.nfilas):
        total = D(v(r, "total"))
        tipo = normalizar(v(r, "tipo"))
        if not total and not tipo:
            continue
        origen = h.origen(r)
        if any(p in tipo for p in ("APPLICATION", "EVENTO", "NOMINA", "ACUSE", "RECIBO DEL BIEN", "ACEPTACION")):
            paquete.filas_ignoradas.append({"origen": origen, "motivo": f"«{v(r, 'tipo')}» no es una compra ni una venta"})
            continue
        estado = normalizar(v(r, "estado"))
        if "RECHAZ" in estado or "ANULAD" in estado:
            paquete.filas_ignoradas.append({"origen": origen, "motivo": "Documento rechazado por la DIAN"})
            cuenta["rechazados"] += 1
            continue
        cufe = str(v(r, "cufe") or "").strip()
        if cufe and cufe in vistos:
            paquete.filas_ignoradas.append({"origen": origen, "motivo": "Documento repetido (mismo CUFE/CUDE)"})
            cuenta["repetidos"] += 1
            continue
        if cufe:
            vistos.add(cufe)
        if not total:
            continue

        nit_e, nit_r = _nit_base(v(r, "nit_emisor")), _nit_base(v(r, "nit_receptor"))
        soporte = "SOPORTE" in tipo
        if como == "grupo":
            grupo = normalizar(v(r, "grupo"))
            emitido = grupo.startswith("EMITID") or grupo.startswith("ENVIAD")
        else:
            emitido = nit_e == dueno if nit_e != nit_r else True
            if dueno and dueno not in (nit_e, nit_r):
                paquete.alertas.append(Alerta(
                    "FE-AJENO", "advertencia",
                    f"El documento {v(r, 'prefijo') or ''}{v(r, 'folio') or ''} no es de este cliente "
                    f"(emisor {nit_e}, receptor {nit_r}); se dejó fuera.", origen=origen))
                continue
        # Documento soporte: lo emite el COMPRADOR a un proveedor no obligado a facturar → es compra.
        venta = emitido and not soporte
        nota_credito = "CREDITO" in tipo and "NOTA" in tipo
        signo = -1 if nota_credito else 1

        iva = D(v(r, "iva"))
        otros = sum((D(h.v(r, c)) for c in otros_cols.values()), CERO)
        rr, ri, rc = D(v(r, "rete_renta")), D(v(r, "rete_iva")), D(v(r, "rete_ica"))
        base = total - iva - otros
        neto = total - rr - ri - rc
        contado = "CONTADO" in normalizar(v(r, "forma_pago"))
        fecha = parse_fecha(v(r, "fecha"))
        if fecha:
            fechas.append(fecha)
        numero = f"{str(v(r, 'prefijo') or '').strip()}{_digitos(v(r, 'folio')) or str(v(r, 'folio') or '').strip()}"
        if venta:
            tercero_id, tercero = nit_r, str(v(r, "nombre_receptor") or "").strip()
            sigla = "NC" if nota_credito else ("ND" if "DEBITO" in tipo else "FV")
        else:
            tercero_id, tercero = (nit_r, str(v(r, "nombre_receptor") or "").strip()) if soporte else \
                (nit_e, str(v(r, "nombre_emisor") or "").strip())
            sigla = "DS" if soporte else ("NCC" if nota_credito else "FC")
        comp = f"{sigla} {numero}".strip()
        desc = f"{str(v(r, 'tipo') or 'Factura').strip()} {numero} · {tercero}".strip()
        if tercero:
            terceros.add(tercero_id or tercero)

        def mv(cta: str, valor: Decimal, debito: bool, que: str) -> None:
            if not valor:
                return
            valor = valor * signo
            # Un valor negativo (nota crédito) pasa al otro lado: nunca hay débitos negativos.
            es_debito = debito if valor > 0 else not debito
            valor = abs(valor)
            paquete.movimientos.append(Movimiento(
                cuenta=cta, debito=valor if es_debito else CERO, credito=CERO if es_debito else valor, fecha=fecha,
                comprobante=comp, tipo="venta" if venta else "compra", tercero_id=tercero_id, tercero_nombre=tercero,
                descripcion=f"{que} · {desc}", origen=origen))

        if venta:
            mv(CAJA if contado else CLIENTES, neto, True, "Por cobrar" if not contado else "Cobro de contado")
            mv(ANT_RETE_RENTA, rr, True, "Retención en la fuente que le practicaron")
            mv(ANT_RETE_IVA, ri, True, "Retención de IVA que le practicaron")
            mv(ANT_RETE_ICA, rc, True, "Retención de ICA que le practicaron")
            # En una nota crédito el signo ya da la vuelta: queda débito a devoluciones en ventas.
            mv(DEVOLUCIONES_VENTAS if nota_credito else INGRESOS, base, False,
               "Devolución en ventas" if nota_credito else "Venta")
            mv(IVA_GENERADO, iva, False, "IVA generado")
            mv(OTROS_IMP, otros, False, "Otros impuestos de la factura")
            sumas["ventas_base"] += base * signo
            sumas["ventas_iva"] += iva * signo
            sumas["ventas_total"] += total * signo
            cuenta["emitidas"] += 1
        else:
            mv(MERCANCIAS, base + otros, True, "Compra")
            mv(IVA_DESCONTABLE, iva, True, "IVA descontable")
            mv(CAJA if contado else PROVEEDORES, neto, False, "Pago de contado" if contado else "Por pagar")
            mv(RET_RENTA, rr, False, "Retención en la fuente practicada")
            mv(RET_IVA, ri, False, "Retención de IVA practicada")
            mv(RET_ICA, rc, False, "Retención de ICA practicada")
            sumas["compras_base"] += (base + otros) * signo
            sumas["compras_iva"] += iva * signo
            sumas["compras_total"] += total * signo
            cuenta["recibidas"] += 1

    if cuenta["recibidas"]:
        paquete.alertas.append(Alerta(
            "FE-COMPRAS", "info",
            f"{cuenta['recibidas']} compra(s) con factura electrónica por {pesos(sumas['compras_base'])} se registraron "
            "como mercancía (1435). Si alguna es un gasto (arriendo, servicios, honorarios…), cambie su cuenta en "
            "«Datos del periodo»."))
    if cuenta["emitidas"] and not cuenta["recibidas"]:
        paquete.alertas.append(Alerta(
            "FE-SOLO-VENTAS", "info",
            "El archivo solo trae facturas emitidas. Para el costo y el IVA descontable, descargue también las "
            "facturas recibidas del portal de la DIAN y súbalas."))
    if como == "frecuente" and dueno:
        paquete.alertas.append(Alerta(
            "FE-DUENO", "advertencia",
            f"El archivo no dice si cada documento es emitido o recibido; se tomó como dueño el NIT {dueno}, que se "
            "repite en todos. Revíselo en la ficha del cliente."))
    for clave, texto in (("rechazados", "rechazado(s) por la DIAN"), ("repetidos", "repetido(s) (mismo CUFE)")):
        if cuenta[clave]:
            paquete.alertas.append(Alerta("FE-FUERA", "info", f"{cuenta[clave]} documento(s) {texto} se dejaron fuera."))

    resumen = {
        "movimientos": len(paquete.movimientos), "emitidas": cuenta["emitidas"], "recibidas": cuenta["recibidas"],
        "ventas_base": sumas["ventas_base"], "ventas_iva": sumas["ventas_iva"], "ventas_total": sumas["ventas_total"],
        "compras_base": sumas["compras_base"], "compras_iva": sumas["compras_iva"],
        "compras_total": sumas["compras_total"], "terceros": len(terceros), "dueno": dueno,
        "dueno_nombre": duenos(h, r0, cols)[1] if dueno else "",
        "desde": min(fechas).isoformat() if fechas else None, "hasta": max(fechas).isoformat() if fechas else None,
    }
    partes = []
    if cuenta["emitidas"]:
        partes.append(f"{cuenta['emitidas']} factura(s) emitida(s)")
    if cuenta["recibidas"]:
        partes.append(f"{cuenta['recibidas']} recibida(s)")
    motivo = ("Facturas electrónicas de la DIAN: " + " y ".join(partes)) if partes else "No trae facturas con valores."
    return Deteccion(id_, h.archivo, h.nombre, FORMATO, bool(paquete.movimientos), motivo, resumen, paquete)
