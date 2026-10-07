# Supuestos — Sistema contable FANANT

Cada supuesto queda como **parámetro configurable** con un valor por defecto. Cuando el cliente confirme, se actualiza la columna "Estado".
Estados: 🟡 pendiente de confirmar · 🟢 confirmado · 🔵 decisión técnica (no requiere al cliente).

## Empresa y periodo

| ID | Supuesto | Parámetro | Valor por defecto | Estado |
|---|---|---|---|---|
| S-01 | El primer ejercicio empieza con el registro mercantil. El EF dice "15 a 31 de diciembre de 2024"; el acta es del 26-nov-2024 | `empresa.inicio_primer_ejercicio` | 2024-12-15 | 🟡 Pedir la fecha exacta del certificado de Cámara de Comercio |
| S-02 | Los movimientos de `cuenta T` / `HojaTRABAJO 01--02--03` son de FANANT, aunque el título diga 2012 | `importador.periodo` (el usuario lo elige en la vista previa) | Lo pregunta la app al importar | 🟡 ¿A qué meses corresponden? |
| S-03 | Grupo NIIF | `empresa.grupo_niif` | **3 (Microempresa)**: empresa nueva, capital de 30M y 1 empleado. El flujo de efectivo se genera igual, marcado como "opcional" | 🟡 |
| S-04 | Responsable de IVA | `empresa.responsable_iva` | **Sí** (el RUT declara la responsabilidad 48). Tarifa por producto: excluido / 5 % / 19 %, parametrizable | 🟡 |
| S-05 | Los "ingresos" de 22.641 de `cuenta T` son rendimientos o pruebas, no ventas | — | Se importan como 4135 tal cual y se muestra una alerta informativa | 🟡 |
| S-06 | Auditar los EF existentes | `auditor_ef.habilitado` | Sí. Importador de "estado financiero existente" que solo **audita** (E1, E2, E3, E19–E21) y no alimenta el mayor | 🔵 |
| S-07 | Capital de 30M efectivamente pagado | `empresa.capital_pagado` | 30.000.000 según estatutos. Las alertas E3, E5 y E18 quedan visibles hasta que se concilie | 🟡 Crítico: el libro de aportes dice pagado 0 |
| S-13 | Domicilio | `empresa.direccion` | Calle 8 No. 9-86, B/ El Limonar, Guacarí (estatutos). "Guabitas" no se usa | 🟡 |
| S-14 | "Luz Adriana Durán" (libro de aportes) = Adriana Durán Jaramillo, CC [CEDULA] | alias de tercero | Misma persona | 🟡 |

## Contabilidad

| ID | Supuesto | Parámetro | Valor por defecto | Estado |
|---|---|---|---|---|
| S-08 | Cuenta de las provisiones mensuales de nómina | `nomina.cuenta_provisiones` | `25` (2510, 2515, 2520, 2525), práctica NIIF. Alternativa `26` (2610) | 🟡 Preguntar al contador cuál usa |
| S-09 | Pasivo corriente frente a no corriente | `ef.plazo_corriente_meses` | 12 meses. Sin fecha de vencimiento, todo pasivo es corriente | 🔵 |
| S-15 | Tabla PUC con las correcciones de `ANALISIS_FUENTES.md` §7 | `data/puc.json` | Semovientes 1584 · Comisiones 4225 · Socios 1325 · Cooperativa 2195 | 🟡 Validar con el contador |
| S-16 | Aritmética | — | `Decimal` en todo el cálculo; redondeo a pesos solo al presentar (ROUND_HALF_UP) | 🔵 |
| S-17 | Periodicidad de los reportes | `reportes.periodo` | Rango libre desde/hasta (sirve para mensual, bimestral o anual). Por defecto mensual | 🟡 |
| S-18 | Impuesto de renta | `renta.tarifa`, `renta.calcular` | 35 %, **desactivado**. Solo se ofrece al cierre anual | 🟡 |
| S-19 | Reserva legal | `reserva.porcentaje`, `reserva.tope` | 10 % de la utilidad líquida hasta el 50 % del capital suscrito (art. 33). Se presenta como propuesta de distribución, no como gasto | 🟢 (estatutos) |
| S-20 | Retención en la fuente sobre honorarios (el contador cobra 300.000/mes; FANANT es agente de retención, responsabilidad 07) | `retencion.honorarios_tarifa` | Parametrizable, sin valor cargado. La app avisa si hay honorarios sin retención | 🟡 |

## Inventario

| ID | Supuesto | Parámetro | Valor por defecto | Estado |
|---|---|---|---|---|
| S-21 | Método de valoración | `inventario.metodo` | Promedio ponderado (PEPS disponible) | 🟡 |
| S-22 | Sistema | `inventario.sistema` | Permanente (kardex). Si solo hay conteo físico, se usa el periódico | 🟡 ¿Hacen conteo físico? |
| S-23 | Alertas de vencimiento | `inventario.alertas_dias` | 30 / 60 / 90 | 🔵 |

## Nómina

| ID | Supuesto | Parámetro | Valor por defecto | Estado |
|---|---|---|---|---|
| S-10 | Jornada máxima legal para el valor hora (Ley 2101 de 2021: 46 h hasta el 14-jul-2025, 44 h desde el 15-jul-2025, 42 h desde el 15-jul-2026) | `parametros_legales[año].jornada` por tramos de fecha | 2025: 46 h → 44 h. Horas por mes = jornada semanal × 5 (230 / 220) | 🟡 Verificar la regla de horas por mes con el contador |
| S-11 | Auxilio de transporte | `nomina.aux_transporte` | Si el salario es ≤ 2 SMMLV, proporcional a los días trabajados. También para trabajadores por horas | 🟢 (ley) |
| S-12 | Exoneración del art. 114-1 E.T. (salud 8,5 %, SENA e ICBF) | `nomina.exonerado_114_1` | **Activada** (persona jurídica declarante de renta, trabajador con menos de 10 SMMLV). La caja 4 % se paga siempre | 🟡 |
| S-24 | Base de los aportes del empleador y de los parafiscales | — | IBC = salario **sin** auxilio de transporte (corrige E12 del PROMPT) | 🟢 (ley) |
| S-25 | Intereses sobre cesantías | — | Provisión mensual del 1 % de (salario + aux.) = 12 % anual | 🟢 |
| S-26 | ARL | `nomina.clase_riesgo` | Clase I, 0,522 % (cargo administrativo) | 🟡 |
| S-27 | Parámetros legales por año | `data/parametros_legales.json` | Solo se carga **2025**: SMMLV 1.423.500 y aux. 200.000. **2026 no se carga**: lo ingresa el usuario (regla del PROMPT: no inventar valores) | 🟡 Pedir los valores de 2026 si hay periodos de 2026 |
| S-28 | Redondeo de los aportes a la PILA (al múltiplo de 100 superior) | `nomina.redondeo_pila` | Desactivado, para que coincida con las cifras de los tests. Activable | 🔵 |

## Técnicos

| ID | Supuesto | Valor |
|---|---|---|
| T-01 | Carpeta del proyecto | `C:\Users\Admin\Documents\DON CARLOS\sistema-contable-fanant` (los originales del cliente quedan intactos en `FARMACIA NATURISTA ANTARES SAS\`) |
| T-02 | Entorno disponible | Python 3.12.10 (`C:\Users\Admin\AppData\Local\Programs\Python\Python312\python.exe`; el `python` del PATH es otro venv), Node 20.18, npm 10.8, Docker 29.4, Git 2.54 |
| T-03 | Ejecución | Script `iniciar.bat` como vía principal (sin exigir Docker). `docker compose` como alternativa |
| T-04 | PDF | ReportLab (WeasyPrint necesita GTK en Windows, lo que complica la instalación del contador) |
| T-05 | Fixture del Test 4 | Balance de prueba sintético con las cifras de EF Hoja2 (ver `ANALISIS_FUENTES.md` §4) |

## Decisiones tomadas durante el desarrollo

| ID | Supuesto | Valor por defecto | Estado |
|---|---|---|---|
| S-29 | Depreciación | Línea recta **desde el mes siguiente a la compra**; los terrenos (1504) no se deprecian | 🔵 |
| S-30 | Periodo sugerido al importar | 1) hoja EMPRESA de la plantilla; 2) mes de la nómina incluida; 3) datos de la empresa. Siempre editable | 🔵 |
| S-31 | Causación de nómina | Se acepta por defecto solo si el diario no trae gastos de personal (5105); si los trae, se propone sin aceptar para no duplicar. Las provisiones y aportes siempre se aceptan | 🔵 |
| S-32 | Horas mensuales para el valor hora | Jornada semanal legal × 5 (enero 2025: 46 h → 230 h) | 🟡 |
| S-33 | Mapeo de «GTO SEGURIDAD SOCIAL», «GASTOS DE PERSONAL» y «gastos administración» | 5105 / 5105 / 5195 (nivel cuenta, sin inventar subcuenta) | 🟡 |
| S-34 | Hoja «cuenta T» y «HojaTRABAJO 01--02--03» de CONTABILIDAD.xls | Son los mismos movimientos: se usa la hoja de trabajo (trae saldos iniciales) y la cuenta T queda desmarcada | 🔵 |
| S-35 | Datos de demostración | Ficticios y marcados «DEMO» en pantalla, Excel y PDF. Solo son reales los datos de la empresa, la nómina de la representante legal y los honorarios del contador | 🔵 |
