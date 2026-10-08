#!/usr/bin/env node
/**
 * v2.3 · Fase 3: el trabajo completo dentro del expediente, de punta a punta.
 *
 *   node scripts/flujo-v23-trabajo.mjs http://127.0.0.1:8001 <carpeta-salida>
 *
 * Sube «11_libro_diario.csv» a un cliente nuevo, entra por el enlace viejo
 * /trabajo?cliente=…&sesion=… (debe redirigir al expediente), calcula, ve el
 * periodo en Contabilidad y lo cierra con el botón principal. Solo contra la
 * copia aislada.
 */
import { mkdirSync, readFileSync } from "node:fs";
import { join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";
import { conSesion, prepararSesion } from "./sesion.mjs";

const [base, salida] = process.argv.slice(2);
if (/:8000\b/.test(base ?? "")) process.exit(1);
await prepararSesion(base);
mkdirSync(salida, { recursive: true });
const BANCO = resolve(fileURLToPath(import.meta.url), "../../../backend/tests/archivos_variados");
const nombre = "11_libro_diario.csv";
const nit = String(900_000_000 + Math.floor(Math.random() * 99_999_999));
const fd = new FormData();
fd.append("archivos", new Blob([readFileSync(join(BANCO, nombre))]), nombre);
const sub = await (await fetch(`${base}/api/subir`, { method: "POST", body: fd })).json();
const imp = await (await fetch(`${base}/api/subir/${sub.subida_id}/confirmar`, {
  method: "POST", headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ clase: "contabilidad", crear: { nit, razon_social: "COMERCIAL PRUEBA EXPEDIENTE S.A.S." } }),
})).json();
if (!imp.sesion_id) {
  console.log("No se pudo preparar la subida:", imp);
  process.exit(1);
}

const errores = [];
const navegador = await chromium.launch({ channel: "msedge" });
await conSesion(navegador, base);
const c = await navegador.newContext({ viewport: { width: 1440, height: 900 }, reducedMotion: "reduce" });
await c.addInitScript(() => {
  localStorage.setItem("cc-tema", "claro");
  sessionStorage.setItem("cc-preloader-visto", "1");
});
const p = await c.newPage();
p.on("console", (m) => m.type() === "error" && errores.push(m.text()));
p.on("pageerror", (e) => errores.push(String(e)));
p.on("response", (r) => r.status() >= 500 && errores.push(`${r.status()} ${r.url()}`));

await p.goto(`${base}/trabajo?cliente=${imp.cliente_id}&sesion=${imp.sesion_id}`, { waitUntil: "networkidle" });
await p.waitForURL((u) => u.pathname === `/clientes/${imp.cliente_id}`);
const calcular = p.getByRole("button", { name: /Calcular (todo|sin ellas)/ }).first();
await calcular.waitFor({ timeout: 20000 });
await p.screenshot({ path: join(salida, "trabajo-1-preguntas.png") });
await calcular.click();
const periodo = p.getByRole("combobox", { name: "Periodo", exact: true });
await periodo.waitFor({ timeout: 60000 });
console.log("calculado:", await periodo.locator("option:checked").innerText());
await p.getByRole("navigation", { name: "Informes del periodo" }).getByRole("button", { name: "Ajustes", exact: true }).click();
await p.waitForURL((u) => u.searchParams.get("vista") === "ajustes");
await p.screenshot({ path: join(salida, "trabajo-2-ajustes.png") });

const cerrar = p.getByRole("button", { name: "Cerrar periodo" });
await cerrar.click();
const deTodos = p.getByRole("button", { name: "Cerrar de todos modos" });
if (await deTodos.isVisible().catch(() => false)) await deTodos.click();
await p.waitForFunction(() => /cerrado/.test(document.querySelector('select[aria-label="Periodo"] option:checked')?.textContent ?? ""), null, { timeout: 20000 })
  .catch(() => errores.push("el periodo no quedó cerrado"));
if (await cerrar.count()) errores.push("el botón «Cerrar periodo» sigue visible tras cerrar");
console.log("después de cerrar:", await periodo.locator("option:checked").innerText());
await p.screenshot({ path: join(salida, "trabajo-3-cerrado.png") });

await navegador.close();
if (errores.length) {
  console.log("ERRORES:", errores);
  process.exit(1);
}
console.log("Sin errores.");
