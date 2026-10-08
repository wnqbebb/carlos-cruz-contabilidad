#!/usr/bin/env node
/**
 * Capturas de todas las pantallas en claro y oscuro, a 1440 y 390 px (v2.2 · 8.4).
 *
 *   node scripts/capturas-modos.mjs http://127.0.0.1:8001 <carpeta-salida> [--sin-datos]
 *
 * Si la base está vacía, primero arma una cartera pequeña por la API (solo en
 * la copia aislada). Revisa además que no haya errores de consola y que a 390
 * px nada desborde a lo ancho.
 */
import { mkdirSync, readFileSync } from "node:fs";
import { join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";

const [base, salida] = process.argv.slice(2);
if (/:8000\b/.test(base ?? "") && !process.argv.includes("--solo-lectura")) {
  console.error("Se niega a correr contra :8000 (la base real) salvo con --solo-lectura.");
  process.exit(1);
}
mkdirSync(salida, { recursive: true });
const BANCO = resolve(fileURLToPath(import.meta.url), "../../../backend/tests/archivos_variados");
const post = (ruta, cuerpo) =>
  fetch(base + ruta, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(cuerpo) }).then((r) => r.json());

async function sembrar() {
  const lista = await (await fetch(`${base}/api/clientes?estado=`)).json();
  if (lista.total > 0 || process.argv.includes("--solo-lectura")) return;
  for (const [archivo, nit, razon, modo] of [
    ["01_ventas_compras_bloques.xlsx", "900800001", "GRANERO LA COSECHA S.A.S.", "por_periodo"],
    ["11_libro_diario.csv", "900800002", "COMERCIAL DEL VALLE S.A.S.", "unico"],
    ["06_cartera_terceros_desconocidos.xlsx", "900800003", "BEBIDAS DEL NORTE S.A.S.", "unico"],
  ]) {
    const fd = new FormData();
    fd.append("archivos", new Blob([readFileSync(join(BANCO, archivo))]), archivo);
    const p = await (await fetch(`${base}/api/subir`, { method: "POST", body: fd })).json();
    const imp = await post(`/api/subir/${p.subida_id}/confirmar`, { crear: { nit, razon_social: razon } });
    const mapeo = Object.fromEntries(imp.mapeo.filter((m) => m.codigo).map((m) => [m.normalizado, m.codigo]));
    await post("/api/calcular", { sesion_id: imp.sesion_id, cliente_id: imp.cliente_id, mapeo, incluir: {}, decisiones: {},
      config: {}, empresa: {}, periodizacion: modo });
  }
  await post("/api/clientes", { nit: "900800004", razon_social: "TALLER SIN PERIODOS S.A.S.", honorarios_mes: "350000" });
}

await sembrar();
const clientes = (await (await fetch(`${base}/api/clientes?estado=`)).json()).clientes;
const ficha = clientes.find((c) => /GRANERO|FARMACIA|PANADER/.test(c.razon_social)) ?? clientes[0];

const RUTAS = [
  ["tablero", "/"],
  ["clientes", "/clientes"],
  ["ficha", `/clientes/${ficha.id}`],
  ["ficha-estados", `/clientes/${ficha.id}?vista=estados`],
  ["ficha-libro", `/clientes/${ficha.id}?vista=movimientos`],
  ["editor", `/clientes/${ficha.id}/editar`],
  ["nuevo", "/clientes/nuevo"],
  ["trabajar", "/trabajo"],
  ["trabajar-cliente", `/trabajo?cliente=${ficha.id}`],
  ["parametros", "/parametros"],
  ["diseno", "/diseno"],
];

const navegador = await chromium.launch({ channel: "msedge" });
const errores = [];
const desbordes = [];
for (const modo of ["claro", "oscuro"]) {
  for (const [ancho, alto] of [[1440, 900], [390, 844]]) {
    const ctx = await navegador.newContext({ viewport: { width: ancho, height: alto }, reducedMotion: "reduce" });
    await ctx.addInitScript((m) => {
      try {
        sessionStorage.setItem("cc-preloader-visto", "1");
        localStorage.setItem("cc-tema", m);
      } catch {}
    }, modo);
    const p = await ctx.newPage();
    p.on("pageerror", (e) => errores.push(`${modo} ${ancho} · ${String(e)}`));
    p.on("console", (m) => m.type() === "error" && errores.push(`${modo} ${ancho} · ${m.text()}`));
    for (const [nombre, ruta] of RUTAS) {
      await p.goto(base + ruta, { waitUntil: "networkidle" });
      await p.waitForTimeout(500);
      const tema = await p.evaluate(() => document.documentElement.dataset.tema);
      if (tema !== modo) errores.push(`${nombre}: data-tema=${tema}, se esperaba ${modo}`);
      await p.screenshot({ path: join(salida, `${nombre}-${modo}-${ancho}.png`), fullPage: true });
      const w = await p.evaluate(() => document.documentElement.scrollWidth);
      if (w > ancho) desbordes.push(`${nombre} ${modo} ${ancho}: ${w}px`);
    }
    await ctx.close();
  }
}
await navegador.close();
console.log(`${RUTAS.length * 4} capturas en ${salida}`);
if (desbordes.length) console.log("DESBORDES:", desbordes);
if (errores.length) {
  console.log("ERRORES:", errores);
  process.exit(1);
}
if (desbordes.length) process.exit(1);
console.log("Sin errores de consola ni desbordes.");
