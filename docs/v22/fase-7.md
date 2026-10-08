# Fase 7 · Tablero del contador (+ H13, H18)

Capturas: `docs/v22/capturas/fase-7/`. Probado en la copia aislada. La base real no se tocó.

## Qué se quitó
El resultado del mes de la cartera, la ecuación contable, la tarjeta de nómina (SMMLV, auxilio y jornada siguen en Parámetros) y toda cifra financiera de un cliente individual (las carpetas recientes ya no muestran la utilidad).

## Qué queda, en orden
1. **Saludo, fecha y «Subir archivo»**, con una zona de arrastre amplia al lado. El nombre del saludo sale de la configuración del contador.
2. **Cuatro indicadores**: clientes activos, honorarios mensuales (suma exacta, sin archivados), al día y atrasados.
3. **Tareas sugeridas**, el bloque principal: prioridad (urgente, importante, cuando pueda), cliente, qué hacer, por qué (el dato exacto) y dos botones: **«Hacer ahora»** lleva al sitio donde se resuelve y **«Posponer hasta mañana»** la saca del tablero hasta mañana. Las dos quedan en la bitácora. Tipos de tarea:
   - contabilizar meses atrasados o el primer periodo;
   - cerrar periodos calculados;
   - revisar descuadres;
   - responder las preguntas pendientes de una importación (abre Trabajar con la misma subida y sus preguntas, sin volver a subir el archivo; si la sesión ya caducó, lo dice);
   - revisar periodos en cero;
   - alertas críticas (causal de disolución);
   - llenar meses que faltan;
   - completar la ficha **solo si ya hay algo que firmar**.
4. **La cartera mes a mes** (12 meses): cerrados, calculados por cerrar y sin contabilizar, con su tabla equivalente.
5. **Clientes recientes** en carpetas (al día o atrasado, último corte), con «Ver todos».
6. **Actividad reciente**: las últimas 8 líneas de la bitácora, con el cliente o el archivo.

## H13 · Los agregados los cuenta el servidor
`/api/tablero` (`backend/app/inteligencia/tablero.py`) entrega indicadores, tareas, meses, recientes y actividad en una sola llamada, con cuatro consultas masivas (no una por cliente). La pantalla no deduce nada. Un mes cuenta como «sin contabilizar» solo desde que se lleva al cliente (su primer periodo o la fecha de su ficha) y nunca el mes en curso. De paso, la serie vieja sumaba importes con `SUM()` de SQL (en SQLite eso pasa por `float`); ya no se usa.

## H18 · Los datos del contador salen de la configuración
Nombre, cargo, tarjeta profesional y municipio viven en `data/contador.json` (o en variables `CONTADOR_*`), se editan en **Parámetros › Contador** y se leen con `/api/contador`. El logotipo, la cabecera, el preloader («Guacarí, Valle del Cauca») y el saludo los toman de ahí. Ya no hay ninguno escrito a mano en la interfaz.

## Defecto corregido de paso
`PUT /api/parametros/{año}` usaba la bitácora sin importarla: guardar parámetros fallaba. Prueba de regresión nueva.

## Verificación
| Comprobación | Resultado |
|---|---|
| Pruebas del backend | ✅ **229** (10 nuevas en `test_tablero.py`) |
| `tsc --noEmit` | ✅ limpio |
| `npm run lint:diseno` | ✅ 0 infracciones (49 archivos) |
| `npm run build` | ✅ |
| Recorrido Playwright (`frontend/scripts/flujo-fase7.mjs`) | ✅ sin errores de consola ni en el log |

Recorrido con una cartera de tres clientes: saludo «Buenos días, Carlos.», 3 activos, $ 250.000 de honorarios, 0 al día y 3 atrasados; 6 tareas ordenadas por urgencia; posponer una la quita y sigue quitada al recargar; «Hacer ahora» sobre «Responder las preguntas del archivo» abrió Trabajar con el panel de preguntas; 12 meses, 8 líneas de actividad, carpetas recientes; 390 px sin desborde; el preloader muestra el municipio de la configuración.
