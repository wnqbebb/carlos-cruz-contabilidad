#!/usr/bin/env node
/**
 * Fase 5 en la interfaz: libro diario y libro mayor y balances.
 *
 *   node scripts/flujo-fase5.mjs http://127.0.0.1:8001 <carpeta-salida>
 *
 *   1. Trabajar: pestañas «Libro diario» (clic en el origen → fila original) y
 *      «Mayor y balances».
 *   2. Ficha › Libro diario: selector de periodo y las cuatro descargas
 *      (diario y mayor y balances, en Excel y PDF) responden con un archivo.
 *
 * Crea clientes y calcula: SOLO contra la copia aislada.
 */
import { mkdirSync } from "node:fs";
import { join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";
import { conSesion, prepararSesion } from "./sesion.mjs";

const [base, salida] = process.argv.slice(2);
await prepararSesion(base);
if (/:8000\b/.test(base ?? "")) {
  console.error("Se niega a correr contra :8000 (la base real).");
  process.exit(1);
}
mkdirSync(salida, { recursive: true });
const BANCO = resolve(fileURLToPath(import.meta.url), "../../../backend/tests/archivos_variados");

const navegador = await chromium.launch({ channel: "msedge" });
await conSesion(navegador, base);
const errores = [];
const contexto = await navegador.newContext({ viewport: { width: 1440, height: 900 }, reducedMotion: "reduce" });
await contexto.addInitScript(() => {
  try { sessionStorage.setItem("cc-preloader-visto", "1"); } catch {}
});
const p = await contexto.newPage();
p.on("pageerror", (e) => errores.push(String(e)));
p.on("console", (m) => m.type() === "error" && !/40[09]|422/.test(m.text()) && errores.push(m.text()));

await p.goto(`${base}/`, { waitUntil: "networkidle" });
await p.locator("input[type=file]").first().setInputFiles(join(BANCO, "01_ventas_compras_bloques.xlsx"));
await p.getByText("Esto es la contabilidad de un cliente").waitFor({ timeout: 60000 });
await p.locator("[role=dialog] input").nth(1).fill("900500777");
await p.getByRole("button", { name: "Crear cliente y calcular" }).click();
await p.getByText("Preguntas sobre este archivo").waitFor({ timeout: 90000 });
await p.getByRole("button", { name: "Usar las respuestas sugeridas y calcular" }).click();
await p.getByText("Resultado del periodo").waitFor({ timeout: 90000 });

/* ── 1. pestañas de los libros ──────────────────────────────────────────── */
await p.getByRole("tab", { name: "Libro diario" }).click();
await p.getByText("Partida doble verificada").waitFor({ timeout: 15000 });
const origen = p.locator("button[aria-expanded]").first();
await origen.click();
await p.getByText("Fila original").waitFor({ timeout: 5000 });
const celdas = await p.getByText("Fila original").locator("xpath=following-sibling::div[1]").innerText();
console.log("1 · fila original al pulsar el origen:", celdas.replace(/\s+/g, " | "));
await p.screenshot({ path: join(salida, "f5-01-libro-diario.png"), fullPage: true });

await p.getByRole("tab", { name: "Mayor y balances" }).click();
await p.getByText("Total grupo 11").first().waitFor({ timeout: 15000 });
await p.screenshot({ path: join(salida, "f5-02-mayor-y-balances.png"), fullPage: true });
console.log("1 · mayor y balances con subtotales por grupo y clase");

/* ── 2. ficha › libro diario ────────────────────────────────────────────── */
const cliente = new URL(p.url()).searchParams.get("cliente");
await p.goto(`${base}/clientes/${cliente}?vista=movimientos`, { waitUntil: "networkidle" });
await p.getByText("Partida doble verificada").waitFor({ timeout: 20000 });
await p.screenshot({ path: join(salida, "f5-03-ficha-libro-diario.png"), fullPage: true });
const enlaces = await p.locator("a[href*='/libro-diario/'], a[href*='/mayor-balances/']").evaluateAll((as) => as.map((a) => a.href));
for (const href of enlaces) {
  const r = await fetch(href);
  const tipo = r.headers.get("content-type");
  const tam = (await r.arrayBuffer()).byteLength;
  console.log(`2 · ${href.split("/").slice(-2).join("/")}: ${r.status} ${tipo?.split(";")[0]} ${tam} bytes`);
  if (r.status !== 200 || tam < 1000) errores.push(`descarga ${href} → ${r.status}`);
}
const periodos = await p.locator("button[aria-pressed]").count();
console.log("2 · periodos en el selector:", periodos);
await p.locator("button[aria-pressed]").nth(1).click();
await p.waitForTimeout(800);
await p.screenshot({ path: join(salida, "f5-04-ficha-otro-periodo.png"), fullPage: true });

/* ── 3. a 390 px ────────────────────────────────────────────────────────── */
await p.setViewportSize({ width: 390, height: 844 });
await p.reload({ waitUntil: "networkidle" });
await p.getByText("Partida doble verificada").waitFor({ timeout: 20000 });
await p.screenshot({ path: join(salida, "f5-05-ficha-libro-390.png"), fullPage: true });
const ancho = await p.evaluate(() => document.documentElement.scrollWidth);
console.log("3 · 390 px: ancho del documento", ancho, ancho <= 390 ? "(sin desborde)" : "(DESBORDA)");
if (ancho > 390) errores.push("desborde a 390 px");

await navegador.close();
if (errores.length) {
  console.log("ERRORES:", errores);
  process.exit(1);
}
console.log("Sin errores de consola.");
