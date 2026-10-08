"""Estructura genérica de reportes: la usan la API (pantalla), Excel y PDF."""
from __future__ import annotations



def col(clave: str, titulo: str, tipo: str = "texto", ancho: int | None = None) -> dict:
    return {"clave": clave, "titulo": titulo, "tipo": tipo, "ancho": ancho}


def fila(tipo: str, valores: dict, nivel: int = 0, suma: list[int] | None = None) -> dict:
    """tipo: seccion | linea | subtotal | total | nota | vacia. `suma` = índices de filas que suman (para fórmulas Excel)."""
    return {"tipo": tipo, "valores": valores, "nivel": nivel, "suma": suma}


def reporte(id_: str, titulo: str, subtitulo: str, columnas: list[dict], filas: list[dict],
            firmas: bool = False, horizontal: bool = False, notas: list[str] | None = None,
            verificacion: dict | None = None) -> dict:
    return {
        "id": id_, "titulo": titulo, "subtitulo": subtitulo, "columnas": columnas, "filas": filas,
        "firmas": firmas, "horizontal": horizontal, "notas": notas or [], "verificacion": verificacion,
    }


class Constructor:
    """Ayuda a armar filas recordando índices para los totales."""

    def __init__(self) -> None:
        self.filas: list[dict] = []

    def agregar(self, tipo: str, valores: dict, nivel: int = 0, suma: list[int] | None = None) -> int:
        self.filas.append(fila(tipo, valores, nivel, suma))
        return len(self.filas) - 1

    def seccion(self, texto: str, clave: str = "cuenta", nivel: int = 0) -> int:
        return self.agregar("seccion", {clave: texto}, nivel)

    def vacia(self) -> int:
        return self.agregar("vacia", {})


