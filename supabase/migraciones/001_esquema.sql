-- ════════════════════════════════════════════════════════════════════════════
--  CARLOS CRUZ · esquema contable multi-cliente
--  Pegue este archivo completo en Supabase → SQL Editor → Run.
--  Es idempotente: puede ejecutarlo varias veces sin romper nada.
--
--  Nota sobre exactitud: TODO importe usa NUMERIC(20,2) o NUMERIC(20,6).
--  NUMERIC en Postgres es decimal exacto (igual que Decimal de Python).
--  NUNCA usar float / double precision para dinero.
-- ════════════════════════════════════════════════════════════════════════════

create extension if not exists "pgcrypto";   -- gen_random_uuid()
create extension if not exists "pg_trgm";    -- búsqueda por similitud a escala
create extension if not exists "unaccent";   -- búsqueda sin tildes

-- ── normalizador usado por los índices de búsqueda ─────────────────────────
create or replace function cc_normalizar(t text)
returns text
language sql
immutable
parallel safe
as $func$
  select upper(regexp_replace(unaccent(coalesce(t, '')), '[^A-Za-z0-9 ]+', ' ', 'g'))
$func$;

-- ── 1. CLIENTES ────────────────────────────────────────────────────────────
create table if not exists clientes (
  id                   uuid primary key default gen_random_uuid(),
  nit                  text not null,
  dv                   text default '',
  razon_social         text not null,
  sigla                text default '',
  tipo_persona         text not null default 'juridica'
                         check (tipo_persona in ('juridica', 'natural')),
  regimen              text not null default 'responsable_iva'
                         check (regimen in ('responsable_iva', 'no_responsable_iva',
                                            'gran_contribuyente', 'simple', 'especial')),
  grupo_niif           smallint not null default 3 check (grupo_niif between 1 and 3),
  responsable_iva      boolean not null default true,
  tarifa_renta         numeric(6,4) not null default 0.3500,
  ciiu                 text default '',
  direccion            text default '',
  municipio            text default '',
  departamento         text default '',
  telefono             text default '',
  email                text default '',
  rep_legal            text default '',
  rep_legal_cc         text default '',
  rep_legal_suplente   text default '',
  contador             text default '',
  contador_cc          text default '',
  contador_tp          text default '',
  fecha_constitucion   date,
  capital_suscrito     numeric(20,2) not null default 0,
  valor_nominal_accion numeric(20,2) not null default 0,
  honorarios_mes       numeric(20,2) not null default 0,
  periodicidad         text not null default 'mensual'
                         check (periodicidad in ('mensual', 'bimestral', 'trimestral',
                                                 'cuatrimestral', 'anual')),
  estado               text not null default 'activo'
                         check (estado in ('activo', 'inactivo', 'archivado')),
  etiquetas            text[] not null default '{}',
  notas                text default '',
  demo                 boolean not null default false,
  creado               timestamptz not null default now(),
  actualizado          timestamptz not null default now(),
  constraint clientes_nit_unico unique (nit)
);

-- Columna de búsqueda: NIT + razón social + sigla + municipio + rep. legal + email,
-- todo en mayúsculas y sin tildes. La llena la aplicación en cada insert/update
-- (no es GENERATED para que el mismo código sirva en Postgres y en SQLite local).
alter table clientes add column if not exists buscable text not null default '';

-- Relleno por si quedaron filas de una carga anterior.
update clientes
   set buscable = cc_normalizar(nit || ' ' || razon_social || ' ' || coalesce(sigla, '') || ' ' ||
                                coalesce(municipio, '') || ' ' || coalesce(rep_legal, '') || ' ' ||
                                coalesce(email, ''))
 where buscable = '';

create index if not exists clientes_buscable_trgm on clientes using gin (buscable gin_trgm_ops);
create index if not exists clientes_nit_idx       on clientes (nit);
create index if not exists clientes_estado_idx    on clientes (estado) where estado = 'activo';
create index if not exists clientes_razon_idx     on clientes (razon_social);
create index if not exists clientes_etiquetas_idx on clientes using gin (etiquetas);

-- ── 2. SOCIOS / ACCIONISTAS ────────────────────────────────────────────────
create table if not exists socios (
  id            bigserial primary key,
  cliente_id    uuid not null references clientes(id) on delete cascade,
  nombre        text not null,
  cedula        text default '',
  cargo         text default '',
  acciones      numeric(20,2) not null default 0,
  participacion numeric(9,6)  not null default 0,
  comprometido  numeric(20,2) not null default 0,
  pagado        numeric(20,2) not null default 0,
  creado        timestamptz not null default now()
);
create index if not exists socios_cliente_idx on socios (cliente_id);

-- ── 3. PERIODOS CONTABLES ──────────────────────────────────────────────────
create table if not exists periodos (
  id               uuid primary key default gen_random_uuid(),
  cliente_id       uuid not null references clientes(id) on delete cascade,
  desde            date not null,
  hasta            date not null,
  etiqueta         text default '',
  estado           text not null default 'borrador'
                     check (estado in ('borrador', 'calculado', 'cerrado')),
  -- indicadores resumidos para listar y graficar sin abrir el resultado completo
  total_activo     numeric(20,2),
  total_pasivo     numeric(20,2),
  total_patrimonio numeric(20,2),
  total_ingresos   numeric(20,2),
  total_gastos     numeric(20,2),
  utilidad         numeric(20,2),
  descuadre        numeric(20,2) not null default 0,
  -- Booleano explícito en vez de comparar el importe en SQL. En Postgres
  -- NUMERIC compara bien, pero el mismo código corre contra SQLite, donde los
  -- importes son TEXTO y la comparación sería lexicográfica ("0" <> "0.00").
  cuadra           boolean not null default true,
  cuentas          integer not null default 0,
  calculado_en     timestamptz,
  cerrado_en       timestamptz,
  creado           timestamptz not null default now(),
  actualizado      timestamptz not null default now(),
  constraint periodos_rango_valido check (hasta >= desde),
  constraint periodos_unicos unique (cliente_id, desde, hasta)
);
create index if not exists periodos_cliente_idx on periodos (cliente_id, desde desc);
create index if not exists periodos_estado_idx  on periodos (cliente_id, estado);
create index if not exists periodos_descuadre_idx on periodos (cuadra) where not cuadra;

-- ── 4. RESULTADO COMPLETO DEL PERIODO (snapshot del motor) ─────────────────
create table if not exists resultados (
  periodo_id uuid primary key references periodos(id) on delete cascade,
  cliente_id uuid not null references clientes(id) on delete cascade,
  payload    jsonb not null,            -- balance, estados, mayor, alertas, auditorías
  peticion   jsonb not null default '{}'::jsonb,
  version    text not null default '2.0.0',
  creado     timestamptz not null default now()
);
create index if not exists resultados_cliente_idx on resultados (cliente_id);

-- ── 5. MOVIMIENTOS (libro diario) ──────────────────────────────────────────
create table if not exists movimientos (
  id             bigserial primary key,
  cliente_id     uuid not null references clientes(id) on delete cascade,
  periodo_id     uuid references periodos(id) on delete cascade,
  fecha          date,
  cuenta         text not null,
  nombre_cuenta  text default '',
  debito         numeric(20,2) not null default 0,
  credito        numeric(20,2) not null default 0,
  comprobante    text default '',
  tipo           text default '',
  tercero_id     text default '',
  tercero_nombre text default '',
  descripcion    text default '',
  origen         text default '',
  base_retencion numeric(20,2),
  creado         timestamptz not null default now(),
  constraint movimientos_no_negativos check (debito >= 0 and credito >= 0)
);
create index if not exists movimientos_periodo_idx on movimientos (periodo_id);
create index if not exists movimientos_cuenta_idx  on movimientos (cliente_id, cuenta);
create index if not exists movimientos_fecha_idx   on movimientos (cliente_id, fecha);
create index if not exists movimientos_tercero_idx on movimientos (cliente_id, tercero_id)
  where tercero_id <> '';

-- ── 6. CIERRES (saldos que abren el periodo siguiente) ─────────────────────
create table if not exists cierres (
  id          bigserial primary key,
  cliente_id  uuid not null references clientes(id) on delete cascade,
  periodo_id  uuid references periodos(id) on delete set null,
  fecha_corte date not null,
  saldos      jsonb not null,
  cuentas     integer not null default 0,
  creado      timestamptz not null default now()
);
create index if not exists cierres_cliente_idx on cierres (cliente_id, fecha_corte desc);

-- ── 7. ALIAS DE CUENTAS CONFIRMADOS POR EL CONTADOR ────────────────────────
create table if not exists alias_cuenta (
  id          bigserial primary key,
  cliente_id  uuid references clientes(id) on delete cascade,
  nit         text not null default '',
  nombre_norm text not null,
  codigo      text not null,
  veces       integer not null default 1,
  creado      timestamptz not null default now(),
  constraint alias_unico unique (nit, nombre_norm)
);
create index if not exists alias_nit_idx on alias_cuenta (nit);

-- ── 8. EMPLEADOS (nómina) ──────────────────────────────────────────────────
create table if not exists empleados (
  id             bigserial primary key,
  cliente_id     uuid not null references clientes(id) on delete cascade,
  nombre         text not null,
  cedula         text default '',
  cargo          text default '',
  salario_basico numeric(20,2) not null default 0,
  dias           numeric(6,2)  not null default 30,
  aux_transporte text not null default 'auto' check (aux_transporte in ('auto', 'si', 'no')),
  clase_riesgo   smallint not null default 1 check (clase_riesgo between 1 and 5),
  activo         boolean not null default true,
  ingreso        date,
  retiro         date,
  creado         timestamptz not null default now()
);
create index if not exists empleados_cliente_idx on empleados (cliente_id) where activo;

-- ── 9. IMPORTACIONES (historial de archivos subidos) ───────────────────────
create table if not exists importaciones (
  id         uuid primary key default gen_random_uuid(),
  cliente_id uuid references clientes(id) on delete cascade,
  archivo    text not null,
  hoja       text default '',
  formato    text default '',
  sha256     text default '',
  bytes      bigint not null default 0,
  filas      integer not null default 0,
  alertas    integer not null default 0,
  creado     timestamptz not null default now()
);
create index if not exists importaciones_cliente_idx on importaciones (cliente_id, creado desc);

-- ── 10. SESIONES DE TRABAJO (reemplaza el estado en memoria RAM) ───────────
create table if not exists sesiones (
  id         text primary key,
  cliente_id uuid references clientes(id) on delete cascade,
  payload    jsonb not null,
  expira     timestamptz not null default (now() + interval '12 hours'),
  creado     timestamptz not null default now()
);
create index if not exists sesiones_expira_idx on sesiones (expira);

-- ── 11. PARÁMETROS LEGALES POR AÑO (SMMLV, aportes, etc.) ──────────────────
create table if not exists parametros_legales (
  anio        integer primary key,
  valores     jsonb not null,
  fuente      text default '',
  actualizado timestamptz not null default now()
);

-- ── 12. BITÁCORA (auditoría de cambios) ────────────────────────────────────
create table if not exists bitacora (
  id         bigserial primary key,
  cliente_id uuid references clientes(id) on delete set null,
  accion     text not null,
  detalle    jsonb not null default '{}'::jsonb,
  creado     timestamptz not null default now()
);
create index if not exists bitacora_cliente_idx on bitacora (cliente_id, creado desc);

-- ── mantener "actualizado" al día ──────────────────────────────────────────
create or replace function cc_touch() returns trigger language plpgsql as $func$
begin
  new.actualizado = now();
  return new;
end
$func$;

drop trigger if exists clientes_touch on clientes;
create trigger clientes_touch before update on clientes
  for each row execute function cc_touch();

drop trigger if exists periodos_touch on periodos;
create trigger periodos_touch before update on periodos
  for each row execute function cc_touch();

-- ── vista de cartera: último periodo y antigüedad por cliente ──────────────
create or replace view v_clientes_resumen as
select c.id,
       c.nit,
       c.razon_social,
       c.sigla,
       c.municipio,
       c.estado,
       c.etiquetas,
       c.honorarios_mes,
       c.periodicidad,
       count(p.id)                                             as periodos,
       count(p.id) filter (where p.estado = 'cerrado')          as periodos_cerrados,
       max(p.hasta)                                            as ultimo_corte,
       (array_agg(p.utilidad     order by p.hasta desc nulls last))[1] as ultima_utilidad,
       (array_agg(p.total_activo order by p.hasta desc nulls last))[1] as ultimo_activo,
       (array_agg(p.descuadre    order by p.hasta desc nulls last))[1] as ultimo_descuadre
from clientes c
left join periodos p on p.cliente_id = c.id
group by c.id;
