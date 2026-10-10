import { expect, test } from "@playwright/test";
import { mkdirSync } from "node:fs";
import { CLAVE, Recorrido, USUARIO } from "./ayuda";

/** J1 · Entrar: crear el acceso (o ingresar) y llegar al Tablero. */
test("J1 · crear el acceso o ingresar y llegar al Tablero", async ({ page }) => {
  const r = new Recorrido(page, "J1", "Entrar");
  await page.goto("/");
  const crear = page.getByRole("heading", { name: "Crear su acceso" });
  const ingresar = page.getByRole("button", { name: /^Ingresar|^Entrar/ });
  await expect(crear.or(ingresar).first()).toBeVisible({ timeout: 90_000 });   // la nube gratis puede estar despertando

  if (await crear.isVisible()) {
    if (process.env.E2E_CODIGO) await page.getByLabel("Código de instalación").fill(process.env.E2E_CODIGO);
    await page.getByLabel("Usuario").fill(USUARIO);
    await page.getByLabel("Contraseña", { exact: true }).fill(CLAVE);
    await page.getByLabel("Repita la contraseña").fill(CLAVE);
    await r.captura("crear-acceso");
    await r.clic(page.getByRole("button", { name: "Crear el acceso" }));
    // Códigos de recuperación: se muestran una sola vez.
    const seguir = page.getByRole("button", { name: /Ya los guardé|Continuar|Entrar/ });
    await expect(seguir.first()).toBeVisible();
    await r.captura("codigos-recuperacion");
    const casilla = page.getByRole("checkbox");
    if (await casilla.count()) await casilla.first().check();
    await r.clic(seguir.first());
  } else {
    await page.getByLabel("Usuario").fill(USUARIO);
    await page.getByLabel("Contraseña").fill(CLAVE);
    await r.clic(ingresar.first());
  }

  // El Tablero de verdad (no la animación de entrada): el saludo y las cifras de la cartera.
  await expect(page.locator("#saludo")).toBeVisible({ timeout: 60_000 });
  await expect(page.locator("#saludo")).toHaveText(/Buen(os|as) (días|tardes|noches)/);
  await expect(page.getByText(/Abriendo expedientes/i)).toBeHidden({ timeout: 30_000 });
  await r.captura("tablero");
  mkdirSync("e2e/.estado", { recursive: true });
  await page.context().storageState({ path: "e2e/.estado/sesion.json" });
  r.fin();
});
