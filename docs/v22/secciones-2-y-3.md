# Secciones 2 y 3 · Revisión externa y pendientes del informe

Estado de cada punto. Los que se hicieron en fases anteriores dicen dónde.

## Sección 2 · revisión externa
| Punto | Estado | Dónde / cómo |
|---|---|---|
| A1 · nombres de archivo con errores de escritura | ✅ Fase 4 | `importadores/identidad.py`: parecido ≥ 85 (rapidfuzz) más fonética; ruido PYME, MIPYME, MICROEMPRESA, NEGOCIO, EMPRESA, REGISTROS; `tests/test_nombre_archivo.py` (12 pruebas) |
| A2 · inicio de sesión | ⏳ Sección 4.2 | |
| A3 · capital en libros ≠ estatutos como advertencia visible en la ficha | ✅ Fase 6 | `inteligencia/sugerencias.py` (`_capital_vs_estatutos`) |
| A4 · nómina registrada dos veces | ✅ Fase 5 | alerta DOBLE-NOMINA con las dos cifras y «Cerrar de todos modos» |
| **A5 · subidas en disco temporal** | ✅ aquí | ver abajo |
| A6 · nota sobre FANANT enero 2025 | ⏳ Sección 4 (se escribe en la base real con la nota exacta; las cifras no se tocan). La aplicación ya muestra notas de cliente (aviso en la ficha) y de periodo. |

### A5 — los archivos subidos ya no viven en la memoria
`repositorio/subidas.py`: entre «subir» y «confirmar», los archivos se escriben en una carpeta temporal (`CC_TMP_SUBIDAS`, por defecto `%TEMP%\carloscruz-subidas\<subida>`) y la sesión guarda solo la ruta. Al confirmar se leen del disco y la carpeta se borra. Las subidas que llevan más de 8 horas sin usarse se borran al arrancar el servidor y cada vez que se sube algo. Los nombres de archivo se limpian para que no puedan salir de su carpeta.

**Prueba de memoria** (`tests/test_subidas_disco.py`): diez subidas de un Word de 20 MB.
- Con el código anterior: **200,4 MB retenidos** (la prueba falla, se comprobó).
- Ahora: por debajo del límite de 15 MB (la prueba pasa).

## Sección 3 · pendientes del informe
| Punto | Estado | Dónde / cómo |
|---|---|---|
| P01 · libro diario en CSV o Excel | ✅ Fase 4 | `importadores/libro_diario.py`; lo usa el cliente de demostración 4 |
| H13 · `/api/tablero` con agregados | ✅ Fase 7 | `inteligencia/tablero.py` |
| H14 · colores del Excel | ✅ Fase 5 | `exportar/excel.py` con los tokens |
| **H15** · `vite.config.ts.timestamp-*` | ✅ aquí | 7 archivos borrados; ya estaban en `.gitignore` |
| H16 · un solo azul por vista en Estados | ✅ Fase 5/8 | |
| **H17** · endpoints y funciones sin uso | ✅ aquí | ver abajo |
| H18 · municipio del preloader | ✅ Fase 7 | `contador.py` |
| **H20** · reintentos a Supabase | ✅ aquí | ver abajo |
| **H22** · naturaleza contraria | ✅ aquí | ver abajo |
| **H23** · aviso del cliente de pruebas | ✅ aquí | `httpx2` en `requirements.txt` (lo pide Starlette 1.7); las pruebas corren **sin avisos**, también con `-W error::SyntaxWarning` |

### H17 — lo que no se usaba
Quitado del backend: `GET /api/clientes/resumen`, `GET /api/clientes/buscar`, `GET /api/clientes/{id}/alias`, `GET /api/periodos/{id}`, `GET /api/versiones/{id}`, `GET /api/actividad`, `GET /api/subir/{id}`, `GET /api/plantilla-demo` y `periodos.serie_cartera()` (que además sumaba dinero en SQL, contra la regla de exactitud). Quitado de `api.ts`: `resumen`, `urlPlantilla` (duplicaba `descargas.plantillaClientes`), `version`, `actividadGeneral`, `puerta.ver`, `plantillaDemo`. Imports sin uso limpiados (pyflakes sin hallazgos fuera de los `__init__`).

Además: **el NIT de FANANT estaba escrito en la interfaz** para decidir dónde mostrar «Cargar sus archivos de ejemplo». Ahora el backend responde `archivos_de_muestra` en la ficha (verdadero solo si el cliente es el dueño de esos archivos y los archivos están en el equipo) y `POST /api/importar/ejemplo` exige ese cliente.

### H20 — cuando la base no responde
- `db.con_reintentos`: un fallo al **conectar** se reintenta tras 0,5 s, 1,5 s y 3 s. Los errores que no son de conexión (por ejemplo, un NIT duplicado) no se reintentan.
- Si sigue sin responder, la API devuelve **503** con `{codigo: "sin_base", mensaje}`: «No hay conexión con la base de datos en la nube (Supabase): se intentó 4 veces durante unos 5 segundos. Revise el internet de este equipo y vuelva a intentar en un momento. Lo que ya estaba guardado no se perdió.» La pantalla lo muestra tal cual.
- Si la conexión se cae a mitad de una consulta, también 503: la siguiente petición abre una conexión nueva.
- La interfaz **repite sola las lecturas** (GET) que no obtuvieron respuesta o recibieron 503, tras 0,8 s y 2 s. Las escrituras no se repiten (podrían hacerse dos veces).
- `tests/test_reintentos.py`: 4 pruebas.

### H22 — IVA con saldo débito
La reclasificación del IVA con saldo de naturaleza contraria (240805 → 240810) ahora se **acepta por defecto** y deja la advertencia RECL-NATURALEZA: «Se reclasificó por defecto $ … de IVA con saldo débito a IVA descontable (240810), para que el balance no muestre un pasivo negativo. Si no corresponde, desmárquelo en «Ajustes» y recalcule.» Las otras reclasificaciones (gastos personales, aportes) siguen solo propuestas.

**FANANT enero 2025 no cambia:** el periodo guardado no se recalcula, y la prueba de control (`test_cifras_de_control_fanant_enero_2025`) fija las mismas decisiones del cierre original (causación aceptada, reclasificación del IVA sin aplicar) y sigue dando los 13 saldos centavo a centavo. Una prueba nueva comprueba el comportamiento por defecto.

## Verificación
| Comprobación | Resultado |
|---|---|
| Pruebas del backend | ✅ 245, sin avisos |
| `tsc --noEmit` · `lint:diseno` · `build` | ✅ · ✅ 0 · ✅ |
| Recorridos de las fases 5, 6, 7 y 9 contra la copia aislada | ✅ sin errores de consola, sin desbordes; registro del servidor sin errores |
