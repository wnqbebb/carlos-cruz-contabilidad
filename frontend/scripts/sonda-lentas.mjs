#!/usr/bin/env node
/**
 * Sonda: carga varias veces unas rutas y anota las peticiones que tardan o nunca terminan.
 *
 *   node scripts/sonda-lentas.mjs http://127.0.0.1:8001 <ruta>… [--veces 8]
 *   node scripts/sonda-lentas.mjs http://127.0.0.1:8001 --todas [--veces 2] [--pyspy <pid del servidor>]
 *
 * Sirve para explicar por qué una pantalla no llega a «networkidle». Solo copia aislada.
 */
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";
import { conSesion } from "./sesion.mjs";

const args = process.argv.slice(2);
const base = args[0];
if (/:8000\b/.test(base ?? "")) process.exit(1);
let veces = 8;
let pid = "";
const pyspy = fileURLToPath(new URL("../../.venv/Scripts/py-spy.exe", import.meta.url));
const rutas = [];
for (let i = 1; i < args.length; i++) {
  if (args[i] === "--veces") veces = Number(args[++i]);
  else if (args[i] === "--pyspy") pid = args[++i];
  else if (!args[i].startsWith("--")) rutas.push(args[i]);
}
const navegador = await chromium.launch({ channel: "msedge" });
await conSesion(navegador, base);
if (args.includes("--todas")) {
  rutas.splice(0, rutas.length, "/", "/clientes", "/renta");
  const { clientes } = await (await fetch(`${base}/api/clientes?estado=&por_pagina=500`)).json();
  for (const cl of clientes) {
    for (const s of ["resumen", "contabilidad", "renta", "archivos", "datos"]) rutas.push(`/clientes/${cl.id}?seccion=${s}`);
  }
}
const c = await navegador.newContext({ viewport: { width: 390, height: 844 } });
await c.addInitScript(() => sessionStorage.setItem("cc-preloader-visto", "1"));
const p = await c.newPage();
const abiertas = new Map();
p.on("request", (r) => abiertas.set(r, Date.now()));
const fin = (r) => {
  const t = abiertas.get(r);
  abiertas.delete(r);
  if (t && Date.now() - t > 1500) console.log(`lenta ${Date.now() - t} ms ${r.method()} ${r.url().replace(base, "")}`);
};
p.on("requestfinished", fin);
p.on("requestfailed", (r) => { console.log(`falló ${r.failure()?.errorText} ${r.url().replace(base, "")}`); abiertas.delete(r); });
for (let i = 0; i < veces; i++) {
  for (const ruta of rutas) {
    try {
      await p.goto(base + ruta, { waitUntil: "networkidle", timeout: 15000 });
    } catch {
      console.log(`sin calma: ${ruta} · abiertas: ${[...abiertas.keys()].map((r) => r.url().replace(base, "")).join(" , ")}`);
      if (pid) {
        // Pilas del servidor en ese momento (py-spy), para saber en qué está esperando.
        const { execFileSync } = await import("node:child_process");
        try {
          console.log(execFileSync(pyspy, ["dump", "--pid", pid], { encoding: "utf-8" }));
        } catch (e) {
          console.log(`py-spy: ${e}`);
        }
      }
    }
  }
}
console.log("listo");
await navegador.close();
