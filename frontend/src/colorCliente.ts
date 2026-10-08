import { rasgosEsfera } from "./ui/EsferaCliente";

/**
 * El color de cada cliente, sacado de su esfera (spec v2.2 · 8.3).
 *
 * La esfera mezcla tres colores de la paleta elegidos por el hash del NIT. Aquí
 * se toma su tono medio en OKLCH (ponderado: el primero pesa más, como en la
 * esfera), se le suma un pequeño desvío del mismo hash para que dos clientes
 * con la misma terna no queden idénticos, y se derivan cuatro colores:
 *
 *   --cliente-tono       L 0,55: subrayado de pestaña, foco, series
 *   --cliente-profundo   L 0,28: carpeta héroe de la ficha, píldora
 *   --cliente-velo       10–14 %: fondo de la cabecera
 *   --cliente-texto      el tono con la L ajustada hasta 4,5:1 sobre --hoja
 *
 * Restricción: ningún cliente cae a menos de 20° del rojo semántico (pérdidas
 * y descuadres no pueden confundirse con el color de un cliente). Los colores
 * semánticos nunca se reemplazan: esto solo da identidad.
 *
 * Se calculan los dos modos y se entregan como `--cliente-*-c` (claro) y
 * `--cliente-*-o` (oscuro); tokens.css elige según `data-tema`.
 */

// Tono OKLCH (grados) de --esfera-1…6, medidos de tokens.css (claro).
const TONO_ESFERA: Record<number, number> = { 1: 266.2, 2: 50.4, 3: 3.8, 4: 28.8, 5: 267.5, 6: 68.0 };
const ROJO = 29;           // tono OKLCH de --rojo (#c21f17)
const MARGEN_ROJO = 20;
const PESOS = [0.5, 0.3, 0.2];

// Fondos de referencia para el contraste del texto (--hoja en cada modo).
const HOJA_CLARO: [number, number, number] = [0.9647, 0.9529, 0.9294]; // #f6f3ed
const HOJA_OSCURO: [number, number, number] = [0.1059, 0.1059, 0.098]; // #1b1b19

function hash(texto: string): number {
  let h = 0x811c9dc5;
  for (const c of texto) {
    h ^= c.charCodeAt(0);
    h = Math.imul(h, 0x01000193) >>> 0;
  }
  return h >>> 0;
}

/** Media circular ponderada de tonos (grados). */
function tonoMedio(tonos: number[], pesos: number[]): number {
  let x = 0;
  let y = 0;
  tonos.forEach((t, i) => {
    x += Math.cos((t * Math.PI) / 180) * pesos[i];
    y += Math.sin((t * Math.PI) / 180) * pesos[i];
  });
  return ((Math.atan2(y, x) * 180) / Math.PI + 360) % 360;
}

function lejosDelRojo(tono: number): number {
  const d = ((tono - ROJO + 540) % 360) - 180; // distancia con signo, -180…180
  if (Math.abs(d) >= MARGEN_ROJO) return tono;
  return (ROJO + (d >= 0 ? MARGEN_ROJO : -MARGEN_ROJO) + 360) % 360;
}

/* ── OKLCH → sRGB, para medir contraste y no salirse del gamut ─────────── */
function oklchARgb(L: number, C: number, H: number): [number, number, number] {
  const a = C * Math.cos((H * Math.PI) / 180);
  const b = C * Math.sin((H * Math.PI) / 180);
  const l_ = L + 0.3963377774 * a + 0.2158037573 * b;
  const m_ = L - 0.1055613458 * a - 0.0638541728 * b;
  const s_ = L - 0.0894841775 * a - 1.291485548 * b;
  const l = l_ ** 3;
  const m = m_ ** 3;
  const s = s_ ** 3;
  return [
    4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s,
    -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s,
    -0.0041960863 * l - 0.7034186147 * m + 1.707614701 * s,
  ];
}

const enGamut = (rgb: number[]) => rgb.every((v) => v >= -0.0005 && v <= 1.0005);

/** Baja el croma hasta que el color quepa en sRGB. */
function ajustarCroma(L: number, C: number, H: number): number {
  let c = C;
  while (c > 0 && !enGamut(oklchARgb(L, c, H))) c -= 0.005;
  return Math.max(0, c);
}

const lineal = (v: number) => Math.min(1, Math.max(0, v));
function luminancia([r, g, b]: [number, number, number]): number {
  // oklchARgb ya devuelve sRGB lineal.
  return 0.2126 * lineal(r) + 0.7152 * lineal(g) + 0.0722 * lineal(b);
}
function linealDeSrgb(v: number): number {
  return v <= 0.04045 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4;
}
export function contraste(L: number, C: number, H: number, fondo: [number, number, number]): number {
  const a = luminancia(oklchARgb(L, C, H));
  const b = 0.2126 * linealDeSrgb(fondo[0]) + 0.7152 * linealDeSrgb(fondo[1]) + 0.0722 * linealDeSrgb(fondo[2]);
  return (Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05);
}

const css = (L: number, C: number, H: number, alfa?: number) =>
  `oklch(${L.toFixed(3)} ${C.toFixed(3)} ${H.toFixed(1)}${alfa !== undefined ? ` / ${alfa}` : ""})`;

export interface ColorCliente {
  tono: number;
  vars: Record<string, string>;
  /** Para la página de diseño: el contraste logrado del texto en cada modo. */
  contrasteClaro: number;
  contrasteOscuro: number;
}

export function colorCliente(nit: string): ColorCliente {
  const { colores } = rasgosEsfera(nit);
  // Los colores de la esfera que caen junto al rojo no aportan su tono.
  const validos = colores.map((c, i) => ({ t: TONO_ESFERA[c], p: PESOS[i] })).filter((x) => {
    const d = Math.abs(((x.t - ROJO + 540) % 360) - 180);
    return d >= MARGEN_ROJO;
  });
  const base = validos.length ? tonoMedio(validos.map((v) => v.t), validos.map((v) => v.p)) : TONO_ESFERA[1];
  const desvio = (hash(nit.replace(/\D/g, "") || nit) >>> 11) % 31 - 15;
  const H = lejosDelRojo((base + desvio + 360) % 360);

  // Texto: la L más clara (en claro) o más oscura (en oscuro) que llegue a 4,5:1.
  let Lc = 0.55;
  while (Lc > 0.2 && contraste(Lc, ajustarCroma(Lc, 0.14, H), H, HOJA_CLARO) < 4.5) Lc -= 0.01;
  let Lo = 0.7;
  while (Lo < 0.95 && contraste(Lo, ajustarCroma(Lo, 0.12, H), H, HOJA_OSCURO) < 4.5) Lo += 0.01;

  const tonoC = [0.55, ajustarCroma(0.55, 0.14, H)] as const;
  const tonoO = [0.72, ajustarCroma(0.72, 0.12, H)] as const;
  const profC = [0.28, ajustarCroma(0.28, 0.07, H)] as const;
  const profO = [0.32, ajustarCroma(0.32, 0.06, H)] as const;

  return {
    tono: H,
    contrasteClaro: contraste(Lc, ajustarCroma(Lc, 0.14, H), H, HOJA_CLARO),
    contrasteOscuro: contraste(Lo, ajustarCroma(Lo, 0.12, H), H, HOJA_OSCURO),
    vars: {
      "--cliente-tono-c": css(tonoC[0], tonoC[1], H),
      "--cliente-profundo-c": css(profC[0], profC[1], H),
      "--cliente-velo-c": css(tonoC[0], tonoC[1], H, 0.12),
      "--cliente-velo-fuerte-c": css(tonoC[0], tonoC[1], H, 0.16),
      "--cliente-texto-c": css(Lc, ajustarCroma(Lc, 0.14, H), H),
      "--cliente-tono-o": css(tonoO[0], tonoO[1], H),
      "--cliente-profundo-o": css(profO[0], profO[1], H),
      "--cliente-velo-o": css(tonoO[0], tonoO[1], H, 0.1),
      "--cliente-velo-fuerte-o": css(tonoO[0], tonoO[1], H, 0.14),
      "--cliente-texto-o": css(Lo, ajustarCroma(Lo, 0.12, H), H),
    },
  };
}
