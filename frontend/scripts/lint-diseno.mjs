#!/usr/bin/env node
/**
 * lint:diseno — vigila que nadie se salte el sistema de diseño (spec, sección 10).
 *
 * POR QUÉ EXISTE
 * En la Fase 0 se encontró que 387 clases de color escritas a mano ignoraban
 * los tokens: por eso cambiar la paleta no cambiaba la pantalla. Este script
 * impide que eso vuelva a pasar. Si falla, la fase no está terminada.
 *
 * Revisa todo `src/` excepto `styles/tokens.css`, que es el único lugar donde
 * pueden vivir colores, sombras y fuentes.
 *
 * Uso:  npm run lint:diseno        (sale con código 1 si encuentra algo)
 */
import { readdirSync, readFileSync, statSync } from "node:fs";
import { join, relative, sep } from "node:path";
import { fileURLToPath } from "node:url";

const RAIZ = fileURLToPath(new URL("..", import.meta.url));
const SRC = join(RAIZ, "src");
const PERMITIDO = join("src", "styles", "tokens.css");

// Archivos donde SÍ se permite la abreviatura "M" (son ejes y etiquetas de gráfica).
const GRAFICAS = new Set([join("src", "componentes", "Grafica.tsx")]);
// Único lugar donde se puede mostrar el estado técnico de la base de datos.
const SISTEMA = new Set([join("src", "paginas", "Parametros.tsx")]);

const PALETAS =
  "slate|gray|zinc|neutral|stone|red|orange|amber|yellow|lime|green|emerald|teal|cyan|sky|blue|indigo|violet|purple|fuchsia|pink|rose";
// border-t-, border-x-, divide-x-… también: `border-t-indigo-600` se colaba en la Fase 1.
const PROPIEDADES =
  "bg|text|border(?:-[trblxyse])?|from|to|via|ring(?:-offset)?|shadow|fill|stroke|outline|divide(?:-[xy])?|accent|decoration|placeholder|caret";

/**
 * Cada regla: qué busca, en qué archivos, y por qué está prohibido.
 * El «porqué» se imprime: así quien la rompa entiende qué hacer.
 */
const REGLAS = [
  {
    id: "paleta-tailwind",
    patron: new RegExp(`\\b(?:[a-z-]+:)?(?:${PROPIEDADES})-(?:${PALETAS})-\\d{2,3}(?:\\/\\d+)?\\b`, "g"),
    archivos: /\.(tsx|ts|jsx|js)$/,
    porque: "Use un token (bg-papel, text-tinta, text-gris, bg-azul, text-rojo…). Las clases de paleta ignoran tokens.css.",
  },
  {
    id: "hex-o-rgb",
    // Hex de 3, 4, 6 u 8 dígitos y funciones de color. No coincide con anclas de Excel ("#'Hoja'!A1") ni entidades HTML (&#…).
    patron: /(?<![\w&/-])#(?:[0-9a-fA-F]{8}|[0-9a-fA-F]{6}|[0-9a-fA-F]{3,4})\b|\brgba?\s*\(|\bhsla?\s*\(/g,
    archivos: /\.(tsx|ts|jsx|js|css)$/,
    porque: "Los colores viven solo en styles/tokens.css. Use var(--token).",
  },
  {
    id: "fuente-prohibida",
    patron: /Plus\s*Jakarta|Poppins|\bInter\b(?![a-zá-ú])/g,
    archivos: /\.(tsx|ts|css|html)$/,
    porque: "La única familia es Geist (Sans y Mono), autoalojada.",
  },
  {
    id: "degradado",
    patron: /\bbg-gradient-to-[a-z]+\b|\bbg-linear-to-[a-z]+\b|\bbg-clip-text\b/g,
    archivos: /\.(tsx|ts|jsx|js)$/,
    porque: "Sin degradados en tarjetas ni texto con degradado (spec 4.4).",
  },
  {
    id: "emoji",
    // Pictogramas. Se permiten ✓ ✗ ▲ ▼ ↗ ← → ↑ ↓ ⌘ · — que son signos tipográficos del spec.
    patron: /(?![✓✗▲▼↗←→↑↓⌘·—])[\p{Extended_Pictographic}\u{FE0F}]/gu,
    archivos: /\.(tsx|jsx)$/,
    porque: "Nada de emojis: los íconos son lucide-react, trazo 1.5.",
  },
  {
    id: "id-supabase",
    patron: /jnyakmcnplrhnpvkunfq|almacenamiento\.proyecto|\.proyecto\b/g,
    archivos: /\.(tsx|jsx)$/,
    excepto: SISTEMA,
    porque: "El ID del proyecto de Supabase no es para el cliente: solo en Parámetros › Sistema.",
  },
  {
    id: "moneda-abreviada",
    patron: /\bpesosCorto\s*\(/g,
    archivos: /\.(tsx|jsx)$/,
    excepto: GRAFICAS,
    porque: "Un contador necesita la cifra exacta. La abreviatura «M» solo en ejes de gráficas.",
  },
];

function* recorrer(dir) {
  for (const nombre of readdirSync(dir)) {
    const ruta = join(dir, nombre);
    if (statSync(ruta).isDirectory()) yield* recorrer(ruta);
    else yield ruta;
  }
}

/** Quita comentarios para no denunciar lo que solo se está explicando. */
function sinComentarios(texto, esCss) {
  let t = texto.replace(/\/\*[\s\S]*?\*\//g, (m) => m.replace(/[^\n]/g, " "));
  if (!esCss) t = t.replace(/(^|[^:"'`])\/\/[^\n]*/g, (m, a) => a + " ".repeat(m.length - a.length));
  return t;
}

const hallazgos = [];
const archivos = [...recorrer(SRC), join(RAIZ, "index.html")];

for (const absoluta of archivos) {
  const rel = relative(RAIZ, absoluta);
  if (rel === PERMITIDO) continue;
  const crudo = readFileSync(absoluta, "utf8");
  const texto = sinComentarios(crudo, /\.(css|html)$/.test(rel));
  const lineas = texto.split("\n");

  for (const regla of REGLAS) {
    if (!regla.archivos.test(rel)) continue;
    if (regla.excepto?.has(rel)) continue;
    lineas.forEach((linea, i) => {
      for (const m of linea.matchAll(regla.patron)) {
        hallazgos.push({ rel: rel.split(sep).join("/"), linea: i + 1, regla, texto: m[0] });
      }
    });
  }
}

if (!hallazgos.length) {
  console.log("lint:diseno ✓  sin infracciones en src/ (" + archivos.length + " archivos revisados)");
  process.exit(0);
}

const porRegla = new Map();
for (const h of hallazgos) {
  if (!porRegla.has(h.regla.id)) porRegla.set(h.regla.id, []);
  porRegla.get(h.regla.id).push(h);
}
for (const [id, lista] of porRegla) {
  console.log(`\n✗ ${id} — ${lista.length} caso(s)\n  ${lista[0].regla.porque}`);
  for (const h of lista.slice(0, 12)) console.log(`    ${h.rel}:${h.linea}  ${h.texto}`);
  if (lista.length > 12) console.log(`    … y ${lista.length - 12} más`);
}
console.log(`\nlint:diseno ✗  ${hallazgos.length} infracción(es). La fase no está terminada.`);
process.exit(1);
