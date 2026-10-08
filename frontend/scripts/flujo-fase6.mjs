#!/usr/bin/env node
/**
 * Fase 6 en la interfaz: crear fácil, editar todo.
 *
 *   node scripts/flujo-fase6.mjs http://127.0.0.1:8001 <carpeta-salida> <carpeta-documentos>
 *
 *   1. Cliente nuevo: solo NIT (con DV calculado) y nombre; «Más datos» plegado.
 *   2. «Llenar desde documentos» con un acta en Word: ficha extraída con origen y
 *      confianza; «Usar estos datos» y «Crear cliente».
 *   3. Edición en la cabecera: razón social con guardar y deshacer; periodicidad.
 *   4. «Editar ficha» con un RUT nuevo: muestra qué cambiaría y se aplica.
 *   5. Archivar y restaurar desde la ficha y desde el filtro «Archivados».
 *   6. Tabla de clientes con las columnas del último periodo, ordenable.
 *
 * Crea clientes: SOLO contra la copia aislada.
 */
import { mkdirSync } from "node:fs";
import { join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";
import { conSesion, prepararSesion } from "./sesion.mjs";

const [base, salida, docs] = process.argv.slice(2);
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
p.on("console", (m) => m.type() === "error" && !/40[0-9]|422/.test(m.text()) && errores.push(m.text()));
const foto = (n) => p.screenshot({ path: join(salida, `f6-${n}.png`), fullPage: true });

/* ── 1. formulario mínimo ───────────────────────────────────────────────── */
await p.goto(`${base}/clientes/nuevo`, { waitUntil: "networkidle" });
const visibles = await p.locator("main input:visible").count();
console.log("1 · campos visibles en «Nuevo cliente»:", visibles, "(NIT y nombre, más el selector de archivos oculto)");
await p.getByPlaceholder("900123456").fill("900777111");
await p.getByText("Dígito de verificación: 9").waitFor({ timeout: 5000 });
console.log("1 · DV calculado al escribir: 9");
await foto("01-formulario-minimo");

/* ── 2. llenar desde documentos ─────────────────────────────────────────── */
await p.locator("main input[type=file]").setInputFiles(join(docs, "acta_panes_del_sur.docx"));
await p.getByText("Ficha extraída").waitFor({ timeout: 30000 });
const datos = await p.locator("text=Ficha extraída").locator("xpath=ancestor::section").locator("li").count();
console.log("2 · ficha extraída con", datos, "datos y su origen");
await foto("02-ficha-extraida");
await p.getByRole("button", { name: "Usar estos datos" }).click();
await p.getByRole("button", { name: "Crear cliente" }).click();
await p.waitForURL(/\/clientes\/[0-9a-f-]{20,}/, { timeout: 30000 });
await p.getByRole("heading", { level: 1 }).waitFor();
console.log("2 · cliente creado:", (await p.getByRole("heading", { level: 1 }).innerText()).trim());
await foto("03-ficha-creada");
const id = p.url().match(/clientes\/([0-9a-f-]+)/)[1];
const ficha = await (await fetch(`${base}/api/clientes/${id}`)).json();
console.log(`2 · guardado: sigla ${ficha.sigla} · capital ${ficha.capital_suscrito} · rep. ${ficha.rep_legal} (${ficha.rep_legal_cc}) · socios ${ficha.socios.length}`);

/* ── 3. edición en la cabecera ──────────────────────────────────────────── */
await p.getByRole("button", { name: "Editar razón social" }).click();
const campo = p.getByRole("textbox", { name: "Razón social" });
await campo.fill("PANES DEL SUR DE TULUÁ S.A.S.");
await campo.press("Enter");
await p.getByText("Guardado · Deshacer").first().waitFor({ timeout: 10000 });
console.log("3 · razón social guardada en la cabecera:", (await (await fetch(`${base}/api/clientes/${id}`)).json()).razon_social);
await foto("04-cabecera-editada");
await p.getByText("Guardado · Deshacer").first().click();
await p.waitForTimeout(800);
console.log("3 · deshacer:", (await (await fetch(`${base}/api/clientes/${id}`)).json()).razon_social);
await p.getByRole("button", { name: "Editar periodicidad" }).click();
await p.getByRole("combobox", { name: "Periodicidad" }).selectOption("bimestral");
await p.getByRole("button", { name: "Guardar Periodicidad" }).click();
await p.waitForTimeout(800);
console.log("3 · periodicidad:", (await (await fetch(`${base}/api/clientes/${id}`)).json()).periodicidad);

/* ── 4. editar ficha con un RUT nuevo ───────────────────────────────────── */
await p.goto(`${base}/clientes/${id}/editar`, { waitUntil: "networkidle" });
await p.locator("main input[type=file]").setInputFiles(join(docs, "RUT_panes_del_sur.pdf"));
await p.getByText(/dato\(s\) cambiarían/).waitFor({ timeout: 30000 });
await foto("05-cambios-por-documento");
const cambios = await p.getByText(/dato\(s\) cambiarían/).innerText();
console.log("4 ·", cambios);
await p.getByRole("button", { name: "Aplicar a la ficha" }).click();
await p.getByRole("button", { name: "Guardar ficha" }).click();
await p.waitForURL(new RegExp(`/clientes/${id}$`), { timeout: 30000 });
const tras = await (await fetch(`${base}/api/clientes/${id}`)).json();
console.log(`4 · tras aplicar el RUT: municipio ${tras.municipio} · correo ${tras.email} · responsabilidades ${tras.responsabilidades}`);

/* ── 5. archivar y restaurar ─────────────────────────────────────────────── */
await fetch(`${base}/api/clientes/${id}`, { method: "DELETE" });
await p.reload({ waitUntil: "networkidle" });
await p.getByText("Este cliente está archivado").waitFor({ timeout: 10000 });
await foto("06-archivado");
await p.getByRole("button", { name: "Restaurar cliente" }).click();
await p.waitForTimeout(800);
console.log("5 · restaurado desde la ficha:", (await (await fetch(`${base}/api/clientes/${id}`)).json()).estado);
await fetch(`${base}/api/clientes/${id}`, { method: "DELETE" });
await p.goto(`${base}/clientes?estado=archivado`, { waitUntil: "networkidle" });
await p.getByRole("radio", { name: /Archivados/ }).click().catch(() => {});
await p.getByRole("button", { name: "Restaurar" }).first().click();
await p.waitForTimeout(800);
console.log("5 · restaurado desde «Archivados»:", (await (await fetch(`${base}/api/clientes/${id}`)).json()).estado);

/* ── 6. tabla de clientes con el último periodo ─────────────────────────── */
for (const n of ["11_libro_diario.csv", "05_hojas_vacias.xlsx"]) {
  const fd = new FormData();
  fd.append("archivos", new Blob([await (await import("node:fs/promises")).readFile(join(BANCO, n))]), n);
  const prop = await (await fetch(`${base}/api/subir`, { method: "POST", body: fd })).json();
  const nit = String(900600000 + Math.floor(Math.random() * 99999));
  const imp = await (await fetch(`${base}/api/subir/${prop.subida_id}/confirmar`, {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ crear: { nit, razon_social: `CLIENTE TABLA ${n.slice(0, 2)}` } }),
  })).json();
  const mapeo = Object.fromEntries(imp.mapeo.filter((m) => m.codigo).map((m) => [m.normalizado, m.codigo]));
  await fetch(`${base}/api/calcular`, {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ sesion_id: imp.sesion_id, cliente_id: imp.cliente_id, mapeo, incluir: {}, decisiones: {}, config: {}, empresa: {} }),
  });
}
await p.evaluate(() => localStorage.setItem("cc-clientes-vista", "tabla"));
await p.goto(`${base}/clientes`, { waitUntil: "networkidle" });
await p.getByRole("button", { name: "Ingresos" }).click();
await p.waitForTimeout(1200);
const primeras = await p.locator("tbody tr").evaluateAll((filas) => filas.slice(0, 3).map((f) => f.innerText.replace(/\s+/g, " ").slice(0, 90)));
console.log("6 · ordenado por ingresos:", primeras.join(" | "));
await foto("07-tabla-ultimo-periodo");

/* ── 7. a 390 px ────────────────────────────────────────────────────────── */
await p.setViewportSize({ width: 390, height: 844 });
await p.goto(`${base}/clientes/nuevo`, { waitUntil: "networkidle" });
await foto("08-nuevo-390");
await p.goto(`${base}/clientes/${id}`, { waitUntil: "networkidle" });
await foto("09-ficha-390");
const ancho = await p.evaluate(() => document.documentElement.scrollWidth);
console.log("7 · 390 px: ancho", ancho, ancho <= 390 ? "(sin desborde)" : "(DESBORDA)");
if (ancho > 390) errores.push("desborde a 390 px");

await navegador.close();
if (errores.length) {
  console.log("ERRORES:", errores);
  process.exit(1);
}
console.log("Sin errores de consola.");
