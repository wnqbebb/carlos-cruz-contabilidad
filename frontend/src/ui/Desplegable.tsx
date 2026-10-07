import { Check, ChevronDown } from "lucide-react";
import { useEffect, useId, useRef, useState, type KeyboardEvent } from "react";
import { clases } from "../formato";

/**
 * Desplegable con estilo propio (spec 6.3: «ordenar como menú desplegable con
 * estilo propio»). Botón píldora + lista de cristal (flota sobre contenido).
 * Teclado: Enter/Espacio/↓ abre, ↑↓ se mueve, Enter elige, Esc cierra.
 */
export function Desplegable<T extends string>({
  etiqueta,
  valor,
  opciones,
  onCambio,
  prefijo,
  className,
}: {
  /** Nombre accesible. */
  etiqueta: string;
  valor: T;
  opciones: { valor: T; texto: string }[];
  onCambio: (v: T) => void;
  /** Texto antes del valor en el botón (p. ej. «Ordenar por»). */
  prefijo?: string;
  className?: string;
}) {
  const [abierto, setAbierto] = useState(false);
  const [foco, setFoco] = useState(0);
  const raiz = useRef<HTMLDivElement>(null);
  const id = useId();
  const actual = opciones.find((o) => o.valor === valor);

  useEffect(() => {
    if (!abierto) return;
    const fuera = (e: MouseEvent) => {
      if (!raiz.current?.contains(e.target as Node)) setAbierto(false);
    };
    document.addEventListener("mousedown", fuera);
    return () => document.removeEventListener("mousedown", fuera);
  }, [abierto]);

  const abrir = () => {
    setFoco(Math.max(0, opciones.findIndex((o) => o.valor === valor)));
    setAbierto(true);
  };
  const elegir = (v: T) => {
    onCambio(v);
    setAbierto(false);
  };

  const teclado = (e: KeyboardEvent) => {
    if (!abierto) {
      if (["Enter", " ", "ArrowDown"].includes(e.key)) {
        e.preventDefault();
        abrir();
      }
      return;
    }
    if (e.key === "Escape") {
      e.preventDefault();
      setAbierto(false);
    } else if (e.key === "ArrowDown") {
      e.preventDefault();
      setFoco((f) => (f + 1) % opciones.length);
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setFoco((f) => (f - 1 + opciones.length) % opciones.length);
    } else if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      elegir(opciones[foco].valor);
    }
  };

  return (
    <div ref={raiz} className={clases("relative", className)} onKeyDown={teclado}>
      <button
        type="button"
        aria-haspopup="listbox"
        aria-expanded={abierto}
        aria-controls={id}
        aria-label={`${etiqueta}: ${actual?.texto ?? ""}`}
        onClick={() => (abierto ? setAbierto(false) : abrir())}
        className="flex h-11 max-w-full items-center gap-2 rounded-full border border-linea bg-hoja px-4 text-[15px] text-tinta transition-colors hover:border-tinta/30"
      >
        {prefijo && <span className="text-gris">{prefijo}</span>}
        <span className="recortar font-medium">{actual?.texto}</span>
        <ChevronDown
          size={16}
          strokeWidth={1.5}
          aria-hidden
          className={clases("shrink-0 transition-transform duration-200", abierto && "rotate-180")}
        />
      </button>

      {abierto && (
        <ul
          id={id}
          role="listbox"
          aria-label={etiqueta}
          className="material-cristal absolute right-0 z-30 mt-2 min-w-[220px] overflow-hidden rounded-control p-1.5 shadow-expediente"
        >
          {opciones.map((o, i) => {
            const elegida = o.valor === valor;
            return (
              <li
                key={o.valor}
                role="option"
                aria-selected={elegida}
                onMouseEnter={() => setFoco(i)}
                onClick={() => elegir(o.valor)}
                className={clases(
                  "flex cursor-pointer items-center justify-between gap-3 rounded-chip px-3 py-2 text-[14px]",
                  i === foco ? "bg-tinta text-sobre-tinta" : "text-tinta",
                )}
              >
                {o.texto}
                {elegida && <Check size={15} strokeWidth={1.5} aria-hidden />}
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
