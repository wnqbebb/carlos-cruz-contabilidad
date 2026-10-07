# Contrastes WCAG 2.1 · Carlos Cruz v2.1

Calculado desde `frontend/src/styles/tokens.css` (fórmula de luminancia relativa WCAG 2.1).
Mínimo AA: 4,5:1 para texto normal; 3:1 para texto ≥ 24 px o ≥ 18,7 px semibold y para bordes de controles.
Si cambia un token de color, esta tabla se vuelve a medir antes de cerrar la fase.

| Texto | Fondo | Uso | Contraste | AA |
|---|---|---|---|---|
| `--tinta` #141414 | `--papel` #F2EFE9 | texto principal | 16,05:1 | ✓ |
| `--grafito` #3A3A38 | `--papel` #F2EFE9 | texto secundario | 9,93:1 | ✓ |
| `--gris` #6B6A66 | `--papel` #F2EFE9 | metadatos | 4,72:1 | ✓ |
| `--azul` #2347D6 | `--papel` #F2EFE9 | acento, «Cuadra», enlaces | 6,22:1 | ✓ |
| `--azul-tinta` #2038A2 | `--papel` #F2EFE9 | subrayados y enlaces | 8,52:1 | ✓ |
| `--rojo` #C21F17 | `--papel` #F2EFE9 | pérdida, descuadre | 5,22:1 | ✓ |
| `--ambar` #A84F06 | `--papel` #F2EFE9 | advertencia | 4,83:1 | ✓ |
| `--tinta` #141414 | `--hoja` #FBFAF7 | texto principal | 17,65:1 | ✓ |
| `--grafito` #3A3A38 | `--hoja` #FBFAF7 | texto secundario | 10,92:1 | ✓ |
| `--gris` #6B6A66 | `--hoja` #FBFAF7 | metadatos | 5,19:1 | ✓ |
| `--azul` #2347D6 | `--hoja` #FBFAF7 | acento, «Cuadra», enlaces | 6,83:1 | ✓ |
| `--azul-tinta` #2038A2 | `--hoja` #FBFAF7 | subrayados y enlaces | 9,36:1 | ✓ |
| `--rojo` #C21F17 | `--hoja` #FBFAF7 | pérdida, descuadre | 5,74:1 | ✓ |
| `--ambar` #A84F06 | `--hoja` #FBFAF7 | advertencia | 5,31:1 | ✓ |
| `--tinta` #141414 | `--hoja-2` #F7F5F0 | texto principal | 16,91:1 | ✓ |
| `--grafito` #3A3A38 | `--hoja-2` #F7F5F0 | texto secundario | 10,46:1 | ✓ |
| `--gris` #6B6A66 | `--hoja-2` #F7F5F0 | metadatos | 4,97:1 | ✓ |
| `--azul` #2347D6 | `--hoja-2` #F7F5F0 | acento, «Cuadra», enlaces | 6,55:1 | ✓ |
| `--azul-tinta` #2038A2 | `--hoja-2` #F7F5F0 | subrayados y enlaces | 8,97:1 | ✓ |
| `--rojo` #C21F17 | `--hoja-2` #F7F5F0 | pérdida, descuadre | 5,50:1 | ✓ |
| `--ambar` #A84F06 | `--hoja-2` #F7F5F0 | advertencia | 5,09:1 | ✓ |
| `--azul` #2347D6 | `--azul-suave` #E7ECFB | insignia azul | 6,04:1 | ✓ |
| `--azul-tinta` #2038A2 | `--azul-suave` #E7ECFB | insignia azul (tinta) | 8,28:1 | ✓ |
| `--rojo` #C21F17 | `--rojo-suave` #FBE9E7 | insignia/aviso rojo | 5,11:1 | ✓ |
| `--ambar` #A84F06 | `--ambar-suave` #FBF0E3 | insignia/aviso ámbar | 4,93:1 | ✓ |
| `--sobre-tinta` #F5F3EE | `--tinta` #141414 | texto en Expediente | 16,61:1 | ✓ |
| `--sobre-tinta-2` #A9A79F | `--tinta` #141414 | secundario en Expediente | 7,65:1 | ✓ |
| `--sobre-tinta` #F5F3EE | `--tinta-2` #1F1F1F | texto en Expediente (hover) | 14,86:1 | ✓ |
| `--blanco` #FFFFFF | `--azul` #2347D6 | botón principal | 7,13:1 | ✓ |
| `--blanco` #FFFFFF | `--azul-tinta` #2038A2 | botón principal (hover) | 9,77:1 | ✓ |
| `--blanco` #FFFFFF | `--rojo` #C21F17 | botón peligro | 6,00:1 | ✓ |
| `--blanco` #FFFFFF | `--rojo-cartel` #D7261E | relleno alerta crítica | 5,02:1 | ✓ |
| `--sobre-tinta` #F5F3EE | `--tinta` #141414 | botón sólido | 16,61:1 | ✓ |
| `--tinta` #141414 | `--rojo-cartel` #D7261E | texto oscuro sobre cartel — **prohibido**, por eso se usa blanco | 3,67:1 | ✓ solo texto grande |

## Notas

- **Verde no existe.** Positivo se marca con `--tinta` y ▲, o con `--azul`. El daltonismo rojo-verde no confunde «gana» con «pierde» porque además del color van el signo ▲/▼ y, en estados financieros, los paréntesis.
- `--linea` (`rgba(20,20,20,.09)`) y `--rejilla` (8 %) son decorativas: no separan controles por sí solas, así que no aplica el 3:1 de componentes. Los campos de formulario llevan además el material Hundido (sombra interior) para que su borde se perciba.
- `--rojo-cartel` es solo para rellenos con texto blanco grande; el texto rojo sobre papel usa `--rojo`.
- `--ambar` sobre `--ambar-suave` es el par más justo: se usa con texto ≥ 13 px y siempre con ícono.
