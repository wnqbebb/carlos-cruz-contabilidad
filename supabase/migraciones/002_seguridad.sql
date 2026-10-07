-- ════════════════════════════════════════════════════════════════════════════
--  CARLOS CRUZ · seguridad de la base (RLS)
--  Ejecute este archivo DESPUÉS de 001_esquema.sql.
--
--  Modelo de acceso elegido:
--    · El backend se conecta con la cadena DATABASE_URL (rol dueño) y por eso
--      NO queda sujeto a RLS. Toda la lógica de permisos vive en el backend.
--    · Las claves públicas (anon / authenticated) quedan BLOQUEADAS. Así, si
--      alguien obtiene la clave anon del frontend, no puede leer ni un cliente.
--
--  Si más adelante quiere que el frontend lea directo de Supabase, se agregan
--  políticas aquí; hoy la postura es "cerrado por defecto".
-- ════════════════════════════════════════════════════════════════════════════

alter table clientes           enable row level security;
alter table socios             enable row level security;
alter table periodos           enable row level security;
alter table resultados         enable row level security;
alter table movimientos        enable row level security;
alter table cierres            enable row level security;
alter table alias_cuenta       enable row level security;
alter table empleados          enable row level security;
alter table importaciones      enable row level security;
alter table sesiones           enable row level security;
alter table parametros_legales enable row level security;
alter table bitacora           enable row level security;

-- Sin políticas definidas + RLS activo = nadie que pase por RLS puede leer.
-- Revocamos además los permisos de tabla para las claves públicas.
revoke all on all tables    in schema public from anon, authenticated;
revoke all on all sequences in schema public from anon, authenticated;
revoke all on all functions in schema public from anon, authenticated;

-- Y para las tablas que se creen en el futuro.
alter default privileges in schema public revoke all on tables    from anon, authenticated;
alter default privileges in schema public revoke all on sequences from anon, authenticated;

-- Limpieza automática de sesiones vencidas (se puede programar con pg_cron).
create or replace function cc_limpiar_sesiones() returns integer language plpgsql as $func$
declare borradas integer;
begin
  delete from sesiones where expira < now();
  get diagnostics borradas = row_count;
  return borradas;
end
$func$;
