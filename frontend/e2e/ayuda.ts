import { appendFileSync, mkdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import type { Locator, Page } from "@playwright/test";

/** Carpeta de evidencias del rescate: capturas y tiempos de cada recorrido. */
export const EVIDENCIAS = join(dirname(fileURLToPath(import.meta.url)), "..", "..", "docs", "rescate");
/** Archivos ficticios de demostración (casos, reportes DIAN, fotos sintéticas). */
export const DEMO = join(dirname(fileURLToPath(import.meta.url)), "..", "..", "docs", "demo");
export const USUARIO = process.env.E2E_USUARIO || "carlos";
export const CLAVE = process.env.E2E_CLAVE || "una frase larga de prueba 2026";

/**
 * Un recorrido del usuario: cuenta los clics, mide el tiempo y guarda capturas.
 * Al terminar escribe una línea en docs/rescate/recorridos.jsonl.
 */
export class Recorrido {
  private inicio = Date.now();
  clics = 0;
  constructor(public page: Page, public id: string, public nombre: string) {
    mkdirSync(join(EVIDENCIAS, "capturas"), { recursive: true });
  }

  async clic(l: Locator) {
    this.clics++;
    await l.click();
  }

  async captura(nombre: string) {
    await this.page.screenshot({ path: join(EVIDENCIAS, "capturas", `${this.id}-${nombre}.png`), fullPage: false });
  }

  fin(extra: Record<string, unknown> = {}) {
    const segundos = Math.round((Date.now() - this.inicio) / 100) / 10;
    appendFileSync(join(EVIDENCIAS, "recorridos.jsonl"),
      JSON.stringify({ id: this.id, nombre: this.nombre, segundos, clics: this.clics, url: this.page.url(),
                       cuando: new Date().toISOString(), ...extra }) + "\n");
    return { segundos, clics: this.clics };
  }
}

/** Lee un archivo descargado a memoria. */
export async function bytesDe(descarga: import("@playwright/test").Download): Promise<Buffer> {
  const ruta = await descarga.path();
  const { readFileSync } = await import("node:fs");
  return readFileSync(ruta!);
}

/** La animación de entrada sale una vez por sesión del navegador; en los recorridos ya se vio en J1. */
export async function sinAnimacionDeEntrada(page: Page) {
  await page.addInitScript(() => sessionStorage.setItem("cc-preloader-visto", "1"));
}

/** Abre el expediente de un cliente desde la lista de Clientes. */
export async function abrirCliente(page: Page, nombre: RegExp) {
  await page.goto("/clientes");
  await page.getByRole("link", { name: nombre }).first().click();
  await page.waitForURL(/\/clientes\/[0-9a-f-]{36}/);
  return page.url().match(/clientes\/([0-9a-f-]{36})/)![1];
}

/** Corre Python (el del proyecto) para revisar un archivo descargado: devuelve lo que imprime en JSON. */
export async function python(codigo: string, ...args: string[]): Promise<any> {
  const { execFileSync } = await import("node:child_process");
  const { existsSync } = await import("node:fs");
  const raiz = join(dirname(fileURLToPath(import.meta.url)), "..", "..");
  const exe = [join(raiz, ".venv", "Scripts", "python.exe"), join(raiz, ".venv", "bin", "python")].find(existsSync) || "python";
  const salida = execFileSync(exe, ["-c", codigo, ...args], { encoding: "utf-8" });
  return JSON.parse(salida.trim().split("\n").pop()!);
}
