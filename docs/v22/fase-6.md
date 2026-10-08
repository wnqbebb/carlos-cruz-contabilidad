# Fase 6 · Cliente: crear fácil, editar todo (+ A3 y A6)

Capturas: `privado/capturas/v22/fase-6/`. Probado en la copia aislada (puerto 8001). La base real no se tocó.

## 1. La ficha se llena sola con los documentos — `backend/app/importadores/ficha.py`
| Documento | Qué se extrae |
|---|---|
| Estatutos y actas (`.docx`, `.pdf`) | Razón social, sigla, tipo de sociedad, municipio y departamento, dirección, objeto social, CIIU principal y secundarios, fecha y documento de constitución, capital autorizado, suscrito y pagado, número de acciones y valor nominal, **socios** (nombre, cédula, acciones, %, aporte), representante legal y suplente con cédula, revisor fiscal (solo si se nombra a alguien), responsabilidades tributarias, correo y teléfono |
| RUT (`.pdf`) | NIT y DV, razón social, dirección, municipio, departamento, teléfono, correo, CIIU principal y secundarios, tipo de persona, responsabilidades (48 ⇒ responsable de IVA) |
| Certificado de cámara (`.pdf`) | Matrícula, fecha de renovación, representante, capital |
| Cartas y certificaciones | Contador con cédula y T.P., composición accionaria |
| Excel contable | Periodo e ingresos (ya los muestra la puerta única) |
| Nombre del archivo | Nombre sugerido (último recurso, Fase 3) |

- Cada dato sale con **origen** (archivo y línea, o tabla) y **confianza**: *seguro* si venía rotulado, *por confirmar* si se dedujo de la redacción.
- **Conflictos**: si dos documentos no coinciden, se marcan y el contador elige. Ejemplo real: la carta de FANANT dice «FARMACIA NATURITA» (errata del original) y el estatuto «NATURISTA».
- Lo que no aparece queda vacío. Las tablas de Excel no se toman como socios (una nómina también tiene «NOMBRE | CÉDULA»).
- **Prueba obligatoria con `privado/fuentes/`** (`test_los_estatutos_y_las_cartas_llenan_la_ficha_de_fanant`): estatutos + `CARTAS_VARIAS.docx` llenan **4 socios, capital 30.000.000, 4.000 acciones de 7.500, representante legal y suplente con cédula, contador con T.P. 103028-T, CIIU 2100 y 4645, 4773, 8292**. Se compara contra la ficha de referencia `data/empresa_fanant.json` **en modo lectura**: no se creó ni modificó ningún cliente real.

Para que todo esto tenga dónde guardarse se agregaron 13 columnas opcionales a `clientes` y `nota` a `periodos`. La aplicación las agrega sola al arrancar si faltan (`db.py · _columnas_nuevas`, probado quitando una columna y volviendo a arrancar); el SQL equivalente para Supabase está en `supabase/migraciones/004_ficha_y_notas.sql`. Ningún dato existente cambia.

## 2. Formulario manual mínimo
«Nuevo cliente» muestra solo **NIT o cédula** (el DV se calcula al escribir) y **nombre o razón social**. Todo lo demás va en **«Más datos (opcional)»**, plegado. Arriba, **«Llenar desde documentos»**: se sueltan los papeles y aparece la **ficha extraída** con origen y confianza por campo; se desmarca lo que no sirve y se elige en los conflictos. La puerta única también lleva aquí la ficha completa cuando lo subido son solo documentos (antes el editor la ignoraba: defecto corregido).

Al crear el cliente desde la puerta única con contabilidad y documentos juntos, se guarda **toda** la ficha y los socios, no solo NIT y nombre. Un DV mal escrito en un documento ya no impide crear el cliente: se usa el calculado.

## 3. Edición en la ficha
- **En la cabecera**, en su sitio: razón social (en el titular), sigla, municipio, periodicidad y honorarios. Clic, lápiz o Enter; Enter guarda, Escape cancela; después de guardar queda **«Guardado · Deshacer»**.
- **«Editar ficha»** acepta soltar documentos nuevos y muestra **qué campos cambiarían** (antes → después, con origen), para aplicarlos uno por uno. Nada se guarda sin confirmar.
- **Cambiar el NIT** pide confirmación; si otro cliente ya lo usa, se dice cuál.

## 4. Restaurar archivados (H09)
Desde la ficha (aviso «Este cliente está archivado» con «Restaurar cliente») y desde el filtro «Archivados» de Clientes (botón «Restaurar» en cada carpeta y fila).

## 5. Columnas de comparación en Clientes
La vista Tabla trae, del **último periodo** de cada cliente: periodo, ingresos, utilidad, margen y estado (cerrado / por cerrar / no cuadra). Se ordena con un clic en el encabezado. El orden por cifras se hace en Python con `Decimal` (en SQLite el dinero es texto y ordenarlo en SQL sería alfabético); los clientes sin periodos van al final.

## 6. Adiciones de la revisión externa
- **A3 · Severidad del capital**: capital en libros distinto del libro de aportes pasa de *info* a **advertencia** (E5), y se ve en la ficha como sugerencia «El capital en libros no coincide con los estatutos» (severidad alta).
- **A6 · Nota en FANANT enero 2025**: quedó lista la mecánica (nota de revisión por periodo, editable en Ficha › Periodos y visible en Estados financieros; nota del cliente visible en la cabecera). **El texto se escribe en la base real en la sección 4**, que es la única que la toca; las cifras no cambian (el endpoint rechaza editar cualquier cosa que no sea la nota).

## Verificación
| Comprobación | Resultado |
|---|---|
| Pruebas del backend | ✅ **219** (21 nuevas: `test_ficha.py`, `test_ficha_api.py`) |
| `tsc --noEmit` | ✅ limpio |
| `npm run lint:diseno` | ✅ 0 infracciones (48 archivos) |
| `npm run build` | ✅ |
| Recorrido Playwright (`frontend/scripts/flujo-fase6.mjs`) | ✅ sin errores de consola ni en el log |

Recorrido: formulario con 2 campos visibles y DV 9 calculado → acta en Word → ficha extraída con 21 datos → cliente creado con sigla, capital, representante con cédula y 2 socios → razón social editada en la cabecera y deshecha → periodicidad bimestral → RUT nuevo: 5 datos cambiarían, aplicados (municipio Buga, correo, responsabilidades) → archivado y restaurado desde la ficha y desde «Archivados» → tabla ordenada por ingresos → 390 px sin desborde.
