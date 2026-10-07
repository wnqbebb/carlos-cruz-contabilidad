# Manual de usuario — Carlos Cruz

*Contabilidad que cuadra.*

Esta aplicación guarda a todos sus clientes en un solo lugar y le arma la
contabilidad de cada uno a partir de sus Excel: balance, estados financieros,
inventario y nómina, listos para descargar y firmar.

---

## 1. Abrir la aplicación

**En este computador:** doble clic en **`iniciar.bat`**. La primera vez instala
lo necesario (1 a 3 minutos) y después abre el navegador en
**http://localhost:8000**. Para cerrarla, cierre la ventana negra.

**En línea:** si ya está publicada, entre a la dirección que le pasaron y listo;
no hay que instalar nada y puede entrar desde el celular.

Abajo a la izquierda del menú hay un punto de color que le dice dónde se están
guardando los datos:

| Punto | Significa |
|---|---|
| 🟢 verde · *Supabase* | Los datos están en línea. Entra desde donde quiera. |
| 🟡 ámbar · *Base local* | Los datos están solo en este computador. |
| 🔴 rojo · *Sin conexión* | Puede calcular, pero **nada se guardará**. |

---

## 2. Sus clientes

### 2.1 Agregar uno

**Clientes** → **+ Nuevo cliente**. Solo son obligatorios el **NIT** (sin puntos
ni dígito de verificación: la aplicación lo calcula sola) y la **razón social**.

Vale la pena llenar también dirección, municipio, actividad CIIU, representante
legal y correo: esos datos salen impresos en los estados financieros, y mientras
falten la aplicación se lo va a recordar.

Dos campos cambian cómo trabaja el sistema:

- **Periodicidad**: define a partir de cuándo le avisa que el cliente está
  atrasado. Mensual avisa a los 2 meses; anual, a los 14.
- **Capital suscrito**: sin él la aplicación no puede avisarle si el patrimonio
  cayó por debajo de la mitad del capital.

### 2.2 Cargar muchos de una vez

**Clientes** → **Importar Excel**. Acepta `.xlsx`, `.xls` y `.csv`, y sirve para
miles de filas.

Solo necesita dos columnas: **NIT** y **RAZÓN SOCIAL** (o **NOMBRE**). Las demás
las reconoce solas si están, aunque vengan en otro orden o escritas distinto:
teléfono, correo, municipio, honorarios, periodicidad, etiquetas y varias más.
Puede descargar una plantilla de ejemplo desde esa misma ventana.

**Haga siempre «Revisar sin guardar» primero.** Hace la pasada completa sin
tocar la base y le muestra qué iba a pasar:

| Columna | Qué le dice |
|---|---|
| Filas leídas | Cuántas tenía el archivo |
| Nuevos | Cuántos clientes se crearían |
| Actualizados | Cuántos ya existían (se identifican por el NIT) |
| Rechazados | Cuáles no sirven, **con el número de fila del Excel y el motivo** |

Corrija esas filas en el archivo, vuelva a revisar y cuando quede limpio pulse
**Importar de verdad**.

Una fila mala no daña las demás: la aplicación la reporta y sigue.

### 2.3 Buscar

**`Ctrl + K`** desde cualquier pantalla. Busque por nombre, NIT, municipio o
representante legal; no importan las tildes ni las mayúsculas, y el NIT lo
encuentra con o sin puntos. Con las flechas se mueve y con Enter abre.

### 2.4 Archivar o eliminar

- **Archivar** lo saca de las listas pero conserva toda su contabilidad. Es lo
  que se usa cuando un cliente se retira.
- **Eliminar** borra la ficha **y todos sus periodos, resultados y
  movimientos**. No se puede deshacer, y por eso le pide escribir `ELIMINAR`.

---

## 3. Contabilizar un periodo

**Trabajar** → elija el cliente. Todo el trabajo queda guardado contra su ficha,
así que el periodo entra en su historia y los saldos de cierre abren el mes
siguiente automáticamente.

### Paso 1 — Subir archivos
- Arrastre uno o varios Excel: contabilidad, nómina, inventario…
- **Cargar archivos de FANANT**: procesa los tres archivos reales del cliente.
- **Cargar demostración**: enero de 2025 con inventario, activos y nómina
  (datos ficticios, marcados como DEMO).
- **Descargar plantilla**: el formato oficial para el día a día.

### Paso 2 — Revisar y mapear
- **Hojas detectadas**: marque cuáles entran en el cálculo. La aplicación ya propone:
  - excluir la hoja «cuenta T» si repite los movimientos de la hoja de trabajo;
  - excluir hojas que no cuadran (por ejemplo, la de abril-junio con diferencia de $ 598);
  - los estados financieros existentes y las nóminas de ejemplo se **auditan** sin sumarse.
- **Mapeo de cuentas**: cada nombre del Excel se convierte en un código PUC.
  - Verde: exacto. Ámbar: por confirmar. Rojo: sin mapear (escriba el código o elija una sugerencia).
  - Las decisiones se recuerdan para ese cliente: el segundo mes es mucho más rápido que el primero.
- **Empresa y periodo**: revise las fechas (se sugieren a partir de la nómina o de la hoja EMPRESA).
- **Opciones**: exoneración art. 114-1, cuenta de provisiones (25 o 26), método de inventario, provisión de renta.
- Pulse **Calcular todo**.

### Paso 3 — Resultados
| Pestaña | Contenido |
|---|---|
| Resumen y alertas | Cifras clave, validaciones (errores, advertencias), guardar cierre |
| Balance de prueba | Saldos iniciales, movimientos y saldos finales con sumas iguales |
| Ajustes | Ajustes propuestos: costo de ventas (kardex), conteo físico, depreciación, nómina, reclasificaciones. Marque o desmarque y pulse **Recalcular** |
| Hoja de trabajo | 12 columnas: prueba → ajustes → ajustado → resultados → balance general |
| Balance definitivo | Balance ajustado, asiento de cierre y balance después del cierre |
| Estados financieros | Situación financiera, resultados, cambios en el patrimonio, flujo de efectivo, indicadores y notas |
| Inventarios | Saldos por producto, vencidos y por vencer, kardex vs. conteo físico, kardex por producto |
| Nómina | Liquidación correcta y **auditoría** de la nómina del archivo (qué celda está mal y por qué) |
| Auditoría EF | Errores del Excel de estados financieros del contador y cifras corregidas |
| Libro mayor y cuentas T | Vista de cuentas T y libro mayor detallado |

**Descargas**: *Excel completo* (todas las hojas, con fórmulas de totales para
auditar y una hoja con el formato del contador), *PDF para firmar* y *Saldos para
el siguiente periodo*.

**Guardar cierre**: guarda los saldos finales; el siguiente periodo los usa como
saldos iniciales automáticamente. Es el paso que no conviene olvidar.

---

## 4. La ficha del cliente

Al abrir un cliente hay cuatro pestañas:

- **Resumen** — Activo, pasivo, patrimonio y utilidad del último periodo; la
  revisión automática (sección 5) y la evolución en gráficas. Debajo de cada
  gráfica puede abrir *Ver los mismos datos en tabla*.
- **Periodos** — Todos los periodos con sus cifras y su estado. Desde aquí
  reabre un cierre (si hay que corregir algo) o elimina un periodo en borrador.
  Un periodo **cerrado** no se puede eliminar sin reabrirlo primero: así no se
  rompen los saldos iniciales del siguiente.
- **Libro diario** — Todos los movimientos guardados, filtrables por cuenta PUC.
  Arriba se ve la suma de débitos y de créditos, y si cuadran.
- **Datos** — La ficha completa, los socios y las notas.

---

## 5. La revisión automática

En cada ficha, la aplicación revisa lo que hay guardado y le dice qué atender.
**Cada aviso trae el dato que lo sustenta**: si no puede sustentarlo, no lo dice.

| Aviso | Cuándo aparece |
|---|---|
| **Balance descuadrado** | El activo no es igual al pasivo más el patrimonio. Es lo más grave: no firme así. |
| **Patrimonio bajo el 50 % del capital** | Deterioro patrimonial. Hay que revelarlo y avisar a los socios. |
| **Periodos sin cerrar** | Están calculados pero no cerrados, así que el siguiente arranca sin saldos iniciales. |
| **Saltos en la secuencia** | Faltan meses entre dos periodos; el error se arrastra hacia adelante. |
| **Atrasado** | Pasaron más meses sin contabilizar de los que permite la periodicidad pactada. |
| **Variación fuerte** | Ingresos, gastos o activo saltaron más del 40 % contra el periodo anterior. Suele ser un archivo cargado dos veces o una cuenta mal mapeada. |
| **Pérdidas seguidas** | Tres periodos o más con pérdida, con el acumulado. |
| **Endeudamiento alto** | El pasivo pasó del 70 % del activo. |
| **Capital por pagar** | Socios con aportes comprometidos y no pagados. |
| **Ficha incompleta** | Faltan datos que van impresos en los estados financieros. |
| **Turno tributario** | Su turno de 1 a 10 según el último dígito del NIT. Las fechas exactas las fija un decreto cada año, así que la aplicación **no las inventa**: cárguelas en Parámetros. |

El **Tablero** reúne lo urgente de toda la cartera: entra, mira qué está en rojo
y sabe por dónde empezar el día.

---

## 6. Plantilla oficial (uso diario)

| Hoja | Qué va |
|---|---|
| EMPRESA | Datos de la empresa y periodo desde/hasta |
| SALDOS_INICIALES | Saldos al inicio del periodo (o déjela vacía si guardó el cierre anterior) |
| MOVIMIENTOS | Libro diario: fecha, comprobante, código PUC, tercero, débito, crédito |
| AJUSTES | Ajustes manuales (opcional) |
| INVENTARIO_MOVS | Inventario inicial, compras, ventas, devoluciones, ajustes, con lote y vencimiento |
| INVENTARIO_FISICO | Conteo al cierre (opcional) |
| ACTIVOS_FIJOS | Costo, fecha y vida útil (depreciación automática) |
| NOMINA | Un renglón por empleado y mes |

Los encabezados pueden ir en cualquier orden. Los números se aceptan como
`1423500` o `1.423.500,00`.

---

## 7. Parámetros legales

Menú **Parámetros**. Solo viene precargado 2025 (SMMLV $ 1.423.500, auxilio
$ 200.000). Para 2026 u otro año, ingrese el SMMLV, el auxilio y la jornada
oficiales: **la aplicación no inventa estos valores**. Al crear un año nuevo, las
tasas de aportes y prestaciones se copian del año anterior más cercano.

Estos parámetros valen para la nómina de todos sus clientes.

---

## 8. Qué hacer ante una alerta del cálculo

| Código | Significado | Acción |
|---|---|---|
| E1 | Capital calculado como cuadre / estado que no cuadra | El capital sale de la cuenta 31; revise aportes y activos |
| E2 | Totales que omiten cuentas | Use los estados que genera la aplicación |
| E3 | Ingreso igual a un aporte de socio | Revise si es capital; hay una reclasificación sugerida |
| E5 / E18 | Capital en libros ≠ estatutos / libro de aportes sin pagos | Concilie el capital con los soportes de consignación |
| E6 | Saldo contrario a la naturaleza (IVA) | Acepte la reclasificación a 240810 si es IVA descontable |
| E8 | Hoja de trabajo que no cuadra | No la use como fuente |
| E9–E16 | Errores de la nómina del archivo | Use la liquidación de la aplicación |
| E17 | Representante legal en nómina | Conserve el acta de asamblea que aprueba su sueldo |
| E19 | Título con otro año | Confirme el periodo real |
| DISOLUCION | Patrimonio < 50 % del capital | Informe a la asamblea (art. 38-6 y 39 de los estatutos) |

---

## 9. Sobre las cifras

Todas las operaciones se hacen con decimales exactos, de punta a punta: el
motor, la base de datos, el envío al navegador y lo que se muestra en pantalla.
No hay redondeos escondidos ni centavos que aparecen de la nada. En las tarjetas
grandes el número va abreviado ($ 2,2 M) para que se lea de un golpe, y justo
debajo siempre está el importe exacto al peso, que es el que se firma.
