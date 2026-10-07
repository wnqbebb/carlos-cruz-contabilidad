import type { ReactNode } from "react";
import { clases } from "../formato";

/**
 * EtiquetaSeccion — «01 • RESUMEN» de ref-03: índice en mono gris, punto de
 * tinta y texto meta, dentro de una píldora con borde --linea.
 */
export function EtiquetaSeccion({
  indice,
  children,
  className,
  sobreTinta,
}: {
  indice?: string | number;
  children: ReactNode;
  className?: string;
  /** Dentro de un Expediente tinta. */
  sobreTinta?: boolean;
}) {
  const num = typeof indice === "number" ? String(indice).padStart(2, "0") : indice;
  return (
    <span
      className={clases(
        "t-meta inline-flex items-center gap-2 rounded-full border px-3 py-1.5",
        sobreTinta ? "border-sobre-tinta/15 text-sobre-tinta" : "border-linea text-tinta",
        className,
      )}
    >
      {num && <span className={sobreTinta ? "text-sobre-tinta-2" : "text-gris"}>{num}</span>}
      <span aria-hidden className={clases("h-1 w-1 rounded-full", sobreTinta ? "bg-sobre-tinta" : "bg-tinta")} />
      <span>{children}</span>
    </span>
  );
}

/**
 * MetaEncabezado — fila de cuatro columnas de texto diminuto (ref-06), arriba
 * de cada página, con la línea horizontal que cierra la rejilla (spec 4.3).
 * En móvil pasa a dos columnas.
 */
export function MetaEncabezado({ columnas, className }: { columnas: ReactNode[]; className?: string }) {
  return (
    <div
      className={clases(
        "t-meta grid grid-cols-2 gap-x-[var(--canal)] gap-y-1 border-b border-linea pb-3 text-gris escritorio:grid-cols-4",
        className,
      )}
    >
      {columnas.slice(0, 4).map((c, i) => (
        <span key={i} className={clases("min-w-0 truncate", i === 3 && "escritorio:text-right")}>
          {c}
        </span>
      ))}
    </div>
  );
}

/** Título de página en `display` (ref-02): bloque compacto, interlineado 0,92. */
export function TituloPagina({
  children,
  subtitulo,
  className,
}: {
  children: ReactNode;
  subtitulo?: ReactNode;
  className?: string;
}) {
  return (
    <div className={clases("min-w-0", className)}>
      <h1 className="t-display text-tinta">{children}</h1>
      {subtitulo && <p className="t-body mt-4 text-grafito">{subtitulo}</p>}
    </div>
  );
}
