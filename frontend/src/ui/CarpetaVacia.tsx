import type { ReactNode } from "react";
import { clases } from "../formato";

/**
 * Estado vacío con la carpeta azul de ref-08 (spec 6.3 y 6.7): carpeta +
 * frase + acción. La carpeta usa solo tokens (azul suave y azul tinta).
 */
export function Carpeta({ tamano = 120, className }: { tamano?: number; className?: string }) {
  return (
    <svg
      width={tamano}
      height={tamano * 0.8}
      viewBox="0 0 120 96"
      aria-hidden
      className={clases("shrink-0", className)}
    >
      {/* trasera con pestaña */}
      <path
        d="M8 20a8 8 0 0 1 8-8h28l10 10h50a8 8 0 0 1 8 8v54a8 8 0 0 1-8 8H16a8 8 0 0 1-8-8z"
        fill="var(--azul-suave)"
        stroke="var(--azul-tinta)"
        strokeWidth="1.5"
      />
      {/* hoja de papel asomando */}
      <rect x="20" y="26" width="80" height="40" rx="3" fill="var(--hoja)" stroke="var(--linea)" />
      <path d="M30 38h44M30 46h60M30 54h36" stroke="var(--linea)" strokeWidth="2" strokeLinecap="round" />
      {/* frente */}
      <path
        d="M8 42a6 6 0 0 1 6-6h92a6 6 0 0 1 6 6v42a8 8 0 0 1-8 8H16a8 8 0 0 1-8-8z"
        fill="var(--azul-suave)"
        stroke="var(--azul-tinta)"
        strokeWidth="1.5"
      />
      <path d="M48 64h24" stroke="var(--azul-tinta)" strokeWidth="1.5" strokeLinecap="round" />
    </svg>
  );
}

export function CarpetaVacia({
  titulo,
  children,
  accion,
  className,
}: {
  titulo: ReactNode;
  children?: ReactNode;
  accion?: ReactNode;
  className?: string;
}) {
  return (
    <div className={clases("flex flex-col items-center px-6 py-16 text-center", className)}>
      <Carpeta />
      <h2 className="t-h1 mt-8 text-tinta">{titulo}</h2>
      {children && <p className="t-body mt-3 max-w-md text-grafito">{children}</p>}
      {accion && <div className="mt-8">{accion}</div>}
    </div>
  );
}
