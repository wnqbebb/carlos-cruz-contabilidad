import { LayoutGrid, LogOut, Monitor, Moon, PenLine, Plus, Search, Settings2, Sun, Users } from "lucide-react";
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useId,
  useLayoutEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { createPortal } from "react-dom";
import { Link, NavLink, useLocation } from "react-router-dom";
import { sesionApi, sistema } from "../api";
import { clases } from "../formato";
import type { EstadoSistema } from "../tipos";
import { DialogoSistema } from "./Sistema";
import { colorCliente } from "../colorCliente";
import { useTema, type PreferenciaTema } from "../tema";
import { BotonAcento, Flip, Interruptor, MetaEncabezado, sinMovimiento, DURACION } from "../ui";
import { Buscador, useAtajoBuscador } from "./Buscador";
import { Logotipo, MARCA, Monograma, useFirmaContador } from "./Marca";

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
] as const;

function seccionDe(ruta: string): { indice: string; nombre: string } {
  if (ruta === "/") return { indice: "01", nombre: "Tablero" };
  if (ruta === "/clientes") return { indice: "02", nombre: "Clientes" };
  if (ruta === "/clientes/nuevo") return { indice: "02", nombre: "Clientes › Nuevo" };
  if (ruta.endsWith("/editar")) return { indice: "02", nombre: "Clientes › Editar ficha" };
  if (ruta.startsWith("/clientes/")) return { indice: "02", nombre: "Clientes › Ficha" };
  if (ruta.startsWith("/trabajo")) return { indice: "03", nombre: "Trabajar" };
  if (ruta.startsWith("/diseno")) return { indice: "00", nombre: "Catálogo" };
  return { indice: "—", nombre: "Página no encontrada" };
}

/** Identidad de la página (8.2): la clave que leen los tokens en `data-seccion`. */
function claveSeccion(ruta: string): "tablero" | "clientes" | "ficha" | "trabajar" {
  if (ruta.startsWith("/trabajo")) return "trabajar";
  if (/^\/clientes\/[0-9a-f-]{8,}$/i.test(ruta)) return "ficha";
  if (ruta.startsWith("/clientes")) return "clientes";
  return "tablero";
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

/* ── Cabecera de cada página (8.2) ──────────────────────────────────────────
   La franja de cabecera es del marco (tono de la sección, rejilla, número de
   índice gigante); el contenido lo pone cada página con <Cabecera>, que lo
   lleva a la franja por un portal. Así el título queda sobre el tono. */
const ContextoCabecera = createContext<{
  hueco: HTMLElement | null;
  fijarCliente: (nit: string | null) => void;
}>({ hueco: null, fijarCliente: () => {} });

/** El título y lo que acompaña al título de una página: va en la franja de cabecera. */
export function Cabecera({ children }: { children: ReactNode }) {
  const { hueco } = useContext(ContextoCabecera);
  return hueco ? createPortal(children, hueco) : null;
}

/** Desde la ficha: pinta la cabecera, la píldora y el foco con el color del cliente (8.3). */
export function useColorCliente(nit: string | null | undefined) {
  const { fijarCliente } = useContext(ContextoCabecera);
  useEffect(() => {
    fijarCliente(nit || null);
    return () => fijarCliente(null);
  }, [nit, fijarCliente]);
}

export function Marco({ children }: { children: ReactNode }) {
  const { cargo, tp } = useFirmaContador();
  const [hueco, setHueco] = useState<HTMLElement | null>(null);
  const [nitCliente, setNitCliente] = useState<string | null>(null);
  const valorCabecera = useMemo(() => ({ hueco, fijarCliente: setNitCliente }), [hueco]);
  const [buscadorAbierto, setBuscadorAbierto] = useState(false);
  const [salud, setSalud] = useState<EstadoSistema | null>(null);
  const [comprobado, setComprobado] = useState<number | null>(null);
  const [metaPagina, setMetaPagina] = useState<string | null>(null);
  const ubicacion = useLocation();
  const seccion = seccionDe(ubicacion.pathname);
  const clave = claveSeccion(ubicacion.pathname);
  const varsCliente = useMemo(
    () => (nitCliente && clave === "ficha" ? colorCliente(nitCliente).vars : null),
    [nitCliente, clave],
  );

  const abrirBuscador = useCallback(() => setBuscadorAbierto(true), []);
  useAtajoBuscador(abrirBuscador);

  // Estado de la base: se comprueba al abrir y cada minuto.
  useEffect(() => {
    let vivo = true;
    const comprobar = () =>
      sistema
        .estado()
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

  const sinBase = salud && !salud.conectado;

  return (
    <ContextoMeta.Provider value={setMetaPagina}>
     <ContextoCabecera.Provider value={valorCabecera}>
      <div
        data-seccion={clave}
        data-cliente-color={varsCliente ? "" : undefined}
        style={(varsCliente ?? undefined) as React.CSSProperties | undefined}
        className="min-h-screen escritorio:pl-[248px]"
      >
        <a
          href="#contenido"
          className="sr-only z-[80] rounded-full bg-tinta px-5 py-3 text-sobre-tinta focus:not-sr-only focus:fixed focus:top-3 focus:left-3"
        >
          Ir al contenido
        </a>
        <div className="grano" aria-hidden />

        {/* ── barra lateral (escritorio) ─────────────────────────────── */}
        <aside className="no-imprimir fixed inset-y-0 left-0 z-40 hidden w-[248px] flex-col border-r border-linea bg-barra escritorio:flex">
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
                <span className="t-body recortar hidden flex-1 sm:inline">Buscar cliente, NIT o acción</span>
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
                <SelectorTema />
                <MenuCuenta titulo={[MARCA, cargo, tp].filter(Boolean).join(" · ")} />
              </div>
            </header>
          </div>

          <div
            data-banda={clave === "trabajar" ? "taller" : undefined}
            data-cliente={varsCliente ? "" : undefined}
            className="franja-cabecera -mt-[68px] overflow-hidden pt-[68px] escritorio:-mt-[80px] escritorio:pt-[80px]"
          >
            <Rejilla />
            <span aria-hidden className="indice-gigante">{seccion.indice}</span>
            <div className="contenedor relative z-10 pt-3 escritorio:pt-6">
              <MetaEncabezado
                columnas={[
                  cargo ? `${MARCA} — ${cargo}` : MARCA,
                  tp,
                  `Índice ${seccion.indice} — ${seccion.nombre}`,
                  metaPagina ?? hoyLargo(),
                ]}
              />
            </div>
            <div ref={setHueco} className="contenedor contener relative z-10 pt-8 pb-10 empty:pb-6 empty:pt-0" />
          </div>

          {sinBase && (
            <div className="contenedor relative z-10 mt-4">
              <div role="status" className="rounded-control border border-ambar/30 bg-ambar-suave p-4 text-sm text-ambar">
                <strong className="font-semibold">Sin conexión con la nube.</strong>{" "}
                Lo que haga se guarda en este equipo y se sincroniza cuando vuelva la conexión.
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
     </ContextoCabecera.Provider>
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
              es ? "text-sobre-acento" : "text-grafito hover:bg-hoja-2 hover:text-tinta",
            )}
          >
            {es && <span data-flip-id={id} aria-hidden className="absolute inset-0 rounded-full bg-acento transition-colors duration-[400ms]" />}
            <span className="relative">
              {s.texto}
              <span aria-hidden className={clases("codigo relative -top-[0.55em] ml-[0.25em] text-[0.62em]", es ? "text-sobre-acento" : "text-gris")}>
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
              es ? "text-sobre-acento" : "text-grafito",
            )}
          >
            {es && <span data-flip-id={id} aria-hidden className="absolute inset-0 rounded-full bg-acento transition-colors duration-[400ms]" />}
            <s.icono size={20} strokeWidth={1.5} aria-hidden className="relative" />
            <span className="relative text-[11px] font-medium leading-4">{s.texto}</span>
          </Link>
        );
      })}
    </nav>
  );
}

/** «Sincronizado · hace 2 min» — sin nombres técnicos ni ID del proyecto. */
function EstadoSincronizacion({ salud, comprobado }: { salud: EstadoSistema | null; comprobado: number | null }) {
  const [, refrescar] = useState(0);
  useEffect(() => {
    const t = setInterval(() => refrescar((n) => n + 1), 30_000);
    return () => clearInterval(t);
  }, []);

  let punto = "bg-gris";
  let titulo = "Comprobando conexión";
  let detalle = "Un momento";
  if (salud) {
    const a = { conectado: salud.conectado, es_postgres: salud.en_la_nube };
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

/* ── Claro⁰¹ | Oscuro⁰² | Sistema⁰³ (8.4) ──────────────────────────────── */
const OPCIONES_TEMA: { valor: PreferenciaTema; texto: string; icono: typeof Sun }[] = [
  { valor: "claro", texto: "Claro", icono: Sun },
  { valor: "oscuro", texto: "Oscuro", icono: Moon },
  { valor: "sistema", texto: "Sistema", icono: Monitor },
];

function SelectorTema() {
  const [tema, setTema] = useTema();
  return (
    <>
      <span className="hidden sm:contents">
        <Interruptor
          etiqueta="Modo de color"
          tamano="sm"
          valor={tema}
          onCambio={setTema}
          opciones={OPCIONES_TEMA.map((o) => ({ valor: o.valor, texto: o.texto }))}
        />
      </span>
      {/* En el teléfono no cabe el texto: solo el ícono, con su nombre accesible. */}
      <span className="contents sm:hidden">
      <Interruptor
        etiqueta="Modo de color"
        tamano="sm"
        valor={tema}
        onCambio={setTema}
        opciones={OPCIONES_TEMA.map((o, i) => ({
          valor: o.valor,
          indice: String(i + 1).padStart(2, "0"),
          texto: (
            <>
              <o.icono size={14} strokeWidth={1.5} aria-hidden className="inline align-[-2px]" />
              <span className="sr-only">{o.texto}</span>
            </>
          ),
        }))}
      />
      </span>
    </>
  );
}


/* ── cuenta: quién está dentro y «Cerrar sesión» (A2) ─────────────────── */
function MenuCuenta({ titulo }: { titulo: string }) {
  const [abierto, setAbierto] = useState(false);
  const [sistemaAbierto, setSistemaAbierto] = useState(false);
  const [usuario, setUsuario] = useState("");
  const raiz = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!abierto) return;
    sesionApi.estado().then((e) => setUsuario(e.usuario ?? "")).catch(() => undefined);
    const fuera = (e: MouseEvent) => {
      if (!raiz.current?.contains(e.target as Node)) setAbierto(false);
    };
    const tecla = (e: KeyboardEvent) => e.key === "Escape" && setAbierto(false);
    document.addEventListener("mousedown", fuera);
    document.addEventListener("keydown", tecla);
    return () => {
      document.removeEventListener("mousedown", fuera);
      document.removeEventListener("keydown", tecla);
    };
  }, [abierto]);

  const salir = async () => {
    try {
      await sesionApi.salir();
    } finally {
      window.location.assign("/");
    }
  };

  return (
    <div ref={raiz} className="relative">
      <button
        type="button"
        title={titulo}
        aria-label="Cuenta y cerrar sesión"
        aria-expanded={abierto}
        aria-haspopup="menu"
        onClick={() => setAbierto((v) => !v)}
        className="grid h-11 w-11 place-items-center rounded-full border border-linea bg-hoja text-[13px] font-semibold tracking-[-0.02em] text-tinta transition-colors hover:border-tinta/30"
      >
        <span aria-hidden>CC</span>
      </button>
      {abierto && (
        <div
          role="menu"
          className="material-cristal absolute right-0 top-[calc(100%+8px)] z-50 w-60 rounded-hoja border border-linea p-2 shadow-expediente"
        >
          <p className="t-meta px-3 pb-2 pt-1 text-gris">
            Sesión de <span className="normal-case text-tinta">{usuario || "…"}</span>
          </p>
          <button
            type="button"
            role="menuitem"
            onClick={() => {
              setAbierto(false);
              setSistemaAbierto(true);
            }}
            className="t-body flex w-full items-center gap-2 rounded-[10px] px-3 py-2 text-left text-tinta transition-colors hover:bg-hoja-2"
          >
            <Settings2 size={16} strokeWidth={1.5} aria-hidden /> Sistema
          </button>
          <button
            type="button"
            role="menuitem"
            onClick={salir}
            className="t-body flex w-full items-center gap-2 rounded-[10px] px-3 py-2 text-left text-tinta transition-colors hover:bg-hoja-2"
          >
            <LogOut size={16} strokeWidth={1.5} aria-hidden /> Cerrar sesión
          </button>
        </div>
      )}
      {sistemaAbierto && <DialogoSistema onCerrar={() => setSistemaAbierto(false)} />}
    </div>
  );
}
