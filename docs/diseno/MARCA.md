# Marca · Carlos Cruz

**Contabilidad que cuadra.** — con punto final, como el cartel de ref-02.

## Monograma

Cuadrado de tinta `#141414`, radio 10 sobre 40 (25 %). Dentro, «CC» en Geist Sans 600
color papel `#F5F3EE` y, debajo, una **cuenta T mínima**: una línea horizontal con un
trazo vertical centrado. Las dos C son el nombre; la T es el oficio.

Geometría sobre una caja de 40 × 40:

| Elemento | Medida |
|---|---|
| Fondo | 40 × 40, radio 10 |
| «CC» | Geist Sans 600 a 18 px, tracking −0,03 em; ocupa x 8,0–31,9 · y 8,0–21,4 |
| Línea horizontal de la T | y = 26,5, x 11–29, trazo 1,8 (2 en el favicon), extremos redondos |
| Trazo vertical de la T | x = 20, y 26,5–33 |

Las letras están convertidas a contornos (no son texto), así que el monograma es idéntico
en la app, en el favicon y en cualquier exportación aunque la fuente no esté instalada.

- Componente: `frontend/src/componentes/Marca.tsx` → `<Monograma />`, `<Logotipo />`.
- Favicon: `frontend/public/favicon.svg` (mismos contornos).

## Logotipo

Monograma + «Carlos Cruz» (Geist 600, −0,03 em) + debajo, en meta:
`CONTADOR PÚBLICO · T.P. 103028-T`. En la barra lateral de 248 px la línea meta se parte
en dos («CONTADOR PÚBLICO ·» / «T.P. 103028-T») porque no cabe entera.

## Área de protección

Alrededor del monograma, libre de texto u otros elementos: **¼ del lado** (10 px en el
monograma de 40). Junto al nombre, la separación es de 12 px.

## Tamaños mínimos

- Monograma: 16 px (favicon). Por debajo de 24 px la T se vuelve un trazo de 1 px; se
  acepta solo en la pestaña del navegador.
- Logotipo completo: 40 px de monograma.

## Usos correctos

- Sobre `--papel`, `--hoja` o fotografía oscura.
- Monograma solo cuando el espacio no da para el logotipo (barra móvil, favicon).

## Usos incorrectos

- Cambiar los colores (nada de azul, rojo o verde en el monograma).
- Usar «CC» escrito con otra fuente o con texto en lugar de los contornos.
- Quitar la cuenta T, girarla o moverla por encima de las letras.
- Estirar, sombrear o poner degradado al cuadrado.
- Escribir el lema sin el punto final o con signos de exclamación.

## Voz

Español de Colombia, precisa, de contador: «Débitos = Créditos», «Cuadra»,
«Descuadre de $ 50.000 en el comprobante CE-014», «Listo para firmar». Nada de
«¡Genial!» ni signos de exclamación.
