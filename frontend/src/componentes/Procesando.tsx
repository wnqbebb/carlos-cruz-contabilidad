import { Check } from "lucide-react";
import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { clases } from "../formato";
import { gsap, sinMovimiento } from "../ui";

/**
 * Procesando (spec 6.5): mini cuenta T que se traza en bucle + lista de
 * etapas que se van marcando. Nunca un spinner genérico.
 *
 * El servidor responde de una sola vez, así que las etapas avanzan con el
 * tiempo pero la última NUNCA se marca hasta que llega la respuesta: no se
 * promete un progreso que no se conoce.
 */
export const ETAPAS_LECTURA = ["Leyendo archivo", "Detectando formato", "Mapeando al PUC"];
export const ETAPAS_CALCULO = ["Calculando mayor", "Validando partida doble", "Armando estados financieros"];

export function Procesando({ etapas, titulo }: { etapas: string[]; titulo: string }) {
  const [hecho, setHecho] = useState(0);
  const t = useRef<SVGSVGElement>(null);

  useEffect(() => {
    const id = setInterval(() => setHecho((h) => Math.min(h + 1, etapas.length - 1)), 900);
    return () => clearInterval(id);
  }, [etapas.length]);

  useLayoutEffect(() => {
    if (!t.current || sinMovimiento()) return;
    const ctx = gsap.context(() => {
      const lineas = t.current!.querySelectorAll("path");
      gsap.set(lineas, { strokeDasharray: 60, strokeDashoffset: 60 });
      gsap
        .timeline({ repeat: -1, repeatDelay: 0.25 })
        .to(lineas[0], { strokeDashoffset: 0, duration: 0.45, ease: "power2.out" })
        .to(lineas[1], { strokeDashoffset: 0, duration: 0.35, ease: "power2.out" })
        .to(lineas, { opacity: 0, duration: 0.3, delay: 0.5 })
        .set(lineas, { strokeDashoffset: 60, opacity: 1 });
    }, t);
    return () => ctx.revert();
  }, []);

  return (
    <div role="status" aria-live="polite" className="flex flex-col items-center gap-6 py-6 text-center">
      <svg ref={t} width="72" height="56" viewBox="0 0 72 56" aria-hidden>
        <path d="M6 10 H66" stroke="var(--tinta)" strokeWidth="3" strokeLinecap="round" fill="none" />
        <path d="M36 10 V50" stroke="var(--tinta)" strokeWidth="3" strokeLinecap="round" fill="none" />
      </svg>
      <p className="t-h2 text-tinta">{titulo}</p>
      <ol className="space-y-2 text-left">
        {etapas.map((e, i) => {
          const listo = i < hecho;
          const actual = i === hecho;
          return (
            <li key={e} className={clases("t-body flex items-center gap-3", listo ? "text-tinta" : actual ? "text-tinta" : "text-gris")}>
              <span
                aria-hidden
                className={clases(
                  "grid h-5 w-5 shrink-0 place-items-center rounded-full border",
                  listo ? "border-tinta bg-tinta text-sobre-tinta" : actual ? "border-tinta" : "border-linea",
                )}
              >
                {listo ? <Check size={12} strokeWidth={2} /> : actual ? <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-tinta" /> : null}
              </span>
              {e}
              {listo && <span className="sr-only">: listo</span>}
            </li>
          );
        })}
      </ol>
    </div>
  );
}
