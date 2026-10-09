-- ════════════════════════════════════════════════════════════════════════════
--  CARLOS CRUZ · declaración de renta de personas naturales, formulario 210 (v2.3)
--  Ejecute este archivo DESPUÉS de 004_ficha_y_notas.sql. Es idempotente.
--
--  La aplicación crea estas tablas sola al arrancar si faltan (create_all).
--  Este archivo es el equivalente manual para el editor SQL de Supabase.
-- ════════════════════════════════════════════════════════════════════════════

create table if not exists renta_declaraciones (
  id           uuid primary key,
  cliente_id   uuid not null references clientes(id) on delete cascade,
  anio         smallint not null,
  -- sin_informacion · borrador · revisada · presentada
  estado       text not null default 'sin_informacion',
  datos        jsonb not null default '{}'::jsonb,   -- líneas leídas, respuestas, beneficios, datos agregados
  resultado    jsonb,                                -- último cálculo (casillas del 210, comparación DIAN)
  presentada   jsonb,                                -- número de formulario y fecha
  creado       timestamptz not null default now(),
  actualizado  timestamptz not null default now()
);
create unique index if not exists renta_cliente_anio_idx on renta_declaraciones (cliente_id, anio);

-- Historial: cada cambio de la declaración deja una versión.
create table if not exists renta_versiones (
  id              bigserial primary key,
  declaracion_id  uuid not null references renta_declaraciones(id) on delete cascade,
  motivo          text not null default '',
  datos           jsonb not null default '{}'::jsonb,
  resultado       jsonb,
  creado          timestamptz not null default now()
);
create index if not exists renta_versiones_idx on renta_versiones (declaracion_id, creado desc);

-- Recortes de la tabla leída por OCR (una fila por imagen). Nunca la foto completa.
create table if not exists renta_recortes (
  id              text primary key,
  declaracion_id  uuid not null references renta_declaraciones(id) on delete cascade,
  png             bytea not null,
  creado          timestamptz not null default now()
);

-- Misma postura que el resto de tablas: cerradas para las claves públicas.
-- Solo el backend (rol de servicio) lee y escribe.
alter table renta_declaraciones enable row level security;
alter table renta_versiones     enable row level security;
alter table renta_recortes      enable row level security;
revoke all on renta_declaraciones from anon, authenticated;
revoke all on renta_versiones     from anon, authenticated;
revoke all on renta_recortes      from anon, authenticated;
