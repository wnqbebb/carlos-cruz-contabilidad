# Fase 5 · Clientes y ficha del cliente — informe

Capturas: `capturas/fase-5/02-clientes*.png`, `05-ficha*.png`, detalle de cada pestaña en `capturas/fase-5/detalle/`.

## ⚠ Hallazgo urgente (no es de diseño)
A las 18:12 alguien usó la app desde un navegador: subió un archivo para FANANT en «Trabajar» y calculó. El archivo traía **0 cuentas** y el resultado **reemplazó el periodo de enero 2025, que estaba cerrado**. Hoy la ficha muestra $ 0 y el backend alerta «patrimonio por debajo de la mitad del capital». El registro del servidor confirma que las escrituras no vinieron de mis scripts (solo hacen lecturas).
Causa en el código: `guardar_resultado` no protege periodos cerrados ni rechaza cálculos vacíos. Es lógica de negocio: **no la toqué**. Propuesta detallada en `PROPUESTAS.md` (punto 5).

## Clientes (spec 6.3)
- Título display + «N expedientes». Acciones: «Importar Excel» (fantasma) y «Nuevo cliente» (primario de tinta; el azul de la vista es «Nuevo periodo» arriba).
- Interruptor **Expedientes⁰¹ | Tabla⁰²** (se recuerda en este navegador) y filtro **Activos⁰¹ Inactivos⁰² Archivados⁰³ Todos⁰⁴** como interruptor.
- Búsqueda en campo Hundido; orden con **desplegable propio** de cristal (teclado completo) y botón de sentido.
- Expedientes: carpeta papel con esfera, razón social, NIT mono, municipio, periodicidad, honorarios exactos, fecha, estado y etiquetas. Hover: pestaña sube, giro −0,6°, flecha avanza.
- Tabla: encabezado meta pegajoso, esfera de 32 px, cifras tabulares a la derecha, sin cebra.
- Vacío: carpeta azul de ref-08 + «Aún no hay expedientes» + «Crear el primer cliente».

## Ficha (spec 6.4)
- Cabecera Escaparate: metadatos en las cuatro esquinas como ref-04 (`FANANT — 828`, `TURNO DIAN — 08`, `FICHA DESDE 06 — 10 — 2026`, `PERIODICIDAD — MENSUAL`), razón social en display, sigla, NIT, municipio, representante legal, contador con T.P., esfera de 240 px que deriva.
- Pestañas con índice y raya deslizante (Flip): Resumen⁰¹ Periodos⁰² Estados financieros⁰³ Inventario⁰⁴ Nómina⁰⁵ Socios⁰⁶ + **Libro diario⁰⁷ y Datos⁰⁸**, que ya existían y no se quitaron (quitar funciones no está permitido).
- Inventario y Nómina reutilizan los informes guardados del periodo, sin datos nuevos; si el periodo no los trae, lo dice.
- Socios pasó de «Datos» a su propia pestaña.

## Corregido de paso
- **Aritmética con floats** en el panel del periodo: el aviso de descuadre sumaba pasivo + patrimonio con `Number`, y razón corriente, endeudamiento y margen se dividían con floats. Ahora `sumar` y `razon` exactos; `Number` queda solo para dibujar medidores.
- Cuatro insignias «Cuadra» en azul sólido rompían «un solo azul sólido por vista»: variante discreta.
- Primitivas de `componentes/ui.tsx` (Tarjeta, Pestañas, Tabla, Aviso, Diálogo de cristal, campos Hundidos, Vacío con carpeta) rehechas con el sistema: todas las pantallas que aún las usan ya se ven coherentes.
- `lint:diseno` ahora detecta `border-t-…`, `divide-x-…`, `ring-offset-…` (se colaba `border-t-indigo-600`).

## Verificación
| Comprobación | Resultado |
|---|---|
| build · tsc · lint | ✅ · ✅ · ✅ 0 |
| Pruebas | ✅ 111 |
| Consola (4 pestañas recorridas) | ✅ sin errores |
| 390 px | ✅ |

## Lista
| | Clientes | Ficha |
|---|---|---|
| ¿Lo importante primero? | ✅ título y conteo, luego carpetas | ✅ quién es el cliente, luego cifras del último periodo |
| ¿Fuera de tokens? | ✅ No | ✅ No |
| Referencias | ref-01 carpetas · ref-03 botones píldora · ref-04 esferas · ref-06 interruptores · ref-07 desplegable de cristal · ref-08 carpeta azul del vacío | ref-02 razón social display · ref-04 esfera 240 y metadatos de esquina · ref-06 pestañas con índice |
| ¿Cifras exactas? | ✅ | ✅ (y corregidos los floats) |
| ¿390 px? | ✅ | ✅ |
| ¿AA? | ✅ | ✅ |
