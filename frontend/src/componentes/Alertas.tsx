import { Info, OctagonX, TriangleAlert } from "lucide-react";
import { useMemo, useState } from "react";
import type { Alerta } from "../tipos";
import { clases } from "../formato";
import { Insignia } from "./ui";

const ICONO = { error: OctagonX, advertencia: TriangleAlert, info: Info };
const TONO = { error: "rojo", advertencia: "ambar", info: "neutro" } as const;
const PLURAL = { error: "Errores", advertencia: "Advertencias", info: "Informativas" } as const;

export function ListaAlertas({ alertas, limite }: { alertas: Alerta[]; limite?: number }) {
  const [filtro, setFiltro] = useState<"todas" | Alerta["severidad"]>("todas");
  const [verTodas, setVerTodas] = useState(false);
  const conteo = useMemo(() => {
    const c = { error: 0, advertencia: 0, info: 0 };
    alertas.forEach((a) => (c[a.severidad] += 1));
    return c;
  }, [alertas]);
  const lista = alertas.filter((a) => filtro === "todas" || a.severidad === filtro);
  const visibles = limite && !verTodas ? lista.slice(0, limite) : lista;
  if (!alertas.length) return <p className="text-sm text-azul">✓ Sin alertas.</p>;
  return (
    <div className="space-y-3">
      <div className="flex flex-wrap gap-2">
        {(["todas", "error", "advertencia", "info"] as const).map((f) => (
          <button key={f} onClick={() => setFiltro(f)}
            className={clases("rounded-full px-3 py-1 text-xs font-medium ring-1 ring-inset transition",
              filtro === f ? "bg-tinta text-sobre-tinta ring-tinta" : "bg-papel text-grafito ring-linea hover:bg-hoja")}>
            {f === "todas" ? `Todas (${alertas.length})` : `${PLURAL[f]} (${conteo[f]})`}
          </button>
        ))}
      </div>
      <ul className="space-y-2">
        {visibles.map((a, i) => (
          <li key={i} className={clases("rounded-lg border px-3.5 py-2.5 text-sm",
            a.severidad === "error" ? "border-rojo bg-rojo-suave/60" : a.severidad === "advertencia" ? "border-ambar bg-ambar-suave" : "border-azul bg-azul-suave/50")}>
            <div className="flex items-start gap-2">
              {(() => { const Icono = ICONO[a.severidad]; return <Icono size={16} strokeWidth={1.5} aria-hidden className="mt-0.5 shrink-0" />; })()}
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-2">
                  <Insignia tono={TONO[a.severidad]}>{a.codigo}</Insignia>
                  <span className="text-tinta">{a.mensaje}</span>
                </div>
                {a.detalle && <p className="mt-1 text-xs text-grafito">{a.detalle}</p>}
                {a.origen && <p className="mt-0.5 text-[11px] text-gris">{a.origen}</p>}
              </div>
            </div>
          </li>
        ))}
      </ul>
      {limite && lista.length > limite && (
        <button className="text-sm font-medium text-tinta hover:underline" onClick={() => setVerTodas(!verTodas)}>
          {verTodas ? "Ver menos" : `Ver las ${lista.length} alertas`}
        </button>
      )}
    </div>
  );
}
