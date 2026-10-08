# Fase 1 · Fallos de la prueba ciega (corrección general)

Probado en la copia aislada. Los archivos nuevos del banco son genéricos (ningún dato real).

## B1 · Cuentas por pagar clasificadas como cartera
- En una lista con abonos o saldos, **el nombre de la hoja y el título del bloque pesan más que el rótulo de una columna**. Se agregaron «proveedores», «lo que debo» a las palabras de cuentas por pagar.
- Si la hoja o el título dicen una cosa y la columna de nombres otra («CUENTAS POR PAGAR» con columna «CLIENTE»), se respeta la hoja **y se pregunta**: «¿Es lo que le deben al cliente o lo que el cliente debe?», con la de la hoja como sugerida.
- La pregunta de terceros dice «compras» cuando la lista es de cuentas por pagar (antes decía «ventas» porque la lista quedaba mal clasificada).

## B2 · Fechas futuras movidas a otro año
- «Mismo día y mes del año anterior» **dejó de ser el valor por defecto**, y solo se ofrece si ese año ya aparece en el archivo: nunca se inventan periodos de un año que el archivo no menciona.
- Opción nueva y sugerida: **«Dejar fuera: todavía no ha ocurrido»**. Esas filas no entran al cálculo ni a la periodización, y queda un aviso.
- Si el título del bloque dice un mes y un año futuros, no se ofrece «cruzar día y mes» ni se arrastran las filas al mes del título: se sugiere dejarlas fuera.

## B3 · Demasiadas preguntas
- La misma pregunta en varios bloques se hace **una sola vez**: «En 11 bloques la forma de pago solo aparece en la primera fila. ¿Aplica a todas las filas de abajo?». Igual para fechas copiadas, fechas futuras y terceros desconocidos.
- El detalle es plegable («Ver los 11 bloques y responder alguno aparte»): cada bloque tiene su selector; la respuesta de un bloque manda sobre la del grupo.
- Medido en los 17 archivos con registros auxiliares del banco y el de la clienta de demostración: **ninguno pasa de 2 preguntas** (meta: 6).

## Pruebas
| Archivo nuevo | Qué reproduce | Cifras esperadas (a mano) |
|---|---|---|
| `19_cxp_con_columna_cliente.xlsx` | hoja «CUENTAS POR PAGAR» con columna «CLIENTE» | proveedores 300.000 − 100.000 + 150.000 = **350.000**; caja −200.000; ingresos 0 |
| `20_bloque_de_mes_futuro.xlsx` | «VENTAS NOVIEMBRE 2026» visto el 8-oct-2026 | solo septiembre: 150.000 − 40.000 = **110.000**; ningún periodo en 2025 ni en noviembre |
| `21_muchos_bloques_iguales.xlsx` | 11 bloques con la forma de pago solo arriba; 4 con una fecha copiada | 2 preguntas; 11 meses de **180.000**; respondiendo marzo aparte: febrero 280.000 y marzo 80.000 |

La prueba anterior que respondía «año anterior» al archivo 03 ahora comprueba que esa opción ya no aparece y que «dejar fuera» saca la fecha futura del cálculo.

| Comprobación | Resultado |
|---|---|
| Pruebas del backend | ✅ 260 (4 nuevas) |
| `tsc` · `lint:diseno` · `build` | ✅ · ✅ 0 · ✅ |
| Recorrido (`frontend/scripts/flujo-v23-preguntas.mjs`) | ✅ claro y oscuro, 1440 y 390 px: 2 preguntas, detalle plegable, respuesta por bloque registrada, sin errores ni desbordes |
