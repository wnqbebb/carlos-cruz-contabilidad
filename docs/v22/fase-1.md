# Fase 1 · Que no se vuelvan a perder datos (H01, H08, H19)

Capturas: `privado/capturas/v22/fase-1/`. Probado en la copia aislada (puerto 8001, SQLite desechable). La base real no se tocó.

## Qué se hizo

### 1. Un periodo cerrado ya no se puede pisar (H01)
- `repositorio/periodos.py · guardar_resultado` lanza `PeriodoCerrado`; la API responde **409** con `{"codigo": "periodo_cerrado", "mensaje", "periodo_id", "desde", "hasta"}`.
- La pantalla Trabajar ya no muestra un error muerto: muestra **«Ese periodo ya está cerrado»** con el botón **«Reabrir y recalcular»** (un clic: reabre, vuelve a enviar el mismo cálculo) y «Dejarlo como está». El aviso explica que el cierre pasa al historial.
- Verificado en la interfaz: con el periodo cerrado, los datos quedan intactos (activo 38.409.022,21, 38 cuentas) mientras no se decida nada.

### 2. Un cálculo vacío no reemplaza nada (H19)
- Se rechaza con `ResultadoVacio` → **422** `{"codigo": "resultado_vacio"}` cuando el resultado trae 0 cuentas **o** 0 movimientos.
- Se comprueba **antes** de tocar la base, así que tampoco deja periodos en blanco. Es exactamente lo que pasó el 6 de octubre.

### 3. Historial de versiones
- Tabla nueva `historial_periodos` + migración `supabase/migraciones/003_historial.sql` (idempotente, con RLS como el resto).
- Se guarda una copia completa —indicadores, resultado del motor, libro diario y cierre— antes de: **recalcular**, **reabrir** y **cerrar de nuevo**. Restaurar también guarda primero el estado actual, así que nunca se pierde nada.
- En Ficha › Periodos, cada periodo muestra «N versiones» y abre un diálogo con fecha, motivo, cuentas, movimientos, activo y utilidad de cada una, con **«Ver»** y **«Restaurar esta versión»**.
- Verificado: restaurar devolvió el periodo a `cerrado`, con su activo y su cierre de vuelta.

### 4. Bitácora e importaciones (H08)
- `repositorio/bitacora.py`: 16 acciones registradas (crear, editar, archivar, restaurar y eliminar cliente; importar directorio; subir archivos; calcular, cerrar, reabrir y eliminar periodo; restaurar versión; cálculo rechazado; guardar parámetros). **Nunca lanza**: si la bitácora falla, el trabajo del contador sigue.
- `repositorio/importaciones.py`: cada archivo subido queda con nombre, **sha256**, tamaño, hojas y formatos reconocidos. Si el mismo archivo se sube dos veces, la respuesta lo avisa en `repetidos`.
- Ficha › **Actividad⁰⁸**: bitácora a la izquierda y archivos subidos a la derecha. Verificado con 11 líneas.

## Verificación
| Comprobación | Resultado |
|---|---|
| Pruebas | ✅ **128** (111 anteriores + 17 nuevas en `test_historial.py`) |
| `tsc --noEmit` | ✅ limpio |
| `lint:diseno` | ✅ 0 |
| `npm run build` | ✅ |
| Recorrido en la interfaz (`scripts/flujo-fase1.mjs`) | ✅ periodo cerrado → aviso y datos intactos → reabrir y recalcular → 2 versiones → restaurar → actividad |

## Cambios en pruebas existentes
- `test_periodos_sugerencias.py · _resultado(...)`: el ayudante ahora genera resúmenes con `movimientos=5` además de `cuentas=10`. Antes construía resultados imposibles (10 cuentas, 0 movimientos) que la guarda nueva rechaza con razón.
- `test_recalcular_reemplaza_y_no_duplica` sigue verde sin cambios: recalcular un periodo **no cerrado** sigue reemplazando, que es lo correcto; lo nuevo es que la versión anterior queda guardada (lo comprueba `test_recalcular_deja_la_version_anterior_en_el_historial`).

## Corregido de paso
- `con_cierre` salía siempre verdadero: el tipo JSON guarda `None` como `null`, no como NULL de SQL, así que `isnot(None)` nunca era falso.
- El diálogo heredaba `white-space: nowrap` y la alineación a la derecha de la celda de tabla desde la que se abre; el texto se salía del cuadro. Ahora `Dialogo` aísla su propio contexto de texto.

## Nota para la Fase 2
La guarda de periodo cerrado afecta la recuperación de FANANT: hay que **reabrir primero**, que ahora guarda el cierre bueno en el historial. Si el recálculo no coincide centavo a centavo, ese cierre se restaura desde la ficha.
