-- ════════════════════════════════════════════════════════════════════════════
--  CARLOS CRUZ · historial de periodos (v2.2)
--  Ejecute este archivo DESPUÉS de 002_seguridad.sql.
--  Es idempotente: puede ejecutarlo varias veces sin romper nada.
--
--  POR QUÉ EXISTE
--  Hasta la v2.1, recalcular un periodo BORRABA el resultado y los movimientos
--  anteriores sin dejar copia. El 6 de octubre de 2026 un archivo sin cuentas
--  reemplazó así el cierre de enero 2025 de un cliente. Desde ahora, antes de
--  reemplazar nada se guarda una versión completa aquí, y se puede restaurar.
-- ════════════════════════════════════════════════════════════════════════════

create table if not exists historial_periodos (
  id           bigserial primary key,
  periodo_id   uuid not null references periodos(id) on delete cascade,
  cliente_id   uuid not null references clientes(id) on delete cascade,
  -- por qué se guardó esta versión: recalculo · reapertura · restauracion · cierre
  motivo       text not null default '',
  periodo      jsonb not null default '{}'::jsonb,   -- indicadores y estado de entonces
  resultado    jsonb,                                -- payload completo del motor
  peticion     jsonb,
  movimientos  jsonb not null default '[]'::jsonb,   -- libro diario de esa versión
  cierre       jsonb,                                -- saldos de cierre, si los había
  cuentas      integer not null default 0,
  creado       timestamptz not null default now()
);

create index if not exists historial_periodo_idx on historial_periodos (periodo_id, creado desc);
create index if not exists historial_cliente_idx on historial_periodos (cliente_id, creado desc);

-- Misma postura de seguridad que el resto: cerrado para las claves públicas.
alter table historial_periodos enable row level security;
revoke all on historial_periodos from anon, authenticated;
