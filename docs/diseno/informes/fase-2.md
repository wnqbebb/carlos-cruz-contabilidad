# Fase 2 · Componentes de firma — informe

Catálogo vivo en `/diseno` (fuera del menú). Capturas: `capturas/fase-2/06-catalogo*.png` y detalle por componente en `capturas/fase-2/detalle/`.

## Componentes (`frontend/src/ui/`)

| Componente | Qué hace | Ref. |
|---|---|---|
| `Expediente` | Carpeta con pestaña (42 % del ancho, 22 px, rampa inclinada). SVG recalculado con ResizeObserver; sombra que sigue la silueta (`--filtro-expediente`, halo cálido). Hover: pestaña −4 px, giro −0,6°, flecha +3 px en 0,3 s. Variantes tinta y papel. Enlace interno, externo, botón o estático. | ref-01 |
| `EsferaCliente` | Avatar del NIT (hash FNV-1a → 3 de `--esfera-1…6` y posición de focos). 32 / 56 / 240 px; a 240 deriva 12–18 s. | ref-04 |
| `EtiquetaSeccion` | «01 • RESUMEN» en píldora con borde `--linea`. | ref-03 |
| `MetaEncabezado` | Cuatro columnas meta + línea inferior (dos en móvil). | ref-06 |
| `TituloPagina` | Título `display`, interlineado 0,92. | ref-02 |
| `Interruptor` | Píldora tinta; la opción activa se desliza con GSAP Flip (0,35 s). Índices 01, 02… Teclado: flechas, Inicio, Fin (radiogroup). | ref-06 |
| `Cifra` | Exacta es-CO, tabular; ▲/▼, paréntesis para EF, odómetro sobre el texto (sin floats), `title` exacto, `encajar` para que nunca desborde. | ref-02, ref-03 |
| `InsigniaEstado` | Cuadra (azul + brillo), Descuadre, Por cerrar, Cerrado · listo para firmar, Activo, Inactivo, Archivado. Cada una con texto e ícono. | — |
| `BotonPrimario` / `BotonAcento` / `BotonFantasma` | 44 px (36 compacto), flecha que avanza 3 px, estado cargando y deshabilitado. | ref-03 |
| `EnlaceSubrayado` | Subrayado azul tinta de 1,5 px que se dibuja de izquierda a derecha. | ref-08 |
| `TablaContable` | Encabezado pegajoso, D/H agrupadas, sangría y peso por nivel PUC, hover sin cebra, totales con doble línea + insignia, densidad cómoda/compacta, punto rojo para saldo contrario. | spec 6.5 |

**Decisión técnica a señalar:** la naturaleza de cada cuenta (débito/crédito) **no** se calcula en la interfaz. El backend ya la entrega por fila (`naturaleza: "D" | "C"`) con las excepciones del PUC (1592 depreciación, 1299 provisiones, 6225…). `avisoSaldoContrario` solo compara débito y crédito con aritmética de texto. Así no se duplica lógica contable.

## Verificación

| Comprobación | Resultado |
|---|---|
| `npm run build` | ✅ |
| Pruebas backend | ✅ 111 verdes |
| `tsc --noEmit` | ✅ |
| `npm run lint:diseno` | ✅ 0 |
| Consola del navegador en `/diseno` (con movimiento activado) | ✅ sin errores ni avisos |
| Interacción probada con Playwright | ✅ Flip del interruptor, flechas del teclado, giro −0,6° del Expediente, odómetro a mitad de recorrido (`detalle/odo-mitad.png`) |
| 390 px | ✅ sin desborde |

## Lista del catálogo

| | Catálogo `/diseno` |
|---|---|
| ¿Se lee primero lo más importante? | ✅ Cada bloque abre con su EtiquetaSeccion; el Expediente tinta es el único elemento pesado |
| ¿Color, sombra o radio fuera de tokens? | ✅ Ninguno (lint) |
| Referencias aplicadas | ref-01 Expediente · ref-02 escala display · ref-03 etiquetas, métricas y botón píldora · ref-04 esferas · ref-05 materiales · ref-06 interruptor y meta-encabezado · ref-07 cristal sobre esfera · ref-08 rejilla y subrayado |
| ¿Cifras exactas, alineadas, es-CO? | ✅ La muestra del balance cuadra: 46.733.560,72 por lado, sumado con aritmética exacta |
| ¿Funciona a 390 px? | ✅ La cifra héroe se encaja al ancho, las métricas se apilan |
| ¿Contraste AA? | ✅ (CONTRASTES.md) |

## Corregido durante la revisión
- Breakpoint `escritorio` declarado en px: Tailwind lo ordenaba antes que `sm` y nunca ganaba. Ahora va en rem.
- El cristal no se veía: un script mío había dejado caracteres de control invisibles en una expresión regular. Se reescribió y se verificó que `src/` no tenga ninguno.
- Superíndices del Interruptor salían diminutos (doble superíndice).
- Métricas encimadas y flecha sobre el texto en el Expediente a 390 px.

## Qué no cambia todavía
Las pantallas reales siguen usando los componentes viejos de `componentes/ui.tsx`. Se migran pantalla por pantalla en las fases 3 a 7, como pide el spec.
