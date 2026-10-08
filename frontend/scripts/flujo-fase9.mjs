#!/usr/bin/env node
/**
 * Fase 9 en la interfaz: los cinco clientes históricos de demostración.
 *
 *   node scripts/flujo-fase9.mjs http://127.0.0.1:8001 <carpeta-salida> [--borrar]
 *
 * Supone la copia aislada ya cargada con `python -m demo.generar_historicos`.
 * Recorre Tablero, Clientes, la ficha de cada cliente de demostración (resumen,
 * periodos, estados, libro diario, inventario y nómina) y Parámetros, en claro y
 * en oscuro, a 1440 y 390 px. Comprueba lo que cada cliente debe mostrar
 * (descuadre, causal de disolución, atraso, periodo sin cerrar), las descargas
 * de un periodo, y con `--borrar` el botón «Eliminar clientes de demostración».
 *
 * Con `--borrar` BORRA clientes: SOLO contra la copia aislada.
 */
import { mkdirSync } from "node:fs";
import { join } from "node:path";
import { chromium } from "playwright";

const [base, salida, opcion] = process.argv.slice(2);
if (/:8000\b/.test(base ?? "")) {
  console.error("Se niega a correr contra :8000 (la base real).");
  process.exit(1);
}
mkdirSync(salida, { recursive: true });
const errores = [];
const json = (ruta) => fetch(base + ruta).then((r) => r.json());

const demo = (await json("/api/clientes/demostracion")).clientes;
console.log("clientes de demostración:", demo.map((c) => c.razon_social).join(" · "));
if (demo.length !== 5) errores.push(`se esperaban 5 clientes de demostración y hay ${demo.length}`);
const por = (texto) => demo.find((c) => c.razon_social.includes(texto));

// Lo que cada ficha debe decir (sale de los datos, no está escrito en la interfaz).
const ESPERADO = {
  "ESPIGA DORADA": ["Luz Marina Ospina Rendon"],
  "EL TORNILLO": ["sin cerrar"],
  "SONRISA DEL VALLE": ["descuadr"],
  "RÍO CAUCA": ["por debajo de la mitad del capital suscrito"],
  "MARÍA ELENA": ["Lleva 3 meses sin contabilizar"],
};

// Descargas de un periodo (Panadería, último mes): Excel, PDF, libro diario y mayor.
const pan = por("ESPIGA DORADA");
const periodos = (await json(`/api/clientes/${pan.id}/periodos`)).periodos;
const ultimo = periodos.sort((a, b) => a.desde.localeCompare(b.desde)).at(-1);
for (const ruta of ["excel", "pdf", "libro-diario/excel", "libro-diario/pdf", "mayor-balances/excel", "mayor-balances/pdf"]) {
  const r = await fetch(`${base}/api/periodos/${ultimo.id}/${ruta}`);
  const tam = (await r.arrayBuffer()).byteLength;
  console.log(`descarga ${ruta}: ${r.status} · ${tam} bytes`);
  if (r.status !== 200 || tam < 1000) errores.push(`descarga ${ruta} falló (${r.status})`);
}

const navegador = await chromium.launch({ channel: "msedge" });
for (const modo of ["claro", "oscuro"]) {
  for (const ancho of [1440, 390]) {
    const contexto = await navegador.newContext({
      viewport: { width: ancho, height: ancho === 390 ? 844 : 900 },
      reducedMotion: "reduce",
      colorScheme: modo === "oscuro" ? "dark" : "light",
    });
    await contexto.addInitScript((m) => {
      try {
        sessionStorage.setItem("cc-preloader-visto", "1");
        localStorage.setItem("cc-tema", m);
      } catch {}
    }, modo);
    const p = await contexto.newPage();
    p.on("pageerror", (e) => errores.push(`${modo} ${ancho}: ${e}`));
    p.on("console", (m) => m.type() === "error" && errores.push(`${modo} ${ancho}: ${m.text()}`));
    const foto = async (nombre) => {
      const w = await p.evaluate(() => document.documentElement.scrollWidth);
      if (w > ancho) errores.push(`${modo} ${ancho} ${nombre}: desborda (${w} px)`);
      const tema = await p.evaluate(() => document.documentElement.dataset.tema);
      if (tema !== modo) errores.push(`${modo} ${ancho} ${nombre}: data-tema=${tema}`);
      if (!nombre.startsWith("x-") && (ancho === 1440 || nombre.startsWith("01") || nombre.startsWith("02"))) {
        await p.screenshot({ path: join(salida, `${nombre}-${modo}-${ancho}.jpg`), fullPage: true, type: "jpeg", quality: 70 });
      }
    };

    await p.goto(`${base}/`, { waitUntil: "networkidle" });
    await p.getByText("Qué hacer, en orden").waitFor({ timeout: 20000 });
    if (modo === "claro" && ancho === 1440) {
      const tareas = await p.locator("#titulo-tareas").locator("xpath=ancestor::section").locator("ol > li").allInnerTexts();
      console.log(`tablero: ${tareas.length} tareas`);
      for (const t of tareas) console.log("   ·", t.replace(/\s+/g, " ").slice(0, 120));
    }
    await foto("01-tablero");

    await p.goto(`${base}/clientes`, { waitUntil: "networkidle" });
    await p.getByText("PANADERÍA LA ESPIGA DORADA S.A.S.").first().waitFor({ timeout: 20000 });
    await foto("02-clientes");

    for (const [clave, textos] of Object.entries(ESPERADO)) {
      const c = por(clave);
      const nombre = clave.toLowerCase().replace(/\W+/g, "-");
      for (const vista of ["resumen", "periodos", "estados", "movimientos", "inventario", "nomina"]) {
        await p.goto(`${base}/clientes/${c.id}?vista=${vista}`, { waitUntil: "networkidle" });
        await p.waitForTimeout(250);
        if (vista === "resumen") {
          const cuerpo = await p.locator("main").innerText();
          for (const t of textos) {
            if (!cuerpo.includes(t) && !(await p.content()).includes(t)) errores.push(`${clave}: no aparece «${t}»`);
          }
        }
        if (ancho === 1440 && (vista === "resumen" || vista === "estados" || modo === "claro")) await foto(`03-${nombre}-${vista}`);
        else await foto(`x-${nombre}-${vista}`);
      }
    }

    await p.goto(`${base}/parametros`, { waitUntil: "networkidle" });
    await p.getByRole("heading", { name: "Clientes de demostración" }).waitFor({ timeout: 20000 });
    await foto("04-parametros");
    await contexto.close();
  }
}

if (opcion === "--borrar") {
  const contexto = await navegador.newContext({ viewport: { width: 1440, height: 900 }, reducedMotion: "reduce" });
  await contexto.addInitScript(() => sessionStorage.setItem("cc-preloader-visto", "1"));
  const p = await contexto.newPage();
  p.on("pageerror", (e) => errores.push(String(e)));
  p.on("console", (m) => m.type() === "error" && errores.push(m.text()));
  const reales = (await json("/api/clientes?estado=&por_pagina=500")).clientes.filter((c) => !c.demo).map((c) => c.razon_social);
  await p.goto(`${base}/parametros`, { waitUntil: "networkidle" });
  await p.getByRole("button", { name: "Eliminar clientes de demostración" }).click();
  await p.getByRole("dialog").waitFor();
  const lista = await p.getByRole("dialog").locator("li").allInnerTexts();
  console.log("diálogo lista:", lista.join(" · "));
  await p.screenshot({ path: join(salida, "05-dialogo-eliminar-demo.jpg"), type: "jpeg", quality: 70 });
  await p.getByRole("button", { name: /^Eliminar 5 cliente/ }).click();
  await p.getByText("No hay clientes de demostración cargados.").waitFor({ timeout: 20000 });
  await p.screenshot({ path: join(salida, "06-sin-demo.jpg"), type: "jpeg", quality: 70 });
  const quedan = (await json("/api/clientes?estado=&por_pagina=500")).clientes.map((c) => c.razon_social);
  console.log("quedan:", quedan.join(" · "));
  if (JSON.stringify(quedan.sort()) !== JSON.stringify(reales.sort())) errores.push("el borrado tocó un cliente que no era de demostración");
  await contexto.close();
}

await navegador.close();
if (errores.length) {
  console.log("ERRORES:", errores);
  process.exit(1);
}
console.log("Sin errores de consola ni desbordes.");
