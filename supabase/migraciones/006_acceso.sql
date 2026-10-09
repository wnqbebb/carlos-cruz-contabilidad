-- ════════════════════════════════════════════════════════════════════════════
--  CARLOS CRUZ · acceso seguro (v2.3 · Fase 6). Ejecute DESPUÉS de 005_renta.sql.
--  Es idempotente. La aplicación también las crea sola al arrancar (create_all).
--
--  - usuarios: el usuario del contador; la contraseña en Argon2id (nunca en claro);
--    el secreto de la verificación en dos pasos, cifrado con AES-256-GCM.
--  - codigos_recuperacion: solo el hash de cada código (de un solo uso).
--  - sesiones_acceso: solo el hash del token de la cookie; vencimiento e inactividad.
-- ════════════════════════════════════════════════════════════════════════════

create table if not exists usuarios (
  id              bigserial primary key,
  usuario         text not null unique,
  hash            text not null,
  totp_secreto    text,
  totp_pendiente  text,
  totp_activo     boolean not null default false,
  clave_cambiada  timestamptz,
  creado          timestamptz not null default now()
);

create table if not exists codigos_recuperacion (
  id          bigserial primary key,
  usuario_id  bigint not null references usuarios(id) on delete cascade,
  hash        text not null,
  usado       timestamptz,
  creado      timestamptz not null default now()
);

create table if not exists sesiones_acceso (
  id             text primary key,
  usuario_id     bigint not null references usuarios(id) on delete cascade,
  csrf           text not null,
  creada         timestamptz not null default now(),
  ultima         timestamptz not null default now(),
  expira         timestamptz not null,
  reautenticada  timestamptz,
  ip             text default '',
  agente         text default '',
  revocada       boolean not null default false
);
create index if not exists sesiones_usuario_idx on sesiones_acceso (usuario_id);

alter table usuarios             enable row level security;
alter table codigos_recuperacion enable row level security;
alter table sesiones_acceso      enable row level security;
revoke all on usuarios             from anon, authenticated;
revoke all on codigos_recuperacion from anon, authenticated;
revoke all on sesiones_acceso      from anon, authenticated;
