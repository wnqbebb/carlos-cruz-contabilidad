# Seguridad de Carlos Cruz

Versión 2.3. Este documento dice qué se protege, de quién, por dónde podrían entrar y con qué controles se cierra
cada puerta. Cada control lleva una prueba automática (`backend/tests/test_seguridad.py`) y su referencia a
**OWASP ASVS 4.0.3, nivel 2**.

## 1. Modelo de amenazas

### Qué se protege
| Activo | Por qué importa |
|---|---|
| Contabilidad de los clientes (balances, nómina, inventario) | Información financiera confidencial de terceros |
| Declaraciones de renta y fotos de exógena | Datos personales (Ley 1581 de 2012): cédulas, nombres, ingresos, patrimonio |
| Acceso a la aplicación | Quien entra ve y cambia todo |
| Secretos del equipo | Conexión a la base en la nube, clave de cifrado de archivos y copias |
| Copias de seguridad | Contienen todo lo anterior |

### De quién
- **Alguien con el equipo encendido y sin vigilancia** (oficina compartida).
- **Una página web maliciosa** abierta en el mismo navegador: CSRF y *DNS rebinding* contra `localhost`.
- **Un archivo malicioso** que llega como «el Excel del cliente»: bombas de compresión, XML con entidades
  externas, imágenes gigantes, PDF que cuelgan el lector, nombres con `../`, macros.
- **Quien obtenga una copia del repositorio, un registro o una copia de seguridad.**
- **Una dependencia comprometida** (cadena de suministro).

### Por dónde podrían entrar
1. La API HTTP en `127.0.0.1:8000` (o el backend desplegado).
2. Los archivos subidos (contabilidad y renta).
3. Los archivos que la aplicación genera (Excel, PDF) y se comparten.
4. El disco: base local, archivos temporales, registros, copias.
5. El repositorio y las dependencias.

## 2. Controles

| # | Control | Dónde | ASVS |
|---|---|---|---|
| **Acceso** | | | |
| C1 | Primer uso desde el navegador, **solo** si no hay usuario y **solo** desde el mismo equipo; 10 códigos de recuperación que se muestran una vez (en la base, solo su hash) | `api/acceso.py`, `seguridad/cuentas.py` | V2.5.1, V2.5.4 |
| C2 | «¿Olvidó la contraseña?» con un código de recuperación de un solo uso; cierra todas las sesiones | `api/acceso.py` | V2.5.2, V2.5.6 |
| C3 | Contraseñas con **Argon2id**; mínimo 12 caracteres; lista de contraseñas comunes; medidor de fortaleza; los hashes bcrypt anteriores se migran al ingresar | `seguridad/claves.py` | V2.1.1, V2.1.7, V2.1.8, V2.4.1 |
| C4 | Verificación en dos pasos **TOTP** opcional (código QR desde Sistema) | `seguridad/cuentas.py` | V2.8.1, V2.8.3 |
| C5 | Límite de intentos de ingreso (5 en 15 min por equipo y por usuario) | `sesion.py` | V2.2.1 |
| C6 | **Sesiones en el servidor**: token opaco aleatorio (solo su hash en la base), rotado al ingresar, 30 min de inactividad, 12 h absolutas, «cerrar todas las sesiones», al salir la cookie deja de servir | `sesion.py` | V3.2.1, V3.3.1, V3.3.2, V3.3.4 |
| C7 | Cookie `HttpOnly`, `SameSite=Lax`, `Secure` con HTTPS | `api/sesion.py` | V3.4.1–V3.4.3 |
| C8 | **Reautenticación** (contraseña, y TOTP si está activo) antes de: eliminar un cliente, eliminar los de demostración, restaurar una versión, cambiar la contraseña, desactivar TOTP, descargar todo | `sesion.py`, `api/acceso.py` | V3.7.1 |
| C9 | Toda la API pide sesión salvo `/api/salud`, `/api/sesion` y el primer uso / recuperación | `main.py` | V4.1.1 |
| **Peticiones** | | | |
| C10 | **CSRF**: `Origin`/`Referer` de la propia aplicación y un token por sesión en cada petición que modifica datos | `seguridad/http.py` | V4.2.2, V13.2.3 |
| C11 | **Host** permitido (contra *DNS rebinding*): `localhost`, `127.0.0.1` y los dominios configurados; el servidor escucha solo en `127.0.0.1` | `seguridad/http.py` | V14.5.3 |
| C12 | **Límite de solicitudes** en toda la API y más estricto en subidas, cálculos y lectura de fotos | `seguridad/http.py` | V11.1.4 |
| C13 | Encabezados: CSP estricta (`script-src 'self'`, `frame-ancestors 'none'`), `nosniff`, `Referrer-Policy: no-referrer`, `Permissions-Policy`, HSTS con HTTPS; `Cache-Control: no-store` en la API | `seguridad/http.py` | V14.4.1–V14.4.7 |
| C14 | CORS cerrado a los orígenes configurados | `main.py` | V14.5.3 |
| C15 | Documentación de la API (`/docs`, `/redoc`, `/openapi.json`) desactivada; solo con `CC_DOCS=1` en desarrollo | `main.py` | V14.3.3 |
| **Errores y registros** | | | |
| C16 | Errores: mensaje humano + **código de incidente** (`INC-7F3A`); el detalle solo en el registro local | `seguridad/incidentes.py` | V7.4.1 |
| C17 | `/api/salud` sin sesión responde solo `{ok, version}` | `api/sistema.py` | V14.3.2 |
| C18 | **Registros sin datos sensibles**: se quitan contraseñas, cookies, tokens y cadenas de conexión; cédulas y NIT enmascarados (`****8740`). Se escriben desde un hilo aparte: una consola o un disco lentos nunca congelan el servidor | `seguridad/incidentes.py` | V7.1.1, V7.1.2 |
| C19 | **Bitácora de seguridad**: ingresos, fallos, contraseña, TOTP, descargas, eliminaciones y restauraciones, con fecha e IP; aviso en Sistema si hubo intentos fallidos recientes | `repositorio/bitacora.py` | V7.2.1, V7.2.2 |
| **Archivos subidos** | | | |
| C20 | Tipo por **contenido** (firma de bytes), no por extensión | `seguridad/archivos.py` | V12.2.1 |
| C21 | Bombas de compresión: límites de tamaño descomprimido, entradas y proporción antes de abrir `.xlsx`/`.docx` | `seguridad/archivos.py` | V12.1.2 |
| C22 | XML seguro (`defusedxml`, sin entidades externas) | `seguridad/archivos.py` | V5.5.2 |
| C23 | Imágenes: límite de píxeles y de proporción; PDF: límite de páginas y tamaño | `seguridad/archivos.py` | V12.1.1 |
| C24 | Análisis **aislado**: cada lote se lee en un proceso aparte con tiempo y memoria limitados. Ninguna ruta corre trabajo síncrono en el bucle del servidor (rutas `def` y sesión leída en un hilo): una subida pesada no congela a los demás | `seguridad/aislado.py`, `seguridad/http.py` | V12.1.3, V11.1.4 |
| C25 | Nombres aleatorios en disco, **cifrado AES-256-GCM**, borrado a las 8 horas; nunca se usa el nombre original como ruta | `repositorio/subidas.py`, `seguridad/cifrado.py` | V12.3.1, V6.2.2 |
| C26 | `.xlsm`: las macros nunca se ejecutan y se avisa | `seguridad/archivos.py` | V12.2.1 |
| C27 | Fotos: nunca se guardan completas (solo recortes de filas de la tabla, sin metadatos); notas a mano y credenciales nunca se guardan | `renta/ocr.py` | V8.3.4 |
| **Archivos generados** | | | |
| C28 | Excel/CSV sin **inyección de fórmulas** (textos que empiezan por `= + - @`, tab o retorno van como texto) | `seguridad/archivos.py` (`texto_seguro`) | V5.3.10 |
| C29 | PDF sin metadatos internos (rutas, usuario del equipo); las descargas quedan en la bitácora | `exportar/` | V8.3.4 |
| **Datos y secretos** | | | |
| C30 | Secretos en el **Administrador de credenciales de Windows** (DPAPI, `keyring`): conexión a la base y clave de cifrado; se migran solos desde el archivo de texto y se borran de él; el espacio del almacén va atado a ese archivo (`CC_ENV` es el único que se lee), así que una copia de prueba nunca toca los secretos reales; `.env` solo en desarrollo, nunca empaquetado | `seguridad/secretos.py` | V6.4.1, V2.10.4 |
| C31 | Base en la nube: rol de **mínimo privilegio** para la aplicación (`supabase/migraciones/007_rol_app.sql`) y SSL `verify-full` | `config.py` | V9.2.1, V1.4.4 |
| C32 | **Copias de seguridad cifradas** diarias (AES-256-GCM), 30 días de retención y prueba de restauración automática | `seguridad/respaldo.py` | V8.1.6 |
| C33 | Ley 1581: cédulas enmascaradas en listas y registros; eliminar un cliente borra sus periodos, archivos, recortes, declaraciones e historial | varios | V8.3.1, V8.3.2 |
| **Cadena de suministro** | | | |
| C34 | Dependencias fijadas con hashes (`backend/requirements.lock`, `npm ci`) | `iniciar.bat` | V14.2.1 |
| C35 | `scripts/seguridad.bat` y GitHub Actions: `pip-audit`, `npm audit`, `bandit`, `semgrep`, `gitleaks`; Dependabot; *pre-commit* con gitleaks y «nada de `privado/`» | `.github/`, `.githooks/` | V14.2.1, V14.2.4 |

## 3. Retención de datos (Ley 1581 de 2012)

| Dato | Dónde | Cuánto se guarda |
|---|---|---|
| Subidas en proceso (archivos ya leídos) | Carpeta temporal, cifradas | 8 horas |
| Fotos de exógena | No se guardan; solo recortes de las filas | Mientras exista la declaración |
| Contabilidad, declaraciones y su historial | Base de datos | Mientras exista el cliente; «eliminar cliente» lo borra todo |
| Bitácora | Base de datos | 5 años (soporte de la actuación profesional); se borra con el cliente |
| Copias de seguridad cifradas | `Documentos\Carlos Cruz\respaldos` | 30 días |
| Registro técnico local | `datos_app\registro` | 30 días, sin datos sensibles |

El titular de los datos puede pedir al contador su consulta, corrección o supresión; la supresión se hace con
«Eliminar cliente» (con reautenticación).

## 4. Fuera del alcance (riesgos aceptados)

- Un atacante con sesión de administrador en Windows puede leer el Administrador de credenciales.
- Sin Docker en este equipo no se corre OWASP ZAP; la misma batería de pruebas de encabezados, CSRF, host y
  archivos maliciosos está en `test_seguridad.py`.
