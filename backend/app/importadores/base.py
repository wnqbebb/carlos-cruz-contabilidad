"""Resultado común de los importadores."""
from __future__ import annotations

from dataclasses import dataclass, field

from ..modelos import Paquete

NOMBRES_FORMATO = {
    # El nombre de un cliente no puede rotular un formato que usan todos.
    "plantilla": "Plantilla oficial de Carlos Cruz",
    "cuenta_t": "Mayor en cuentas T",
    "hoja_trabajo": "Hoja de trabajo (balance inicial + movimiento)",
    "aportes": "Libro de aportes de socios",
    "nomina": "Nómina",
    "estados_existentes": "Estados financieros existentes (auditoría)",
    "desconocido": "Formato no reconocido",
}


@dataclass
class Deteccion:
    id: str
    archivo: str
    hoja: str
    formato: str
    incluir: bool = True
    motivo: str = ""
    resumen: dict = field(default_factory=dict)
    paquete: Paquete = field(default_factory=Paquete)
    solo_auditoria: bool = False

    @property
    def formato_nombre(self) -> str:
        return NOMBRES_FORMATO.get(self.formato, self.formato)
