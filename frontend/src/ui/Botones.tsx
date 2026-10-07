import { ArrowRight } from "lucide-react";
import type { AnchorHTMLAttributes, ButtonHTMLAttributes, ReactNode } from "react";
import { Link } from "react-router-dom";
import { clases } from "../formato";

/**
 * Botones (spec 4.5).
 *
 *   BotonPrimario  píldora de tinta, 44 px (ref-03). Hover: --tinta-2 y la
 *                  flecha avanza 3 px.
 *   BotonAcento    azul. SOLO la acción principal de la vista: máximo un
 *                  elemento azul sólido por pantalla (spec 4.1).
 *   BotonFantasma  borde --linea.
 *
 * Los tres aceptan `a` (ruta interna), `href` (descarga o externo) o se
 * comportan como <button>.
 */

type Comunes = {
  children: ReactNode;
  /** Muestra la flecha que avanza al pasar el cursor. */
  flecha?: boolean;
  icono?: ReactNode;
  cargando?: boolean;
  compacto?: boolean;
  className?: string;
};

type Props = Comunes &
  (
    | ({ a: string; href?: never } & Omit<AnchorHTMLAttributes<HTMLAnchorElement>, "href">)
    | ({ href: string; a?: never } & AnchorHTMLAttributes<HTMLAnchorElement>)
    | ({ a?: never; href?: never } & ButtonHTMLAttributes<HTMLButtonElement>)
  );

const BASE =
  "boton group inline-flex shrink-0 select-none items-center justify-center gap-2 rounded-full font-medium " +
  "transition-[background-color,border-color,color,transform] duration-200 active:scale-[0.98] " +
  "disabled:pointer-events-none disabled:opacity-45";

const VARIANTES = {
  primario: "bg-tinta text-sobre-tinta hover:bg-tinta-2",
  acento: "bg-azul text-white hover:bg-azul-tinta",
  fantasma: "border border-linea bg-transparent text-tinta hover:border-tinta/30 hover:bg-hoja",
} as const;

function crear(variante: keyof typeof VARIANTES) {
  return function Boton(props: Props) {
    const { children, flecha, icono, cargando, compacto, className, ...resto } = props;
    const clase = clases(
      BASE,
      VARIANTES[variante],
      compacto ? "h-9 px-4 text-[13px]" : "h-11 px-5 text-[15px]",
      className,
    );
    const contenido = (
      <>
        {cargando ? (
          <span aria-hidden className="h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" />
        ) : (
          icono
        )}
        <span>{children}</span>
        {flecha && (
          <ArrowRight
            size={compacto ? 16 : 18}
            strokeWidth={1.5}
            aria-hidden
            className="transition-transform duration-300 group-hover:translate-x-[3px]"
          />
        )}
      </>
    );
    if ("a" in resto && resto.a) {
      const { a, ...enlace } = resto as { a: string } & AnchorHTMLAttributes<HTMLAnchorElement>;
      return <Link to={a} className={clase} {...enlace}>{contenido}</Link>;
    }
    if ("href" in resto && resto.href) {
      return <a className={clase} {...(resto as AnchorHTMLAttributes<HTMLAnchorElement>)}>{contenido}</a>;
    }
    const b = resto as ButtonHTMLAttributes<HTMLButtonElement>;
    return (
      <button type="button" {...b} disabled={b.disabled || cargando} aria-busy={cargando || undefined} className={clase}>
        {contenido}
      </button>
    );
  };
}

export const BotonPrimario = crear("primario");
export const BotonAcento = crear("acento");
export const BotonFantasma = crear("fantasma");

/**
 * EnlaceSubrayado — subrayado azul tinta de 1,5 px que se dibuja de izquierda
 * a derecha al pasar el cursor (ref-08). Estilos en `index.css` (.enlace-subrayado).
 */
export function EnlaceSubrayado({
  a,
  href,
  children,
  className,
  ...resto
}: { a?: string; href?: string; children: ReactNode; className?: string } & Omit<
  AnchorHTMLAttributes<HTMLAnchorElement>,
  "href"
>) {
  const clase = clases("enlace-subrayado", className);
  if (a) return <Link to={a} className={clase} {...resto}>{children}</Link>;
  return <a href={href} className={clase} {...resto}>{children}</a>;
}
