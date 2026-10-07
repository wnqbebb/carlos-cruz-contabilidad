#!/usr/bin/env node
/**
 * ¿Hay que recompilar la interfaz?  Sale con 0 si dist/ está al día y con 1 si
 * algún archivo de src/, index.html, package.json o vite.config.ts es más nuevo
 * que dist/index.html (o si dist no existe).
 *
 * Lo usa iniciar.bat. Antes solo compilaba si dist/ no existía, así que una
 * pantalla editada seguía mostrándose vieja (causa hallada en la Fase 0).
 */
import { existsSync, readdirSync, statSync } from "node:fs";
import { join } from "node:path";
import { fileURLToPath } from "node:url";

const RAIZ = fileURLToPath(new URL("..", import.meta.url));
const salida = join(RAIZ, "dist", "index.html");
if (!existsSync(salida)) process.exit(1);
const compilado = statSync(salida).mtimeMs;

function masNuevo(ruta) {
  const info = statSync(ruta);
  if (!info.isDirectory()) return info.mtimeMs > compilado;
  return readdirSync(ruta).some((n) => masNuevo(join(ruta, n)));
}

const fuentes = ["src", "public", "index.html", "package.json", "vite.config.ts"]
  .map((r) => join(RAIZ, r))
  .filter(existsSync);

process.exit(fuentes.some(masNuevo) ? 1 : 0);
