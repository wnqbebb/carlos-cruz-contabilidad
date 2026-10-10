import { expect, test, type Page } from "@playwright/test";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { CLAVE, DEMO, Recorrido, python, sinAnimacionDeEntrada } from "./ayuda";

test.beforeEach(async ({ page }) => sinAnimacionDeEntrada(page));

/** Lo que está impreso en el papel de la Contribuyente A (tabla anonimizada de PROMPT_V23 §5.10). */
const CASO_A = JSON.parse(readFileSync(join(DEMO, "..", "..", "backend", "tests", "renta", "caso_a.json"), "utf-8"));
const difiere = (a: string, b: string) => [...a].filter((ch, i) => ch !== b[i]).length;

const ESPERADO_210: Record<number, number> = {
  29: 4_600_000, 30: 52_201_000, 74: 65_400_000, 77: 32_800_000, 111: 32_604_000, 116: 0, 132: 5_000, 137: 5_000,
};

async function casillas(page: Page, cid: string): Promise<Record<number, number>> {
  const v = await (await page.request.get(`/api/renta/${cid}/2025`)).json();
  return Object.fromEntries(v.resultado.casillas.map((c: { casilla: number; optimizada: string }) => [c.casilla, Number(c.optimizada)]));
}

/** Escribe la contraseña si la aplicación la pide (acciones delicadas). */
async function contrasenaSiLaPide(page: Page) {
  const dialogo = page.getByRole("dialog", { name: "Confirme su contraseña" });
  if (await dialogo.waitFor({ state: "visible", timeout: 5_000 }).then(() => true).catch(() => false)) {
    await dialogo.getByLabel("Contraseña").fill(CLAVE);
    await dialogo.getByRole("button", { name: "Confirmar" }).click();
  }
}

/**
 * J7 · Renta con foto legible: soltar la foto en Renta⁰³ → la pantalla dice qué falta → confirmar las filas →
 * responder la pregunta → ingresos y costos del negocio y el 1 % de compras → casillas = 210 presentado → ZIP.
 */
test("J7 · renta de la Contribuyente A desde la foto hasta el ZIP", async ({ page }) => {
  const r = new Recorrido(page, "J7", "Renta con foto legible");
  await page.goto("/renta");
  await page.getByLabel("Archivos de exógena").setInputFiles(join(DEMO, "renta", "contribuyente_a_foto.jpg"));
  await expect(page).toHaveURL(/\/clientes\/[0-9a-f-]+\?seccion=renta/, { timeout: 180_000 });
  const cid = page.url().match(/clientes\/([0-9a-f-]{36})/)![1];

  // La pantalla dice exactamente qué falta, arriba, con un botón por cosa.
  const caja = page.getByRole("region", { name: /Para terminar/ });
  await expect(caja).toBeVisible({ timeout: 60_000 });
  await expect(caja.getByText("Ingresos y costos del negocio")).toBeVisible();
  await expect(caja.getByText(/Consignaciones 93,1 M · Facturación 4,8 M/)).toBeVisible();
  await expect(page.getByText(/Se calculará cuando se completen los datos/).first()).toBeVisible();
  await r.captura("que-falta");

  // 1. Confirmar las filas dudosas, con el recorte de la foto al lado.
  const confirmarFilas = caja.getByRole("button", { name: "Revisar y confirmar" });
  if (await confirmarFilas.count()) {
    await r.clic(confirmarFilas);
    const dialogo = page.getByRole("dialog", { name: /Confirmar \d+ fila/ });
    await expect(dialogo.getByRole("img").first()).toBeVisible();
    await r.captura("confirmar-filas");
    // Como el contador: compara cada valor con el recorte del papel y corrige lo que el lector leyó mal
    // (las filas impresas dos veces son justamente las que la app manda a confirmar).
    const papel = CASO_A.lineas.map((l: { valor: string }) => l.valor);
    const campos = dialogo.getByRole("textbox");
    for (let i = 0; i < (await campos.count()); i++) {
      const leido = await campos.nth(i).inputValue();
      if (papel.includes(leido)) continue;
      const parecido = papel.filter((v: string) => v.length === leido.length)
        .sort((a: string, b: string) => difiere(a, leido) - difiere(b, leido))[0];
      if (parecido) await campos.nth(i).fill(parecido);
    }
    await r.clic(dialogo.getByRole("button", { name: "Confirmar todas" }));
    await expect(dialogo).toBeHidden();
  }

  // 2. Responder las preguntas (un toque cada una).
  const preguntas = page.getByRole("region", { name: "Por confirmar" }).getByRole("group");
  for (let i = 0; i < (await preguntas.count()); i++) {
    const opcion = preguntas.nth(i).getByRole("button", { pressed: true }).first();
    await r.clic(opcion.or(preguntas.nth(i).getByRole("button").first()).first());
  }

  // 3. Lo que solo usted sabe: el negocio.
  const negocio = page.getByRole("region", { name: "Lo que solo usted sabe" });
  await negocio.getByLabel("Ingresos del negocio en el año").fill("65400000");
  await negocio.getByLabel("Costos y gastos del negocio").fill("32800000");
  await r.clic(negocio.getByRole("button", { name: "Guardar ingresos y costos" }));
  await expect(page.getByText("Ingresos y costos del negocio", { exact: true })).toHaveCount(1);   // ya no en «falta»

  // 4. El 1 % de compras con factura electrónica: lo que decidió el contador (48.000).
  const menos = page.getByRole("region", { name: "¿Podemos pagar menos?" });
  const grupo = menos.getByRole("group", { name: /factura electr/i });
  await r.clic(grupo.getByRole("button", { name: "Sí" }));
  const uno = menos.getByLabel("Valor del 1 % de compras");
  await uno.fill("48000");
  await uno.blur();

  // Las casillas coinciden con el 210 presentado.
  await expect.poll(async () => {
    const c = await casillas(page, cid);
    return Object.entries(ESPERADO_210).every(([n, v]) => c[Number(n)] === v);
  }, { timeout: 60_000 }).toBe(true);
  await expect(page.getByRole("region", { name: /Para terminar/ })).toHaveCount(0);
  await expect(page.getByText("Le devuelven").first()).toBeVisible();
  await expect(page.getByText("$ 5.000").first()).toBeVisible();
  await expect(page.getByRole("heading", { name: /Por qué su declaración es distinta/ })).toBeVisible();
  await r.captura("borrador-completo");

  // 5. Descargar el ZIP (pide la contraseña: es una acción delicada).
  const [zip] = await Promise.all([
    page.waitForEvent("download", { timeout: 60_000 }),
    (async () => {
      await r.clic(page.getByRole("button", { name: /Descargar (todo|borrador, papel de trabajo y resumen)/ }));
      await contrasenaSiLaPide(page);
    })(),
  ]);
  const ruta = (await zip.path())! + ".zip";
  await zip.saveAs(ruta);
  const contenido = await python([
    "import sys, json, zipfile",
    "z = zipfile.ZipFile(sys.argv[1])",
    "print(json.dumps(sorted(z.namelist())))",
  ].join("\n"), ruta);
  expect(contenido.length).toBe(3);
  expect(contenido.join(" ")).toMatch(/borrador-210\.pdf/);
  r.fin();
});
