-- ════════════════════════════════════════════════════════════════════════════
--  CARLOS CRUZ · ficha completa del cliente y nota de revisión del periodo (v2.2)
--  Ejecute este archivo DESPUÉS de 003_historial.sql. Es idempotente.
--
--  La aplicación agrega estas columnas sola al arrancar si faltan
--  (backend/app/db.py · _columnas_nuevas). Este archivo es el equivalente
--  manual, por si se prefiere aplicarlo desde el editor SQL de Supabase.
--  Todas son opcionales o con valor por defecto: ningún dato cambia.
-- ════════════════════════════════════════════════════════════════════════════

alter table clientes add column if not exists tipo_sociedad          text default '';
alter table clientes add column if not exists objeto_social          text default '';
alter table clientes add column if not exists documento_constitucion text default '';
alter table clientes add column if not exists capital_autorizado     numeric(20,2) not null default 0;
alter table clientes add column if not exists capital_pagado         numeric(20,2) not null default 0;
alter table clientes add column if not exists numero_acciones        numeric(20,2) not null default 0;
alter table clientes add column if not exists rep_legal_suplente_cc  text default '';
alter table clientes add column if not exists revisor_fiscal         text default '';
alter table clientes add column if not exists revisor_fiscal_tp      text default '';
alter table clientes add column if not exists matricula_mercantil    text default '';
alter table clientes add column if not exists fecha_renovacion       date;
alter table clientes add column if not exists ciiu_secundarios       text default '';
alter table clientes add column if not exists responsabilidades      text default '';

-- Nota de revisión del contador sobre un periodo (p. ej. «pendiente de revisión»).
alter table periodos add column if not exists nota text default '';
