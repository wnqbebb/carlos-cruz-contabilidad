import { ArrowUpRight } from "lucide-react";
import { useLayoutEffect, useRef, useState, type ReactNode } from "react";
import { Link } from "react-router-dom";
import { clases } from "../formato";
import { DURACION, gsap, sinMovimiento } from "./movimiento";

/**
 * Expediente — la carpeta negra de ref-01.
 *
 * Cuerpo con radio 26 px y pestaña arriba a la derecha (≈ 42 % del ancho,
 * 22 px de alto, borde izquierdo inclinado). La silueta es un <svg> cuyo
 * `path` se recalcula con ResizeObserver: si se escalara un SVG fijo, las
 * esquinas se deformarían al cambiar el ancho.
 *
 * Hover (spec 8): la pestaña sube 4 px, la carpeta gira -0,6° y la flecha ↗
 * avanza 3 px, en 0,3 s. Con «menos movimiento» no se anima nada.
 *
 * Máximo 1–2 de variante «tinta» por vista (spec 4.4).
 */

const R = 26;
const PESTANA = 22;
const RAMPA = 30;
const ANCHO_PESTANA = 0.42;
const PESTANA_MINIMA = 170; // en tarjetas angostas, 42 % no deja espacio a la etiqueta

/** Dónde empieza la rampa de la pestaña para un ancho dado. */
function inicioPestana(w: number, r: number): number {
  return Math.max(r * 2, Math.min(w * (1 - ANCHO_PESTANA), w - PESTANA_MINIMA));
}

/** Silueta completa en un solo trazo: así el borde de la variante papel no
 *  muestra costuras entre cuerpo y pestaña. `sube` levanta solo la pestaña. */
export function siluetaExpediente(w: number, h: number, sube = 0): string {
  if (w <= 0 || h <= 0) return "";
  const r = Math.min(R, w / 4, (h - PESTANA) / 2);
  const t = PESTANA;
  const arriba = -sube;
  const x0 = inicioPestana(w, r);                      // inicio de la rampa
  const x1 = x0 + RAMPA;                               // fin de la rampa
  const rp = Math.min(r, 18);                          // radio de la esquina de la pestaña
  return [
    `M ${r} ${t}`,
    `L ${x0} ${t}`,
    // rampa en S: sale horizontal del cuerpo y llega horizontal a la pestaña
    `C ${x0 + RAMPA * 0.55} ${t} ${x1 - RAMPA * 0.55} ${arriba} ${x1} ${arriba}`,
    `L ${w - rp} ${arriba}`,
    `A ${rp} ${rp} 0 0 1 ${w} ${arriba + rp}`,
    `L ${w} ${h - r}`,
    `A ${r} ${r} 0 0 1 ${w - r} ${h}`,
    `L ${r} ${h}`,
    `A ${r} ${r} 0 0 1 0 ${h - r}`,
    `L 0 ${t + r}`,
    `A ${r} ${r} 0 0 1 ${r} ${t}`,
    "Z",
  ].join(" ");
}

type Variante = "tinta" | "papel";

export function Expediente({
  variante = "tinta",
  etiqueta,
  titulo,
  children,
  a,
  href,
  onClick,
  flecha = true,
  className,
  etiquetaAccesible,
}: {
  variante?: Variante;
  /** Texto pequeño sobre la pestaña (p. ej. «01 • RESULTADO»). */
  etiqueta?: ReactNode;
  titulo?: ReactNode;
  children?: ReactNode;
  /** Ruta interna (react-router). */
  a?: string;
  /** Enlace externo o descarga. */
  href?: string;
  onClick?: () => void;
  flecha?: boolean;
  className?: string;
  /** Nombre accesible cuando el contenido no basta (p. ej. solo cifras). */
  etiquetaAccesible?: string;
}) {
  const caja = useRef<HTMLDivElement>(null);
  const trazo = useRef<SVGPathElement>(null);
  const icono = useRef<HTMLSpanElement>(null);
  const [medida, setMedida] = useState({ w: 0, h: 0 });
  const estado = useRef({ sube: 0 });

  // Recalcular la silueta cuando cambia el tamaño real.
  useLayoutEffect(() => {
    const el = caja.current;
    if (!el) return;
    const medir = () => setMedida({ w: el.offsetWidth, h: el.offsetHeight });
    medir();
    const ro = new ResizeObserver(medir);
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  useLayoutEffect(() => {
    trazo.current?.setAttribute("d", siluetaExpediente(medida.w, medida.h, estado.current.sube));
  }, [medida]);

  // Hover: un solo contexto GSAP, limpiado al desmontar.
  useLayoutEffect(() => {
    const el = caja.current;
    if (!el) return;
    const ctx = gsap.context(() => {});
    const mover = (dentro: boolean) => {
      if (sinMovimiento()) return;
      ctx.add(() => {
        gsap.to(estado.current, {
          sube: dentro ? 4 : 0,
          duration: DURACION.hover,
          ease: "power3.out",
          overwrite: true,
          onUpdate: () =>
            trazo.current?.setAttribute(
              "d",
              siluetaExpediente(el.offsetWidth, el.offsetHeight, estado.current.sube),
            ),
        });
        gsap.to(el, { rotation: dentro ? -0.6 : 0, duration: DURACION.hover, ease: "power3.out", overwrite: "auto" });
        if (icono.current) {
          gsap.to(icono.current, { x: dentro ? 3 : 0, y: dentro ? -3 : 0, duration: DURACION.hover, ease: "power3.out", overwrite: "auto" });
        }
      });
    };
    const entra = () => mover(true);
    const sale = () => mover(false);
    el.addEventListener("pointerenter", entra);
    el.addEventListener("pointerleave", sale);
    el.addEventListener("focusin", entra);
    el.addEventListener("focusout", sale);
    return () => {
      el.removeEventListener("pointerenter", entra);
      el.removeEventListener("pointerleave", sale);
      el.removeEventListener("focusin", entra);
      el.removeEventListener("focusout", sale);
      ctx.revert();
    };
  }, []);

  const tinta = variante === "tinta";
  const interactivo = !!(a || href || onClick);

  const cuerpo = (
    <>
      <svg
        aria-hidden
        className="pointer-events-none absolute inset-0 h-full w-full overflow-visible"
        style={{ filter: tinta ? "var(--filtro-expediente)" : "var(--filtro-hoja)" }}
      >
        <path
          ref={trazo}
          fill={tinta ? "var(--tinta)" : "var(--hoja)"}
          stroke={tinta ? "none" : "var(--linea)"}
          strokeWidth={1}
          vectorEffect="non-scaling-stroke"
        />
      </svg>

      {/* Etiqueta sobre la pestaña, alineada a su inicio */}
      {etiqueta && (
        <span
          className={clases(
            "t-meta absolute top-[5px] right-5 truncate",
            tinta ? "text-sobre-tinta-2" : "text-gris",
          )}
          style={{ left: medida.w ? inicioPestana(medida.w, Math.min(R, medida.w / 4)) + RAMPA - 6 : "62%" }}
        >
          {etiqueta}
        </span>
      )}

      {flecha && (
        <span
          ref={icono}
          aria-hidden
          className={clases("absolute right-5 top-[36px]", tinta ? "text-sobre-tinta" : "text-tinta")}
        >
          <ArrowUpRight size={28} strokeWidth={1.5} />
        </span>
      )}

      <div className="@container relative px-6 pb-6 pt-[calc(var(--expediente-pestana)+24px)] sm:px-7 sm:pb-7">
        {titulo && (
          <div className={clases("t-h2 pr-10", tinta ? "text-sobre-tinta" : "text-tinta")}>{titulo}</div>
        )}
        {children && (
          <div className={clases(titulo ? "mt-3" : flecha && "[&>*:first-child]:pr-10", tinta ? "text-sobre-tinta-2" : "text-grafito")}>
            {children}
          </div>
        )}
      </div>
    </>
  );

  const comunes = {
    ref: caja,
    className: clases(
      "expediente relative block min-w-0 text-left",
      interactivo && "cursor-pointer",
      tinta ? "text-sobre-tinta" : "text-tinta",
      className,
    ),
    "aria-label": etiquetaAccesible,
  };

  if (a) return <Link to={a} {...comunes} ref={caja as never}>{cuerpo}</Link>;
  if (href) return <a href={href} {...comunes} ref={caja as never}>{cuerpo}</a>;
  if (onClick)
    return (
      <div {...comunes} role="button" tabIndex={0} onClick={onClick}
        onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && (e.preventDefault(), onClick())}>
        {cuerpo}
      </div>
    );
  return <div {...comunes}>{cuerpo}</div>;
}
