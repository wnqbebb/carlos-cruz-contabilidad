import { Info, OctagonX, TriangleAlert, X } from "lucide-react";
import { useEffect, useId, useLayoutEffect, useRef, type ReactNode } from "react";
import { clases, esNegativo, pesos } from "../formato";
import { Carpeta } from "../ui/CarpetaVacia";
import { DURACION, Flip, sinMovimiento } from "../ui/movimiento";

/* ═════════════════════════════════════════════════════════════════════════
   Primitivas de pantalla (v2.1)

   Conservan la misma API que usaban las pantallas, pero ya hablan el
   lenguaje del sistema: tokens, materiales Hoja/Hundido/Cristal, tipografía
   t-*, íconos lucide. Los componentes de firma nuevos viven en src/ui/;
   estas primitivas son el puente mientras cada pantalla se migra.
   ═════════════════════════════════════════════════════════════════════════ */

/* ── etiqueta técnica (meta, mono, mayúsculas) ─────────────────────────── */
export function Rotulo({ children, className, id }: { children?: ReactNode; className?: string; id?: string }) {
  return (
    <span id={id} className={clases("t-meta text-gris", className)}>
      {children}
    </span>
  );
}

/* ── botones ───────────────────────────────────────────────────────────── */
type Variante =
  | "solido" | "lima" | "contorno" | "fantasma" | "peligro"
  | "primario" | "secundario" | "exito";
type Tamano = "sm" | "md" | "lg";

/* «lima», «primario» y «exito» son la acción principal: azul (una por vista).
   «solido» es el BotonPrimario de tinta del spec. */
const ESTILO_VARIANTE: Record<Variante, string> = {
  solido: "bg-tinta text-sobre-tinta hover:bg-tinta-2",
  lima: "bg-azul text-white hover:bg-azul-tinta",
  contorno: "border border-linea bg-transparent text-tinta hover:border-tinta/30 hover:bg-hoja",
  fantasma: "text-grafito hover:bg-hoja-2 hover:text-tinta",
  peligro: "bg-rojo text-white hover:bg-rojo-cartel",
  primario: "bg-azul text-white hover:bg-azul-tinta",
  secundario: "border border-linea bg-transparent text-tinta hover:border-tinta/30 hover:bg-hoja",
  exito: "bg-azul text-white hover:bg-azul-tinta",
};

const ESTILO_TAMANO: Record<Tamano, string> = {
  sm: "h-9 px-4 text-[13px] gap-1.5",
  md: "h-11 px-5 text-[15px] gap-2",
  lg: "h-12 px-6 text-[15px] gap-2.5",
};

const BASE_BOTON =
  "inline-flex shrink-0 select-none items-center justify-center rounded-full font-medium " +
  "transition-[background-color,border-color,color,transform] duration-200 active:scale-[0.98] " +
  "disabled:cursor-not-allowed disabled:opacity-45";

export function Boton({
  variante = "contorno",
  tamano = "md",
  cargando,
  className,
  children,
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement> & {
  variante?: Variante;
  tamano?: Tamano;
  cargando?: boolean;
}) {
  return (
    <button
      type="button"
      {...props}
      disabled={props.disabled || cargando}
      aria-busy={cargando || undefined}
      className={clases(BASE_BOTON, ESTILO_VARIANTE[variante], ESTILO_TAMANO[tamano], className)}
    >
      {cargando && (
        <span aria-hidden className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-current border-t-transparent" />
      )}
      {children}
    </button>
  );
}

export function Enlace({
  href,
  variante = "contorno",
  tamano = "md",
  descargar,
  className,
  children,
}: {
  href: string;
  variante?: Variante;
  tamano?: Tamano;
  descargar?: boolean;
  className?: string;
  children: ReactNode;
}) {
  return (
    <a
      href={href}
      download={descargar}
      className={clases(BASE_BOTON, ESTILO_VARIANTE[variante], ESTILO_TAMANO[tamano], className)}
    >
      {children}
    </a>
  );
}

/* ── contenedores ──────────────────────────────────────────────────────── */
export function Tarjeta({
  rotulo,
  titulo,
  subtitulo,
  acciones,
  children,
  className,
  sinRelleno,
}: {
  rotulo?: ReactNode;
  titulo?: ReactNode;
  subtitulo?: ReactNode;
  acciones?: ReactNode;
  children: ReactNode;
  className?: string;
  sinRelleno?: boolean;
}) {
  return (
    <section className={clases("material-hoja contener relative overflow-hidden", className)}>
      {(titulo || acciones || rotulo) && (
        <header className="contener flex flex-wrap items-end justify-between gap-3 border-b border-linea px-5 pt-5 pb-4 sm:px-6">
          <div className="contener min-w-0">
            {rotulo && <Rotulo className="block">{rotulo}</Rotulo>}
            {titulo && <h2 className="t-h2 mt-1.5 text-tinta">{titulo}</h2>}
            {subtitulo && <p className="t-small mt-1 text-gris">{subtitulo}</p>}
          </div>
          {acciones && <div className="flex flex-wrap items-center gap-2">{acciones}</div>}
        </header>
      )}
      <div className={clases("contener", sinRelleno ? "" : "p-5 sm:p-6")}>{children}</div>
    </section>
  );
}

/* ── distintivos ───────────────────────────────────────────────────────── */
/* «verde» y «lima» se conservan como nombres por compatibilidad, pero pintan
   azul: en esta aplicación no existe el verde (spec 4.1). */
export type Tono = "verde" | "ambar" | "rojo" | "azul" | "lima" | "neutro" | "tinta" | "gris";

const ESTILO_TONO: Record<Tono, string> = {
  verde: "bg-azul-suave text-azul border border-azul/30",
  ambar: "bg-ambar-suave text-ambar border border-ambar/30",
  rojo: "bg-rojo-suave text-rojo border border-rojo/30",
  azul: "bg-azul-suave text-azul border border-azul/30",
  lima: "bg-azul-suave text-azul border border-azul/30",
  neutro: "bg-hoja text-grafito border border-linea",
  tinta: "bg-tinta text-sobre-tinta",
  gris: "bg-hoja-2 text-grafito border border-linea",
};

export function Insignia({
  tono = "neutro",
  children,
  className,
}: {
  tono?: Tono;
  children: ReactNode;
  className?: string;
}) {
  return (
    <span
      className={clases(
        "inline-flex shrink-0 items-center gap-1.5 whitespace-nowrap rounded-full px-2.5 py-1 text-[12px] font-medium leading-4",
        ESTILO_TONO[tono],
        className,
      )}
    >
      {children}
    </span>
  );
}

/* ── cifra destacada (tarjeta de indicador) ────────────────────────────── */
export function Cifra({
  rotulo,
  valor,
  detalle,
  tono,
  destacada,
  className,
}: {
  rotulo: ReactNode;
  valor: ReactNode;
  detalle?: ReactNode;
  tono?: Tono;
  destacada?: boolean;
  className?: string;
}) {
  return (
    <div className={clases("contener @container p-5", destacada ? "material-expediente" : "material-hoja", className)}>
      <Rotulo className={destacada ? "!text-sobre-tinta-2" : undefined}>{rotulo}</Rotulo>
      <div
        className={clases(
          "cifras mt-3 font-medium leading-none tracking-[-0.03em]",
          destacada ? "text-sobre-tinta" : tono === "rojo" ? "text-rojo" : "text-tinta",
        )}
        // Cifra exacta: si no cabe, se achica con el ancho de la tarjeta; nunca se parte.
        style={{ fontSize: "clamp(18px, 9.5cqi, 32px)" }}
      >
        {valor}
      </div>
      {detalle && (
        <div className={clases("t-small mt-2", destacada ? "text-sobre-tinta-2" : "text-gris")}>{detalle}</div>
      )}
    </div>
  );
}

/** Importe ya formateado y coloreado según su signo. */
export function Dinero({ valor, className }: { valor: string | number | null | undefined; className?: string }) {
  return (
    <span className={clases("cifras", esNegativo(valor) ? "text-rojo" : "text-tinta", className)}>{pesos(valor)}</span>
  );
}

/* ── formulario: campos Hundidos (spec 4.4) ────────────────────────────── */
const BASE_CAMPO =
  "h-11 rounded-control border-0 bg-hoja-2 px-4 text-[15px] text-tinta shadow-hundido " +
  "placeholder:text-gris transition-shadow focus:outline-none focus-visible:shadow-[var(--foco)]";

export const estiloCampo = "w-full " + BASE_CAMPO;
export const estiloCampoAuto = "w-auto max-w-full shrink-0 " + BASE_CAMPO;
export const estiloInput = estiloCampo;

export function Campo({
  etiqueta,
  ayuda,
  error,
  obligatorio,
  children,
  className,
}: {
  etiqueta: string;
  ayuda?: string;
  error?: string;
  obligatorio?: boolean;
  children: ReactNode;
  className?: string;
}) {
  return (
    <label className={clases("block", className)}>
      <span className="t-meta mb-2 block text-gris">
        {etiqueta}
        {obligatorio && (
          <span className="ml-1 text-rojo" aria-label="obligatorio">
            *
          </span>
        )}
      </span>
      {children}
      {error ? (
        <span className="t-small mt-1.5 block font-medium text-rojo">{error}</span>
      ) : (
        ayuda && <span className="t-small mt-1.5 block text-gris">{ayuda}</span>
      )}
    </label>
  );
}

/* ── pestañas con índice (spec 6.4) ────────────────────────────────────────
   Resumen⁰¹ Periodos⁰² … La raya de tinta bajo la activa se desliza con Flip. */
export function Pestanas<T extends string>({
  opciones,
  valor,
  onCambio,
  className,
}: {
  opciones: { id: T; texto: string; cuenta?: number }[];
  valor: T;
  onCambio: (v: T) => void;
  className?: string;
}) {
  const idFlip = "pestana-" + useId();
  const lista = useRef<HTMLDivElement>(null);
  const estado = useRef<Flip.FlipState | null>(null);

  const elegir = (v: T) => {
    if (v === valor) return;
    const raya = lista.current?.querySelector<HTMLElement>(`[data-flip-id="${idFlip}"]`);
    if (raya && !sinMovimiento()) estado.current = Flip.getState(raya);
    onCambio(v);
  };

  useLayoutEffect(() => {
    const s = estado.current;
    estado.current = null;
    const raya = lista.current?.querySelector<HTMLElement>(`[data-flip-id="${idFlip}"]`);
    if (!s || !raya) return;
    const anim = Flip.from(s, { targets: raya, duration: DURACION.interruptor, ease: "power3.inOut" });
    return () => {
      anim.kill();
    };
  }, [valor, idFlip]);

  return (
    <div
      ref={lista}
      role="tablist"
      className={clases("barra-fina flex gap-6 overflow-x-auto border-b border-linea", className)}
      onKeyDown={(e) => {
        const i = opciones.findIndex((o) => o.id === valor);
        const j = e.key === "ArrowRight" ? i + 1 : e.key === "ArrowLeft" ? i - 1 : -99;
        if (j === -99) return;
        e.preventDefault();
        const o = opciones[(j + opciones.length) % opciones.length];
        elegir(o.id);
        lista.current?.querySelectorAll<HTMLElement>("[role=tab]")[(j + opciones.length) % opciones.length]?.focus();
      }}
    >
      {opciones.map((o, i) => {
        const activo = valor === o.id;
        return (
          <button
            key={o.id}
            type="button"
            role="tab"
            aria-selected={activo}
            tabIndex={activo ? 0 : -1}
            onClick={() => elegir(o.id)}
            className={clases(
              "relative flex shrink-0 items-center gap-2 pt-1 pb-3 text-[15px] font-medium transition-colors duration-200",
              activo ? "text-tinta" : "text-grafito hover:text-tinta",
            )}
          >
            <span>
              {o.texto}
              <span aria-hidden className="codigo relative -top-[0.55em] ml-[0.2em] text-[0.62em] text-gris">
                {String(i + 1).padStart(2, "0")}
              </span>
            </span>
            {o.cuenta !== undefined && o.cuenta > 0 && (
              <span className="cifras rounded-full border border-linea px-1.5 text-[11px] leading-[18px] text-grafito">
                {o.cuenta}
              </span>
            )}
            {activo && (
              <span data-flip-id={idFlip} aria-hidden className="absolute inset-x-0 -bottom-px h-0.5 rounded-full bg-tinta" />
            )}
          </button>
        );
      })}
    </div>
  );
}

export const Pestañas = Pestanas;

/* ── estados ───────────────────────────────────────────────────────────── */
export function Vacio({
  titulo,
  children,
  accion,
}: {
  titulo?: string;
  children?: ReactNode;
  accion?: ReactNode;
}) {
  return (
    <div className="material-hoja flex flex-col items-center px-6 py-12 text-center sm:py-14">
      <Carpeta tamano={88} />
      {titulo && <p className="t-h2 mt-6 text-tinta">{titulo}</p>}
      {children && <p className="t-body mx-auto mt-2 max-w-md text-grafito">{children}</p>}
      {accion && <div className="mt-6 flex justify-center">{accion}</div>}
    </div>
  );
}

export function Cargando({ texto = "Cargando" }: { texto?: string }) {
  return (
    <div role="status" aria-live="polite" className="material-hoja space-y-4 p-6">
      <span className="sr-only">{texto}…</span>
      <span aria-hidden className="block h-5 w-48 animate-pulse rounded-full bg-tinta/[0.07]" />
      <span aria-hidden className="block h-4 w-full animate-pulse rounded-chip bg-tinta/[0.07]" />
      <span aria-hidden className="block h-4 w-11/12 animate-pulse rounded-chip bg-tinta/[0.07]" />
      <span aria-hidden className="block h-4 w-4/5 animate-pulse rounded-chip bg-tinta/[0.07]" />
    </div>
  );
}

const ICONO_AVISO: Partial<Record<Tono, typeof Info>> = { rojo: OctagonX, ambar: TriangleAlert };

export function Aviso({
  tono = "ambar",
  titulo,
  children,
  onCerrar,
}: {
  tono?: Tono;
  titulo?: ReactNode;
  children: ReactNode;
  onCerrar?: () => void;
}) {
  const Icono = ICONO_AVISO[tono] ?? Info;
  return (
    <div
      role={tono === "rojo" ? "alert" : "status"}
      className={clases("flex items-start gap-3 rounded-control px-4 py-3.5 text-[14px]", ESTILO_TONO[tono])}
    >
      <Icono size={18} strokeWidth={1.5} aria-hidden className="mt-0.5 shrink-0" />
      <div className="min-w-0 flex-1">
        {titulo && <p className="font-semibold">{titulo}</p>}
        <div className={titulo ? "mt-0.5 leading-relaxed" : undefined}>{children}</div>
      </div>
      {onCerrar && (
        <button type="button" onClick={onCerrar} aria-label="Cerrar aviso" className="shrink-0 opacity-70 hover:opacity-100">
          <X size={16} strokeWidth={1.5} aria-hidden />
        </button>
      )}
    </div>
  );
}

/* ── ventana modal: cristal sobre velo (spec 4.4) ──────────────────────── */
export function Dialogo({
  titulo,
  rotulo,
  onCerrar,
  ancho = "max-w-2xl",
  pie,
  children,
}: {
  titulo: ReactNode;
  rotulo?: ReactNode;
  onCerrar: () => void;
  ancho?: string;
  pie?: ReactNode;
  children: ReactNode;
}) {
  const idTitulo = useId();
  useEffect(() => {
    const alPulsar = (e: KeyboardEvent) => e.key === "Escape" && onCerrar();
    document.addEventListener("keydown", alPulsar);
    const previo = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", alPulsar);
      document.body.style.overflow = previo;
    };
  }, [onCerrar]);

  return (
    <div className="no-imprimir fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-[var(--velo)]" aria-hidden onClick={onCerrar} />
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby={idTitulo}
        className={clases(
          // `whitespace-normal text-left`: el diálogo puede abrirse desde una celda
          // de tabla, y heredaría su `nowrap` y su alineación a la derecha.
          "material-cristal relative flex max-h-[90vh] w-full flex-col overflow-hidden rounded-hoja",
          "whitespace-normal text-left shadow-expediente",
          ancho,
        )}
      >
        <header className="flex items-start justify-between gap-3 border-b border-linea px-6 pt-5 pb-4">
          <div className="min-w-0">
            {rotulo && <Rotulo className="block">{rotulo}</Rotulo>}
            <h2 id={idTitulo} className="t-h2 mt-1.5 text-tinta">
              {titulo}
            </h2>
          </div>
          <button
            type="button"
            onClick={onCerrar}
            aria-label="Cerrar"
            className="grid h-9 w-9 shrink-0 place-items-center rounded-full border border-linea text-grafito transition-colors hover:text-tinta"
          >
            <X size={16} strokeWidth={1.5} aria-hidden />
          </button>
        </header>
        <div className="barra-fina flex-1 overflow-y-auto bg-hoja/60 p-6">{children}</div>
        {pie && <footer className="flex flex-wrap justify-end gap-2 border-t border-linea px-6 py-4">{pie}</footer>}
      </div>
    </div>
  );
}

/* ── tabla (registro Taller): encabezado meta, sin cebra ───────────────── */
export function Tabla({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <div className={clases("barra-fina overflow-x-auto", className)}>
      <table className="t-tabla w-full min-w-full border-separate border-spacing-0">{children}</table>
    </div>
  );
}

export function Th({
  children,
  derecha,
  className,
}: {
  children?: ReactNode;
  derecha?: boolean;
  className?: string;
}) {
  return (
    <th
      scope="col"
      className={clases(
        "t-meta border-b border-linea bg-hoja px-4 py-3 whitespace-nowrap text-gris",
        derecha ? "text-right" : "text-left",
        className,
      )}
    >
      {children}
    </th>
  );
}

export function Td({
  children,
  derecha,
  className,
}: {
  children?: ReactNode;
  derecha?: boolean;
  className?: string;
}) {
  return (
    <td
      className={clases(
        "border-b border-linea px-4 py-3 align-top text-grafito",
        derecha ? "cifras text-right" : "text-left",
        className,
      )}
    >
      {children}
    </td>
  );
}
