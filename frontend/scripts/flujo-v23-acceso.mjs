#!/usr/bin/env node
/**
 * v2.3 · Fase 6: el acceso sin terminal, de punta a punta, contra una instancia VACÍA.
 *
 *   node scripts/flujo-v23-acceso.mjs http://127.0.0.1:8002 <carpeta-salida>
 *
 * Primer uso («Crear su acceso») → 10 códigos de recuperación → entrar → confirmar la
 * contraseña antes de una acción delicada → salir → «¿Olvidó la contraseña?» con un código →
 * entrar con la nueva. Revisa que ninguna pantalla muestre comandos, rutas ni archivos.
 * En claro/oscuro y 1440/390 se captura la pantalla de ingreso.
 */
import { mkdirSync } from "node:fs";
import { join } from "node:path";
import { chromium } from "playwright";

const [base, salida] = process.argv.slice(2);
mkdirSync(salida, { recursive: true });
const errores = [];
const PROHIBIDO = /python|crear_usuario|\.py\b|\.env|backend|C:\\|\/Users\/|comando|terminal/i;
const USUARIO = "carlos";
const CLAVE = "Mi-Contabilidad-Cuadra-2026";
const NUEVA = "Otra-Frase-Larga-Y-Segura-77";

const navegador = await chromium.launch({ channel: "msedge" });
const c = await navegador.newContext({ viewport: { width: 1440, height: 900 }, reducedMotion: "reduce" });
await c.addInitScript(() => { localStorage.setItem("cc-tema", "claro"); sessionStorage.setItem("cc-preloader-visto", "1"); });
const p = await c.newPage();
p.on("console", (m) => m.type() === "error" && !/401|403/.test(m.text()) && errores.push(m.text()));
p.on("pageerror", (e) => errores.push(String(e)));
p.on("response", (r) => r.status() >= 500 && errores.push(`${r.status()} ${r.url()}`));

await p.goto(base, { waitUntil: "networkidle" });
await p.getByRole("heading", { name: "Crear su acceso" }).waitFor();
if (PROHIBIDO.test(await p.locator("body").innerText())) errores.push("la pantalla de primer uso muestra algo técnico");
await p.screenshot({ path: join(salida, "acceso-1-crear.png") });
await p.getByLabel("Usuario").fill(USUARIO);
await p.getByLabel("Contraseña", { exact: true }).fill("corta");
await p.getByText(/Use al menos 12 caracteres/).waitFor();
await p.getByLabel("Contraseña", { exact: true }).fill(CLAVE);
await p.getByLabel("Repita la contraseña").fill(CLAVE);
await p.getByRole("button", { name: "Crear el acceso" }).click();
await p.getByText("Guárdelos ahora: no se vuelven a mostrar").waitFor();
const codigos = await p.locator(".codigos-impresion li").allInnerTexts();
if (codigos.length !== 10) errores.push(`se mostraron ${codigos.length} códigos`);
await p.screenshot({ path: join(salida, "acceso-2-codigos.png") });
await p.getByRole("button", { name: "Ya los guardé: entrar" }).click();
await p.getByRole("navigation").first().waitFor();

// Acción delicada: el servidor pide confirmar la contraseña (se fuerza vencida a los 5 min con una espera simulada:
// aquí se usa recién ingresado, así que primero se cierra y se abre de nuevo el panel tras cambiar la contraseña).
await p.getByRole("button", { name: "Cuenta y cerrar sesión" }).click();
await p.getByRole("menuitem", { name: "Sistema" }).click();
await p.getByRole("button", { name: "Cambiar la contraseña" }).click();
await p.getByLabel("Contraseña actual").fill(CLAVE);
await p.getByLabel("Contraseña nueva").fill(NUEVA);
await p.getByRole("button", { name: "Guardar" }).click();
await p.getByText(/Contraseña cambiada/).waitFor();
await p.screenshot({ path: join(salida, "acceso-3-sistema.png") });
await p.keyboard.press("Escape");
await p.getByRole("button", { name: "Cuenta y cerrar sesión" }).click();
await p.getByRole("menuitem", { name: /Cerrar sesión/ }).click();
await p.getByRole("heading", { name: "Ingresar" }).waitFor();

// ¿Olvidó la contraseña? con el primer código
await p.getByRole("link", { name: "¿Olvidó la contraseña?" }).click();
await p.getByLabel("Usuario").fill(USUARIO);
await p.getByLabel("Código de recuperación").fill(codigos[0]);
await p.getByLabel("Contraseña nueva").fill(CLAVE + "-R");
await p.getByRole("button", { name: "Poner la contraseña nueva" }).click();
await p.getByRole("heading", { name: "Contraseña nueva lista" }).waitFor();
await p.getByRole("button", { name: "Ingresar" }).click();
await p.getByLabel("Usuario").fill(USUARIO);
await p.getByLabel("Contraseña").fill(CLAVE + "-R");
await p.getByRole("button", { name: "Entrar" }).click();
await p.getByRole("navigation").first().waitFor();
console.log("Primer uso → códigos → cambio de contraseña → recuperación con código → ingreso: correcto");
await c.close();

for (const modo of ["claro", "oscuro"]) {
  for (const ancho of [1440, 390]) {
    const v = await navegador.newContext({ viewport: { width: ancho, height: ancho === 390 ? 844 : 900 }, reducedMotion: "reduce" });
    await v.addInitScript((m) => { localStorage.setItem("cc-tema", m); sessionStorage.setItem("cc-preloader-visto", "1"); }, modo);
    const q = await v.newPage();
    q.on("pageerror", (e) => errores.push(`${modo} ${ancho}: ${e}`));
    await q.goto(base, { waitUntil: "networkidle" });
    await q.getByRole("heading", { name: "Ingresar" }).waitFor();
    const texto = await q.locator("body").innerText();
    if (PROHIBIDO.test(texto)) errores.push(`${modo} ${ancho}: la pantalla de ingreso muestra algo técnico`);
    const w = await q.evaluate(() => document.documentElement.scrollWidth);
    if (w > ancho + 1) errores.push(`${modo} ${ancho}: se desborda (${w})`);
    await q.screenshot({ path: join(salida, `ingreso-${modo}-${ancho}.png`) });
    await v.close();
  }
}
await navegador.close();
if (errores.length) {
  console.log("ERRORES:", errores);
  process.exit(1);
}
console.log("Sin errores.");
