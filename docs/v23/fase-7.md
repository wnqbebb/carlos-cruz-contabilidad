# v2.3 · Fase 7 — Verificación final, repositorio y despliegue local

## 1. Revisión completa (Playwright, copia aislada)

`frontend/scripts/revision-final.mjs`, puesto al día para la v2.3. Recorre Tablero, Clientes, Renta⁰³, las cinco
secciones del expediente de los 22 clientes de la copia, las 14 vistas contables y los redireccionamientos de
`/trabajo` y `/parametros`. Lo hace en claro y oscuro, a 1440 y 390 px.

| Paso | Resultado |
|---|---|
| Pantallas | **708 vistas** (177 × 4), sin errores de consola, sin desbordes, modo correcto. La más lenta tardó 2,1 s |
| Botones | **620 pulsados**, todos hacen algo. No se pulsan los que borran, cierran o guardan, porque los prueban los recorridos de cada fase |
| Descargas | **105 de 105** responden con un archivo de verdad: PDF y Excel de cada periodo, libros oficiales y borradores de renta |

Para este recorrido la copia aislada sube el límite de solicitudes (`CC_LIMITE_GENERAL`): el script recarga la
página por cada botón y supera las 600 por minuto de un uso normal.

### Lo que encontró la revisión, y se corrigió

- **El servidor se congelaba unos 30 s de vez en cuando (0,3 % de las cargas).** La sonda
  `scripts/sonda-lentas.mjs --pyspy` lo atrapó: el bucle del servidor esperaba a que terminara de escribir un
  registro.
  - En Windows, eso pasa cuando alguien selecciona texto en la ventana de `iniciar.bat`, o cuando el antivirus
    revisa el archivo.
  - Ahora los registros se escriben desde un hilo aparte. Las rutas de subida (OCR, Excel) pasan a hilos y la
    sesión se lee en un hilo.
  - Después de la corrección: 0 esperas en 708 cargas. Hay pruebas en `test_seguridad.py`.
- **Secretos en el espacio equivocado.** Una instancia de prueba sin `CC_ENV` leyó `backend/.env` y movió sus
  secretos al espacio del almacén de esa instancia. Para que no vuelva a pasar:
  - el espacio del almacén va ahora atado al archivo de configuración;
  - con `CC_ENV` solo se lee ese archivo.
  - Ver «Pendiente», abajo.
- **TOTP con la base copiada a otro equipo** daba error 500. Ahora ese ingreso pide un código de recuperación.
- **Versiones de periodos:** había una petición por periodo (21 a la vez en un cliente). Ahora el listado trae el
  número de versiones y la lista se pide al abrir el historial.
- Los filtros de Alertas no tenían `aria-pressed`.
- El filtro de registros enmascaraba como cédula la fecha del nombre del respaldo. Ahora se llama
  `respaldo-AAAA-MM-DD_HHhMMmSSs.ccr`.
- `docs/GUIA_CREDENCIALES.md` tenía una contraseña con apariencia de real y la referencia del proyecto. Ahora
  tiene marcadores, y la regla de gitleaks toma la contraseña como secreto.

## 2. Cifras

| Caso | Resultado |
|---|---|
| FANANT enero 2025 | `test_fanant.py`: 19 de 19, cifras intactas |
| Renta, caso A (foto real) | casillas del 210 **iguales** a la declaración presentada. **16 s y 9 clics** de soltar la foto al borrador |
| Renta, caso B (3 fotos difíciles) | debe declarar por 4 motivos y paga $130.000, con un ahorro de $6.275.000 frente a la propuesta de la DIAN. **42 s y 3 clics**. El OCR leyó 50 filas, el 46 % con confianza alta en el valor |

## 3. Pruebas y revisión de seguridad

| Revisión | Resultado |
|---|---|
| `pytest` | **344 en verde** |
| `tsc`, `lint:diseno`, `npm run build` | limpios |
| `scripts\seguridad.bat` | **todo en verde**: pip-audit (lock con hashes), npm audit, bandit, semgrep, gitleaks sobre **todo el historial** y 50 pruebas de seguridad |

## 4. Ejecutable

Se reconstruyó con `empaquetar/carloscruz.spec`: 576 MB, con el lector de fotos dentro, sin consola y con ícono
en la bandeja. Se probó con un perfil de Windows vacío:
1. primer uso;
2. «Crear su acceso»;
3. 10 códigos de recuperación;
4. cambio de contraseña;
5. recuperación con un código;
6. ingreso.

Todo correcto y sin errores. En `Documentos\Carlos Cruz` quedan solo la base, la configuración sin secretos, el
registro (sin datos sensibles) y la primera copia cifrada, con su restauración de prueba correcta. `LEAME.txt`
está escrito para la v2.3.

## 5. Repositorio

- **Respaldo completo** (`git clone --mirror`) en `privado/respaldo-repo/`, antes de cualquier cambio.
- **Historial limpio, en este equipo.** Se usó `git filter-repo`; el detalle está en `docs/PRIVADO.md`.
  - El árbol actual quedó idéntico.
  - El repositorio pasó de 139 MB a 8,6 MB.
  - gitleaks sobre todo el historial: sin hallazgos.
  - Cero apariciones de las cédulas y el NIT reales.
- **Visibilidad:** el repositorio de GitHub sigue **público**.
  - `gh` no está instalado en este equipo, así que no se pudo cambiar desde aquí.
  - Por eso **no se hizo `push --force` ni `push`**: el historial limpio espera a que el repositorio sea privado.
  - Los pasos están en el mensaje de entrega.

## 6. Pendiente

- **La aplicación real (puerto 8000) sigue con la v2.2**, y no se reinició. El 8 de octubre a las 20:59, una
  instancia de prueba movió `DATABASE_URL` y `SUPABASE_SERVICE_KEY` de `backend/.env` a otro espacio del
  Administrador de credenciales (`…@CarlosCruz-5855756e29e5`).
  - Así, al reiniciar, la aplicación no encontraría la conexión y abriría la base local sin avisar.
  - El proceso abierto los tiene en memoria y sigue funcionando.
  - Para arreglarlo: volver a escribir esas dos líneas en `backend/.env` (desde el panel de Supabase, o
    copiándolas de esas entradas del Administrador de credenciales) y ejecutar `iniciar.bat`. Al abrir, la v2.3
    las guarda en el espacio correcto y las borra del archivo.
- OWASP ZAP: no se corrió porque este equipo no tiene Docker.
- El Administrador de credenciales guarda entradas `CarlosCruz-…` de las copias de prueba. Se pueden borrar.
