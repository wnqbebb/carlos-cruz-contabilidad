# PROMPT DE RESCATE — Que la app funcione de verdad para el usuario

> Para Claude Code en la terminal. Ejecuta todo en orden. Antes de empezar, lee `CLAUDE.md`, que tiene las reglas de verificación y honestidad.

---

## 0. LA VERDAD DEL ESTADO ACTUAL (verificado desde fuera sobre el commit `d23058e`)

Los últimos informes dijeron «todo resuelto, 344 pruebas en verde, tsc limpio, desplegado». **No es cierto.** Reprodúcelo tú mismo antes de tocar nada:

| # | Hallazgo | Cómo comprobarlo |
|---|---|---|
| H1 | **No hay backend en la nube.** El servicio `carloscruz-api` de Render **no existe**. Por eso, en la versión de Vercel, nada funciona: ni el ingreso, ni el Excel, ni la renta | `curl -sI https://carloscruz-api.onrender.com/api/salud` responde 404 con `x-render-routing: no-server`. `https://carlos-cruz-contabilidad.vercel.app/api/salud` también responde 404 |
| H2 | **Hay 2 pruebas fallando:** `test_caso_c_persona_nueva_solo_renta` (`ErrorCliente` en `repositorio/clientes.py:84`) y `test_lo_publico_no_pide_sesion` (da 503 si no existe `frontend/dist`) | `cd backend && python -m pytest -q` → «2 failed, 331 passed» |
| H3 | **TypeScript tiene 8 errores** en `PanelEditarCliente.tsx`. El panel usa campos de socio que no existen (`identificacion`, `porcentaje`, `aporte`); el tipo `Socio` usa otros. **La edición de socios está rota.** Llegó a producción porque `npm run build` no revisa tipos | `cd frontend && npx tsc --noEmit` |
| H4 | **El Excel completo sí se genera en el backend**: 15 hojas, incluidas «EF formato contador» y «Cuentas T», también para periodos guardados por versiones anteriores. Si el usuario no puede descargarlo, la falla está en la nube (H1) o en el botón de la interfaz | Descárgalo con Playwright desde el navegador, en local y en la nube, y abre el archivo |
| H5 | **Renta con la foto real de una contribuyente:** el OCR leyó bien (los 5 topes cuadran; la diferencia de 3 pesos del Tope 4 se atribuye correctamente al propio reporte). Pero el resultado queda **«incompleto»** porque hay **6 filas para confirmar** y **1 pregunta sin confirmar**, y el usuario **no entendió qué tenía que hacer ni pudo editar nada** | Sube la foto de `privado/renta/imagenes/` por `/api/renta/subir-universal` y mira `motivos_incompleto` |
| H6 | **Renta no pregunta lo esencial del negocio.** Es una comerciante con consignaciones de 93,1 millones y facturación electrónica de 4,8 millones. El contador declaró ingresos no laborales de 65.400.000 y costos de 32.800.000. La app no pide ese dato, así que la columna «Declaración» queda en 0 y la de «Propuesta DIAN» en 4.787.000. El usuario no entiende la diferencia | Ver el PDF «borrador incompleto»: también imprime **113 casillas, casi todas en $ 0** |
| H7 | **No se pueden editar valores dentro de la app.** Ni movimientos, ni saldos, ni las cifras de la renta. Tampoco se pueden reemplazar los archivos subidos. Es lo que más pide el usuario | Recorre la interfaz |
| H8 | **El usuario siente que todo empeoró desde la v2.3** («simplificar»). Hay una matriz de regresiones en `docs/v24/AUDITORIA.md` §2, pero nadie comprobó en el navegador que lo marcado como «restaurado» funcione | Recorre cada fila de la matriz en el navegador contra la v2.2.0 (`a48cf1e`) |

---

## 1. MÉTODO DE TRABAJO (obligatorio)

1. **Primero los recorridos del usuario como pruebas automáticas** (Playwright, navegador real): sección 2. Escríbelos, córrelos, **míralos fallar** y guarda esa salida. Después corrige hasta que pasen.
2. Cada corrección lleva su prueba.
3. **Orden:**
   1. lo roto (H2, H3, H4);
   2. editar (H7);
   3. renta (H5, H6);
   4. regresiones (H8);
   5. nube (H1).
4. `npm run build` debe correr `tsc --noEmit` primero (ajusta `package.json`), para que un error de tipos nunca vuelva a llegar a producción.
5. La prueba que depende de `frontend/dist` debe compilar antes o saltarse con un aviso claro, nunca dar un falso fallo.
6. **Informe final con la salida real pegada** de: `git log -1`, el resumen de pytest, `tsc`, la cola del build, el resumen de Playwright y los `curl` de la nube.

---

## 2. RECORRIDOS DEL USUARIO = DEFINICIÓN DE TERMINADO

Crea `frontend/e2e/` con estas pruebas. Corren contra `http://localhost:8000` y, al final, contra la URL de Vercel.

| # | Recorrido | Debe cumplirse |
|---|---|---|
| J1 | Entrar | Crear acceso (o ingresar) y llegar al Tablero |
| J2 | Subir contabilidad | Soltar un archivo (caso demo «completo» y los archivos de FANANT de `privado/`) → resultado en pantalla **de inmediato**, sin pasos extra |
| J3 | Navegar | Estados financieros → estado de resultados → cambiar de mes **conserva la vista** |
| J4 | Editar el cliente | Cambiar el nombre directamente en el título (menos de 10 s) y, desde el panel lateral, sus datos y **socios**. Recargar la página y comprobar que todo quedó guardado |
| J5 | **Editar valores** (sección 3) | Abrir los datos del periodo → cambiar el valor y la cuenta de un movimiento → agregar una fila → borrar otra → cambiar un saldo inicial → los estados se recalculan solos → se ve «Cuadra» o «Descuadre» → «Deshacer» funciona → la versión anterior queda en el historial |
| J6 | Descargar | **Excel completo** (comprobar en el archivo descargado las 15 hojas y que las cifras coinciden con la pantalla), PDF y libros (diario, mayor y balances) en Excel y PDF. Además, «Descargar datos para editar» → modificar el archivo → volver a subirlo → el mismo periodo se actualiza |
| J7 | **Renta con foto legible** | Soltar la foto de la contribuyente en Renta⁰³ → la pantalla dice exactamente qué falta → confirmar las filas → responder la pregunta → escribir los ingresos (65.400.000) y costos (32.800.000) del negocio y el 1 % de compras (48.000) → las casillas coinciden con su 210 presentado (patrimonio 4.600.000; deudas 52.201.000; renta líquida gravable 32.604.000; impuesto 0; retenciones 5.000; saldo a favor 5.000) → descargar el ZIP |
| J8 | Renta con fotos difíciles | Las 3 fotos del otro contribuyente → **ninguna cifra de impuesto ni sanción** mientras falten datos → «Digitar lo esencial» → resultado coherente con los topes |
| J9 | Renta de una persona nueva | Soltar una exógena desde Renta⁰³ → crear el contribuyente con un clic → borrador. Esa persona **no** aparece entre los clientes contables |

Cada recorrido registra su tiempo y sus clics, y guarda capturas en `docs/rescate/`.

---

## 3. EDITAR DENTRO DE LA APP (lo que más pide el usuario)

### 3.1 «Datos del periodo»: un editor tipo Excel dentro del expediente
- Pestañas: **Movimientos** (libro diario), **Saldos iniciales**, **Inventario**, **Nómina**, **Activos fijos**.
- Columnas de Movimientos: fecha, comprobante, cuenta (con autocompletado del PUC por código o nombre), tercero, descripción, débito y crédito.
- **Agregar, duplicar y borrar filas.** Pegar desde Excel (varias filas a la vez).
- Validación en vivo: partida doble por comprobante y cuentas inexistentes.
- **Recálculo automático** al dejar de escribir. Los estados financieros, los libros y el Excel se actualizan.
- Cada guardado crea una **versión** en el historial que ya existe, con «Deshacer» inmediato y «Restaurar versión».
- Si el periodo está cerrado: «Reábralo para editar» (respeta la protección de la v2.2).

### 3.2 Archivos del periodo
- En «Archivos»: la lista de archivos subidos, con **ver**, **reemplazar**, **quitar** y **volver a procesar**.
- **«Descargar datos para editar»:** genera la plantilla oficial **con los datos actuales** del periodo. El usuario la edita en Excel y la vuelve a subir: la app reconoce que es el mismo periodo y **pregunta si actualizarlo**.

### 3.3 Cliente
- Nombre editable en el título (`EnLinea`) y el **panel lateral** con todos los campos y los socios (corrige H3).
- **Prueba de guardado y recarga de cada campo.**

---

## 4. RENTA: CLARA, EDITABLE Y CORRECTA

1. **Caja «Para terminar faltan N cosas»**, arriba y siempre visible, con un botón por cada cosa. Ejemplo: «[Confirmar 6 filas leídas de la foto] [Responder 1 pregunta] [Ingresos y costos del negocio]».
   - Confirmar filas: la imagen recortada al lado de cada valor; «Confirmar todas» después de verlas; edición directa de cualquier valor.
2. **Sección «Lo que solo usted sabe»**, con preguntas en lenguaje sencillo:
   - **Ingresos y costos del negocio.** Se pide automáticamente cuando la persona tiene actividad comercial (CIIU, facturación emitida) o cuando las consignaciones superan con mucho los ingresos reportados. Muestra la comparación: «Consignaciones 93,1 M · Facturación 4,8 M · Ingresos que usted declara: ____».
   - Dependientes, intereses de vivienda, medicina prepagada, aportes voluntarios.
   - El 1 % de compras con factura electrónica, con el máximo permitido y lo que el contador decida.
3. **Todo editable:**
   - cada línea de la exógena (valor, concepto, categoría, incluir o excluir);
   - **cada casilla** del 210: clic → de dónde sale + «Ajuste manual» con nota obligatoria, marcado en el papel de trabajo.
   - Todo recalcula al instante y queda en versiones.
4. **Las dos columnas explicadas.** Encabezados: «Lo que propondría la DIAN» y «Su declaración». Cada diferencia con su explicación en una línea («La DIAN toma la facturación como ingreso; usted declaró los ingresos reales del negocio»).
5. **PDF:**
   - El borrador completo muestra **solo las casillas con valor**, agrupadas por sección, más una tabla resumen. La lista completa de casillas va en un anexo.
   - El incompleto lleva primero la lista de lo que falta.
6. Corrige `test_caso_c_persona_nueva_solo_renta` (H2) y verifica que los casos A, B, C y D pasen **también en el navegador** (J7–J9).

---

## 5. REGRESIONES DESDE LA v2.2 (H8)

- Recorre en el navegador **cada fila** de la matriz de `docs/v24/AUDITORIA.md` §2, en la v2.2.0 (`git worktree add ../v22 a48cf1e`) y en la versión actual.
- Lo que falte o funcione peor **se restaura**, sin perder el diseño actual. Lo dudoso se le pregunta al usuario en **una sola tanda**.
- **Completo > minimalista.** Toda información que la v2.2 mostraba sigue disponible, aunque esté plegada.

---

## 6. NUBE: una sola dirección para el usuario (al final, H1)

**Decisión de arquitectura:**
- El usuario entra **siempre por `https://carlos-cruz-contabilidad.vercel.app`**.
- **Frontend en Vercel; backend en Render** (Docker con Tesseract), detrás del proxy `/api/*` que ya está en `vercel.json`. Para el usuario, «todo está en Vercel».
- **No muevas el backend a funciones serverless de Vercel.** El OCR necesita el binario de Tesseract, y los procesos largos (OCR, cálculos de muchos meses) superan los límites de tamaño y de tiempo de esas funciones.
- Si encuentras una alternativa mejor que Render (por ejemplo, Railway o Fly.io), propónla con sus costos en una sola pregunta.

**Pasos:**
1. **Pídele al usuario**, paso a paso y con capturas o texto exacto:
   - crear la cuenta en Render, si no la tiene;
   - crear el servicio desde el Blueprint `render.yaml`;
   - escribir **él mismo** las variables que exige el código. Revisa la lista real en `config.py`, `seguridad/` y `render.yaml`: como mínimo `DATABASE_URL`, `CC_CODIGO_INSTALACION`, `CLAVE_SESION` o `CC_CLAVE_MAESTRA`, y `CORS_ORIGENES`.
2. Comprueba que el nombre del servicio coincida con el destino de `vercel.json`. Si Render asigna otro nombre, actualiza `vercel.json` y vuelve a desplegar Vercel.
3. **Verifica tú:**
   - `curl -s https://<servicio>.onrender.com/api/salud` devuelve JSON;
   - `curl -s https://carlos-cruz-contabilidad.vercel.app/api/salud` devuelve el mismo JSON a través del proxy.
4. Corre J1–J9 contra la URL de Vercel. Hasta que pasen, **no digas que la nube funciona**.
5. Plan gratuito: el aviso «Despertando el servidor…» debe aparecer de verdad. Además, deja configurado el aviso para mantenerlo despierto (`.github/workflows/mantener-supabase-vivo.yml` o un *cron* externo) y explícale al usuario la opción de pago.

---

## 6.1 DATOS DE DEMOSTRACIÓN (local y nube)

El usuario quiere ver la app **llena y funcionando** con varios clientes ficticios. Todos llevan la etiqueta «Demostración» y se cargan **por la API**, igual que un usuario real.
- **Contabilidad:**
  - los 5 clientes históricos de la v2.2 (panadería, ferretería, clínica dental, transportadora y persona natural con registros auxiliares), con periodos de enero 2025 a septiembre 2026;
  - **3 más:** un restaurante, una droguería y un taller de motos, cada uno con un formato de entrada distinto y situaciones variadas: al día, atrasado, con descuadre, con inventario y con nómina.
- **Renta:** los 6 contribuyentes ficticios del caso D, más 2 con fotos sintéticas de exógena, para ver el flujo completo.
- **Comando para cargarlos o quitarlos:** «Eliminar demostración» en el panel Sistema. **Nunca** toca datos reales.

## 6.2 DISEÑO COMPLETO

- Conserva el sistema de diseño actual (tokens, modo claro/oscuro, `lint:diseno`).
- **Completo antes que minimalista:** cada pantalla debe tener la información y las acciones que el usuario necesita, sin tener que adivinar dónde están.
- Revisa con capturas en claro y oscuro, a 1440 y 390 px: Tablero, Clientes, el expediente (cada sección), el editor de datos, Renta (cartera y declaración) y Sistema.
- Cada pantalla vacía explica qué hacer y tiene su botón.

---

## 7. ENTREGA

1. Los recorridos J1–J9 en verde en local. En la nube, si el usuario ya creó el servicio.
2. `docs/rescate/INFORME.md` con:
   - la tabla H1–H8: antes, después y evidencia;
   - la salida real de todas las verificaciones;
   - tiempos y clics de cada recorrido;
   - lo que quedó pendiente y por qué.
3. App corriendo con `iniciar.bat` en `http://localhost:8000`.
4. **Mensaje final corto:**
   - qué probar primero;
   - qué necesita del usuario (por ejemplo, crear el servicio en Render);
   - la salida de las verificaciones pegada, no resumida.
