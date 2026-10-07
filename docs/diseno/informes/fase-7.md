# Fase 7 · Parámetros y estados transversales — informe

Capturas: `capturas/fase-7/04-parametros*.png`, `06-catalogo*.png` y `detalle/` (estados, aviso, error).

## Parámetros (spec 6.6)
- Años como **Interruptor** (2025⁰¹ · 2026⁰²) sobre los valores vigentes: SMMLV, auxilio, suma y jornada en cifras exactas.
- Formulario con campos Hundidos y **máscara de miles en vivo** (escribe 1750905, ve 1.750.905) y vista previa «SMMLV + auxilio = $ 2.000.000».
- **Jornada por tramos en filas** [fecha] [horas] [quitar] + «Agregar tramo», en vez del texto crudo `2026-01-01=44; …`.
- **Contrato sin cambios, verificado:** en la instancia de prueba se guardó 2026 y la petición fue `{"smmlv":"1750905","aux_transporte":"249095","jornada_tramos":[{"desde":"2026-01-01","horas_semana":44},…]}`, idéntica a la de antes; los datos leídos después quedaron iguales.
- **Sistema**: almacenamiento, estado, motor, **ID del proyecto de Supabase**, sesiones abiertas, versión y último error de conexión. Es el único lugar donde aparece (el lint lo impide en cualquier otro).

## Estados transversales (spec 6.7)
| Estado | Cómo quedó |
|---|---|
| Cargando | Esqueletos con la forma real: Tablero (carpeta héroe, ecuación, tira de 12 meses), rejilla de Expedientes, ficha (cabecera + esfera + pestañas). Latido de opacidad, sin degradados. El `Cargando` genérico también es ya un esqueleto, no un spinner |
| Vacío | Carpeta azul de ref-08 + frase + acción (Clientes, Trabajar, ficha inexistente, informes sin datos) |
| Error | Hoja con borde rojo, mensaje humano, **detalle técnico plegable** y «Reintentar» (Tablero, Clientes, ficha, Parámetros) |
| No existe | Una ficha que no existe ya no dice «puede ser la conexión»: dice «Ese expediente no existe» y lleva al directorio |
| Sin conexión | Banda ámbar del Marco (Fase 3) |
| Avisos | «Tira de papel» que entra desde abajo a la derecha (GSAP), con borde de tinta, rojo o ámbar; se usa al guardar parámetros y al guardar el cierre del periodo |

## Verificación
| Comprobación | Resultado |
|---|---|
| build · tsc · lint | ✅ · ✅ · ✅ 0 |
| Pruebas | ✅ 111 |
| Guardado de parámetros (instancia de prueba) | ✅ mismo contrato, datos idénticos, aviso visible |
| 390 px | ✅ |

## Lista
| | Parámetros | Estados |
|---|---|---|
| ¿Lo importante primero? | ✅ valores vigentes del año, luego editar, luego sistema | ✅ el mensaje humano antes que el detalle técnico |
| ¿Fuera de tokens? | ✅ No | ✅ No |
| Referencias | ref-06 interruptor de años · ref-05 Hundido · ref-03 etiquetas | ref-08 carpeta del vacío · ref-05 papel de la tira |
| ¿Cifras exactas? | ✅ máscara sin floats; suma con `sumar` | — |
| ¿390 px? | ✅ | ✅ |
| ¿AA? | ✅ | ✅ |
