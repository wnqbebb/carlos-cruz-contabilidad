/**
 * Formateo de importes SIN pasar por `number`.
 *
 * El backend manda el dinero como cadena decimal exacta ("1423500.10") porque
 * un `number` de JavaScript es un float de 64 bits y no puede representar 0,1:
 *
 *     0.1 + 0.2            → 0.30000000000000004
 *     1423500.1 * 3        → 4270500.299999999
 *
 * En una contabilidad eso produce descuadres de centavos que nadie puede
 * explicar. Aquí la cadena se parte en signo, parte entera y decimales, y se
 * formatea manipulando TEXTO. El valor que ve el contador es, dígito por
 * dígito, el que calculó Python con `Decimal`.
 *
 * Si alguna vez necesita comparar o sumar importes en el frontend, use las
 * funciones `cmp` y `suma` de este archivo, nunca `Number(...)`.
 */

export type Importe = string | number | null | undefined;

/** Partes de un importe decimal, ya separadas y sin signo. */
interface Partes {
  negativo: boolean;
  entero: string;
  decimales: string;
}

const VACIO: Partes = { negativo: false, entero: "0", decimales: "" };

function partir(v: Importe): Partes | null {
  if (v === null || v === undefined || v === "") return null;
  // Un `number` solo aparece en campos que no son dinero (conteos, índices).
  let s = typeof v === "number" ? String(v) : String(v).trim();
  if (!s) return null;

  let negativo = false;
  if (s.startsWith("-")) {
    negativo = true;
    s = s.slice(1);
  } else if (s.startsWith("+")) {
    s = s.slice(1);
  }

  // Notación científica: el backend no la emite, pero si llegara hay que
  // devolverla a decimal plano antes de formatear.
  if (/e/i.test(s)) {
    const n = Number(s);
    if (!Number.isFinite(n)) return null;
    s = n.toFixed(6).replace(/0+$/, "").replace(/\.$/, "");
  }

  if (!/^\d*(\.\d*)?$/.test(s)) return null;

  const [enteroCrudo = "", decCrudo = ""] = s.split(".");
  const entero = enteroCrudo.replace(/^0+(?=\d)/, "") || "0";
  const decimales = decCrudo.replace(/0+$/, "");
  return { negativo, entero, decimales };
}

/** Agrupa de tres en tres con punto, al estilo colombiano: 1423500 → 1.423.500 */
function agrupar(entero: string): string {
  return entero.replace(/\B(?=(\d{3})+(?!\d))/g, ".");
}

/** ¿Es cero exacto? (sirve para ocultar ceros y para pintar descuadres) */
export function esCero(v: Importe): boolean {
  const p = partir(v);
  if (!p) return true;
  return p.entero === "0" && p.decimales === "";
}

export function esNegativo(v: Importe): boolean {
  const p = partir(v);
  return !!p && p.negativo && !(p.entero === "0" && p.decimales === "");
}

/**
 * Número con separador de miles. Los decimales solo se muestran si existen,
 * y siempre a dos cifras (2,5 → 2,50) como se acostumbra en contabilidad.
 */
export function numero(v: Importe, decimalesForzados?: number): string {
  const p = partir(v);
  if (!p) return typeof v === "string" ? v : "";
  let dec = p.decimales;
  if (decimalesForzados !== undefined) {
    dec = (dec + "0".repeat(decimalesForzados)).slice(0, decimalesForzados);
  } else if (dec.length === 1) {
    dec = dec + "0";
  } else if (dec.length > 2) {
    dec = dec.slice(0, 2); // se recorta para mostrar; el valor guardado no cambia
  }
  const cuerpo = agrupar(p.entero) + (dec ? "," + dec : "");
  return (p.negativo && cuerpo !== "0" ? "-" : "") + cuerpo;
}

/** Importe en pesos: $ 1.423.500 · -$ 2.204.760,72 */
export function pesos(v: Importe): string {
  const p = partir(v);
  if (!p) return typeof v === "string" ? v : "";
  const sinSigno = numero(p.entero + (p.decimales ? "." + p.decimales : ""));
  return (p.negativo && sinSigno !== "0" ? "-$ " : "$ ") + sinSigno;
}

/** Importe compacto para tarjetas grandes: $ 1,4 M · $ 850 K */
export function pesosCorto(v: Importe): string {
  const p = partir(v);
  if (!p) return "";
  const digitos = p.entero.length;
  const signo = p.negativo && p.entero !== "0" ? "-" : "";
  if (digitos > 9) return `${signo}$ ${coma(p.entero, 9)} MM`;
  if (digitos > 6) return `${signo}$ ${coma(p.entero, 6)} M`;
  if (digitos > 3) return `${signo}$ ${coma(p.entero, 3)} K`;
  return pesos(v);
}

/** 1423500 con escala 6 → "1,4" (una decimal, sin redondeo flotante) */
function coma(entero: string, escala: number): string {
  const cabeza = entero.slice(0, entero.length - escala);
  const resto = entero.slice(entero.length - escala, entero.length - escala + 1);
  return resto && resto !== "0" ? `${agrupar(cabeza)},${resto}` : agrupar(cabeza);
}

/** Cantidades de inventario: hasta 2 decimales, sin símbolo. */
export function cant(v: Importe): string {
  return numero(v);
}

/** Porcentaje a partir de una fracción exacta en texto: "0.4" → "40,0%" */
export function porcentaje(v: Importe, decimales = 1): string {
  const p = partir(v);
  if (!p) return "";
  // Multiplicar por 100 es correr la coma dos lugares: operación de texto.
  const digitos = p.entero + p.decimales;
  const puntoOriginal = p.entero.length;
  const puntoNuevo = puntoOriginal + 2;
  const relleno = digitos.padEnd(Math.max(puntoNuevo, digitos.length), "0");
  const entero = relleno.slice(0, puntoNuevo).replace(/^0+(?=\d)/, "") || "0";
  const dec = relleno.slice(puntoNuevo, puntoNuevo + decimales).padEnd(decimales, "0");
  return `${p.negativo ? "-" : ""}${agrupar(entero)}${decimales ? "," + dec : ""}%`;
}

/** Compara dos importes exactamente. Devuelve -1, 0 o 1. */
export function cmp(a: Importe, b: Importe): number {
  const pa = partir(a) ?? VACIO;
  const pb = partir(b) ?? VACIO;
  const sa = pa.negativo && !(pa.entero === "0" && !pa.decimales) ? -1 : 1;
  const sb = pb.negativo && !(pb.entero === "0" && !pb.decimales) ? -1 : 1;
  if (sa !== sb) return sa < sb ? -1 : 1;
  const largo = Math.max(pa.entero.length, pb.entero.length);
  const ea = pa.entero.padStart(largo, "0");
  const eb = pb.entero.padStart(largo, "0");
  let r = ea === eb ? 0 : ea < eb ? -1 : 1;
  if (r === 0) {
    const dl = Math.max(pa.decimales.length, pb.decimales.length);
    const da = pa.decimales.padEnd(dl, "0");
    const db = pb.decimales.padEnd(dl, "0");
    r = da === db ? 0 : da < db ? -1 : 1;
  }
  return sa < 0 ? -r : r;
}

/** Fecha ISO → 31/01/2025 */
export function fecha(iso: string | null | undefined): string {
  if (!iso) return "";
  const [a, m, d] = iso.slice(0, 10).split("-");
  if (!a || !m || !d) return iso;
  return `${d}/${m}/${a}`;
}

const MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio",
  "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"];

/** Fecha ISO → "31 de enero de 2025" */
export function fechaLarga(iso: string | null | undefined): string {
  if (!iso) return "";
  const [a, m, d] = iso.slice(0, 10).split("-");
  const mes = MESES[Number(m) - 1];
  if (!mes) return fecha(iso);
  return `${Number(d)} de ${mes} de ${a}`;
}

/** "2025-01-01".."2025-01-31" → "Enero 2025" cuando el rango es un mes completo */
export function periodoCorto(desde: string, hasta: string): string {
  if (!desde || !hasta) return "";
  const [a1, m1, d1] = desde.slice(0, 10).split("-");
  const [a2, m2] = hasta.slice(0, 10).split("-");
  if (a1 === a2 && m1 === m2 && d1 === "01") {
    const mes = MESES[Number(m1) - 1] ?? "";
    return `${mes.charAt(0).toUpperCase()}${mes.slice(1)} ${a1}`;
  }
  // Meses completos (bimestre, trimestre…): «Enero – febrero 2025», «Diciembre 2025 – enero 2026».
  const d2 = hasta.slice(8, 10);
  if (d1 === "01" && Number(d2) === new Date(Number(a2), Number(m2), 0).getDate()) {
    const ini = MESES[Number(m1) - 1] ?? "";
    const fin = MESES[Number(m2) - 1] ?? "";
    const Ini = `${ini.charAt(0).toUpperCase()}${ini.slice(1)}`;
    return a1 === a2 ? `${Ini} – ${fin} ${a2}` : `${Ini} ${a1} – ${fin} ${a2}`;
  }
  return `${fecha(desde)} – ${fecha(hasta)}`;
}

/** Une clases condicionales. */
export function clases(...c: (string | false | null | undefined)[]): string {
  return c.filter(Boolean).join(" ");
}

/**
 * Suma exacta de importes decimales en texto.
 *
 * No usa `+` sobre números: escala cada valor a enteros con `BigInt`, suma, y
 * devuelve el resultado como cadena decimal. Así, sumar mil líneas de un
 * balance en el navegador da exactamente lo mismo que sumarlas con `Decimal`
 * en Python.
 *
 *     sumar("0.1", "0.2")        → "0.3"      (con números daría 0.30000000000000004)
 *     sumar("1423500.10", "-500") → "1423000.10"
 */
export function sumar(...valores: Importe[]): string {
  let escala = 0;
  const partidos: Partes[] = [];
  for (const v of valores) {
    const p = partir(v);
    if (!p) continue;
    partidos.push(p);
    if (p.decimales.length > escala) escala = p.decimales.length;
  }
  if (!partidos.length) return "0";

  let total = 0n;
  for (const p of partidos) {
    const digitos = p.entero + p.decimales.padEnd(escala, "0");
    const entero = BigInt(digitos || "0");
    total += p.negativo ? -entero : entero;
  }

  const negativo = total < 0n;
  const texto = (negativo ? -total : total).toString().padStart(escala + 1, "0");
  const entero = escala ? texto.slice(0, texto.length - escala) : texto;
  const decimales = escala ? texto.slice(texto.length - escala).replace(/0+$/, "") : "";
  const cuerpo = (entero.replace(/^0+(?=\d)/, "") || "0") + (decimales ? "." + decimales : "");
  return negativo && cuerpo !== "0" ? "-" + cuerpo : cuerpo;
}

/** Resta exacta: `restar(a, b)` es `a − b`. */
export function restar(a: Importe, b: Importe): string {
  const p = partir(b);
  if (!p) return sumar(a);
  const negado = (p.negativo ? "" : "-") + p.entero + (p.decimales ? "." + p.decimales : "");
  return sumar(a, negado);
}

/**
 * Cociente exacto `a / b` como texto decimal, redondeado a `decimales` cifras
 * (mitad hacia arriba, lejos de cero). Para razones de presentación como el
 * margen: `porcentaje(razon(utilidad, ingresos, 4))` → "24,2%".
 * Devuelve null si `b` es cero. Sin floats: escala a enteros con BigInt.
 */
export function razon(a: Importe, b: Importe, decimales = 4): string | null {
  const pa = partir(a);
  const pb = partir(b);
  if (!pa || !pb) return null;
  const escala = Math.max(pa.decimales.length, pb.decimales.length);
  const na = BigInt(pa.entero + pa.decimales.padEnd(escala, "0")) * (pa.negativo ? -1n : 1n);
  const nb = BigInt(pb.entero + pb.decimales.padEnd(escala, "0")) * (pb.negativo ? -1n : 1n);
  if (nb === 0n) return null;
  const negativo = (na < 0n) !== (nb < 0n);
  const absA = na < 0n ? -na : na;
  const absB = nb < 0n ? -nb : nb;
  // Una cifra de más para redondear: (a·10^(d+1)) / b, luego mitad hacia arriba.
  const crudo = (absA * 10n ** BigInt(decimales + 1)) / absB;
  const redondeado = (crudo + 5n) / 10n;
  const texto = redondeado.toString().padStart(decimales + 1, "0");
  const entero = texto.slice(0, texto.length - decimales);
  const dec = decimales ? texto.slice(texto.length - decimales) : "";
  const cuerpo = entero + (dec ? "." + dec : "");
  return negativo && redondeado !== 0n ? "-" + cuerpo : cuerpo;
}
