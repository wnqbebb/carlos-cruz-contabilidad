#!/usr/bin/env node
/**
 * Mide los contrastes del sistema de diseño en claro y en oscuro (v2.2 · 8.1 y 8.4)
 * y escribe docs/diseno/CONTRASTES.md. Lee los valores de styles/tokens.css: si un
 * token cambia, el informe cambia. Sale con código 1 si algún par no cumple.
 *
 *   node scripts/contrastes.mjs
 *
 * Criterios:
 *   · superficies (lienzo↔hoja, barra↔lienzo, campo↔hoja): ≥ 1,10:1 (más el borde);
 *   · texto: AA, 4,5:1 (3:1 para texto grande, marcado como tal).
 */
import { readFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { fileURLToPath } from "node:url";

const RAIZ = fileURLToPath(new URL("..", import.meta.url));
const css = readFileSync(join(RAIZ, "src", "styles", "tokens.css"), "utf8").replace(/\/\*[\s\S]*?\*\//g, "");

function bloque(inicio) {
  const i = css.indexOf(inicio);
  let nivel = 0;
  for (let j = css.indexOf("{", i); j < css.length; j++) {
    if (css[j] === "{") nivel++;
    if (css[j] === "}" && --nivel === 0) return css.slice(i, j);
  }
  return "";
}
const leer = (texto) => Object.fromEntries([...texto.matchAll(/(--[a-z0-9-]+)\s*:\s*([^;]+);/g)].map((m) => [m[1], m[2].trim()]));
const claro = leer(bloque(":root {"));
const oscuro = { ...claro, ...leer(bloque(':root[data-tema="oscuro"]')) };

function color(valor, tokens, fondo) {
  let v = valor;
  for (let n = 0; n < 6 && v.startsWith("var("); n++) v = tokens[v.slice(4, -1).split(",")[0].trim()];
  if (!v) return null;
  let m = v.match(/^#([0-9a-f]{6})$/i);
  if (m) return [0, 2, 4].map((i) => parseInt(m[1].slice(i, i + 2), 16));
  m = v.match(/^rgba?\(([^)]+)\)$/);
  if (m) {
    const [r, g, b, a = 1] = m[1].split(",").map(Number);
    if (a >= 1 || !fondo) return [r, g, b];
    return [r, g, b].map((c, i) => Math.round(c * a + fondo[i] * (1 - a)));
  }
  if (v === "transparent") return fondo;
  return null;
}
const lum = (rgb) => {
  const [r, g, b] = rgb.map((c) => {
    c /= 255;
    return c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
  });
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
};
const razon = (a, b) => {
  const [x, y] = [lum(a), lum(b)].sort((p, q) => q - p);
  return (x + 0.05) / (y + 0.05);
};

// [texto, fondo, mínimo, nota, sobre (fondo debajo del fondo, si es translúcido)]
const PARES = [
  ["--hoja", "--lienzo", 1.1, "superficie: tarjeta sobre lienzo"],
  ["--barra", "--lienzo", 1.1, "superficie: barra lateral sobre lienzo"],
  ["--campo", "--hoja", 1.1, "superficie: campo sobre tarjeta (con borde --borde-campo)", null, 1.0],
  ["--borde-campo", "--hoja", 1.5, "borde del campo sobre tarjeta"],
  ["--tinta", "--lienzo", 4.5, "texto principal"],
  ["--tinta", "--hoja", 4.5, "texto principal"],
  ["--tinta", "--campo", 4.5, "texto en campos"],
  ["--grafito", "--lienzo", 4.5, "texto secundario"],
  ["--grafito", "--hoja", 4.5, "texto secundario, etiquetas de campo"],
  ["--grafito", "--barra", 4.5, "navegación inactiva"],
  ["--gris", "--hoja", 4.5, "metadatos"],
  ["--gris", "--lienzo", 4.5, "metadatos"],
  ["--gris", "--hoja-2", 4.5, "metadatos sobre zona secundaria"],
  ["--azul-tinta", "--hoja", 4.5, "enlaces"],
  ["--azul-tinta", "--lienzo", 4.5, "enlaces"],
  ["--azul", "--hoja", 4.5, "estado «Cuadra»"],
  ["--sobre-color", "--azul", 4.5, "botón principal"],
  ["--rojo", "--hoja", 4.5, "pérdidas y descuadres"],
  ["--rojo", "--rojo-suave", 4.5, "aviso de error"],
  ["--ambar", "--hoja", 4.5, "advertencias"],
  ["--ambar", "--ambar-suave", 4.5, "aviso de advertencia"],
  ["--sobre-tinta", "--tinta", 4.5, "texto sobre tinta (Expediente, píldora)"],
  ["--sobre-tinta-2", "--tinta", 4.5, "texto secundario sobre tinta"],
  ["--banda-texto", "--banda-taller", 4.5, "banda de taller (Trabajar)"],
  ["--banda-texto-2", "--banda-taller", 4.5, "banda de taller, secundario"],
  ["--banda-azul-tinta", "--banda-taller", 4.5, "enlace en la banda de taller"],
  ["--tinta", "--cabecera-clientes", 4.5, "título sobre la cabecera de Clientes", "--lienzo"],
  ["--gris", "--cabecera-clientes", 4.5, "metaencabezado sobre la cabecera de Clientes", "--lienzo"],
  ["--tinta", "--cabecera-parametros", 4.5, "título sobre la cabecera de Parámetros"],
  ["--gris", "--cabecera-parametros", 4.5, "metaencabezado sobre la cabecera de Parámetros"],
  ["--sobre-color", "--frio-oscuro", 4.5, "píldora activa de Parámetros"],
  ["--sobre-color", "--azul-tinta", 4.5, "píldora activa de Clientes"],
  ["--sobre-tinta", "--grafito", 4.5, "píldora activa de Trabajar"],
];

let fallos = 0;
function tabla(nombre, tokens) {
  const filas = [];
  for (const [t, f, minimo, nota, sobre] of PARES) {
    const base = sobre ? color(tokens[sobre], tokens) : color(tokens["--lienzo"], tokens);
    const fondo = color(tokens[f], tokens, base);
    const texto = color(tokens[t], tokens, fondo);
    if (!fondo || !texto) {
      filas.push(`| ${t} sobre ${f} | — | ${minimo}:1 | no medible | ${nota} |`);
      continue;
    }
    const r = razon(texto, fondo);
    const ok = r + 1e-9 >= minimo;
    if (!ok) fallos++;
    filas.push(`| \`${t}\` sobre \`${f}\` | **${r.toFixed(2)}:1** | ${minimo.toFixed(2).replace(".", ",")}:1 | ${ok ? "✅" : "❌"} | ${nota} |`);
  }
  return `## ${nombre}\n\n| Par | Contraste | Mínimo | | Uso |\n|---|---|---|---|---|\n${filas.join("\n")}\n`;
}

const md = `# Contrastes medidos (v2.2)

Generado por \`frontend/scripts/contrastes.mjs\` a partir de \`src/styles/tokens.css\`.
No es una lista escrita a mano: si un token cambia, se vuelve a correr y el informe cambia.
Los colores translúcidos se componen sobre el fondo que tienen debajo.

Criterios: superficies ≥ 1,10:1 además de su borde (8.1); texto AA 4,5:1.
El color de cada cliente (8.3) se ajusta solo a 4,5:1 sobre la hoja, en cada modo
(\`colorCliente.ts\`); las ocho muestras están en el catálogo \`/diseno\`.

${tabla("Modo claro", claro)}
${tabla("Modo oscuro", oscuro)}`;
writeFileSync(join(RAIZ, "..", "docs", "diseno", "CONTRASTES.md"), md);
console.log(md);
if (fallos) {
  console.log(`\n${fallos} par(es) por debajo del mínimo.`);
  process.exit(1);
}
