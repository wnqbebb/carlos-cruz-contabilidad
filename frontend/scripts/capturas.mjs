#!/usr/bin/env node
/**
 * Capturas de verificación visual (spec: cada fase cierra con capturas).
 *
 *   npm run capturas -- fase-1                 → docs/diseno/capturas/fase-1/
 *   npm run capturas -- fase-1 http://127.0.0.1:8000
 *
 * Necesita la app corriendo (uvicorn sirve dist/). Toma cada pantalla a
 * 1440×900 y 390×844, página completa. Usa Edge del sistema: no descarga
 * navegadores.
 */
import { mkdirSync } from "node:fs";
import { join } from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";

const fase = process.argv[2] ?? "borrador";
const base = (process.argv[3] ?? "http://127.0.0.1:8000").replace(/\/$/, "");
const RAIZ = fileURLToPath(new URL("../..", import.meta.url));
const destino = join(RAIZ, "docs", "diseno", "capturas", fase);
mkdirSync(destino, { recursive: true });

const TAMANOS = [
  { sufijo: "", ancho: 1440, alto: 900 },
  { sufijo: "-movil", ancho: 390, alto: 844 },
];

// La ficha usa el primer cliente que devuelva la API.
let primerCliente = null;
try {
  const r = await fetch(`${base}/api/clientes?limite=1`);
  const datos = await r.json();
  const lista = Array.isArray(datos) ? datos : datos.clientes ?? datos.items ?? [];
  primerCliente = lista[0]?.id ?? null;
} catch {
  console.error(`No responde ${base}. Arranque la app antes de capturar.`);
  process.exit(1);
}

const PANTALLAS = [
  ["01-tablero", "/"],
  ["02-clientes", "/clientes"],
  ["03-trabajar", "/trabajo"],
  ["04-parametros", "/parametros"],
  ...(primerCliente ? [["05-ficha", `/clientes/${primerCliente}`]] : []),
  ["06-catalogo", "/diseno"],
];

const navegador = await chromium.launch({ channel: "msedge" });
for (const t of TAMANOS) {
  const contexto = await navegador.newContext({
    viewport: { width: t.ancho, height: t.alto },
    deviceScaleFactor: 1,
    reducedMotion: "reduce",
  });
  // El preloader solo sale una vez por sesión: se marca como visto.
  await contexto.addInitScript(() => {
    try { sessionStorage.setItem("cc-preloader-visto", "1"); } catch {}
  });
  const pagina = await contexto.newPage();
  for (const [nombre, ruta] of PANTALLAS) {
    await pagina.goto(base + ruta, { waitUntil: "networkidle" });
    await pagina.evaluate(() => document.fonts.ready);
    await pagina.waitForTimeout(700);
    const archivo = join(destino, `${nombre}${t.sufijo}.png`);
    await pagina.screenshot({ path: archivo, fullPage: true });
    // Desborde horizontal = error de maquetación en móvil.
    const desborde = await pagina.evaluate(
      () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
    );
    console.log(`${desborde > 0 ? "✗ desborda " + desborde + "px" : "✓"}  ${archivo}`);
  }
  await contexto.close();
}
await navegador.close();
