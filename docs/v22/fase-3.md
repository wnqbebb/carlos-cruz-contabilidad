# Fase 3 · Una sola puerta (H03, H10)

Capturas: `docs/v22/capturas/fase-3/`. Probado en la copia aislada (puerto 8001, SQLite desechable). La base real no se tocó.

## El defecto que se cierra

Usted subió el Excel de un cliente pequeño en **Clientes › Importar Excel** y la aplicación respondió:

> No se encontraron las columnas obligatorias NIT y RAZÓN SOCIAL

El archivo estaba bien. La pantalla era la otra. Ese mensaje era el final del camino y no decía adónde ir.

Ahora el backend mira **el contenido** del archivo, no la pantalla por la que entró, y decide qué es: una lista de clientes, la contabilidad de uno, o documentos que solo lo identifican.

## Qué se hizo

### 1. El backend clasifica lo que llega
`backend/app/importadores/clasificador.py` abre todos los archivos y clasifica **cada hoja**:

| Respuesta | Cuándo |
|---|---|
| `directorio` | hay columnas NIT y razón social **y** al menos dos NIT distintos con nombre |
| `contabilidad` | alguna hoja cae en un formato contable reconocido |
| `documentos` | solo texto, pero con identidad dentro (estatutos, RUT, cartas) |
| `ambiguo` | las dos primeras a la vez: se pregunta |
| `desconocido` | nada reconocible: se explica qué se vio en cada hoja |

Una sola fila con NIT y nombre **no** es un directorio: eso es la cabecera de una contabilidad. Se exigen dos documentos distintos.

### 2. De quién es, sacado de los propios archivos
`backend/app/importadores/identidad.py`. Busca NIT, DV, cédula y razón social en hojas de cálculo, en párrafos de Word y en páginas de PDF. Cada dato sale con **tres cosas**:

- el **valor**,
- de **dónde** salió (archivo, hoja y celda; o archivo y párrafo),
- y la **confianza**: `seguro` (venía rotulado «NIT: …»), `probable` (la forma lo delata: «… S.A.S.»), `sugerido` (deducido del nombre del archivo).

Reglas que costó afinar, y por qué:

- **NIT y cédula se separan por la etiqueta.** En unos estatutos aparecen las cédulas de los socios; tomar la primera como NIT de la empresa es el error fácil. Una cédula solo se usa como identificación del cliente cuando no hay NIT ni razón social (persona natural).
- **Los títulos de documento no son nombres de empresa.** «ESTATUTOS DE SOCIEDAD POR ACCIONES SIMPLIFICADA S.A.S.» termina en sufijo societario y no es ningún cliente.
- **Una fila ancha es una fila de tabla, no una línea de identidad.** En un libro de movimientos, «05/01 · 110505 · CLIENTE EJEMPLO S.A.S. · 500.000» lleva el nombre de un **tercero**. La identidad de la empresa va sola en su renglón.
- **El nombre del archivo es el último recurso.** Se le quitan las palabras que dicen *qué* es el archivo (contabilidad, balance, enero, copia, final…) pero **no** las que pueden ser parte del negocio: «TIENDA», «DROGUERÍA» y «FERRETERÍA» se conservan. Va siempre rotulado como `sugerido`.

Verificado contra los tres documentos reales de FANANT que ya estaban en el repositorio:

| Documento | Lo que sacó |
|---|---|
| `CORREGIDO_acta_y_estatutos_FANANT.docx` | razón social, *probable* |
| `CARTAS_VARIAS.docx` | razón social, *probable* (con la errata que trae el original) |
| `cuentas_de_cobro_Word.docx` | razón social **y** NIT [NIT]-9, *seguro* |

### 3. Word y PDF entran de verdad (H04 parcial)
`backend/app/importadores/documentos.py` + `lector.leer_archivo`:

- `.docx` → cada tabla es una hoja, más una hoja de texto con los párrafos.
- `.pdf` → las tablas con **pdfplumber**, más el texto con **pypdf**, además del lector que ya existía.
- `.doc` (el viejo) → se dice claro que hay que guardarlo como `.docx`.

Dependencias nuevas declaradas en `backend/requirements.txt` y en `empaquetar/carloscruz.spec` (`docx`, `pdfplumber`, `pypdf`).

### 4. Una sola puerta en la pantalla
`frontend/src/componentes/Subir.tsx` envuelve toda la aplicación:

- **«Subir archivo»** es ahora el botón principal del Tablero, de Clientes y de la ficha del cliente.
- Se puede **soltar un archivo sobre cualquier pantalla**, incluida Parámetros. Aparece «Suelte aquí» a pantalla completa.
- Una **sola tarjeta de confirmación**, ya llena: qué encontré, de quién es, y **de dónde salió cada dato**. Los únicos campos obligatorios son **nombre** y **NIT o cédula**.
- Botón **«Crear cliente y calcular»**. El archivo **nunca** se vuelve a pedir: los bytes quedan en la sesión del servidor hasta que se confirma.
- Si el archivo es ambiguo, dos botones: «Son clientes para el directorio» / «Es la contabilidad de un cliente».
- Si el NIT encontrado ya está en el directorio, se reconoce al cliente y no se pregunta nada. Si solo se parece el nombre, se avisa de que puede ser el mismo.

### 5. La puerta del directorio ya no es un callejón
Clientes › «Importar Excel» pasa a llamarse **«Importar directorio de clientes»**, que es lo que hace. Y cuando ahí cae una contabilidad:

> **Esto no parece una lista de clientes.** No encontré columnas de NIT y razón social… Pero el archivo puede estar perfectamente bien: si es la contabilidad de un cliente, la proceso ahora mismo sin que la vuelva a subir.
> **[ Ver qué trae este archivo ]**

Ese botón pasa el **mismo archivo** a la puerta única. No hay que volver a buscarlo.

### 6. Se dejó de suponer FANANT (H10)
- Calcular sin cliente ya **no** usa el NIT ni la razón social de FANANT: la empresa queda vacía y la identidad sale de los archivos.
- La plantilla en blanco ya no viene con los datos de FANANT dentro; sale vacía y con el mes corriente.
- El formato que se llamaba «Plantilla oficial FANANT» ahora es **«Plantilla oficial de Carlos Cruz»**: el nombre de un cliente no puede rotular algo que usan todos.
- **«Cargar sus archivos de ejemplo»** se fue del paso «Subir» (donde salía para cualquier cliente, con el riesgo de meter la contabilidad de una empresa en el expediente de otra) y ahora **solo aparece en la ficha de FANANT**.

## Verificación

| Comprobación | Resultado |
|---|---|
| Pruebas del backend | ✅ **145** (128 anteriores + 17 nuevas en `test_subir.py`) |
| `tsc --noEmit` | ✅ limpio |
| `npm run lint:diseno` | ✅ 0 infracciones (46 archivos) |
| `npm run build` | ✅ |
| Flujo en el navegador | ✅ `frontend/scripts/flujo-fase3.mjs`, sin errores de consola |

Lo que pidió el encargo, probado:

| Caso | Dónde se prueba | Resultado |
|---|---|---|
| Plantilla con hoja EMPRESA → cero preguntas | `test_la_plantilla_oficial_es_contabilidad_y_no_pregunta_nada` | ✅ `falta: []`, confianza *seguro* |
| Archivo sin identidad → pide solo el NIT y continúa | flujo, paso 3 | ✅ botón bloqueado sin NIT, activo al escribirlo, sigue sin volver a subir |
| Estatutos `.docx` + `CONTABILIDAD.xls` juntos | `test_word_mas_excel_juntos_identidad_del_word_cifras_del_excel` | ✅ nombre del Word, cifras del Excel |
| Contabilidad en la carga masiva → se ofrece procesarla | flujo, paso 1 | ✅ con el mismo archivo |

En el navegador, de punta a punta: la contabilidad soltada en la puerta del directorio llegó hasta **03 Mapeo** con el cliente `COMERCIALIZADORA EJEMPLO COMPLETO S.A.S. · 901.234.567-7` creado solo, sin volver a pedir el archivo.

Capturas a 1440 px (`f3-01` … `f3-08`) y a 390 px (`f3-09`, `f3-10`).

## Lo que falta, y es honesto decirlo

- **Un Excel de listas de ventas y compras todavía no se reconoce como contabilidad.** Es justo lo que construye la **Fase 4** (el importador de registros auxiliares). Hoy ese archivo cae en «No reconocí lo que trae» y se explica qué se vio en cada hoja; la salida desde la carga masiva sí funciona ya, porque es independiente del detector.
- **Un libro diario suelto en CSV** (`Fecha · Cuenta · Débito · Crédito`) tampoco se reconoce. No está en el encargo: queda anotado en `docs/PROPUESTAS.md` (P01).
- Un PDF **escaneado** sigue sin tener nada que leer: es una foto. La aplicación lo dice.

## Archivos tocados

**Nuevos:** `backend/app/importadores/{identidad,documentos,clasificador}.py` · `backend/app/api/subir.py` · `backend/tests/test_subir.py` · `frontend/src/componentes/Subir.tsx` · `frontend/scripts/flujo-fase3.mjs` · `docs/PROPUESTAS.md`

**Modificados:** `importadores/{lector,base}.py` · `api/{__init__,trabajo}.py` · `exportar/plantilla.py` · `requirements.txt` · `empaquetar/carloscruz.spec` · `frontend/src/{api.ts,tipos.ts,App.tsx}` · `frontend/src/paginas/{Inicio,Trabajo,Clientes,Tablero,ClienteFicha}.tsx`
