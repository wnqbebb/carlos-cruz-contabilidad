import { expect, test } from "@playwright/test";
import { Recorrido, abrirCliente, sinAnimacionDeEntrada } from "./ayuda";

test.beforeEach(async ({ page }) => sinAnimacionDeEntrada(page));

/** J4 · Editar el cliente: nombre en el título (< 10 s) y, en el panel lateral, sus datos y socios. Recargar. */
test("J4 · editar nombre, datos y socios, y comprobar tras recargar", async ({ page }) => {
  const r = new Recorrido(page, "J4", "Editar el cliente");
  await abrirCliente(page, /COMERCIALIZADORA EJEMPLO COMPLETO/i);

  const t0 = Date.now();
  await r.clic(page.getByRole("heading", { level: 1 }).getByText(/COMERCIALIZADORA/));
  const nombre = page.getByRole("textbox", { name: "Razón social" });
  await nombre.fill("COMERCIALIZADORA EJEMPLO COMPLETO DOS S.A.S.");
  await nombre.press("Enter");
  await expect(page.getByRole("heading", { level: 1 })).toContainText("COMPLETO DOS");
  expect(Date.now() - t0).toBeLessThan(10_000);

  await r.clic(page.getByRole("button", { name: "Editar cliente" }));
  const panel = page.getByRole("dialog", { name: "Editar cliente" });
  await panel.getByLabel("Municipio").fill("Buga");
  await panel.getByLabel("Teléfono").fill("3001234567");
  await r.clic(panel.getByRole("button", { name: "+ Agregar socio" }));
  await panel.getByLabel("Nombre del socio 1").fill("Ana Lucía Ruiz");
  await panel.getByLabel("Cédula", { exact: true }).first().fill("20333444");
  await panel.getByLabel("Cargo", { exact: true }).first().fill("Gerente");
  await panel.getByLabel(/Participación/).first().fill("0.6");
  await panel.getByLabel("Pagado", { exact: true }).first().fill("6000000");
  await r.captura("panel");
  await r.clic(panel.getByRole("button", { name: "Guardar cambios" }));
  await expect(panel).toBeHidden();

  await page.reload();
  await expect(page.getByRole("heading", { level: 1 })).toContainText("COMPLETO DOS");
  await page.getByRole("button", { name: "Editar cliente" }).click();
  await expect(panel.getByLabel("Municipio")).toHaveValue("Buga");
  await expect(panel.getByLabel("Teléfono")).toHaveValue("3001234567");
  await expect(panel.getByLabel("Nombre del socio 1")).toHaveValue("Ana Lucía Ruiz");
  await expect(panel.getByLabel("Cédula", { exact: true }).first()).toHaveValue("20333444");
  await expect(panel.getByLabel("Cargo", { exact: true }).first()).toHaveValue("Gerente");
  await expect(panel.getByLabel("Pagado", { exact: true }).first()).toHaveValue(/^6000000(\.00)?$/);
  await r.captura("tras-recargar");
  // Devuelve el nombre para los demás recorridos.
  await panel.getByLabel("Razón social o nombre completo").fill("COMERCIALIZADORA EJEMPLO COMPLETO S.A.S.");
  await panel.getByRole("button", { name: "Guardar cambios" }).click();
  await expect(panel).toBeHidden();
  r.fin();
});
