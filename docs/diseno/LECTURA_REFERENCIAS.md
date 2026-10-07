# Fase 0 · Lectura de las referencias

Colores medidos con muestreo de píxeles sobre las imágenes guardadas en
`referencias/`. Donde mi lectura difiere del spec, lo digo al final de cada una.

---

## ref-01 · Carpeta negra
`referencias/ref-01-carpeta-negra.png` (1080 × 1350)

1. Tinta de la carpeta medida: **#161616**. El spec dice `#1A1A1A` para la
   referencia y `--tinta #141414` para el sistema: coinciden a ±4.
2. Proporción de la pestaña: el cuerpo mide ≈ 707 px de ancho; la pestaña
   arranca en x ≈ 575 y llega al borde derecho → **≈ 45 % del ancho**. Sube
   ≈ 38 px sobre un cuerpo de ≈ 600 px de alto (≈ 6 %). El borde izquierdo de
   la pestaña es una rampa de ≈ 85 px, no un escalón vertical.
3. Radio de las esquinas ≈ 40 px sobre 707 px (≈ 5,6 % del ancho). A tamaño de
   tarjeta real (≈ 460 px) eso da ≈ 26 px: cuadra con el radio 26 del spec.
4. Halo cálido confirmado: el borde exterior mide **#FEF3EF** sobre fondo
   `#FFFFFF`. Es un resplandor rosado-anaranjado muy tenue, no gris.
5. Jerarquía interna: flecha ↗ arriba a la derecha (trazo grueso, ≈ 8 % del
   ancho), titular blanco semibold en dos líneas, párrafo gris claro (**#D5D5D5**)
   con interlineado amplio. Mucho aire: el texto ocupa la mitad inferior-izquierda.

**Dónde:** componente `Expediente` (KPI héroe del Tablero, tarjetas de cliente,
accesos de navegación). **Coincide con el spec.**

---

## ref-02 · Cartel rojo
`referencias/ref-02-cartel-suizo.png` (1200 × 1600)

1. Rojo del campo medido: **#BE1005**, más profundo que el `--rojo-cartel
   #D7261E` del spec.
2. Titular «NOT IN THE MOOD.» en tres líneas que ocupan ≈ 36 % del alto, con
   interlineado ≈ 0,88: las líneas casi se tocan. Alineado a la izquierda,
   pegado al margen (≈ 30 px de 1200).
3. Grotesca neutra muy pesada, sin versalitas ni tracking abierto: todo el
   carácter sale del tamaño, no del estilo.
4. Bloque secundario abajo a la izquierda en el mismo tipo, ≈ ⅕ del tamaño del
   titular; créditos diminutos abajo a la derecha («BM / 587.», «PHOTOGRAPHY BY…»).
5. Grano de papel visible sobre el rojo: textura fina, no ruido digital.

**Dónde:** títulos de página, número héroe del Tablero, palabra «CUADRA.» del
preloader. El rojo cartel solo para pérdidas y descuadres.
**Diferencia:** el rojo de la referencia (#BE1005) es más oscuro que el del
spec. Propongo dejar el del spec para rellenos (lee mejor en pantalla) y no
cambiarlo sin su visto bueno.

---

## ref-03 · «What We've Built»
`referencias/ref-03-casos-estudio.png` (736 × 736)

1. Etiqueta de sección «005 • CASE STUDIES»: índice en gris, punto negro, texto
   en mayúsculas diminutas, todo dentro de una píldora de borde muy suave.
2. Titular grande centrado, peso medio (no negrita), tracking negativo.
3. Fila de tres métricas «+40% / +25% / 3x», cifras ≈ 3× el tamaño de su pie
   («Demo Booking», «Closing Rate»), sin separadores entre ellas.
4. Carrusel: la tarjeta activa al centro, las vecinas asoman recortadas y
   desvanecidas a izquierda y derecha, con flechas circulares negras.
5. Botón píldora negro pequeño y centrado («Explore all Case Studies»), y
   paginación de puntos donde el activo es una píldora alargada.

**Dónde:** `EtiquetaSeccion`, filas de indicadores, `BotonPrimario`, carrusel de
clientes recientes. **Coincide con el spec.**

---

## ref-04 · Esferas
`referencias/ref-04-esferas.png` (736 × 978)

1. Seis esferas sobre gris muy claro (**#F2F2F2**), cada una ≈ 40 % del ancho
   de su recuadro, centradas.
2. Cada esfera combina 2–4 colores con borde difuso y **aberración cromática**:
   franjas verdes y rosadas en el contorno. No es un degradado plano.
3. Halo exterior suave del mismo color de la esfera, que se funde en el fondo.
4. Metadatos editoriales en las cuatro esquinas: arriba-izquierda «ID —
   UNKNOWN / ORIGINAL MIX», arriba-derecha «ULR — 000», abajo-izquierda fecha
   «12 — 24 — 2017», abajo-derecha el logotipo. Raya larga «—» como separador.

**Dónde:** `EsferaCliente` (avatar generado desde el NIT), aurora de las
cabeceras, metadatos de esquina en la ficha del cliente.
**Nota:** la aberración cromática trae verde a los bordes. Como el sistema no
admite verde, las esferas usarán solo azul, ámbar, ciruela y rojo de la paleta.

---

## ref-05 · Materiales
`referencias/ref-05-materiales.png` (1152 × 2048)

1. Papel medido: **#F2EDE7**. El spec dice `--papel #F2EFE9`: coinciden a ±2.
2. Drop shadow (03): sombra corta y dura abajo-derecha, el cuadro queda
   apenas más oscuro que el fondo (**#EDE5E0**).
3. Inner shadow (07): el cuadro parece hundido, con sombra en el borde
   superior interno.
4. Glow (04) y outer glow (06): resplandor de color alrededor del borde, cálido
   en uno y azul en el otro.
5. Texture overlay (10): grano fino tipo papel de acuarela.

**Dónde:** fondo general y los cinco materiales de la sección 4.4 (Hoja,
Expediente, Hundido, Cristal, Brillo «Cuadra»), más el grano.
**Coincide:** neumorfismo (02), bisel (08) y satén (09) quedan fuera, como
pide el spec.

---

## ref-06 · Interruptor Future⁰¹ / Now⁰²
`referencias/ref-06-interruptor-suizo.png` (1200 × 1383)

1. Fondo gris neutro **#EBEBEB**, sin calidez.
2. Interruptor: píldora negra exterior que contiene una píldora clara a la
   derecha; las dos palabras con superíndices ⁰¹ ⁰² pegados arriba.
3. Rejilla de cuatro columnas de texto diminuto en el borde superior («1.»,
   frase, «2.», frase, «Index», «Ch.— I»), alineadas a columnas exactas.
4. Pie: «Option^SX / Temporal Mechanics» abajo-izquierda en tamaño medio,
   «Process Module: Active» al centro, «F to N» abajo-derecha.
5. El 80 % de la página está vacío a propósito: el interruptor solo, al centro.

**Dónde:** `Interruptor` (Expedientes/Tabla, años de Parámetros…),
`MetaEncabezado` de cada página, índices en la navegación.
**Coincide con el spec.**

---

## ref-07 · Cristal esmerilado
`referencias/ref-07-cristal.png` (736 × 615)

1. Tres paneles de cristal sobre una **fotografía** (escritorio, libros, luz
   cálida). El efecto existe porque detrás hay algo con color y forma.
2. «Frosted»: desenfoque fuerte, casi sin forma reconocible detrás. «Clear»:
   apenas desenfoque, se ve la imagen deformada. «Blur»: intermedio.
3. Borde claro de 1 px y radio ≈ 28 px; texto blanco grande, centrado, con
   etiqueta pequeña debajo («Concept», «iOS», «One UI»).

**Dónde:** solo superficies flotantes con algo detrás (paleta ⌘K, modales,
barra flotante de estados financieros, preloader).
**Advertencia:** sobre el papel liso de la app no hay nada que difuminar, así
que el cristal se ve como un rectángulo blanco. Ya pasó con el diseño actual.
Solo se usará encima de la aurora de esferas o de contenido real.

---

## ref-08 · Rejilla moodboard
`referencias/ref-08-rejilla-moodboard.png` (1200 × 1500)

1. Fondo **#EFEFEF**; líneas de rejilla **#BCBCBC**, o sea bien visibles
   (≈ 21 % de opacidad negra), en 5 columnas y 5 filas.
2. Palabras con tracking muy negativo («moodboard», «goals», «make stuff»):
   las letras se tocan.
3. Subrayado azul bajo las etiquetas medido: **#2038A2**, un azul tinta
   profundo. El spec usa `--azul #2347D6`, más brillante.
4. Tachado usado como recurso de voz («don't ~~die~~»).
5. Carpeta azul estilo macOS (**#73D1F7**) como único objeto ilustrado.

**Dónde:** rejilla del lienzo, `EnlaceSubrayado`, ícono de carpeta en estados
vacíos.
**Dos diferencias con el spec, a decidir:**
- **Intensidad de la rejilla.** La referencia la tiene al ≈ 21 %; el spec pide
  `rgba(20,20,20,.05)`, cuatro veces más tenue. Al 5 % sobre `#F2EFE9` casi no
  se percibe. Propongo **8 %**: se ve, pero no compite con las cifras en una
  herramienta de ocho horas diarias.
- **El azul.** El de la referencia (#2038A2) es más «tinta de pluma». El del
  spec (#2347D6) pasa contraste (6,22:1) y es más legible en botones. Propongo
  el del spec para botones y el de la referencia para subrayados y enlaces.

---

## Contrastes del spec, verificados

Sobre `--papel #F2EFE9`:

| Color | Uso | Contraste | AA texto (4,5) |
|---|---|---|---|
| `--gris #6B6A66` | metadatos | 4,72 | ✅ |
| `--azul #2347D6` | acento | 6,22 | ✅ |
| `--rojo #C21F17` | pérdida | 5,22 | ✅ |
| `--ambar #A84F06` | advertencia | 4,83 | ✅ |
| `#A9A79F` sobre `--tinta #141414` | secundario en Expediente | 7,65 | ✅ |

La tabla completa (todos los pares) va en `CONTRASTES.md` en la Fase 1.
