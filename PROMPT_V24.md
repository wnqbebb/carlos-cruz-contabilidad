# PROMPT v2.4 — Auditoría completa y corrección definitiva

> Guárdalo como `PROMPT_V24.md` en la raíz del repo.
> **"Lee PROMPT_V24.md completo y ejecútalo. Cuando necesites algo de mí, pídemelo con una pregunta concreta y sigue con lo que no dependa de eso."**

---

## 0. LA SITUACIÓN, SIN ADORNOS

La v2.3.0 se reportó como «terminada y verificada»: 344 pruebas, 708 vistas revisadas, seguridad en verde. **Para el usuario no funciona:**

1. **La app desplegada no deja entrar.** En `https://carlos-cruz-contabilidad.vercel.app`, al pulsar «Ingresar», sale **405**.
2. **El usuario no sabe su usuario ni su contraseña.**
3. **Renta no hace nada.** La pantalla Renta solo muestra un contribuyente con «Sin información» y no hay forma de subir ni calcular desde ahí.
4. **Clientes y el trabajo contable quedaron peor que antes.** La simplificación quitó cosas que se usaban:
   - ya no se puede editar el nombre ni los datos con facilidad;
   - las gráficas son complicadas;
   - el Excel descargado ya no está completo.
5. **La franja oscura de arriba** (en Renta, por ejemplo) dificulta leer y no corresponde al modo elegido.
6. Después de más de 5 horas de trabajo, **el resultado práctico fue casi nulo**.

La causa de fondo: **se verificó contra pruebas propias y contra `localhost`, no contra lo que usa el usuario.** Desde esta versión, **«terminado» significa que funciona en la URL desplegada, con los archivos reales, recorrido por un humano de principio a fin.**

---

## 1. EVIDENCIA ENCONTRADA EN LA REVISIÓN EXTERNA (reprodúcela tú)

### E1 · Por qué sale 405 (causa confirmada)
Vercel solo tiene el **frontend estático**. No hay backend desplegado:
- `GET https://carlos-cruz-contabilidad.vercel.app/api/salud` devuelve **el HTML de la app** (200 `text/html`), no JSON.
- `POST /api/sesion` devuelve **405** desde Vercel: la regla `rewrites` de `frontend/vercel.json` envía todo, incluido `/api/*`, a `index.html`, y un archivo estático no acepta POST.
- El build se hizo **sin `VITE_API`**, así que el frontend llama a su propio dominio.
- Aunque se configurara `VITE_API` hacia otro dominio, **la cookie de sesión no viajaría**: es `SameSite=Lax` y estaría en otro sitio. Además, la validación de `Host` y `Origin` y el CSRF lo rechazarían.

### E2 · La declaración de renta puede dar un resultado peligroso
Con las fotos reales del Caso B (las 3 fotos giradas e impresas dos veces), en un entorno Linux con Tesseract 5:
- El OCR leyó texto basura (por ejemplo, entidad «SI A AAA A a»), con un 42 % de confianza alta. Aun así, la app produjo un **borrador «Paga $ 289.321.000»** y una **sanción de $ 16.891.000**.
- Sumó $ 627.024.000 en rentas de trabajo, cuando el **Tope 1 del propio reporte dice $ 82.535.904**. Puso patrimonio en 0, cuando el Tope 2 dice $ 226.543.936.
- Atribuyó «$ 514.118.785 pagados por BANCO DE BOGOTA» (en realidad, saldos y movimientos mal leídos) y aplicó la respuesta por defecto «trabajo personal» **sin que nadie la confirmara**.
- Solo 1 de los 5 topes se validó («cuadra»). Los demás no se compararon, y **nada bloqueó el resultado**.

En el entorno de Claude Code, el mismo caso dio «paga $ 130.000». **El resultado depende de la máquina:** el OCR no es reproducible. Con el Caso A (foto legible), el patrimonio (4.600.000) y las deudas (52.201.000) sí salieron bien.

### E3 · El Excel de un periodo guardado está incompleto
Con el caso de demostración «completo»:
- El Excel del cálculo recién hecho (`/api/exportar/{sid}/excel`) tiene 14 hojas.
- El del **periodo guardado** (`/api/periodos/{id}/excel`), que es el que usa el expediente desde la v2.3, **no trae «EF formato contador»**, que es justamente el formato del contador.
- **Ninguno de los dos trae las cuentas T.**

### E4 · Se perdió la edición en el expediente
El componente `EnLinea.tsx` (edición directa del nombre y los datos en la cabecera, de la v2.2) **existe pero ya no se usa en ninguna página**. Hoy solo queda un enlace «Editar ficha» que lleva a otra pantalla.

### E5 · Renta no tiene puerta de entrada
- `Renta.tsx` no tiene zona de subida: solo lista personas naturales que **ya** están en el directorio.
- Un contador recibe para la renta a personas que **no** lleva en contabilidad. Hoy no hay cómo crear un contribuyente subiendo su exógena.

### E6 · Otros
- **El repositorio en GitHub sigue público.**
- `backend/.env` del equipo tiene en texto plano tokens personales de GitHub, Vercel y Supabase.
- Las credenciales de Supabase quedaron guardadas en un espacio del Administrador de credenciales que la app real no usa.

---

## 2. CÓMO TRABAJAR ESTA VEZ

1. **Primero la auditoría, después las correcciones.** Escribe `docs/v24/AUDITORIA.md` antes de cambiar código.
2. **Pide lo que necesites, pero no te detengas.** Si algo depende del usuario (cuentas, contraseñas, decisiones), hazle **una pregunta concreta**, con opciones y tu recomendación, y sigue con lo que no dependa de eso. Agrupa las preguntas: no más de una tanda cada vez.
3. **Los secretos nunca pasan por el chat.** Contraseñas, `DATABASE_URL` y tokens los escribe el usuario directamente en el panel de Render o Vercel, o en el archivo local. Tú le dices exactamente dónde y cómo.
4. **«Terminado» = funciona para el usuario.** Cada bloque se verifica:
   - (a) con pruebas automáticas;
   - (b) **contra la URL desplegada**, con Playwright;
   - (c) con un guion de prueba manual corto para el usuario (`docs/v24/PROBAR.md`).
5. **Nada se quita sin reemplazo.** Toda función de la v2.2.0 (commit `a48cf1e`) sigue existiendo, salvo Parámetros y Trabajar, que se fusionaron.
6. **Resultados reproducibles.** Una misma entrada da el mismo resultado en Windows, en Linux y en el servidor.
7. Commits por bloque. Push al final de cada bloque (el usuario indicó expresamente mantener público el repo hasta finalizar).

---

## 3. AUDITORÍA COMPLETA (`docs/v24/AUDITORIA.md`)

Revisa el proyecto de principio a fin y documenta, con evidencia:

1. **Despliegue y acceso:** qué está desplegado, dónde y con qué variables; por qué falla; cómo ingresa el usuario hoy en local y en la nube.
2. **Regresiones de la v2.2 a la v2.3.** Haz una **matriz función por función**:
   - pantallas, botones, ediciones;
   - descargas y sus hojas;
   - informes, gráficas, atajos.

   Por cada fila: v2.2 / v2.3 / ¿se perdió? / ¿dónde está ahora? Usa `git diff a48cf1e HEAD` y recorre ambas versiones con Playwright.
3. **Recorridos reales de usuario**, cronometrados, en la URL desplegada y en local:
   - (a) crear un cliente subiendo sus archivos;
   - (b) ver sus estados financieros y cambiar de mes;
   - (c) editar el nombre del cliente;
   - (d) descargar el Excel completo;
   - (e) hacer la renta de una persona que **no** es cliente, subiendo su exógena;
   - (f) hacer la renta de los casos A y B.

   Por cada uno: clics, segundos, errores y lo que confunde.
4. **Renta:**
   - exactitud con las 5 imágenes reales (en `privado/`), en tu máquina **y** en un contenedor Linux igual al de producción;
   - qué validaciones existen y cuáles faltan;
   - en qué casos puede mostrar una cifra falsa.
5. **Exportaciones:** cada Excel y cada PDF, hoja por hoja y columna por columna, contra la v2.2.
6. **Diseño:** contraste real de cada cabecera y franja en claro, oscuro y sistema; capturas.
7. **Seguridad en la nube:** qué de la v2.3 supone Windows (almacén de credenciales DPAPI, `127.0.0.1`) y no sirve en un servidor Linux.
8. **Datos reales:** qué hay hoy en Supabase. Por ejemplo, por qué el contador aparece como contribuyente en Renta.

Cada hallazgo lleva: severidad, evidencia, causa, corrección y prueba que lo cubrirá. Después **corrige todo**, en el orden de la sección 4.

---

## 4. CORRECCIONES (en este orden)

### Bloque 1 — Que se pueda entrar: en la nube y en local

**1.1 Desplegar el backend.**
- Usa Render con `render.yaml` y `Dockerfile` (ya existen), salvo que la auditoría muestre algo mejor; en ese caso, pregúntale al usuario.
- La imagen Docker incluye **Tesseract con el idioma español, con versión fijada**: la misma versión que use el `.exe`.
- **Pídele al usuario** lo necesario:
  - crear el servicio en Render, o darte acceso;
  - pegar en Render las variables secretas (`DATABASE_URL` y las demás). Dile exactamente cuáles y dónde.
- En Linux, los secretos vienen de **variables de entorno**. El almacén de Windows queda solo para el `.exe`. Que la app detecte el modo sola.
- **Atención al plan gratuito:** si se duerme, el primer ingreso tarda. Muestra «Despertando el servidor…» en lugar de un error, y documenta la opción de pago.

**1.2 Que el navegador hable con el backend en el mismo dominio.**
- En `frontend/vercel.json`, antes de la regla que manda todo a `index.html`, agrega una **regla de reescritura de `/api/(.*)` hacia el backend**. Así la cookie es del mismo sitio y funcionan `SameSite=Lax`, el CSRF y `Origin`.
- Configura `TrustedHost` y los `Origin` permitidos para el dominio de Vercel y el host del backend.
- Si algo de esto exige cambiar la seguridad, explícalo en la auditoría y **no la debilites sin decirlo**.

**1.3 Recuperar el acceso** (el usuario no sabe su usuario ni su contraseña):
- **En local:** un `restablecer_acceso.bat` que solo funciona en el equipo, borra el usuario actual y deja la app en «Crear su acceso». Explícaselo en el chat; no se menciona en la interfaz.
- **En la nube:** «Crear su acceso» abierto a internet permitiría que **cualquiera** se apropie de la app. Protégelo con un **código de instalación de un solo uso** (variable `CC_CODIGO_INSTALACION` en Render). La pantalla lo pide y, una vez usado, deja de servir.
  - Dile al usuario cómo definirlo y cuándo usarlo. Él elige su usuario y contraseña en la pantalla; tú nunca los ves.
- **La pantalla de ingreso explica cada error en lenguaje humano**, nunca un código HTTP suelto:
  - «No hay conexión con el servidor; puede estar despertando, espere unos segundos»;
  - «Usuario o contraseña incorrectos»;
  - «Demasiados intentos, espere 15 minutos».

**Verificación:**
1. En la URL de Vercel: crear acceso con código → ingresar → cerrar sesión → ingresar.
2. Lo mismo en local tras `restablecer_acceso.bat`.
3. Prueba automática que falla si `/api/salud` desplegado no devuelve JSON.

### Bloque 2 — Renta que funcione y que nunca mienta

**2.1 Bloqueo de resultados no confiables** (lo más importante del bloque). La app **no muestra «Paga $ X» ni sanción** si ocurre cualquiera de estas cosas:
- algún tope del encabezado no cuadra con la suma de sus líneas (con una tolerancia de pocos pesos, explicada);
- los ingresos clasificados superan el Tope 1 o el patrimonio difiere del Tope 2;
- hay líneas con valores en baja confianza que afectan casillas;
- quedan preguntas que cambian la cédula **sin confirmar**.

En esos casos muestra **«Borrador incompleto»**, con la lista exacta de lo que falta y el botón para corregirlo. **Las respuestas por defecto nunca se aplican en silencio** a decisiones que cambian el impuesto: se proponen, pero el resultado espera la confirmación.

**2.2 OCR reproducible y honesto.**
- Misma versión de Tesseract y mismo preprocesado en Windows, Linux y el `.exe`.
- Prueba en CI dentro del contenedor de producción con imágenes sintéticas, y en local con las 5 reales.
- Las líneas ilegibles (texto basura) **no se convierten en datos**: quedan para escribirlas a mano con la imagen recortada al lado.
- Si la hoja está impresa dos veces y la mayoría es ilegible, se dice claramente y se ofrece:
  - (a) subir el PDF o Excel del portal de la DIAN;
  - (b) **digitar solo los 5 topes y las líneas clave en una tabla rápida**, con la foto al lado.
- **Meta Caso B:** nunca una cifra falsa. O el resultado correcto, o «incompleto» con la ruta para completarlo.

**2.3 La puerta de entrada que falta.**
- En **Renta⁰³**, una zona grande: **«Suelte la exógena de cualquier persona»**.
- La app lee el documento y el nombre del encabezado.
  - Si la persona ya es cliente, abre su renta.
  - Si no, **la crea como contribuyente de renta** (persona natural, sin contabilidad) con un clic de confirmación.
- La cartera de Renta muestra a todos: clientes con contabilidad y contribuyentes solo de renta.
- Averigua por qué el contador aparece como contribuyente y corrígelo si es un error de datos.

**2.4 Flujo de 3 pasos real**, medido en la URL desplegada: soltar → revisar (veredicto, cifras, preguntas) → descargar.
- Caso A: casillas iguales al 210 presentado.
- Caso B: según 2.2.
- Persona nueva: de soltar a borrador en menos de 3 minutos.

### Bloque 3 — Clientes y contabilidad: devolver lo que se quitó y hacerlo más fácil

**3.1 «Subo los archivos y hace todo de inmediato y correcto».**
- Al soltar archivos (en Clientes o en el cliente), la app **calcula en el acto con las respuestas sugeridas** y muestra el resultado.
- Las preguntas quedan como una franja «Revise 3 supuestos», donde cambiar una respuesta recalcula.
- Excepción: las preguntas que cambian cifras de forma importante (como en renta, 2.1) se marcan y el periodo **no se cierra** hasta confirmarlas.

**3.2 Panel de edición.**
- Vuelve la edición directa del **nombre** y los datos principales en la cabecera del expediente (reutiliza `EnLinea.tsx`).
- Además, un **panel lateral «Editar cliente»** que se abre sin salir del expediente, con todos los campos y los socios, y guardado inmediato con «Deshacer».
- **Prueba:** editar el nombre en menos de 10 segundos.

**3.3 Excel completo, como en la v2.2 o mejor.**
- El Excel del periodo guardado debe ser **idéntico en hojas y contenido** al del cálculo recién hecho, **incluida «EF formato contador»**. Guarda en el resultado lo necesario para regenerarla.
- Agrega la hoja de **Cuentas T**.
- **Prueba automática:** ambos Excel tienen las mismas hojas y las mismas cifras.
- **Matriz de la auditoría:** ninguna hoja ni columna de la v2.2 falta.

**3.4 Gráficas simples.**
- Máximo **2** en el resumen del cliente: ingresos vs. gastos por mes (barras) y utilidad por mes (línea).
- Con etiquetas legibles y el valor exacto al pasar el cursor. Sin anillos ni medidores difíciles de leer.
- Lo demás, en números claros.

**3.5 Recupera lo perdido de la matriz de regresiones**, salvo que el usuario decida quitarlo. Pregúntale por lo dudoso, en una sola tanda.

### Bloque 4 — Diseño legible
- **Quita las franjas oscuras de cabecera** en modo claro. Cada sección conserva su identidad con un tono claro sutil y su número de índice.
- En modo oscuro, todo es oscuro y coherente.
- Ningún texto de cabecera por debajo de 4,5:1 en **los tres modos**: mídelo y documéntalo.
- El selector Claro/Oscuro/Sistema cambia **toda** la pantalla al instante.

### Bloque 5 — Higiene
- El repositorio en GitHub se mantiene **público** por indicación expresa hasta finalizar el proyecto.
- Saca de `backend/.env` los tokens que la app no usa.
- Recomiéndale **revocar y regenerar** los tokens de GitHub, Vercel y Supabase que estuvieron en texto plano.
- Repara las credenciales de Supabase guardadas en el espacio equivocado: pídele al usuario que pegue `DATABASE_URL` en el `.env` local una vez; la app la guarda en el lugar correcto y la borra del archivo.

---

## 5. VERIFICACIÓN FINAL Y ENTREGA

1. Todo en verde: pruebas, `tsc`, lint, build y `scripts/seguridad.bat`.
2. **Recorridos de la auditoría (3a–3f) repetidos en la URL desplegada**, con video o capturas en `docs/v24/`, cronometrados, antes y después.
3. **`docs/v24/PROBAR.md`:** un guion de 10 minutos para que el usuario compruebe cada punto que reportó: entrar, editar el nombre, subir y ver resultados, cambiar de mes, descargar el Excel completo, hacer una renta nueva, y casos A y B.
4. Versión `v2.4.0`, desplegada en Render y Vercel, y en local con `iniciar.bat`.
5. **Mensaje final en el chat, corto:**
   - ¿Ya se puede entrar en la URL? Cómo, paso a paso.
   - Lo que tuvo que hacer o decidir el usuario y lo que falta, si algo.
   - Los 6 problemas reportados: resuelto o no, uno por uno, con su evidencia.
   - Qué probar primero.
