#!/usr/bin/env node
/**
 * Antes / después lado a lado (spec, sección 12).
 *
 *   node scripts/comparar.mjs fase-1
 *
 * Toma docs/diseno/capturas/fase-0/actual-0X-*.png (antes) y la captura de la
 * misma pantalla en la fase indicada (después), y guarda
 * docs/diseno/capturas/<fase>/comparar-0X-*.png con ambas, recortadas al
 * primer pantallazo (lo que el cliente ve sin desplazarse).
 */
import { existsSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";

const fase = process.argv[2] ?? "fase-1";
const RAIZ = fileURLToPath(new URL("../..", import.meta.url));
const CAP = join(RAIZ, "docs", "diseno", "capturas");
const PANTALLAS = ["01-tablero", "02-clientes", "03-trabajar", "04-parametros", "05-ficha"];

const datos = (ruta) => "data:image/png;base64," + readFileSync(ruta).toString("base64");

const navegador = await chromium.launch({ channel: "msedge" });
for (const movil of [false, true]) {
  const suf = movil ? "-movil" : "";
  const [ancho, alto] = movil ? [390, 844] : [1440, 900];
  const pagina = await navegador.newPage({ viewport: { width: ancho * 2 + 48, height: alto + 64 } });
  for (const p of PANTALLAS) {
    const antes = join(CAP, "fase-0", `actual-${p}${suf}.png`);
    const despues = join(CAP, fase, `${p}${suf}.png`);
    if (!existsSync(antes) || !existsSync(despues)) continue;
    await pagina.setContent(`<!doctype html><html><body style="margin:0;background:#d9d6cf;font:500 12px ui-monospace,monospace;letter-spacing:.12em;color:#141414">
      <div style="display:flex;gap:16px;padding:16px">
        ${[["ANTES · FASE 0", antes], [`DESPUÉS · ${fase.toUpperCase()}`, despues]].map(([t, r]) => `
          <figure style="margin:0;width:${ancho}px">
            <figcaption style="height:24px">${t}</figcaption>
            <div style="width:${ancho}px;height:${alto}px;overflow:hidden;outline:1px solid rgba(0,0,0,.2)">
              <img src="${datos(r)}" style="display:block;width:${ancho}px">
            </div>
          </figure>`).join("")}
      </div></body></html>`);
    const salida = join(CAP, fase, `comparar-${p}${suf}.png`);
    await pagina.screenshot({ path: salida });
    console.log("✓ ", salida);
  }
  await pagina.close();
}
await navegador.close();
