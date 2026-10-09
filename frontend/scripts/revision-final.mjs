#!/usr/bin/env node
/**
 * Revisión final (v2.3 · Fase 7): toda la aplicación, en claro y oscuro, a 1440 y 390 px.
 *
 *   node scripts/revision-final.mjs http://127.0.0.1:8001 <carpeta-salida> [--sin-capturas] [--sin-botones]
 *
 * 1. Cada pantalla y cada pestaña de cada ficha: sin errores de consola, sin
 *    desbordes, con el modo pedido.
 * 2. Cada botón, pestaña y enlace (1440 claro): al pulsarlo algo tiene que pasar
 *    (cambia la página, aparece algo, se descarga o se abre). Los que borran,
 *    archivan, cierran o guardan no se pulsan aquí: los prueban los recorridos de
 *    sus fases; se listan aparte.
 * 3. Cada descarga que ofrece la interfaz responde 200 con un archivo de verdad.
 *
 * Solo contra la copia aislada.
 */
import { mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { chromium } from "playwright";
import { conSesion, prepararSesion } from "./sesion.mjs";

const [base, salida, ...opciones] = process.argv.slice(2);
if (/:8000\b/.test(base ?? "")) {
  console.error("Se niega a correr contra :8000 (la base real).");
  process.exit(1);
}
await prepararSesion(base);
mkdirSync(salida, { recursive: true });
const conCapturas = !opciones.includes("--sin-capturas");
const conBotones = !opciones.includes("--sin-botones");
const conPantallas = !opciones.includes("--solo-botones");
const errores = [];
const json = (ruta) => fetch(base + ruta).then((r) => r.json());

const todos = (await json("/api/clientes?estado=&por_pagina=500")).clientes;
// Los de demostración, los que no son de prueba (FANANT) y tres del banco de archivos (Excel, Word, CSV).
const DEL_BANCO = /01_VENTAS|09_VENTAS_EN_WORD|11_LIBRO_DIARIO/;
const clientes = todos.filter((c) => c.demo || !c.razon_social.startsWith("PRUEBA ") || DEL_BANCO.test(c.razon_social));
console.log(`clientes en la copia: ${clientes.length}`);
// v2.3: el expediente tiene cinco secciones; la contabilidad, una vista por informe y periodo.
const SECCIONES = ["resumen", "contabilidad", "renta", "archivos", "datos"];
const VISTAS_CONTABLES = ["situacion", "resultados", "patrimonio", "flujo", "prueba", "ajustes", "hoja", "definitivo",
  "diario", "mayor", "cuentas_t", "inventario", "nomina", "alertas"];
// /trabajo y /parametros quedan como redirecciones de enlaces viejos.
const rutas = ["/", "/clientes", "/clientes?estado=archivado", "/clientes/nuevo", "/renta", "/trabajo", "/parametros",
  "/diseno", "/no-existe"];
const extraDescargas = new Set(["/api/plantilla", "/api/clientes/plantilla"]);
let conTodasLasVistas = 0;
for (const c of clientes) {
  for (const s of SECCIONES) rutas.push(`/clientes/${c.id}?seccion=${s}`);
  rutas.push(`/clientes/${c.id}/editar`);
  const { periodos = [] } = await json(`/api/clientes/${c.id}/periodos`).catch(() => ({}));
  const guardados = periodos.filter((x) => x.estado !== "borrador");
  // Todas las vistas en el primer periodo de dos clientes (FANANT y una demostración); en el resto, la principal.
  for (const per of guardados.slice(0, 1)) {
    const mes = per.desde.slice(0, 7);
    const vistas = conTodasLasVistas < 2 ? VISTAS_CONTABLES : ["situacion"];
    if (vistas.length > 1) conTodasLasVistas++;
    for (const v of vistas) rutas.push(`/clientes/${c.id}?seccion=contabilidad&periodo=${mes}&vista=${v}`);
    for (const d of ["excel", "pdf", "saldos", "libro-diario/excel", "libro-diario/pdf", "mayor-balances/excel", "mayor-balances/pdf"]) {
      extraDescargas.add(`/api/periodos/${per.id}/${d}`);
    }
  }
}
for (const fila of (await json("/api/renta/cartera?anio=2025").catch(() => ({ declaraciones: [] }))).declaraciones ?? []) {
  if (fila.estado === "sin_informacion" || fila.neto == null) continue; // sin borrador: la interfaz no ofrece descarga
  for (const d of ["pdf", "excel", "resumen"]) extraDescargas.add(`/api/renta/${fila.cliente_id}/${fila.anio}/descargar/${d}`);
}

const navegador = await chromium.launch({ channel: "msedge" });
await conSesion(navegador, base);
const descargas = new Set(extraDescargas);

async function pagina(modo, ancho) {
  const contexto = await navegador.newContext({
    viewport: { width: ancho, height: ancho === 390 ? 844 : 900 },
    reducedMotion: "reduce",
    acceptDownloads: true,
  });
  await contexto.addInitScript((m) => {
    try {
      localStorage.setItem("cc-tema", m);
      sessionStorage.setItem("cc-preloader-visto", "1");
    } catch {}
  }, modo);
  const p = await contexto.newPage();
  p.on("pageerror", (e) => errores.push(`${modo} ${ancho} ${p.url().replace(base, "")}: ${e}`));
  p.on("console", (m) => {
    if (m.type() === "error") errores.push(`${modo} ${ancho} ${p.url().replace(base, "")}: ${m.text()}`);
  });
  return { contexto, p };
}

// ── 1 · todas las pantallas ──────────────────────────────────────────────
let vistas = 0;
const lentas = [];
const tiempos = [];
for (const modo of conPantallas ? ["claro", "oscuro"] : []) {
  for (const ancho of [1440, 390]) {
    const { contexto, p } = await pagina(modo, ancho);
    for (const ruta of rutas) {
      const t0 = Date.now();
      try {
        await p.goto(base + ruta, { waitUntil: "networkidle", timeout: 20000 });
      } catch {
        lentas.push(`${modo} ${ancho} ${ruta}`);
        await p.goto(base + ruta, { waitUntil: "load", timeout: 30000 });
        await p.waitForTimeout(1500);
      }
      tiempos.push([Date.now() - t0, ruta]);
      await p.waitForTimeout(200);
      vistas++;
      const w = await p.evaluate(() => document.documentElement.scrollWidth);
      if (w > ancho + 1) errores.push(`${modo} ${ancho} ${ruta}: desborda (${w} px)`);
      if ((await p.evaluate(() => document.documentElement.dataset.tema)) !== modo) errores.push(`${modo} ${ancho} ${ruta}: modo`);
      for (const h of await p.locator('a[href*="/api/"]').evaluateAll((as) => as.map((a) => a.getAttribute("href")))) {
        if (h) descargas.add(h);
      }
      const conVista = ruta.includes("seccion=");
      const capturar = conCapturas && (ancho === 1440
        ? !conVista || /seccion=(resumen|renta)$|vista=(situacion|resultados)$/.test(ruta)
        : !conVista && !ruta.includes("/editar"));
      if (capturar) {
        const nombre = ruta.replace(/[/?=&]+/g, "_").replace(/^_/, "") || "tablero";
        await p.screenshot({ path: join(salida, `${nombre}-${modo}-${ancho}.jpg`), type: "jpeg", quality: 60, fullPage: true });
      }
    }
    await contexto.close();
    console.log(`1 · ${modo} ${ancho}: ${rutas.length} pantallas`);
  }
}

if (tiempos.length) {
  tiempos.sort((x, y) => y[0] - x[0]);
  console.log(`   carga más lenta: ${tiempos.slice(0, 5).map(([ms, r]) => `${ms} ms ${r}`).join(" · ")}`);
  if (lentas.length) console.log(`   sin calma de red en 20 s (${lentas.length}): ${lentas.slice(0, 5).join(" · ")}`);
}
if (errores.length) {
  console.log(`   errores en las pantallas: ${errores.length}`);
  for (const e of errores.slice(0, 20)) console.log("     ·", e);
}

// ── 2 · cada botón hace algo ────────────────────────────────────────────
const PELIGROSOS = /eliminar|borrar|archivar|restaurar|reabrir|cerrar (el )?periodo|cerrar de todos modos|cerrar sesi|cerrar las dem|importar de verdad|guardar|crear cliente|confirmar|aplicar|usar estos datos|posponer|calcular|subir archivo|registrar|presentada|desactivar|generar c/i;
const omitidos = new Set();
const muertos = [];
let pulsados = 0;
if (conBotones) {
  const { contexto, p } = await pagina("claro", 1440);
  // /diseno es el catálogo de componentes: sus botones son muestras, no acciones.
  const paraBotones = rutas.filter((r) => !r.includes("/editar") && !r.includes("no-existe") && r !== "/diseno");
  // Una ficha de cada tipo basta para los botones (todas comparten componentes).
  const fichas = new Set();
  const lista = paraBotones.filter((r) => {
    const m = r.match(/\/clientes\/([^/?]+)\?seccion=(\w+)(?:.*vista=(\w+))?/);
    if (!m) return true;
    const clave = `${m[2]}:${m[3] ?? ""}`;
    if (fichas.has(clave) && !/ESPIGA|TORNILLO/.test(clientes.find((c) => c.id === m[1])?.razon_social ?? "")) return false;
    fichas.add(clave);
    return true;
  });
  // Carga tolerante: si la red no se calma en 15 s, se sigue con lo que haya.
  const ir = async (ruta) => {
    try {
      await p.goto(base + ruta, { waitUntil: "networkidle", timeout: 15000 });
    } catch {
      await p.goto(base + ruta, { waitUntil: "load", timeout: 30000 });
      await p.waitForTimeout(800);
    }
  };
  for (const ruta of lista) {
    await ir(ruta);
    const total = await p.locator("main button:visible, main a[href]:visible, main [role=tab]:visible, header button:visible").count();
    for (let i = 0; i < total; i++) {
      await ir(ruta);
      const el = p.locator("main button:visible, main a[href]:visible, main [role=tab]:visible, header button:visible").nth(i);
      if (!(await el.count())) continue;
      const nombre = ((await el.getAttribute("aria-label")) || (await el.innerText().catch(() => "")) || (await el.getAttribute("title")) || "").replace(/\s+/g, " ").trim().slice(0, 60);
      if (!nombre) {
        muertos.push(`${ruta}: elemento ${i} sin nombre accesible`);
        continue;
      }
      if (PELIGROSOS.test(nombre)) {
        omitidos.add(nombre);
        continue;
      }
      if (await el.isDisabled().catch(() => false)) continue;
      // Lo que ya está elegido (pestaña actual, mes seleccionado, opción marcada) no tiene que cambiar nada.
      const activo = await el.evaluate((n) => ["aria-selected", "aria-pressed", "aria-checked"].some((a) => n.getAttribute(a) === "true")
        || n.hasAttribute("aria-current")
        // La columna por la que ya está ordenada una tabla (aria-sort en su encabezado).
        || ["ascending", "descending"].includes(n.closest("th")?.getAttribute("aria-sort") ?? ""));
      if (activo) continue;
      const href = await el.getAttribute("href");
      if (href && href.includes("/api/")) continue; // descargas: se prueban en el paso 3
      const antes = p.url();
      await p.evaluate(() => {
        window.__cambios = 0;
        new MutationObserver((m) => (window.__cambios += m.length)).observe(document.body, {
          subtree: true, childList: true, attributes: true, characterData: true,
        });
      });
      let otro = false;
      const alAbrir = () => (otro = true);
      p.once("download", alAbrir);
      p.context().once("page", alAbrir);
      p.once("filechooser", alAbrir);
      await el.click({ timeout: 4000 }).catch((e) => muertos.push(`${ruta}: «${nombre}» no se pudo pulsar (${String(e).split("\n")[0]})`));
      await p.waitForTimeout(500);
      const cambios = await p.evaluate(() => window.__cambios ?? 0).catch(() => 1);
      pulsados++;
      if (!otro && p.url() === antes && cambios === 0) muertos.push(`${ruta}: «${nombre}» no hace nada`);
      p.off("download", alAbrir);
      p.context().off("page", alAbrir);
      p.off("filechooser", alAbrir);
    }
  }
  await contexto.close();
  console.log(`2 · botones pulsados: ${pulsados}; sin efecto: ${muertos.length}`);
  for (const m of muertos) console.log("     ·", m);
  console.log(`   no se pulsan aquí (borran, archivan, cierran o guardan): ${[...omitidos].sort().join(" · ")}`);
  errores.push(...muertos);
}

// ── 3 · cada descarga ───────────────────────────────────────────────────
let buenas = 0;
for (const h of descargas) {
  const url = h.startsWith("http") ? h : base + h;
  const r = await fetch(url);
  const tam = (await r.arrayBuffer()).byteLength;
  const tipo = r.headers.get("content-type") ?? "";
  if (r.status !== 200 || tam < 300) errores.push(`descarga ${h}: ${r.status} · ${tam} bytes`);
  else buenas++;
  void tipo;
}
console.log(`3 · descargas ofrecidas: ${descargas.size}; correctas: ${buenas}`);

await navegador.close();
writeFileSync(join(salida, "resumen.json"), JSON.stringify({ vistas, rutas: rutas.length, pulsados, muertos, omitidos: [...omitidos], descargas: descargas.size, buenas, errores }, null, 2));
if (errores.length) {
  console.log(`ERRORES (${errores.length}):`);
  for (const e of errores.slice(0, 60)) console.log("  ·", e);
  process.exit(1);
}
console.log(`Sin errores: ${vistas} vistas, ${pulsados} botones, ${buenas} descargas.`);
