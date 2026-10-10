// Exploración manual (no es una prueba): recorre una pantalla y guarda capturas en test-results/explorar.
//   node e2e/explorar.mjs <url> <archivo>
import { chromium } from "playwright";
import { mkdirSync } from "node:fs";

const url = process.argv[2] || "http://127.0.0.1:8011";
const archivo = process.argv[3];
const salida = "test-results/explorar";
mkdirSync(salida, { recursive: true });
const b = await chromium.launch();
const page = await b.newPage({ viewport: { width: 1440, height: 900 } });
await page.addInitScript(() => sessionStorage.setItem("cc-preloader-visto", "1"));
let n = 0;
const foto = async (q) => { await page.waitForTimeout(800); await page.screenshot({ path: `${salida}/${String(++n).padStart(2, "0")}-${q}.png`, fullPage: true }); console.log("foto", n, q, page.url()); };
await page.goto(url);
await page.waitForTimeout(1500);
if (await page.getByRole("heading", { name: "Crear su acceso" }).isVisible()) {
  await page.getByLabel("Usuario").fill("carlos");
  await page.getByLabel("Contraseña", { exact: true }).fill("una frase larga de prueba 2026");
  await page.getByLabel("Repita la contraseña").fill("una frase larga de prueba 2026");
  await page.getByRole("button", { name: "Crear el acceso" }).click();
  await page.waitForTimeout(1000);
  const c = page.getByRole("checkbox"); if (await c.count()) await c.first().check();
  await page.getByRole("button", { name: /Ya los guardé|Continuar|Entrar/ }).first().click();
} else if (await page.getByLabel("Usuario").isVisible()) {
  await page.getByLabel("Usuario").fill("carlos");
  await page.getByLabel("Contraseña").fill("una frase larga de prueba 2026");
  await page.getByRole("button", { name: /Ingresar|Entrar/ }).first().click();
}
await page.waitForTimeout(1500);
await foto("tablero");
if (archivo) {
  await page.getByRole("button", { name: "Subir archivo" }).first().click();
  await foto("dialogo-subir");
  const input = page.locator('input[type="file"]').first();
  await input.setInputFiles(archivo);
  for (let i = 0; i < 6; i++) { await page.waitForTimeout(2500); await foto(`tras-subir-${i}`); }
}
await b.close();
