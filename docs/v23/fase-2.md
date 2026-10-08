# Fase 2 · Quitar Parámetros al 100 %

- **Fuera:** la pantalla `Parametros.tsx`, su ruta (ahora `/parametros` redirige al Tablero), su entrada en la navegación y en el buscador, el enlace del catálogo de diseño, los textos que la mencionaban («…en la pantalla de parámetros», «…desde Parámetros › Sistema»), `GET/PUT /api/parametros`, `PUT /api/contador` y la tabla como fuente de verdad (`repositorio/parametros.py` borrado).
- **Los valores legales viven en la aplicación**, en `data/parametros_legales.json`, con su fuente por año. Se agregó la UVT:

| Año | SMMLV | Auxilio | UVT | Fuente |
|---|---|---|---|---|
| 2025 | 1.423.500 | 200.000 | 49.799 | Decretos 1572 y 1573 de 2024 · Resolución DIAN 000193 de 2024 |
| 2026 | 1.750.905 | 249.095 | 52.374 | Decretos 1469 y 1470 de 2025 · Resolución DIAN 000238 de 2025 |

- **Año sin valores** (p. ej. 2027): no se inventa nada. El Tablero muestra la tarea crítica «Faltan los valores legales de 2027» y la nómina de ese año se bloquea con «Faltan los valores legales de 2027… la aplicación no inventa estos valores». Cómo agregar un año: `docs/MANTENIMIENTO.md`.
- **Panel «Sistema»** en el menú de la cuenta (CC): «En la nube · conectado» / «En este equipo · funcionando» / «Sin conexión», la versión y «Eliminar clientes de demostración». Cambiar contraseña, verificación en dos pasos y sesiones abiertas llegan con la Fase 6. Nada técnico: el panel lee `GET /api/sistema`, que solo devuelve `{conectado, en_la_nube, version}`.
- **`/api/salud` sin sesión** responde solo `{ok, version}` (adelantado de la 6.1).
- Una ruta de la API que no existe responde 404 (antes devolvía la página de la aplicación con 200). La página sin interfaz compilada ya no muestra comandos.
- Se quitó la sugerencia informativa «Turno N en el calendario tributario», que mandaba a la pantalla de parámetros (el vencimiento de renta llega con la Fase 5).

| Comprobación | Resultado |
|---|---|
| Pruebas del backend | ✅ 267 (`tests/test_parametros_legales.py`: ruta inexistente, valores 2025 y 2026 con fuente, nómina de cada año, 2027 sin valores con mensaje claro, tarea del Tablero, `/api/salud` mínimo, panel Sistema sin datos técnicos) |
| `tsc` · `lint:diseno` · `build` | ✅ · ✅ 0 · ✅ |
| Recorrido (`frontend/scripts/flujo-v23-sistema.mjs`) | ✅ claro y oscuro, 1440 y 390 px: `/parametros` → Tablero, ninguna «Parámetros» en pantalla, panel Sistema sin nada técnico, sin errores |
