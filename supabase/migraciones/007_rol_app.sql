-- ════════════════════════════════════════════════════════════════════════════
--  CARLOS CRUZ · rol de MÍNIMO PRIVILEGIO para la aplicación (v2.3 · Fase 6, control C31).
--  Ejecute DESPUÉS de 006_acceso.sql, con el usuario administrador (postgres) en el editor SQL.
--
--  La aplicación solo lee y escribe filas de SUS tablas: no crea ni borra tablas, no toca
--  otros esquemas ni la autenticación de Supabase. Las migraciones (este directorio) se
--  corren con el usuario administrador; la aplicación, con este rol.
--
--  1. Cambie 'CAMBIE-ESTA-CLAVE' por una contraseña larga y aleatoria.
--  2. Ejecute este archivo.
--  3. En la aplicación, ponga DATABASE_URL con el usuario  carloscruz_app.<ref-del-proyecto>
--     (el formato del pooler de Supabase) y esa contraseña. Al abrirla, la conexión se guarda en el
--     Administrador de credenciales de Windows y se borra del archivo de texto.
-- ════════════════════════════════════════════════════════════════════════════

do $$
begin
  if not exists (select 1 from pg_roles where rolname = 'carloscruz_app') then
    create role carloscruz_app login password 'CAMBIE-ESTA-CLAVE'
      nosuperuser nocreatedb nocreaterole noinherit noreplication nobypassrls;
  end if;
end $$;

grant usage on schema public to carloscruz_app;
revoke create on schema public from carloscruz_app;

grant select, insert, update, delete on
  clientes, socios, periodos, resultados, movimientos, cierres, alias_cuenta, empleados,
  importaciones, sesiones, parametros_legales, bitacora, historial_periodos,
  renta_declaraciones, renta_versiones, renta_recortes,
  usuarios, codigos_recuperacion, sesiones_acceso
to carloscruz_app;

grant usage, select on all sequences in schema public to carloscruz_app;

-- RLS: la aplicación es el único cliente de la base; el rol propio pasa por políticas explícitas.
do $$
declare t text;
begin
  foreach t in array array['clientes','socios','periodos','resultados','movimientos','cierres','alias_cuenta',
    'empleados','importaciones','sesiones','parametros_legales','bitacora','historial_periodos',
    'renta_declaraciones','renta_versiones','renta_recortes','usuarios','codigos_recuperacion','sesiones_acceso']
  loop
    execute format('drop policy if exists app_todo on %I', t);
    execute format('create policy app_todo on %I for all to carloscruz_app using (true) with check (true)', t);
  end loop;
end $$;
