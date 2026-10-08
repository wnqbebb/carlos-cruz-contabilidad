#!/usr/bin/env node
/**
 * Fase 7 en la interfaz: el tablero del contador.
 *
 *   node scripts/flujo-fase7.mjs http://127.0.0.1:8001 <carpeta-salida>
 *
 * Prepara una cartera pequeña por la API (un cliente sin periodos, uno con un
 * periodo calculado sin cerrar, uno con preguntas sin responder) y comprueba:
 * saludo, cuatro indicadores, tareas con «Hacer ahora» y «Posponer hasta
 * mañana», la cartera mes a mes, recientes y actividad. Claro, 1440 y 390 px.
 *
 * Crea clientes: SOLO contra la copia aislada.
 */
import { mkdirSync, readFileSync } from "node:fs";
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
const post = (ruta, cuerpo) =>
  fetch(base + ruta, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(cuerpo) }).then((r) => r.json());

async function subir(nombre, nit, razon, calcular = true) {
  const fd = new FormData();
  fd.append("archivos", new Blob([readFileSync(join(BANCO, nombre))]), nombre);
  const p = await (await fetch(`${base}/api/subir`, { method: "POST", body: fd })).json();
  const imp = await post(`/api/subir/${p.subida_id}/confirmar`, { crear: { nit, razon_social: razon } });
  if (calcular) {
    const mapeo = Object.fromEntries(imp.mapeo.filter((m) => m.codigo).map((m) => [m.normalizado, m.codigo]));
    await post("/api/calcular", { sesion_id: imp.sesion_id, cliente_id: imp.cliente_id, mapeo, incluir: {}, decisiones: {}, config: {}, empresa: {} });
  }
  return imp;
}

await post("/api/clientes", { nit: "900700001", razon_social: "TIENDA SIN PERIODOS S.A.S.", honorarios_mes: "250000" });
await subir("11_libro_diario.csv", "900700002", "COMERCIAL CON PERIODO S.A.S.");
await subir("03_fechas_copiadas_y_futuras.xlsx", "900700003", "SERVICIOS CON PREGUNTAS S.A.S.", false);

const navegador = await chromium.launch({ channel: "msedge" });
await conSesion(navegador, base);
const errores = [];
const contexto = await navegador.newContext({ viewport: { width: 1440, height: 900 }, reducedMotion: "reduce" });
await contexto.addInitScript(() => {
  try { sessionStorage.setItem("cc-preloader-visto", "1"); } catch {}
});
const p = await contexto.newPage();
p.on("pageerror", (e) => errores.push(String(e)));
p.on("console", (m) => m.type() === "error" && errores.push(m.text()));

await p.goto(`${base}/`, { waitUntil: "networkidle" });
await p.getByText("Qué hacer, en orden").waitFor({ timeout: 20000 });
console.log("1 · saludo:", (await p.locator("#saludo").innerText()).trim());
const indicadores = await p.locator('section[aria-label="Indicadores de la cartera"] > *').allInnerTexts();
console.log("2 · indicadores:", indicadores.map((t) => t.replace(/\s+/g, " ").trim()).join(" | "));
const tareas = await p.locator("#titulo-tareas").locator("xpath=ancestor::section").locator("ol > li").allInnerTexts();
console.log("3 · tareas:", tareas.length);
for (const t of tareas) console.log("     ·", t.replace(/\s+/g, " ").slice(0, 140));
await p.screenshot({ path: join(salida, "f7-01-tablero.png"), fullPage: true });

// Posponer la primera tarea.
const antes = tareas.length;
await p.getByRole("button", { name: "Posponer hasta mañana" }).first().click();
await p.waitForTimeout(800);
const despues = await p.locator("#titulo-tareas").locator("xpath=ancestor::section").locator("ol > li").count();
console.log(`3 · posponer: ${antes} → ${despues} tareas`);
await p.reload({ waitUntil: "networkidle" });
const tras = await p.locator("#titulo-tareas").locator("xpath=ancestor::section").locator("ol > li").count();
console.log("3 · tras recargar sigue pospuesta:", tras === despues ? "sí" : "NO");

// «Hacer ahora» sobre la de preguntas: abre Trabajar con las preguntas del archivo.
const fila = p.locator("ol > li", { hasText: "Responder las preguntas del archivo" });
if (await fila.count()) {
  await fila.getByRole("button", { name: "Hacer ahora" }).click();
  await p.getByText("Preguntas sobre este archivo").waitFor({ timeout: 20000 });
  console.log("3 · «Hacer ahora» abrió la subida con sus preguntas:", p.url().replace(base, ""));
  await p.screenshot({ path: join(salida, "f7-02-hacer-ahora-preguntas.png"), fullPage: true });
}

await p.goto(`${base}/`, { waitUntil: "networkidle" });
const meses = await p.locator('ol[aria-label="Clientes por mes"] > li').count();
console.log("4 · meses en la cartera:", meses);
const actividad = await p.locator("#titulo-actividad").locator("xpath=ancestor::section").locator("ol > li").count();
console.log("5 · líneas de actividad:", actividad);
const recientes = await p.locator("#titulo-recientes").locator("xpath=ancestor::section").locator("ul > li").count();
console.log("6 · carpetas recientes (más «Cliente nuevo»):", recientes);

await p.setViewportSize({ width: 390, height: 844 });
await p.reload({ waitUntil: "networkidle" });
await p.screenshot({ path: join(salida, "f7-03-tablero-390.png"), fullPage: true });
const ancho = await p.evaluate(() => document.documentElement.scrollWidth);
console.log("7 · 390 px: ancho", ancho, ancho <= 390 ? "(sin desborde)" : "(DESBORDA)");
if (ancho > 390) errores.push("desborde a 390 px");

// El preloader toma el municipio de la configuración del contador (H18).
const c2 = await navegador.newContext({ viewport: { width: 1440, height: 900 } });
const p2 = await c2.newPage();
await p2.goto(`${base}/`, { waitUntil: "domcontentloaded" });
await p2.waitForTimeout(600);
await p2.screenshot({ path: join(salida, "f7-04-preloader.png") });
const esquinas = await p2.locator("[data-esquina]").allInnerTexts().catch(() => []);
console.log("8 · preloader:", esquinas.join(" | "));

await navegador.close();
if (errores.length) {
  console.log("ERRORES:", errores);
  process.exit(1);
}
console.log("Sin errores de consola.");
