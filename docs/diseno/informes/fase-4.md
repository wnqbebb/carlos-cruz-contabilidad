# Fase 4 · Tablero — informe

Capturas: `capturas/fase-4/01-tablero*.png` · antes/después: `capturas/fase-4/comparar-01-tablero*.png`.

## Orden de lectura (spec 6.2)

1. **Título «Tablero»** en display + «1 cliente activo · último corte 31 de enero de 2025». Meta-encabezado con «Corte 31 ene 2025».
2. **Fila héroe**
   - Expediente tinta (7 columnas): «01 • Resultado», utilidad neta de toda la cartera del último mes en display-xl con odómetro, **exacta** ($ 2.666.661,49, ya no «$ 2,6 M»), ▲ como indicador. Debajo Ingresos · Gastos · Margen neto (24,2 %, división exacta con BigInt, sin floats). La flecha ↗ abre la ficha del cliente directo en «Estados financieros».
   - Hoja de ecuación (5 columnas): Activo = Pasivo + Patrimonio con las tres cifras, barras proporcionales que se nivelan como balanza (back.out 1.4, 0,6 s) e insignia **Cuadra** con brillo. La insignia sale del campo `cuadra` que calcula el backend; si no cuadra, muestra «Descuadre de $ …».
3. **Fila de estado**
   - Tira de 12 meses: cerrado (tinta), abierto (azul con borde), sin contabilizar (rayado tenue), en mora (rojo). Con los datos reales se ve el atraso de FANANT: 9 meses en rojo y 3 aún dentro de la tolerancia.
   - Nómina y seguridad social: SMMLV, auxilio, suma y jornada vigente **leídos de /api/parametros**. Antes estaban escritos a mano en el código. «Ajustar» con EnlaceSubrayado; la fuente legal se pliega.
4. **Cola de operaciones**: barra lateral por severidad, EsferaCliente, nombre, NIT, alerta y «Ver ficha ↗».
5. **Clientes recientes**: carrusel de Expedientes papel con esfera, último corte, estado y utilidad; flechas negras circulares (ref-03) y tarjeta «Abrir un expediente nuevo».

**Eliminado:** tarjeta azul «Salud contable 100 %» con curva sin ejes, bloque duplicado «Mes de ene 25», píldora índigo «Utilidad neta», burbuja «FA / FANANT» escrita a mano.

## Datos: sin endpoints nuevos
- Héroe: último mes de `serie` de `/api/tablero` (toda la cartera).
- Ecuación y carrusel: los 8 clientes activos más recientes (`/api/clientes`) y sus periodos (`/api/clientes/:id/periodos`). La ecuación indica de qué cliente y corte es.
- Tira: un mes es «en mora» solo si el backend reporta una alerta ATRASADO y el mes supera la tolerancia del backend (`MESES_SIN_TRABAJO["mensual"] = 2`). No se inventó otro criterio.
- Límite conocido, anotado en PROPUESTAS.md: con miles de clientes, el estado cerrado/abierto de un mes se lee de los 8 recientes y del total de periodos abiertos.

## Verificación

| Comprobación | Resultado |
|---|---|
| build · tsc · lint:diseno | ✅ · ✅ · ✅ 0 |
| Pruebas | ✅ 111 |
| Consola | ✅ sin errores |
| 390 px | ✅ sin desborde (la jornada desbordaba 1 px: corregido) |

## Lista

| Pregunta | Tablero |
|---|---|
| ¿Se lee primero lo más importante? | ✅ Resultado del mes en la carpeta negra, después si cuadra, después qué falta |
| ¿Algo fuera de tokens? | ✅ No |
| Referencias | ref-01 Expediente héroe y carrusel · ref-02 título display y cifra display-xl · ref-03 etiquetas 01–06, fila de métricas con pie diminuto, flechas circulares y carrusel con vecina · ref-04 esferas en cola y carrusel · ref-05 hojas y grano · ref-06 meta-encabezado e índices · ref-07 cristal del buscador · ref-08 rejilla y subrayados |
| ¿Cifras exactas, es-CO? | ✅ Todas; el margen se calcula con división exacta |
| ¿390 px? | ✅ |
| ¿Contraste AA? | ✅ |

## Ajustes de componentes hechos en esta fase
- Expediente: pestaña de al menos 170 px y etiqueta alineada al final real de la rampa (en tarjetas de 320 px se cortaba).
- ClienteFicha acepta `?vista=estados` para abrir directo esa pestaña.
- `formato.razon()`: cociente exacto con BigInt para razones de presentación.
