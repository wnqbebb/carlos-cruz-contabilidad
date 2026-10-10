import { defineConfig, devices } from "@playwright/test";

/**
 * Recorridos del usuario (rescate · definición de «terminado»).
 *
 *   npx playwright test                      → servidor aislado en 127.0.0.1:8010 (base temporal)
 *   E2E_URL=http://localhost:8000 npx playwright test          → contra la app que ya está abierta
 *   E2E_URL=https://carlos-cruz-contabilidad.vercel.app E2E_CODIGO=… E2E_USUARIO=… E2E_CLAVE=… npx playwright test
 *
 * Un solo trabajador: los recorridos comparten la misma cuenta y la misma base, en orden.
 */
const externa = process.env.E2E_URL;

export default defineConfig({
  testDir: "./e2e",
  timeout: 240_000,
  expect: { timeout: 30_000 },
  workers: 1,
  fullyParallel: false,
  retries: 0,
  reporter: [["list"], ["json", { outputFile: "../docs/rescate/playwright.json" }]],
  use: {
    baseURL: externa || "http://127.0.0.1:8010",
    locale: "es-CO",
    timezoneId: "America/Bogota",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    acceptDownloads: true,
    viewport: { width: 1440, height: 900 },
  },
  projects: [
    { name: "acceso", testMatch: /j1.*\.spec\.ts/ },
    {
      name: "recorridos",
      testMatch: /j[2-9].*\.spec\.ts/,
      dependencies: ["acceso"],
      use: { ...devices["Desktop Chrome"], viewport: { width: 1440, height: 900 }, storageState: "e2e/.estado/sesion.json" },
    },
  ],
  webServer: externa
    ? undefined
    : {
        command: "npm run build && node e2e/servidor.mjs",
        url: "http://127.0.0.1:8010/api/salud",
        timeout: 240_000,
        reuseExistingServer: false,
        stdout: "ignore",
        stderr: "pipe",
      },
});
