#!/usr/bin/env node
/**
 * Inicio de sesión en la interfaz (A2).
 *
 *   node scripts/flujo-sesion.mjs http://127.0.0.1:8001 <carpeta-salida>
 *
 * Sin cookie se ve solo la pantalla de ingreso (claro y oscuro, 1440 y 390 px);
 * una contraseña equivocada muestra el error; la buena abre el Tablero; si la
 * sesión se pierde a mitad de camino, la aplicación vuelve al ingreso; «Cerrar
 * sesión» desde el menú de la cuenta también.
 */
import { mkdirSync } from "node:fs";
import { join } from "node:path";
import { chromium } from "playwright";
import { CLAVE, USUARIO } from "./sesion.mjs";

const [base, salida] = process.argv.slice(2);
mkdirSync(salida, { recursive: true });
const errores = [];
const navegador = await chromium.launch({ channel: "msedge" });

for (const modo of ["claro", "oscuro"]) {
  for (const ancho of [1440, 390]) {
    const c = await navegador.newContext({ viewport: { width: ancho, height: ancho === 390 ? 844 : 900 }, reducedMotion: "reduce" });
    await c.addInitScript((m) => {
      try {
        localStorage.setItem("cc-tema", m);
        sessionStorage.setItem("cc-preloader-visto", "1");
      } catch {}
    }, modo);
    const p = await c.newPage();
    // Sin sesión la API responde 401 a propósito: eso no es un error de la página.
    p.on("console", (m) => m.type() === "error" && !/401/.test(m.text()) && errores.push(`${modo} ${ancho}: ${m.text()}`));
    p.on("pageerror", (e) => errores.push(String(e)));
    await p.goto(`${base}/clientes`, { waitUntil: "networkidle" });
    await p.getByRole("heading", { name: "Ingresar" }).waitFor({ timeout: 15000 });
    const w = await p.evaluate(() => document.documentElement.scrollWidth);
    if (w > ancho) errores.push(`${modo} ${ancho}: la pantalla de ingreso desborda (${w})`);
    if ((await p.evaluate(() => document.documentElement.dataset.tema)) !== modo) errores.push(`${modo} ${ancho}: tema`);
    await p.screenshot({ path: join(salida, `ingreso-${modo}-${ancho}.png`) });
    await c.close();
  }
}

const c = await navegador.newContext({ viewport: { width: 1440, height: 900 }, reducedMotion: "reduce" });
await c.addInitScript(() => sessionStorage.setItem("cc-preloader-visto", "1"));
const p = await c.newPage();
p.on("console", (m) => m.type() === "error" && !/401/.test(m.text()) && errores.push(m.text()));
p.on("pageerror", (e) => errores.push(String(e)));
await p.goto(`${base}/clientes`, { waitUntil: "networkidle" });
await p.getByLabel("Usuario").fill(USUARIO);
await p.getByLabel("Contraseña").fill("equivocada");
await p.getByRole("button", { name: "Entrar" }).click();
await p.getByRole("alert").waitFor();
console.log("1 · clave equivocada:", await p.getByRole("alert").innerText());
await p.screenshot({ path: join(salida, "ingreso-error.png") });

await p.getByLabel("Contraseña").fill(CLAVE);
await p.getByRole("button", { name: "Entrar" }).click();
await p.waitForURL(/\/clientes/);
await p.getByText("Ingresar").waitFor({ state: "detached", timeout: 15000 }).catch(() => undefined);
await p.locator("main").first().waitFor();
console.log("2 · tras ingresar quedó en:", p.url().replace(base, ""), "·", (await p.title()).trim());

// La sesión se pierde (otra pestaña cerró sesión, venció): la siguiente consulta lleva al ingreso.
await c.clearCookies();
await p.goto(`${base}/parametros`, { waitUntil: "networkidle" });
await p.getByRole("heading", { name: "Ingresar" }).waitFor({ timeout: 15000 });
console.log("3 · sin cookie a mitad de camino: vuelve al ingreso");

await p.getByLabel("Usuario").fill(USUARIO);
await p.getByLabel("Contraseña").fill(CLAVE);
await p.getByRole("button", { name: "Entrar" }).click();
await p.getByRole("button", { name: "Cuenta y cerrar sesión" }).click();
await p.getByRole("menu").waitFor();
console.log("4 · menú:", (await p.getByRole("menu").innerText()).replace(/\s+/g, " "));
await p.screenshot({ path: join(salida, "menu-cuenta.png") });
await p.getByRole("menuitem", { name: "Cerrar sesión" }).click();
await p.getByRole("heading", { name: "Ingresar" }).waitFor({ timeout: 15000 });
const estado = await p.evaluate(() => fetch("/api/sesion").then((r) => r.json()));
console.log("5 · tras cerrar sesión:", JSON.stringify(estado));
if (estado.activa) errores.push("la sesión siguió activa después de cerrar sesión");

await navegador.close();
if (errores.length) {
  console.log("ERRORES:", errores);
  process.exit(1);
}
console.log("Sin errores.");
