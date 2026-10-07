import { createHash } from "node:crypto";
import { readdirSync, readFileSync, statSync } from "node:fs";
import { join } from "node:path";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import paquete from "./package.json";

/**
 * Sello de compilación del pie: `v2.1.0 · build <hash> · <fecha-hora>`.
 * El hash sale del contenido de src/: si el pie no cambia tras editar una
 * pantalla, el navegador está mostrando una compilación vieja (Fase 0).
 */
function huellaDe(dir: string, h = createHash("sha1")): ReturnType<typeof createHash> {
  for (const nombre of readdirSync(dir).sort()) {
    const ruta = join(dir, nombre);
    if (statSync(ruta).isDirectory()) huellaDe(ruta, h);
    else h.update(nombre).update(readFileSync(ruta));
  }
  return h;
}

const ahora = new Intl.DateTimeFormat("es-CO", {
  timeZone: "America/Bogota",
  year: "numeric", month: "2-digit", day: "2-digit",
  hour: "2-digit", minute: "2-digit", hour12: false,
}).format(new Date());

export default defineConfig({
  plugins: [react(), tailwindcss()],
  define: {
    __VERSION__: JSON.stringify(paquete.version),
    __BUILD__: JSON.stringify(huellaDe(join(__dirname, "src")).digest("hex").slice(0, 7)),
    __FECHA_BUILD__: JSON.stringify(ahora),
  },
  server: { port: 5173, proxy: { "/api": "http://127.0.0.1:8000" } },
});
