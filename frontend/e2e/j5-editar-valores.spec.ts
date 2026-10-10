import { expect, test, type Page } from "@playwright/test";
import { Recorrido, abrirCliente, sinAnimacionDeEntrada } from "./ayuda";

test.beforeEach(async ({ page }) => sinAnimacionDeEntrada(page));

async function utilidad(page: Page, clienteId: string, mes: string): Promise<number> {
  const { periodos } = await (await page.request.get(`/api/clientes/${clienteId}/periodos`)).json();
  const p = periodos.find((x: { desde: string }) => x.desde.startsWith(mes));
  const { resultado } = await (await page.request.get(`/api/periodos/${p.id}/resultado`)).json();
  return Number(resultado.resumen.utilidad_neta);
}

async function esperarGuardado(page: Page) {
  await expect(page.getByText("Guardado", { exact: true })).toBeVisible({ timeout: 60_000 });
}

/** Filas visibles de la tabla después de buscar `texto`. */
async function filas(page: Page, texto: string) {
  await page.getByLabel("Buscar en la tabla").fill(texto);
  return page.getByRole("table").locator("tbody tr");
}

/**
 * J5 · Editar valores: abrir los datos del periodo → cambiar el valor y la cuenta de un movimiento →
 * agregar filas → borrar otras → cambiar un saldo inicial → se recalcula solo → «Cuadra» / «Descuadre» →
 * «Deshacer» → la versión anterior queda en el historial.
 */
test("J5 · editar movimientos y saldos dentro de la aplicación", async ({ page }) => {
  const r = new Recorrido(page, "J5", "Editar valores del periodo");
  const id = await abrirCliente(page, /COMERCIALIZADORA EJEMPLO COMPLETO/i);
  await page.goto(`/clientes/${id}?seccion=contabilidad&periodo=2025-01`);
  const antes = await utilidad(page, id, "2025-01");
  await r.clic(page.getByRole("button", { name: "Editar los datos del periodo" }));
  await expect(page.getByRole("heading", { name: "Datos del periodo" })).toBeVisible();
  await expect(page.getByText("Cuadra", { exact: true })).toBeVisible();

  // 1. Valor y cuenta de la papelería (CE-003: dos líneas).
  let tr = await filas(page, "CE-003");
  await expect(tr).toHaveCount(2);
  const esDebito = Number(await tr.nth(0).getByLabel(/^Débito fila/).inputValue()) > 0;
  const lineaDeb = esDebito ? tr.nth(0) : tr.nth(1);
  const lineaCre = esDebito ? tr.nth(1) : tr.nth(0);
  await lineaDeb.getByLabel(/^Débito fila/).fill("95000");
  await lineaDeb.getByLabel(/^Cuenta fila/).fill("519595");
  await lineaCre.getByLabel(/^Crédito fila/).fill("95000");

  // 2. Agregar un comprobante de dos filas.
  await page.getByLabel("Buscar en la tabla").fill("");
  for (const [cuenta, d, c] of [["513550", "40000", "0"], ["110505", "0", "40000"]]) {
    await r.clic(page.getByRole("button", { name: "Agregar fila" }));
    const nueva = page.getByRole("table").locator("tbody tr").last();
    await nueva.getByLabel(/^Comprobante fila/).fill("CE-099");
    await nueva.getByLabel(/^Cuenta fila/).fill(cuenta);
    await nueva.getByLabel(/^Débito fila/).fill(d);
    await nueva.getByLabel(/^Crédito fila/).fill(c);
  }

  // 3. Borrar las comisiones bancarias (NC-002).
  tr = await filas(page, "NC-002");
  await expect(tr).toHaveCount(2);
  await r.clic(tr.nth(0).getByRole("button", { name: /^Borrar fila/ }));
  await r.clic(tr.nth(0).getByRole("button", { name: /^Borrar fila/ }));
  await page.getByLabel("Buscar en la tabla").fill("");

  // 4. Saldo inicial: caja +100.000 contra capital.
  await r.clic(page.getByRole("tab", { name: /Saldos iniciales/ }));
  for (const [cuenta, campo] of [["110505", "Saldo débito"], ["3105", "Saldo crédito"]]) {
    const fila = (await filas(page, cuenta)).first();
    const celda = fila.getByLabel(new RegExp(`^${campo} fila`));
    await celda.fill(String(Number(await celda.inputValue()) + 100000));
  }
  await esperarGuardado(page);
  await expect(page.getByText("Cuadra", { exact: true })).toBeVisible();
  await r.captura("editado-cuadra");
  // Los estados se recalcularon solos.
  await expect.poll(() => utilidad(page, id, "2025-01"), { timeout: 30_000 }).toBe(antes - 10000 - 40000 + 15000);

  // 5. Un descuadre se ve en pantalla.
  await r.clic(page.getByRole("tab", { name: /Movimientos/ }));
  tr = await filas(page, "CE-099");
  await tr.nth(0).getByLabel(/^Débito fila/).fill("45000");
  await expect(page.getByText("Descuadre", { exact: true })).toBeVisible();
  await expect(page.getByText(/no cumple partida doble/)).toBeVisible();
  await r.captura("descuadre");
  await esperarGuardado(page);

  // 6. Deshacer devuelve el cambio y deja la versión en el historial.
  await r.clic(page.getByRole("button", { name: "Deshacer" }));
  await expect(page.getByText("Se deshizo el último cambio.")).toBeVisible();
  await expect(page.getByText("Cuadra", { exact: true })).toBeVisible();
  const { periodos } = await (await page.request.get(`/api/clientes/${id}/periodos`)).json();
  const enero = periodos.find((x: { desde: string }) => x.desde.startsWith("2025-01"));
  const { versiones } = await (await page.request.get(`/api/periodos/${enero.id}/versiones`)).json();
  expect(versiones.length).toBeGreaterThanOrEqual(2);
  await r.captura("deshacer");
  const t = r.fin();
  expect(t.segundos).toBeLessThan(180);
});
