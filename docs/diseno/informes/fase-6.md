# Fase 6 · Trabajar — informe

Capturas del recorrido completo: `capturas/fase-6/t01…t07*.png` (escritorio y móvil), `t07-impresion.png` y `t07-impresion.pdf` (carta).

**Cómo se probó sin riesgo:** calcular guarda el periodo en el expediente, y en la Fase 5 se vio que puede sobrescribir uno cerrado. Por eso el recorrido se hizo contra una **segunda instancia en el puerto 8001 con SQLite desechable** y un cliente de prueba. El script `scripts/flujo-trabajo.mjs` se niega a correr contra `:8000`. La base real no se tocó.

## Qué se hizo

| Paso | Detalle |
|---|---|
| Paso a paso | 01 Cliente · 02 Subir · 03 Mapeo · 04 Balance de prueba · 05 Ajustes · 06 Definitivo · 07 Estados, pegajoso, de cristal. Actual en tinta, hechos con ✓, futuros en gris y deshabilitados hasta tener datos. Los pasos 04–07 abren la pestaña correspondiente del resultado: el flujo y las llamadas al servidor son los de siempre |
| 01 Cliente | Buscador grande Hundido + rejilla de Expedientes con esfera |
| 02 Subir | Zona Hundida de 280 px con borde discontinuo; al arrastrar, borde azul + brillo + «Suelta para leer»; chips `.xlsx .xls .csv .pdf`; los 3 ejemplos con «Cargar» y «Descargar Excel» |
| Procesando | Cuenta T que se traza en bucle + etapas que se marcan. **Honesto:** la subida muestra lectura, formato y mapeo; el cálculo muestra mayor, partida doble y estados. La última etapa no se marca hasta que responde el servidor |
| 03 Mapeo | Semáforo sin verde: tinta ✓ exacto · ámbar por confirmar · rojo sin mapear. Barra «Calcular todo» de cristal que ya no tapa la navegación móvil |
| 04–06 Informes | `Reporte` rehecho con el lenguaje de TablaContable: cabeceras D/H agrupadas («Saldo inicial · Movimiento · Saldo final»), código en mono, sangría por nivel, totales con doble línea, densidad cómoda/compacta, negativos entre paréntesis, punto rojo de saldo contrario (dato del backend: `cuentas_t[].contraria`) |
| 07 Estados | Cada estado es un **documento carta sobre hoja**: razón social, NIT, nombre del estado, corte, «cifras en pesos colombianos», cuerpo y firmas del representante legal (C.C.) y del contador (T.P.). Barra flotante de cristal: Excel · PDF · Imprimir · anterior/siguiente |
| Impresión | Imprime **solo el documento** en carta, sin menú, barras ni lienzo; encabezado de tabla repetido en cada página |

## Corregido durante la revisión
- El paso «04 Balance de prueba» no respondía desde el resumen.
- Depreciación acumulada salía en rojo en el balance: es cuenta correctora, no pérdida. En los documentos el rojo queda solo para resultados negativos; los paréntesis siempre.
- La impresión salía en blanco (un contenedor con `overflow: hidden` recortaba el documento).
- «Errors (0)» → «Errores (0)»; «Paso 2 de 3» → «03 • Mapeo».
- «Nuevo periodo» se oculta dentro de Trabajar: ya está ahí y sería un segundo azul.

## Verificación
| Comprobación | Resultado |
|---|---|
| build · tsc · lint | ✅ · ✅ · ✅ 0 |
| Pruebas | ✅ 111 |
| Recorrido completo (escritorio y 390 px) | ✅ sin errores de consola, sin desbordes en ningún paso |
| Impresión | ✅ verificada como imagen y como PDF carta |

## Lista
| Pregunta | Trabajar |
|---|---|
| ¿Lo importante primero? | ✅ Siempre se ve en qué paso va; en 07 el documento ocupa el centro |
| ¿Fuera de tokens? | ✅ No |
| Referencias | ref-01 Expedientes en 01 · ref-03 botones píldora y etiquetas · ref-05 Hundido en zona de arrastre y campos · ref-06 índices 01–07 · ref-07 cristal en paso a paso, barra de documento y procesando (con contenido detrás) · ref-08 subrayados |
| ¿Cifras exactas? | ✅ es-CO, tabulares, paréntesis en estados |
| ¿390 px? | ✅ medido en cada paso |
| ¿AA? | ✅ |
