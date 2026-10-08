#!/usr/bin/env node
/**
 * Capturas de varias rutas en claro/oscuro y 1440/390 px, con errores de consola.
 *
 *   node scripts/capturas-v23.mjs http://127.0.0.1:8001 <carpeta-salida> <ruta>…
 */
import { mkdirSync } from "node:fs";
import { join } from "node:path";
import { chromium } from "playwright";
import { conSesion, prepararSesion } from "./sesion.mjs";

const [base, salida, ...rutas] = process.argv.slice(2);
await prepararSesion(base);
mkdirSync(salida, { recursive: true });
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
    p.on("console", (m) => m.type() === "error" && errores.push(`${modo} ${ancho} ${p.url()}: ${m.text()}`));
    p.on("pageerror", (e) => errores.push(`${modo} ${ancho}: ${e}`));
    p.on("response", (r) => r.status() >= 500 && errores.push(`${modo} ${ancho}: ${r.status()} ${r.url()}`));
    for (const [i, ruta] of rutas.entries()) {
      await p.goto(base + ruta, { waitUntil: "networkidle" });
      await p.waitForTimeout(500);
      const ancho_doc = await p.evaluate(() => document.documentElement.scrollWidth);
      if (ancho_doc > ancho + 1) errores.push(`${modo} ${ancho} ${ruta}: la página se desborda a lo ancho (${ancho_doc} px)`);
      await p.screenshot({ path: join(salida, `${String(i + 1).padStart(2, "0")}-${modo}-${ancho}.png`) });
    }
    await c.close();
  }
}
await navegador.close();
if (errores.length) {
  console.log("ERRORES:", errores);
  process.exit(1);
}
console.log(`Sin errores · ${rutas.length} rutas × 4 variantes.`);
