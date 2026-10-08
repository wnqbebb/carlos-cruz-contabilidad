# Fase 5 · Libro diario, libro mayor y balances, y todos los entregables desde cualquier archivo

Capturas: `privado/capturas/v22/fase-5/`. Probado en la copia aislada (puerto 8001). La base real no se tocó.

## Qué se hizo

### 1. Libros oficiales (H05, H06) — `backend/app/contabilidad/libros.py`
| Libro | Contenido |
|---|---|
| **Libro diario** | Comprobantes en orden cronológico; por línea: fecha, número y tipo de comprobante, cuenta (código y nombre), tercero, descripción, débito, crédito y **origen**. Total por comprobante (marcado «NO CUADRA» si no cumple partida doble), total del periodo y verificación. Incluye los ajustes aceptados, que es lo que queda registrado |
| **Libro mayor y balances** | Por cuenta: saldo anterior, movimientos y nuevo saldo, débito y crédito; subtotales por **grupo** y por **clase**; sumas iguales |

Salen igual en **pantalla, Excel y PDF** porque los tres consumen la misma estructura de informe.

- **Pantalla**: en Trabajar, pestañas «Libro diario» y «Mayor y balances». En la ficha, la pestaña «Libro diario» ahora tiene **selector de periodo**, filtro por cuenta y cuatro descargas (diario y mayor y balances, en Excel y PDF). Clic en el origen de una línea → se ve **la fila original** del archivo del cliente.
- **Excel**: hojas «Libro diario» y «Mayor y balances» en el libro completo, y descarga suelta de cada libro (`/api/periodos/{id}/libro-diario/excel`, `/mayor-balances/excel`).
- **PDF**: los dos libros van en el PDF completo y como descarga suelta (`…/pdf`). En el PDF se omiten tipo, comprobante y origen (ya van en la cabecera de cada asiento y no caben en carta).
- **Periodos guardados antes de la v2.2** (FANANT enero 2025): los libros se arman al vuelo con lo guardado: el diario con los movimientos de la base y el mayor y balances con el balance de prueba ajustado. No se modifica nada guardado.

### 2. Todos los entregables, siempre
El resultado de cualquier archivo trae libro diario, mayor y balances, balance de prueba, balance definitivo, los cuatro estados, indicadores, notas y saldos de inventario. Si no hay kardex, el informe de inventario aparece igual con la explicación («El archivo no trae movimientos de inventario…»), **sin ceros inventados**. Probado con seis formatos: Excel de listas, CSV en partida doble, PDF con texto, tabla en PDF, Word y balance en Excel.

### 3. H07
Hecho en la Fase 4 (saldos de la hoja de trabajo + detalle de la cuenta T). FANANT: 29 líneas en el diario en vez de 6, mismo resultado.

### 4. H14 · Colores del Excel y del PDF con los tokens
Fuera el índigo (`4338CA`) y el verde (`059669`): encabezados en `--hoja-2`, totales en `--azul-suave` con texto en tinta, «cuadra» en `--azul`, pérdidas en `--rojo`. Una prueba revisa el XML del Excel y falla si reaparecen.

### 5. H16 · Un solo azul sólido por vista
En la ficha › Estados, «Excel completo» pasa a tinta y «PDF para firmar» a contorno: el único azul sólido es «Nuevo periodo».

### Defectos encontrados al revisar el PDF y corregidos
- Los importes de un periodo **guardado** (texto) salían sin separador de miles: `70000`. Ahora `70.000`.
- Si el primer informe era horizontal, el PDF empezaba con **una página en blanco**.
- El NIT salía sin dígito de verificación; ahora `900.500.777-4`.
- `/api/clientes/{id}/movimientos` sumaba los importes con `SUM()` de SQL: en SQLite el dinero es texto y eso pasa por `float`. Ahora suma en Python con `Decimal`, y acepta `periodo_id`.

## Cifras de control de FANANT
Prueba nueva `test_cifras_de_control_fanant_enero_2025`: recalcula en memoria con `CONTABILIDAD.xls` y la nómina, con la causación aceptada, y compara los **13 saldos** del cierre y los totales (activo 37.144.505 · pasivo 2.202.480,72 · patrimonio 34.942.024,28 · pérdida 2.857.975,72). **Idénticos.** La base real no se tocó.

## Verificación
| Comprobación | Resultado |
|---|---|
| Pruebas del backend | ✅ **198** (16 nuevas: `test_libros.py` y la de FANANT) |
| `tsc --noEmit` | ✅ limpio |
| `npm run lint:diseno` | ✅ 0 infracciones (47 archivos) |
| `npm run build` | ✅ |
| Recorrido Playwright (`frontend/scripts/flujo-fase5.mjs`) | ✅ sin errores de consola ni en el log; cuatro descargas con 200 y archivo; 390 px sin desborde |
