#!/usr/bin/env node
/**
 * Fase 1 en la interfaz: que un periodo cerrado ofrezca «Reabrir y recalcular»
 * y que el historial de versiones se vea y se pueda restaurar.
 *
 *   node scripts/flujo-fase1.mjs http://127.0.0.1:8001 <carpeta-salida>
 *
 * Calcula y guarda, así que SOLO contra la copia aislada.
 */
import { mkdirSync } from "node:fs";
import { join } from "node:path";
import { chromium } from "playwright";
import { conSesion, prepararSesion } from "./sesion.mjs";

const [base, salida] = process.argv.slice(2);
await prepararSesion(base);
if (/:8000\b/.test(base ?? "")) {
  console.error("Se niega a correr contra :8000 (la base real).");
  process.exit(1);
}
mkdirSync(salida, { recursive: true });

const api = async (ruta, opciones) => {
  const r = await fetch(base + ruta, opciones);
  return { estado: r.status, cuerpo: await r.json().catch(() => null) };
};

// Cliente y periodo calculado por la API, para no depender de la pantalla.
const nombre = "HISTORIAL DE PRUEBA S.A.S.";
let { cuerpo: cliente } = await api("/api/clientes", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ nit: "899999061", razon_social: nombre, periodicidad: "mensual" }),
});
if (!cliente?.id) {
  const lista = await api("/api/clientes?q=899999061&estado=");
  cliente = lista.cuerpo.clientes[0];
}
const cid = cliente.id;

const imp = (await api(`/api/importar/demo?cliente_id=${cid}&caso=completo`, { method: "POST" })).cuerpo;
const peticion = {
  sesion_id: imp.sesion_id,
  cliente_id: cid,
  mapeo: Object.fromEntries(imp.mapeo.filter((i) => i.codigo).map((i) => [i.normalizado, i.codigo])),
  incluir: Object.fromEntries(imp.hojas.map((h) => [h.id, h.incluir])),
};
const calc = await api("/api/calcular", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(peticion),
});
console.log("calcular:", calc.estado, "guardado:", calc.cuerpo?.guardado);
await api(`/api/cierre/${imp.sesion_id}`, { method: "POST" });
console.log("periodo cerrado");

const navegador = await chromium.launch({ channel: "msedge" });
await conSesion(navegador, base);
const contexto = await navegador.newContext({ viewport: { width: 1440, height: 900 }, reducedMotion: "reduce" });
await contexto.addInitScript(() => {
  try { sessionStorage.setItem("cc-preloader-visto", "1"); } catch {}
});
const p = await contexto.newPage();
const errores = [];
p.on("pageerror", (e) => errores.push(String(e)));
// El 409 del periodo cerrado es la respuesta esperada: el navegador lo anota igual.
p.on("console", (m) => m.type() === "error" && !/409/.test(m.text()) && errores.push(m.text()));

// ── 1. recalcular un periodo cerrado desde la pantalla ─────────────────────
await p.goto(`${base}/trabajo?cliente=${cid}`, { waitUntil: "networkidle" });
await p.getByRole("button", { name: "Cargar", exact: true }).first().click();
await p.getByText("Mapeo de cuentas al PUC").waitFor({ timeout: 60000 });
await p.getByRole("button", { name: /Calcular todo/ }).click();

const aviso = p.getByText("Ese periodo ya está cerrado");
await aviso.waitFor({ timeout: 60000 });
await p.screenshot({ path: join(salida, "f1-periodo-cerrado.png"), fullPage: true });
console.log("aviso de periodo cerrado: visible");

// Las cifras del periodo siguen intactas mientras no se decida nada.
const antes = (await api(`/api/clientes/${cid}/periodos`)).cuerpo.periodos[0];
console.log("periodo intacto:", antes.estado, antes.total_activo, `${antes.cuentas} cuentas`);

await p.getByRole("button", { name: "Reabrir y recalcular" }).click();
await p.getByText("Resultado del periodo").waitFor({ timeout: 120000 });
console.log("tras reabrir y recalcular: resultado en pantalla");
await p.screenshot({ path: join(salida, "f1-tras-recalcular.png"), fullPage: true });

// ── 2. historial de versiones en la ficha ─────────────────────────────────
await p.goto(`${base}/clientes/${cid}?vista=periodos`, { waitUntil: "networkidle" });
await p.waitForTimeout(800);
await p.getByRole("button", { name: /versiones?$/ }).first().click();
await p.getByText("Versiones guardadas").waitFor({ timeout: 15000 });
await p.screenshot({ path: join(salida, "f1-historial.png"), fullPage: true });
const filas = await p.locator("[role=dialog] li").count();
console.log("versiones listadas:", filas);

await p.getByRole("button", { name: "Restaurar esta versión" }).last().click();
await p.getByText(/restaurado a esa versión/i).waitFor({ timeout: 20000 });
const despues = (await api(`/api/clientes/${cid}/periodos`)).cuerpo;
console.log("tras restaurar:", despues.periodos[0].estado, despues.periodos[0].total_activo,
            "· cierres:", despues.cierres.length);
await p.screenshot({ path: join(salida, "f1-restaurado.png"), fullPage: true });

// ── 3. actividad ──────────────────────────────────────────────────────────
await p.goto(`${base}/clientes/${cid}?vista=actividad`, { waitUntil: "networkidle" });
await p.waitForTimeout(600);
await p.screenshot({ path: join(salida, "f1-actividad.png"), fullPage: true });
const lineas = await p.locator("section li").count();
console.log("líneas de actividad:", lineas);

console.log(errores.length ? "ERRORES:\n" + errores.join("\n") : "sin errores de consola");
await navegador.close();
