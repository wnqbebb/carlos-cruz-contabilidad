#!/usr/bin/env node
/** Captura de página completa de una ruta: node scripts/captura.mjs <base> <ruta> <png> [ancho] [claro|oscuro] */
import { chromium } from "playwright";
import { conSesion, prepararSesion } from "./sesion.mjs";
const [base, ruta, archivo, ancho = "1440", modo = "claro"] = process.argv.slice(2);
await prepararSesion(base);
const n = await chromium.launch({ channel: "msedge" });
await conSesion(n, base);
const c = await n.newContext({ viewport: { width: +ancho, height: 900 }, reducedMotion: "reduce" });
await c.addInitScript((m) => { localStorage.setItem("cc-tema", m); sessionStorage.setItem("cc-preloader-visto", "1"); }, modo);
const p = await c.newPage();
await p.goto(base + ruta, { waitUntil: "networkidle" });
await p.waitForTimeout(600);
await p.screenshot({ path: archivo, fullPage: true });
await n.close();
