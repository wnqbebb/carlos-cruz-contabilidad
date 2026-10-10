import { expect, test } from "@playwright/test";
import { join } from "node:path";
import { DEMO, Recorrido, sinAnimacionDeEntrada } from "./ayuda";

test.beforeEach(async ({ page }) => sinAnimacionDeEntrada(page));

/**
 * J8 · Renta con fotos difíciles: las 3 fotos del otro contribuyente → ninguna cifra de impuesto ni
 * sanción mientras falten datos → «Digitar lo esencial» → resultado coherente con los topes.
 */
test("J8 · tres fotos difíciles: sin cifras falsas y digitar lo esencial", async ({ page }) => {
  const r = new Recorrido(page, "J8", "Renta con fotos difíciles");
  await page.goto("/renta");
  await page.getByLabel("Archivos de exógena").setInputFiles(
    [3, 1, 2].map((n) => join(DEMO, "renta", `contribuyente_f_pagina_${n}.jpg`)));   // en desorden
  await expect(page).toHaveURL(/\/clientes\/[0-9a-f-]+\?seccion=renta/, { timeout: 240_000 });
  const cid = page.url().match(/clientes\/([0-9a-f-]{36})/)![1];

  await expect(page.getByRole("region", { name: /Para terminar/ })).toBeVisible({ timeout: 60_000 });
  // Ninguna cifra de impuesto ni sanción mientras falten datos.
  await expect(page.getByText(/Sanción estimada/)).toHaveCount(0);
  await expect(page.getByRole("region", { name: "Cifras de la declaración" }).getByText(/^\$ /)).toHaveCount(0);
  const v = await (await page.request.get(`/api/renta/${cid}/2025`)).json();
  expect(v.resultado.cifras.neto).toBeNull();
  expect(v.resultado.sancion).toBeNull();
  await r.captura("sin-cifras");

  // Digitar lo esencial, con la foto al lado: los topes ya vienen leídos.
  await r.clic(page.getByRole("button", { name: "Digitar lo esencial" }).first());
  const modal = page.getByRole("dialog", { name: "Digitar lo esencial" });
  await expect(modal).toBeVisible();
  await r.captura("digitar-esencial");
  await r.clic(modal.getByRole("button", { name: /Guardar|Validar|Liquidar/ }));
  await expect(modal).toBeHidden({ timeout: 60_000 });
  const despues = await (await page.request.get(`/api/renta/${cid}/2025`)).json();
  // Coherente con los topes: obligado por ingresos, patrimonio y consignaciones.
  const motivos = despues.resultado.obligacion.motivos.filter((m: { supera: boolean }) => m.supera).map((m: { tope: string }) => m.tope);
  expect(motivos).toEqual(expect.arrayContaining(["ingresos", "patrimonio", "consignaciones"]));
  await r.captura("despues");
  r.fin({ incompleto: despues.resultado.incompleto });
});
