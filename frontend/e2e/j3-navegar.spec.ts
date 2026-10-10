import { expect, test } from "@playwright/test";
import { join } from "node:path";
import { DEMO, Recorrido, abrirCliente, sinAnimacionDeEntrada } from "./ayuda";

test.beforeEach(async ({ page }) => sinAnimacionDeEntrada(page));

/** J3 · Navegar: estados financieros → estado de resultados → cambiar de mes conserva la vista. */
test("J3 · cambiar de mes conserva la vista", async ({ page }) => {
  const r = new Recorrido(page, "J3", "Navegar entre meses");
  await abrirCliente(page, /COMERCIALIZADORA EJEMPLO COMPLETO/i);
  // Un segundo mes para poder cambiar: febrero, subido desde el expediente.
  await page.getByRole("button", { name: "Subir archivos de otro periodo" }).click();
  await page.locator('input[type="file"]').first().setInputFiles(join(DEMO, "casos", "caso_completo_febrero.xlsx"));
  const seguir = page.getByRole("button", { name: /Calcular|Seguir|Usar este cliente|Confirmar/ });
  if (await seguir.first().waitFor({ state: "visible", timeout: 30_000 }).then(() => true).catch(() => false)) await seguir.first().click();
  await expect(page.getByRole("combobox", { name: "Periodo" })).toHaveValue(/.+/, { timeout: 120_000 });
  await expect(page.getByRole("option", { name: /Febrero 2025/ })).toHaveCount(1);

  await r.clic(page.getByRole("button", { name: "Resultados", exact: true }).first());
  await expect(page).toHaveURL(/vista=resultados/);
  await expect(page.getByRole("heading", { name: /Estado de resultados/i })).toBeVisible();
  await r.captura("resultados-febrero");
  await r.clic(page.getByRole("button", { name: "Periodo anterior" }));
  await expect(page).toHaveURL(/periodo=2025-01/);
  await expect(page).toHaveURL(/vista=resultados/);
  await expect(page.getByRole("heading", { name: /Estado de resultados/i })).toBeVisible();
  await expect(page.getByText(/enero de 2025/i).first()).toBeVisible();
  await r.captura("resultados-enero");
  r.fin();
});
