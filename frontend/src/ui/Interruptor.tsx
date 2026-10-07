import { useId, useLayoutEffect, useRef, type KeyboardEvent, type ReactNode } from "react";
import { clases } from "../formato";
import { DURACION, Flip, sinMovimiento } from "./movimiento";

/**
 * Interruptor — segmentado de ref-06 (Future⁰¹ / Now⁰²).
 *
 * Píldora de tinta por fuera; la opción activa es una píldora clara que se
 * desliza con GSAP Flip (0,35 s, power3.inOut). Cada opción lleva su índice
 * en superíndice. Se maneja con flechas, Inicio y Fin (patrón radiogroup).
 */

export type OpcionInterruptor<T extends string> = { valor: T; texto: ReactNode; indice?: string };

const indiceDe = (n: number) => String(n).padStart(2, "0");

export function Interruptor<T extends string>({
  opciones,
  valor,
  onCambio,
  etiqueta,
  tamano = "md",
  className,
}: {
  opciones: OpcionInterruptor<T>[];
  valor: T;
  onCambio: (v: T) => void;
  /** Nombre accesible del grupo. */
  etiqueta: string;
  tamano?: "sm" | "md";
  className?: string;
}) {
  // React crea un indicador nuevo dentro de la opción elegida: Flip los
  // empareja por este id para animar del viejo al nuevo.
  const idFlip = "interruptor-" + useId();
  const indicador = useRef<HTMLSpanElement>(null);
  const previo = useRef<Flip.FlipState | null>(null);
  const botones = useRef<(HTMLButtonElement | null)[]>([]);

  const elegir = (v: T) => {
    if (v === valor) return;
    if (indicador.current && !sinMovimiento()) previo.current = Flip.getState(indicador.current);
    onCambio(v);
  };

  // Cuando React mueve el indicador al botón nuevo, Flip anima desde donde estaba.
  useLayoutEffect(() => {
    const estado = previo.current;
    previo.current = null;
    if (!estado || !indicador.current) return;
    const anim = Flip.from(estado, { targets: indicador.current, duration: DURACION.interruptor, ease: "power3.inOut" });
    return () => {
      anim.kill();
    };
  }, [valor]);

  const teclado = (e: KeyboardEvent<HTMLDivElement>) => {
    const i = opciones.findIndex((o) => o.valor === valor);
    let j = -1;
    if (e.key === "ArrowRight" || e.key === "ArrowDown") j = (i + 1) % opciones.length;
    else if (e.key === "ArrowLeft" || e.key === "ArrowUp") j = (i - 1 + opciones.length) % opciones.length;
    else if (e.key === "Home") j = 0;
    else if (e.key === "End") j = opciones.length - 1;
    if (j < 0) return;
    e.preventDefault();
    elegir(opciones[j].valor);
    botones.current[j]?.focus();
  };

  return (
    <div
      role="radiogroup"
      aria-label={etiqueta}
      onKeyDown={teclado}
      className={clases("inline-flex max-w-full items-center overflow-x-auto rounded-full bg-tinta p-1 barra-fina", className)}
    >
      {opciones.map((o, i) => {
        const activo = o.valor === valor;
        return (
          <button
            key={o.valor}
            ref={(el) => {
              botones.current[i] = el;
            }}
            type="button"
            role="radio"
            aria-checked={activo}
            tabIndex={activo ? 0 : -1}
            onClick={() => elegir(o.valor)}
            className={clases(
              "relative shrink-0 rounded-full font-medium whitespace-nowrap transition-colors duration-200",
              tamano === "sm" ? "px-3 py-1 text-[13px]" : "px-4 py-1.5 text-[15px]",
              activo ? "text-tinta" : "text-sobre-tinta-2 hover:text-sobre-tinta",
            )}
          >
            {activo && (
              <span ref={indicador} data-flip-id={idFlip} aria-hidden className="absolute inset-0 rounded-full bg-hoja" />
            )}
            <span className="relative">
              {o.texto}
              <span aria-hidden className="codigo relative -top-[0.55em] ml-[0.2em] text-[0.6em] leading-none">
                {o.indice ?? indiceDe(i + 1)}
              </span>
            </span>
          </button>
        );
      })}
    </div>
  );
}
