import { Check, Search } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { useLocation, useNavigate, useSearchParams } from "react-router-dom";
import { analisis, clientes as apiClientes, trabajo as apiTrabajo, ErrorApi } from "../api";
import { useMetaPagina } from "../componentes/Marco";
import { Aviso, Cargando } from "../componentes/ui";
import { clases, periodoCorto } from "../formato";
import type { Cliente, Importacion, Peticion, Resultado } from "../tipos";
import {
  BotonFantasma,
  BotonPrimario,
  CarpetaVacia,
  EnlaceSubrayado,
  EsferaCliente,
  EsqueletoExpedientes,
  Expediente,
  TituloPagina,
} from "../ui";
import { Inicio } from "./Inicio";
import { Resultados, type Pestaña } from "./Resultados";
import { VistaPrevia } from "./VistaPrevia";

/**
 * Trabajar un periodo (spec 6.5).
 *
 * Paso a paso de 7 pasos, siempre visible (pegajoso):
 *   01 Cliente · 02 Subir · 03 Mapeo · 04 Balance de prueba · 05 Ajustes ·
 *   06 Definitivo · 07 Estados
 *
 * El flujo real sigue siendo el mismo de siempre (subir → revisar → calcular);
 * los pasos 04 a 07 son vistas del resultado calculado. Ninguna llamada al
 * servidor cambió.
 */

type Fase = "subir" | "revisar" | "resultados";

const PASOS = [
  { n: "01", texto: "Cliente" },
  { n: "02", texto: "Subir" },
  { n: "03", texto: "Mapeo" },
  { n: "04", texto: "Balance de prueba" },
  { n: "05", texto: "Ajustes" },
  { n: "06", texto: "Definitivo" },
  { n: "07", texto: "Estados" },
] as const;

/** Qué paso del spec corresponde a cada pestaña del resultado. */
const PASO_DE_PESTAÑA: Record<Pestaña, number> = {
  resumen: 3,
  prueba: 3,
  ajustes: 4,
  trabajo: 5,
  definitivo: 5,
  estados: 6,
  inventario: 6,
  nomina: 6,
  auditoria: 6,
  mayor: 6,
  diario: 6,
  mayorbal: 6,
};
const PESTAÑA_DE_PASO: Record<number, Pestaña> = { 3: "prueba", 4: "ajustes", 5: "definitivo", 6: "estados" };

export function Trabajo() {
  const [parametros, setParametros] = useSearchParams();
  const clienteEnRuta = parametros.get("cliente") ?? "";
  const ubicacion = useLocation();
  const navegar = useNavigate();

  const [cliente, setCliente] = useState<Cliente | null>(null);
  const [cargandoCliente, setCargandoCliente] = useState(!!clienteEnRuta);
  const [fase, setFase] = useState<Fase>("subir");
  const [pestaña, setPestaña] = useState<Pestaña>("resumen");
  const [importacion, setImportacion] = useState<Importacion | null>(null);
  const [peticion, setPeticion] = useState<Peticion | null>(null);
  const [resultado, setResultado] = useState<Resultado | null>(null);
  const [calculando, setCalculando] = useState(false);
  const [error, setError] = useState("");
  // Periodo cerrado que impide guardar: se ofrece reabrir en vez de dejar al
  // contador atascado con un mensaje de error (H01).
  const [cerrado, setCerrado] = useState<{ mensaje: string; periodoId: string; peticion: Peticion } | null>(null);
  const [reabriendo, setReabriendo] = useState(false);

  useMetaPagina(cliente ? cliente.sigla || cliente.razon_social : null);

  /* La puerta única (`componentes/Subir.tsx`) puede mandar aquí un archivo ya
     leído: entonces no hay que volver a subir nada, se entra directo a 03
     Mapeo. El estado se consume una sola vez para que recargar no lo repita. */
  useEffect(() => {
    const traida = (ubicacion.state as { importacion?: Importacion } | null)?.importacion;
    if (!traida) return;
    setImportacion(traida);
    setPeticion(null);
    setResultado(null);
    setFase("revisar");
    navegar(`${ubicacion.pathname}${ubicacion.search}`, { replace: true, state: null });
  }, [ubicacion, navegar]);

  /* Desde una tarea del tablero: «Responder las preguntas del archivo». La
     sesión del servidor guarda lo leído; si ya caducó, se dice y se pide subir. */
  const sesionEnRuta = parametros.get("sesion") ?? "";
  useEffect(() => {
    if (!sesionEnRuta) return;
    apiTrabajo
      .verImportacion(sesionEnRuta)
      .then((imp) => {
        setImportacion(imp);
        setPeticion(null);
        setResultado(null);
        setFase("revisar");
      })
      .catch(() => setError("La subida con preguntas pendientes ya caducó (dura 8 horas). Vuelva a subir el archivo."))
      .finally(() => {
        const sin = new URLSearchParams(parametros);
        sin.delete("sesion");
        setParametros(sin, { replace: true });
      });
    // Solo al entrar con ?sesion=
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sesionEnRuta]);

  useEffect(() => {
    if (!clienteEnRuta) {
      setCliente(null);
      return;
    }
    setCargandoCliente(true);
    apiClientes
      .obtener(clienteEnRuta)
      .then(setCliente)
      .catch(() => setCliente(null))
      .finally(() => setCargandoCliente(false));
  }, [clienteEnRuta]);

  const calcular = useCallback(
    async (p: Peticion) => {
      setCalculando(true);
      setError("");
      try {
        const r = await apiTrabajo.calcular({ ...p, cliente_id: clienteEnRuta || null });
        setPeticion(p);
        setResultado(r);
        setFase("resultados");
        setPestaña("resumen");
        window.scrollTo({ top: 0, behavior: "smooth" });
      } catch (e) {
        const err = e as ErrorApi;
        if (err.codigo === "periodo_cerrado") {
          setCerrado({ mensaje: err.message, periodoId: String(err.datos.periodo_id ?? ""), peticion: p });
        } else {
          setError(err.message);
        }
      } finally {
        setCalculando(false);
      }
    },
    [clienteEnRuta],
  );

  if (cargandoCliente) return <Cargando texto="Abriendo el cliente" />;

  // Paso actual según el spec (0 = 01 Cliente … 6 = 07 Estados).
  const actual = !clienteEnRuta ? 0 : fase === "subir" ? 1 : fase === "revisar" ? 2 : PASO_DE_PESTAÑA[pestaña];
  const disponible = (i: number) =>
    i === 0 || (i === 1 && !!clienteEnRuta) || (i === 2 && !!importacion) || (i >= 3 && !!resultado);

  const irA = (i: number) => {
    // 04–07 son pestañas del resultado: el resumen también cae en 04, así que
    // pulsar «Balance de prueba» desde el resumen debe cambiar de pestaña.
    if (!disponible(i) || (i < 3 && i === actual)) return;
    if (i === 0) setParametros({});
    else if (i === 1) setFase("subir");
    else if (i === 2) setFase("revisar");
    else {
      setFase("resultados");
      setPestaña(PESTAÑA_DE_PASO[i]);
    }
    window.scrollTo({ top: 0 });
  };

  return (
    <div className="space-y-10">
      <div className="flex flex-wrap items-end justify-between gap-6">
        <TituloPagina
          subtitulo={
            cliente ? (
              <span className="flex flex-wrap items-center gap-x-3 gap-y-1">
                <EnlaceSubrayado a={`/clientes/${cliente.id}`}>{cliente.razon_social}</EnlaceSubrayado>
                <span className="codigo text-[13px] text-gris">NIT {cliente.nit_formateado}</span>
              </span>
            ) : (
              "Primero el cliente: todo el trabajo queda en su expediente."
            )
          }
        >
          {resultado
            ? periodoCorto(resultado.empresa.periodo_desde, resultado.empresa.periodo_hasta)
            : "Trabajar"}
        </TituloPagina>
        {clienteEnRuta && (
          <BotonFantasma compacto onClick={() => setParametros({})}>
            Cambiar de cliente
          </BotonFantasma>
        )}
      </div>

      <PasoAPaso actual={actual} disponible={disponible} onIr={irA} />

      {error && (
        <Aviso tono="rojo" titulo="No se pudo calcular" onCerrar={() => setError("")}>
          {error}
        </Aviso>
      )}

      {cerrado && (
        <Aviso tono="ambar" titulo="Ese periodo ya está cerrado">
          <p>{cerrado.mensaje}</p>
          <p className="mt-2 t-small">
            Si reabre, el cierre actual y sus cifras quedan guardados en el historial del periodo:
            puede volver a ellos cuando quiera desde la ficha del cliente.
          </p>
          <div className="mt-4 flex flex-wrap gap-3">
            <BotonPrimario
              compacto
              cargando={reabriendo}
              onClick={async () => {
                setReabriendo(true);
                try {
                  await analisis.reabrirPeriodo(cerrado.periodoId);
                  const p = cerrado.peticion;
                  setCerrado(null);
                  await calcular(p);
                } catch (e) {
                  setError((e as Error).message);
                } finally {
                  setReabriendo(false);
                }
              }}
            >
              Reabrir y recalcular
            </BotonPrimario>
            <BotonFantasma compacto onClick={() => setCerrado(null)}>
              Dejarlo como está
            </BotonFantasma>
          </div>
        </Aviso>
      )}

      {resultado?.guardado === false && resultado.aviso_guardado && (
        <Aviso tono="ambar" titulo="El cálculo está bien, pero no se guardó">
          {resultado.aviso_guardado}
        </Aviso>
      )}

      {!clienteEnRuta && <ElegirCliente onElegir={(id) => setParametros({ cliente: id })} />}

      {clienteEnRuta && fase === "subir" && (
        <Inicio
          clienteId={clienteEnRuta}
          onImportado={(d) => {
            setImportacion(d);
            setPeticion(null);
            setResultado(null);
            setFase("revisar");
          }}
        />
      )}

      {clienteEnRuta && fase === "revisar" && importacion && (
        <VistaPrevia
          key={importacion.sesion_id}
          datos={importacion}
          peticionPrevia={peticion}
          calculando={calculando}
          onCalcular={calcular}
          onVolver={() => setFase("subir")}
        />
      )}

      {clienteEnRuta && fase === "resultados" && resultado && peticion && (
        <Resultados
          key={JSON.stringify(peticion.decisiones) + resultado.resumen.periodo}
          res={resultado}
          peticion={peticion}
          calculando={calculando}
          onRecalcular={calcular}
          onEditar={() => setFase("revisar")}
          pestaña={pestaña}
          onPestaña={setPestaña}
        />
      )}
    </div>
  );
}

/* ── paso a paso pegajoso: actual en tinta, hechos con ✓, futuros en gris ── */
function PasoAPaso({
  actual,
  disponible,
  onIr,
}: {
  actual: number;
  disponible: (i: number) => boolean;
  onIr: (i: number) => void;
}) {
  return (
    <nav
      aria-label="Pasos del trabajo"
      className="no-imprimir sticky top-[68px] z-20 -mx-1 escritorio:top-[80px]"
    >
      <ol className="material-cristal barra-fina flex gap-1 overflow-x-auto rounded-full p-1.5">
        {PASOS.map((p, i) => {
          const hecho = i < actual;
          const es = i === actual;
          const puede = disponible(i);
          return (
            <li key={p.n} className="shrink-0">
              <button
                type="button"
                onClick={() => onIr(i)}
                disabled={!puede}
                aria-current={es ? "step" : undefined}
                className={clases(
                  "flex h-10 items-center gap-2 rounded-full px-4 text-[14px] font-medium whitespace-nowrap transition-colors duration-200",
                  es && "bg-tinta text-sobre-tinta",
                  !es && hecho && "text-tinta hover:bg-hoja",
                  !es && !hecho && (puede ? "text-grafito hover:bg-hoja" : "cursor-not-allowed text-gris"),
                )}
              >
                <span
                  aria-hidden
                  className={clases(
                    "codigo grid h-5 min-w-5 place-items-center rounded-full text-[10px]",
                    es ? "text-sobre-tinta-2" : hecho ? "bg-tinta text-sobre-tinta" : "text-gris",
                  )}
                >
                  {hecho ? <Check size={12} strokeWidth={2} /> : p.n}
                </span>
                {p.texto}
                {hecho && <span className="sr-only">(hecho)</span>}
              </button>
            </li>
          );
        })}
      </ol>
    </nav>
  );
}

/* ── 01 Cliente: buscador grande + rejilla de Expedientes ───────────────── */
function ElegirCliente({ onElegir }: { onElegir: (id: string) => void }) {
  const [q, setQ] = useState("");
  const [lista, setLista] = useState<Cliente[]>([]);
  const [total, setTotal] = useState(0);
  const [cargando, setCargando] = useState(true);

  useEffect(() => {
    let vivo = true;
    setCargando(true);
    const t = setTimeout(
      () => {
        apiClientes
          .listar({ q, estado: "activo", por_pagina: 12 })
          .then((d) => {
            if (!vivo) return;
            setLista(d.clientes);
            setTotal(d.total);
          })
          .finally(() => vivo && setCargando(false));
      },
      q ? 250 : 0,
    );
    return () => {
      vivo = false;
      clearTimeout(t);
    };
  }, [q]);

  return (
    <section aria-labelledby="titulo-elegir" className="space-y-8">
      <div>
        <h2 id="titulo-elegir" className="t-h1 text-tinta">¿De qué cliente?</h2>
        <p className="t-body mt-2 max-w-2xl text-grafito">
          El periodo queda en la historia del cliente y los saldos de cierre abren el mes siguiente solos.
        </p>
      </div>

      <label className="material-hundido flex h-14 max-w-2xl items-center gap-3 rounded-full px-5">
        <Search size={20} strokeWidth={1.5} aria-hidden className="shrink-0 text-gris" />
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Nombre o NIT del cliente"
          aria-label="Buscar cliente"
          autoFocus
          className="min-w-0 flex-1 bg-transparent text-[17px] text-tinta placeholder:text-gris focus:outline-none focus-visible:shadow-none"
        />
      </label>

      {cargando && !lista.length && <EsqueletoExpedientes cuantos={3} />}

      {!cargando && lista.length === 0 && (
        <CarpetaVacia
          titulo={q ? "Ningún cliente coincide" : "Todavía no hay clientes activos"}
          accion={<BotonPrimario a="/clientes/nuevo" flecha>Crear el cliente</BotonPrimario>}
        >
          Cree la ficha del cliente antes de contabilizarle un periodo.
        </CarpetaVacia>
      )}

      {lista.length > 0 && (
        <>
          <ul className="grid gap-x-6 gap-y-10 pt-4 sm:grid-cols-2 escritorio:grid-cols-3">
            {lista.map((c, i) => (
              <li key={c.id} className="min-w-0">
                <Expediente
                  variante="papel"
                  etiqueta={`${c.sigla || "Cliente"} — ${String(i + 1).padStart(3, "0")}`}
                  onClick={() => onElegir(c.id)}
                  etiquetaAccesible={`Trabajar un periodo de ${c.razon_social}`}
                  className="h-full"
                >
                  <div className="flex items-start gap-3">
                    <EsferaCliente nit={c.nit} nombre={c.razon_social} tamano={56} />
                    <div className="min-w-0">
                      <p className="t-body line-clamp-2 font-semibold text-tinta">{c.razon_social}</p>
                      <p className="codigo mt-1 text-[12px] text-gris">NIT {c.nit_formateado}</p>
                    </div>
                  </div>
                  <p className="t-small mt-4 text-grafito">
                    {c.municipio || "Sin municipio"} · <span className="capitalize">{c.periodicidad}</span>
                  </p>
                </Expediente>
              </li>
            ))}
          </ul>
          {total > lista.length && (
            <p className="t-meta text-gris">
              Mostrando {lista.length} de {total.toLocaleString("es-CO")}. Escriba para filtrar.
            </p>
          )}
        </>
      )}
    </section>
  );
}
