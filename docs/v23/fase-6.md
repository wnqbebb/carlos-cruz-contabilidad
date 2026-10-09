# v2.3 · Fase 6 — Seguridad de nivel profesional

El modelo de amenazas, los 35 controles con su relación con OWASP ASVS nivel 2 y la política de retención están en
[`docs/SEGURIDAD.md`](../SEGURIDAD.md). Aquí va lo que se hizo, cómo se comprobó y lo que queda pendiente.

## Lo que ve el usuario

- **Ingreso sin nada técnico.** Desapareció «`python backend/crear_usuario.py`». La primera vez, y solo desde el mismo
  equipo, aparece **«Crear su acceso»**: usuario, contraseña con medidor de fortaleza y **10 códigos de recuperación**
  que se muestran una sola vez (descargar .txt o imprimir). En la base queda solo el hash de cada código.
- **«¿Olvidó la contraseña?»** pide un código de recuperación y deja poner una nueva; cierra todas las sesiones.
- **Sistema › Acceso seguro:** cambiar la contraseña, activar la verificación en dos pasos con un código QR, generar
  códigos nuevos, cerrar las demás sesiones y un aviso si hubo intentos fallidos en las últimas 24 horas.
- **Reautenticación:** eliminar un cliente, eliminar los de demostración, restaurar una versión, cambiar la
  contraseña, desactivar la verificación en dos pasos y «Descargar todo» piden la contraseña otra vez (vale 5 min).
- **Errores:** un mensaje humano y un código `INC-XXXX`. Se quitó el «Detalle técnico» visible.
- **Cédulas enmascaradas** en las listas de Clientes y Renta.
- **Ejecutable:** sin ventana negra, ícono en la bandeja (Abrir · Cerrar), nada por consola.

## Lo que cambió por dentro

| Área | Dónde |
|---|---|
| Argon2id, política de contraseñas, migración de bcrypt | `seguridad/claves.py`, `seguridad/cuentas.py` |
| TOTP (pyotp + QR con segno), secreto cifrado | `seguridad/cuentas.py`, `api/acceso.py` |
| Sesiones en el servidor (`sesiones_acceso`), rotación, 30 min / 12 h, cerrar todas | `sesion.py` |
| Host permitido, límite de solicitudes, CSRF (Origin/Referer + `X-CSRF`), encabezados, CSP | `seguridad/http.py` |
| Códigos de incidente, filtro de registros (contraseñas, cookies, cadenas de conexión, cédulas/NIT) | `seguridad/incidentes.py` |
| Secretos en el Administrador de credenciales (keyring/DPAPI), migración desde `.env` | `seguridad/secretos.py`, `config.py` |
| AES-256-GCM para subidas y copias | `seguridad/cifrado.py`, `repositorio/subidas.py` |
| Tipo por contenido, bombas ZIP, XXE, imágenes, PDF, macros, inyección de fórmulas | `seguridad/archivos.py` |
| Lectura en un proceso aparte con tiempo y memoria limitados | `seguridad/aislado.py` |
| Copia diaria cifrada, 30 días, restauración de prueba | `seguridad/respaldo.py` |
| Rol de mínimo privilegio y SSL `verify-full` con la CA de Supabase | `supabase/migraciones/006_acceso.sql`, `007_rol_app.sql`, `config.py` |
| `/docs`, `/redoc` y `/openapi.json` → 404 (solo con `CC_DOCS=1`) | `main.py` |
| Script inline de `index.html` movido a `public/tema-inicial.js` (CSP sin `unsafe-inline` en scripts) | `frontend/` |

## Cadena de suministro

- `backend/requirements.lock` con hashes (generado con `uv pip compile --generate-hashes`; `pip-compile` se colgó
  más de 30 min). `iniciar.bat` instala con `--require-hashes`; el frontend con `npm ci`.
- Se actualizó vite a 6.4 y react-router a 7.18 para cerrar vulnerabilidades altas de `npm audit`.
- `scripts/seguridad.bat` y `.github/workflows/seguridad.yml`: pip-audit, npm audit, bandit, semgrep, gitleaks y las
  pruebas de seguridad. Dependabot en `.github/dependabot.yml`.
- `.githooks/pre-commit`: bloquea `privado/` y corre `gitleaks protect --staged` con `.gitleaks.toml` (reglas para
  cadenas de conexión, cédulas, NIT y clave de sesión). `iniciar.bat` activa el hook.
- `.gitattributes`: los `.bat` siempre con CRLF.

## Resultados

| Revisión | Resultado |
|---|---|
| Pruebas backend (`pytest`) | **339 en verde**, de ellas 33 en `test_seguridad.py` y 13 en `test_sesion.py` |
| `pip-audit` (lock con hashes) | sin vulnerabilidades conocidas |
| `npm audit` | 0 vulnerabilidades |
| `bandit -c backend/bandit.yaml` | 0 hallazgos |
| `semgrep` (`p/python`, `p/secrets`) | 0 hallazgos. Se revisaron 4 y eran falsos positivos, ahora anotados: un `ALTER TABLE` con nombres del esquema propio y tres registros que solo escriben *nombres* de secretos, nunca valores |
| `tsc`, `lint:diseno`, `npm run build` | limpios |
| Playwright (claro/oscuro, 1440/390) | expediente, trabajo, sistema, preguntas, renta, capturas y acceso (instancia vacía en el puerto 8002: primer uso → códigos → cambio de contraseña → recuperación → ingreso), sin errores de consola ni de servidor |

Las pruebas de 6.8 cubren:
- todas las rutas sin sesión responden 401, salvo las públicas;
- `/docs` → 404 y `/api/salud` → `{ok, version}`;
- Host y Origin ajenos, y la falta de token CSRF;
- la cookie vieja tras salir, la inactividad y las 12 h;
- la reautenticación;
- bomba ZIP, XXE, imagen gigante, PDF malicioso y el proceso aislado;
- nombres con `../`;
- `=HYPERLINK` como texto;
- incidentes sin detalle, encabezados y registros sin cédulas ni contraseñas;
- recortes de fotos sin EXIF ni GPS;
- la copia cifrada que se restaura;
- eliminar un cliente borra su rastro.

## Pendiente o fuera de alcance

- **OWASP ZAP:** no se corrió porque este equipo no tiene Docker. El flujo de GitHub Actions puede agregarlo.
- **gitleaks sobre todo el historial** falla mientras el historial tenga los archivos personales de versiones
  anteriores. Se limpia en la Fase 7, con el repositorio ya privado.
- **El ejecutable reconstruido** (`console=False`, bandeja, secretos en el almacén) se prueba en la Fase 7 con un
  perfil vacío.
- **La aplicación real (puerto 8000)** sigue con el código de la v2.2. Al reiniciarla con esta versión:
  - los secretos de `backend/.env` pasan al Administrador de credenciales;
  - el usuario actual se importa a la tabla `usuarios`;
  - la contraseña se migra a Argon2id en el primer ingreso.
