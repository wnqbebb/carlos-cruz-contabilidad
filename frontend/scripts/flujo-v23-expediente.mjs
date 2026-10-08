#!/usr/bin/env node
/**
 * v2.3 · Fase 3: Clientes y Trabajar unificados en el expediente.
 *
 *   node scripts/flujo-v23-expediente.mjs http://127.0.0.1:8001 <cliente-id con ≥12 periodos> <carpeta-salida>
 *
 * - Sin «Trabajar» en la navegación; /trabajo?cliente=X y ?vista= viejos redirigen.
 * - Se recorren 12 meses hacia atrás desde Resultados, Balance definitivo y Libro
 *   diario: el informe elegido no cambia y la página no salta.
 * - Claro y oscuro, 1440 y 390 px, sin errores de consola ni del servidor.
 */
import { mkdirSync } from "node:fs";
import { join } from "node:path";
import { chromium } from "playwright";
import { conSesion, prepararSesion } from "./sesion.mjs";

const [base, cliente, salida] = process.argv.slice(2);
await prepararSesion(base);
mkdirSync(salida, { recursive: true });
const errores = [];
const navegador = await chromium.launch({ channel: "msedge" });
await conSesion(navegador, base);

const VISTAS = [
  ["resultados", "Resultados"],
  ["definitivo", "Balance definitivo"],
  ["diario", "Libro diario"],
];

for (const modo of ["claro", "oscuro"]) {
  for (const ancho of [1440, 390]) {
    const etiqueta = `${modo} ${ancho}`;
    const c = await navegador.newContext({ viewport: { width: ancho, height: ancho === 390 ? 844 : 900 }, reducedMotion: "reduce" });
    await c.addInitScript((m) => {
      localStorage.setItem("cc-tema", m);
      sessionStorage.setItem("cc-preloader-visto", "1");
    }, modo);
    const p = await c.newPage();
    p.on("console", (m) => m.type() === "error" && errores.push(`${etiqueta}: ${m.text()}`));
    p.on("pageerror", (e) => errores.push(`${etiqueta}: ${e}`));
    p.on("response", (r) => r.status() >= 500 && errores.push(`${etiqueta}: ${r.status()} ${r.url()}`));

    // Enlaces viejos
    await p.goto(`${base}/trabajo?cliente=${cliente}`, { waitUntil: "networkidle" });
    await p.waitForURL((u) => u.pathname === `/clientes/${cliente}` && u.searchParams.get("seccion") === "contabilidad", { timeout: 8000 })
      .catch(() => errores.push(`${etiqueta}: /trabajo?cliente= no lleva a la contabilidad del cliente (${p.url()})`));
    await p.goto(`${base}/clientes/${cliente}?vista=nomina`, { waitUntil: "networkidle" });
    await p.waitForURL((u) => u.searchParams.get("seccion") === "contabilidad" && u.searchParams.get("vista") === "nomina", { timeout: 8000 })
      .catch(() => errores.push(`${etiqueta}: ?vista=nomina no se traduce (${p.url()})`));

    await p.goto(`${base}/clientes/${cliente}`, { waitUntil: "networkidle" });
    const nav = await p.getByRole("navigation").first().innerText();
    if (/Trabajar/.test(nav)) errores.push(`${etiqueta}: la navegación todavía dice Trabajar`);
    const selPeriodo = p.getByRole("combobox", { name: "Periodo", exact: true });
    await selPeriodo.waitFor({ timeout: 15000 });
    const pestanas = await p.getByRole("tab").count();
    if (pestanas > 5) errores.push(`${etiqueta}: ${pestanas} pestañas (máximo 5)`);

    const recorrido = modo === "claro" && ancho === 1440 ? 11 : 3;
    for (const [vista, texto] of VISTAS) {
      await p.goto(`${base}/clientes/${cliente}?seccion=contabilidad`, { waitUntil: "networkidle" });
      await selPeriodo.waitFor();
      if (ancho >= 900) await p.getByRole("navigation", { name: "Informes del periodo" }).getByRole("button", { name: texto, exact: true }).click();
      else await p.getByRole("combobox", { name: "Informe del periodo" }).selectOption(vista);
      await p.waitForURL((u) => u.searchParams.get("vista") === vista);
      await p.waitForLoadState("networkidle");
      await p.mouse.wheel(0, 500);
      await p.waitForTimeout(300);
      for (let i = 0; i < recorrido; i++) {
        const antes = await p.evaluate(() => window.scrollY);
        const periodoAntes = await selPeriodo.inputValue();
        const atras = p.getByRole("button", { name: "Periodo anterior" });
        if (await atras.isDisabled()) {
          errores.push(`${etiqueta}: ${vista} se quedó sin periodos anteriores en el paso ${i + 1}`);
          break;
        }
        await atras.click();
        await p.waitForFunction((v) => document.querySelector('select[aria-label="Periodo"]')?.value !== v, periodoAntes);
        await p.waitForLoadState("networkidle");
        await p.waitForTimeout(150);
        const url = new URL(p.url());
        if (url.searchParams.get("vista") !== vista) errores.push(`${etiqueta}: al cambiar de mes la vista pasó de ${vista} a ${url.searchParams.get("vista")}`);
        const despues = await p.evaluate(() => window.scrollY);
        const alto = await p.evaluate(() => document.documentElement.scrollHeight - window.innerHeight);
        // La página no salta al inicio: conserva la posición (salvo que el mes nuevo sea más corto).
        if (Math.abs(despues - antes) > 4 && despues < alto - 4) {
          errores.push(`${etiqueta}: ${vista} saltó de ${antes} a ${despues} px al cambiar de mes`);
        }
      }
      if (modo === "claro" && ancho === 1440) console.log(`${vista}: ${recorrido} meses recorridos, termina en ${await selPeriodo.locator("option:checked").innerText()}`);
      await p.screenshot({ path: join(salida, `expediente-${vista}-${modo}-${ancho}.png`) });
    }
    await c.close();
  }
}
await navegador.close();
if (errores.length) {
  console.log("ERRORES:", errores);
  process.exit(1);
}
console.log("Sin errores.");
