# v2.3 · Fase 4 — Simplificar: que nadie se pierda

## Qué cambió

1. **Expediente con 4 secciones** (Resumen · Contabilidad · Archivos y actividad · Datos); Renta será la quinta (Fase 5).
2. **Contabilidad: lista lateral agrupada**, exactamente la del spec (en el celular, un desplegable):
   Estados financieros (situación, resultados, patrimonio, flujo) · Balances (prueba, ajustes, hoja, definitivo) ·
   Libros (diario, mayor y balances, cuentas T) · Detalle (inventario, nómina, alertas).
   Las notas quedan plegadas bajo Situación financiera y los indicadores bajo Resultados.
3. **Sin pestañas dentro de pestañas**: la vista de resultados ya no tiene las 12 pestañas + 6 anidadas de Trabajar.
4. **Lo avanzado, plegado** («Ver…»): asiento de cierre, libro mayor por cuenta, balance ajustado, depreciación,
   kardex, auditorías de nómina y de estados anteriores; en *Revisar*, las hojas detectadas con lo que el
   importador interpretó y los datos de la empresa/opciones de cálculo; en el expediente, los cierres guardados,
   la actividad más antigua y los indicadores del último periodo.
5. **Un botón principal por pantalla**: Tablero → «Hacer ahora» solo en la primera tarea (las demás, secundarias;
   de la sexta en adelante, plegadas); Contabilidad → «Cerrar periodo»; Revisar → «Calcular todo».
   Sin cifras repetidas: el resumen del cliente muestra las cuatro cifras en una sola franja (antes, cuatro tarjetas
   que repetían el estado de situación); el Tablero ya no tiene la segunda zona de subida (soltar un archivo funciona
   en cualquier pantalla) ni la tarjeta «Cliente nuevo» (está en Clientes).
   La cabecera del cliente es de solo lectura: todo se edita en «Editar ficha» (Datos).
   La tabla de periodos ya no repite en cada fila «nota / reabrir / eliminar» (están en el menú «···» de Contabilidad).
   La huella SHA-256 de los archivos subidos ya no se muestra.

Ninguna función se perdió: cada acción quitada de una pantalla vive en otra (indicado arriba).

## Inventario antes y después

Medido con `frontend/scripts/inventario-ui.mjs` sobre las **mismas URL** (las viejas redirigen a su sección nueva),
la misma base (copia aislada) y a 1440 px en claro. Cuenta lo visible dentro de `<main>` y la cabecera; lo plegado en
un `<details>` cerrado no cuenta (`checkVisibility`). El «antes» se volvió a medir con el código de la Fase 2
(commit `c548f3b`) en un servidor aparte contra una copia exacta de la base.

| Ruta | Pestañas | Botones | Tarjetas | Textos |
|---|---|---|---|---|
| `/` | 0 → 0 | 22 → 11 | 7 → 7 | 38 → 21 |
| `/clientes` | 0 → 0 | 11 → 11 | 0 → 0 | 15 → 15 |
| `/trabajo` (→ `/clientes`) | 0 → 0 | 14 → 11 | 1 → 0 | 23 → 15 |
| `/trabajo?cliente={id}` | 0 → 4 | 13 → 23 | 6 → 1 | 13 → 15 |
| `/clientes/{id}?vista=resumen` | 9 → 4 | 22 → 4 | 13 → 3 | 22 → 6 |
| `?vista=periodos` | 9 → 4 | 85 → 4 | 2 → 3 | 3 → 21 |
| `?vista=estados` | 18 → 4 | 63 → 23 | 10 → 1 | 18 → 15 |
| `?vista=inventario` | 10 → 4 | 49 → 25 | 3 → 2 | 5 → 7 |
| `?vista=nomina` | 10 → 4 | 51 → 27 | 4 → 3 | 6 → 7 |
| `?vista=socios` | 9 → 4 | 22 → 5 | 1 → 2 | 4 → 3 |
| `?vista=movimientos` | 9 → 4 | 47 → 25 | 0 → 1 | 4 → 6 |
| `?vista=actividad` | 9 → 4 | 22 → 4 | 2 → 3 | 143 → 21 |
| `?vista=ficha` | 9 → 4 | 24 → 5 | 5 → 2 | 5 → 3 |
| **Total** | **92 → 40 (−57 %)** | **445 → 178 (−60 %)** | **54 → 28 (−48 %)** | **299 → 155 (−48 %)** |

**En conjunto: 890 → 401 elementos (−55 %).** Meta ≥ 40 % cumplida en cada categoría.

Notas honestas:
- `/trabajo?cliente=…` antes abría la pantalla de subida; ahora abre la contabilidad ya calculada del cliente
  (más botones porque trae la lista de informes, pero ya no hay que volver a subir nada).
- `periodos` y `actividad` ahora son la misma sección: por eso sus textos suben (21) aunque juntos bajan de 146 a 21.
- La vista de resultados de Trabajar (12 pestañas + 6 anidadas) no se midió en el «antes» porque solo existía tras
  calcular; su reemplazo está incluido en las filas de Contabilidad.

## Control de calidad

| Prueba | Resultado |
|---|---|
| `pytest backend/tests` | 268 pasan |
| `tsc --noEmit` | limpio |
| `npm run lint:diseno` | 0 infracciones |
| `npm run build` | correcto |
| `flujo-v23-expediente.mjs` (claro/oscuro · 1440/390) | 12 meses desde Resultados, Definitivo y Diario sin que cambie la vista ni salte la página; sin errores |
| `flujo-v23-trabajo.mjs` | subir → calcular → cerrar, sin errores |
| `flujo-v23-preguntas.mjs`, `flujo-v23-sistema.mjs` | sin errores |
| `capturas-v23.mjs` (6 rutas × 4 variantes) | sin errores de consola ni desbordes |
