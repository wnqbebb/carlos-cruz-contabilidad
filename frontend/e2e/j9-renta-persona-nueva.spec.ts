import { expect, test } from "@playwright/test";
import { join } from "node:path";
import { DEMO, Recorrido, sinAnimacionDeEntrada } from "./ayuda";

test.beforeEach(async ({ page }) => sinAnimacionDeEntrada(page));

/** J9 · Persona nueva: soltar una exógena en Renta⁰³ → contribuyente creado con un clic → borrador.
 *  Esa persona NO aparece entre los clientes contables. */
test("J9 · exógena de una persona nueva: borrador y fuera de los clientes contables", async ({ page }) => {
  const r = new Recorrido(page, "J9", "Renta de una persona nueva");
  await page.goto("/renta");
  await page.getByLabel("Archivos de exógena").setInputFiles(join(DEMO, "renta", "exogena_persona_nueva.xlsx"));
  await expect(page).toHaveURL(/\/clientes\/[0-9a-f-]+\?seccion=renta/, { timeout: 120_000 });
  await expect(page.getByRole("heading", { name: /PERSONA NUEVA FICTICIA/ }).first()).toBeVisible();
  await expect(page.getByText(/Renta 2025/).first()).toBeVisible();
  await r.captura("borrador");

  await page.goto("/renta");
  await expect(page.getByText("PERSONA NUEVA FICTICIA").first()).toBeVisible();
  const { clientes } = await (await page.request.get("/api/clientes?por_pagina=500")).json();
  expect(clientes.some((c: { razon_social: string }) => c.razon_social.includes("PERSONA NUEVA"))).toBe(false);
  await page.goto("/clientes");
  await expect(page.getByText("PERSONA NUEVA FICTICIA")).toHaveCount(0);
  r.fin();
});
