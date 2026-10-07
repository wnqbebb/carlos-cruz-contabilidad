#!/usr/bin/env node
/**
 * Recorre «Trabajar» de punta a punta y captura cada paso (Fase 6).
 *
 *   node scripts/flujo-trabajo.mjs <url-base> <cliente-id> <carpeta-salida>
 *
 * OJO: calcular GUARDA el periodo en el expediente del cliente. Úsese SOLO
 * contra una instancia de prueba (p. ej. ALMACENAMIENTO=local + CC_SQLITE a
 * un archivo desechable), nunca contra la base real.
 */
import { mkdirSync } from "node:fs";
import { join } from "node:path";
import { chromium } from "playwright";

const [base, cliente, salida] = process.argv.slice(2);
if (!base || !cliente || !salida) {
  console.error("Uso: node scripts/flujo-trabajo.mjs <url-base> <cliente-id> <carpeta-salida>");
  process.exit(1);
}
if (/:8000\b/.test(base)) {
  console.error("Se niega a correr contra :8000 (la base real). Use una instancia de prueba.");
  process.exit(1);
}
mkdirSync(salida, { recursive: true });

const navegador = await chromium.launch({ channel: "msedge" });
const errores = [];
for (const [sufijo, ancho, alto] of [["", 1440, 900], ["-movil", 390, 844]]) {
  const contexto = await navegador.newContext({ viewport: { width: ancho, height: alto }, reducedMotion: "reduce" });
  const p = await contexto.newPage();
  p.on("pageerror", (e) => errores.push(String(e)));
  p.on("console", (m) => m.type() === "error" && errores.push(m.text()));
  const foto = (n) => p.screenshot({ path: join(salida, `${n}${sufijo}.png`), fullPage: true });

  await p.goto(`${base}/trabajo`, { waitUntil: "networkidle" });
  await foto("t01-cliente");

  await p.goto(`${base}/trabajo?cliente=${cliente}`, { waitUntil: "networkidle" });
  await p.waitForTimeout(400);
  await foto("t02-subir");

  // Ejemplo «completo»: lee y deja listo el mapeo.
  await p.getByRole("button", { name: "Cargar", exact: true }).first().click();
  await p.getByText("Mapeo de cuentas al PUC").waitFor({ timeout: 60000 });
  await p.waitForTimeout(400);
  await foto("t03-mapeo");

  await p.getByRole("button", { name: /Calcular todo/ }).click();
  const confirmar = p.getByRole("button", { name: /Calcular de todos modos|Calcular igual|Continuar/ });
  if (await confirmar.count()) await confirmar.first().click();
  await p.getByText("Resultado del periodo").waitFor({ timeout: 120000 });
  await p.waitForTimeout(500);
  await foto("t04-resultado");

  const pasos = p.getByRole("navigation", { name: "Pasos del trabajo" });
  await pasos.getByRole("button", { name: /Balance de prueba/ }).click();
  await p.waitForTimeout(400);
  await foto("t04-balance-prueba");
  await pasos.getByRole("button", { name: /Definitivo/ }).click();
  await p.waitForTimeout(400);
  await foto("t06-definitivo");
  await pasos.getByRole("button", { name: /Estados/ }).click();
  await p.waitForTimeout(500);
  await foto("t07-estados");

  if (!sufijo) {
    await p.emulateMedia({ media: "print" });
    await p.screenshot({ path: join(salida, "t07-impresion.png"), fullPage: true });
    await p.emulateMedia({ media: "screen" });
  }
  await contexto.close();
}
await navegador.close();
console.log(errores.length ? "errores:\n" + errores.join("\n") : "sin errores de consola");
