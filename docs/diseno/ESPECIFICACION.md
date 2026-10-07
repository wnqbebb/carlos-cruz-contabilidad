# Especificación de diseño v2.1 (texto entregado por el usuario el 2026-10-06)

Copia literal. Las decisiones posteriores del usuario (rejilla 8 %, dos azules, preloader sí) están en LECTURA_REFERENCIAS.md y en los informes de fase.

0. LEE ESTO PRIMERO — Por qué las instrucciones de diseño anteriores no se aplicaron

El cliente ha pedido cambios de diseño varias veces y el resultado visual casi no cambia. Antes de diseñar nada, diagnostica y corrige estas causas probables, y reporta cuál era la real:

Build desactualizado. La app se abre en http://localhost:8000, que es el backend sirviendo el frontend compilado. Si editas src/ y no ejecutas el build (o el backend sirve otra carpeta dist/), el cliente ve el diseño viejo. Verifica qué carpeta sirve FastAPI, recompila después de cada fase y agrega en el pie de página v2.1.0 · build <hash corto> · <fecha-hora> para que el cliente confirme que ve la versión nueva.
Estilos viejos que ganan. Busca CSS global, index.css, tailwind.config, clases sueltas (bg-indigo-*, from-blue-*, text-green-*), estilos inline y variables antiguas que sobrescriben los tokens nuevos. Elimínalos; no los dejes "por si acaso".
Instrucciones vagas. Este documento no usa adjetivos sueltos: da valores exactos (hex, px, ms, fuentes). Si algo no está especificado, pregunta en vez de inventar.
No había verificación visual. Desde ahora ninguna pantalla se da por terminada sin capturas de pantalla revisadas por ti mismo contra las referencias (sección 12).
Reglas inviolables
No modifiques lógica de negocio, cálculos, endpoints, modelos, conexión a Supabase ni contratos de api.ts. Las 111 pruebas deben seguir verdes y TypeScript limpio al final de cada fase.
Solo cambias: estilos, componentes de presentación, layout, microcopy, animación, iconografía, estados vacíos/carga/error y accesibilidad.
No inventes funcionalidades ni "mejoras" que no estén aquí. Si crees que algo falta, anótalo en docs/diseno/PROPUESTAS.md y sigue.
Una pantalla a la vez, en el orden de la sección 11.
1. EL OBJETIVO EN UNA FRASE

Que el contador Carlos Cruz abra la app frente a su cliente y el cliente piense "esto es de otro nivel": un despacho contable con estética editorial suiza (tipografía grande y precisa, rejilla visible, papel, tinta) y materiales táctiles (carpetas, cristal, sombras finas), sin perder la seriedad de un documento contable. Nivel Awwwards en la presentación; nivel herramienta profesional en el trabajo diario.

Dos registros de diseño, siempre separados:

Escaparate (preloader, encabezado del Tablero, ficha del cliente, estados vacíos, estados financieros listos): expresivo, tipografía gigante, animación con carácter.
Taller (tablas, mapeo de cuentas, ajustes, formularios): sobrio, denso, rápido, animación casi invisible. Se usa ocho horas seguidas.
2. REFERENCIAS VISUALES — qué tomar de cada una (obligatorio usarlas todas)

Copia las imágenes con estos nombres (en el orden en que fueron enviadas):

Archivo original	Guardar como	Qué tomar EXACTAMENTE	Dónde se aplica
…163004.png (tarjeta negra con pestaña)	ref-01-carpeta-negra.png	Forma de carpeta con pestaña inclinada arriba a la derecha, tinta 
#1A1A1A, flecha ↗ arriba a la derecha, titular blanco semibold + texto gris claro, halo cálido muy tenue alrededor	Componente Expediente (tarjeta héroe del KPI principal, tarjeta de cliente, accesos de navegación)
…162807.png (cartel rojo de la vaca)	ref-02-cartel-suizo.png	Tipografía display gigante, interlineado 0.88, todo en un bloque compacto; texto pequeño de créditos abajo a la derecha; grano de papel	Titulares de página, número héroe del Tablero, palabra "CUADRA." del preloader. El rojo cartel se reserva para pérdidas/descuadres
…162903.png ("What We've Built")	ref-03-casos-estudio.png	Etiqueta de sección 005 • CASE STUDIES (índice + punto + mayúsculas pequeñas), fila de métricas grandes con pie diminuto (+40% / Demo Booking), botón píldora negro, tarjetas en carrusel con la vecina asomando	Encabezados de sección, filas de indicadores, botón primario, carrusel de clientes/periodos
…162919.png (esferas de gradiente)	ref-04-esferas.png	Esferas de color difuminadas sobre gris claro, metadatos editoriales en esquinas (ULR — 000, fecha 12 — 24 — 2017)	Avatar único por cliente (esfera generada desde el NIT), aurora de fondo del Escaparate, metadatos de fichas
…162925.png (10 efectos)	ref-05-materiales.png	Fondo papel cálido 
#F2EFE9; sistema de materiales: drop shadow, inner shadow, glow, glass, texture overlay	Fondo general y los 5 materiales de la sección 4.4 (no usar los 10: neumorfismo, bisel y satén quedan prohibidos)
…162934.png (Future⁰¹ / Now⁰²)	ref-06-interruptor-suizo.png	Interruptor segmentado píldora negra/blanca con superíndices ⁰¹ ⁰²; textos diminutos alineados a una rejilla de 4 columnas en el borde superior e inferior	Selectores (Expedientes/Tabla, Mensual/Anual, Débito/Crédito), meta-encabezado de cada página, navegación con índices
…162950.png (Frosted/Clear/Blur)	ref-07-cristal.png	Cristal esmerilado con borde claro de 1 px y texto blanco encima de una imagen	Solo superficies flotantes con algo detrás: paleta ⌘K, barra de herramientas flotante de estados financieros, modales, preloader
…162955.png (moodboard)	ref-08-rejilla-moodboard.png	Rejilla de líneas finas visible en el lienzo, palabras con tracking muy negativo, subrayados azul tinta bajo etiquetas, tachado, carpeta azul tipo macOS	Lienzo de fondo, enlaces subrayados, ícono de carpeta en estados vacíos
image.png (1ª)	actual-01-tablero.png	Estado actual — lo que hay que superar	—
image.png (2ª)	actual-02-clientes.png	Estado actual	—
image.png (3ª)	actual-03-trabajar.png	Estado actual	—
image.png (4ª)	actual-04-parametros.png	Estado actual	—

En la Fase 0 abre cada imagen y escribe en docs/diseno/LECTURA_REFERENCIAS.md, por cada una, 3 a 5 observaciones concretas (medidas aproximadas, colores, proporciones) y en qué componente las vas a aplicar. Si tu lectura difiere de la tabla, dilo.

3. DIAGNÓSTICO DEL DISEÑO ACTUAL (lo que se elimina)

Basado en las 4 capturas actuales:

Plantilla SaaS genérica: tarjetas blancas idénticas, degradados índigo/violeta, píldora índigo flotante para "Utilidad neta", tarjeta azul saturada de "Salud contable". Nada lo diferencia de cualquier dashboard.
Sin jerarquía: todas las tarjetas pesan lo mismo; el ojo no sabe qué mirar primero.
Datos duplicados: "Resumen financiero consolidado" y "Mes de ene 25" muestran los mismos tres números ($11 M, $4 M, $2,6 M).
Cifras redondeadas a "M" en un producto contable. Un contador necesita la cifra exacta.
Información de infraestructura expuesta: el ID del proyecto de Supabase (jnyakmcnplrhnpvkunfq) en la barra lateral. Eso no es para el cliente.
"Carlos Cruz" repetido en la barra lateral y en la barra superior.
Páginas vacías: Clientes y Trabajar tienen un 70 % de pantalla en blanco sin intención.
Gráfica decorativa sin ejes ni significado en "Salud contable".
Formulario de jornada como texto crudo 2026-01-01=44; 2026-07-15=42: propenso a errores.
Plus Jakarta Sans + monoespaciada mezcladas sin sistema.
4. SISTEMA DE DISEÑO — fuente única de verdad

Crea src/styles/tokens.css con estas variables y haz que Tailwind (tailwind.config) lea solo de ellas. Ningún componente usa un hex ni una clase de paleta de Tailwind directamente.

4.1 Color
css
:root {
  /* Superficies */
  --papel:        #F2EFE9;  /* lienzo general (ref-05) */
  --hoja:         #FBFAF7;  /* tarjetas de trabajo */
  --hoja-2:       #F7F5F0;  /* filas alternas, zonas hundidas */
  --tinta:        #141414;  /* texto principal y Expediente */
  --tinta-2:      #1F1F1F;  /* hover sobre tinta */
  --grafito:      #3A3A38;  /* texto secundario */
  --gris:         #6B6A66;  /* metadatos (≥4.5:1 sobre --papel) */
  --linea:        rgba(20,20,20,.09);
  --rejilla:      rgba(20,20,20,.05);

  /* Acento de marca: azul tinta de pluma (ref-08) */
  --azul:         #2347D6;
  --azul-suave:   #E7ECFB;

  /* Semántica contable (solo para su significado) */
  --rojo:         #C21F17;  /* pérdida, descuadre, crítico (texto) */
  --rojo-cartel:  #D7261E;  /* rellenos de alerta crítica, ref-02 */
  --rojo-suave:   #FBE9E7;
  --ambar:        #A84F06;  /* advertencias */
  --ambar-suave:  #FBF0E3;
  /* Positivo = --tinta o --azul. NO existe verde en esta app. */
}

Reglas: utilidad positiva se muestra en --tinta con ▲; pérdida en --rojo con ▼ y entre paréntesis en estados financieros (1.234.475,72). El azul es acento, no relleno masivo: máximo un elemento azul sólido por vista (el botón de acción principal o el estado "Cuadra"). Verifica contraste AA de cada par texto/fondo y deja la tabla en docs/diseno/CONTRASTES.md.

4.2 Tipografía
Geist Sans (UI y display) y Geist Mono (metadatos, códigos PUC, NIT). Autoalojadas vía npm (geist o @fontsource), sin CDN. Prohibido Plus Jakarta Sans, Poppins, Inter.
Cifras: Geist Sans con font-variant-numeric: tabular-nums (no mono para dinero).
Formato de moneda siempre con Intl.NumberFormat('es-CO'): $ 11.034.200. Las abreviaturas ("M") solo en ejes de gráficas.
Token	Tamaño / interlineado	Peso	Tracking	Uso
display-xl	clamp(64px, 8vw, 128px) / 0.88	600	-0.05em	Preloader "CUADRA.", número héroe
display	clamp(48px, 5vw, 80px) / 0.92	600	-0.045em	Título de página (Tablero, Clientes…)
h1	32 / 36	600	-0.03em	Título de sección
h2	22 / 28	600	-0.02em	Título de tarjeta
kpi	40 / 44	500	-0.03em	Cifras de indicadores
body	15 / 22	400	-0.005em	Texto
small	13 / 18	400	0	Texto auxiliar
meta	11 / 14, Geist Mono, MAYÚSCULAS	500	0.12em	01 • RESUMEN, metadatos de esquina
tabla	13.5 / 20, tabular-nums	400 (totales 600)	0	Tablas contables
4.3 Rejilla y espaciado
Contenedor de 12 columnas, máximo 1440 px, márgenes 40 px (escritorio) / 20 px (móvil), canal 24 px.
Rejilla visible en el lienzo (ref-08): líneas verticales de 1 px --rejilla alineadas exactamente a las columnas del contenedor, más una línea horizontal bajo el meta-encabezado. Las tablas y formularios quedan siempre sobre --hoja, nunca sobre la rejilla.
Escala de espaciado en múltiplos de 4: 4, 8, 12, 16, 24, 32, 48, 64, 96.
Radios: 8 (chips), 12 (inputs, botones cuadrados), 18 (Hoja), 26 (Expediente), 999 (píldoras).
4.4 Materiales (de ref-05 y ref-07) — solo estos cinco
Material	Especificación	Uso
Hoja (drop shadow)	fondo --hoja, borde 1 px --linea, sombra 0 1px 0 rgba(255,255,255,.8) inset, 0 1px 2px rgba(20,20,20,.04), 0 12px 32px -18px rgba(20,20,20,.18)	Tarjetas de trabajo, tablas, formularios
Expediente (carpeta negra, ref-01)	fondo --tinta, texto 
#F5F3EE, secundario 
#A9A79F, sombra 0 40px 80px -40px rgba(20,20,20,.55) + halo 0 0 90px -30px rgba(255,140,100,.22)	Máximo 1–2 por vista: KPI héroe y accesos clave
Hundido (inner shadow)	fondo --hoja-2, inset 0 1px 2px rgba(20,20,20,.07), inset 0 0 0 1px rgba(20,20,20,.08)	Inputs, zona de arrastre, celdas editables
Cristal (ref-07)	rgba(251,250,247,.62), backdrop-filter: blur(22px) saturate(1.4), borde 1 px rgba(255,255,255,.65), reflejo superior linear-gradient(180deg, rgba(255,255,255,.55), transparent 40%)	Solo si hay contenido o aurora detrás: paleta ⌘K, modales, barra flotante, preloader. Nunca sobre blanco liso
Brillo "Cuadra" (glow)	0 0 0 1px rgba(35,71,214,.35), 0 0 28px rgba(35,71,214,.28)	Únicamente el estado "Cuadra" y el foco del elemento activo principal

Grano (texture overlay): capa fija SVG feTurbulence, opacidad 0.035, mix-blend-mode: multiply, pointer-events: none, sobre todo el lienzo. Prohibidos: neumorfismo, bisel/relieve, satén, degradados de color en tarjetas o en texto.

4.5 Componentes de firma (constrúyelos primero, en src/ui/)
Expediente — tarjeta con forma de carpeta de ref-01: cuerpo con radio 26 px y pestaña elevada arriba a la derecha (≈ 42 % del ancho, 22 px de alto, borde izquierdo inclinado). Dibújala con un <svg> cuyo path se recalcula con ResizeObserver para que las esquinas no se deformen. Flecha ↗ arriba a la derecha. Variantes: tinta (negra) y papel (clara con borde).
EsferaCliente — avatar generado del NIT (hash → 3 colores de la paleta de ref-04), círculo con radial-gradient múltiple y filter: blur en un pseudo-elemento. Tamaños 32 / 56 / 240 px. A 240 px se desplaza lentamente (deriva de 12 s). Reemplaza los círculos "FA".
EtiquetaSeccion — 01 • RESUMEN estilo ref-03: índice mono, punto, texto meta, dentro de una píldora con borde --linea.
MetaEncabezado — fila de 4 columnas de texto diminuto (ref-06) arriba de cada página. Ej. en Tablero: Carlos Cruz — Contador Público · T.P. 103028-T · Índice 01 — Tablero · Corte 31 ene 2025.
Interruptor — segmentado píldora negra/blanca con superíndices ⁰¹ ⁰² (ref-06); la píldora de tinta se desliza entre opciones con GSAP Flip.
Cifra — número de dinero con tabular-nums, signo y color semántico, animación de odómetro opcional, title con el valor exacto.
TablaContable — ver 6.5.
Insignia — estados: Cuadra (azul + brillo), Descuadre (rojo), Por cerrar (ámbar), Cerrado · listo para firmar (tinta), Activo/Inactivo/Archivado (neutros).
BotonPrimario — píldora --tinta texto claro (ref-03), altura 44 px; hover: fondo --tinta-2 y flecha que avanza 3 px. BotonAcento (azul) solo para la acción principal de la vista. BotonFantasma con borde --linea.
EnlaceSubrayado — subrayado azul de 1.5 px que se dibuja de izquierda a derecha al hover (ref-08).

Iconos: lucide-react, trazo 1.5, tamaños 16 y 20. Nada de emojis.

5. BRANDING — "Carlos Cruz · Contabilidad que cuadra."
Monograma: cuadrado --tinta de radio 10 px con "CC" en Geist 600 color 
#F5F3EE, y bajo las letras una línea horizontal con un trazo vertical centrado: una cuenta T mínima. Es el sello de marca y el favicon (SVG).
Logotipo: monograma + "Carlos Cruz" (Geist 600, -0.03em) + debajo CONTADOR PÚBLICO · T.P. 103028-T en meta.
Lema: Contabilidad que cuadra. (con punto final, como el cartel de ref-02).
Voz de la interfaz: español de Colombia, precisa, de contador. Ejemplos: "Débitos = Créditos", "Cuadra", "Descuadre de $ 50.000 en el comprobante CE-014", "Listo para firmar". Nada de "¡Genial!" ni signos de exclamación.
Crea docs/diseno/MARCA.md con monograma, usos correctos/incorrectos y área de protección.
6. PANTALLAS

Todas comparten: lienzo --papel + rejilla + grano; MetaEncabezado; título display; barra lateral nueva.

6.1 Barra lateral y barra superior
Barra lateral sobre --papel (no tarjeta flotante), ancho 248 px, borde derecho --linea. Arriba: logotipo. Navegación con índices estilo ref-06: Tablero⁰¹, Clientes⁰², Trabajar⁰³, Parámetros⁰⁴. Activo = píldora --tinta que se desliza (GSAP Flip).
Abajo: estado de sincronización humano: punto + "Sincronizado · hace 2 min". El ID de Supabase se mueve a Parámetros › Sistema.
Barra superior: se elimina el nombre duplicado. Queda: buscador ⌘K (cristal), botón + Nuevo periodo (BotonAcento) y avatar con iniciales.
Móvil (<900 px): barra lateral → barra inferior de 4 íconos con etiqueta.
6.2 Tablero

Orden y jerarquía (de arriba abajo):

MetaEncabezado + título Tablero en display + subtítulo: "1 cliente activo · último corte 31 de enero de 2025".
Fila héroe: a la izquierda (7 columnas) un Expediente tinta: 01 • RESULTADO DEL PERIODO, cifra de utilidad neta en display-xl con odómetro (cifra exacta, no "2,6 M"), debajo tres métricas pequeñas estilo ref-03: Ingresos / Gastos / Margen. Flecha ↗ lleva al estado de resultados. A la derecha (5 columnas) una Hoja con la ecuación contable tipográfica: Activo = Pasivo + Patrimonio con las tres cifras, dos barras horizontales proporcionales que se nivelan como una balanza y la insignia Cuadra con brillo.
Fila de estado: Gestión de periodos como tira de 12 meses (cada mes una celda: cerrado = tinta, abierto = azul con borde, sin contabilizar = rayado tenue, en mora = rojo) — así "Lleva 21 meses sin contabilizar" se ve, no solo se lee. Al lado, Nómina y seguridad social 2026 con SMMLV, auxilio y jornada vigente, y enlace "Ajustar".
Cola de operaciones: lista con barra lateral de color por severidad, EsferaCliente, nombre, descripción y acción ("Ver ficha ↗").
Clientes recientes: carrusel horizontal de Expediente papel con la esfera del cliente (ref-03 con la tarjeta vecina asomando).
Eliminar la tarjeta azul "Salud contable 100 %" con la curva sin ejes y el bloque duplicado "Mes de ene 25".
6.3 Clientes
Título Clientes + conteo + Interruptor: Expedientes⁰¹ | Tabla⁰².
Vista Expedientes (por defecto): rejilla de carpetas (Expediente papel), cada una con esfera, razón social, sigla, NIT en mono, municipio, periodicidad, honorarios/mes, insignia de estado y última actualización. Hover: la pestaña sube 4 px, la carpeta rota -0.6°, la flecha ↗ avanza.
Vista Tabla: la tabla actual refinada con TablaContable.
Filtros Activos/Inactivos/Archivados como Interruptor. Ordenar como menú desplegable con estilo propio.
Estado vacío: carpeta azul estilo ref-08 + "Aún no hay expedientes" + BotonPrimario "Crear el primer cliente".
6.4 Ficha del cliente
Cabecera Escaparate: EsferaCliente de 240 px con deriva lenta a la derecha, razón social en display, sigla, NIT, municipio, representante legal, contador; metadatos en esquinas estilo ref-04 (FANANT — 001, Constituida 26 — 11 — 2024).
Debajo, pestañas con índice: Resumen⁰¹ Periodos⁰² Estados financieros⁰³ Inventario⁰⁴ Nómina⁰⁵ Socios⁰⁶.
Reutiliza el panel de métricas existente (anillo de ecuación, indicadores con marca de referencia, gasto, liquidez, nómina, inventario) pero con los nuevos componentes y colores.
6.5 Trabajar (flujo de procesamiento) — prioridad UX
Paso a paso horizontal con índices: 01 Cliente · 02 Subir · 03 Mapeo · 04 Balance de prueba · 05 Ajustes · 06 Definitivo · 07 Estados. El paso actual en tinta, los completados con ✓, los futuros en gris. Siempre visible arriba (sticky).
01 Cliente: buscador grande + rejilla de Expedientes (no una sola tarjeta perdida en la página).
02 Subir: zona de arrastre Hundido de 280 px de alto, borde discontinuo; al arrastrar un archivo encima: borde azul + brillo + texto "Suelta para leer". Chips de formatos aceptados (.xlsx .xls .csv .pdf). Debajo, los 3 ejemplos (Tienda completa / Caso desordenado / Caso sencillo) como tarjetas con su descripción y botones "Cargar" y "Descargar Excel".
Procesando: mini cuenta T animada + lista de etapas que se van marcando (Leyendo archivo → Detectando formato → Mapeando al PUC → Calculando mayor → Validando partida doble). Nunca un spinner genérico.
03 Mapeo: tabla con semáforo de tres estados: tinta + ✓ = exacto, ámbar = por confirmar, rojo = sin mapear (sin verde, coherente con 4.1).
TablaContable (balance de prueba, ajustes, definitivo, mayor): encabezado pegajoso, cifras alineadas a la derecha con tabular-nums, código PUC en mono, sangría por nivel PUC (clase/grupo/cuenta/subcuenta) con peso tipográfico decreciente, hover de fila --hoja-2, sin cebra. Fila de totales con doble línea inferior (convención de libro contable) y la insignia Cuadra/Descuadre al lado. Columnas D/H agrupadas bajo cabecera común. Selector de densidad (cómoda/compacta). Saldos contrarios a su naturaleza marcados con un punto rojo y tooltip explicativo.
07 Estados financieros: cada estado se presenta como un documento sobre hoja (sombra Hoja grande, proporción carta), con encabezado (razón social, NIT, nombre del estado, fecha de corte), cuerpo y firmas del representante legal y del contador con T.P. — como el Excel que el contador ya usa, pero impecable. Barra de herramientas flotante de cristal abajo al centro: Excel · PDF · Imprimir · Ver anterior/siguiente. Estilos @media print correctos.
6.6 Parámetros
Años como Interruptor (2025⁰¹ | 2026⁰²) sobre una tabla de valores vigentes.
Formulario: inputs Hundido con máscara de miles en vivo (1.750.905) mientras se escribe, y vista previa "SMMLV + Auxilio = $ 2.000.000".
Jornada por tramos: reemplazar el texto crudo por filas editables [fecha] [horas] [quitar] + "Agregar tramo". Internamente se sigue serializando al mismo formato AAAA-MM-DD=horas; … que espera el backend (no cambies el contrato).
Nueva subsección Sistema: aquí va el estado de Supabase y el ID del proyecto.
6.7 Estados transversales

Diseña para todas las vistas: cargando (esqueletos con la forma real del contenido, brillo sutil), vacío (carpeta ref-08 + frase + acción), error (Hoja con borde rojo, mensaje humano + detalle técnico plegable + "Reintentar"), sin conexión. Toasts como "tira de papel" que entra desde abajo a la derecha.

7. PRELOADER — "La cuenta T"

Solo en la primera carga de la sesión (sessionStorage). Duración objetivo 2,6 s. Se salta con clic, Esc o cualquier tecla (texto "Saltar ↵" en la esquina). Su progreso está atado a la carga real de los datos del tablero: si cargan antes, no se alarga; si tardan, la cuenta T queda en un bucle sutil, nunca bloquea más de 4 s.

Línea de tiempo (GSAP timeline):

0.0–0.5 s — Lienzo --papel con grano. Las líneas de la rejilla se dibujan de arriba abajo (escala Y 0→1, stagger 0.03). Aparecen los textos de esquina estilo ref-06: arriba izquierda Carlos Cruz — Contador Público, arriba derecha T.P. 103028-T, abajo izquierda Guacarí, Valle del Cauca, abajo derecha Abriendo expedientes + contador 000 → 100 en mono.
0.4–1.3 s — En el centro se traza una cuenta T grande: primero la línea horizontal, luego la vertical (stroke-dashoffset). Aparecen DEBE y HABER en meta. Bajo cada lado ruedan columnas de cifras (odómetro) hasta dos totales iguales.
1.3–1.8 s — Entre los totales aparece = y el brillo azul "Cuadra"; encima, la palabra CUADRA. en display-xl tinta, con el interlineado apretado del cartel de ref-02, entrando con máscara desde abajo.
1.8–2.6 s — La cuenta T se contrae y vuela (GSAP Flip) hasta la posición del monograma en la barra lateral, mientras una forma de carpeta negra (ref-01) se abre desde el centro con clip-path y revela el Tablero, cuyos elementos entran con stagger.

prefers-reduced-motion: monograma + lema con fundido de 300 ms y nada más. Accesible: role="status", aria-live="polite" con "Cargando el tablero".

8. ANIMACIÓN (GSAP) — sistema, no adornos

Centraliza todo en src/animacion/ (amplía el animacion.ts existente). Registra Flip. No uses Lenis ni scroll suave (rompe las tablas pegajosas), ni cursores personalizados.

Movimiento	Especificación	Registro
Entrada de página	contenido y 12 px → 0, opacidad 0→1, 0.45 s power3.out, stagger 0.04	Ambos
Salida de página	opacidad 1→0, 0.15 s	Ambos
Odómetro de cifras	cada dígito rueda, 0.9 s expo.out, solo al cargar datos nuevos	Escaparate
Hover Expediente	pestaña -4 px, rotación -0.6°, flecha +3 px, 0.3 s	Escaparate
Interruptor / navegación	píldora desliza con Flip, 0.35 s power3.inOut	Ambos
Balanza de la ecuación	barras se nivelan con un leve asentamiento (back.out(1.4)) 0.6 s	Escaparate
Aurora / esferas	deriva lenta 12–18 s en bucle, solo en cabeceras	Escaparate
Aparición por scroll	ScrollTrigger una sola vez, y 16 px, 0.5 s	Escaparate
Tablas, formularios, mapeo	sin animación de entrada; solo cambios de estado ≤ 0.2 s	Taller

Solo transform y opacity. Todo respeta prefers-reduced-motion (duraciones a 0 salvo fundidos ≤ 0.2 s). Limpia con gsap.context() en cada desmontaje de React.

9. ACCESIBILIDAD Y CALIDAD
Contraste AA en todo el texto (4.5:1; 3:1 para texto ≥ 24 px). Documentado en CONTRASTES.md.
Foco visible: anillo de 2 px --azul con 2 px de separación.
Navegación completa por teclado; ⌘K/Ctrl+K abre la paleta.
El color nunca es el único portador de significado (▲▼, paréntesis, texto de la insignia).
Sin desbordes horizontales a 390 px; las tablas anchas se desplazan dentro de su contenedor.
Lighthouse (accesibilidad y buenas prácticas) ≥ 95 en Tablero y Clientes.
10. LISTA DE PROHIBIDOS (validación automática)

Crea scripts/lint-diseno.mjs y el comando npm run lint:diseno, que falle si encuentra en src/ (excepto tokens.css):

Clases de paleta de Tailwind: (bg|text|border|from|to|via|ring|shadow)-(indigo|violet|purple|green|emerald|lime|teal|sky|blue|cyan|fuchsia|pink|rose)-\d+.
Cualquier hex o rgb( fuera de tokens.css.
Plus Jakarta, Poppins, Inter en fuentes.
bg-gradient-to- en tarjetas y bg-clip-text (texto con degradado).
Emojis en JSX.
Texto con el ID de Supabase en componentes de UI.
Formatos de moneda con "M" fuera de componentes de gráfica.

Agrégalo al flujo junto con las pruebas y tsc. Si falla, la fase no está terminada.

11. FASES

Fase 0 — Diagnóstico y lectura (sin código). Causa real de que no se vieran los cambios (sección 0); inventario de dónde salen los estilos actuales; LECTURA_REFERENCIAS.md. Espera aprobación. Fase 1 — Cimientos. Fuentes, tokens.css, Tailwind conectado a tokens, lienzo (papel + rejilla + grano), eliminación de estilos viejos, lint:diseno, sello de build en el pie. Fase 2 — Componentes de firma (4.5) y una página /diseno interna que muestre todos los componentes y estados (catálogo vivo). Fase 3 — Marca y estructura. Monograma, favicon, barra lateral, barra superior, MetaEncabezado, versión móvil. Fase 4 — Tablero. Fase 5 — Clientes y ficha del cliente. Fase 6 — Trabajar (los 7 pasos, TablaContable, estados financieros como documento, impresión). Fase 7 — Parámetros y estados transversales (carga, vacío, error). Fase 8 — Preloader y animación (secciones 7 y 8). Fase 9 — Pulido. Accesibilidad, Lighthouse, revisión cruzada con todas las referencias, docs/diseno/ANTES_Y_DESPUES.md.

Al final de cada fase: npm run build, pruebas (111 verdes), tsc, lint:diseno, capturas (sección 12) y un informe corto.

12. VERIFICACIÓN VISUAL OBLIGATORIA
Crea npm run capturas con Playwright: captura cada ruta a 1440×900 y 390×844 (y el preloader a mitad de animación) en docs/diseno/capturas/<fase>/.
Abre tú mismo cada captura y compárala con las referencias y con esta especificación. Corrige antes de reportar.
En el informe de la fase incluye por pantalla una lista de verificación con ✅/❌:
¿Se lee primero lo más importante?
¿Hay algún color, sombra o radio fuera de los tokens?
¿Qué referencias se ven aplicadas aquí y dónde exactamente?
¿Las cifras son exactas, alineadas y en formato es-CO?
¿Funciona a 390 px?
¿Contraste AA?
Muestra la captura antes (de actual-0X) y después lado a lado.

Criterio de aceptación final: al comparar actual-01-tablero.png con la nueva captura, nadie debe poder decir que es la misma aplicación con otros colores. Debe reconocerse en ella la carpeta de ref-01, la tipografía de ref-02, las etiquetas y métricas de ref-03, las esferas de ref-04, los materiales de ref-05, el interruptor y los metadatos de ref-06, el cristal de ref-07 y la rejilla de ref-08 — y a la vez debe seguir pareciendo el despacho de un contador serio.
