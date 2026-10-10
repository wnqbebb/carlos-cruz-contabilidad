# Informe del rescate · octubre de 2026

Todo lo que dice este informe tiene una prueba que se puede volver a correr. Las salidas de los comandos
están pegadas tal cual en la sección 5. Los datos de las pruebas, de la demostración y de las capturas
son **ficticios**: no se usó ninguna foto ni archivo real de clientes.

## 1. Prioridades del usuario y cómo quedaron

| Prioridad | Estado | Evidencia |
|---|---|---|
| **Todo gratis** | Vercel (Hobby) + Render (Free) + Supabase (Free) + GitHub Actions (repositorio público: sin costo). | `render.yaml` con `plan: free`; tarea `mantener-render-despierto.yml`. |
| **Aguanta 10.000 clientes** | Probado en Postgres 16 con 10.000 clientes × 3 periodos: nada falla y la base pesa **329 MB** (era 940 MB). | `backend/scripts/prueba_carga.py`, `docs/rescate/carga_10k.json`. Tabla en §3. |
| **Todo en la nube** | El código está listo y subido; **falta que usted cree el servicio en Render** (no hay conector para hacerlo desde aquí). | §6. |

## 2. Tabla H1–H8: antes, después y evidencia

| # | Antes (verificado al empezar) | Después | Evidencia |
|---|---|---|---|
| H1 | Render respondía `x-render-routing: no-server`; Vercel `/api/salud` daba 404. Además, **en Postgres la lista de clientes fallaba** (`'Comparator' object has no attribute 'any'`) y la clave de cifrado se habría perdido en cada reinicio de Render. | Postgres corregido y probado: toda la batería corre también contra Postgres. `render.yaml` genera `CLAVE_SESION` y `CC_CLAVE_DATOS`; lector aislado ajustado a los 512 MB de Render. **La nube sigue sin servicio hasta que usted lo cree.** | `CC_PRUEBAS_POSTGRES=… pytest` → ver §5. `curl` de §5. |
| H2 | `2 failed, 356 passed`. | `test_caso_c…`: el NIT provisional fallaba al azar (letras); ahora 12 dígitos «0000…» + etiqueta `documento_pendiente`. `test_lo_publico…`: se salta con aviso si falta `frontend/dist`. | §5 pytest. |
| H3 | `tsc`: 8 errores en `PanelEditarCliente.tsx`; socios con campos inexistentes. | Panel lateral con **toda** la ficha y los socios (mismos bloques que «Editar ficha»). `npm run build` corre `tsc --noEmit` primero. | `tsc` limpio; J4 en navegador. |
| H4 | El Excel completo existía pero no se había probado desde el navegador. | 15 hojas, incluidas «EF formato contador» y «Cuentas T», también desde un periodo guardado; el total del activo del archivo es el de la pantalla. | J6. |
| H5 | Con la foto, «incompleto» y el usuario no sabía qué hacer. | Caja **«Para terminar faltan N cosas»** arriba, un botón por cosa; confirmar filas con el **recorte de la foto** al lado y corregir antes de confirmar; las preguntas sugeridas se confirman con un toque. | J7. |
| H6 | No pedía ingresos y costos del negocio; «Su declaración» quedaba en 0. | **«Lo que solo usted sabe»**: se piden cuando hay CIIU de actividad, facturación electrónica o consignaciones muy por encima de lo reportado, con la comparación «Consignaciones 93,1 M · Facturación 4,8 M · Ingresos que usted declara: ___». Columnas «Lo que propondría la DIAN» / «Su declaración», cada diferencia explicada. PDF solo con casillas con valor + anexo. | J7: casillas = 210 presentado (29, 30, 74, 77, 111, 116, 132, 137). |
| H7 | No se podía editar nada. | **«Datos del periodo»** (editor tipo Excel): movimientos, saldos iniciales, inventario, nómina, activos fijos; agregar, duplicar, borrar, pegar desde Excel, PUC, validación en vivo, recálculo al dejar de escribir, «Deshacer», versiones; archivos del periodo (ver, quitar, volver a procesar); «Descargar datos para editar» y volver a subir al mismo periodo. Renta: cada casilla de dato con ajuste manual y nota obligatoria. | J5, J6, pruebas `test_datos_periodo.py`. |
| H8 | Matriz de `docs/v24/AUDITORIA.md` §2 sin comprobar en navegador. | Ver la tabla de §4. Restaurado: edición directa de sigla, municipio, honorarios y periodicidad en la cabecera. | J4. |

## 3. Escala: 10.000 clientes (Postgres 16 local, misma versión de esquema que Supabase)

| Pantalla | Respuesta | Tiempo (1.ª vez) |
|---|---|---|
| Lista de clientes (página 1) | 200 | 0,03 s |
| Lista ordenada por utilidad | 200 | 0,76 s |
| Buscar «panader» / por NIT | 200 | 0,01–0,07 s |
| Tablero del contador (todos los clientes contables) | 200 | 3,1 s la primera vez; 0,02 s después, desde memoria hasta el siguiente cambio |
| Cartera de renta | 200 | 0,09 s (la pantalla dibuja por tandas de 200) |
| Ficha / periodos de un cliente | 200 | < 0,02 s |
| Resultado de un periodo (rearmado desde la entrada) | 200 | 0,03 s |

**Peso de la base:** 940 MB → **329 MB** con 10.000 clientes × 3 periodos (≈ 11 KB por cliente-mes).
Cómo: cada periodo guarda su **entrada** comprimida (`periodo_entradas`) y su **libro diario** en un bloque
comprimido (`periodo_diarios`); del resultado solo se guarda el resumen y lo demás se rearma idéntico al abrirlo
(probado comparando el resultado completo).

**Lo que hay que saber (con honestidad):** Supabase gratis da 500 MB. Con el tamaño medido caben unos
**45.000 cliente-mes**: por ejemplo, 10.000 clientes con 4 meses, o unos 3.700 clientes con el año completo
mensual. Para 10.000 clientes con 12 meses cada uno se necesitan ≈ 1,3 GB: eso ya no cabe en ningún plan
gratuito de Supabase (el plan Pro, 25 USD/mes, trae 8 GB). Las fichas, la renta y la búsqueda de 10.000
personas sí caben de sobra.

## 4. Regresiones desde la v2.2 (matriz de `docs/v24/AUDITORIA.md` §2)

| Función | Hoy | Comprobado |
|---|---|---|
| Edición en la cabecera del cliente | Razón social, sigla, municipio, honorarios y periodicidad, ahí mismo (restaurado). | J4 (nombre y honorarios, tras recargar). |
| Panel lateral de edición | Toda la ficha y los socios. | J4. |
| Excel de un cálculo nuevo y de un periodo guardado | 15 hojas, con «EF formato contador» y «Cuentas T». | J6 (y `test_entrada.py`). |
| Hoja Cuentas T en el Excel | Sí. | J6. |
| Pantalla Trabajar | Integrada en el expediente; si no hay nada que decidir, calcula sin pasos extra. | J2. |
| Parámetros | En la aplicación (aceptado en la v2.3). | — |
| Gráficas del cliente | Las mismas de la v2.2 (`GraficaHistorico` + tabla) en Resumen; los indicadores, plegados. | Capturas `docs/rescate/diseno/expediente-resumen-*`. |
| Puerta de entrada en Renta | Soltar la exógena (foto, PDF o Excel) de cualquier persona. | J7, J8, J9. |

## 5. Salida real de las verificaciones

```
$ cd backend && python -m pytest -q                       (SQLite)
367 passed, 25 skipped, 1 warning in 86.68s (0:01:26)

$ CC_PRUEBAS_POSTGRES=postgresql://…/pruebas python -m pytest -q   (Postgres 16)
367 passed, 25 skipped, 77 warnings in 98.59s (0:01:38)

$ npx tsc --noEmit
(sin errores)

$ npm run build   (cola; ahora corre tsc primero)
✓ built in 9.28s

$ npm run lint:diseno
lint:diseno ✓  sin infracciones en src/ (56 archivos revisados)

$ npx playwright test
  ok  1 [acceso] › J1 · crear el acceso o ingresar y llegar al Tablero (4.8s)
  ok  2 [recorridos] › J2 · subir la plantilla del caso completo → resultado en pantalla (6.4s)
  ok  3 [recorridos] › J2 · subir las facturas electrónicas de la DIAN → ventas y compras organizadas solas (6.0s)
  ok  4 [recorridos] › J3 · cambiar de mes conserva la vista (6.9s)
  ok  5 [recorridos] › J4 · editar nombre, datos y socios, y comprobar tras recargar (5.4s)
  ok  6 [recorridos] › J5 · editar movimientos y saldos dentro de la aplicación (11.1s)
  ok  7 [recorridos] › J6 · Excel completo, PDF, libros y datos para editar (11.9s)
  ok  8 [recorridos] › J7 · renta de la Contribuyente A desde la foto hasta el ZIP (42.9s)
  ok  9 [recorridos] › J8 · tres fotos difíciles: sin cifras falsas y digitar lo esencial (1.0m)
  ok 10 [recorridos] › J9 · exógena de una persona nueva: borrador y fuera de los clientes contables (4.2s)
  10 passed (3.1m)

$ python backend/scripts/prueba_carga.py --solo-medir     (10.000 clientes × 3 periodos, Postgres 16)
{"base_mb": 329.2, … "clientes": 10000, "periodos": 30077}
Lista de clientes (página 1)             200    0.03 s  mediana   0.03 s
Lista ordenada por utilidad              200    0.76 s  mediana   0.76 s
Buscar «panader»                         200    0.03 s  mediana   0.01 s
Buscar por NIT                           200    0.01 s  mediana   0.01 s
Tablero del contador                     200    3.12 s  mediana   0.02 s
Cartera de renta 2025                    200    0.14 s  mediana   0.13 s
Ficha de un cliente                      200    0.01 s  mediana   0.01 s
Periodos de un cliente                   200    0.01 s  mediana   0.01 s
Resultado de un periodo (rearmado)       200    0.03 s  mediana   0.03 s

$ curl -si https://carloscruz-api.onrender.com/api/salud
HTTP/1.1 404 Not Found
x-render-routing: no-server
$ curl -si https://carlos-cruz-contabilidad.vercel.app/api/salud
HTTP/1.1 404 Not Found
```
La nube **todavía no funciona**: falta crear el servicio en Render (§6).

### Tiempos y clics de cada recorrido (navegador real, servidor local)
Los clics cuentan botones pulsados; escribir en un campo no cuenta.

| Recorrido | Tiempo | Clics |
|---|---|---|
| J1 Entrar | 4,7 s | 2 |
| J2 Subir contabilidad (caso completo) | 5,7 s | 2 |
| J2 Subir facturas DIAN | 5,6 s | 2 |
| J3 Navegar entre meses | 6,1 s | 2 |
| J4 Editar el cliente (nombre en < 10 s, honorarios, panel, socios, recarga) | 4,5 s | 5 |
| J5 Editar valores del periodo | 10,7 s | 8 |
| J6 Descargar (Excel, PDF, libros, datos para editar) | 16,5 s | 4 |
| J7 Renta con foto legible, hasta el ZIP | 41,8 s | 6 |
| J8 Renta con fotos difíciles | 60,7 s | 2 |
| J9 Renta de una persona nueva | 3,8 s | 0 (soltar el archivo) |

Capturas: `docs/rescate/capturas/` (recorridos) y `docs/rescate/diseno/` (claro y oscuro, 1440 y 390 px).

### Otras fallas encontradas y corregidas por el camino
- Lector aislado: avisaba «el lector se detuvo» con archivos buenos si el proceso terminaba justo entre dos
  revisiones (pasaba con el equipo ocupado; en la nube gratuita, a menudo).
- El cargador de demostración fallaba con 403 desde la v2.3 (no mandaba el token CSRF).
- El tablero solo miraba los primeros 5.000 clientes y contaba como «atrasados» a quienes solo vienen por la renta.
- «Digitar lo esencial» traía fijas cifras de un contribuyente real (saldo a favor y patrimonio anterior).
- Una exógena en Excel pedía «confirmar filas» aunque trae el dato exacto.
- `iniciar.bat` tenía una línea partida (`node frontend\scripts` + `ecesita-build.mjs`).
- Celular: el selector del mes quedaba de 30 px y sin texto.

## 6. Lo que falta y por qué

1. **Crear el servicio en Render** (depende de usted, ver los pasos en el mensaje final). Hasta que exista,
   `https://carlos-cruz-contabilidad.vercel.app/api/salud` responde 404 y **la nube no funciona**. En cuanto
   exista, corro J1–J9 contra la dirección de Vercel.
2. Plan gratuito de Render: 512 MB de RAM y el servidor duerme a los 15 minutos. La tarea de GitHub lo
   mantiene despierto de 6 a. m. a 10 p. m.; fuera de ese horario la primera visita tarda 30–60 s
   («Despertando el servidor…»). Opción de pago: Render Starter, 7 USD/mes, nunca duerme.
3. La imagen de Docker no se pudo construir en este equipo (no hay Docker); se construye en Render.
4. Las pruebas que usaban fotos y archivos reales (25) siguen saltándose con aviso: se reemplazaron por
   recorridos y pruebas con datos ficticios, pero esas 25 no se borraron (por la regla «no quitar sin preguntar»).
