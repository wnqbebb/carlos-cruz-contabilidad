import { Check, PenLine, Undo2, X } from "lucide-react";
import { useEffect, useRef, useState, type ReactNode } from "react";
import { clases } from "../formato";

/**
 * Dato editable en su sitio (spec v2.2 · Fase 6.3).
 *
 * Clic sobre el valor, el lápiz o Enter con el foco encima → se edita ahí
 * mismo. Enter guarda, Escape cancela. Después de guardar queda unos segundos
 * «Deshacer», que vuelve al valor anterior con otro guardado.
 */
export function EnLinea({
  valor,
  etiqueta,
  onGuardar,
  children,
  opciones,
  formatear,
  tipo = "texto",
  className,
}: {
  valor: string;
  etiqueta: string;
  onGuardar: (nuevo: string) => Promise<void>;
  /** Cómo se ve el valor cuando no se está editando. */
  children?: ReactNode;
  /** Si llega, se edita con una lista de opciones. */
  opciones?: { valor: string; texto: string }[];
  formatear?: (v: string) => string;
  tipo?: "texto" | "numero";
  className?: string;
}) {
  const [editando, setEditando] = useState(false);
  const [borrador, setBorrador] = useState(valor);
  const [guardando, setGuardando] = useState(false);
  const [error, setError] = useState("");
  const [anterior, setAnterior] = useState<string | null>(null);
  const campo = useRef<HTMLInputElement & HTMLSelectElement>(null);

  useEffect(() => {
    if (editando) campo.current?.focus();
  }, [editando]);
  useEffect(() => {
    if (anterior === null) return;
    const t = setTimeout(() => setAnterior(null), 8000);
    return () => clearTimeout(t);
  }, [anterior]);

  const guardar = async (nuevo: string, deshacer = false) => {
    const limpio = tipo === "numero" ? nuevo.replace(/[^\d.]/g, "") : nuevo.trim();
    if (!deshacer && (limpio === valor || (!limpio && tipo === "texto"))) {
      setEditando(false);
      return;
    }
    setGuardando(true);
    setError("");
    try {
      await onGuardar(limpio);
      setAnterior(deshacer ? null : valor);
      setEditando(false);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setGuardando(false);
    }
  };

  if (editando) {
    const comun = {
      ref: campo,
      "aria-label": etiqueta,
      disabled: guardando,
      onKeyDown: (e: React.KeyboardEvent) => {
        if (e.key === "Enter") guardar(borrador);
        if (e.key === "Escape") {
          setBorrador(valor);
          setEditando(false);
        }
      },
      className:
        "min-w-0 flex-1 rounded-chip border border-linea bg-hoja px-2 py-1 text-inherit text-tinta focus-visible:outline-none",
    };
    return (
      <span className={clases("inline-flex max-w-full flex-wrap items-center gap-2 align-middle", className)}>
        {opciones ? (
          <select {...comun} value={borrador} onChange={(e) => setBorrador(e.target.value)}>
            {opciones.map((o) => (
              <option key={o.valor} value={o.valor}>{o.texto}</option>
            ))}
          </select>
        ) : (
          <input
            {...comun}
            value={borrador}
            inputMode={tipo === "numero" ? "decimal" : undefined}
            onChange={(e) => setBorrador(e.target.value)}
            size={Math.max(6, Math.min(48, borrador.length + 2))}
          />
        )}
        <button type="button" onClick={() => guardar(borrador)} aria-label={`Guardar ${etiqueta}`}
          className="grid h-8 w-8 place-items-center rounded-full bg-tinta text-sobre-tinta">
          <Check size={14} strokeWidth={2} aria-hidden />
        </button>
        <button type="button" onClick={() => { setBorrador(valor); setEditando(false); }} aria-label="Cancelar"
          className="grid h-8 w-8 place-items-center rounded-full border border-linea text-grafito">
          <X size={14} strokeWidth={2} aria-hidden />
        </button>
        {error && <span className="t-small basis-full text-rojo">{error}</span>}
      </span>
    );
  }

  return (
    <span className={clases("group inline-flex max-w-full flex-wrap items-center gap-2 align-middle", className)}>
      <span
        role="button"
        tabIndex={0}
        title={`Editar ${etiqueta.toLowerCase()}`}
        onClick={() => { setBorrador(valor); setEditando(true); }}
        onKeyDown={(e) => {
          if (e.key === "Enter") {
            e.preventDefault();
            setBorrador(valor);
            setEditando(true);
          }
        }}
        className="cursor-text rounded-chip decoration-1 underline-offset-4 hover:underline focus-visible:underline"
      >
        {children ?? (valor ? (formatear ? formatear(valor) : valor) : <span className="text-gris">Sin {etiqueta.toLowerCase()}</span>)}
      </span>
      <button
        type="button"
        onClick={() => { setBorrador(valor); setEditando(true); }}
        aria-label={`Editar ${etiqueta.toLowerCase()}`}
        className="grid h-7 w-7 shrink-0 place-items-center rounded-full text-gris opacity-60 transition-opacity hover:bg-hoja-2 hover:text-tinta group-hover:opacity-100"
      >
        <PenLine size={13} strokeWidth={1.5} aria-hidden />
      </button>
      {anterior !== null && (
        <button
          type="button"
          onClick={() => guardar(anterior, true)}
          className="t-small inline-flex items-center gap-1 rounded-full border border-linea px-2.5 py-1 text-grafito hover:text-tinta"
        >
          <Undo2 size={12} strokeWidth={1.5} aria-hidden /> Guardado · Deshacer
        </button>
      )}
    </span>
  );
}
