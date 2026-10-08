#!/usr/bin/env node
/**
 * Inventario de la interfaz (v2.3 · Fase 4): cuántas pestañas, botones, tarjetas y
 * bloques de texto ve el contador en cada pantalla. Sirve para medir «antes» y
 * «después» de simplificar.
 *
 *   node scripts/inventario-ui.mjs http://127.0.0.1:8001 <salida.json> <ruta>…
 *
 * Cada ruta se mide tal como abre (sin pulsar nada), a 1440 px y en claro.
 * Cuenta solo lo visible dentro de <main> y de la cabecera de la página.
 */
import { writeFileSync } from "node:fs";
import { chromium } from "playwright";
import { conSesion, prepararSesion } from "./sesion.mjs";

const [base, salida, ...rutas] = process.argv.slice(2);
await prepararSesion(base);
const navegador = await chromium.launch({ channel: "msedge" });
await conSesion(navegador, base);
const c = await navegador.newContext({ viewport: { width: 1440, height: 900 }, reducedMotion: "reduce" });
await c.addInitScript(() => {
  localStorage.setItem("cc-tema", "claro");
  sessionStorage.setItem("cc-preloader-visto", "1");
});
const p = await c.newPage();
const resultado = {};
for (const ruta of rutas) {
  await p.goto(base + ruta, { waitUntil: "networkidle" });
  await p.waitForTimeout(400);
  resultado[ruta] = await p.evaluate(() => {
    const visible = (el) => {
      const r = el.getBoundingClientRect();
      const s = getComputedStyle(el);
      return r.width > 0 && r.height > 0 && s.visibility !== "hidden" && s.display !== "none";
    };
    const raiz = [document.querySelector("main"), document.querySelector(".franja-cabecera")].filter(Boolean);
    const contar = (sel) => raiz.reduce((n, r) => n + [...r.querySelectorAll(sel)].filter(visible).length, 0);
    return {
      pestanas: contar('[role="tab"]'),
      botones: contar('button, a[href].inline-flex, [role="button"]'),
      tarjetas: contar(".material-hoja, .material-expediente, .material-cristal"),
      textos: contar("p"),
    };
  });
  const r = resultado[ruta];
  console.log(`${ruta.padEnd(60)} pestañas ${r.pestanas} · botones ${r.botones} · tarjetas ${r.tarjetas} · textos ${r.textos}`);
}
await navegador.close();
writeFileSync(salida, JSON.stringify(resultado, null, 2));
