# PROMPT — Correcciones v2.2: «Subir y listo» con Excel, PDF y Word; registros auxiliares; Tablero del contador; diseño con más definición; modo claro/oscuro; 5 clientes históricos

## 0. CONTEXTO Y REGLAS

Documentos vigentes: `PROMPT.md`, `PROMPT_DISENO.md`, `docs/INFORME_ESTADO_ACTUAL.md` (los IDs H01…H23 vienen de ahí).

La frase que manda:

> «Subo un Excel (o un PDF o un Word) y la aplicación calcula automáticamente el balance de prueba, el balance definitivo, los estados financieros, los saldos de inventario, **el libro diario y el libro mayor**, sin que yo tenga que pasar nada a mano. Y los datos del cliente los saca de los mismos archivos.»

### Qué pasó en la última prueba del usuario
Subió el Excel de un cliente pequeño en **Clientes › Importar Excel**. Ese archivo no era un libro en partida doble: eran listas de ventas, compras, cartera y cuentas por pagar. Esa pantalla es la carga masiva del directorio, así que respondió «No se encontraron las columnas obligatorias NIT y RAZÓN SOCIAL».

El usuario no tiene por qué saber que existen dos puertas distintas, ni qué formato espera la app. **Ese es el problema central de esta versión.**

### Prueba ciega
- **No se recibe ese archivo.** Al terminar, el usuario subirá archivos reales nunca vistos.
- No buscarlo, no pedirlo, no preparar la app para un archivo en particular.
- Construir importadores **generales**, que razonen sobre estructura y coherencia, y probarlos con archivos variados generados por mí (4.5).
- Éxito = un archivo desconocido produce resultados correctos o explica con claridad qué le falta.

### Autorizaciones
- Autorizados: H01, H02, H03, H04, H05, H06, H07, H08, H09, H10, H19, importador nuevo (Fase 4), extracción de ficha desde documentos (Fase 6). Librerías nuevas permitidas (`python-docx`, `pdfplumber`) → `requirements.txt` + empaquetado.
- Aditivos cuando se pueda, con migración si cambian tablas y con pruebas nuevas.
- Lo que no esté aquí no se implementa: anotarlo en `docs/PROPUESTAS.md`.

### Reglas de cada fase
1. Pruebas existentes verdes. Única excepción: `test_recalcular_reemplaza_y_no_duplica`, que se adapta a H01. Una prueba nueva por comportamiento nuevo.
2. Al cerrar cada fase: `tsc` limpio, `lint:diseno` 0, `npm run build`, capturas 1440 y 390 px **en claro y oscuro** desde la Fase 8.
3. Datos reales de FANANT solo en la Fase 2. Todo lo demás en copia aislada (SQLite temporal, puerto 8001).
4. Informe corto por fase en `docs/v22/fase-N.md`.

---

## FASE 1 — Que no se vuelvan a perder datos (H01, H08, H19)

1. `guardar_resultado` **rechaza** guardar sobre un periodo cerrado → HTTP 409: «El periodo está cerrado. Reábralo para recalcular». La interfaz ofrece **«Reabrir y recalcular»** (un clic, con confirmación que explica que el cierre se moverá al historial).
2. Rechaza resultado con **0 cuentas o 0 movimientos**: «El archivo no aportó ninguna cuenta; no se guardó nada».
3. **Historial**: antes de reemplazar resultado, movimientos o cierre, copiar todo a tablas de historial (migración `003_historial.sql`). En Ficha › Periodos, versiones anteriores con «Ver» y «Restaurar esta versión».
4. **Bitácora e importaciones** (H08): cada subida en `importaciones` (archivo, sha256, hojas, formato, cliente, fecha); cada acción en `bitacora` (calcular, cerrar, reabrir, restaurar, eliminar, crear/editar cliente). Ficha muestra sección **Actividad**.
5. Pruebas: recalcular cerrado → 409 y datos intactos; cálculo vacío → rechazado; reemplazo → versión anterior en historial y restaurable; cada acción deja línea en bitácora.

## FASE 2 — Recuperar FANANT enero 2025 (H02)

Según §4.10 del informe: 1) respaldo del cierre; 2) reabrir; 3) subir `CONTABILIDAD.xls` y `NOMINA__enero__2025.xlsx` con hojas por defecto; 4) **aceptar la causación de nómina**; 5) calcular y cerrar.

**Criterio:** el nuevo cierre coincide **centavo a centavo** con los 13 saldos de §4.10 (caja 37.144.505; capital 37.800.000; pérdida 2.857.975,72…). Si no coincide, **no cerrar**: restaurar del historial y reportar la diferencia.

## FASE 3 — Una sola puerta: «Subir» inteligente (H03, H10)

1. **Cualquier** zona de subida acepta cualquier archivo; el backend decide qué es (Tablero, Clientes › Importar, Trabajar › 02, ficha, arrastrar en cualquier pantalla).
   - Formatos: `.xlsx`, `.xlsm`, `.xls`, `.csv`, `.txt`, `.pdf`, `.docx`. Para `.doc` antiguo: convertir si hay LibreOffice; si no, mensaje claro pidiendo `.docx`.
   - **Varios archivos a la vez** del mismo cliente (estatutos Word + RUT PDF + contabilidad Excel): identidad de los documentos, cifras de las hojas contables.
   - Directorio de clientes (columnas NIT/RAZÓN SOCIAL) → carga masiva. Contabilidad → flujo de cálculo. Ambiguo → una pregunta con dos botones.
   - Contabilidad subida en carga masiva → «Este archivo parece la contabilidad de un cliente (ventas, compras, cartera). ¿Lo proceso?».
2. **Identificar al cliente sin trabajo manual**, en orden: 1) hoja EMPRESA; 2) documentos Word/PDF; 3) celdas con NIT o razón social (`NIT`, `N.I.T.`, `C.C.`, `S.A.S.`, `LTDA`, `E.U.`); 4) **nombre del archivo** (quitar CONTABILIDAD, PYME, EXCEL, años, guiones; tolerar errores); 5) coincidencia con clientes existentes por NIT o nombre ≥ 90 % → «¿Es este cliente?».
3. **Tarjeta de confirmación**, una sola, ya llena: «Encontré: JUAN PEREZ · NIT — · Enero a septiembre 2026 · Ventas, compras, cartera y cuentas por pagar». Cada dato muestra **de dónde salió**. Obligatorios: **nombre y NIT/cédula**; si falta el NIT se pide solo eso. Botón «Crear cliente y calcular». El archivo **nunca** se vuelve a pedir.
4. Quitar la **empresa por defecto FANANT** (`modelos.empresa_por_defecto`, `data/empresa_fanant.json`). Sin cliente, empresa vacía y se pide.
5. H10: «Cargar archivos de FANANT» solo en la ficha de FANANT.
6. Clientes › «Importar Excel» → **«Importar directorio de clientes»**. Botón principal de la app → **«Subir archivo»**.
7. Pruebas: Excel de ventas/compras en carga masiva → se ofrece procesarlo; plantilla con hoja EMPRESA → cero preguntas; archivo sin identidad → pide solo NIT; estatutos `.docx` + `CONTABILIDAD.xls` juntos → cliente por el Word y cifras por el Excel.

## FASE 4 — Importador nuevo: «Registros auxiliares» y contabilidad dentro de PDF y Word

### 4.1 Detección general (por contenido, no por nombre)
- **Ventas:** fecha + cliente/comprador + producto/concepto + valor.
- **Compras y gastos:** fecha + proveedor + producto/concepto + cantidad y/o valor.
- **Cartera:** tercero + valor + abono y/o saldo. **Cuentas por pagar:** igual con proveedores.
- **Gastos operativos:** arriendo, servicios, nómina, transporte…
- **Inventario o conteo:** producto + cantidad + costo.

Tolerancias: encabezados fuera de la fila 1, títulos encima, celdas combinadas; **varios bloques por hoja** (uno por mes, con su título y encabezado); encabezados con otros nombres, mal escritos o en cualquier orden; filas de totales, vacías y fórmulas en 0; hojas vacías (ignorar con aviso); números como texto, con `$`, puntos de miles o comas decimales.

### 4.2 Problemas de calidad que debe detectar y explicar (nunca corregir en silencio)
1. **Columnas mal rotuladas:** identificar por comportamiento (si `total = col × valor unitario`, esa col es la cantidad). Avisar qué se interpretó y por qué.
2. **Fechas incoherentes:** que no coinciden con el mes del título del bloque, fuera del periodo o **en meses futuros**. Preguntar, con valor por defecto razonable.
3. **Errores de escritura en títulos y años:** interpretar lo evidente y avisar.
4. **Datos incompletos repetidos hacia abajo** (método de pago solo en la primera fila): preguntar si aplica a las demás.
5. **Inventario insuficiente:** si se vende más de lo comprado, kardex negativo. No inventar costo: avisar mes y producto, proponer cargar compras o conteo físico.
6. **Márgenes anómalos:** precio muy distinto del costo sugiere unidades distintas (kilo vs caja). Avisar y pedir confirmar unidad.
7. **Terceros de cartera o CxP que no aparecen en ventas ni compras.** Preguntar una vez por hoja: (a) saldos anteriores → saldo inicial; (b) ventas/compras a crédito adicionales → se registran; (c) ya incluidas → reclasificar de caja a cartera/proveedores.
8. **Sin identidad o sin saldos iniciales:** caja y capital en 0, con aviso y opción de cargar balance de apertura.
9. **Hojas que prometen algo que no traen:** aviso informativo.

Todas las preguntas **juntas en un panel «Preguntas sobre este archivo»**, con respuesta por defecto marcada y botón «Usar las respuestas sugeridas y calcular». Nada de diálogos encadenados.

### 4.3 Reglas contables de la conversión
| Registro | Asiento |
|---|---|
| Venta de contado | D 110505 Caja · C ingreso operacional (4135 por defecto; el usuario puede elegir otra del grupo 41) |
| Venta a crédito | D 130505 Clientes (con tercero) · C ingreso |
| Compra de mercancía | D 1435 Inventario (kardex por producto) · C 110505, o 220505 Proveedores |
| Gasto operativo | D 51/52 según concepto (mapeo PUC con alias) · C 110505 o 2335 |
| Salida por venta | D 6135 Costo de ventas · C 1435, al costo promedio, **solo hasta el saldo disponible** |
| Abono de cartera | D 110505 · C 130505 |
| Abono a proveedor | D 220505 · C 110505 |
| IVA | Según «Responsable de IVA» de la ficha. Si no es responsable o el producto es excluido, no se discrimina |

- Cada asiento con comprobante automático (`VTA-0001`, `CMP-0001`, `GTO-0001`, `REC-0001`, `PAG-0001`), fecha, tercero, descripción y **origen** (archivo, hoja, fila). En el libro diario, clic en el origen muestra la fila original.
- Periodización: si cubre varios meses, ofrecer «Procesar mes a mes, cerrando cada uno» (por defecto, según periodicidad) o «Un solo periodo».

### 4.4 Contabilidad dentro de PDF y Word (H04 ampliado)
- **PDF con texto:** completar H04; tablas de balances, EF, listados y auxiliares entran al mismo detector.
- **Word `.docx`:** leer las **tablas** (python-docx) y pasarlas al mismo detector; párrafos para la identidad (Fase 6).
- **PDF escaneado:** no inventar. «Este documento es una imagen; no tiene texto que leer. Pida el archivo original o en Excel».
- Todo pasa por la misma vista previa y el mismo panel de preguntas.

### 4.5 Cómo probarlo sin archivo de referencia
Banco de **al menos 12 archivos** en `backend/tests/archivos_variados/`: listas mensuales en bloques; columnas mal rotuladas; fechas copiadas y meses futuros; totales mezclados; hojas vacías; cartera con terceros desconocidos; archivos sin NIT; balance de prueba en PDF con texto; tabla de ventas en Word; PDF escaneado. Cifras esperadas **calculadas a mano en la prueba**. Pruebas: cifras, partida doble por comprobante, detección de cada problema de 4.2, respuestas por defecto y recorrido en la interfaz con Playwright.

## FASE 5 — Libro diario, libro mayor y todos los entregables desde cualquier archivo (H05, H06, H07)

El resultado siempre incluye **todos** los entregables: libro diario; libro mayor y balances; balance de prueba; balance definitivo; situación financiera, **estado de resultados**, cambios en el patrimonio, flujo de efectivo; notas e indicadores; saldos de inventario. Si falta algo, aparece igual con la explicación, nunca con ceros inventados.

- **Libro diario:** selector de periodo; orden cronológico; fecha, número y tipo de comprobante, cuenta, tercero, descripción, débito y crédito; totales por comprobante y del periodo; insignia de partida doble; enlace al origen.
- **Libro mayor y balances:** por cuenta, subtotales por grupo y clase; saldo anterior, movimientos y saldo final (D/C).
- **H07:** saldos iniciales de la hoja de trabajo + movimientos detallados de la cuenta T cuando ambas coinciden en sumas.

En pantalla, Excel y PDF, en formato oficial.

## FASE 6 — Cliente: crear fácil, editar todo

1. **La ficha se llena sola con los documentos** (camino normal = subir archivos):

| Documento | Qué se extrae |
|---|---|
| Estatutos, actas (`.docx`, `.pdf`) | Razón social, sigla, tipo de sociedad, domicilio, objeto y CIIU, fecha y documento de constitución, capital autorizado/suscrito/pagado, número y valor nominal de acciones, **socios** (nombre, cédula, acciones, %, aporte), representante legal y suplente con cédulas, revisor fiscal |
| RUT (`.pdf`) | NIT y DV, razón social, dirección, municipio, departamento, teléfono, correo, CIIU principal y secundarios, tipo de persona, responsabilidades tributarias |
| Certificado de cámara (`.pdf`) | Matrícula, representantes, capital, fecha de renovación |
| Certificaciones y cartas (`.docx`, `.pdf`) | Contador y T.P., composición accionaria |
| Excel contable | Periodo, ingresos, actividad deducida |
| Nombre del archivo | Nombre sugerido (último recurso) |

   - **Ficha extraída** completa antes de guardar, con origen por campo y señal de confianza (seguro / por confirmar).
   - Conflictos entre documentos → marcados, se deja elegir.
   - «Guardar ficha» confirma. Lo que no aparezca queda vacío.
   - Prueba obligatoria con `docs/fuentes/`: los estatutos y `CARTAS_VARIAS.docx` deben llenar la ficha de FANANT (4 socios, capital, representante legal y suplente, contador con T.P., CIIU). Comparar contra la ficha real **en modo lectura, sin sobrescribir**.
2. **Formulario manual** (respaldo): visibles solo **NIT o cédula** (calcula DV) y **nombre o razón social**; plegable «Más datos (opcional)»; botón «Crear cliente»; opción «Llenar desde documentos».
3. **Edición en la ficha:** razón social editable **en el titular** (clic, lápiz o Enter, con guardado y deshacer); igual sigla, municipio, periodicidad y honorarios desde la cabecera; el resto en «Editar ficha», que acepta soltar documentos nuevos (mostrando qué campos cambiarían); el NIT con confirmación y aviso si ya existe otro.
4. **Restaurar** cliente archivado (H09) desde la ficha y desde el filtro «Archivados».
5. En la vista Tabla de Clientes, columnas del **último periodo**: ingresos, utilidad, margen y estado, ordenables.

## FASE 7 — Tablero del contador: básico y útil

**Quitar:** resultado del mes de la cartera, ecuación contable, tarjeta de nómina (SMMLV, auxilio, jornada → Parámetros) y cualquier cifra financiera de un cliente individual.

**Queda, en orden:**
1. Saludo, fecha y botón principal **«Subir archivo»**, con zona de arrastre amplia.
2. Cuatro indicadores: **clientes activos**, **honorarios mensuales**, **al día**, **atrasados**.
3. **Tareas sugeridas** (bloque principal), desde `inteligencia/sugerencias.py`, con prioridad, cliente, qué hacer, por qué y acción directa: contabilizar meses atrasados; cerrar periodos calculados; revisar descuadres; responder preguntas pendientes de una importación; periodos en cero; alertas críticas; completar datos de la ficha **solo** si hacen falta para firmar. Acciones: «Hacer ahora» y «Posponer hasta mañana» (en bitácora).
4. **Clientes** en carpetas (recientes) con «Ver todos».
5. **Actividad reciente** (últimas 8 líneas de la bitácora).

## FASE 8 — Diseño: más definición, cada página distinta, color por cliente, modo claro y oscuro

### 8.1 Tres planos claramente distintos
```css
--lienzo:  #E8E4DC;  --barra:   #F3F0EA;  --hoja:    #FFFDF9;  --hoja-2:  #F5F2EC;
--campo:   #FFFFFF;
--linea: rgba(20,20,20,.10);  --linea-fuerte: rgba(20,20,20,.18);  --borde-campo: rgba(20,20,20,.24);
```
- **Campos:** fondo `--campo`, borde 1 px `--borde-campo`, etiquetas en `--grafito`. Se abandona el «hundido» gris sobre gris en formularios.
- **Tarjetas:** borde 1 px `--linea` + sombra Hoja; distinguibles del lienzo sin depender de la sombra.
- **Rejilla:** solo en la franja de cabecera (hasta debajo del título) y en el preloader. Opacidad 5 %.
- **Pestañas:** activa texto `--tinta` 600, subrayado 2 px en el color de sección/cliente, contador relleno; inactivas `--grafito` 500; hover subrayado 1 px.
- **Barra lateral:** activo = píldora en el color de la sección; inactivos `--grafito`.
- **Medición obligatoria** en `CONTRASTES.md`: lienzo↔hoja, barra↔lienzo, campo↔hoja (≥ 1,10:1 + borde) y todos los pares de texto en AA, **en ambos modos**.

### 8.2 Cada página se reconoce al instante
| Sección | Tono de cabecera | Motivo | Píldora activa |
|---|---|---|---|
| Tablero⁰¹ | Papel neutro | Fecha grande y saludo; zona de arrastre | Tinta |
| Clientes⁰² | Velo azul tinta 6 % | Pila de carpetas | Azul tinta |
| Trabajar⁰³ | **Banda de taller oscura** (`#24221F`, texto claro) con el paso a paso | Regla graduada 01–07 | Grafito |
| Parámetros⁰⁴ | Gris frío `#E6E7E9` | Renglones de libro contable | Gris frío oscuro |
| Ficha de cliente | **Color del cliente** | Su esfera | Color del cliente |

- Cabecera con **número de índice gigante y delineado** («01», «02»…) a la derecha, `display-xl` solo contorno.
- La transición entre páginas cambia el tono de cabecera de forma visible (0,4 s).

### 8.3 Personalización por cliente desde su esfera
1. De los 3 colores de la esfera (hash del NIT), en **OKLCH**: `--cliente-tono` (L 0,55); `--cliente-profundo` (L 0,28); `--cliente-velo` (10–14 %); `--cliente-texto` (ajustada hasta 4,5:1 sobre `--hoja`).
2. **Restricción:** excluir tonos a menos de 20° del rojo semántico.
3. Se aplican en: velo de cabecera (desde la posición de la esfera); subrayado de pestaña activa; carpeta héroe de la ficha (`--cliente-profundo`); pestaña de su carpeta en Clientes; anillo de foco dentro de su ficha; series de sus gráficas.
4. Los colores semánticos **nunca** se reemplazan.
5. Mostrarlo en `/diseno` con 8 NIT distintos, en claro y oscuro.

### 8.4 Modo claro y modo oscuro
- **Selector** en la barra superior con `Interruptor`: `Claro⁰¹ | Oscuro⁰² | Sistema⁰³`. Se guarda en el navegador; por defecto «Sistema».
- **Tokens oscuros** (todos los tokens deben tener valor oscuro; `lint:diseno` falla si falta alguno):
```css
[data-tema="oscuro"] {
  --lienzo: #0E0E0D;  --barra: #151514;  --hoja: #1B1B19;  --hoja-2: #23231F;
  --campo: #121211;   --borde-campo: rgba(255,255,255,.18);
  --tinta: #EDEAE4;   --grafito: #BDB9B0;  --gris: #94908A;
  --linea: rgba(255,255,255,.10);  --linea-fuerte: rgba(255,255,255,.18);
  --azul: #8FA6FF;    --rojo: #FF7B70;     --ambar: #F2A65A;
}
```
- **Carpeta héroe:** en oscuro se invierte a papel `#F2EFE9` con texto `#141414`; en la ficha usa `--cliente-profundo` con borde 1 px más claro.
- **Superficies:** sombras casi nulas (profundidad por bordes y leve brillo); grano 5 % en `screen`; esferas un poco más brillantes.
- **Excepciones:** la banda de taller se mantiene oscura pero se diferencia con `#2A2824`; impresión y PDF **siempre** en claro; el preloader respeta el modo.
- **Verificación:** capturas de todas las pantallas en los dos modos, contrastes medidos en los dos, Lighthouse accesibilidad ≥ 95 en los dos.

## FASE 9 — Cinco clientes históricos de demostración

1. Script reproducible `backend/demo/generar_historicos.py` (semilla fija). Genera los archivos en `docs/demo/` y **los carga por el mismo flujo de la app** (subir → identificar → calcular → cerrar mes a mes, por la API). **Nunca** inserciones directas.
2. NIT ficticio con DV válido, etiqueta **«Demostración»**, periodos **enero 2025 a septiembre 2026**. En Parámetros › Sistema, botón «Eliminar clientes de demostración» con confirmación.
3. Cada uno con **formato de entrada distinto**:

| # | Cliente | Ciudad | Formato | Rasgos | Situación |
|---|---|---|---|---|---|
| 1 | PANADERÍA LA ESPIGA DORADA S.A.S. | Tuluá | Plantilla oficial | Producción y venta, kardex de insumos, nómina de 4, responsable de IVA, pico en diciembre | Al día y cerrado |
| 2 | FERRETERÍA EL TORNILLO S.A.S. | Buga | Plantilla oficial | Ventas a crédito, cartera creciente, proveedores, depreciación | Agosto calculado sin cerrar, septiembre sin subir |
| 3 | CLÍNICA DENTAL SONRISA DEL VALLE S.A.S. | Cali | Cuenta T y hoja de trabajo | Servicios de salud, sin inventario, honorarios con retención, arriendo | Un mes con descuadre intencional de $ 50.000 |
| 4 | TRANSPORTES RÍO CAUCA S.A.S. | Palmira | CSV del libro diario | Vehículos, préstamo con intereses, depreciación, meses con pérdida | Patrimonio cerca del 50 % del capital (alerta) |
| 5 | MARÍA ELENA ROJAS (persona natural) | Guacarí | Registros auxiliares con desorden realista | Productos agrícolas, bimestral | Atrasada 3 meses |

4. Cifras verosímiles; **cada periodo cuadra** (salvo el descuadre del #3); saldo final de cada mes = saldo inicial del siguiente.
5. Con estos 5 más FANANT, el Tablero muestra tareas variadas y la Tabla de Clientes permite comparar.
6. Al menos **dos** se crean subiendo documentos de identidad generados por el script (estatutos `.docx` y RUT `.pdf` ficticios).

## FASE 10 — Verificación final y entrega

1. Recorrido con Playwright, claro y oscuro, 1440 y 390 px: registros auxiliares subidos **en la carga masiva** → reconocido → cliente creado pidiendo solo el NIT → panel de preguntas → cálculo mes a mes → libro diario con enlaces al origen → estados → inventario con avisos; estatutos `.docx` + contabilidad de FANANT juntos (copia aislada); PDF con texto y Word con tablas; los 5 de demostración y FANANT.
2. Pruebas, `tsc`, `lint:diseno`, build y sello **v2.2.0** en el pie.
3. `docs/v22/ENTREGA.md`: qué cambió por fase; capturas antes/después de Tablero, Clientes, Ficha, Trabajar y Parámetros en claro y oscuro; cifras de control del banco de archivos y de FANANT; pendientes.
4. Mensaje final: ¿«subo un archivo y calcula todo» funciona ya con Excel, PDF y Word? (por formato); estado de FANANT; instrucciones para la **prueba ciega**; limitaciones conocidas.
