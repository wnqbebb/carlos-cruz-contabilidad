#!/usr/bin/env node
/**
 * Fase 4 en la interfaz: registros auxiliares, PDF y Word.
 *
 *   node scripts/flujo-fase4.mjs http://127.0.0.1:8001 <carpeta-salida>
 *
 * Lo que comprueba, en el navegador:
 *   1. Listas de ventas y cartera soltadas en la carga masiva del directorio:
 *      se reconocen, se crea el cliente pidiendo solo el NIT, aparece el panel
 *      «Preguntas sobre este archivo» y se calcula con las respuestas sugeridas.
 *   2. Un archivo de varios meses se procesa mes a mes, cerrando cada uno.
 *   3. Un balance de prueba en PDF con texto y una tabla de ventas en Word
 *      llegan hasta los estados financieros.
 *
 * Crea clientes y calcula: SOLO contra la copia aislada.
 */
import { mkdirSync } from "node:fs";
import { join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";

const [base, salida] = process.argv.slice(2);
if (/:8000\b/.test(base ?? "")) {
  console.error("Se niega a correr contra :8000 (la base real).");
  process.exit(1);
}
mkdirSync(salida, { recursive: true });
const BANCO = resolve(fileURLToPath(import.meta.url), "../../../backend/tests/archivos_variados");
const archivo = (n) => join(BANCO, n);
let nit = 900400100;

const navegador = await chromium.launch({ channel: "msedge" });
const errores = [];

async function pagina(ancho = 1440, alto = 900) {
  const contexto = await navegador.newContext({ viewport: { width: ancho, height: alto }, reducedMotion: "reduce" });
  await contexto.addInitScript(() => {
    try { sessionStorage.setItem("cc-preloader-visto", "1"); } catch {}
  });
  const p = await contexto.newPage();
  p.on("pageerror", (e) => errores.push(String(e)));
  p.on("console", (m) => m.type() === "error" && !/40[09]|422/.test(m.text()) && errores.push(m.text()));
  return p;
}

/** Sube por la puerta única, completa lo que falte y entra a 03 Mapeo. */
async function subirYCrear(p, ruta, foto) {
  await p.locator("input[type=file]").first().setInputFiles(ruta);
  await p.getByText("Esto es la contabilidad de un cliente").waitFor({ timeout: 60000 });
  const campos = p.locator("[role=dialog] input");
  if (!(await campos.first().inputValue())) await campos.first().fill(`CLIENTE DE PRUEBA ${nit}`);
  if (!(await campos.nth(1).inputValue())) await campos.nth(1).fill(String(nit++));
  if (foto) await p.screenshot({ path: join(salida, foto), fullPage: true });
  await p.getByRole("button", { name: "Crear cliente y calcular" }).click();
  await p.getByText("Mapeo de cuentas al PUC").waitFor({ timeout: 90000 });
}

/* ── 1. listas en la puerta del directorio ─────────────────────────────── */
{
  const p = await pagina();
  await p.goto(`${base}/clientes`, { waitUntil: "networkidle" });
  await p.getByRole("button", { name: "Importar directorio de clientes" }).click();
  await p.getByText("Carga masiva").waitFor({ timeout: 15000 });
  await p.locator("[role=dialog] input[type=file]").setInputFiles(archivo("06_cartera_terceros_desconocidos.xlsx"));
  await p.getByRole("button", { name: "Revisar sin guardar" }).click();
  await p.getByText("Esto no parece una lista de clientes").waitFor({ timeout: 30000 });
  await p.getByRole("button", { name: "Ver qué trae este archivo" }).click();
  await p.getByText("Esto es la contabilidad de un cliente").waitFor({ timeout: 60000 });
  const texto = await p.locator("[role=dialog]").innerText();
  console.log("1 · tarjeta:", texto.match(/Encontré[^.]*\./)?.[0]);
  const boton = p.getByRole("button", { name: "Crear cliente y calcular" });
  console.log("1 · sin NIT el botón está", (await boton.isDisabled()) ? "bloqueado" : "ACTIVO (mal)");
  await p.locator("[role=dialog] input").nth(1).fill(String(nit++));
  await p.screenshot({ path: join(salida, "f4-01-listas-reconocidas.png"), fullPage: true });
  await boton.click();
  await p.getByText("Preguntas sobre este archivo").waitFor({ timeout: 90000 });
  await p.screenshot({ path: join(salida, "f4-02-preguntas.png"), fullPage: true });
  const preguntas = await p.locator("fieldset legend").allInnerTexts();
  console.log("1 · preguntas:", preguntas.length, "·", preguntas.join(" | "));
  await p.getByRole("button", { name: "Usar las respuestas sugeridas y calcular" }).click();
  await p.getByText("Resultado del periodo").waitFor({ timeout: 90000 });
  await p.screenshot({ path: join(salida, "f4-03-resultado.png"), fullPage: true });
  console.log("1 · calculado con las respuestas sugeridas");
  await p.context().close();
}

/* ── 2. varios meses: mes a mes ─────────────────────────────────────────── */
{
  const p = await pagina();
  await p.goto(`${base}/`, { waitUntil: "networkidle" });
  await subirYCrear(p, archivo("01_ventas_compras_bloques.xlsx"));
  await p.getByText("¿Cómo lo proceso?").waitFor({ timeout: 30000 });
  await p.screenshot({ path: join(salida, "f4-04-periodizacion.png"), fullPage: true });
  await p.getByRole("button", { name: "Usar las respuestas sugeridas y calcular" }).click();
  await p.getByText("Procesado periodo a periodo").waitFor({ timeout: 90000 });
  await p.screenshot({ path: join(salida, "f4-05-mes-a-mes.png"), fullPage: true });
  const filas = await p.locator("text=Procesado periodo a periodo").locator("xpath=ancestor::section").locator("li").allInnerTexts();
  console.log("2 · periodos:", filas.map((t) => t.replace(/\s+/g, " ")).join(" | "));
  await p.context().close();
}

/* ── 3. PDF con texto y Word ────────────────────────────────────────────── */
for (const [n, foto] of [["08_balance_de_prueba.pdf", "f4-06-pdf"], ["09_ventas_en_word.docx", "f4-07-word"]]) {
  const p = await pagina();
  await p.goto(`${base}/`, { waitUntil: "networkidle" });
  await subirYCrear(p, archivo(n));
  await p.getByRole("button", { name: "Calcular todo" }).click();
  await p.getByText("Resultado del periodo").waitFor({ timeout: 90000 });
  await p.screenshot({ path: join(salida, `${foto}.png`), fullPage: true });
  const kpis = await p.locator(".t-kpi, .cifras").first().innerText().catch(() => "");
  console.log(`3 · ${n}: calculado (${kpis.trim()})`);
  await p.context().close();
}

/* ── 4. el panel a 390 px ───────────────────────────────────────────────── */
{
  const p = await pagina(390, 844);
  await p.goto(`${base}/`, { waitUntil: "networkidle" });
  await subirYCrear(p, archivo("03_fechas_copiadas_y_futuras.xlsx"));
  await p.getByText("Preguntas sobre este archivo").waitFor({ timeout: 30000 });
  await p.screenshot({ path: join(salida, "f4-08-preguntas-390.png"), fullPage: true });
  const ancho = await p.evaluate(() => document.documentElement.scrollWidth);
  console.log("4 · 390 px: ancho del documento", ancho, ancho <= 390 ? "(sin desborde)" : "(DESBORDA)");
  await p.context().close();
}

await navegador.close();
if (errores.length) {
  console.log("ERRORES DE CONSOLA:", errores);
  process.exit(1);
}
console.log("Sin errores de consola.");
