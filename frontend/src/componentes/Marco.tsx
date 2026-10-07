import { LayoutGrid, PenLine, Plus, Search, Settings2, Users } from "lucide-react";
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useId,
  useLayoutEffect,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { Link, NavLink, useLocation } from "react-router-dom";
import { sistema } from "../api";
import { clases } from "../formato";
import type { Salud } from "../tipos";
import { BotonAcento, Flip, MetaEncabezado, sinMovimiento, DURACION } from "../ui";
import { Buscador, useAtajoBuscador } from "./Buscador";
import { CARGO, Logotipo, MARCA, Monograma, TARJETA_PROFESIONAL } from "./Marca";

/**
 * Estructura de la aplicación (spec 6.1).
 *
 * Escritorio (≥ 900 px): barra lateral de 248 px sobre el papel, con borde
 * derecho --linea; navegación con índices (Tablero⁰¹ … Parámetros⁰⁴) y una
 * píldora de tinta que se desliza con Flip hasta la sección activa. Abajo,
 * el estado de sincronización en lenguaje humano.
 *
 * Barra superior: buscador ⌘K de cristal, «Nuevo periodo» (BotonAcento) y
 * avatar con iniciales. Sin repetir el nombre.
 *
 * Móvil (< 900 px): barra inferior de cuatro íconos con etiqueta.
 */

const SECCIONES = [
  { ruta: "/", texto: "Tablero", indice: "01", icono: LayoutGrid, exacto: true },
  { ruta: "/clientes", texto: "Clientes", indice: "02", icono: Users },
  { ruta: "/trabajo", texto: "Trabajar", indice: "03", icono: PenLine },
  { ruta: "/parametros", texto: "Parámetros", indice: "04", icono: Settings2 },
] as const;

function seccionDe(ruta: string): { indice: string; nombre: string } {
  if (ruta === "/") return { indice: "01", nombre: "Tablero" };
  if (ruta === "/clientes") return { indice: "02", nombre: "Clientes" };
  if (ruta === "/clientes/nuevo") return { indice: "02", nombre: "Clientes › Nuevo" };
  if (ruta.endsWith("/editar")) return { indice: "02", nombre: "Clientes › Editar ficha" };
  if (ruta.startsWith("/clientes/")) return { indice: "02", nombre: "Clientes › Ficha" };
  if (ruta.startsWith("/trabajo")) return { indice: "03", nombre: "Trabajar" };
  if (ruta.startsWith("/parametros")) return { indice: "04", nombre: "Parámetros" };
  if (ruta.startsWith("/diseno")) return { indice: "00", nombre: "Catálogo" };
  return { indice: "—", nombre: "Página no encontrada" };
}

const hoyLargo = () =>
  new Intl.DateTimeFormat("es-CO", { day: "numeric", month: "short", year: "numeric" })
    .format(new Date())
    .replace(/\./g, "");

/* ── MetaEncabezado por página ─────────────────────────────────────────────
   La cuarta columna la decide cada pantalla (p. ej. «Corte 31 ene 2025» en el
   Tablero). Si no dice nada, se muestra la fecha de hoy. */
const ContextoMeta = createContext<(texto: string | null) => void>(() => {});

/** Desde una página: fija la cuarta columna del meta-encabezado. */
export function useMetaPagina(texto: string | null | undefined) {
  const fijar = useContext(ContextoMeta);
  useEffect(() => {
    fijar(texto ?? null);
    return () => fijar(null);
  }, [texto, fijar]);
}

export function Marco({ children }: { children: ReactNode }) {
  const [buscadorAbierto, setBuscadorAbierto] = useState(false);
  const [salud, setSalud] = useState<Salud | null>(null);
  const [comprobado, setComprobado] = useState<number | null>(null);
  const [metaPagina, setMetaPagina] = useState<string | null>(null);
  const ubicacion = useLocation();
  const seccion = seccionDe(ubicacion.pathname);

  const abrirBuscador = useCallback(() => setBuscadorAbierto(true), []);
  useAtajoBuscador(abrirBuscador);

  // Estado de la base: se comprueba al abrir y cada minuto.
  useEffect(() => {
    let vivo = true;
    const comprobar = () =>
      sistema
        .salud()
        .then((s) => {
          if (!vivo) return;
          setSalud(s);
          setComprobado(Date.now());
        })
        .catch(() => vivo && setSalud(null));
    comprobar();
    const t = setInterval(comprobar, 60_000);
    return () => {
      vivo = false;
      clearInterval(t);
    };
  }, []);

  const sinBase = salud && !salud.almacenamiento.conectado;

  return (
    <ContextoMeta.Provider value={setMetaPagina}>
      <div className="min-h-screen escritorio:pl-[248px]">
        <a
          href="#contenido"
          className="sr-only z-[80] rounded-full bg-tinta px-5 py-3 text-sobre-tinta focus:not-sr-only focus:fixed focus:top-3 focus:left-3"
        >
          Ir al contenido
        </a>
        <div className="grano" aria-hidden />

        {/* ── barra lateral (escritorio) ─────────────────────────────── */}
        <aside className="no-imprimir fixed inset-y-0 left-0 z-40 hidden w-[248px] flex-col border-r border-linea escritorio:flex">
          <Link to="/" aria-label={`${MARCA}, ir al tablero`} className="block px-6 pt-7 pb-8">
            <Logotipo />
          </Link>

          <NavegacionLateral />

          <div className="mt-auto px-6 pb-6">
            <EstadoSincronizacion salud={salud} comprobado={comprobado} />
          </div>
        </aside>

        {/* ── columna de contenido ───────────────────────────────────── */}
        <div className="relative flex min-h-screen min-w-0 flex-col">
          <Rejilla />

          <div className="contenedor no-imprimir sticky top-0 z-30 pt-3 pb-3 escritorio:pt-5">
            <header className="flex items-center gap-3">
              <Link to="/" aria-label={`${MARCA}, ir al tablero`} className="escritorio:hidden">
                <Monograma tamano={36} />
              </Link>

              <button
                type="button"
                onClick={abrirBuscador}
                aria-label="Buscar clientes y acciones"
                className="material-cristal flex h-11 min-w-0 flex-1 items-center gap-3 rounded-full px-4 text-left text-gris transition-colors hover:text-tinta escritorio:max-w-[420px]"
              >
                <Search size={18} strokeWidth={1.5} aria-hidden className="shrink-0" />
                <span className="t-body recortar flex-1">Buscar cliente, NIT o acción</span>
                <kbd className="codigo hidden rounded-chip border border-linea px-1.5 py-0.5 text-[11px] text-gris sm:inline">
                  Ctrl K
                </kbd>
              </button>

              <div className="ml-auto flex shrink-0 items-center gap-3">
                {/* En Trabajar sobra: ya está ahí, y sería un segundo azul en la vista. */}
                <span className={ubicacion.pathname.startsWith("/trabajo") ? "hidden" : "hidden sm:contents"}>
                  <BotonAcento a="/trabajo" icono={<Plus size={18} strokeWidth={1.5} aria-hidden />}>
                    Nuevo periodo
                  </BotonAcento>
                </span>
                <span
                  title={`${MARCA} · ${CARGO} · ${TARJETA_PROFESIONAL}`}
                  className="grid h-11 w-11 place-items-center rounded-full border border-linea bg-hoja text-[13px] font-semibold tracking-[-0.02em] text-tinta"
                >
                  <span aria-hidden>CC</span>
                  <span className="sr-only">{MARCA}</span>
                </span>
              </div>
            </header>
          </div>

          <div className="contenedor relative z-10 pt-3 escritorio:pt-6">
            <MetaEncabezado
              columnas={[
                `${MARCA} — ${CARGO}`,
                TARJETA_PROFESIONAL,
                `Índice ${seccion.indice} — ${seccion.nombre}`,
                metaPagina ?? hoyLargo(),
              ]}
            />
          </div>

          {sinBase && (
            <div className="contenedor relative z-10 mt-4">
              <div role="status" className="rounded-control border border-ambar/30 bg-ambar-suave p-4 text-sm text-ambar">
                <strong className="font-semibold">Sin conexión con la nube.</strong>{" "}
                Lo que haga se guarda en este equipo. El detalle técnico está en Parámetros › Sistema.
              </div>
            </div>
          )}

          <main id="contenido" tabIndex={-1} className="contener relative z-10 flex-1 pt-8 pb-28 outline-none escritorio:pb-12">
            <div className="contenedor contener">
              {children}
            </div>
          </main>

          <footer className="contenedor no-imprimir relative z-10 hidden text-gris escritorio:block">
            <div className="t-small flex flex-wrap items-center justify-between gap-3 border-t border-linea py-4">
              <span>PUC Decreto 2650/1993 · NIIF Decreto 2420/2015 · Cálculo con precisión decimal exacta</span>
              <span className="codigo text-[12px]" title="Versión de la aplicación">
                v{__VERSION__} · build {__BUILD__} · {__FECHA_BUILD__}
              </span>
            </div>
          </footer>
        </div>

        <NavegacionMovil />

        <Buscador abierto={buscadorAbierto} onCerrar={() => setBuscadorAbierto(false)} />
      </div>
    </ContextoMeta.Provider>
  );
}

/** ¿Qué sección está activa? La ficha y el editor pertenecen a Clientes. */
function useSeccionActiva(): string {
  const { pathname } = useLocation();
  const s = [...SECCIONES].reverse().find((x) => (x.ruta === "/" ? pathname === "/" : pathname.startsWith(x.ruta)));
  return s?.ruta ?? "";
}

/**
 * La píldora activa vive dentro del enlace activo; al cambiar de sección,
 * React la monta en otro enlace y Flip la anima desde donde estaba
 * (emparejadas por `data-flip-id`). 0,35 s, power3.inOut (spec 8).
 */
function usePildoraDeslizante(activa: string) {
  const id = "pildora-" + useId();
  const contenedor = useRef<HTMLElement>(null);
  const estado = useRef<Flip.FlipState | null>(null);
  const previa = useRef(activa);

  // Se captura ANTES de que cambie la ruta, en el clic.
  const capturar = () => {
    const el = contenedor.current?.querySelector<HTMLElement>(`[data-flip-id="${id}"]`);
    if (el && !sinMovimiento()) estado.current = Flip.getState(el);
  };

  useLayoutEffect(() => {
    if (previa.current === activa) return;
    previa.current = activa;
    const s = estado.current;
    estado.current = null;
    const el = contenedor.current?.querySelector<HTMLElement>(`[data-flip-id="${id}"]`);
    if (!s || !el) return;
    const anim = Flip.from(s, { targets: el, duration: DURACION.interruptor, ease: "power3.inOut" });
    return () => {
      anim.kill();
    };
  }, [activa, id]);

  return { id, contenedor, capturar };
}

function NavegacionLateral() {
  const activa = useSeccionActiva();
  const { id, contenedor, capturar } = usePildoraDeslizante(activa);
  return (
    <nav ref={contenedor} aria-label="Secciones" className="flex flex-col gap-1 px-4">
      {SECCIONES.map((s) => {
        const es = s.ruta === activa;
        return (
          <Link
            key={s.ruta}
            to={s.ruta}
            onClick={capturar}
            aria-current={es ? "page" : undefined}
            className={clases(
              "relative flex h-11 items-center rounded-full px-4 text-[15px] font-medium transition-colors duration-200",
              es ? "text-sobre-tinta" : "text-grafito hover:bg-hoja-2 hover:text-tinta",
            )}
          >
            {es && <span data-flip-id={id} aria-hidden className="absolute inset-0 rounded-full bg-tinta" />}
            <span className="relative">
              {s.texto}
              <span aria-hidden className={clases("codigo relative -top-[0.55em] ml-[0.25em] text-[0.62em]", es ? "text-sobre-tinta-2" : "text-gris")}>
                {s.indice}
              </span>
            </span>
          </Link>
        );
      })}
    </nav>
  );
}

function NavegacionMovil() {
  const activa = useSeccionActiva();
  const { id, contenedor, capturar } = usePildoraDeslizante(activa);
  return (
    <nav
      ref={contenedor}
      aria-label="Secciones"
      className="material-cristal no-imprimir fixed inset-x-3 bottom-3 z-40 grid grid-cols-4 gap-1 rounded-full p-1.5 escritorio:hidden"
    >
      {SECCIONES.map((s) => {
        const es = s.ruta === activa;
        return (
          <Link
            key={s.ruta}
            to={s.ruta}
            onClick={capturar}
            aria-current={es ? "page" : undefined}
            className={clases(
              "relative flex flex-col items-center gap-0.5 rounded-full py-2 transition-colors",
              es ? "text-sobre-tinta" : "text-grafito",
            )}
          >
            {es && <span data-flip-id={id} aria-hidden className="absolute inset-0 rounded-full bg-tinta" />}
            <s.icono size={20} strokeWidth={1.5} aria-hidden className="relative" />
            <span className="relative text-[11px] font-medium leading-4">{s.texto}</span>
          </Link>
        );
      })}
    </nav>
  );
}

/** «Sincronizado · hace 2 min» — sin nombres técnicos ni ID del proyecto. */
function EstadoSincronizacion({ salud, comprobado }: { salud: Salud | null; comprobado: number | null }) {
  const [, refrescar] = useState(0);
  useEffect(() => {
    const t = setInterval(() => refrescar((n) => n + 1), 30_000);
    return () => clearInterval(t);
  }, []);

  let punto = "bg-gris";
  let titulo = "Comprobando conexión";
  let detalle = "Un momento";
  if (salud) {
    const a = salud.almacenamiento;
    const minutos = comprobado ? Math.floor((Date.now() - comprobado) / 60_000) : 0;
    const hace = minutos < 1 ? "hace un momento" : minutos === 1 ? "hace 1 min" : `hace ${minutos} min`;
    if (!a.conectado) {
      punto = "bg-ambar";
      titulo = "Sin conexión";
      detalle = "Se guarda en este equipo";
    } else if (a.es_postgres) {
      punto = "bg-azul";
      titulo = "Sincronizado";
      detalle = hace;
    } else {
      punto = "bg-tinta";
      titulo = "Guardado en este equipo";
      detalle = hace;
    }
  }
  return (
    <div role="status" className="flex items-start gap-2.5 border-t border-linea pt-4">
      <span aria-hidden className={clases("mt-[7px] h-2 w-2 shrink-0 rounded-full", punto)} />
      <p className="t-small min-w-0 text-grafito">
        <span className="font-medium text-tinta">{titulo}</span> · {detalle}
      </p>
    </div>
  );
}

/** Rejilla visible del lienzo (ref-08): 12 columnas alineadas al `.contenedor`. */
function Rejilla() {
  return (
    <div className="rejilla no-imprimir" aria-hidden>
      <div>
        {Array.from({ length: 12 }, (_, i) => <span key={i} />)}
      </div>
    </div>
  );
}
