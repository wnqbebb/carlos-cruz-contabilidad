#!/usr/bin/env node
/**
 * Fase 3 en la interfaz: una sola puerta.
 *
 *   node scripts/flujo-fase3.mjs http://127.0.0.1:8001 <carpeta-salida>
 *
 * Lo que comprueba, en el navegador y sin tocar ningún endpoint a mano:
 *   1. La contabilidad de un cliente soltada en «Importar directorio de
 *      clientes» ya no deja al contador atascado: se le ofrece la salida.
 *   2. Un Excel con hoja EMPRESA no pregunta nada y se puede crear el cliente
 *      y calcular sin volver a subir el archivo.
 *   3. Un archivo sin identidad pide el NIT y sigue.
 *   4. Arrastrar sobre CUALQUIER pantalla abre la puerta.
 *
 * Crea clientes y calcula: SOLO contra la copia aislada.
 */
import { mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { chromium } from "playwright";

const [base, salida] = process.argv.slice(2);
if (/:8000\b/.test(base ?? "")) {
  console.error("Se niega a correr contra :8000 (la base real).");
  process.exit(1);
}
mkdirSync(salida, { recursive: true });

const api = async (ruta, opciones) => {
  const r = await fetch(base + ruta, opciones);
  return { estado: r.status, cuerpo: await r.json().catch(() => null) };
};

/* Los archivos de prueba salen de la propia aplicación: así el guion no
   depende de ningún archivo concreto del disco. */
const plantilla = Buffer.from(await (await fetch(`${base}/api/plantilla-demo?caso=completo`)).arrayBuffer());
const tmp = join(salida, "archivos");
mkdirSync(tmp, { recursive: true });
const RUTA_PLANTILLA = join(tmp, "contabilidad del cliente.xlsx");
writeFileSync(RUTA_PLANTILLA, plantilla);

const RUTA_DIRECTORIO = join(tmp, "mis clientes.csv");
writeFileSync(
  RUTA_DIRECTORIO,
  "NIT,RAZON SOCIAL,MUNICIPIO\n" +
    "900111222,PANADERIA EL TRIGO S.A.S.,Palmira\n" +
    "900333444,TRANSPORTES DEL SUR LTDA,Tuluá\n" +
    "900555666,DROGUERIA LA SALUD S.A.S.,Buga\n",
  "utf8",
);

/* Una hoja de trabajo en un formato que la aplicación ya reconoce, pero sin
   un solo dato de identidad: ni hoja EMPRESA, ni NIT, ni razón social. Sirve
   para ver que la pantalla pide únicamente el NIT y sigue con el mismo
   archivo, sin pedirlo otra vez. */
const RUTA_ANONIMO = join(tmp, "libro del cliente.csv");
writeFileSync(
  RUTA_ANONIMO,
  "CUENTA,BALANCE INICIAL,,MOVIMIENTO,\n" +
    ",DEBE,HABER,DEBE,HABER\n" +
    "CAJA,500000,0,200000,0\n" +
    "APORTES SOCIALES,0,500000,0,0\n" +
    "VENTAS,0,0,0,200000\n",
  "utf8",
);

const navegador = await chromium.launch({ channel: "msedge" });
const contexto = await navegador.newContext({ viewport: { width: 1440, height: 900 }, reducedMotion: "reduce" });
await contexto.addInitScript(() => {
  try { sessionStorage.setItem("cc-preloader-visto", "1"); } catch {}
});
const p = await contexto.newPage();
const errores = [];
p.on("pageerror", (e) => errores.push(String(e)));
p.on("console", (m) => m.type() === "error" && !/40[09]|422/.test(m.text()) && errores.push(m.text()));

const foto = (n) => p.screenshot({ path: join(salida, `f3-${n}.png`), fullPage: true });

/* ── 1. el defecto original: contabilidad en la puerta del directorio ───── */
await p.goto(`${base}/clientes`, { waitUntil: "networkidle" });
await p.getByRole("button", { name: "Importar directorio de clientes" }).click();
await p.getByText("Carga masiva").waitFor({ timeout: 15000 });
await p.locator('[role=dialog] input[type=file]').setInputFiles(RUTA_PLANTILLA);
await p.getByRole("button", { name: "Revisar sin guardar" }).click();
await p.getByText("Esto no parece una lista de clientes").waitFor({ timeout: 30000 });
await foto("01-contabilidad-en-la-puerta-del-directorio");
console.log("1 · aviso con salida ofrecida: visible");

await p.getByRole("button", { name: "Ver qué trae este archivo" }).click();
await p.getByText("Esto es la contabilidad de un cliente").waitFor({ timeout: 60000 });
await foto("02-reconocida-como-contabilidad");
const nombreDetectado = await p.locator('[role=dialog] input').first().inputValue();
const nitDetectado = await p.locator('[role=dialog] input').nth(1).inputValue();
console.log(`1 · detectado sin preguntar: «${nombreDetectado}» · NIT ${nitDetectado}`);

await p.getByRole("button", { name: "Crear cliente y calcular" }).click();
await p.getByText("Mapeo de cuentas al PUC").waitFor({ timeout: 90000 });
await foto("03-mapeo-sin-volver-a-subir");
console.log("1 · entró a 03 Mapeo sin volver a pedir el archivo");

const creado = (await api(`/api/clientes?q=${encodeURIComponent(nitDetectado)}&estado=`)).cuerpo;
console.log("1 · cliente creado:", creado.clientes[0]?.razon_social, "·", creado.clientes[0]?.nit_formateado);

/* ── 2. un directorio de verdad, por la misma puerta ────────────────────── */
await p.goto(`${base}/`, { waitUntil: "networkidle" });
await p.locator("input[type=file]").first().setInputFiles(RUTA_DIRECTORIO);
await p.getByText("Esto es una lista de clientes").waitFor({ timeout: 30000 });
await foto("04-directorio-desde-el-tablero");
await p.getByRole("button", { name: "Importar al directorio" }).click();
await p.getByText("Clientes importados").waitFor({ timeout: 30000 });
await foto("05-directorio-importado");
const total = (await api("/api/clientes?estado=")).cuerpo.total;
console.log("2 · clientes en el directorio tras importar:", total);

/* ── 3. un archivo sin identidad: pide solo el NIT ──────────────────────── */
await p.getByRole("button", { name: "Cerrar" }).first().click();
await p.goto(`${base}/clientes`, { waitUntil: "networkidle" });
await p.locator("input[type=file]").first().setInputFiles(RUTA_ANONIMO);
await p.getByText("Esto es la contabilidad de un cliente").waitFor({ timeout: 30000 });
const boton = p.getByRole("button", { name: "Crear cliente y calcular" });
console.log("3 · sin NIT el botón está", (await boton.isDisabled()) ? "bloqueado" : "ACTIVO (mal)");
await foto("06-sin-identidad-pide-el-nit");
await p.locator('[role=dialog] input').nth(1).fill("830053105");
await p.locator('[role=dialog] input').first().fill("TALLER SIN PAPELES S.A.S.");
console.log("3 · con el NIT escrito el botón está", (await boton.isDisabled()) ? "BLOQUEADO (mal)" : "activo");
await boton.click();
await p.getByText("Mapeo de cuentas al PUC").waitFor({ timeout: 90000 });
console.log("3 · siguió sin volver a pedir el archivo");
await foto("07-sigue-con-el-nit-escrito");

/* ── 4. se puede soltar sobre cualquier pantalla ────────────────────────── */
await p.goto(`${base}/parametros`, { waitUntil: "networkidle" });
const hayVelo = await p.evaluate(() => {
  const dt = new DataTransfer();
  dt.items.add(new File(["x"], "prueba.xlsx"));
  window.dispatchEvent(new DragEvent("dragenter", { dataTransfer: dt, bubbles: true }));
  return true;
});
await p.waitForTimeout(300);
const velo = await p.getByText("Suelte aquí").isVisible().catch(() => false);
console.log("4 · arrastrar sobre Parámetros muestra «Suelte aquí»:", hayVelo && velo);
if (velo) await foto("08-arrastre-sobre-cualquier-pantalla");

/* ── 5. la misma tarjeta en teléfono (390 px) ───────────────────────────── */
const movil = await contexto.newPage();
await movil.setViewportSize({ width: 390, height: 844 });
await movil.goto(`${base}/clientes`, { waitUntil: "networkidle" });
await movil.locator("input[type=file]").first().setInputFiles(RUTA_ANONIMO);
await movil.getByText("Esto es la contabilidad de un cliente").waitFor({ timeout: 30000 });
await movil.screenshot({ path: join(salida, "f3-09-movil-tarjeta.png"), fullPage: true });
await movil.goto(`${base}/`, { waitUntil: "networkidle" });
await movil.screenshot({ path: join(salida, "f3-10-movil-tablero.png"), fullPage: true });
console.log("5 · capturas a 390 px tomadas");

console.log(errores.length ? "ERRORES:\n" + errores.join("\n") : "sin errores de consola");
await navegador.close();
