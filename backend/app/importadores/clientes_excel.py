"""Importación masiva del directorio de clientes desde Excel o CSV.

Está hecho para archivos grandes (decenas de miles de filas):
  · lee el .xlsx en modo `read_only` y por filas, así no carga todo en memoria;
  · reconoce los encabezados aunque vengan con otro nombre o con tildes;
  · inserta y actualiza por lotes;
  · nunca aborta por una fila mala: la reporta y sigue con las demás.

El informe de vuelta dice exactamente qué pasó con cada fila rechazada, con su
número de fila en el Excel, para que el contador la corrija en el archivo.
"""
from __future__ import annotations

import csv
import io
import uuid
from datetime import datetime, timezone

from sqlalchemy import insert, select, update

from ..db import conexion
from ..esquema import clientes as T
from ..repositorio.clientes import ErrorCliente, _defectos, _texto_buscable, normalizar_entrada
from ..utils import nit as unit
from ..utils.numeros import normalizar

# ── reconocimiento de encabezados ───────────────────────────────────────────
# Cada campo lista los encabezados que lo identifican, ya normalizados
# (mayúsculas, sin tildes ni puntuación). El primer acierto gana.
ENCABEZADOS: dict[str, tuple[str, ...]] = {
    "nit": ("NIT", "NIT CLIENTE", "IDENTIFICACION", "CEDULA O NIT", "NIT CC", "DOCUMENTO", "RUT"),
    "dv": ("DV", "DIGITO VERIFICACION", "DIGITO DE VERIFICACION"),
    "razon_social": ("RAZON SOCIAL", "NOMBRE", "CLIENTE", "NOMBRE CLIENTE", "EMPRESA",
                     "NOMBRE O RAZON SOCIAL", "RAZON SOCIAL O NOMBRE"),
    "sigla": ("SIGLA", "NOMBRE COMERCIAL", "ALIAS"),
    "tipo_persona": ("TIPO PERSONA", "TIPO", "PERSONA", "NATURALEZA"),
    "regimen": ("REGIMEN", "REGIMEN TRIBUTARIO", "RESPONSABILIDAD"),
    "grupo_niif": ("GRUPO NIIF", "NIIF", "GRUPO"),
    "responsable_iva": ("RESPONSABLE IVA", "IVA", "RESPONSABLE DE IVA"),
    "tarifa_renta": ("TARIFA RENTA", "RENTA", "TARIFA DE RENTA"),
    "ciiu": ("CIIU", "ACTIVIDAD", "ACTIVIDAD ECONOMICA", "CODIGO CIIU"),
    "direccion": ("DIRECCION", "DOMICILIO"),
    "municipio": ("MUNICIPIO", "CIUDAD"),
    "departamento": ("DEPARTAMENTO", "DEPTO"),
    "telefono": ("TELEFONO", "CELULAR", "TEL", "CONTACTO", "MOVIL"),
    "email": ("EMAIL", "CORREO", "CORREO ELECTRONICO", "E MAIL", "MAIL"),
    "rep_legal": ("REPRESENTANTE LEGAL", "REP LEGAL", "REPRESENTANTE"),
    "rep_legal_cc": ("CC REPRESENTANTE", "CEDULA REPRESENTANTE", "CC REP LEGAL", "CC"),
    "rep_legal_suplente": ("SUPLENTE", "REPRESENTANTE SUPLENTE", "REP SUPLENTE"),
    "contador": ("CONTADOR",),
    "contador_tp": ("TARJETA PROFESIONAL", "TP", "TP CONTADOR"),
    "fecha_constitucion": ("FECHA CONSTITUCION", "CONSTITUCION", "FECHA DE CONSTITUCION", "FECHA INICIO"),
    "capital_suscrito": ("CAPITAL", "CAPITAL SUSCRITO", "CAPITAL SOCIAL"),
    "honorarios_mes": ("HONORARIOS", "HONORARIOS MES", "VALOR MENSUAL", "MENSUALIDAD", "HONORARIOS MENSUALES"),
    "periodicidad": ("PERIODICIDAD", "FRECUENCIA"),
    "estado": ("ESTADO", "ACTIVO"),
    "etiquetas": ("ETIQUETAS", "TAGS", "CATEGORIA", "GRUPO CLIENTE"),
    "notas": ("NOTAS", "OBSERVACIONES", "COMENTARIOS"),
}

# Valores que vienen escritos "como habla la gente" y hay que traducir.
TIPOS_PERSONA = {
    "JURIDICA": "juridica", "J": "juridica", "PJ": "juridica", "PERSONA JURIDICA": "juridica",
    "SOCIEDAD": "juridica", "EMPRESA": "juridica",
    "NATURAL": "natural", "N": "natural", "PN": "natural", "PERSONA NATURAL": "natural",
}
REGIMENES = {
    "RESPONSABLE DE IVA": "responsable_iva", "RESPONSABLE IVA": "responsable_iva", "COMUN": "responsable_iva",
    "NO RESPONSABLE DE IVA": "no_responsable_iva", "NO RESPONSABLE": "no_responsable_iva",
    "SIMPLIFICADO": "no_responsable_iva", "GRAN CONTRIBUYENTE": "gran_contribuyente",
    "SIMPLE": "simple", "REGIMEN SIMPLE": "simple", "ESPECIAL": "especial", "ESAL": "especial",
}
PERIODICIDADES = {
    "MENSUAL": "mensual", "MES": "mensual", "BIMESTRAL": "bimestral", "TRIMESTRAL": "trimestral",
    "CUATRIMESTRAL": "cuatrimestral", "ANUAL": "anual", "ANO": "anual",
}
ESTADOS = {
    "ACTIVO": "activo", "SI": "activo", "S": "activo", "X": "activo", "1": "activo", "VIGENTE": "activo",
    "INACTIVO": "inactivo", "NO": "inactivo", "N": "inactivo", "0": "inactivo", "RETIRADO": "inactivo",
    "ARCHIVADO": "archivado",
}
LOTE = 500


def _mapear_encabezados(fila: list) -> dict[int, str]:
    """{índice de columna: campo}. Las columnas que no se reconocen se ignoran."""
    mapa: dict[int, str] = {}
    usados: set[str] = set()
    for i, celda in enumerate(fila):
        clave = normalizar(celda)
        if not clave:
            continue
        for campo, variantes in ENCABEZADOS.items():
            if campo in usados:
                continue
            if clave in variantes:
                mapa[i] = campo
                usados.add(campo)
                break
    return mapa


def _buscar_fila_encabezado(filas: list[list]) -> tuple[int, dict[int, str]]:
    """Encuentra la fila de títulos en las primeras 15. Exige NIT y razón social."""
    mejor: tuple[int, dict[int, str]] = (-1, {})
    for r, fila in enumerate(filas[:15]):
        mapa = _mapear_encabezados(fila)
        if "nit" in mapa.values() and "razon_social" in mapa.values():
            return r, mapa
        if len(mapa) > len(mejor[1]):
            mejor = (r, mapa)
    return mejor


def _traducir(campo: str, valor) -> object:
    texto = normalizar(valor)
    if campo == "tipo_persona":
        return TIPOS_PERSONA.get(texto, "juridica" if texto else "")
    if campo == "regimen":
        return REGIMENES.get(texto, "")
    if campo == "periodicidad":
        return PERIODICIDADES.get(texto, "")
    if campo == "estado":
        return ESTADOS.get(texto, "")
    if campo == "etiquetas":
        return [e.strip() for e in str(valor or "").replace(";", ",").split(",") if e.strip()]
    return valor


def _filas_de_archivo(contenido: bytes, archivo: str) -> list[list]:
    """Lee el archivo a una lista de filas. .xlsx va en modo streaming."""
    ext = archivo.lower().rsplit(".", 1)[-1]
    if ext in ("xlsx", "xlsm"):
        from openpyxl import load_workbook

        libro = load_workbook(io.BytesIO(contenido), data_only=True, read_only=True)
        try:
            hoja = libro.worksheets[0]
            return [list(f) for f in hoja.iter_rows(values_only=True)]
        finally:
            libro.close()
    if ext == "xls":
        from .lector import leer_xls

        hojas = leer_xls(contenido, archivo)
        return hojas[0].valores if hojas else []
    if ext in ("csv", "txt"):
        from .lector import leer_csv

        hojas = leer_csv(contenido, archivo)
        return hojas[0].valores if hojas else []
    raise ValueError(f"Formato no soportado: .{ext}. Use .xlsx, .xls o .csv")


def importar(contenido: bytes, archivo: str, *, actualizar_existentes: bool = True,
             solo_revisar: bool = False) -> dict:
    """Carga el archivo al directorio de clientes.

    `solo_revisar=True` hace la pasada completa sin escribir nada: sirve para
    mostrar al contador qué va a pasar antes de confirmar.
    """
    filas = _filas_de_archivo(contenido, archivo)
    if not filas:
        return _informe(archivo, 0, [], [], [], mensaje="El archivo está vacío.")

    fila_titulos, mapa = _buscar_fila_encabezado(filas)
    campos = set(mapa.values())
    if "nit" not in campos or "razon_social" not in campos:
        reconocidas = sorted(campos)
        return _informe(
            archivo, 0, [], [], [],
            mensaje=(
                "No se encontraron las columnas obligatorias. El archivo debe tener una columna "
                "«NIT» y una columna «RAZÓN SOCIAL» (o «NOMBRE»). "
                + (f"Columnas reconocidas: {', '.join(reconocidas)}." if reconocidas
                   else "No se reconoció ninguna columna.")
            ),
        )

    nuevos: list[dict] = []
    cambios: list[dict] = []
    rechazos: list[dict] = []
    vistos: dict[str, int] = {}
    defectos = _defectos()

    for desplazamiento, fila in enumerate(filas[fila_titulos + 1:]):
        numero_excel = fila_titulos + 2 + desplazamiento
        if all(c is None or (isinstance(c, str) and not c.strip()) for c in fila):
            continue

        crudo: dict[str, object] = {}
        for indice, campo in mapa.items():
            if indice < len(fila):
                valor = _traducir(campo, fila[indice])
                if valor not in (None, "", []):
                    crudo[campo] = valor

        try:
            limpio = normalizar_entrada(crudo)
        except ErrorCliente as ex:
            rechazos.append({"fila": numero_excel, "nit": str(crudo.get("nit") or ""),
                             "razon_social": str(crudo.get("razon_social") or ""), "motivo": str(ex)})
            continue

        if limpio["nit"] in vistos:
            rechazos.append({
                "fila": numero_excel, "nit": unit.formatear(limpio["nit"]),
                "razon_social": limpio.get("razon_social", ""),
                "motivo": f"NIT repetido dentro del mismo archivo (ya venía en la fila {vistos[limpio['nit']]}).",
            })
            continue
        vistos[limpio["nit"]] = numero_excel
        limpio["_fila"] = numero_excel
        nuevos.append({**defectos, **limpio})

    if not nuevos:
        return _informe(archivo, len(filas) - fila_titulos - 1, [], [], rechazos,
                        mensaje="Ninguna fila del archivo era utilizable.")

    # ── separar altas de actualizaciones ───────────────────────────────────
    insertar: list[dict] = []
    with conexion() as cn:
        existentes: dict[str, str] = {}
        todos_nit = [n["nit"] for n in nuevos]
        for i in range(0, len(todos_nit), LOTE):
            trozo = todos_nit[i:i + LOTE]
            for f in cn.execute(select(T.c.id, T.c.nit).where(T.c.nit.in_(trozo))).all():
                existentes[f.nit] = str(f.id)

        for fila_datos in nuevos:
            numero_excel = fila_datos.pop("_fila")
            if fila_datos["nit"] in existentes:
                if not actualizar_existentes:
                    rechazos.append({
                        "fila": numero_excel, "nit": unit.formatear(fila_datos["nit"]),
                        "razon_social": fila_datos["razon_social"],
                        "motivo": "Ya existe y se pidió no actualizar los existentes.",
                    })
                    continue
                cambios.append({"id": existentes[fila_datos["nit"]], "fila": numero_excel, **fila_datos})
            else:
                fila_datos["id"] = str(uuid.uuid4())
                fila_datos["buscable"] = _texto_buscable(fila_datos)
                insertar.append({"fila": numero_excel, **fila_datos})

        if not solo_revisar:
            cuerpos = [{k: v for k, v in f.items() if k != "fila"} for f in insertar]
            for i in range(0, len(cuerpos), LOTE):
                cn.execute(insert(T), cuerpos[i:i + LOTE])
            ahora = datetime.now(timezone.utc)
            for c in cambios:
                valores = {k: v for k, v in c.items() if k not in ("id", "fila")}
                valores["buscable"] = _texto_buscable(valores)
                valores["actualizado"] = ahora
                cn.execute(update(T).where(T.c.id == c["id"]).values(**valores))

    return _informe(
        archivo,
        len(filas) - fila_titulos - 1,
        [{"fila": f["fila"], "nit": unit.formatear(f["nit"], f["dv"]), "razon_social": f["razon_social"]} for f in insertar],
        [{"fila": c["fila"], "nit": unit.formatear(c["nit"], c["dv"]), "razon_social": c["razon_social"]} for c in cambios],
        rechazos,
        columnas=sorted(campos),
        solo_revisar=solo_revisar,
    )


def _informe(archivo: str, leidas: int, insertados: list, actualizados: list,
             rechazos: list, mensaje: str = "", columnas: list | None = None,
             solo_revisar: bool = False) -> dict:
    if not mensaje:
        verbo = "Se habrían" if solo_revisar else "Se"
        partes = []
        if insertados:
            partes.append(f"{len(insertados)} cliente(s) nuevo(s)")
        if actualizados:
            partes.append(f"{len(actualizados)} actualizado(s)")
        if rechazos:
            partes.append(f"{len(rechazos)} rechazado(s)")
        mensaje = (f"{verbo} {'procesado' if solo_revisar else 'procesaron'}: " + ", ".join(partes) + "."
                   if partes else "No hubo cambios.")
    return {
        "archivo": archivo,
        "solo_revisar": solo_revisar,
        "filas_leidas": max(0, leidas),
        "insertados": len(insertados),
        "actualizados": len(actualizados),
        "rechazados": len(rechazos),
        "columnas_reconocidas": columnas or [],
        "mensaje": mensaje,
        # Se recortan las listas: con 100.000 filas la respuesta no puede traerlas todas.
        "muestra_insertados": insertados[:50],
        "muestra_actualizados": actualizados[:50],
        "rechazos": rechazos[:200],
        "rechazos_omitidos": max(0, len(rechazos) - 200),
    }


def plantilla_csv() -> bytes:
    """Archivo de ejemplo con los encabezados exactos, para que el contador parta de ahí."""
    columnas = ["NIT", "RAZON SOCIAL", "SIGLA", "TIPO PERSONA", "REGIMEN", "GRUPO NIIF",
                "CIIU", "DIRECCION", "MUNICIPIO", "DEPARTAMENTO", "TELEFONO", "EMAIL",
                "REPRESENTANTE LEGAL", "CC REPRESENTANTE", "FECHA CONSTITUCION",
                "CAPITAL SUSCRITO", "HONORARIOS MES", "PERIODICIDAD", "ESTADO",
                "ETIQUETAS", "NOTAS"]
    # Filas de ejemplo inventadas (ningún dato es de un cliente real).
    ejemplos = [
        ["900123456", "TIENDA EJEMPLO S.A.S.", "EJEMPLO", "Jurídica", "Responsable de IVA", "3",
         "4711", "Calle 1 No. 2-3", "Guacarí", "Valle del Cauca", "3000000000",
         "contacto@ejemplo.com", "Nombre Apellido Ejemplo", "1000000001", "2024-01-15",
         "10000000", "300000", "Mensual", "Activo", "Comercio;Ejemplo", "Fila de ejemplo: bórrela"],
        ["1000000002", "PERSONA NATURAL EJEMPLO", "", "Natural", "No responsable de IVA", "3",
         "6920", "", "Guacarí", "Valle del Cauca", "", "", "", "", "",
         "0", "0", "Anual", "Activo", "Persona natural", "Fila de ejemplo: bórrela"],
    ]
    salida = io.StringIO()
    escritor = csv.writer(salida, delimiter=";", lineterminator="\r\n")
    escritor.writerow(columnas)
    escritor.writerows(ejemplos)
    return salida.getvalue().encode("utf-8-sig")
