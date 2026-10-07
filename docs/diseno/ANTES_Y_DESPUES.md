# Antes y después · Carlos Cruz v2.1

Rediseño completo en 9 fases según `ESPECIFICACION.md`. Cada fase tiene su informe en `informes/fase-N.md` y sus capturas en `capturas/fase-N/`.

## Capturas lado a lado

| Pantalla | Escritorio | Móvil (390 px) |
|---|---|---|
| Tablero (con cifras reales, antes del incidente del 6 oct, ver abajo) | `capturas/fase-4/comparar-01-tablero.png` | `capturas/fase-4/comparar-01-tablero-movil.png` |
| Tablero (estado final) | `capturas/fase-9/comparar-01-tablero.png` | `capturas/fase-9/comparar-01-tablero-movil.png` |
| Clientes | `capturas/fase-9/comparar-02-clientes.png` | `capturas/fase-9/comparar-02-clientes-movil.png` |
| Trabajar | `capturas/fase-9/comparar-03-trabajar.png` | `capturas/fase-9/comparar-03-trabajar-movil.png` |
| Parámetros | `capturas/fase-9/comparar-04-parametros.png` | `capturas/fase-9/comparar-04-parametros-movil.png` |
| Ficha del cliente | `capturas/fase-9/comparar-05-ficha.png` | `capturas/fase-9/comparar-05-ficha-movil.png` |
| Flujo completo de Trabajar (7 pasos) | `capturas/fase-6/t01…t07*.png` | ídem `-movil` |
| Estado financiero impreso | `capturas/fase-6/t07-impresion.png`, `.pdf` | — |
| Preloader | `capturas/fase-8/preloader-*.png` | ídem `-movil` |

> **Por qué el Tablero final muestra $ 0:** el 6 oct a las 18:12 alguien calculó desde un navegador un archivo sin cuentas para FANANT, y el sistema reemplazó el periodo cerrado de enero 2025. No es el diseño: es la lógica de guardado (ver `PROPUESTAS.md`, punto 5). Las capturas de la Fase 4 muestran el mismo Tablero con las cifras reales.

## Criterio de aceptación del spec

> «Al comparar actual-01-tablero.png con la nueva captura, nadie debe poder decir que es la misma aplicación con otros colores.»

| Referencia | Dónde se reconoce en la app |
|---|---|
| ref-01 Carpeta negra | Expediente héroe del Tablero; carpetas papel en Clientes, Trabajar · 01 y el carrusel; la carpeta negra que se abre en el preloader |
| ref-02 Cartel suizo | Títulos display (Tablero, Clientes, razón social de la ficha); «CUADRA.» del preloader; «404.»; cifra héroe display-xl |
| ref-03 Casos de estudio | Etiquetas «01 • RESUMEN», fila de métricas con pie diminuto bajo la utilidad, botones píldora negros, flechas circulares y carrusel con la vecina asomando |
| ref-04 Esferas | Avatar único por NIT en todo el sistema; esfera de 240 px que deriva y metadatos en las cuatro esquinas de la ficha |
| ref-05 Materiales | Papel con grano; Hoja, Hundido (campos, zona de arrastre), Expediente, Cristal y Brillo «Cuadra». Sin neumorfismo, bisel ni satén |
| ref-06 Interruptor ⁰¹ ⁰² | Expedientes⁰¹/Tabla⁰², años de Parámetros, densidad de tablas; índices en la navegación (Tablero⁰¹…) y en las pestañas; meta-encabezado de cuatro columnas en cada página |
| ref-07 Cristal | Buscador ⌘K, paleta, barra móvil, paso a paso de Trabajar, barra flotante de estados financieros, diálogos, desplegable de orden. Siempre con contenido detrás |
| ref-08 Rejilla y moodboard | Rejilla de 12 columnas al 8 % alineada al contenido; línea horizontal bajo el meta-encabezado; subrayado azul tinta que se dibuja; carpeta azul en los estados vacíos |

## Qué se eliminó del diseño anterior
- Paleta índigo/violeta, degradados, píldora índigo «Utilidad neta», tarjeta azul «Salud contable» con curva sin ejes y el bloque duplicado «Mes de ene 25».
- Cifras abreviadas («$ 11 M», «$ 2,6 M»): todas son exactas en es-CO. La «M» solo vive en ejes de gráficas.
- ID del proyecto de Supabase en la barra lateral (ahora solo en Parámetros › Sistema).
- «Carlos Cruz» repetido en dos barras; «Panel de control».
- Plus Jakarta Sans, Inter y JetBrains Mono desde Google Fonts: ahora Geist autoalojada.
- Jornada como texto crudo `2026-01-01=44; …`.
- SMMLV y auxilio escritos a mano en el Tablero (ahora se leen de los parámetros).
- 443 infracciones de diseño (clases de paleta, hex, emojis, degradados): hoy `lint:diseno` da 0 y falla si alguien las reintroduce.

## Calidad (spec 9)

| Comprobación | Resultado |
|---|---|
| Lighthouse accesibilidad · buenas prácticas, escritorio (Tablero, Clientes) | 100 · 100 |
| Lighthouse accesibilidad · buenas prácticas, móvil (Tablero, Clientes, Ficha, Trabajar, Parámetros) | 100 · 100 en las cinco |
| Contraste AA | 34 pares medidos, todos pasan (`CONTRASTES.md`) |
| Foco visible | Anillo azul de 2 px con 2 px de separación en todos los controles |
| Teclado | Orden lógico; «Ir al contenido»; Ctrl/⌘ K abre la paleta; interruptores y pestañas con flechas |
| El color nunca va solo | ▲ ▼, paréntesis, texto en cada insignia, íconos en avisos |
| 390 px | Sin desborde horizontal en ninguna pantalla ni paso; las tablas se desplazan dentro de su contenedor |
| Menos movimiento | Todas las animaciones se apagan; el preloader queda en monograma + lema |
| Pruebas backend | 111 verdes al cierre de cada fase |
| TypeScript | Limpio al cierre de cada fase |

## Defectos de base encontrados durante el rediseño (y corregidos)
1. El cristal nunca desenfocó en Edge/Chrome (el minificador eliminaba `backdrop-filter`).
2. El CSS propio ganaba a las utilidades de Tailwind (desbordes en móvil).
3. El breakpoint de escritorio no se aplicaba (estaba en px junto a breakpoints en rem).
4. Aritmética con floats en el panel del periodo (descuadre, razón corriente, endeudamiento, margen).
5. La impresión de estados financieros salía en blanco.
6. Varios contrastes insuficientes (texto blanco sobre azul pálido, tinta sobre azul sólido).

## Pendiente que necesita su decisión
- **Urgente:** proteger los periodos cerrados contra sobrescritura (`PROPUESTAS.md`, punto 5) y recuperar enero 2025 de FANANT volviendo a cargar sus archivos.
- Reempaquetar el ejecutable `.exe`: el que existe congela la interfaz vieja.
- El resto de propuestas (`PROPUESTAS.md`) son opcionales.
