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
 * Con DETALLE=1 imprime qué elementos contó.
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
  p.on("console", (m) => process.env.DETALLE && m.type() === "log" && console.log(m.text()));
  resultado[ruta] = await p.evaluate((detalle) => {
    // `checkVisibility` deja fuera lo plegado en <details> cerrados (content-visibility),
    // que getBoundingClientRect sí mide.
    const visible = (el) => {
      const r = el.getBoundingClientRect();
      return r.width > 0 && r.height > 0 && el.checkVisibility({ contentVisibilityAuto: true, visibilityProperty: true, opacityProperty: false });
    };
    const raiz = [document.querySelector("main"), document.querySelector(".franja-cabecera")].filter(Boolean);
    const contar = (sel) => raiz.reduce((n, r) => n + [...r.querySelectorAll(sel)].filter(visible).length, 0);
    if (detalle) {
      const ver = (sel) => raiz.flatMap((r) => [...r.querySelectorAll(sel)].filter(visible))
        .map((e) => `${e.tagName.toLowerCase()}: ${(e.getAttribute("aria-label") || e.textContent || "").trim().slice(0, 50)}`);
      console.log(JSON.stringify({ botones: ver('button, a[href].inline-flex, [role="button"]'), textos: ver("p") }, null, 1));
    }
    return {
      pestanas: contar('[role="tab"]'),
      botones: contar('button, a[href].inline-flex, [role="button"]'),
      tarjetas: contar(".material-hoja, .material-expediente, .material-cristal"),
      textos: contar("p"),
    };
  }, !!process.env.DETALLE);
  const r = resultado[ruta];
  console.log(`${ruta.padEnd(60)} pestañas ${r.pestanas} · botones ${r.botones} · tarjetas ${r.tarjetas} · textos ${r.textos}`);
}
await navegador.close();
writeFileSync(salida, JSON.stringify(resultado, null, 2));
