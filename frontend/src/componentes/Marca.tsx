import { clases } from "../formato";

export const MARCA = "Carlos Cruz";
export const LEMA = "Contabilidad que cuadra.";
export const CARGO = "Contador Público";
export const TARJETA_PROFESIONAL = "T.P. 103028-T";

/**
 * «CC» en Geist Sans 600 con tracking −0,03 em, convertido a contornos.
 * Se usan contornos (no <text>) para que el monograma sea idéntico en la app,
 * en el favicon y en cualquier exportación, aunque la fuente no esté cargada.
 * Generado desde @fontsource/geist-sans latin-600 a 18 px de cuerpo.
 */
const LETRAS_CC =
  "M12.26-4.46L9.77-4.59C9.47-2.79 8.39-1.78 6.79-1.78C4.34-1.78 3.22-3.82 3.22-6.37C3.22-8.95 4.32-11.00 6.79-11.00C8.32-11.00 9.38-10.08 9.72-8.42L12.19-8.55C11.63-11.36 9.70-13.07 6.82-13.07C3.06-13.07 0.79-10.13 0.79-6.37C0.79-2.63 3.08 0.29 6.82 0.29C9.85 0.29 11.75-1.51 12.26-4.46Z" +
  "M24.68-4.46L22.19-4.59C21.89-2.79 20.81-1.78 19.21-1.78C16.76-1.78 15.64-3.82 15.64-6.37C15.64-8.95 16.74-11.00 19.21-11.00C20.74-11.00 21.80-10.08 22.14-8.42L24.61-8.55C24.05-11.36 22.12-13.07 19.24-13.07C15.48-13.07 13.21-10.13 13.21-6.37C13.21-2.63 15.50 0.29 19.24 0.29C22.27 0.29 24.17-1.51 24.68-4.46Z";

/**
 * Monograma (spec 5): cuadrado de tinta, radio 10, «CC» en papel claro y
 * debajo una cuenta T mínima — una línea horizontal con un trazo vertical
 * centrado. Es el sello de marca y el favicon (`public/favicon.svg`).
 *
 * Geometría en una caja de 40 × 40: letras de y = 8 a 21,4; la T en y = 26,5
 * (horizontal, x 11–29) y de 26,5 a 33 (vertical). Ver docs/diseno/MARCA.md.
 */
export function Monograma({ tamano = 40, className }: { tamano?: number; className?: string }) {
  return (
    <svg
      width={tamano}
      height={tamano}
      viewBox="0 0 40 40"
      role="img"
      aria-label={MARCA}
      className={clases("monograma shrink-0", className)}
    >
      <rect width="40" height="40" rx="10" fill="var(--tinta)" />
      <path d={LETRAS_CC} transform="translate(7.26 21.07)" fill="var(--sobre-tinta)" />
      <path
        data-cuenta-t
        d="M11 26.5 H29 M20 26.5 V33"
        stroke="var(--sobre-tinta)"
        strokeWidth="1.8"
        strokeLinecap="round"
        fill="none"
      />
    </svg>
  );
}

/** Logotipo: monograma + nombre + «CONTADOR PÚBLICO · T.P. 103028-T». */
export function Logotipo({ tamano = 40, className }: { tamano?: number; className?: string }) {
  return (
    <span className={clases("flex min-w-0 items-center gap-3", className)}>
      <Monograma tamano={tamano} />
      <span className="min-w-0 leading-none">
        <span className="block truncate text-[17px] font-semibold tracking-[-0.03em] text-tinta">{MARCA}</span>
        {/* «CONTADOR PÚBLICO · T.P. 103028-T»: en 248 px no cabe en una línea */}
        <span className="t-meta mt-1.5 block text-[10px] tracking-[0.1em] text-gris">
          {CARGO} ·<br />
          {TARJETA_PROFESIONAL}
        </span>
      </span>
    </span>
  );
}
