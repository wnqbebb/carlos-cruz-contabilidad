# Propuestas

Cosas que aparecieron trabajando en la v2.2 y que **no están en el encargo**, así
que no se implementaron. Cada una dice qué pasa hoy, qué se propone y qué costaría.
Nada de esto se toca sin que usted lo autorice.

---

## P01 · Un libro diario suelto en CSV todavía no se reconoce — ✅ HECHO en la Fase 4 (`importadores/libro_diario.py`)
**Hoy:** un archivo con las columnas `Fecha · Cuenta · Débito · Crédito` y nada más
—el volcado típico de un programa contable— cae en «No reconocí lo que trae».
La Fase 4 enseña a leer registros auxiliares (ventas, compras, cartera), que es
otra cosa: esto es partida doble ya hecha.

**Se propone:** un detector más para ese formato, con el mismo criterio general
que los demás (se reconoce por las columnas, no por el nombre del archivo).

**Costo:** un archivo nuevo en `backend/app/importadores/`, parecido a
`hoja_trabajo.py`, más sus pruebas. Media jornada.

---

## P02 · Quedan dos caminos de subida en el backend
**Hoy:** `/api/subir` (la puerta única) y `/api/importar` (el camino antiguo, que
usan el paso «Subir» de Trabajar y los ejemplos). El segundo ya no se puede
alcanzar equivocándose de pantalla, pero sigue ahí.

**Se propone:** dejar `/api/importar` solo para los ejemplos y que todo lo demás
pase por `/api/subir`, o fundirlos. Reduce a la mitad lo que hay que mantener.

**Costo:** poco código, pero toca el flujo de trabajo entero; conviene hacerlo
cuando las fases que lo usan estén cerradas, no antes.

---

## P03 · El paquete de JavaScript pesa 578 kB
**Hoy:** `npm run build` avisa de que el archivo pasa de 500 kB. Carga bien, pero
en una conexión lenta la primera visita se nota.

**Se propone:** separar GSAP y las pantallas grandes (Resultados, Ficha) en
trozos que se carguen cuando hagan falta.

**Costo:** una tarde, y hay que volver a medir las animaciones de entrada.

---

## P04 · El nombre sacado del archivo puede ser un apodo
**Hoy:** si los archivos no traen identidad, se propone el nombre del archivo sin
las palabras de relleno («CONTABILIDAD_TIENDA_JUAN_PEREZ_2026.xlsx» → «TIENDA
JUAN PEREZ»). Va rotulado como **sugerido** y el contador lo confirma.

**Se propone:** comparar esa sugerencia contra el directorio antes de mostrarla,
para proponer directamente el cliente que ya existe en vez de un nombre a medias.
Hoy la comparación solo se hace con el nombre encontrado dentro del archivo.

**Costo:** pequeño; es ampliar la búsqueda por parecido que ya existe.
