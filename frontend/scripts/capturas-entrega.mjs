#!/usr/bin/env node
/**
 * Capturas «después» para docs/v22/ENTREGA.md, en una copia que SOLO tiene los
 * clientes de demostración (ningún dato real queda en el repositorio).
 *
 *   node scripts/capturas-entrega.mjs http://127.0.0.1:8003 <carpeta-salida>
 */
import { mkdirSync } from "node:fs";
import { join } from "node:path";
import { chromium } from "playwright";
import { conSesion, prepararSesion } from "./sesion.mjs";

const [base, salida] = process.argv.slice(2);
await prepararSesion(base);
mkdirSync(salida, { recursive: true });
const clientes = (await (await fetch(`${base}/api/clientes?estado=&por_pagina=50`)).json()).clientes;
if (clientes.some((c) => !c.demo)) {
  console.error("La copia tiene clientes que no son de demostración: las capturas irían al repositorio. Se detiene.");
  process.exit(1);
}
const pan = clientes.find((c) => c.razon_social.includes("ESPIGA"));
const PAGINAS = [
  ["tablero", "/"], ["clientes", "/clientes"], ["ficha", `/clientes/${pan.id}`],
  ["ficha-estados", `/clientes/${pan.id}?vista=estados`], ["trabajar", "/trabajo"], ["parametros", "/parametros"],
];
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
    p.on("console", (m) => m.type() === "error" && errores.push(m.text()));
    for (const [nombre, ruta] of PAGINAS) {
      if (ancho === 390 && !["tablero", "ficha", "clientes"].includes(nombre)) continue;
      await p.goto(base + ruta, { waitUntil: "networkidle" });
      await p.waitForTimeout(300);
      await p.screenshot({ path: join(salida, `${nombre}-${modo}-${ancho}.jpg`), type: "jpeg", quality: 62, fullPage: ancho === 390 ? false : true });
    }
    await c.close();
  }
}
await navegador.close();
console.log(errores.length ? `ERRORES: ${errores.join(" | ")}` : "Capturas listas, sin errores de consola.");
process.exit(errores.length ? 1 : 0);
