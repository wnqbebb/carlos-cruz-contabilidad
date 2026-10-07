import { CircleAlert, RotateCcw, X } from "lucide-react";
import { createContext, useCallback, useContext, useLayoutEffect, useRef, useState, type ReactNode } from "react";
import { clases } from "../formato";
import { BotonPrimario } from "./Botones";
import { DURACION, gsap, sinMovimiento } from "./movimiento";

/* ═══════════════════════════════════════════════════════════════════════════
   Estados transversales (spec 6.7): carga, error y avisos.
   El vacío vive en CarpetaVacia.tsx.
   ═══════════════════════════════════════════════════════════════════════════ */

/* ── carga: esqueletos con la forma real del contenido ─────────────────── */

/** Bloque gris que late suave. Sin degradados: solo opacidad. */
export function Hueso({ className, style }: { className?: string; style?: React.CSSProperties }) {
  return <span aria-hidden className={clases("block animate-pulse rounded-chip bg-tinta/[0.07]", className)} style={style} />;
}

function Anuncio({ texto }: { texto: string }) {
  return (
    <span role="status" aria-live="polite" className="sr-only">
      {texto}
    </span>
  );
}

/** Esqueleto de página con título display + bloques (forma genérica). */
export function EsqueletoPagina({ texto = "Cargando", bloques = 3 }: { texto?: string; bloques?: number }) {
  return (
    <div className="space-y-10">
      <Anuncio texto={`${texto}…`} />
      <div className="space-y-4">
        <Hueso className="h-16 w-[min(420px,80%)] rounded-control" />
        <Hueso className="h-4 w-64" />
      </div>
      <div className="grid gap-6 escritorio:grid-cols-12">
        {Array.from({ length: bloques }, (_, i) => (
          <div
            key={i}
            className={clases(
              "material-hoja space-y-4 p-6",
              i === 0 ? "escritorio:col-span-7" : i === 1 ? "escritorio:col-span-5" : "escritorio:col-span-12",
            )}
          >
            <Hueso className="h-6 w-40 rounded-full" />
            <Hueso className="h-10 w-3/4" />
            <Hueso className="h-4 w-full" />
            <Hueso className="h-4 w-5/6" />
          </div>
        ))}
      </div>
    </div>
  );
}

/** Esqueleto del Tablero: carpeta héroe + ecuación + tira de meses. */
export function EsqueletoTablero() {
  return (
    <div className="space-y-16">
      <Anuncio texto="Abriendo el tablero…" />
      <div className="space-y-4">
        <Hueso className="h-20 w-[min(380px,70%)] rounded-control" />
        <Hueso className="h-4 w-72" />
      </div>
      <div className="columnas-12">
        <div className="col-span-12 space-y-6 rounded-expediente bg-tinta/[0.06] p-8 escritorio:col-span-7">
          <Hueso className="h-3 w-64" />
          <Hueso className="h-24 w-4/5 rounded-control" />
          <div className="grid grid-cols-3 gap-6 pt-6">
            <Hueso className="h-8" />
            <Hueso className="h-8" />
            <Hueso className="h-8" />
          </div>
        </div>
        <div className="material-hoja col-span-12 space-y-5 p-7 escritorio:col-span-5">
          <Hueso className="h-7 w-48 rounded-full" />
          <Hueso className="h-8 w-full" />
          <Hueso className="h-8 w-full" />
          <Hueso className="h-8 w-full" />
          <Hueso className="h-3 w-full rounded-full" />
        </div>
      </div>
      <div className="material-hoja space-y-5 p-7">
        <Hueso className="h-7 w-48 rounded-full" />
        <div className="grid grid-cols-6 gap-2 sm:grid-cols-12">
          {Array.from({ length: 12 }, (_, i) => (
            <Hueso key={i} className="h-14" />
          ))}
        </div>
      </div>
    </div>
  );
}

/** Esqueleto de rejilla de Expedientes (Clientes, Trabajar · 01). */
export function EsqueletoExpedientes({ cuantos = 6 }: { cuantos?: number }) {
  return (
    <ul className="grid gap-x-6 gap-y-10 pt-4 sm:grid-cols-2 escritorio:grid-cols-3">
      <Anuncio texto="Abriendo expedientes…" />
      {Array.from({ length: cuantos }, (_, i) => (
        <li key={i} className="material-hoja space-y-4 p-6">
          <div className="flex items-center gap-3">
            <Hueso className="h-14 w-14 shrink-0 rounded-full" />
            <div className="flex-1 space-y-2">
              <Hueso className="h-4 w-4/5" />
              <Hueso className="h-3 w-1/2" />
            </div>
          </div>
          <Hueso className="h-px w-full" />
          <div className="grid grid-cols-2 gap-3">
            <Hueso className="h-8" />
            <Hueso className="h-8" />
          </div>
        </li>
      ))}
    </ul>
  );
}

/** Esqueleto de la ficha: cabecera Escaparate + pestañas. */
export function EsqueletoFicha() {
  return (
    <div className="space-y-12">
      <Anuncio texto="Abriendo el expediente…" />
      <div className="grid gap-10 border-b border-linea pb-8 escritorio:grid-cols-12 escritorio:items-center">
        <div className="space-y-5 escritorio:col-span-8">
          <Hueso className="h-3 w-24" />
          <Hueso className="h-16 w-11/12 rounded-control" />
          <Hueso className="h-16 w-2/3 rounded-control" />
          <Hueso className="h-4 w-80" />
        </div>
        <div className="flex justify-center escritorio:col-span-4 escritorio:justify-end">
          <Hueso className="h-[240px] w-[240px] rounded-full" />
        </div>
      </div>
      <div className="flex gap-6 border-b border-linea pb-3">
        {Array.from({ length: 6 }, (_, i) => (
          <Hueso key={i} className="h-4 w-20" />
        ))}
      </div>
    </div>
  );
}

/* ── error: hoja con borde rojo, mensaje humano, detalle plegable ───────── */
export function EstadoError({
  titulo,
  mensaje = "Puede ser la conexión o el servidor. Lo que ya estaba guardado no se perdió.",
  detalle,
  onReintentar,
}: {
  titulo: string;
  mensaje?: ReactNode;
  /** Texto técnico (mensaje del servidor). Plegado por defecto. */
  detalle?: string;
  onReintentar?: () => void;
}) {
  return (
    <section role="alert" className="material-hoja border-rojo/40 p-6 sm:p-8">
      <div className="flex items-start gap-4">
        <CircleAlert size={24} strokeWidth={1.5} aria-hidden className="mt-0.5 shrink-0 text-rojo" />
        <div className="min-w-0 flex-1">
          <h2 className="t-h2 text-tinta">{titulo}</h2>
          <p className="t-body mt-2 text-grafito">{mensaje}</p>
          {detalle && (
            <details className="mt-4">
              <summary className="t-meta cursor-pointer select-none text-gris">Detalle técnico</summary>
              <pre className="codigo mt-3 overflow-x-auto whitespace-pre-wrap rounded-chip bg-hoja-2 p-3 text-[12px] text-grafito">
                {detalle}
              </pre>
            </details>
          )}
          {onReintentar && (
            <div className="mt-6">
              <BotonPrimario onClick={onReintentar} icono={<RotateCcw size={16} strokeWidth={1.5} aria-hidden />}>
                Reintentar
              </BotonPrimario>
            </div>
          )}
        </div>
      </div>
    </section>
  );
}

/* ── avisos: «tira de papel» que entra desde abajo a la derecha ─────────── */
type Tono = "tinta" | "rojo" | "ambar";
type Aviso = { id: number; texto: string; tono: Tono };

const ContextoAvisos = createContext<(texto: string, tono?: Tono) => void>(() => {});

/** `const avisar = useAvisos(); avisar("Parámetros de 2026 guardados.")` */
export function useAvisos() {
  return useContext(ContextoAvisos);
}

export function ProveedorAvisos({ children }: { children: ReactNode }) {
  const [avisos, setAvisos] = useState<Aviso[]>([]);
  const siguiente = useRef(1);

  const quitar = useCallback((id: number) => setAvisos((a) => a.filter((x) => x.id !== id)), []);
  const avisar = useCallback(
    (texto: string, tono: Tono = "tinta") => {
      const id = siguiente.current++;
      setAvisos((a) => [...a.slice(-2), { id, texto, tono }]);
      window.setTimeout(() => quitar(id), tono === "rojo" ? 9000 : 5000);
    },
    [quitar],
  );

  return (
    <ContextoAvisos.Provider value={avisar}>
      {children}
      <div
        aria-live="polite"
        className="no-imprimir pointer-events-none fixed right-4 bottom-[100px] z-[70] flex w-[min(380px,calc(100vw-32px))] flex-col items-end gap-3 escritorio:right-8 escritorio:bottom-8"
      >
        {avisos.map((a) => (
          <TiraPapel key={a.id} aviso={a} onCerrar={() => quitar(a.id)} />
        ))}
      </div>
    </ContextoAvisos.Provider>
  );
}

function TiraPapel({ aviso, onCerrar }: { aviso: Aviso; onCerrar: () => void }) {
  const el = useRef<HTMLDivElement>(null);
  useLayoutEffect(() => {
    if (!el.current || sinMovimiento()) return;
    const ctx = gsap.context(() => {
      gsap.from(el.current, { y: 24, x: 12, opacity: 0, rotation: 1.2, duration: DURACION.interruptor, ease: "power3.out" });
    });
    return () => ctx.revert();
  }, []);
  return (
    <div
      ref={el}
      role={aviso.tono === "rojo" ? "alert" : "status"}
      className={clases(
        "material-hoja pointer-events-auto flex w-full items-start gap-3 rounded-chip border-l-4 py-3.5 pr-3 pl-4",
        aviso.tono === "rojo" ? "border-l-rojo" : aviso.tono === "ambar" ? "border-l-ambar" : "border-l-tinta",
      )}
    >
      <p className="t-body min-w-0 flex-1 text-tinta">{aviso.texto}</p>
      <button
        type="button"
        onClick={onCerrar}
        aria-label="Cerrar aviso"
        className="grid h-7 w-7 shrink-0 place-items-center rounded-full text-gris transition-colors hover:text-tinta"
      >
        <X size={14} strokeWidth={1.5} aria-hidden />
      </button>
    </div>
  );
}
