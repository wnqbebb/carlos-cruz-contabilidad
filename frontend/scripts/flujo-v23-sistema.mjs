#!/usr/bin/env node
/**
 * v2.3 · Fase 2: sin pantalla Parámetros; panel «Sistema» en el menú de la cuenta.
 *
 *   node scripts/flujo-v23-sistema.mjs http://127.0.0.1:8001 <carpeta-salida>
 */
import { mkdirSync } from "node:fs";
import { join } from "node:path";
import { chromium } from "playwright";
import { conSesion, prepararSesion } from "./sesion.mjs";

const [base, salida] = process.argv.slice(2);
await prepararSesion(base);
mkdirSync(salida, { recursive: true });
const errores = [];
const PROHIBIDO = /supabase|sqlite|postgres|jnyakmcnplrhnpvkunfq|\.env|python |backend\/|C:\\|\/Users\//i;
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
    await p.goto(`${base}/parametros`, { waitUntil: "networkidle" });
    await p.waitForURL((u) => new URL(u).pathname === "/", { timeout: 8000 })
      .catch(() => errores.push(`${modo} ${ancho}: /parametros no redirige al Tablero`));
    const nav = await p.getByRole("navigation").first().innerText();
    if (/Parámetros/.test(nav)) errores.push(`${modo} ${ancho}: la navegación todavía dice Parámetros`);
    await p.getByRole("button", { name: "Cuenta y cerrar sesión" }).click();
    await p.getByRole("menuitem", { name: "Sistema" }).click();
    const dialogo = p.getByRole("dialog");
    await dialogo.getByText(/funcionando|conectado|Sin conexión/).waitFor();
    const texto = await dialogo.innerText();
    if (PROHIBIDO.test(texto)) errores.push(`${modo} ${ancho}: el panel muestra algo técnico: ${texto.match(PROHIBIDO)[0]}`);
    const cuerpo = await p.locator("body").innerText();
    if (/Parámetros/.test(cuerpo)) errores.push(`${modo} ${ancho}: aún aparece «Parámetros» en pantalla`);
    await p.screenshot({ path: join(salida, `sistema-${modo}-${ancho}.png`) });
    if (modo === "claro" && ancho === 1440) console.log("panel Sistema:", texto.replace(/\s+/g, " ").slice(0, 200));
    await c.close();
  }
}
await navegador.close();
if (errores.length) {
  console.log("ERRORES:", errores);
  process.exit(1);
}
console.log("Sin errores.");
