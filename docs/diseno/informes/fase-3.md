# Fase 3 · Marca y estructura — informe

## Qué se hizo

| Pieza | Detalle |
|---|---|
| Monograma | «CC» en Geist 600 convertido a contornos + cuenta T mínima. Mismos contornos en la app y en el favicon. `componentes/Marca.tsx` |
| Favicon | `public/favicon.svg`, verificado a 16, 32 y 64 px (`detalle/favicon.png`) |
| Logotipo | Monograma + «Carlos Cruz» + `CONTADOR PÚBLICO · T.P. 103028-T` (`detalle/logo.png`) |
| `MARCA.md` | Geometría, área de protección, tamaños mínimos, usos correctos e incorrectos, voz |
| Barra lateral | Sobre el papel, 248 px, borde `--linea`. Navegación Tablero⁰¹ Clientes⁰² Trabajar⁰³ Parámetros⁰⁴; la píldora de tinta se desliza con Flip (medido: 111 → 255 px en ~0,3 s) |
| Sincronización | «Sincronizado · hace un momento / hace N min», comprobado cada minuto. Sin ID de Supabase ni nombres técnicos |
| Barra superior | Buscador de cristal + «Nuevo periodo» (BotonAcento) + avatar «CC». Se quitó el nombre repetido y el título «Panel de control» |
| MetaEncabezado | En todas las pantallas: `CARLOS CRUZ — CONTADOR PÚBLICO · T.P. 103028-T · ÍNDICE 0N — SECCIÓN · fecha`. La cuarta columna la puede fijar cada página (`useMetaPagina`) |
| Paleta ⌘K | Cristal sobre velo; fila activa en tinta (antes: texto tinta sobre azul sólido, contraste insuficiente) |
| Móvil | Barra inferior de cristal con cuatro íconos y etiqueta, píldora deslizante; monograma arriba; «Nuevo periodo» se oculta (está en «Trabajar») |

## Defectos de base encontrados y corregidos
1. **El cristal nunca desenfocaba**, en ninguna pantalla: el minificador de CSS fusionaba `backdrop-filter` con su versión `-webkit-` y Edge/Chrome se quedaban sin efecto. Ahora el valor viaja en `--cristal-filtro`.
2. **Las clases propias le ganaban a Tailwind**: `.material-cristal` anulaba `fixed` (desborde de 12 px en móvil). Todo lo propio está ahora en `@layer components` y el foco global en `@layer base`.
3. **Flip del Interruptor**: se añadió `data-flip-id` para emparejar el indicador viejo con el nuevo (verificado fotograma a fotograma).
4. Favicon inválido por un `--` dentro de un comentario XML.

## Verificación

| Comprobación | Resultado |
|---|---|
| `npm run build` · `tsc` · `lint:diseno` | ✅ · ✅ · ✅ 0 |
| Pruebas | ✅ 111 |
| Consola al navegar | ✅ sin errores |
| 390 px | ✅ sin desborde en las 6 rutas |

## Lista (estructura común a todas las pantallas)

| Pregunta | |
|---|---|
| ¿Se lee primero lo más importante? | ✅ La barra ya no compite con el contenido: sin tarjeta flotante, sin nombre duplicado. El contenido de cada pantalla se ordena en las fases 4–7 |
| ¿Algo fuera de tokens? | ✅ No (lint) |
| Referencias | ref-06 índices en superíndice y meta-encabezado de cuatro columnas · ref-07 cristal en buscador, paleta y barra móvil (ahora sí con algo detrás) · ref-08 rejilla con línea horizontal bajo el meta-encabezado · ref-02 lema con punto final |
| ¿Cifras exactas? | ✅ (sin cambios respecto a la Fase 1) |
| ¿390 px? | ✅ |
| ¿Contraste AA? | ✅ Corregida la fila activa de la paleta |

Antes/después: `capturas/fase-3/comparar-*.png`.
