# PROMPT v2.3 — Simple, unificada, con Declaración de renta automática y seguridad de nivel profesional

> Para Claude Code (Opus 5). Guárdalo como `PROMPT_V23.md` en la raíz del repo (reemplaza cualquier versión anterior) y dile:
> **"Lee PROMPT_V23.md completo, mira con atención las 5 imágenes que te pasé, arma tu lista de tareas y ejecútalo de corrido hasta dejar la app corriendo en local."**

---

## 0. CONTEXTO, REGLAS Y MATERIAL

La v2.2.0 está entregada (commit `dafd781`). Se revisó desde fuera: 235 pruebas pasan, y la prueba ciega con un Excel real de un cliente pequeño **funcionó en lo grueso**:
- identificó al cliente;
- detectó ventas, compras y cartera;
- interpretó la columna mal rotulada;
- detectó las fechas copiadas y el inventario insuficiente;
- avisó del margen anómalo.

Quedaron 3 fallos (Fase 1) y varios puntos de seguridad (Fase 6).

### Lo que pide el usuario en esta versión
1. Corregir los fallos de la prueba ciega.
2. **Quitar Parámetros** por completo.
3. **Unificar Clientes y Trabajar.**
4. **Simplificar.** La app está muy completa, pero tiene tantas cosas que el cliente se pierde.
5. **Declaración de renta automática** e **increíblemente fácil**, por cliente y también como sección propia.
6. **Seguridad de nivel profesional**, y que **ninguna clave, comando ni dato interno del backend aparezca nunca en la interfaz**.

### Las 5 imágenes que te pasó el usuario (obligatorio estudiarlas)
Son material real del contador. **Míralas una por una, con zoom, antes de diseñar la Fase 5.**
- Guarda copia en `privado/renta/imagenes/`. Nunca en git: tienen nombres, cédulas y posibles contraseñas.
- Escribe lo que encuentres en `privado/renta/LECTURA_IMAGENES.md`, y una versión **anonimizada** en `docs/v23/LECTURA_IMAGENES.md`.

| # | Qué es | Qué debes encontrar |
|---|---|---|
| 1 | Página 1 del **reporte de información exógena** de un contribuyente (persona natural), **fotografiado** | Encabezado de topes (Tope 1 Ingresos, Tope 2 Patrimonio, Tope 3 Consumo TC, Tope 4 Movimiento, Tope 5 Compras) y la columna «Uso declaración sugerida». Además: **texto encimado** (la hoja se imprimió dos veces), filas **resaltadas en rosa** por el contador, notas **escritas a mano** arriba (cédula, nombre y algo que parece una **contraseña o un usuario**) y abajo («SF: 6.275.000»), y en el margen izquierdo texto de un recetario médico que **no es parte del reporte** |
| 2 | Página 2 del mismo reporte, **girada 90°** | Más filas, muchas resaltadas, texto encimado, y la línea «Número declaraciones IVA … Tope 6: Responsable IVA» de la página 1 |
| 3 | Página 3 del mismo reporte, **girada 90°**, casi vacía | Últimas filas, entre ellas el **patrimonio bruto declarado el año anterior**, un dedo tapando parte de la hoja y un papel ajeno en la esquina |
| 4 | Reporte de exógena de **otra contribuyente**, legible | Tipo y número de documento, nombre, topes, y las columnas entidad · titular (a veces «NO REGISTRA NO») · detalle · valor · uso sugerido (`R29`, `R30`, `R58`, `R132`, «Tope N»). También una nota manuscrita en el encabezado |
| 5 | **Formulario 210 de esa misma contribuyente, ya presentado** (año gravable 2025, con sello de recibido) | El resultado correcto con el que se comprueba la app (sección 5.10) |

Lo que estas imágenes enseñan, y la app debe resolver solo:
- las fotos llegan **giradas, recortadas, con dedos, sombras y texto encimado**;
- el contador **resalta** filas y **escribe a mano** en el papel;
- un mismo reporte viene en **varias páginas**;
- el resultado final que importa es el **formulario 210**.

### Reglas generales
- Trabaja de corrido. Detente solo ante un bloqueo real.
- Control de calidad al cerrar cada fase:
  - todas las pruebas en verde;
  - `tsc` limpio;
  - `lint:diseno` en 0;
  - `npm run build`;
  - las pruebas de seguridad de la Fase 6 (desde que existan);
  - recorrido con Playwright en claro y oscuro, a 1440 y 390 px, sin errores de consola ni de servidor;
  - informe en `docs/v23/fase-N.md`.
- Commits locales por fase. **`git push` solo al final** (Fase 7).
- **El repositorio es público hasta la Fase 7.** Ningún dato real de clientes entra a git: imágenes, documentos, nombres, cédulas, NIT, notas manuscritas. Todo eso va en `privado/`. Las pruebas en git usan datos **anonimizados o ficticios**; las que usan `privado/` se saltan con aviso si no existe.
- **Prueba ciega:** sigue sin entregarse ningún archivo real de contabilidad. Corrige de forma **general**.
- No modifiques las cifras de FANANT enero 2025.

---

## FASE 1 — Fallos de la prueba ciega (corrección general)

**B1 · Cuentas por pagar clasificadas como cartera.** Una hoja cuyo nombre y título dicen «cuentas por pagar», pero cuyo encabezado de columna dice «cliente», se clasificó como cuentas por cobrar. Corrígelo así:
- El **nombre de la hoja y el título del bloque pesan más** que el rótulo de una columna. Palabras como «por pagar», «proveedores», «acreedores» o «deudas» indican cuentas por pagar.
- Si las señales se contradicen, se pregunta: «¿Es lo que le deben al cliente o lo que el cliente debe?».
- El texto de las preguntas de terceros debe decir «compras» y no «ventas» cuando corresponde.

**B2 · Fechas futuras movidas a otro año.**
- El valor por defecto «mismo día y mes del año anterior» **inventó periodos en un año que el archivo no menciona**, con ventas que no ocurrieron. Eso nunca puede ser el valor por defecto.
- Si el título del bloque dice explícitamente un mes y un año futuros, el valor por defecto es **«Dejar fuera: todavía no ha ocurrido»**, y esos registros no entran al cálculo.
- La periodización nunca crea periodos anteriores a la primera fecha real ni de años que el archivo no menciona.

**B3 · Demasiadas preguntas.** Una misma pregunta repetida en muchos bloques produjo más de 25 preguntas.
- Agrupa las iguales en una sola: «En 11 bloques la forma de pago solo aparece en la primera fila. ¿Aplica a todas?», con el detalle plegable y la opción de responder bloque por bloque.
- Lo mismo para las fechas copiadas y las fechas futuras.
- **Meta:** un archivo desordenado típico no genera más de 6 preguntas.

**Pruebas:** al menos 3 archivos nuevos en `backend/tests/archivos_variados/` que reproduzcan estos patrones de forma genérica, con cifras esperadas calculadas a mano.

---

## FASE 2 — Quitar Parámetros al 100 %

1. Elimina la pantalla `Parametros.tsx`, su ruta, su entrada en la navegación, los enlaces, los textos que la mencionen y el endpoint `PUT /api/parametros/{anio}`. `/parametros` redirige al Tablero.
2. Los valores legales viven **dentro de la aplicación**, en `data/parametros_legales.json`, versionados por año y con la fuente oficial de cada uno. Ya están verificados:

| Año | SMMLV | Auxilio de transporte | UVT | Fuente |
|---|---|---|---|---|
| 2025 | 1.423.500 | 200.000 | 49.799 | Decretos 1572 y 1573 de 2024 · Resolución DIAN 000193 de 2024 |
| 2026 | 1.750.905 | 249.095 | 52.374 | Decretos 1469 y 1470 de 2025 · Resolución DIAN 000238 de 2025 |

   2025 **se mantiene**: FANANT, los clientes de demostración y la renta del año gravable 2025 lo usan.
3. **Panel «Sistema»** en el menú del avatar (CC). Solo muestra:
   - «En la nube · conectado» o «Sin conexión»;
   - la versión;
   - cambiar contraseña;
   - verificación en dos pasos;
   - sesiones abiertas;
   - eliminar clientes de demostración.

   **Nunca** muestra el ID del proyecto, el motor de base de datos, URLs, rutas de archivos, variables de entorno ni nombres de comandos.
4. Si se usa un año sin valores (por ejemplo, 2027), la app **no inventa nada**: una tarea en el Tablero dice «Faltan los valores legales de 2027». El cálculo de nómina de ese año queda bloqueado con un mensaje claro. La instrucción técnica para actualizarlos va en `docs/MANTENIMIENTO.md`, no en la interfaz.
5. Pruebas: la ruta ya no existe; nómina 2025 y 2026 con sus valores; año sin valores → mensaje claro.

---

## FASE 3 — Unificar Clientes y Trabajar

### 3.1 Navegación final
`Tablero⁰¹ · Clientes⁰² · Renta⁰³`. **Trabajar desaparece.** `/trabajo` redirige a Clientes, y `/trabajo?cliente=X` a ese cliente.

### 3.2 El cliente es un solo lugar: su expediente
- **Si ya tiene periodos calculados:** se abre directo en el **último periodo**, con todo listo, como hoy en el resultado de Trabajar:
  - balance de prueba, balance definitivo y estados financieros;
  - libro diario y libro mayor;
  - inventario y nómina;
  - descargas en Excel y PDF.

  **No se vuelve a pedir ningún archivo.** «Subir archivos» queda como botón secundario, para un periodo nuevo o para reemplazar uno.
- **Si no tiene nada:** zona de subida grande, con el mismo flujo de pasos de Trabajar (subir → preguntas → resultado), dentro del cliente.
- Una sola vista de resultados para lo recién calculado y lo guardado: unifica `Resultados.tsx` y `ResultadoGuardado.tsx` en un componente.

### 3.3 El error de navegación que reportó el usuario
Estaba en Clientes › Estados financieros › Estado de resultados. Al tocar otro mes, **la vista saltaba a otro lugar** y se perdía. Corrígelo así:
- **Selector de periodo único**, fijo arriba del expediente («Enero 2025 ▾», con flechas ‹ ›).
- **Cambiar el periodo conserva la vista exacta** y la posición de desplazamiento.
- La URL lo refleja todo (`/clientes/:id?periodo=2025-01&vista=resultados`).
- **Prueba en Playwright:** recorrer los 12 meses de un cliente de demostración desde el estado de resultados, el balance definitivo y el libro diario. La vista nunca cambia sola.

---

## FASE 4 — Simplificar: que nadie se pierda

1. **Expediente del cliente:** máximo **5** secciones:
   - Resumen;
   - Contabilidad;
   - Renta;
   - Archivos y actividad;
   - Datos del cliente.
2. **Dentro de Contabilidad**, una **lista lateral corta y agrupada** en lugar de 13 pestañas (en móvil, un desplegable):
   - *Estados financieros:* situación, resultados, patrimonio, flujo;
   - *Balances:* prueba, ajustes, hoja de trabajo, definitivo;
   - *Libros:* diario, mayor y balances, cuentas T;
   - *Detalle:* inventario, nómina, alertas.
3. **Prohibidas las pestañas dentro de pestañas.**
4. **Lo avanzado, plegado** («Ver detalle»): auditoría del archivo, hoja de trabajo, cuentas T, interpretaciones del importador.
5. **Un botón principal por pantalla.** Sin cifras repetidas. Cada tarjeta lleva un título y como máximo una línea de texto.
6. **Inventario antes y después**, en el informe: por pantalla, cuántas pestañas, botones, tarjetas y bloques de texto. Meta: **al menos 40 % menos**, sin perder ninguna función.

---

## FASE 5 — Declaración de renta automática e increíblemente fácil (personas naturales, formulario 210)

### 5.1 Qué es y qué no es
- La app **prepara sola el borrador completo** de la declaración:
  - si debe declarar y por qué tope;
  - cada casilla del 210, con su fuente;
  - los beneficios legales aplicados;
  - el impuesto o el saldo a favor;
  - la comparación con la propuesta de la DIAN.
- **No la presenta**: no hay una vía pública para hacerlo por software y requiere la firma electrónica del contribuyente. El contador revisa y la diligencia en el portal de la DIAN. La app lo dice con claridad.

### 5.2 La experiencia: tres pasos, nada más
La meta es que el contador vaya **de soltar las fotos al borrador en menos de 5 minutos y con 10 clics o menos**. Mídelo en Playwright con los casos de 5.10.

**Paso 1 · «Suelte todo».**
- Se suelta lo que se tenga del cliente, en cualquier orden y formato, todo junto: fotos del celular (giradas, recortadas, de varias páginas), PDF del portal de la DIAN, Excel, la declaración del año anterior, certificados.
- La app, sola:
  1. endereza cada imagen y recorta la hoja;
  2. reconoce qué es cada documento y **de quién es** (número de documento y nombre impresos en el encabezado);
  3. **ordena las páginas** y une el reporte en una sola tabla;
  4. quita las filas duplicadas;
  5. comprueba que la suma de las filas da los totales de los topes del encabezado.
- Si un archivo es de otro contribuyente, lo dice y lo separa.

**Paso 2 · «Revise en una pantalla».** De arriba abajo:
1. **Un veredicto grande:** «Debe declarar — supera los topes de ingresos, patrimonio y consignaciones, y fue responsable de IVA» (o «No está obligado»).
2. **Tres cifras grandes:**
   - **«Paga $X»** o **«Le devuelven $Y»**;
   - **«Ahorro frente a la propuesta de la DIAN: $Z»**;
   - **«Vence el 26 de agosto · vencida hace 43 días»**, o «faltan 6 días».
3. **«Por confirmar» (máximo 5 preguntas, en lenguaje sencillo, con un toque).** Ejemplos:
   - «Estos $ 49.276.700 que le pagó la misma empresa en 8 documentos soporte, ¿son por su trabajo personal o por venta de productos?» (define la cédula y los beneficios).
   - «Estas 2 cuentas no están a nombre del contribuyente como titular principal. ¿Las incluimos?»
   - «Hay un saldo a favor del año anterior de $ 6.275.000. ¿Lo usamos?»
4. **«¿Podemos pagar menos?»** Preguntas de sí/no con el ahorro estimado al lado:
   - «¿Tiene hijos o personas a cargo? Ahorro posible: hasta $ …»;
   - «¿Paga crédito de vivienda?»;
   - «¿Paga medicina prepagada?»;
   - «¿Hizo aportes voluntarios a pensión o AFC?»

   Cada «sí» pide la foto del certificado y recalcula al instante.
5. **Detalle plegado:** la tabla completa clasificada, editable con un clic.

**Paso 3 · «Descargue».** Un botón genera:
- el **borrador del 210** en PDF;
- el **papel de trabajo** en Excel;
- el **resumen para el cliente** (una página).

Después, «Marcar como presentada» pide el número de formulario y la fecha.

### 5.3 Lectura de imágenes (OCR) robusta
- Tesseract en español (`pytesseract`), incluido en el `.exe` y en `iniciar.bat`.
- **Preprocesado:** detección y corrección de rotación, detección de la hoja y corrección de perspectiva, contraste adaptativo y eliminación de sombras.
- **Detección de la tabla:** líneas y celdas, columnas entidad · titular · detalle · valor · uso.
- **Solo se lee la tabla y su encabezado impreso.** Los márgenes (como el texto de un recetario) se ignoran.
- **Texto encimado** (hoja impresa dos veces): dentro de cada celda se separa la capa más nítida y legible. Si no se puede, la fila queda en ámbar con «Texto superpuesto: confirme este valor». Si es la mayoría de la hoja: «Esta hoja se imprimió dos veces; para mayor seguridad descargue el reporte en PDF o Excel del portal de la DIAN». Aun así, se sigue con lo que se pueda leer.
- **Valores:** se validan con el formato monetario (`$ 1,234,567.00`) y con la suma de los topes. Si la suma no cuadra, se señala la fila más probable de estar mal leída (por ejemplo, la que corrige la diferencia cambiando un solo dígito).
- **Resaltado del contador:** las filas resaltadas se detectan y se muestran como «marcadas en el papel». Es una pista visible, no una decisión.
- **Escritura a mano:** se detecta y **nunca se guarda ni se muestra completa**. Si parece una contraseña, un usuario o un correo (por ejemplo, algo como «nombre1977@»), se oculta y se avisa: «La foto tiene datos de acceso escritos a mano; no se guardaron. Recomiende al cliente cambiar esa contraseña». Las cifras manuscritas útiles (como «SF: 6.275.000») se ofrecen como sugerencia para confirmar, nunca como dato.
- **Pantalla de verificación:** la imagen al lado de cada valor leído, con su confianza. Nada leído por OCR entra sin que el contador lo vea; los valores seguros se confirman en bloque con un clic.

### 5.4 Clasificación
Cada línea del reporte se clasifica en:
- **topes** de obligación (incluido el **Tope 6: responsable de IVA**);
- **patrimonio bruto** (cuentas, inversiones, inmuebles, vehículos) y **deudas**;
- **ingresos por cédula:** rentas de trabajo, de trabajo no laborales (honorarios), de capital, no laborales, pensiones, dividendos, ganancias ocasionales;
- **ingresos no constitutivos;**
- **costos y deducciones;**
- **retenciones;**
- **compras con factura electrónica;**
- **información del año anterior** (patrimonio bruto declarado, saldo a favor, anticipo);
- **solo informativo.**

Reglas:
- Primera señal: el **renglón que sugiere la DIAN** (`Rnn`). Tus reglas lo validan; si no coinciden, se marca.
- **Agrupa por pagador:** «la misma empresa le pagó $ X en N documentos» es una sola decisión, no N.
- **Marca:**
  - duplicados;
  - líneas donde el contribuyente no es el titular principal («NO REGISTRA NO»);
  - consignaciones muy superiores a los ingresos declarados («la DIAN cruza este dato»);
  - facturación electrónica emitida que no está en los ingresos;
  - bienes con avalúo (pedir el costo fiscal si se tiene);
  - **diferencia patrimonial** contra el patrimonio del año anterior (posible renta por comparación patrimonial).
- Cada línea se reclasifica con un clic y todo se recalcula. El papel de trabajo guarda **de dónde salió cada peso**: documento, página, fila e imagen recortada.

### 5.5 Cálculo del formulario 210
- **Diseño del formulario versionado por año gravable** (`data/renta/210_ag2025.json`), tomado del **formulario oficial y su instructivo** para el año gravable 2025. Búscalos en la web y cita la resolución.
  - Contrasta las casillas con la **imagen 5**, que es un 210 real del año gravable 2025 (por ejemplo, patrimonio bruto, deudas y patrimonio líquido en 29–31; retenciones en 132; saldo a favor en 137; 1 % de compras con factura electrónica en 28).
  - No inventes casillas. Lo que no puedas confirmar va a `docs/v23/SUPUESTOS_RENTA.md`.
- **Parámetros tributarios versionados** (`data/renta/parametros_ag2025.json`), **cada uno con su artículo del Estatuto Tributario y la fuente oficial**, verificados en el normograma de la DIAN:
  - UVT 2025 (49.799);
  - topes de obligación (1.400 UVT = $ 69.718.600; 4.500 UVT = $ 224.095.500; responsable de IVA);
  - tabla del art. 241;
  - límite general de rentas exentas y deducciones (art. 336) y los beneficios por fuera de él;
  - renta exenta laboral del 25 % con su tope;
  - dependientes, incluida la deducción adicional de la Ley 2277 de 2022;
  - intereses de vivienda;
  - medicina prepagada;
  - aportes voluntarios y AFC;
  - 50 % del GMF;
  - 1 % de compras con factura electrónica, con tope y requisitos;
  - componente inflacionario del año (decreto);
  - ganancias ocasionales;
  - dividendos;
  - anticipo.

  Todo debe tener pruebas con valores calculados a mano.
- **Aproximación** de los valores al **múltiplo de mil más cercano**, según la norma vigente de aproximación en las declaraciones. Patrimonio líquido nunca negativo.
- **Vencimientos:** calendario de personas naturales del año gravable 2025 (del 12 de agosto al 26 de octubre de 2026, por los dos últimos dígitos del NIT), tomado del decreto. Si ya venció, la **sanción por extemporaneidad estimada**, con su norma.

### 5.6 Optimización legal: por qué la propuesta de la DIAN suele salir más cara
La propuesta de la DIAN usa solo lo que reportaron terceros y deja por fuera beneficios que requieren soportes que ella no tiene. La app:
1. Calcula **dos columnas**: **propuesta DIAN** y **declaración optimizada**, con la diferencia casilla por casilla y su explicación en una línea.
2. Aplica **todos los beneficios legales con soporte**, respetando sus topes:
   - ingresos no constitutivos (aportes obligatorios, componente inflacionario);
   - 25 % exento;
   - dependientes;
   - intereses de vivienda;
   - medicina prepagada;
   - aportes voluntarios;
   - GMF;
   - 1 % de compras con factura electrónica;
   - costos y gastos de las rentas no laborales con soporte (desde la contabilidad del cliente en la app, si existe);
   - retenciones;
   - saldo a favor anterior.
3. Elige la **cédula correcta** de cada ingreso y explica su efecto.
4. Lista **«Documentos que bajarían el impuesto»**, con el ahorro estimado de cada uno.
5. **Nada ilegal ni agresivo.** Cada beneficio cita su artículo. Lo que dependa de un hecho no verificable se aplica solo si el contador lo confirma.

### 5.7 Salidas
- **Borrador del 210** en PDF, con la numeración de casillas del oficial y la marca «BORRADOR — no válido para presentar».
- **Papel de trabajo** en Excel: cada casilla con su fórmula y sus líneas de origen.
- **Resumen para el cliente** en lenguaje sencillo: ¿debe declarar?, ¿paga o le devuelven?, ahorro frente a la DIAN, documentos faltantes y fecha límite.
- Registro de la presentación (número, fecha y PDF). Esos valores alimentan el año siguiente.

### 5.8 Dónde vive
- **Renta⁰³ (cartera):** por persona natural, la siguiente información, ordenable y filtrable:
  - año gravable;
  - si está obligado y por qué;
  - vencimiento según su NIT y días que faltan o «vencida»;
  - estado (`sin información` → `borrador` → `revisada` → `presentada`);
  - impuesto o saldo a favor;
  - ahorro frente a la DIAN.
- **Dentro del cliente:** la sección Renta, por año gravable.
- **Tablero:** una tarea por cada declaración que vence en 15 días o menos o ya venció sin presentarse.
- **Personas jurídicas (formulario 110):** no se hace ahora. Su sección Renta lo dice y queda anotado en `docs/PROPUESTAS.md`.
- **Datos:** migración `005_renta.sql` con RLS, historial de versiones y endpoints `/api/renta/*` protegidos.

### 5.9 Contribuyentes ficticios para pruebas
Crea al menos 6, con resultados calculados a mano:
- asalariado con dependientes y vivienda;
- independiente con honorarios;
- pensionado;
- rentista de capital con dividendos;
- no obligado;
- uno con fotos sintéticas difíciles generadas por ti: tabla girada, con perspectiva, poco contraste, texto encimado, resaltados y anotaciones a mano.

### 5.10 Casos con respuesta conocida (de las imágenes)
**Caso A — imágenes 4 y 5** (en git, **anonimizado**: «Contribuyente A», cédula ficticia, comercio al por menor, año gravable 2025):
- **Entrada:** el reporte de la imagen 4. Transcríbelo desde la imagen y verifica cada cifra.
  - Sumas de referencia: Tope 2 = 4.600.014 (cuatro líneas R29), deudas R30 = 52.201.487 (seis líneas), R58 = 117.144, R132 = 4.920.
  - En la transcripción preliminar del revisor, las tres líneas de movimientos suman 93.121.227, frente al total del encabezado de 93.121.224: **confirma en la imagen cuál dígito está mal leído**. La prueba usa lo que diga la imagen.
  - Lo que agregó el contador por conocer el negocio (no está en la exógena): ingresos de rentas no laborales 65.400.000; costos 32.800.000; 1 % de compras con factura electrónica, declarado en 48.000 (la app propone el máximo permitido con requisitos y deja ajustarlo).
- **Salida esperada (debe coincidir con la imagen 5):**

| Concepto | Valor |
|---|---|
| Patrimonio bruto | 4.600.000 |
| Deudas | 52.201.000 |
| Patrimonio líquido | 0 |
| Rentas de capital: ingresos | 117.000 |
| Rentas de capital: ingresos no constitutivos (componente inflacionario) | 65.000 |
| Rentas de capital: renta líquida | 52.000 |
| Rentas no laborales: ingresos | 65.400.000 |
| Rentas no laborales: costos | 32.800.000 |
| Rentas no laborales: renta líquida | 32.600.000 |
| Rentas exentas y deducciones imputables | 48.000 |
| Renta líquida gravable | 32.604.000 |
| Impuesto | 0 |
| Retenciones | 5.000 |
| Saldo a favor | 5.000 |

  - Obligada por el **Tope 4**.
  - Las 2 líneas «NO REGISTRA NO» deben quedar marcadas.
  - Aviso de que las consignaciones (≈ 93 millones) superan con mucho la facturación electrónica (≈ 4,8 millones).

**Caso B — imágenes 1, 2 y 3** (solo en `privado/`; la prueba se salta si no está). Es la **prueba de robustez del OCR**:
- Las tres fotos se sueltan juntas y en desorden. La app debe identificar que son del mismo contribuyente y ordenar las páginas.
- Debe leer los topes:
  - ingresos 82.535.904;
  - patrimonio 226.543.936;
  - consumo con tarjeta 19.977.892;
  - movimiento 125.053.184;
  - compras 12.910.068;
  - más el Tope 6 (responsable de IVA).
- **Veredicto esperado:** obligado por ingresos (≥ 69.718.600), patrimonio (≥ 224.095.500), consignaciones y por ser responsable de IVA.
- Debe encontrar el **saldo a favor** (6.275.000) y el **patrimonio del año anterior** que aparece en la página 3.
- Debe **agrupar los pagos de una misma empresa** en una sola pregunta.
- **No debe guardar la nota manuscrita del encabezado** que parece credencial; debe avisar.
- Las filas que no se puedan leer por el texto encimado quedan en ámbar. Reporta qué porcentaje de filas leyó con confianza alta.

---

## FASE 6 — Seguridad de nivel profesional

Escribe primero `docs/SEGURIDAD.md`: un modelo de amenazas corto (qué se protege, de quién, por dónde podrían entrar) y la lista de controles, con su relación con OWASP ASVS nivel 2. Luego implementa. **Cada control lleva una prueba automática.**

### 6.1 Ningún secreto ni dato interno a la vista
1. **Pantalla de ingreso:** quita cualquier mención a comandos, archivos o rutas (hoy dice `python backend/crear_usuario.py`). Nada técnico en ninguna pantalla.
2. **Primer uso desde el navegador**, solo si no existe usuario y solo desde el mismo equipo:
   - pantalla «Crear su acceso» con usuario y contraseña;
   - se muestran **10 códigos de recuperación** una sola vez, con opción de descargarlos o imprimirlos;
   - en la base solo queda el hash de cada código.
3. **«¿Olvidó la contraseña?»** pide un código de recuperación y deja crear una nueva. Sin terminal.
4. **Ejecutable:**
   - sin ventana negra (`console=False`), con un ícono en la bandeja del sistema (Abrir · Cerrar);
   - no pide contraseñas por consola;
   - no muestra rutas ni configuración.
5. **Secretos del equipo** (conexión a la base, clave de sesión): en el **Administrador de credenciales de Windows** (DPAPI, librería `keyring`), no en archivos de texto plano.
   - La clave de sesión se genera sola.
   - `.env` queda solo para desarrollo y nunca se empaqueta.
   - Migra los secretos que haya en texto plano y borra el archivo.
6. **Errores:** la interfaz muestra un mensaje humano y un **código de incidente** (por ejemplo `INC-7F3A`). El detalle técnico va solo al registro local, nunca a la pantalla. Quita el «Detalle técnico» visible.
7. **`/api/salud` sin sesión** responde solo `{ok, version}`. El resto del diagnóstico requiere sesión.
8. **Documentación de la API** (`/docs`, `/redoc`, `/openapi.json`) **desactivada**. Hoy responden 200 sin sesión. Solo se activan con una variable de desarrollo.
9. **Registros sin datos sensibles:** un filtro elimina de todos los registros las contraseñas, cookies, cadenas de conexión, tokens, y enmascara cédulas y NIT (`****8740`).

### 6.2 Sesión y acceso
- **Contraseñas con Argon2id.** Mínimo 12 caracteres, revisada contra una lista de contraseñas comunes, y con un medidor de fortaleza. Migra los hashes bcrypt existentes al ingresar.
- **Verificación en dos pasos (TOTP)** opcional, activable desde Sistema con un código QR (`pyotp`), con sus códigos de recuperación.
- **Sesiones en el servidor** (tabla), en lugar de solo la cookie firmada:
  - se rotan al ingresar;
  - expiran por inactividad (30 min) y por tiempo absoluto (12 h);
  - «cerrar todas las sesiones» desde Sistema;
  - **al cerrar sesión, la cookie anterior deja de servir.**
- **Reautenticación** antes de acciones destructivas o sensibles: eliminar un cliente, eliminar los clientes de demostración, restaurar una versión, cambiar la contraseña, desactivar la verificación en dos pasos, descargar todo.
- **Límite de intentos** en el ingreso (ya existe) y **límite de solicitudes** en toda la API, con valores más estrictos en subidas, cálculos y OCR.
- **Protección CSRF:** verificación de `Origin` y `Referer` y un token en toda petición que modifique datos.

### 6.3 Endurecimiento HTTP
- **Encabezados de seguridad en todas las respuestas:**
  - CSP estricta (`default-src 'self'`, sin scripts en línea, o con hashes si el build los necesita);
  - `frame-ancestors 'none'`;
  - `X-Content-Type-Options: nosniff`;
  - `Referrer-Policy: no-referrer`;
  - `Permissions-Policy` restrictiva;
  - HSTS cuando haya HTTPS.
- `Cache-Control: no-store` en toda respuesta con datos de clientes.
- **Protección contra DNS rebinding** (crítica en una app local): validar el encabezado `Host` (`TrustedHostMiddleware`, solo `localhost` y `127.0.0.1` y los dominios configurados) y el `Origin`. Sigue escuchando solo en `127.0.0.1`.
- CORS cerrado a los orígenes configurados.

### 6.4 Archivos subidos (la superficie de ataque más grande)
- **Tipo por contenido** (firma de bytes), no por extensión.
- **Bombas de compresión:** `.xlsx` y `.docx` son ZIP. Limita el tamaño descomprimido, el número de entradas y la proporción de compresión antes de abrirlos.
- **XML seguro:** `defusedxml` donde aplique; entidades externas desactivadas (XXE).
- **Imágenes:** límite de píxeles de Pillow; rechaza imágenes desproporcionadas.
- **Límites en PDF:** páginas, tamaño y tiempo.
- **Análisis aislado:** cada archivo se procesa en un **proceso separado con tiempo límite y memoria limitada**, para que un archivo malicioso no cuelgue ni tumbe el servidor.
- **Nombres:** los archivos se guardan con nombres aleatorios, sin usar el nombre original (evita recorrer rutas), con permisos restringidos y **cifrados en disco** (AES-GCM con la clave del almacén de credenciales). Se borran solos a las 8 horas.
- **Macros:** los `.xlsm` nunca ejecutan nada; se avisa que contienen macros.
- **Fotos:** se eliminan los metadatos (EXIF, ubicación GPS) al recibirlas. La imagen original se borra después de la verificación, salvo que el contador decida conservarla (cifrada).

### 6.5 Archivos que la app genera
- **Inyección de fórmulas en Excel y CSV:** todo texto que venga de datos del usuario y empiece con `=`, `+`, `-`, `@`, tabulador o retorno se escribe como texto (prefijo `'`). Las fórmulas propias de la app no se tocan.
- PDF sin metadatos internos (rutas, usuario del equipo).
- Las descargas quedan en la bitácora (quién, qué y cuándo).

### 6.6 Base de datos y datos personales
- **Rol de mínimo privilegio** para la app en Supabase: solo las operaciones que usa, sobre sus tablas, sin crear ni borrar tablas. Las migraciones usan otro rol. Conexión SSL con verificación del certificado (`verify-full`).
- **Copias de seguridad:** exportación diaria cifrada (AES-GCM) a una carpeta local, con retención de 30 días y una prueba de restauración automatizada. Lo mismo para el SQLite del ejecutable.
- **Ley 1581 de 2012 (datos personales):**
  - cédulas y NIT enmascarados en listas y registros, completos solo donde hacen falta;
  - «eliminar cliente» borra también sus archivos, imágenes, historial y declaraciones;
  - política de retención documentada en `docs/SEGURIDAD.md`.
- **Bitácora de seguridad:** ingresos, fallos, cambios de contraseña, verificación en dos pasos, descargas, eliminaciones y restauraciones, con fecha e IP. En Sistema se ve un aviso si hubo intentos fallidos recientes.

### 6.7 Cadena de suministro y repositorio
- Dependencias **fijadas con hashes** (`pip-tools --generate-hashes`, `npm ci` con lockfile).
- `scripts/seguridad.bat` (y la misma revisión en GitHub Actions en cada push), que corre:
  - `pip-audit` y `npm audit`, sin vulnerabilidades altas;
  - `bandit` y `semgrep`;
  - `gitleaks`, con reglas adicionales para cédulas, NIT, cadenas de conexión y claves.
- Dependabot activado.
- Hook de pre-commit con gitleaks y la regla «nada de `privado/`».

### 6.8 Pruebas de seguridad (automáticas)
- Recorre **todas las rutas registradas**: sin sesión → 401, salvo las explícitamente públicas.
- `/docs` y `/openapi.json` → 404.
- `/api/salud` → solo `{ok, version}`.
- Petición con `Host` o `Origin` ajenos → rechazada.
- Petición que modifica datos sin token CSRF → rechazada.
- Cookie vieja después de cerrar sesión → 401.
- Expiración por inactividad.
- Reautenticación exigida en acciones destructivas.
- Bomba ZIP, XML con entidad externa, imagen gigante y PDF malicioso → rechazados dentro del tiempo límite, sin tumbar el servidor.
- Nombre de archivo con `../` → inofensivo.
- Celda con `=HYPERLINK(...)` → exportada como texto.
- Ningún secreto ni ruta en las respuestas de error.
- Encabezados de seguridad presentes.
- Registros sin cédulas ni contraseñas.
- Copia de seguridad cifrada que se restaura correctamente.
- Si hay Docker, un escaneo base de **OWASP ZAP** contra `localhost`, con el informe en `docs/v23/`.

---

## FASE 7 — Verificación final, repositorio privado y despliegue local

1. **Revisión completa** con Playwright en claro y oscuro, a 1440 y 390 px: todas las pantallas, botones y descargas, cero errores. Mide el tiempo y los clics del flujo de renta (Paso 1 → 3) con los casos A y B.
2. **Cifras:** FANANT intactas, caso A exacto, caso B dentro de lo esperado.
3. **`scripts/seguridad.bat`** en verde.
4. **Ejecutable:** reempaquétalo (OCR incluido, sin consola, secretos en el almacén de Windows) y pruébalo con un perfil vacío: primer uso → crear acceso → códigos de recuperación → ingresar.
5. **Repositorio:**
   - **Respaldo completo** (`git clone --mirror`) en `privado/respaldo-repo/`.
   - Si `gh` está autenticado: `gh repo edit --visibility private --accept-visibility-change-consequences`. Si no, deja los pasos exactos en el mensaje final.
   - Con el repositorio ya privado, limpia el historial de los archivos con datos personales (`git filter-repo`, con la lista de `docs/v22/ENTREGA.md` más lo nuevo) y haz `git push --force`. Verifica con gitleaks que el historial quedó limpio.
6. **Versión `v2.3.0`:** commit y push. Arranca con `iniciar.bat` en `http://localhost:8000` y **deja el servidor corriendo**.

## MENSAJE FINAL EN EL CHAT (corto)
1. URL, y qué ve el usuario la primera vez (crear acceso y códigos de recuperación).
2. Estado: pruebas, `tsc`, lint, build y seguridad.
3. Navegación antes y después, y cuánto se simplificó.
4. Renta:
   - cómo hacer una declaración en 3 pasos;
   - si los casos A y B dieron lo esperado;
   - tiempo y clics medidos;
   - porcentaje de filas que el OCR leyó con confianza alta en las fotos difíciles.
5. Seguridad: los controles aplicados y lo que quedó pendiente.
6. Repositorio: ¿quedó privado y con el historial limpio?
7. Qué hacer cuando cambie el año.
