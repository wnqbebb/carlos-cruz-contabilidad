# Fase 8 · Más definición, identidad por página, color por cliente, modo claro/oscuro/sistema

Capturas: `privado/capturas/v22/fase-8/` — las 11 pantallas en **claro y oscuro, a 1440 y 390 px** (44 capturas, JPEG). Probado en la copia aislada.

## 8.1 Tres planos que se distinguen
- Tokens nuevos: `--lienzo`, `--barra`, `--hoja`, `--hoja-2`, `--campo`, `--linea` (10 %), `--linea-fuerte` (18 %), `--borde-campo` (24 %). `--papel` queda como alias del lienzo.
- **Campos**: fondo `--campo` y borde de 1 px `--borde-campo`; etiquetas en `--grafito`. Se abandonó el «hundido» gris sobre gris (también en los buscadores de Clientes y Trabajar).
- **Tarjetas**: borde `--linea` y sombra Hoja.
- **Rejilla**: solo en la franja de cabecera y en el preloader, al 5 %.
- **Pestañas**: activa en tinta 600 con subrayado de 2 px en el color de la sección o del cliente y contador relleno; inactivas en grafito 500; al pasar, subrayado de 1 px.
- **Barra lateral**: fondo `--barra`; la píldora activa toma el color de la sección.

**Ajuste a los valores del encargo, medido:** con los hex pedidos tres pares no llegaban al mínimo que el mismo encargo fija (1,10:1): campo #FFFFFF sobre hoja #FFFDF9 daba **1,02:1**; en oscuro, barra #151514 sobre lienzo **1,06:1** y campo #121211 sobre hoja **1,09:1**. Se movió lo justo: hoja clara **#F6F3ED** (y hoja-2 #EFEBE4), barra oscura **#1A1A18**, campo oscuro **#0F0F0E**. Además `--gris` pasó de #66655F a **#5C5B55** porque Lighthouse midió 4,19:1 del metaencabezado sobre la cabecera de Clientes.

## 8.2 Cada página se reconoce al instante
| Sección | Cabecera | Píldora activa |
|---|---|---|
| Tablero⁰¹ | papel neutro, saludo, fecha y zona de arrastre | tinta |
| Clientes⁰² | velo de azul tinta al 6 % | azul tinta |
| Trabajar⁰³ | **banda de taller oscura** (#24221F; #2A2824 en oscuro) con el título y la regla graduada 01–07 | grafito |
| Parámetros⁰⁴ | gris frío #E6E7E9 | gris frío oscuro |
| Ficha de cliente | **el color del cliente**, con un velo que nace desde su esfera | el color del cliente |

- La franja de cabecera es del marco: empieza detrás de la barra superior y llega hasta debajo del título. Cada página pone su título en ella con `<Cabecera>` (un portal). Lleva el **número de índice gigante y delineado** a la derecha.
- Al cambiar de página, el tono de la cabecera y de la píldora cambia en **0,4 s**.
- Dentro de la banda de taller el texto, los azules y las líneas se redefinen por variables: el contraste se mantiene en los dos modos.

## 8.3 El color de cada cliente, desde su esfera — `frontend/src/colorCliente.ts`
De los tres colores de la esfera (hash del NIT) se toma el tono medio en **OKLCH**, ponderado como en la esfera, más un desvío pequeño del mismo hash para que dos clientes con la misma terna no queden idénticos. Se derivan `--cliente-tono` (L 0,55), `--cliente-profundo` (L 0,28), `--cliente-velo` (12 %; 10 % en oscuro) y `--cliente-texto` (L ajustada hasta **4,5:1** sobre la hoja, en cada modo). **Ningún cliente cae a menos de 20° del rojo semántico.** Se calculan los dos modos y `tokens.css` elige según `data-tema`.

Se aplica en: el velo de la cabecera, el subrayado de pestañas, la carpeta héroe de la ficha (`--cliente-profundo` con borde un poco más claro), la franja de la pestaña de su carpeta en Clientes, el anillo de foco dentro de la ficha y la serie principal de sus gráficas. Los colores semánticos (rojo de pérdida, azul de «cuadra») no se tocan. **El catálogo `/diseno` muestra 8 NIT** con sus cuatro colores en claro y en oscuro, el tono y el contraste logrado.

## 8.4 Modo claro, oscuro y sistema
- Selector en la barra superior con el Interruptor: **Claro⁰¹ | Oscuro⁰² | Sistema⁰³** (en el teléfono, con íconos). Se guarda en el navegador; por defecto «Sistema», que sigue al sistema operativo en vivo. `index.html` fija el modo antes de pintar: no hay destello claro.
- Todos los tokens de color tienen valor oscuro, con los del encargo (#0E0E0D, #1B1B19, #EDEAE4, #8FA6FF, #FF7B70, #F2A65A…). **`lint:diseno` ahora falla si un token de color no tiene valor oscuro** (probado quitando uno).
- La carpeta héroe se invierte a papel con texto oscuro; en la ficha usa el color profundo del cliente con borde más claro. Sombras casi nulas (profundidad por bordes y un leve brillo); grano al 5 % en `screen`; esferas más brillantes.
- Impresión y PDF siempre en claro (el bloque oscuro es solo `@media screen`); el preloader respeta el modo.
- Textos blancos fijos sobre azul o rojo pasaron a `--sobre-color` (blanco en claro, casi negro en oscuro, donde el azul es claro).

## Verificación
**Contrastes** (`frontend/scripts/contrastes.mjs` → `docs/diseno/CONTRASTES.md`, generado desde `tokens.css`): 34 pares por modo — superficies lienzo↔hoja, barra↔lienzo, campo↔hoja (≥ 1,10:1, más el borde) y todos los pares de texto en AA. **Todos cumplen en claro y en oscuro.**

**Lighthouse 12** (accesibilidad · buenas prácticas), con el modo verificado por el brillo de la captura (claro ≈ 220, oscuro ≈ 40):

| Página | Claro móvil | Claro escritorio | Oscuro móvil | Oscuro escritorio |
|---|---|---|---|---|
| Tablero | 100 · 100 | 100 · 100 | 100 · 100 | 100 · 100 |
| Clientes | 100 · 96 | 100 · 100 | 100 · 96 | 100 · 100 |
| Ficha | 100 · 100 | 100 · 100 | 100 · 100 | 100 · 100 |
| Trabajar | 100 · 100 | 100 · 100 | 100 · 100 | 100 · 100 |
| Parámetros | 100 · 100 | 100 · 100 | 100 · 100 | 100 · 100 |

| Comprobación | Resultado |
|---|---|
| Pruebas del backend | ✅ 229 (la fase no tocó el backend) |
| `tsc --noEmit` | ✅ limpio |
| `npm run lint:diseno` | ✅ 0 infracciones, con la regla nueva de tokens oscuros |
| `npm run build` | ✅ |
| Capturas (`frontend/scripts/capturas-modos.mjs`) | ✅ 44 capturas, sin errores de consola y sin desbordes a 390 px, `data-tema` comprobado en cada una |
| Recorridos de las fases 5 y 7 repetidos tras el cambio visual | ✅ sin errores |

Defectos encontrados en la revisión de capturas y corregidos: los dos selectores de tema (escritorio y teléfono) se veían a la vez; la carpeta héroe de la ficha era ilegible en oscuro (las utilidades ganaban a la regla: ahora se redefinen variables); el enlace azul en la banda de taller tenía poco contraste en claro; el buscador y la zona de documentos se apretaban a 390 px; el superíndice de la píldora tenía opacidad y bajaba a 4,28:1.
