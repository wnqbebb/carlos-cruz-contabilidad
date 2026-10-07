# Fase 1 · Cimientos — informe

Fecha: 2026-10-06 · build mostrado en el pie de cada captura.

## Qué se hizo

| Pieza | Archivo | Estado |
|---|---|---|
| Geist Sans/Mono autoalojadas (@fontsource, subconjunto latino) | `src/styles/tokens.css` | ✅ |
| Google Fonts (Plus Jakarta, Inter, JetBrains) retirado | `index.html` | ✅ |
| Tokens: color, radios, materiales, tipografía, rejilla, movimiento | `src/styles/tokens.css` | ✅ |
| Tailwind lee solo de tokens (`--color-*: initial` borra la paleta de fábrica) | `src/styles/tokens.css` | ✅ |
| Escala tipográfica `.t-*` y los 5 materiales | `src/index.css` | ✅ |
| Lienzo: papel + rejilla de 12 columnas (8 %) + grano | `index.css`, `Marco.tsx` | ✅ |
| Migración: 387 clases de paleta + 199 nombres viejos + 7 degradados + 13 hex/rgb + 19 emojis | 20 archivos TSX | ✅ |
| Cifras exactas: `pesosCorto` fuera de todo lo que no es eje de gráfica (15 usos) | 6 archivos | ✅ |
| ID de Supabase retirado de la barra lateral («En la nube · Sincronizado») | `Marco.tsx` | ✅ |
| Sello `v2.1.0 · build <hash> · <fecha-hora>` en el pie | `vite.config.ts`, `Marco.tsx` | ✅ |
| `index.html` sin caché (FastAPI y Vercel); `/assets` inmutable | `backend/app/main.py`, `vercel.json` | ✅ |
| `iniciar.bat` recompila si `src/` es más nuevo que `dist/` | `iniciar.bat`, `scripts/necesita-build.mjs` | ✅ |
| `npm run lint:diseno` (7 reglas del spec, sección 10) | `scripts/lint-diseno.mjs` | ✅ |
| `npm run capturas -- <fase>` y comparación antes/después | `scripts/capturas.mjs`, `scripts/comparar.mjs` | ✅ |
| Tabla de contrastes | `docs/diseno/CONTRASTES.md` | ✅ (34 pares, todos AA) |

## Verificación

| Comprobación | Resultado |
|---|---|
| `npm run build` | ✅ |
| Pruebas backend | ✅ 111 verdes |
| `tsc --noEmit` | ✅ limpio |
| `npm run lint:diseno` | ✅ 0 infracciones (línea base: 443) |
| Desborde horizontal a 390 px | ✅ ninguno en las 5 pantallas (Clientes desbordaba 22 px: corregido) |

## Lista por pantalla

Esta fase cambia material, color, tipografía y cifras. La jerarquía y la maquetación de cada pantalla se rehacen en las fases 3 a 7, así que la primera pregunta queda ❌ a propósito.

| | Tablero | Clientes | Trabajar | Parámetros | Ficha |
|---|---|---|---|---|---|
| ¿Se lee primero lo más importante? | ❌ (Fase 4) | ❌ (Fase 5) | ❌ (Fase 6) | ❌ (Fase 7) | ❌ (Fase 5) |
| ¿Color, sombra o radio fuera de tokens? | ✅ ninguno de color; quedan radios a mano (`rounded-[22px]`, `rounded-2xl`) que caen con los componentes de la Fase 2 | ✅ igual | ✅ igual | ✅ igual | ✅ igual |
| Referencias aplicadas | ref-05 papel y grano, ref-08 rejilla, ref-01 tinta en la tarjeta de salud | ref-05, ref-08 | ref-05, ref-08 | ref-05, ref-08 | ref-05, ref-08, ref-01 en el KPI de utilidad |
| ¿Cifras exactas, alineadas, es-CO? | ✅ ($ 2.666.661,49, ya no «2,6 M») | ✅ | ✅ | ✅ | ✅ (sin cifra repetida en el pie) |
| ¿Funciona a 390 px? | ✅ | ✅ | ✅ | ✅ (tabla ancha se desplaza dentro) | ✅ |
| ¿Contraste AA? | ✅ (la píldora «Utilidad neta» había quedado blanco sobre azul pálido: corregida) | ✅ | ✅ | ✅ | ✅ |

Antes/después: `capturas/fase-1/comparar-*.png`.

## Pendiente que no es de esta fase
- La tarjeta «Salud contable» y el bloque «Mes de ene 25» siguen ahí: el spec los elimina en la Fase 4.
- El tono `verde` de `Insignia` ya pinta azul; el nombre desaparece con la Insignia nueva (Fase 2).
- El estado técnico de Supabase (ID, error) va a Parámetros › Sistema en la Fase 7.
