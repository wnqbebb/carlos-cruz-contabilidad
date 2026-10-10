// Capturas de diseño del rescate (§6.2): claro y oscuro, a 1440 y 390 px.
//   node e2e/capturas-rescate.mjs http://127.0.0.1:8011 carlos "clave"
// Guarda en docs/rescate/diseno/. Usa datos ficticios de demostración (nada real).
import { chromium } from "playwright";
import { mkdirSync } from "node:fs";

const [url = "http://127.0.0.1:8011", usuario = "carlos", clave = "una frase larga de prueba 2026"] = process.argv.slice(2);
const salida = "../docs/rescate/diseno";
mkdirSync(salida, { recursive: true });

const b = await chromium.launch();
const contexto = await b.newContext({ viewport: { width: 1440, height: 900 } });
const page = await contexto.newPage();
await page.addInitScript(() => sessionStorage.setItem("cc-preloader-visto", "1"));
await page.goto(url);
await page.getByLabel("Usuario").fill(usuario);
await page.getByLabel("Contraseña").fill(clave);
await page.getByRole("button", { name: /Ingresar|Entrar/ }).first().click();
await page.waitForSelector("#saludo");

const api = async (ruta) => (await page.request.get(url + ruta)).json();
const lista = (await api("/api/clientes?por_pagina=100")).clientes;
const id = (re) => lista.find((c) => re.test(c.razon_social))?.id;
const panaderia = id(/PANADER/);
const drogueria = id(/DROGUER/);
const renta = (await api("/api/renta/cartera?anio=2025")).declaraciones;
const contribuyenteA = renta.find((f) => /CONTRIBUYENTE A/.test(f.razon_social))?.cliente_id;

const pantallas = [
  ["tablero", "/"],
  ["clientes", "/clientes"],
  ["expediente-resumen", `/clientes/${panaderia}?seccion=resumen`],
  ["expediente-contabilidad", `/clientes/${panaderia}?seccion=contabilidad&vista=situacion`],
  ["expediente-resultados", `/clientes/${panaderia}?seccion=contabilidad&vista=resultados`],
  ["expediente-archivos", `/clientes/${panaderia}?seccion=archivos`],
  ["expediente-datos", `/clientes/${panaderia}?seccion=datos`],
  ["editor-datos", `/clientes/${drogueria}?seccion=contabilidad&vista=datos`],
  ["renta-cartera", "/renta"],
  ["renta-declaracion", `/clientes/${contribuyenteA}?seccion=renta`],
];

for (const esquema of ["light", "dark"]) {
  for (const ancho of [1440, 390]) {
    await page.emulateMedia({ colorScheme: esquema });
    await page.setViewportSize({ width: ancho, height: ancho === 390 ? 844 : 900 });
    for (const [nombre, ruta] of pantallas) {
      await page.goto(url + ruta);
      await page.waitForLoadState("networkidle");
      await page.waitForTimeout(900);
      const archivo = `${salida}/${nombre}-${esquema === "light" ? "claro" : "oscuro"}-${ancho}.png`;
      await page.screenshot({ path: archivo, fullPage: false });
      console.log(archivo);
    }
    // Sistema (menú de la cuenta)
    await page.goto(url + "/");
    await page.getByRole("button", { name: /^CC$|Cuenta|Menú de la cuenta/ }).first().click().catch(() => {});
    await page.getByRole("menuitem", { name: /Sistema/ }).first().click().catch(() => {});
    await page.waitForTimeout(800);
    await page.screenshot({ path: `${salida}/sistema-${esquema === "light" ? "claro" : "oscuro"}-${ancho}.png` });
  }
}
await b.close();
