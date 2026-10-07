import { useLayoutEffect, useRef } from "react";
import { clases, esCero, esNegativo, numero, pesos, type Importe } from "../formato";
import { DURACION, gsap, sinMovimiento } from "./movimiento";

/**
 * Cifra — importe de dinero (spec 4.5).
 *
 * · Siempre exacta y en es-CO: «$ 2.666.661,49». Nunca «2,6 M».
 * · Geist Sans con números tabulares (no mono).
 * · Color con significado: pérdida en --rojo con ▼; con `indicador`, lo
 *   positivo lleva ▲ en tinta. El color nunca va solo (spec 9).
 * · `parentesis`: convención de estados financieros, (1.234.475,72).
 * · `odometro`: cada dígito rueda al llegar un valor nuevo (0,9 s expo.out).
 *   Se anima el texto ya formateado: no hay conversión a número flotante.
 * · `title` con el valor exacto completo.
 * · `encajar`: una cifra exacta no se parte ni se abrevia; si no cabe, se
 *   achica según el ancho del contenedor (container query, `cqi`). Necesita un
 *   ancestro con la clase `@container` (el Expediente ya la trae).
 */

type Tamano = "tabla" | "body" | "h2" | "kpi" | "display" | "display-xl";

/** Tamaño máximo de cada escala, para `encajar` (mismos valores que index.css). */
const TAMANO_MAXIMO: Record<Tamano, string> = {
  tabla: "13.5px",
  body: "15px",
  h2: "22px",
  kpi: "40px",
  display: "clamp(48px, 5vw, 80px)",
  "display-xl": "clamp(64px, 8vw, 128px)",
};

const CLASE_TAMANO: Record<Tamano, string> = {
  tabla: "t-tabla",
  body: "t-body",
  h2: "t-h2",
  kpi: "t-kpi",
  display: "t-display",
  "display-xl": "t-display-xl",
};

export function textoCifra(valor: Importe, { parentesis = false, simbolo = true } = {}): string {
  if (parentesis && esNegativo(valor)) {
    return `(${numero(String(valor).replace("-", ""))})`;
  }
  return simbolo ? pesos(valor) : numero(valor);
}

export function Cifra({
  valor,
  tamano = "body",
  indicador = false,
  parentesis = false,
  simbolo = true,
  odometro = false,
  neutra = false,
  encajar = false,
  className,
}: {
  valor: Importe;
  tamano?: Tamano;
  /** Muestra ▲ / ▼ además del color. */
  indicador?: boolean;
  parentesis?: boolean;
  simbolo?: boolean;
  odometro?: boolean;
  /** Sin color semántico (p. ej. totales de débito y crédito). */
  neutra?: boolean;
  encajar?: boolean;
  className?: string;
}) {
  const texto = textoCifra(valor, { parentesis, simbolo });
  const negativo = esNegativo(valor);
  const flecha = indicador && !esCero(valor) ? (negativo ? "▼" : "▲") : "";
  const raiz = useRef<HTMLSpanElement>(null);

  useLayoutEffect(() => {
    if (!odometro || !raiz.current) return;
    const quieto = sinMovimiento();
    const ctx = gsap.context(() => {
      raiz.current!.querySelectorAll<HTMLElement>("[data-digito]").forEach((col, i) => {
        const d = Number(col.dataset.digito);
        // GSAP es el único dueño de la posición de cada columna.
        if (quieto) return void gsap.set(col, { yPercent: -d * 10 });
        gsap.fromTo(
          col,
          { yPercent: 0 },
          { yPercent: -d * 10, duration: DURACION.odometro, ease: "expo.out", delay: i * 0.02 },
        );
      });
    }, raiz);
    return () => ctx.revert();
  }, [texto, odometro]);

  return (
    <span
      ref={raiz}
      title={pesos(valor)}
      // Ancho medio por carácter ≈ 0,55 em (dígitos tabulares 0,6; punto y coma, menos).
      style={encajar ? { fontSize: `min(${TAMANO_MAXIMO[tamano]}, ${(100 / ((texto.length + (flecha ? 1 : 0)) * 0.55)).toFixed(2)}cqi)` } : undefined}
      className={clases(
        "cifras inline-flex items-baseline",
        CLASE_TAMANO[tamano],
        !neutra && negativo ? "text-rojo" : undefined,
        className,
      )}
    >
      {flecha && (
        <span aria-hidden className="mr-[0.25em] text-[0.55em] leading-none">
          {flecha}
        </span>
      )}
      {odometro ? (
        <>
          <span className="sr-only">{(negativo ? "Pérdida de " : "") + texto}</span>
          <span aria-hidden className="inline-flex">
            {texto.split("").map((c, i) =>
              /\d/.test(c) ? (
                <span key={i} className="relative inline-block h-[1em] overflow-hidden leading-none" style={{ lineHeight: 1 }}>
                  <span data-digito={c} className="flex flex-col">
                    {"0123456789".split("").map((n) => (
                      <span key={n} className="block h-[1em] leading-none">{n}</span>
                    ))}
                  </span>
                </span>
              ) : (
                <span key={i} className="leading-none">{c === " " ? " " : c}</span>
              ),
            )}
          </span>
        </>
      ) : (
        <span>{texto}</span>
      )}
    </span>
  );
}
