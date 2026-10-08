# Fase 4 · Registros auxiliares, contabilidad en PDF y Word, libro diario suelto

Capturas: `docs/v22/capturas/fase-4/`. Todo probado en la copia aislada (puerto 8001, SQLite desechable). La base real no se tocó.

## El problema que se cierra
Un negocio pequeño no lleva partida doble: lleva **listas**. Ventas del mes, compras, gastos, lo que le deben, lo que debe, un conteo de la mercancía. Hasta ahora esas listas caían en «No reconocí lo que trae». Ahora se reconocen por su **contenido** y se convierten en asientos.

## Qué se hizo

### 1. Importador de registros auxiliares (`importadores/auxiliares.py`)
- **Detecta por contenido**: una fila con un rol descriptivo (fecha, tercero, producto, concepto) y uno de valor (cantidad, precio, total, abono, saldo). Los encabezados se reconocen con sinónimos, en cualquier orden y **con errores de escritura** (`importadores/encabezados.py`: «CANTIDA», «PROVEDOR», «V/R UNIT»…).
- **Tolera** títulos encima, encabezados fuera de la fila 1, **varios bloques por hoja** (uno por mes), **dos tablas lado a lado** (ventas a la izquierda, compras a la derecha), **una hoja por mes** (el mes sale del nombre de la hoja), filas de totales y subtotales sin rótulo, filas vacías o en cero, números como texto con `$`, puntos de miles y comas decimales, y la fecha escrita como solo el día.
- **Tipos**: ventas, compras, gastos, cartera, cuentas por pagar e inventario (inicial o conteo físico). Si una lista con fechas no dice qué es, **se pregunta** en vez de ignorarla.

### 2. Problemas de calidad: se detectan y se explican, nunca se corrigen en silencio
| Problema (4.2) | Qué hace la aplicación |
|---|---|
| 1 · Columnas mal rotuladas | Si total = A × B, A y B son cantidad y precio aunque digan otra cosa; si están cruzadas, el tamaño de los números lo delata. Aviso con la explicación |
| 2 · Fechas incoherentes | Fechas que no son del mes del título o están en el futuro → pregunta (sugerida: la del título; cruzar día y mes si así cae en el rango) |
| 3 · Títulos y años mal escritos | «ENRO 2O26» se lee como enero de 2026, con aviso |
| 4 · Datos solo en la primera fila | Forma de pago, tercero o fecha → pregunta «¿aplica a las demás?» (sugerida: sí) |
| 5 · Inventario insuficiente | El costo se registra solo hasta lo disponible; aviso con mes y producto, sin inventar costo |
| 6 · Márgenes anómalos | Precio más de 5 veces o menos de la mitad del costo → aviso de posible unidad distinta |
| 7 · Terceros de cartera/CxP desconocidos | Una pregunta por hoja: saldo anterior (sugerida), venta o compra a crédito adicional, o ya incluida (reclasificación de caja) |
| 8 · Sin saldos iniciales | Aviso: caja y capital en 0, con la opción de cargar un balance de apertura |
| 9 · Hojas que prometen y no traen | Aviso informativo |

Todas las preguntas van juntas en el panel **«Preguntas sobre este archivo»**, con la respuesta sugerida marcada y el botón **«Usar las respuestas sugeridas y calcular»**.

### 3. Asientos (4.3)
Cada registro es un comprobante (`VTA-0001`, `CMP-`, `GTO-`, `REC-`, `PAG-`, `RCL-` para reclasificaciones), con fecha, tercero, descripción y **origen exacto** (archivo, hoja y fila). La fila original queda guardada con el resultado (`origenes`) para verla desde el libro diario. El costo de cada venta va en su mismo comprobante (D 6135 · C 1435) al costo promedio, con el mismo kardex que usa el motor, así no aparece un ajuste de costo de ventas duplicado. Los gastos proponen su cuenta PUC por concepto (arriendo 512010, energía 513530…) y el contador la puede cambiar en el mapeo. El IVA se discrimina solo si el archivo lo trae y la ficha dice que el cliente es responsable.

**Periodización**: si el archivo cubre varios meses, se ofrece «Procesar mes a mes, cerrando cada uno» (sugerido, según la periodicidad del cliente: bimestral = ene-feb, mar-abr…) o «Un solo periodo». El cierre de cada mes abre el siguiente, y el kardex de cada mes arranca con lo que dejó el anterior. **El último queda calculado, sin cerrar**, para que el contador lo revise y lo cierre él (decisión propia: anotada abajo). Un periodo que ya estaba cerrado no se toca.

### 4. Contabilidad dentro de PDF y Word (H04)
- **Balance de prueba o listado de saldos** en Excel, tabla de Word o PDF (`importadores/balance.py`): se toman solo las cuentas sin subcuentas en la lista (la clase, el grupo y la cuenta padre son subtotales). Con encabezados se usan saldo anterior, débitos, créditos y saldo final; sin ellos (PDF de texto) un valor se toma como saldo del lado de la naturaleza y cuatro valores solo si la aritmética cuadra. La fecha de corte sale del título («A 31 DE MARZO DE 2026»).
- **Tablas en PDF y Word** entran al mismo detector que las hojas de Excel.
- **PDF escaneado**: «es una imagen del papel… pida el archivo original».
- El lector de PDF ya no convierte importes a `float` (seguía haciéndolo; la prueba que lo exigía se corrigió a `Decimal`).

### 5. Libro diario suelto (P01) — `importadores/libro_diario.py`
Fecha, comprobante, cuenta, tercero, descripción, débito y crédito, con los encabezados en cualquier orden. La cuenta puede venir como código o como nombre. Se distingue de un balance porque trae fecha o comprobante y no trae saldos.

### 6. Adiciones de la revisión externa en esta fase
- **A1** (`identidad.py`): el nombre del archivo pierde las palabras de ruido aunque estén mal escritas (parecido ≥ 85 por letra **y por sonido**: «CANTABILIDAD», «VENTAZ», «CONTAVILIDAD»), más PYME, MIPYME, MICROEMPRESA, NEGOCIO, EMPRESA. 12 pruebas, incluidas tres que comprueban que no se come el nombre del negocio («COMERCIAL», «FINCA», «MARIA»).
- **A4** (`motor.py`, `Resultados.tsx`): causación de nómina aceptada con 5105 ya en el diario → advertencia «Posible doble registro del salario» con las dos cifras, visible junto al botón de cierre, que cambia a «Cerrar de todos modos».
- **H07** (`detector.py`, `motor.py`): si la hoja de trabajo y la cuenta T coinciden cuenta por cuenta (comparadas por código PUC), se usan los saldos iniciales de una y el detalle de la otra: FANANT pasa de 6 movimientos agregados a 29 con el mismo resultado (−653.215).

### Defecto encontrado en el recorrido y corregido
La captura del panel mostró que el nombre del cliente se tomaba de **un proveedor de la lista** («POSTOBON SA | 200.000 | 50.000»). Una fila con importes es un registro, no una línea de identidad: ya no se usa para el nombre. Prueba nueva.

## Banco de archivos (`backend/tests/archivos_variados/`, 19 archivos, generador reproducible)
| Archivo | Lo que prueba | Cifra de control (a mano) |
|---|---|---|
| 01 ventas y compras en bloques | encabezados en otro orden, totales, mes a mes | utilidad 40.000 (ene 25.000 · feb 15.000) |
| 02 columnas mal rotuladas | REFERENCIA = cantidad; cantidad y precio cruzados | ingresos 108.000 |
| 03 fechas copiadas y futuras | preguntas de fechas y respuestas alternativas | ene 70.000 · feb 105.000 |
| 04 totales mezclados | $, comas, subtotales, filas en cero | inventario 2.350.000,50 |
| 05 hojas vacías | hojas vacías y una que promete compras | ingresos 12.000 |
| 06 cartera con terceros desconocidos | saldo anterior, abonos, reclasificación | activo 210.000 · pasivo 150.000 |
| 07 gastos en CSV sin NIT | pide solo el NIT; cuentas por concepto | utilidad −2.388.800 |
| 08 balance de prueba en PDF | cuentas padre, fecha de corte | activo 5.500.000 · utilidad 500.000 |
| 08b ventas en tabla de PDF | tabla con líneas | ingresos 60.000 |
| 09 ventas en Word | identidad en párrafos, cifras en la tabla | ingresos 160.000 |
| 10 PDF escaneado | no inventa nada | mensaje claro |
| 11 libro diario CSV | P01, mes a mes | utilidad 400.000 (1.000.000 · −600.000) |
| 12 inventario insuficiente | costo hasta lo disponible, margen | costo 220.000 · utilidad 82.500 |
| 13 datos repetidos | forma de pago y proveedor solo arriba | pasivo 72.000 (o 20.000 si «no») |
| 14 títulos mal escritos | ENRO 2O26, FEBERO, solo el día | 30.000 · 30.000 |
| 15 inventario inicial y conteo | apertura, faltante físico | utilidad 8.000 · inventario 18.000 |
| 16 balance en Excel | saldo anterior + movimientos | patrimonio 1.200.000 |
| 17 hoja por mes, tablas lado a lado | carriles de columnas, mes del nombre de la hoja | caja 29.000 |
| 18 listas sin tipo | se pregunta; sugerencia por concepto | utilidad −580.000 |

Cada prueba comprueba además la **partida doble comprobante por comprobante**, leyendo el libro diario guardado.

## Verificación
| Comprobación | Resultado |
|---|---|
| Pruebas del backend | ✅ **182** (145 al empezar + 37 nuevas) |
| `tsc --noEmit` | ✅ limpio |
| `npm run lint:diseno` | ✅ 0 infracciones |
| `npm run build` | ✅ |
| Recorrido Playwright (`frontend/scripts/flujo-fase4.mjs`) | ✅ sin errores de consola ni en el log del servidor |

Recorrido: listas soltadas en la carga masiva del directorio → reconocidas («Encontré ventas, cartera (cuentas por cobrar) y cuentas por pagar de junio de 2026») → cliente creado pidiendo solo el NIT → panel con 2 preguntas → calculado con las sugeridas. Archivo de dos meses → enero cerrado (utilidad 25.000), febrero calculado (15.000). PDF y Word hasta los estados. Panel a 390 px sin desborde.

## Decisiones propias (para revisar)
- **El último periodo del mes a mes no se cierra solo.** El encargo dice «cerrando cada uno»; se cierran todos menos el último, que queda listo para que el contador lo revise y lo cierre con un clic. La API acepta `cerrar_ultimo` para cerrarlo también (lo usan los clientes de demostración).
- **Contrapartida de los saldos de apertura** que salen de las listas (cartera que venía de antes, inventario inicial): 3705 Utilidades acumuladas. Si el cliente ya tiene un cierre anterior, esos saldos no se suman: se usan los del cierre y se avisa.
- Pagos por transferencia, Nequi, Daviplata o tarjeta van a 111005 Bancos; en efectivo, a 110505 Caja.
