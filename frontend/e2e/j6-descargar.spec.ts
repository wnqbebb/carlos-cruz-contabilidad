import { expect, test } from "@playwright/test";
import { readFileSync } from "node:fs";
import { Recorrido, abrirCliente, python, sinAnimacionDeEntrada } from "./ayuda";

test.beforeEach(async ({ page }) => sinAnimacionDeEntrada(page));

const REVISAR_EXCEL = [
  "import sys, json",
  "from openpyxl import load_workbook",
  "wb = load_workbook(sys.argv[1], data_only=True)",
  "valores = []",
  "for ws in wb.worksheets:",
  "    for fila in ws.iter_rows(values_only=True):",
  "        valores += [v for v in fila if isinstance(v, (int, float))]",
  "print(json.dumps({'hojas': wb.sheetnames, 'valores': valores[:20000]}))",
].join("\n");

const EDITAR_EXCEL = [
  "import sys, json",
  "from openpyxl import load_workbook",
  "wb = load_workbook(sys.argv[1])",
  "ws = wb['MOVIMIENTOS']",
  "enc = [c.value for c in ws[1]]",
  "ic, idb, icr = enc.index('No. comprobante'), enc.index('Débito'), enc.index('Crédito')",
  "n = 0",
  "for fila in ws.iter_rows(min_row=2):",
  "    if fila[ic].value == 'CE-003':",
  "        if fila[idb].value: fila[idb].value = 120000",
  "        else: fila[icr].value = 120000",
  "        n += 1",
  "wb.save(sys.argv[2])",
  "print(json.dumps({'cambiadas': n}))",
].join("\n");

/** J6 · Descargar: Excel completo (15 hojas, cifras = pantalla), PDF, libros; datos para editar ida y vuelta. */
test("J6 · Excel completo, PDF, libros y datos para editar", async ({ page }) => {
  const r = new Recorrido(page, "J6", "Descargar");
  const id = await abrirCliente(page, /COMERCIALIZADORA EJEMPLO COMPLETO/i);
  await page.goto(`/clientes/${id}?seccion=contabilidad&periodo=2025-01&vista=situacion`);
  const { periodos } = await (await page.request.get(`/api/clientes/${id}/periodos`)).json();
  const enero = periodos.find((x: { desde: string }) => x.desde.startsWith("2025-01"));
  const activo = Number(enero.total_activo);

  // Excel completo
  await r.clic(page.getByRole("button", { name: "Descargar" }));
  const [xlsx] = await Promise.all([page.waitForEvent("download"), page.getByRole("menuitem", { name: "Excel completo" }).click()]);
  const rutaXlsx = (await xlsx.path())! + ".xlsx";
  await xlsx.saveAs(rutaXlsx);   // openpyxl exige la extensión
  const info = await python(REVISAR_EXCEL, rutaXlsx);
  expect(info.hojas.length).toBe(15);
  expect(info.hojas).toEqual(expect.arrayContaining(["EF formato contador", "Cuentas T", "Libro diario", "Mayor y balances"]));
  expect(info.valores.some((v: number) => Math.abs(v - activo) < 0.01)).toBe(true);   // el total del activo de la pantalla

  // PDF para firmar
  await r.clic(page.getByRole("button", { name: "Descargar" }));
  const [pdf] = await Promise.all([page.waitForEvent("download"), page.getByRole("menuitem", { name: "PDF para firmar" }).click()]);
  expect(readFileSync((await pdf.path())!).subarray(0, 4).toString()).toBe("%PDF");

  // Libros oficiales: diario y mayor, en Excel y PDF
  for (const libro of ["libro-diario", "mayor-balances"]) {
    for (const formato of ["excel", "pdf"]) {
      const resp = await page.request.get(`/api/periodos/${enero.id}/${libro}/${formato}`);
      expect(resp.status(), `${libro} ${formato}`).toBe(200);
      expect((await resp.body()).length).toBeGreaterThan(1000);
    }
  }

  // Datos para editar: descargar → cambiar la papelería en Excel → volver a subir → mismo periodo actualizado.
  await page.goto(`/clientes/${id}?seccion=contabilidad&periodo=2025-01&vista=datos`);
  const [plantilla] = await Promise.all([page.waitForEvent("download"),
    page.getByRole("link", { name: "Descargar datos para editar" }).click()]);
  const original = (await plantilla.path())! + ".xlsx";
  await plantilla.saveAs(original);
  const editado = original + ".editado.xlsx";
  const cambio = await python(EDITAR_EXCEL, original, editado);
  expect(cambio.cambiadas).toBe(2);
  const antes = Number(enero.utilidad);
  await r.clic(page.getByRole("button", { name: "Subir archivos de otro periodo" }));
  await page.locator('input[type="file"]').first().setInputFiles(editado);
  const seguir = page.getByRole("button", { name: /Calcular|Seguir|Actualizar|Confirmar/ });
  if (await seguir.first().waitFor({ state: "visible", timeout: 30_000 }).then(() => true).catch(() => false)) await r.clic(seguir.first());
  await expect.poll(async () => {
    const lista = (await (await page.request.get(`/api/clientes/${id}/periodos`)).json()).periodos;
    const mismo = lista.filter((x: { desde: string }) => x.desde.startsWith("2025-01"));
    return mismo.length === 1 && mismo[0].id === enero.id ? Number(mismo[0].utilidad) : antes;
  }, { timeout: 120_000 }).not.toBe(antes);
  await r.captura("datos-editados-subidos");
  r.fin();
});
