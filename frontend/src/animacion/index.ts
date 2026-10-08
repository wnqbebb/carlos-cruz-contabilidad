/**
 * Sistema de animación de Carlos Cruz (spec 8). Todo el movimiento pasa por
 * aquí: GSAP con Flip y ScrollTrigger registrados una sola vez.
 *
 * Reglas:
 *  · solo `transform` y `opacity` (la GPU los anima sin recalcular la página);
 *  · todo respeta «menos movimiento»: duraciones a cero, salvo fundidos ≤ 0,2 s;
 *  · cada componente limpia sus animaciones con `gsap.context()` al desmontarse;
 *  · nada de Lenis ni scroll suave (rompe las tablas pegajosas) ni cursores
 *    personalizados.
 *
 *  Movimiento                    Especificación                       Registro
 *  Entrada de página             y 12 → 0, opacidad 0 → 1, 0,45 s,    ambos
 *                                power3.out, escalonado 0,04
 *  Salida de página              opacidad 1 → 0, 0,15 s               ambos
 *  Odómetro de cifras            cada dígito rueda, 0,9 s expo.out    Escaparate
 *  Hover Expediente              pestaña −4 px, giro −0,6°, 0,3 s     Escaparate
 *  Interruptor / navegación      Flip 0,35 s power3.inOut             ambos
 *  Balanza de la ecuación        back.out(1.4) 0,6 s                  Escaparate
 *  Aurora / esferas              deriva 12–18 s en bucle              Escaparate
 *  Aparición por scroll          ScrollTrigger una vez, y 16, 0,5 s   Escaparate
 *  Tablas, formularios, mapeo    sin entrada; cambios ≤ 0,2 s         Taller
 */
import { gsap } from "gsap";
import { Flip } from "gsap/Flip";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { useLayoutEffect, type RefObject } from "react";

gsap.registerPlugin(Flip, ScrollTrigger);

export { gsap, Flip, ScrollTrigger };

/** ¿El sistema pidió menos movimiento? Se consulta en cada uso: puede cambiar. */
export function sinMovimiento(): boolean {
  return typeof window !== "undefined" && !!window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
}

/** Duraciones del spec (sección 8), en segundos. */
export const DURACION = {
  entrada: 0.45,
  salida: 0.15,
  hover: 0.3,
  interruptor: 0.35,
  odometro: 0.9,
  balanza: 0.6,
  aparicion: 0.5,
  estado: 0.2,
} as const;

/* ── páginas ─────────────────────────────────────────────────────────── */

/**
 * Entrada de una pantalla: sus bloques de primer nivel suben 12 px y
 * aparecen, escalonados 0,04 s. Devuelve la animación para poder limpiarla.
 */
export function animarPantalla(nodo: HTMLElement | null): gsap.core.Tween | undefined {
  if (!nodo) return;
  const bloques = Array.from(nodo.children) as HTMLElement[];
  const objetivo = bloques.length && bloques.length <= 12 ? bloques : [nodo];
  if (sinMovimiento()) {
    gsap.set(objetivo, { clearProps: "opacity,transform" });
    return;
  }
  return gsap.fromTo(
    objetivo,
    { opacity: 0, y: 12 },
    { opacity: 1, y: 0, duration: DURACION.entrada, ease: "power3.out", stagger: 0.04, clearProps: "transform" },
  );
}

/** Salida de una pantalla: fundido de 0,15 s. Resuelve cuando termina. */
export function salirPantalla(nodo: HTMLElement | null): Promise<void> {
  if (!nodo || sinMovimiento()) return Promise.resolve();
  return new Promise((listo) => {
    gsap.to(nodo, { opacity: 0, duration: DURACION.salida, ease: "power1.out", onComplete: () => listo() });
  });
}

/**
 * Aparición por scroll (Escaparate): el bloque sube 16 px y aparece la
 * primera vez que entra en pantalla. Una sola vez.
 */
export function useAparicion(ref: RefObject<HTMLElement | null>, activo = true) {
  useLayoutEffect(() => {
    const el = ref.current;
    if (!el || !activo || sinMovimiento()) return;
    const ctx = gsap.context(() => {
      gsap.from(el, {
        y: 16,
        opacity: 0,
        duration: DURACION.aparicion,
        ease: "power3.out",
        clearProps: "transform,opacity",
        scrollTrigger: { trigger: el, start: "top 90%", once: true },
      });
    });
    return () => ctx.revert();
  }, [ref, activo]);
}

/* ── señal «el Tablero ya tiene datos» para el preloader ─────────────── */
let tableroListo = false;

/** La llama el Tablero cuando llegan sus datos. */
export function marcarTableroListo() {
  if (tableroListo) return;
  tableroListo = true;
  window.dispatchEvent(new Event("cc:tablero-listo"));
}

export function estaTableroListo() {
  return tableroListo;
}
