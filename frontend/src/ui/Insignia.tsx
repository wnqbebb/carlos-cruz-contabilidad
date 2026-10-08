import { Check, CircleDashed, Lock, TriangleAlert } from "lucide-react";
import type { ReactNode } from "react";
import { clases } from "../formato";

/**
 * Insignia de estado (spec 4.5). Cada estado tiene texto propio: el color
 * nunca es el único portador de significado.
 *
 *   cuadra      azul + brillo «Cuadra»  (el único brillo permitido)
 *   descuadre   rojo
 *   por-cerrar  ámbar
 *   cerrado     tinta · «Cerrado · listo para firmar»
 *   activo / inactivo / archivado   neutros
 */
export type EstadoInsignia =
  | "cuadra"
  | "descuadre"
  | "por-cerrar"
  | "cerrado"
  | "activo"
  | "inactivo"
  | "archivado";

const ESTILO: Record<EstadoInsignia, { clase: string; texto: string; icono?: ReactNode }> = {
  cuadra: {
    clase: "bg-azul text-sobre-color brillo-cuadra",
    texto: "Cuadra",
    icono: <Check size={14} strokeWidth={2} aria-hidden />,
  },
  descuadre: {
    clase: "bg-rojo-suave text-rojo border border-rojo/30",
    texto: "Descuadre",
    icono: <TriangleAlert size={14} strokeWidth={1.5} aria-hidden />,
  },
  "por-cerrar": {
    clase: "bg-ambar-suave text-ambar border border-ambar/30",
    texto: "Por cerrar",
    icono: <CircleDashed size={14} strokeWidth={1.5} aria-hidden />,
  },
  cerrado: {
    clase: "bg-tinta text-sobre-tinta",
    texto: "Cerrado · listo para firmar",
    icono: <Lock size={13} strokeWidth={1.5} aria-hidden />,
  },
  activo: { clase: "bg-hoja text-tinta border border-tinta/25", texto: "Activo" },
  inactivo: { clase: "bg-hoja-2 text-grafito border border-linea", texto: "Inactivo" },
  archivado: { clase: "bg-transparent text-gris border border-dashed border-tinta/20", texto: "Archivado" },
};

export function InsigniaEstado({
  estado,
  children,
  discreta,
  className,
}: {
  estado: EstadoInsignia;
  /** «Cuadra» en azul suave y sin brillo: para listas de comprobaciones, donde
   *  varias insignias juntas romperían la regla de un solo azul sólido por vista. */
  discreta?: boolean;
  /** Reemplaza el texto por defecto (p. ej. «Descuadre de $ 50.000»). */
  children?: ReactNode;
  className?: string;
}) {
  const e = ESTILO[estado];
  return (
    <span
      className={clases(
        "inline-flex shrink-0 items-center gap-1.5 whitespace-nowrap rounded-full px-2.5 py-1 text-[12px] font-medium leading-4",
        discreta && estado === "cuadra" ? "border border-azul/30 bg-azul-suave text-azul" : e.clase,
        className,
      )}
    >
      {e.icono}
      {children ?? e.texto}
    </span>
  );
}
