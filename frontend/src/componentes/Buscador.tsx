import { CornerDownLeft, Search } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { clientes as apiClientes } from "../api";
import { clases } from "../formato";
import type { ResultadoBusqueda } from "../tipos";
import { Rotulo } from "./ui";

/** Acciones fijas que siempre se pueden invocar desde el buscador. */
const ACCIONES: { id: string; titulo: string; subtitulo: string; ruta: string; palabras: string }[] = [
  { id: "a-nuevo", titulo: "Nuevo cliente", subtitulo: "Agregar una ficha al directorio", ruta: "/clientes/nuevo", palabras: "crear alta agregar empresa" },
  { id: "a-trabajo", titulo: "Trabajar un periodo", subtitulo: "Subir archivos y calcular", ruta: "/trabajo", palabras: "calcular importar excel balance estados" },
  { id: "a-clientes", titulo: "Ver todos los clientes", subtitulo: "Directorio completo", ruta: "/clientes", palabras: "directorio listado cartera" },
  { id: "a-tablero", titulo: "Tablero", subtitulo: "Pendientes y resumen del día", ruta: "/", palabras: "inicio resumen pendientes" },
  { id: "a-parametros", titulo: "Parámetros legales", subtitulo: "SMMLV, auxilio y aportes por año", ruta: "/parametros", palabras: "smmlv salario auxilio nomina configuracion ajustes" },
];

function sinTildes(t: string): string {
  return t.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
}

export function Buscador({ abierto, onCerrar }: { abierto: boolean; onCerrar: () => void }) {
  const navegar = useNavigate();
  const [q, setQ] = useState("");
  const [encontrados, setEncontrados] = useState<ResultadoBusqueda[]>([]);
  const [buscando, setBuscando] = useState(false);
  const [activo, setActivo] = useState(0);
  const campo = useRef<HTMLInputElement>(null);

  const acciones = useMemo(() => {
    const t = sinTildes(q.trim());
    if (!t) return ACCIONES;
    return ACCIONES.filter((a) => sinTildes(a.titulo + " " + a.palabras).includes(t));
  }, [q]);

  const lista = useMemo(
    () => [
      ...encontrados.map((c) => ({ clave: `c-${c.id}`, titulo: c.titulo, subtitulo: c.subtitulo, ruta: `/clientes/${c.id}`, grupo: "Clientes" })),
      ...acciones.map((a) => ({ clave: a.id, titulo: a.titulo, subtitulo: a.subtitulo, ruta: a.ruta, grupo: "Acciones" })),
    ],
    [encontrados, acciones],
  );

  useEffect(() => {
    if (abierto) {
      setActivo(0);
      const t = setTimeout(() => campo.current?.focus(), 30);
      return () => clearTimeout(t);
    }
    setQ("");
    setEncontrados([]);
  }, [abierto]);

  // Búsqueda con freno: no se consulta en cada tecla.
  useEffect(() => {
    if (!abierto) return;
    const texto = q.trim();
    if (texto.length < 2) {
      setEncontrados([]);
      setBuscando(false);
      return;
    }
    setBuscando(true);
    let cancelado = false;
    const t = setTimeout(async () => {
      try {
        const r = await apiClientes.buscar(texto, 7);
        if (!cancelado) setEncontrados(r.resultados);
      } catch {
        if (!cancelado) setEncontrados([]);
      } finally {
        if (!cancelado) setBuscando(false);
      }
    }, 180);
    return () => {
      cancelado = true;
      clearTimeout(t);
    };
  }, [q, abierto]);

  useEffect(() => setActivo(0), [lista.length]);

  if (!abierto) return null;

  const ir = (ruta: string) => {
    onCerrar();
    navegar(ruta);
  };

  const alTeclear = (e: React.KeyboardEvent) => {
    if (e.key === "Escape") return onCerrar();
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setActivo((i) => (i + 1) % Math.max(lista.length, 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActivo((i) => (i - 1 + lista.length) % Math.max(lista.length, 1));
    } else if (e.key === "Enter" && lista[activo]) {
      e.preventDefault();
      ir(lista[activo].ruta);
    }
  };

  let grupoPrevio = "";

  return (
    <div className="no-imprimir fixed inset-0 z-[60] flex items-start justify-center px-4 pt-[8vh]">
      <div className="absolute inset-0 bg-[var(--velo)]" aria-hidden onClick={onCerrar} />
      <div
        role="dialog"
        aria-modal="true"
        aria-label="Buscador"
        className="material-cristal relative w-full max-w-xl overflow-hidden rounded-hoja shadow-expediente"
      >
        <div className="flex items-center gap-3 border-b border-linea px-4">
          <Search size={20} strokeWidth={1.5} aria-hidden className="shrink-0 text-gris" />
          <input
            ref={campo}
            value={q}
            onChange={(e) => setQ(e.target.value)}
            onKeyDown={alTeclear}
            placeholder="Buscar cliente por nombre o NIT, o escribir una acción…"
            className="w-full bg-transparent py-4 text-[15px] placeholder:text-gris focus:outline-none focus-visible:shadow-none"
            aria-label="Buscar"
          />
          <kbd className="rotulo hidden rounded border border-linea px-1.5 py-0.5 sm:block">esc</kbd>
        </div>

        <div className="barra-fina max-h-[55vh] overflow-y-auto py-2">
          {buscando && q.trim().length >= 2 && (
            <p className="rotulo px-4 py-3">Buscando…</p>
          )}
          {!lista.length && !buscando && (
            <p className="px-4 py-6 text-center text-sm text-grafito">
              Nada coincide con «{q}».
            </p>
          )}
          {lista.map((item, i) => {
            const encabezado = item.grupo !== grupoPrevio ? item.grupo : "";
            grupoPrevio = item.grupo;
            return (
              <div key={item.clave}>
                {encabezado && <Rotulo className="mt-2 block px-4 py-1.5">{encabezado}</Rotulo>}
                <button
                  onMouseEnter={() => setActivo(i)}
                  onClick={() => ir(item.ruta)}
                  className={clases(
                    "flex w-full items-center justify-between gap-3 px-4 py-2.5 text-left transition",
                    i === activo ? "bg-tinta" : "hover:bg-hoja/70",
                  )}
                >
                  <span className="min-w-0">
                    <span className={clases("block truncate text-sm font-medium", i === activo ? "text-sobre-tinta" : "text-tinta")}>{item.titulo}</span>
                    <span className={clases("block truncate text-xs", i === activo ? "text-sobre-tinta-2" : "text-grafito")}>{item.subtitulo}</span>
                  </span>
                  {i === activo && <CornerDownLeft size={16} strokeWidth={1.5} aria-hidden className="shrink-0 text-sobre-tinta-2" />}
                </button>
              </div>
            );
          })}
        </div>

        <div className="flex items-center justify-between border-t border-linea px-4 py-2.5">
          <Rotulo>↑↓ moverse · ↵ abrir</Rotulo>
          <Rotulo>Ctrl + K</Rotulo>
        </div>
      </div>
    </div>
  );
}

/** Engancha Ctrl/⌘ + K en toda la aplicación. */
export function useAtajoBuscador(abrir: () => void) {
  useEffect(() => {
    const alPulsar = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        abrir();
      }
    };
    document.addEventListener("keydown", alPulsar);
    return () => document.removeEventListener("keydown", alPulsar);
  }, [abrir]);
}
