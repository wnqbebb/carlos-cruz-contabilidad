# PROMPT — Declaración de renta funcionando, automática y correcta (personas naturales, formulario 210, año gravable 2025)

> Para Claude Code (Opus 5). Guárdalo como `PROMPT_RENTA.md` en la raíz del repo y dile:
> **"Lee PROMPT_RENTA.md y ejecútalo completo en local. Esto va antes que cualquier otra cosa. Si necesitas algo de mí, pídemelo con una pregunta concreta y sigue."**

---

## 0. OBJETIVO Y DEFINICIÓN DE «TERMINADO»

El contador suelta los documentos de una persona (la exógena de la DIAN en Excel, PDF o foto, la declaración del año anterior y sus certificados) y la app entrega el **borrador correcto del formulario 210** con el impuesto o el saldo a favor. **La regla de oro: la app nunca muestra una cifra falsa.** Si no tiene datos confiables, dice exactamente qué falta y ofrece la forma más rápida de completarlo.

**Terminado** significa que se cumplen las cuatro cosas:
1. Los 4 casos de la sección 6 pasan en pruebas automáticas.
2. Pasan **también** dentro del contenedor Linux de producción (`Dockerfile`).
3. El usuario los recorre en `http://localhost:8000` siguiendo `docs/renta/PROBAR.md`, sin ayuda.
4. **Se trabaja en local.** El despliegue en la nube va por separado (`PROMPT_V24.md`, Bloque 1); no esperes a eso.

---

## 1. LO QUE ESTÁ MAL HOY (revisión externa, reprodúcelo primero)

1. **Resultado peligroso con fotos malas.** Con las 3 fotos del Caso B (giradas e impresas dos veces), en Linux con Tesseract 5:
   - El OCR leyó texto basura (entidades como «SI A AAA A a») y la app igual mostró **«Paga $ 289.321.000» y una sanción de $ 16.891.000**.
   - Sumó $ 627.024.000 en rentas de trabajo, cuando el **Tope 1 del propio reporte dice $ 82.535.904**. Puso el patrimonio en 0, cuando el Tope 2 dice $ 226.543.936.
   - Solo 1 de los 5 topes se validó.
   - La respuesta por defecto «trabajo personal» se aplicó sin confirmación.
   - En la máquina de Claude Code el mismo caso dio «$ 130.000»: **el resultado depende del computador**.
2. **No hay puerta de entrada:** la pantalla Renta⁰³ no tiene dónde subir archivos y solo lista clientes que ya existen.
3. **El usuario no puede entrar en local** porque no recuerda su usuario y contraseña.

---

## 2. PASO 0 — Que el usuario pueda entrar en local

- Crea `restablecer_acceso.bat`. Solo funciona en el propio equipo: borra el usuario actual y las sesiones, y deja la app en «Crear su acceso».
- Ejecútalo tú, y dile al usuario que abra `http://localhost:8000`, cree su usuario y contraseña y guarde los códigos de recuperación.
- **Nunca pidas ni veas la contraseña.**
- No se menciona en la interfaz. Va solo en `docs/MANTENIMIENTO.md` y en tu mensaje.

---

## 3. LA PUERTA DE ENTRADA Y EL FLUJO (3 pasos)

### Paso 1 · «Suelte los documentos» (en Renta⁰³ y en Cliente › Renta)
- Una zona grande en la pantalla **Renta⁰³**: «Suelte la exógena de cualquier persona». También dentro de cada cliente.
- Acepta todo junto y en cualquier orden: Excel, CSV, PDF con texto, PDF escaneado, fotos (`jpg`, `png`, `heic`), el 210 del año anterior (PDF o foto) y certificados.
- La app identifica a la persona por el tipo y número de documento y el nombre del encabezado.
  - Si ya existe (cliente o contribuyente), abre su renta.
  - Si no, muestra **«Crear contribuyente: NOMBRE · C.C. ****8740 · ¿Correcto?»** y, con un clic, lo crea como **contribuyente solo de renta**: persona natural, sin contabilidad, que no se mezcla con los clientes contables.
- Si los documentos son de dos personas distintas, los separa y lo dice.
- La cartera de Renta⁰³ lista a todos (clientes y contribuyentes) con:
  - vencimiento según los dos últimos dígitos del documento, y días que faltan o «vencida hace N días»;
  - estado;
  - impuesto o saldo a favor;
  - ahorro frente a la propuesta de la DIAN.
- Averigua por qué hoy aparece el propio contador como contribuyente y corrígelo si es un error de datos.

### Paso 2 · «Revise» (una pantalla)
1. **Estado de los datos**, arriba y siempre visible:
   - **«Datos completos y validados»** (verde tinta), o
   - **«Faltan datos para calcular»** (ámbar), con la lista exacta de lo que falta y un botón por cada cosa.
2. **Veredicto de obligación:** «Debe declarar por: ingresos, patrimonio, consignaciones, responsable de IVA», o «No está obligado». Se muestra aunque falten otros datos, si los topes están validados.
3. **Cifras grandes** («Paga $ X» o «Le devuelven $ Y», el ahorro frente a la DIAN y el vencimiento) **solo cuando el estado es «completos y validados»**. Mientras no lo sea, en su lugar se lee «Se calculará cuando se completen los datos».
4. **Preguntas** (máximo 5, en lenguaje sencillo). **Las que cambian la cédula o el impuesto no tienen respuesta automática:** la sugerencia aparece marcada, pero el resultado espera a que el contador toque una opción.
5. **«¿Podemos pagar menos?»:** dependientes, intereses de vivienda, medicina prepagada, aportes voluntarios a pensión y AFC, con el ahorro estimado. Cada «sí» pide el certificado y recalcula.
6. **Tabla completa**, plegada y editable con un clic.

### Paso 3 · «Descargue»
Un ZIP con:
- **borrador del 210** en PDF, con las casillas del formulario oficial y la marca «BORRADOR — no válido para presentar»;
- **papel de trabajo** en Excel: cada casilla con su fórmula y sus líneas de origen, incluida la imagen recortada si viene de una foto;
- **resumen para el cliente** en una página.

Después, «Marcar como presentada» pide el número de formulario, la fecha y el PDF presentado. Esos datos alimentan el año siguiente.

**Nada de esto se descarga mientras el estado sea «Faltan datos».** Solo se descarga un «Borrador incompleto», marcado así en cada página.

---

## 4. LECTURA DE DOCUMENTOS: CORRECTA Y REPRODUCIBLE

### 4.1 Orden de preferencia
1. **Excel o CSV** de la DIAN: lectura directa, 100 % confiable.
2. **PDF con texto** de la DIAN: extracción de tablas con `pdfplumber`, 100 % confiable.
3. **Foto o PDF escaneado:** OCR, siempre con verificación.

La pantalla de subida dice, discreta: «El Excel o PDF descargado del portal de la DIAN es lo más rápido y seguro».

### 4.2 OCR que no inventa
- **Reproducible:**
  - la misma versión exacta de Tesseract y del modelo de español en Windows (`.exe`, `iniciar.bat`) y en el `Dockerfile`;
  - el mismo preprocesado: rotación por OSD, detección de la hoja, perspectiva, contraste adaptativo y limpieza de sombras;
  - registra la versión en cada resultado.
- **Reconstrucción por estructura, no por texto suelto:**
  - detecta la cuadrícula de la tabla y lee **celda por celda**, con la columna de valores restringida a dígitos y separadores;
  - la columna «Detalle» se reconcilia con el **catálogo de conceptos de la exógena**: las frases que usa la DIAN, como «Saldo cuentas bancarias», «Cuentas por pagar de clientes (Concepto: 1315)», «Valor total de los movimientos en cuentas», «Otros ingresos (Concepto: 5016)», «Ingresos documentos soporte», «Valor avalúo catastral», «Retención…». Construye ese catálogo en `data/renta/conceptos_exogena.json`;
  - las entidades se reconcilian con un catálogo de entidades frecuentes (bancos, cooperativas, la DIAN, fiduciarias).
- **Una línea solo se vuelve dato si se cumplen las cuatro condiciones:**
  1. el valor tiene formato monetario válido;
  2. el concepto se reconcilió con el catálogo con similitud suficiente;
  3. la confianza de la celda supera el umbral;
  4. la línea es coherente con el uso sugerido.

  Si falla cualquiera, queda **«por verificar»**: el recorte de la imagen al lado, con campos para escribir valor y concepto. **Nunca entra al cálculo sin confirmar.**
- **Texto encimado** (hoja impresa dos veces): intenta separar la capa más nítida dentro de cada celda. Lo que no se pueda separar queda «por verificar».
- **Escritura a mano:** se recorta y no se guarda. Si parece una credencial, se avisa de que no se guardó.

### 4.3 Validación obligatoria contra los topes del encabezado
Para **cada uno** de los topes 1 a 5 (y el 6, responsable de IVA), compara el valor del encabezado con la suma de las líneas que el reporte asigna a ese tope:
- **Cuadra** (diferencia de pocos pesos, con tolerancia documentada): validado.
- **No cuadra:**
  - señala la línea más probable de estar mal leída (la que corrige la diferencia cambiando un dígito, o la que tiene menor confianza);
  - el tope queda «por verificar»;
  - el estado general pasa a «Faltan datos».
- **Faltan líneas** (páginas no subidas o ilegibles): «Parece que falta la página N o hay filas sin leer: la suma da $ X y el encabezado dice $ Y».

**Coherencias que bloquean el resultado:**
- ingresos clasificados en cualquier cédula > Tope 1 + tolerancia;
- patrimonio bruto ≠ Tope 2 (salvo ajustes manuales explicados);
- líneas «por verificar» que afectan alguna casilla.

### 4.4 Entrada rápida cuando la foto no sirve
Si más del 30 % de las líneas quedan «por verificar», se ofrece **«Digitar lo esencial»**: una tabla corta, con la foto al lado y cada fila resaltada mientras se escribe.
- los 6 topes;
- las líneas de ingresos, patrimonio, deudas y retenciones, solo las que el contador marque en la foto.

Meta: un reporte de 3 páginas en menos de 5 minutos. Con eso, la validación de 4.3 corre igual.

---

## 5. CÁLCULO CORRECTO DEL 210

1. **Formulario oficial del año gravable 2025:**
   - casillas, nombres y fórmulas en `data/renta/210_ag2025.json`, tomados del formulario y el instructivo oficiales de la DIAN (cita la resolución);
   - contrasta con la imagen 5 (un 210 real del año gravable 2025);
   - **prueba de que cada casilla tiene su fórmula** y de que las casillas de totales cuadran.
2. **Parámetros del año gravable 2025** en `data/renta/parametros_ag2025.json`, cada uno con su artículo del Estatuto Tributario y la fuente. Verifícalos en el normograma de la DIAN.

| Parámetro | Valor y regla |
|---|---|
| UVT | 49.799 |
| Topes de obligación | 1.400 UVT = 69.718.600; 4.500 UVT = 224.095.500; responsable de IVA |
| Tarifa | Tabla del art. 241 |
| Límites de beneficios | Límite del art. 336 y lo que queda por fuera |
| Renta exenta laboral | 25 % con su tope |
| Deducciones | Dependientes (incluida la de la Ley 2277), intereses de vivienda, medicina prepagada, aportes voluntarios y AFC, 50 % del GMF |
| Factura electrónica | 1 % de compras, con tope y requisitos |
| Rendimientos financieros | Componente inflacionario de 2025 |
| Otras rentas | Ganancias ocasionales y dividendos |
| Anticipo | Regla del año |
| Aproximación | Al múltiplo de mil más cercano |
| Patrimonio líquido | Nunca negativo |

3. **Vencimiento:** calendario oficial del año gravable 2025, por los dos últimos dígitos del documento sin el dígito de verificación. Va del 12 de agosto al 26 de octubre de 2026; por ejemplo, 01–02 vence el 12 de agosto y 21–22 el 27 de agosto. Cárgalo completo desde el decreto y pruébalo con al menos 10 terminaciones.
4. **Sanción por extemporaneidad (art. 641), con todos sus casos:**
   - con impuesto a cargo;
   - sin impuesto a cargo (sobre ingresos brutos);
   - sin ingresos (sobre el patrimonio);
   - sus topes;
   - la **sanción mínima del art. 639 con la UVT del año en que se presenta** (2026: 52.374);
   - las reducciones del art. 640, como opción con sus condiciones.

   Pruebas para cada caso. **Nunca** se calcula una sanción sobre datos «por verificar».
5. **Dos columnas:** «propuesta DIAN» (solo lo reportado por terceros) y «optimizada» (con beneficios con soporte). Diferencia por casilla, con su explicación y su artículo. **Nada agresivo:** lo que depende de un hecho no verificable solo se aplica si el contador lo confirma.

---

## 6. CASOS DE ACEPTACIÓN

Las imágenes reales están en `privado/renta/imagenes/`. Las pruebas que las usan se saltan con aviso si no están. Todo lo que va a git está **anonimizado**.

**Caso A — exógena legible + 210 presentado (imágenes 4 y 5).**
- Entrada: la foto 4 más lo que agregó el contador: rentas no laborales con ingresos de 65.400.000 y costos de 32.800.000, y el 1 % de compras con factura electrónica, que el contador declaró en 48.000.
- Debe dar **exactamente** las casillas del 210 presentado (imagen 5):
  - patrimonio bruto 4.600.000; deudas 52.201.000; patrimonio líquido 0;
  - rentas de capital: 117.000 / 65.000 / 52.000;
  - rentas no laborales: 65.400.000 / 32.800.000 / 32.600.000;
  - rentas exentas y deducciones 48.000;
  - renta líquida gravable 32.604.000;
  - impuesto 0; retenciones 5.000; saldo a favor 5.000.
- Obligada por el Tope 4. Las 2 líneas «NO REGISTRA NO» marcadas.
- Repite el caso con la **misma información en Excel**: mismo resultado.

**Caso B — 3 fotos difíciles (imágenes 1, 2 y 3).**
- **Nunca** muestra «Paga» ni sanción con datos sin validar. Esta prueba falla si aparece cualquier cifra de impuesto o de sanción mientras el estado sea «Faltan datos».
- Debe:
  - identificar que las 3 fotos son de la misma persona y ordenarlas;
  - leer y validar los topes: ingresos 82.535.904; patrimonio 226.543.936; tarjeta de crédito 19.977.892; movimientos 125.053.184; compras 12.910.068; responsable de IVA;
  - dar el veredicto «Debe declarar por ingresos, patrimonio, consignaciones y responsable de IVA»;
  - mostrar el vencimiento: 27 de agosto de 2026, vencida;
  - encontrar el saldo a favor del año anterior (6.275.000) y el patrimonio del año anterior (página 3);
  - agrupar los pagos de una misma empresa en una sola pregunta;
  - ofrecer «Digitar lo esencial».
- **Después de que una prueba automática simule esa digitación** (con los valores de las fotos), el resultado debe ser coherente con los topes, y la sanción debe aparecer calculada según el art. 641.

**Caso C — persona nueva.** Una exógena ficticia de alguien que no es cliente:
- se crea el contribuyente con un clic;
- el borrador sale en menos de 3 minutos;
- el contribuyente no aparece en la lista de clientes contables.

**Caso D — 6 contribuyentes ficticios** con resultados calculados a mano:
- asalariado con dependientes y vivienda;
- independiente con honorarios;
- pensionado;
- rentista con dividendos;
- no obligado;
- declaración vencida sin impuesto a cargo (prueba la sanción sobre ingresos brutos).

**Determinismo:** los casos A, B y D se corren **dos veces en Windows y dos en el contenedor Linux**. Los resultados deben ser idénticos byte a byte en las cifras.

---

## 7. ENTREGA

1. Todo en verde:
   - pruebas, `tsc`, lint, build y `scripts/seguridad.bat`;
   - los 4 casos en Windows y en Docker (si no hay Docker en el equipo, en el workflow de GitHub Actions, con su enlace).
2. **`docs/renta/PROBAR.md`:** un guion de 10 minutos para el usuario:
   - entrar;
   - soltar la exógena de Fanny (foto) y comprobar las casillas contra su 210;
   - soltar las 3 fotos de José y ver que no inventa nada, que pide digitar lo esencial y que con eso calcula;
   - crear una persona nueva;
   - descargar el ZIP.
3. Arranca con `iniciar.bat` y **deja el servidor corriendo** en `http://localhost:8000`.
4. **Mensaje final, corto:**
   - cómo entrar (paso 0);
   - qué dio cada caso;
   - cuánto tarda el flujo;
   - qué tiene que hacer el usuario para la renta de José, que está vencida desde el 27 de agosto;
   - qué queda pendiente, si algo.
