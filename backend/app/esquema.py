"""Definición de tablas (SQLAlchemy Core) que funciona igual en Supabase/Postgres y en SQLite local.

Regla de oro del proyecto: **ningún importe pasa jamás por float.**
  · En Postgres los importes son NUMERIC(20,2), que es decimal exacto.
  · En SQLite no existe el tipo decimal, así que el tipo `Dinero` los guarda
    como TEXTO y los devuelve como `Decimal`. Exacto en ambos motores.

Los nombres de tabla y columna son idénticos a `supabase/migraciones/001_esquema.sql`,
de modo que el mismo código sirve contra la base real o contra la copia local.
"""
from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import (
    ARRAY,
    JSON,
    Boolean,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    MetaData,
    Numeric,
    SmallInteger,
    String,
    Table,
    Text,
    Uuid,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import BigInteger, TypeDecorator

metadatos = MetaData()


class Dinero(TypeDecorator):
    """Importe decimal exacto, portable entre Postgres y SQLite.

    Postgres → NUMERIC(20,2). SQLite → TEXT con el valor decimal literal.
    En los dos casos Python recibe un `Decimal`, nunca un float.

    El valor se cuantiza SIEMPRE a la misma escala antes de guardarlo. Es lo que
    Postgres hace solo con NUMERIC(20,2), y hacerlo también en SQLite garantiza
    que la misma ficha se lea idéntica en los dos motores: sin esto, un importe
    de 300.000 salía "300000.00" en Supabase y "300000" en la base local.
    """

    cache_ok = True
    escala = 2
    impl = Numeric(20, 2, asdecimal=True)

    @property
    def _cuanto(self) -> Decimal:
        return Decimal(1).scaleb(-self.escala)

    def _numerico(self) -> Numeric:
        return Numeric(20, self.escala, asdecimal=True)

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(self._numerico())
        return dialect.type_descriptor(Text())

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        valor = value if isinstance(value, Decimal) else Decimal(str(value))
        valor = valor.quantize(self._cuanto, rounding=ROUND_HALF_UP)
        if dialect.name == "postgresql":
            return valor
        return format(valor, "f")  # texto decimal plano, sin notación científica

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        valor = value if isinstance(value, Decimal) else Decimal(str(value))
        return valor.quantize(self._cuanto, rounding=ROUND_HALF_UP)


class Tasa(Dinero):
    """Igual que `Dinero` pero con 6 decimales (tarifas, participaciones)."""

    cache_ok = True
    escala = 6
    impl = Numeric(12, 6, asdecimal=True)

    def _numerico(self) -> Numeric:
        return Numeric(12, 6, asdecimal=True)


# JSON nativo: JSONB en Postgres (indexable), JSON de texto en SQLite.
Json = JSON().with_variant(JSONB, "postgresql")
# Lista de textos: text[] en Postgres, JSON en SQLite.
ListaTexto = JSON().with_variant(ARRAY(Text), "postgresql")
# Identificador: uuid nativo en Postgres, CHAR(32) en SQLite. Python ve `str`.
Id = Uuid(as_uuid=False)
# Clave autoincremental. SQLite solo autoincrementa un "INTEGER PRIMARY KEY":
# si se declara BIGINT deja de ser alias del rowid y falla el insert. Por eso
# en SQLite se degrada a INTEGER y en Postgres sigue siendo bigserial.
Serial = BigInteger().with_variant(Integer, "sqlite")

AHORA = func.now()

# ── 1. CLIENTES ─────────────────────────────────────────────────────────────
clientes = Table(
    "clientes",
    metadatos,
    Column("id", Id, primary_key=True),
    Column("nit", Text, nullable=False, unique=True),
    Column("dv", Text, default=""),
    Column("razon_social", Text, nullable=False),
    Column("sigla", Text, default=""),
    Column("tipo_persona", Text, nullable=False, default="juridica"),
    Column("regimen", Text, nullable=False, default="responsable_iva"),
    Column("grupo_niif", SmallInteger, nullable=False, default=3),
    Column("responsable_iva", Boolean, nullable=False, default=True),
    Column("tarifa_renta", Tasa, nullable=False, default=Decimal("0.35")),
    Column("ciiu", Text, default=""),
    Column("direccion", Text, default=""),
    Column("municipio", Text, default=""),
    Column("departamento", Text, default=""),
    Column("telefono", Text, default=""),
    Column("email", Text, default=""),
    Column("rep_legal", Text, default=""),
    Column("rep_legal_cc", Text, default=""),
    Column("rep_legal_suplente", Text, default=""),
    Column("contador", Text, default=""),
    Column("contador_cc", Text, default=""),
    Column("contador_tp", Text, default=""),
    Column("fecha_constitucion", Date),
    Column("capital_suscrito", Dinero, nullable=False, default=Decimal("0")),
    Column("valor_nominal_accion", Dinero, nullable=False, default=Decimal("0")),
    Column("honorarios_mes", Dinero, nullable=False, default=Decimal("0")),
    Column("periodicidad", Text, nullable=False, default="mensual"),
    Column("estado", Text, nullable=False, default="activo"),
    Column("etiquetas", ListaTexto, nullable=False, default=list),
    Column("notas", Text, default=""),
    # v2.2 · Fase 6: lo que traen los estatutos, el RUT y la cámara de comercio.
    Column("tipo_sociedad", Text, default=""),
    Column("objeto_social", Text, default=""),
    Column("documento_constitucion", Text, default=""),
    Column("capital_autorizado", Dinero, nullable=False, default=Decimal("0")),
    Column("capital_pagado", Dinero, nullable=False, default=Decimal("0")),
    Column("numero_acciones", Dinero, nullable=False, default=Decimal("0")),
    Column("rep_legal_suplente_cc", Text, default=""),
    Column("revisor_fiscal", Text, default=""),
    Column("revisor_fiscal_tp", Text, default=""),
    Column("matricula_mercantil", Text, default=""),
    Column("fecha_renovacion", Date),
    Column("ciiu_secundarios", Text, default=""),
    Column("responsabilidades", Text, default=""),
    Column("demo", Boolean, nullable=False, default=False),
    Column("buscable", Text, nullable=False, default=""),
    Column("creado", DateTime(timezone=True), nullable=False, server_default=AHORA),
    Column("actualizado", DateTime(timezone=True), nullable=False, server_default=AHORA),
    CheckConstraint("tipo_persona in ('juridica','natural')", name="clientes_tipo_persona"),
    CheckConstraint("estado in ('activo','inactivo','archivado')", name="clientes_estado"),
    Index("clientes_nit_idx", "nit"),
    Index("clientes_razon_idx", "razon_social"),
)

# ── 2. SOCIOS ───────────────────────────────────────────────────────────────
socios = Table(
    "socios",
    metadatos,
    Column("id", Serial, primary_key=True, autoincrement=True),
    Column("cliente_id", Id, ForeignKey("clientes.id", ondelete="CASCADE"), nullable=False),
    Column("nombre", Text, nullable=False),
    Column("cedula", Text, default=""),
    Column("cargo", Text, default=""),
    Column("acciones", Dinero, nullable=False, default=Decimal("0")),
    Column("participacion", Tasa, nullable=False, default=Decimal("0")),
    Column("comprometido", Dinero, nullable=False, default=Decimal("0")),
    Column("pagado", Dinero, nullable=False, default=Decimal("0")),
    Column("creado", DateTime(timezone=True), nullable=False, server_default=AHORA),
    Index("socios_cliente_idx", "cliente_id"),
)

# ── 3. PERIODOS ─────────────────────────────────────────────────────────────
periodos = Table(
    "periodos",
    metadatos,
    Column("id", Id, primary_key=True),
    Column("cliente_id", Id, ForeignKey("clientes.id", ondelete="CASCADE"), nullable=False),
    Column("desde", Date, nullable=False),
    Column("hasta", Date, nullable=False),
    Column("etiqueta", Text, default=""),
    Column("estado", Text, nullable=False, default="borrador"),
    Column("total_activo", Dinero),
    Column("total_pasivo", Dinero),
    Column("total_patrimonio", Dinero),
    Column("total_ingresos", Dinero),
    Column("total_gastos", Dinero),
    Column("utilidad", Dinero),
    Column("descuadre", Dinero, nullable=False, default=Decimal("0")),
    # Se guarda aparte, como booleano, a propósito. En SQLite los importes son
    # TEXTO y compararlos dentro del SQL es lexicográfico: "0" != "0.00" da
    # verdadero, y "-5" > "10" también. Cualquier filtro de dinero en SQL es
    # una trampa; este booleano lo evita y además permite indexar.
    Column("cuadra", Boolean, nullable=False, default=True),
    Column("cuentas", Integer, nullable=False, default=0),
    Column("calculado_en", DateTime(timezone=True)),
    Column("cerrado_en", DateTime(timezone=True)),
    # Nota de revisión del contador sobre este periodo (A6).
    Column("nota", Text, default=""),
    Column("creado", DateTime(timezone=True), nullable=False, server_default=AHORA),
    Column("actualizado", DateTime(timezone=True), nullable=False, server_default=AHORA),
    CheckConstraint("hasta >= desde", name="periodos_rango_valido"),
    CheckConstraint("estado in ('borrador','calculado','cerrado')", name="periodos_estado"),
    Index("periodos_unicos", "cliente_id", "desde", "hasta", unique=True),
    Index("periodos_cliente_idx", "cliente_id", "desde"),
)

# ── 4. RESULTADOS ───────────────────────────────────────────────────────────
resultados = Table(
    "resultados",
    metadatos,
    Column("periodo_id", Id, ForeignKey("periodos.id", ondelete="CASCADE"), primary_key=True),
    Column("cliente_id", Id, ForeignKey("clientes.id", ondelete="CASCADE"), nullable=False),
    Column("payload", Json, nullable=False),
    Column("peticion", Json, nullable=False, default=dict),
    Column("version", Text, nullable=False, default="2.0.0"),
    Column("creado", DateTime(timezone=True), nullable=False, server_default=AHORA),
    Index("resultados_cliente_idx", "cliente_id"),
)

# ── 5. MOVIMIENTOS ──────────────────────────────────────────────────────────
movimientos = Table(
    "movimientos",
    metadatos,
    Column("id", Serial, primary_key=True, autoincrement=True),
    Column("cliente_id", Id, ForeignKey("clientes.id", ondelete="CASCADE"), nullable=False),
    Column("periodo_id", Id, ForeignKey("periodos.id", ondelete="CASCADE")),
    Column("fecha", Date),
    Column("cuenta", Text, nullable=False),
    Column("nombre_cuenta", Text, default=""),
    Column("debito", Dinero, nullable=False, default=Decimal("0")),
    Column("credito", Dinero, nullable=False, default=Decimal("0")),
    Column("comprobante", Text, default=""),
    Column("tipo", Text, default=""),
    Column("tercero_id", Text, default=""),
    Column("tercero_nombre", Text, default=""),
    Column("descripcion", Text, default=""),
    Column("origen", Text, default=""),
    Column("base_retencion", Dinero),
    Column("creado", DateTime(timezone=True), nullable=False, server_default=AHORA),
    Index("movimientos_periodo_idx", "periodo_id"),
    Index("movimientos_cuenta_idx", "cliente_id", "cuenta"),
    Index("movimientos_fecha_idx", "cliente_id", "fecha"),
)

# ── 6. CIERRES ──────────────────────────────────────────────────────────────
cierres = Table(
    "cierres",
    metadatos,
    Column("id", Serial, primary_key=True, autoincrement=True),
    Column("cliente_id", Id, ForeignKey("clientes.id", ondelete="CASCADE"), nullable=False),
    Column("periodo_id", Id, ForeignKey("periodos.id", ondelete="SET NULL")),
    Column("fecha_corte", Date, nullable=False),
    Column("saldos", Json, nullable=False),
    Column("cuentas", Integer, nullable=False, default=0),
    Column("creado", DateTime(timezone=True), nullable=False, server_default=AHORA),
    Index("cierres_cliente_idx", "cliente_id", "fecha_corte"),
)

# ── 7. ALIAS DE CUENTAS ─────────────────────────────────────────────────────
alias_cuenta = Table(
    "alias_cuenta",
    metadatos,
    Column("id", Serial, primary_key=True, autoincrement=True),
    Column("cliente_id", Id, ForeignKey("clientes.id", ondelete="CASCADE")),
    Column("nit", Text, nullable=False, default=""),
    Column("nombre_norm", Text, nullable=False),
    Column("codigo", Text, nullable=False),
    Column("veces", Integer, nullable=False, default=1),
    Column("creado", DateTime(timezone=True), nullable=False, server_default=AHORA),
    Index("alias_unico", "nit", "nombre_norm", unique=True),
)

# ── 8. EMPLEADOS ────────────────────────────────────────────────────────────
empleados = Table(
    "empleados",
    metadatos,
    Column("id", Serial, primary_key=True, autoincrement=True),
    Column("cliente_id", Id, ForeignKey("clientes.id", ondelete="CASCADE"), nullable=False),
    Column("nombre", Text, nullable=False),
    Column("cedula", Text, default=""),
    Column("cargo", Text, default=""),
    Column("salario_basico", Dinero, nullable=False, default=Decimal("0")),
    Column("dias", Tasa, nullable=False, default=Decimal("30")),
    Column("aux_transporte", Text, nullable=False, default="auto"),
    Column("clase_riesgo", SmallInteger, nullable=False, default=1),
    Column("activo", Boolean, nullable=False, default=True),
    Column("ingreso", Date),
    Column("retiro", Date),
    Column("creado", DateTime(timezone=True), nullable=False, server_default=AHORA),
    Index("empleados_cliente_idx", "cliente_id"),
)

# ── 9. IMPORTACIONES ────────────────────────────────────────────────────────
importaciones = Table(
    "importaciones",
    metadatos,
    Column("id", Id, primary_key=True),
    Column("cliente_id", Id, ForeignKey("clientes.id", ondelete="CASCADE")),
    Column("archivo", Text, nullable=False),
    Column("hoja", Text, default=""),
    Column("formato", Text, default=""),
    Column("sha256", Text, default=""),
    Column("bytes", BigInteger, nullable=False, default=0),
    Column("filas", Integer, nullable=False, default=0),
    Column("alertas", Integer, nullable=False, default=0),
    Column("creado", DateTime(timezone=True), nullable=False, server_default=AHORA),
    Index("importaciones_cliente_idx", "cliente_id", "creado"),
)

# ── 10. SESIONES DE TRABAJO ─────────────────────────────────────────────────
sesiones = Table(
    "sesiones",
    metadatos,
    Column("id", String(64), primary_key=True),
    Column("cliente_id", Id, ForeignKey("clientes.id", ondelete="CASCADE")),
    Column("payload", Json, nullable=False),
    Column("expira", DateTime(timezone=True), nullable=False),
    Column("creado", DateTime(timezone=True), nullable=False, server_default=AHORA),
    Index("sesiones_expira_idx", "expira"),
)

# ── 11. PARÁMETROS LEGALES ──────────────────────────────────────────────────
parametros_legales = Table(
    "parametros_legales",
    metadatos,
    Column("anio", Integer, primary_key=True, autoincrement=False),
    Column("valores", Json, nullable=False),
    Column("fuente", Text, default=""),
    Column("actualizado", DateTime(timezone=True), nullable=False, server_default=AHORA),
)

# ── 12. BITÁCORA ────────────────────────────────────────────────────────────
bitacora = Table(
    "bitacora",
    metadatos,
    Column("id", Serial, primary_key=True, autoincrement=True),
    Column("cliente_id", Id, ForeignKey("clientes.id", ondelete="SET NULL")),
    Column("accion", Text, nullable=False),
    Column("detalle", Json, nullable=False, default=dict),
    Column("creado", DateTime(timezone=True), nullable=False, server_default=AHORA),
    Index("bitacora_cliente_idx", "cliente_id", "creado"),
)

# ── 13. HISTORIAL DE PERIODOS ───────────────────────────────────────────────
# Antes de reemplazar un resultado, sus movimientos o un cierre, se guarda aquí
# una copia completa. Así un recálculo nunca borra para siempre lo anterior:
# en la ficha se puede ver cada versión y restaurarla (H01 del informe).
historial_periodos = Table(
    "historial_periodos",
    metadatos,
    Column("id", Serial, primary_key=True, autoincrement=True),
    Column("periodo_id", Id, ForeignKey("periodos.id", ondelete="CASCADE"), nullable=False),
    Column("cliente_id", Id, ForeignKey("clientes.id", ondelete="CASCADE"), nullable=False),
    # recalculo · reapertura · restauracion · cierre
    Column("motivo", Text, nullable=False, default=""),
    Column("periodo", Json, nullable=False, default=dict),      # indicadores y estado
    Column("resultado", Json),                                  # payload del motor
    Column("peticion", Json),
    Column("movimientos", Json, nullable=False, default=list),
    Column("cierre", Json),
    Column("cuentas", Integer, nullable=False, default=0),
    Column("creado", DateTime(timezone=True), nullable=False, server_default=AHORA),
    Index("historial_periodo_idx", "periodo_id", "creado"),
)
