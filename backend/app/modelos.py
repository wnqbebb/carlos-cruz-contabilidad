"""Estructuras de datos del motor contable (todas con Decimal)."""
from __future__ import annotations

import dataclasses
import json
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from .config import DATA
from .utils.numeros import CERO, D, parse_fecha


@dataclass
class Movimiento:
    cuenta: str
    debito: Decimal = CERO
    credito: Decimal = CERO
    fecha: date | None = None
    comprobante: str = ""
    tipo: str = ""
    nombre_cuenta: str = ""
    tercero_id: str = ""
    tercero_nombre: str = ""
    descripcion: str = ""
    origen: str = ""
    base_retencion: Decimal | None = None


@dataclass
class SaldoInicial:
    cuenta: str
    debito: Decimal = CERO
    credito: Decimal = CERO
    nombre_cuenta: str = ""
    origen: str = ""


@dataclass
class MovInventario:
    codigo: str
    tipo: str  # inventario_inicial | compra | venta | devolucion_compra | devolucion_venta | ajuste
    cantidad: Decimal
    fecha: date | None = None
    documento: str = ""
    descripcion: str = ""
    laboratorio: str = ""
    lote: str = ""
    vencimiento: date | None = None
    costo_unitario: Decimal | None = None
    precio_venta: Decimal | None = None
    origen: str = ""


@dataclass
class ConteoFisico:
    codigo: str
    cantidad: Decimal
    fecha: date | None = None
    origen: str = ""


@dataclass
class ActivoFijo:
    descripcion: str
    cuenta: str
    fecha_compra: date | None
    costo: Decimal
    vida_util_meses: int
    valor_residual: Decimal = CERO
    metodo: str = "linea_recta"
    origen: str = ""


@dataclass
class Empleado:
    nombre: str
    cargo: str = ""
    cedula: str = ""
    mes: int | None = None
    año: int | None = None
    salario_basico: Decimal | None = None  # salario mensual
    valor_hora: Decimal | None = None
    horas: Decimal | None = None
    dias: Decimal = Decimal("30")
    aux_transporte: str = "auto"  # auto | si | no
    horas_extra: Decimal = CERO  # valor en pesos
    comisiones: Decimal = CERO
    clase_riesgo: int = 1
    origen: str = ""


@dataclass
class AporteSocio:
    nombre: str
    cedula: str = ""
    comprometido: Decimal = CERO
    pagado: Decimal = CERO
    saldo: Decimal = CERO
    origen: str = ""


@dataclass
class Alerta:
    codigo: str
    severidad: str  # error | advertencia | info
    mensaje: str
    detalle: str = ""
    origen: str = ""


@dataclass
class Empresa:
    razon_social: str = ""
    sigla: str = ""
    nit: str = ""
    direccion: str = ""
    municipio: str = ""
    constitucion: str = ""
    ciiu: str = ""
    rep_legal: str = ""
    rep_legal_cc: str = ""
    rep_legal_suplente: str = ""
    contador: str = ""
    contador_cc: str = ""
    contador_tp: str = ""
    grupo_niif: int = 3
    responsable_iva: bool = True
    tarifa_renta: Decimal = Decimal("0.35")
    capital_suscrito: Decimal = CERO
    valor_nominal_accion: Decimal = CERO
    accionistas: list = field(default_factory=list)
    periodo_desde: date = date(2025, 1, 1)
    periodo_hasta: date = date(2025, 1, 31)
    demo: bool = False
    tipo_persona: str = "juridica"
    tipo_sociedad: str = ""

    @classmethod
    def desde_dict(cls, d: dict) -> "Empresa":
        e = cls()
        for f in dataclasses.fields(cls):
            if f.name not in d or d[f.name] is None:
                continue
            v = d[f.name]
            if f.name in ("tarifa_renta", "capital_suscrito", "valor_nominal_accion"):
                v = D(v)
            elif f.name in ("periodo_desde", "periodo_hasta"):
                v = parse_fecha(v) or getattr(e, f.name)
            elif f.name == "grupo_niif":
                v = int(v)
            elif f.name in ("responsable_iva", "demo"):
                v = v if isinstance(v, bool) else str(v).strip().upper() in ("SI", "SÍ", "TRUE", "1", "S")
            setattr(e, f.name, v)
        return e


def empresa_por_defecto() -> Empresa:
    datos = json.loads((DATA / "empresa_fanant.json").read_text(encoding="utf-8"))
    return Empresa.desde_dict(datos)


@dataclass
class Paquete:
    """Datos importados de una o varias hojas."""
    empresa: dict | None = None
    saldos_iniciales: list[SaldoInicial] = field(default_factory=list)
    movimientos: list[Movimiento] = field(default_factory=list)
    ajustes_manuales: list[Movimiento] = field(default_factory=list)
    inventario_movs: list[MovInventario] = field(default_factory=list)
    inventario_fisico: list[ConteoFisico] = field(default_factory=list)
    activos_fijos: list[ActivoFijo] = field(default_factory=list)
    empleados: list[Empleado] = field(default_factory=list)
    aportes_socios: list[AporteSocio] = field(default_factory=list)
    alertas: list[Alerta] = field(default_factory=list)
    filas_ignoradas: list[dict] = field(default_factory=list)
    auditoria_nomina: list[dict] = field(default_factory=list)
    auditoria_ef: list[dict] = field(default_factory=list)
    titulos: list[str] = field(default_factory=list)

    def unir(self, otro: "Paquete") -> None:
        if otro.empresa:
            self.empresa = {**(self.empresa or {}), **otro.empresa}
        for f in dataclasses.fields(self):
            if f.name == "empresa":
                continue
            getattr(self, f.name).extend(getattr(otro, f.name))


def a_json(obj):
    """Serializa dataclasses/Decimal/fechas a tipos JSON **sin perder exactitud**.

    Los importes salen como cadena decimal, no como float. El motivo está
    explicado en `app/exactitud.py`: un float no puede representar 0.1 y en un
    balance de miles de líneas eso produce descuadres de centavos inexplicables.
    """
    from .exactitud import a_json as exacto

    return exacto(obj)
