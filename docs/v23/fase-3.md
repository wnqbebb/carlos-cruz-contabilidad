# v2.3 · Fase 3 — Clientes y Trabajar en un solo lugar

## Qué cambió

- **Un expediente por cliente** (`paginas/Expediente.tsx`) reemplaza a la ficha y a «Trabajar».
  Secciones: Resumen · Contabilidad · Archivos y actividad · Datos (`?seccion=`). Renta llega en la Fase 5.
- **Contabilidad** (`componentes/Contabilidad.tsx`) es la sección por defecto:
  - sin periodos: zona de subida → preguntas → resultado, todo sin salir del cliente;
  - con periodos: abre el último. Selector pegajoso «‹ Septiembre 2026 · cerrado ▾ ›».
    Cambiar de mes **conserva el informe y la posición** (`?periodo=AAAA-MM&vista=…`);
    mientras llega el mes nuevo se sigue viendo el anterior, así la página no salta;
  - un solo botón principal: **Cerrar periodo** (`POST /api/periodos/{id}/cerrar`, cierra con los
    saldos guardados; ya no hace falta la sesión de trabajo). Si hay nómina doble o descuadre, pide confirmación;
  - «Descargar» (PDF, Excel, saldos) y «···» (subir otro periodo, nota, reabrir/eliminar) son menús.
- **Una sola vista del resultado** (`componentes/VistaContable.tsx`): la misma para lo recién calculado y lo guardado.
  Lista lateral agrupada (en el celular, un selector):
  Estados financieros · Balances · Libros · Detalle. Lo avanzado (asiento de cierre, libro mayor por cuenta,
  kardex, auditorías) va plegado en «Ver…». Con la sesión del último cálculo, los ajustes se pueden cambiar y recalcular.
- Navegación: Tablero⁰¹ · Clientes⁰². Sin «Trabajar» ni el botón «Nuevo periodo» de la barra superior.
- Enlaces viejos: `/trabajo` → `/clientes`; `/trabajo?cliente=X[&sesion=S]` → `/clientes/X?seccion=contabilidad[&sesion=S]`;
  `/clientes/X?vista=nomina` → `?seccion=contabilidad&vista=nomina` (y así con las demás pestañas antiguas).
- La puerta única (soltar un archivo en cualquier pantalla) vuelve a la contabilidad del cliente.
- Tareas del Tablero: rutas nuevas (`?seccion=contabilidad`, `?seccion=archivos`); la tarea global
  «Faltan los valores legales» solo informa (sin botón «Hacer ahora»).
- Se quitaron los «Tres ejemplos» de la pantalla de subida (su descarga apuntaba a una ruta que ya no existía).

Borrados: `Trabajo.tsx`, `Resultados.tsx`, `ResultadoGuardado.tsx`, `ClienteFicha.tsx`, `Inicio.tsx`.

## Control de calidad

| Prueba | Resultado |
|---|---|
| `pytest backend/tests` | 268 pasan |
| `tsc --noEmit` | limpio |
| `npm run lint:diseno` | 0 infracciones |
| `npm run build` | correcto |
| `flujo-v23-expediente.mjs` (claro/oscuro · 1440/390) | 12 meses hacia atrás desde Resultados, Balance definitivo y Libro diario: la vista no cambia y la página no salta; redirecciones viejas correctas; ≤ 5 pestañas; sin errores |
| `flujo-v23-trabajo.mjs` | subir → enlace viejo `/trabajo?…&sesion=` → calcular → ajustes → **Cerrar periodo** → «cerrado»; sin errores |
| `flujo-v23-preguntas.mjs` | 2 preguntas, respuesta por bloque registrada; sin errores |
| `capturas-v23.mjs` (6 rutas × 4 variantes) | sin errores de consola ni desbordes |

Todo contra la copia aislada (SQLite, puerto 8001).
