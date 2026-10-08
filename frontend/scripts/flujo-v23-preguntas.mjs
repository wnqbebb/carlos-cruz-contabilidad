#!/usr/bin/env node
/**
 * v2.3 · Fase 1: el panel de preguntas con preguntas agrupadas (B3).
 *
 *   node scripts/flujo-v23-preguntas.mjs http://127.0.0.1:8001 <carpeta-salida>
 *
 * Sube «21_muchos_bloques_iguales.xlsx» (once bloques con la misma rareza) y
 * comprueba en claro y oscuro, a 1440 y 390 px, que salen 2 preguntas, que el
 * detalle de un grupo se despliega y que un bloque se puede responder aparte.
 * Solo contra la copia aislada.
 */
import { mkdirSync, readFileSync } from "node:fs";
import { join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";
import { conSesion, prepararSesion } from "./sesion.mjs";

const [base, salida] = process.argv.slice(2);
if (/:8000\b/.test(base ?? "")) process.exit(1);
await prepararSesion(base);
mkdirSync(salida, { recursive: true });
const BANCO = resolve(fileURLToPath(import.meta.url), "../../../backend/tests/archivos_variados");
const nombre = "21_muchos_bloques_iguales.xlsx";
const fd = new FormData();
fd.append("archivos", new Blob([readFileSync(join(BANCO, nombre))]), nombre);
const sub = await (await fetch(`${base}/api/subir`, { method: "POST", body: fd })).json();
const imp = await (await fetch(`${base}/api/subir/${sub.subida_id}/confirmar`, {
  method: "POST", headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ crear: { nit: "900500111", razon_social: "TIENDA ONCE MESES S.A.S." } }),
})).json();
console.log("preguntas:", imp.preguntas.length, "·", imp.preguntas.map((p) => p.titulo).join(" | "));

const errores = [];
const navegador = await chromium.launch({ channel: "msedge" });
await conSesion(navegador, base);
for (const modo of ["claro", "oscuro"]) {
  for (const ancho of [1440, 390]) {
    const c = await navegador.newContext({ viewport: { width: ancho, height: ancho === 390 ? 844 : 900 }, reducedMotion: "reduce" });
    await c.addInitScript((m) => {
      localStorage.setItem("cc-tema", m);
      sessionStorage.setItem("cc-preloader-visto", "1");
    }, modo);
    const p = await c.newPage();
    p.on("console", (m) => m.type() === "error" && errores.push(`${modo} ${ancho}: ${m.text()}`));
    p.on("pageerror", (e) => errores.push(String(e)));
    await p.goto(`${base}/trabajo?cliente=${imp.cliente_id}&sesion=${imp.sesion_id}`, { waitUntil: "networkidle" });
    await p.getByText("Preguntas sobre este archivo").waitFor({ timeout: 20000 });
    await p.getByText(/Ver los 11 bloques/).click();
    const w = await p.evaluate(() => document.documentElement.scrollWidth);
    if (w > ancho) errores.push(`${modo} ${ancho}: desborda (${w})`);
    if (modo === "claro" && ancho === 1440) {
      await p.getByLabel(/Respuesta para .*MARZO/).first().selectOption({ index: 2 });
      const cambio = await p.getByText(/Cambió 1 respuesta/).count();
      console.log("respuesta propia de un bloque:", cambio ? "registrada" : "NO");
      if (!cambio) errores.push("la respuesta por bloque no se registró");
    }
    await p.screenshot({ path: join(salida, `preguntas-${modo}-${ancho}.png`), fullPage: true });
    await c.close();
  }
}
await navegador.close();
if (errores.length) {
  console.log("ERRORES:", errores);
  process.exit(1);
}
console.log("Sin errores.");
