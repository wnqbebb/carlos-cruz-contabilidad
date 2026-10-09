#!/usr/bin/env node
/**
 * v2.3 · Fase 5: declaración de renta de punta a punta, midiendo tiempo y clics.
 *
 *   node scripts/flujo-v23-renta.mjs http://127.0.0.1:8001 <carpeta-salida> <foto-o-archivo>… [--nit 10000006]
 *
 * Crea una persona natural (o reutiliza la del NIT), abre su sección Renta, suelta los
 * archivos, espera el veredicto y descarga el borrador. Cuenta los clics del contador
 * desde que suelta las fotos hasta tener el borrador (meta: 10 o menos, menos de 5 min).
 * Después recorre Renta⁰³ y la sección en claro/oscuro, 1440/390 px. Solo copia aislada.
 */
import { mkdirSync } from "node:fs";
import { basename, join } from "node:path";
import { chromium } from "playwright";
import { conSesion, prepararSesion } from "./sesion.mjs";

const args = process.argv.slice(2);
const base = args[0];
const salida = args[1];
let nit = "10000006";
let casoA = false;
const archivos = [];
for (let i = 2; i < args.length; i++) {
  if (args[i] === "--nit") nit = args[++i];
  else if (args[i] === "--caso-a") casoA = true;
  else archivos.push(args[i]);
}
if (/:8000\b/.test(base ?? "")) process.exit(1);
await prepararSesion(base);
mkdirSync(salida, { recursive: true });

const lista = await (await fetch(`${base}/api/clientes?q=${nit}&por_pagina=5`)).json();
let cliente = lista.clientes?.find((c) => c.nit === nit);
if (!cliente) {
  cliente = await (await fetch(`${base}/api/clientes`, {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ nit, razon_social: `CONTRIBUYENTE PRUEBA ${nit.slice(-2)}`, tipo_persona: "natural" }),
  })).json();
}

const errores = [];
const navegador = await chromium.launch({ channel: "msedge" });
await conSesion(navegador, base);
const c = await navegador.newContext({ viewport: { width: 1440, height: 900 }, reducedMotion: "reduce", acceptDownloads: true });
await c.addInitScript(() => { localStorage.setItem("cc-tema", "claro"); sessionStorage.setItem("cc-preloader-visto", "1"); });
const p = await c.newPage();
p.on("console", (m) => m.type() === "error" && errores.push(m.text()));
p.on("pageerror", (e) => errores.push(String(e)));
p.on("response", (r) => r.status() >= 500 && errores.push(`${r.status()} ${r.url()}`));

let clics = 0;
await p.goto(`${base}/clientes/${cliente.id}?seccion=renta`, { waitUntil: "networkidle" });
const inicio = Date.now();
// 1 · Suelte todo (elegir archivos = 1 clic)
clics += 1;
await p.getByLabel("Documentos de renta", { exact: true }).setInputFiles(archivos);
await p.getByRole("region", { name: "Veredicto" }).waitFor({ timeout: 240000 });
const veredicto = await p.getByRole("region", { name: "Veredicto" }).innerText();
const cifras = (await p.getByRole("region", { name: "Cifras de la declaración" }).innerText()).replace(/\s+/g, " ");
await p.screenshot({ path: join(salida, "renta-revision-1440.png"), fullPage: true });
// 2 · Revise: las respuestas sugeridas ya vienen marcadas; se confirma en bloque lo seguro (1 clic)
await p.getByText(/Ver las \d+ líneas leídas/).click();
clics += 1;
const confirmar = p.getByRole("button", { name: /Confirmar \d+ valores seguros/ });
if (await confirmar.count()) {
  await confirmar.click();
  clics += 1;
  await p.waitForLoadState("networkidle");
}
if (casoA) {
  // Lo que el contador sabe del negocio (caso A): ingresos 65.400.000, costos 32.800.000 y el 1 % en 48.000.
  for (const [categoria, valor] of [["ingreso_no_laboral", "65400000"], ["costo_no_laboral", "32800000"]]) {
    await p.getByLabel("Qué es").selectOption(categoria);
    clics += 1;
    await p.getByLabel("Valor del dato").fill(valor);
    await p.getByRole("button", { name: "Agregar", exact: true }).click();
    clics += 1;
    await p.waitForLoadState("networkidle");
  }
  await p.getByRole("group", { name: /compras con factura electrónica/ }).getByRole("button", { name: "Sí" }).click();
  clics += 1;
  await p.waitForLoadState("networkidle");
  await p.getByLabel("Valor del 1 % de compras").fill("48000");
  await p.getByLabel("Valor del 1 % de compras").blur();
  await p.waitForLoadState("networkidle");
  const v = await (await fetch(`${base}/api/renta/${cliente.id}/2025`)).json();
  const cas = Object.fromEntries(v.resultado.casillas.map((x) => [x.casilla, x.optimizada]));
  const esperado = { 29: "4600000", 30: "52201000", 31: "0", 58: "117000", 59: "65000", 61: "52000", 74: "65400000",
    77: "32800000", 78: "32600000", 91: "32652000", 92: "48000", 97: "32604000", 116: "0", 132: "5000", 137: "5000" };
  for (const [n, val] of Object.entries(esperado)) if (String(cas[n]) !== val) errores.push(`casilla ${n}: ${cas[n]} ≠ ${val}`);
  console.log("Caso A: casillas del 210 comparadas con la declaración presentada:", errores.length ? "con diferencias" : "iguales");
}
// 3 · Descargue (1 clic)
const [descarga] = await Promise.all([
  p.waitForEvent("download"),
  p.getByRole("link", { name: /Descargar borrador, papel de trabajo y resumen/ }).click(),
]);
clics += 1;
const nombre = descarga.suggestedFilename();
await descarga.saveAs(join(salida, nombre));
const segundos = Math.round((Date.now() - inicio) / 1000);
console.log(`Archivos: ${archivos.map((a) => basename(a)).join(", ")}`);
console.log(`Veredicto: ${veredicto.trim()}`);
console.log(`Cifras: ${cifras}`);
console.log(`De soltar las fotos al borrador: ${segundos} s y ${clics} clics → ${nombre}`);
if (clics > 10) errores.push(`demasiados clics: ${clics}`);
if (segundos > 300) errores.push(`demasiado tiempo: ${segundos} s`);

// Marcar como presentada
await p.getByRole("button", { name: "Marcar como presentada" }).click();
await p.getByLabel("Número de formulario").fill("2118000000001");
await p.getByRole("button", { name: "Guardar" }).click();
await p.getByText("Presentada", { exact: true }).first().waitFor();
await c.close();

// Renta⁰³ y la sección, en claro/oscuro y 1440/390
for (const modo of ["claro", "oscuro"]) {
  for (const ancho of [1440, 390]) {
    const v = await navegador.newContext({ viewport: { width: ancho, height: ancho === 390 ? 844 : 900 }, reducedMotion: "reduce" });
    await v.addInitScript((m) => { localStorage.setItem("cc-tema", m); sessionStorage.setItem("cc-preloader-visto", "1"); }, modo);
    const q = await v.newPage();
    q.on("console", (m) => m.type() === "error" && errores.push(`${modo} ${ancho}: ${m.text()}`));
    q.on("pageerror", (e) => errores.push(`${modo} ${ancho}: ${e}`));
    await q.goto(`${base}/renta`, { waitUntil: "networkidle" });
    await q.getByRole("link", { name: cliente.razon_social }).first().waitFor();
    const nav = await q.getByRole("navigation").first().innerText();
    if (!/Renta/.test(nav)) errores.push(`${modo} ${ancho}: la navegación no tiene Renta`);
    let w = await q.evaluate(() => document.documentElement.scrollWidth);
    if (w > ancho + 1) errores.push(`${modo} ${ancho}: /renta se desborda (${w})`);
    await q.screenshot({ path: join(salida, `renta-cartera-${modo}-${ancho}.png`) });
    await q.goto(`${base}/clientes/${cliente.id}?seccion=renta`, { waitUntil: "networkidle" });
    await q.getByRole("region", { name: "Veredicto" }).waitFor();
    w = await q.evaluate(() => document.documentElement.scrollWidth);
    if (w > ancho + 1) errores.push(`${modo} ${ancho}: la sección Renta se desborda (${w})`);
    await q.screenshot({ path: join(salida, `renta-seccion-${modo}-${ancho}.png`) });
    await v.close();
  }
}
await navegador.close();
if (errores.length) {
  console.log("ERRORES:", errores);
  process.exit(1);
}
console.log("Sin errores.");
