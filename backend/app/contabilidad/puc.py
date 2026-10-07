"""Plan Único de Cuentas: nombres, naturaleza, jerarquía y mapeo de nombres del cliente."""
from __future__ import annotations

import json
from functools import lru_cache

from rapidfuzz import fuzz, process

from ..config import DATA
from ..utils.numeros import normalizar

UMBRAL_DIFUSO = 80

NOMBRE_CLASE = {
    "1": "Activo", "2": "Pasivo", "3": "Patrimonio", "4": "Ingresos", "5": "Gastos",
    "6": "Costos de ventas", "7": "Costos de producción",
}


class PUC:
    def __init__(self) -> None:
        datos = json.loads((DATA / "puc.json").read_text(encoding="utf-8"))
        self.cuentas: dict[str, str] = datos["cuentas"]
        self._exc_c = datos["naturaleza_credito_en_clases_debito"]
        self._exc_d = datos["naturaleza_debito_en_clases_credito"]

    def existe(self, codigo: str) -> bool:
        return codigo in self.cuentas

    def valido(self, codigo: str) -> bool:
        """Código numérico cuyo propio código o algún padre (4 o 2 dígitos) existe."""
        if not codigo or not codigo.isdigit() or codigo[0] not in NOMBRE_CLASE:
            return False
        return any(codigo[:n] in self.cuentas for n in (len(codigo), 6, 4, 2) if n <= len(codigo))

    def nombre(self, codigo: str, respaldo: str = "") -> str:
        if codigo in self.cuentas:
            return self.cuentas[codigo]
        if respaldo:
            return respaldo
        for n in (6, 4, 2, 1):
            if len(codigo) > n and codigo[:n] in self.cuentas:
                return self.cuentas[codigo[:n]]
        return codigo

    def naturaleza(self, codigo: str) -> str:
        """'D' débito o 'C' crédito."""
        if any(codigo.startswith(e) for e in self._exc_c):
            return "C"
        if any(codigo.startswith(e) for e in self._exc_d):
            return "D"
        return "C" if codigo[:1] in ("2", "3", "4") else "D"

    @staticmethod
    def clase(codigo: str) -> str:
        return codigo[:1] if codigo and codigo[0].isdigit() else "?"

    @staticmethod
    def grupo(codigo: str) -> str:
        return codigo[:2]

    @staticmethod
    def cuenta4(codigo: str) -> str:
        return codigo[:4] if len(codigo) >= 4 else codigo

    def listado(self) -> list[dict]:
        return [{"codigo": c, "nombre": n} for c, n in self.cuentas.items() if len(c) >= 4]


@lru_cache
def puc() -> PUC:
    return PUC()


@lru_cache
def _alias_base() -> tuple[dict[str, str], dict[str, str]]:
    datos = json.loads((DATA / "alias.json").read_text(encoding="utf-8"))
    return datos["alias"], datos.get("banderas", {})


class Mapeador:
    """Resuelve nombres de cuentas del cliente a códigos PUC."""

    def __init__(self, confirmados: dict[str, str] | None = None) -> None:
        self.alias, self.banderas = _alias_base()
        self.confirmados = confirmados or {}
        p = puc()
        self._objetivos: dict[str, str] = dict(self.alias)
        for codigo, nombre in p.cuentas.items():
            if len(codigo) >= 4:
                self._objetivos.setdefault(normalizar(nombre), codigo)

    def resolver(self, nombre: str) -> dict:
        n = normalizar(nombre)
        p = puc()
        base = {"nombre": nombre, "normalizado": n, "bandera": self.banderas.get(n)}
        if n in self.confirmados:
            return {**base, "codigo": self.confirmados[n], "estado": "exacto", "fuente": "confirmado", "candidatos": []}
        if n in self.alias:
            return {**base, "codigo": self.alias[n], "estado": "exacto", "fuente": "alias", "candidatos": []}
        codigo_directo = n.split(" ")[0] if n else ""
        if codigo_directo.isdigit() and p.valido(codigo_directo):
            return {**base, "codigo": codigo_directo, "estado": "exacto", "fuente": "codigo", "candidatos": []}
        if not n:
            return {**base, "codigo": None, "estado": "sin", "fuente": "", "candidatos": []}
        encontrados = process.extract(n, list(self._objetivos.keys()), scorer=fuzz.WRatio, limit=5)
        candidatos, vistos = [], set()
        for clave, puntaje, _ in encontrados:
            codigo = self._objetivos[clave]
            if codigo in vistos:
                continue
            vistos.add(codigo)
            candidatos.append({"codigo": codigo, "nombre": p.nombre(codigo), "puntaje": round(puntaje)})
        if candidatos and candidatos[0]["puntaje"] >= UMBRAL_DIFUSO:
            return {**base, "codigo": candidatos[0]["codigo"], "estado": "confirmar", "fuente": "difuso", "candidatos": candidatos}
        return {**base, "codigo": None, "estado": "sin", "fuente": "", "candidatos": candidatos}
