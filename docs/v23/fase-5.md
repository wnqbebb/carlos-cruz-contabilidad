# v2.3 · Fase 5 — Declaración de renta automática (personas naturales, formulario 210)

## Qué hace

**Tres pasos.** En el cliente › **Renta**:

1. **Suelte todo**: fotos (giradas, recortadas, de varias páginas, en desorden), PDF o Excel del portal.
2. **Revise en una pantalla**: veredicto grande, tres cifras (paga / le devuelven · ahorro frente a la propuesta de
   la DIAN · vencimiento con días), máximo 5 preguntas de un toque, «¿Podemos pagar menos?» con el ahorro de cada
   beneficio, cosas a mirar, y el detalle plegado (cada línea con el recorte de la foto, editable y reclasificable
   con un clic; las casillas del 210 en dos columnas).
3. **Descargue**: un botón → ZIP con el borrador del 210 en PDF («BORRADOR — no válido para presentar»), el papel de
   trabajo en Excel (cada casilla con su fórmula y de dónde sale cada peso) y el resumen de una página para el
   cliente. Luego «Marcar como presentada» (número y fecha).

La aplicación **no presenta** la declaración y lo dice.

**Renta⁰³** (navegación): la cartera de personas naturales con obligación y motivo, vencimiento por NIT y días,
estado, impuesto o saldo a favor y ahorro; ordenable y filtrable. **Tablero**: una tarea por declaración que vence en
15 días o menos o ya venció sin presentarse. Las personas jurídicas ven que el 110 no se prepara aún
(`docs/PROPUESTAS.md`, P05).

## Cómo lee las fotos (`backend/app/renta/ocr.py`)

Orientación (OSD y, si duda, comparación por confianza) → enderezado fino por el ángulo de las líneas → la hoja
frente al fondo → la tabla por sus líneas y su perspectiva aplanada → rejilla (un trazo es línea si mide más de
2,2 veces la letra: las letras alineadas no se confunden con columnas) → lectura por fila sin las líneas de la
rejilla, separando filas cuando una franja abarca varias → **relectura celda por celda** del valor y de lo dudoso →
resaltados relativos a la propia hoja. Fuera de la tabla solo se buscan notas a mano: nunca se guardan; si hay tinta o
algo con forma de credencial, se avisa. Se guardan solo recortes de filas de la tabla, nunca la foto completa.

Los importes dudosos (el «$» leído como «5») guardan alternativas; la validación contra los topes del encabezado elige
la que cuadra. Diferencias de hasta 1.000 pesos se reconocen como redondeo de la fuente.

## Cálculo (`backend/app/renta/calculo.py`)

Formulario versionado (`data/renta/210_ag2025.json`, 114 casillas del oficial) y parámetros con norma y fuente
(`data/renta/parametros_ag2025.json`): UVT, topes, art. 241, límite 40 % / 1.340 UVT, 25 % con 790 UVT, dependientes
(incluida la adición de 72 UVT), vivienda, prepagada, AFC/FVP, GMF, 1 % de compras con factura electrónica,
componente inflacionario 55,43 % (Decreto 898 de 2026), dividendos, ganancias ocasionales, anticipo, aproximación a
miles, calendario y sanción. Lo no confirmable: `docs/v23/SUPUESTOS_RENTA.md`.

## Resultados con las imágenes del contador

| Caso | Resultado |
|---|---|
| **A** (imágenes 4 y 5) | La foto real se lee completa: 5 topes y las 23 filas con **todos** los valores iguales a la transcripción; las 5 sumas cuadran (Tope 4 con su diferencia de 3 pesos del propio reporte). Con lo que agrega el contador, **todas las casillas comparadas coinciden con el 210 presentado** (29, 30, 31, 58, 59, 61, 74, 77, 78, 91, 92, 97, 116, 132, 137). Obligada solo por el Tope 4; las 2 líneas «NO REGISTRA NO» marcadas; aviso de consignaciones ≫ facturación electrónica; la nota manuscrita junto al nombre se detecta y no se guarda. |
| **B** (imágenes 1–3, en desorden) | Las tres se reconocen como del mismo contribuyente y se unen. Topes exactos (82.535.904 · 226.543.936 · 19.977.892 · 125.053.184 · 12.910.068) y Tope 6 (IVA). Veredicto: obligado por ingresos, patrimonio, consignaciones e IVA. Saldo a favor 6.275.000 encontrado (línea impresa de la página 2). Los pagos de la misma empresa: **una sola pregunta** (11 documentos). Nota manuscrita: detectada, no guardada, aviso. **50 filas leídas; 46 % con confianza alta** en el valor (la hoja se imprimió dos veces). El patrimonio del año anterior (página 3, 181.910.000) se lee como valor, pero su detalle está encimado e ilegible: queda en ámbar para clasificarlo con un clic. |
| **F** (sintético difícil, en git) | Girada 90°, perspectiva, poco contraste, sombra, una fila encimada, 3 resaltadas, nota con aspecto de contraseña, «SF: …» a mano y un recetario al margen: 5 topes exactos, 12/12 líneas, sumas cuadradas, resaltados detectados, la credencial no se guarda y el «SF» se ofrece como sugerencia. |

**Tiempo y clics** (Playwright, de soltar las fotos al borrador descargado; meta ≤ 10 clics y < 5 min):

| Caso | Tiempo | Clics |
|---|---|---|
| F (1 foto sintética) | 13 s | 4 |
| A (foto real + 2 datos del contador + 1 %) | 14 s | 9 |
| B (3 fotos reales) | 42 s | 3 |

## Datos y seguridad

`supabase/migraciones/005_renta.sql`: `renta_declaraciones` (una por cliente y año), `renta_versiones` (cada cambio
deja versión) y `renta_recortes`, con RLS y sin permisos para las claves públicas. `/api/renta/*` pide sesión.
El Excel escapa los textos que empiezan por `= + - @`. El lector de fotos queda en `datos_app/` (fuera de git) con
`scripts/preparar_ocr.ps1`, que usan `iniciar.bat` y el empaquetado del `.exe`.

## Control de calidad

| Prueba | Resultado |
|---|---|
| `pytest backend/tests` | 304 pasan (cálculo a mano de 6 contribuyentes + caso A, API, OCR sintético, caso A y B con fotos reales en `privado/`) |
| `tsc --noEmit` | limpio |
| `npm run lint:diseno` | 0 |
| `npm run build` | correcto |
| `flujo-v23-renta.mjs` (claro/oscuro · 1440/390) | sin errores; Renta⁰³ y la sección, sin desbordes |
| expediente, trabajo, preguntas, sistema, capturas | sin errores |

Los casos A y B con fotos reales solo corren donde existe `privado/` (si no, se saltan con aviso).
La lectura de las imágenes está en `docs/v23/LECTURA_IMAGENES.md` (anonimizada) y `privado/renta/LECTURA_IMAGENES.md`.
