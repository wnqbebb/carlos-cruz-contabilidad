-- ════════════════════════════════════════════════════════════════════════════
--  CARLOS CRUZ · entrada de cada periodo (rescate, octubre 2026)
--  Ejecute DESPUÉS de 007_rol_app.sql, con el usuario administrador. Es idempotente.
--
--  POR QUÉ EXISTE
--  Cada periodo guardaba el resultado entero del motor (≈140 KB, 82 % de reportes ya
--  formateados) y los archivos subidos se borraban a las 8 horas. Así no se podía editar
--  nada dentro de la aplicación y 10.000 clientes no cabían en el plan gratuito.
--  Ahora se guarda lo que recibió el motor (movimientos, saldos, inventario, nómina…)
--  en JSON comprimido; el resultado se guarda liviano y los reportes se recalculan.
--  Medido en Postgres con los 5 clientes de demostración: de 6,2 MB a 3,9 MB.
-- ════════════════════════════════════════════════════════════════════════════

create table if not exists periodo_entradas (
  periodo_id   uuid primary key references periodos(id) on delete cascade,
  cliente_id   uuid not null references clientes(id) on delete cascade,
  contenido    bytea not null,          -- zlib(JSON) · ver backend/app/contabilidad/entrada.py
  bytes        integer not null default 0,
  actualizado  timestamptz not null default now()
);
create index if not exists periodo_entradas_cliente_idx on periodo_entradas (cliente_id);

-- Una versión del historial guarda solo la entrada: pocos KB en vez de copiar todo.
alter table historial_periodos add column if not exists entrada bytea;

alter table periodo_entradas enable row level security;
revoke all on periodo_entradas from anon, authenticated;

do $$
begin
  if exists (select 1 from pg_roles where rolname = 'carloscruz_app') then
    grant select, insert, update, delete on periodo_entradas to carloscruz_app;
    drop policy if exists app_todo on periodo_entradas;
    create policy app_todo on periodo_entradas for all to carloscruz_app using (true) with check (true);
  end if;
end $$;
