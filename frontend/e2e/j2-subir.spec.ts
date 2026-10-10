import { expect, test, type Page } from "@playwright/test";
import { join } from "node:path";
import { DEMO, Recorrido, sinAnimacionDeEntrada } from "./ayuda";

async function subirDesdeTablero(page: Page, r: Recorrido, archivo: string) {
  await page.goto("/");
  await r.clic(page.getByRole("button", { name: "Subir archivo" }).first());
  await page.locator('input[type="file"]').first().setInputFiles(archivo);
  const dialogo = page.getByRole("dialog");
  await expect(dialogo.getByText("¿De quién es?")).toBeVisible({ timeout: 60_000 });
  await r.captura("de-quien-es");
  await r.clic(dialogo.getByRole("button", { name: /Crear cliente y calcular|Calcular/ }));
}

test.beforeEach(async ({ page }) => sinAnimacionDeEntrada(page));

test("J2 · subir la plantilla del caso completo → resultado en pantalla", async ({ page }) => {
  const r = new Recorrido(page, "J2a", "Subir contabilidad (caso completo)");
  await subirDesdeTablero(page, r, join(DEMO, "casos", "caso_completo.xlsx"));
  // El resultado de inmediato: el expediente del cliente, enero de 2025, estados financieros, cuadra.
  await expect(page).toHaveURL(/\/clientes\/[0-9a-f-]+/, { timeout: 120_000 });
  await expect(page.getByRole("combobox", { name: "Periodo" })).toHaveValue(/.+/);
  await expect(page.getByRole("heading", { name: /COMERCIALIZADORA EJEMPLO COMPLETO/i }).first()).toBeVisible();
  await expect(page.getByRole("heading", { name: "Estado de situación financiera" })).toBeVisible();
  await expect(page.getByText("No cuadra")).toHaveCount(0);
  await r.captura("resultado");
  const t = r.fin();
  expect(t.clics).toBeLessThanOrEqual(3);
});

test("J2 · subir las facturas electrónicas de la DIAN → ventas y compras organizadas solas", async ({ page }) => {
  const r = new Recorrido(page, "J2b", "Subir facturas electrónicas DIAN");
  await subirDesdeTablero(page, r, join(DEMO, "dian", "facturas_todas_enero_2025.xlsx"));
  await expect(page).toHaveURL(/\/clientes\/[0-9a-f-]+/, { timeout: 120_000 });
  await expect(page.getByRole("heading", { name: /DROGUER/i }).first()).toBeVisible();
  // Estado de resultados: ingresos 3.300.000 (ventas 3.500.000 − devolución 200.000).
  await page.getByRole("button", { name: "Resultados", exact: true }).first().click();
  await expect(page.getByText("3.300.000").first()).toBeVisible();
  await r.captura("resultado");
  r.fin();
});
