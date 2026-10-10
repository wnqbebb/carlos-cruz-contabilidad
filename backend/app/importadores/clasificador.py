"""Qué es cada archivo que llega: directorio de clientes, contabilidad o documento.

POR QUÉ EXISTE
Hasta la v2.1 la aplicación tenía dos puertas distintas —«Importar Excel» en
Clientes y «Subir» en Trabajar— y el contador tenía que saber cuál usar. Si se
equivocaba, veía «No se encontraron las columnas obligatorias NIT y RAZÓN
SOCIAL» y se quedaba ahí. Desde la v2.2 hay una sola puerta y el backend
decide, mirando el CONTENIDO del archivo, no su nombre ni la pantalla.

Las tres respuestas posibles:
  · `directorio`    → una lista de clientes para dar de alta en bloque
  · `contabilidad`  → movimientos, saldos o registros auxiliares de UN cliente
  · `documentos`    → estatutos, RUT, cámara, cartas: solo aportan identidad
Si llega algo que encaja en dos, se devuelve `ambiguo` y la pantalla pregunta.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ..contabilidad.puc import Mapeador
from ..modelos import Empresa
from ..utils.numeros import normalizar
from . import identidad as ident
from .clientes_excel import _buscar_fila_encabezado
from .documentos import es_hoja_de_texto
from .lector import Hoja, leer_archivo

DIRECTORIO = "directorio"
CONTABILIDAD = "contabilidad"
DOCUMENTOS = "documentos"
AMBIGUO = "ambiguo"
DESCONOCIDO = "desconocido"


@dataclass
class HojaClasificada:
    hoja: Hoja
    clase: str                  # directorio · contabilidad · texto · desconocido
    formato: str = ""           # formato contable reconocido, si lo hay
    razon: str = ""             # por qué se clasificó así, en español
    filas_datos: int = 0


@dataclass
class Lectura:
    """Todo lo que se pudo saber de los archivos subidos, antes de decidir."""
    hojas: list[HojaClasificada] = field(default_factory=list)
    identidad: ident.Identidad = field(default_factory=ident.Identidad)
    ilegibles: list[dict] = field(default_factory=list)
    archivos: list[str] = field(default_factory=list)
    fechas: list = field(default_factory=list)      # fechas de los registros, para decir qué meses cubre

    @property
    def clase(self) -> str:
        clases = {h.clase for h in self.hojas}
        if CONTABILIDAD in clases and DIRECTORIO in clases:
            return AMBIGUO
        if CONTABILIDAD in clases:
            return CONTABILIDAD
        if DIRECTORIO in clases:
            return DIRECTORIO
        if "texto" in clases and self.identidad.campos:
            return DOCUMENTOS
        return DESCONOCIDO

    def hojas_de(self, clase: str) -> list[HojaClasificada]:
        return [h for h in self.hojas if h.clase == clase]

    def ficha(self):
        """La ficha del cliente que se puede sacar de estos documentos (Fase 6)."""
        from .ficha import extraer

        por_archivo: dict[str, list[Hoja]] = {}
        for h in self.hojas:
            por_archivo.setdefault(h.hoja.archivo, []).append(h.hoja)
        return extraer(por_archivo)


def _parece_directorio(hoja: Hoja) -> tuple[bool, str, int]:
    """¿Es una LISTA de clientes? Hacen falta las dos columnas y varias filas.

    Una sola fila con NIT y nombre es la cabecera de una contabilidad, no un
    directorio: por eso se exigen al menos dos documentos distintos.
    """
    filas = hoja.valores
    r, mapa = _buscar_fila_encabezado(filas)
    campos = set(mapa.values())
    if r < 0 or not {"nit", "razon_social"} <= campos:
        return False, "", 0

    col_nit = next(i for i, c in mapa.items() if c == "nit")
    col_nombre = next(i for i, c in mapa.items() if c == "razon_social")
    nits, llenas = set(), 0
    for fila in filas[r + 1:]:
        nit = normalizar(fila[col_nit]) if col_nit < len(fila) else ""
        nombre = normalizar(fila[col_nombre]) if col_nombre < len(fila) else ""
        if nit and nombre:
            llenas += 1
            nits.add("".join(ch for ch in nit if ch.isdigit()))
    if llenas >= 2 and len(nits) >= 2:
        return True, f"Tiene columnas NIT y razón social con {llenas} clientes distintos.", llenas
    return False, "", llenas


def leer(archivos: list[tuple[str, bytes]], mapeador: Mapeador | None = None,
         empresa: Empresa | None = None) -> Lectura:
    """Abre todos los archivos y clasifica cada hoja. No decide nada todavía."""
    from .detector import detectar_hoja        # import tardío: evita un ciclo

    mapeador = mapeador or Mapeador()
    empresa = empresa or Empresa()
    lectura = Lectura(archivos=[n for n, _ in archivos])

    for i, (nombre, contenido) in enumerate(archivos):
        try:
            hojas = leer_archivo(contenido, nombre)
        except Exception as ex:
            lectura.ilegibles.append({"archivo": nombre, "motivo": str(ex)})
            continue

        for j, hoja in enumerate(hojas):
            if es_hoja_de_texto(hoja):
                ident.de_texto(getattr(hoja, "texto_plano", ""), f"{nombre} › texto", lectura.identidad)
                lectura.hojas.append(HojaClasificada(hoja, "texto", razon="Texto del documento."))
                continue

            ident.de_hoja(hoja, lectura.identidad)

            es_dir, razon, filas = _parece_directorio(hoja)
            if es_dir:
                lectura.hojas.append(HojaClasificada(hoja, DIRECTORIO, razon=razon, filas_datos=filas))
                continue

            det = detectar_hoja(hoja, f"{i}-{j}", mapeador, empresa)
            if det.formato != "desconocido":
                razon = det.formato_nombre
                filas = int(det.resumen.get("movimientos") or 0)
                if det.formato == "auxiliares":
                    # «ventas, compras y cartera», que es lo que el contador reconoce.
                    from .auxiliares import NOMBRE_TIPO

                    tipos = det.resumen.get("tipos") or []
                    razon = ", ".join(NOMBRE_TIPO[t].lower() for t in tipos) or "listas sin tipo claro"
                    filas = int(det.resumen.get("registros") or 0)
                    lectura.fechas += [r.fecha_archivo for b in getattr(det, "bloques", []) for r in b.registros
                                       if r.fecha_archivo]
                lectura.fechas += [m.fecha for m in det.paquete.movimientos if m.fecha]
                if det.formato == "facturas_dian" and det.resumen.get("dueno"):
                    # Los reportes de la DIAN dicen de quién son: el NIT que está en todos los documentos.
                    origen = f"{nombre} › {hoja.nombre} (NIT en todos los documentos)"
                    lectura.identidad.poner("nit", det.resumen["dueno"], origen, ident.SEGURO)
                    lectura.identidad.poner("razon_social", det.resumen.get("dueno_nombre"), origen, ident.SEGURO)
                lectura.hojas.append(HojaClasificada(hoja, CONTABILIDAD, formato=det.formato, razon=razon,
                                                     filas_datos=filas))
            else:
                lectura.hojas.append(HojaClasificada(hoja, DESCONOCIDO, razon=det.motivo))

    # El nombre del archivo es el último recurso para el nombre del cliente.
    if "razon_social" not in lectura.identidad.campos:
        for nombre in lectura.archivos:
            sugerido = ident.nombre_desde_archivo(nombre)
            if sugerido:
                lectura.identidad.poner("razon_social", sugerido, f"nombre del archivo «{nombre}»",
                                        ident.SUGERIDO)
                break

    return lectura
