import { ArrowRight, Clock, Plus } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { marcarTableroListo, useAparicion } from "../animacion";
import { analisis } from "../api";
import { useContador } from "../contador";
import { Cabecera, useMetaPagina } from "../componentes/Marco";
import { BotonSubirArchivo, ZonaSubida } from "../componentes/Subir";
import { clases, fecha, fechaLarga } from "../formato";
import type { MesTablero, Tablero as DatosTablero, Tarea } from "../tipos";
import {
  Cifra,
  EnlaceSubrayado,
  EsferaCliente,
  EsqueletoTablero,
  EstadoError,
  EtiquetaSeccion,
  Expediente,
  InsigniaEstado,
  useAvisos,
} from "../ui";

/**
 * Tablero del contador (spec v2.2 · Fase 7). Básico y útil, en este orden:
 *   1. Saludo, fecha y «Subir archivo» con una zona de arrastre amplia.
 *   2. Cuatro indicadores: clientes activos, honorarios mensuales, al día, atrasados.
 *   3. Tareas sugeridas (el bloque principal): prioridad, cliente, qué hacer,
 *      por qué y acción directa; «Hacer ahora» o «Posponer hasta mañana».
 *   4. La cartera mes a mes (H13: cerrados, abiertos, sin contabilizar).
 *   5. Clientes recientes en carpetas, con «Ver todos».
 *   6. Actividad reciente: las últimas 8 líneas de la bitácora.
 *
 * Ya no está: el resultado del mes de la cartera, la ecuación contable, la
 * tarjeta de nómina (vive en Parámetros) ni cifras financieras de un cliente.
 * Todo lo que se muestra lo cuenta el servidor (`/api/tablero`).
 */

const MESES_CORTOS = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"];

const PRIORIDAD: Record<Tarea["prioridad"], { texto: string; punto: string }> = {
  critica: { texto: "Urgente", punto: "bg-rojo-cartel" },
  alta: { texto: "Importante", punto: "bg-ambar" },
  media: { texto: "Cuando pueda", punto: "bg-tinta/40" },
};

function saludo(hora: number): string {
  if (hora < 12) return "Buenos días";
  if (hora < 19) return "Buenas tardes";
  return "Buenas noches";
}

export function Tablero() {
  const [datos, setDatos] = useState<DatosTablero | null>(null);
  const [error, setError] = useState("");
  const [intento, setIntento] = useState(0);
  const contador = useContador();

  useEffect(() => {
    setError("");
    analisis.tablero().then(setDatos).catch((e) => setError((e as Error).message));
  }, [intento]);

  useMetaPagina(datos?.trabajo.ultimo_corte ? `Último corte ${fecha(datos.trabajo.ultimo_corte)}` : null);

  // El preloader espera esta señal (o se rinde a los 4 s).
  useEffect(() => {
    if (datos || error) marcarTableroListo();
  }, [datos, error]);

  if (error) {
    return <EstadoError titulo="No se pudo abrir el tablero" detalle={error} onReintentar={() => setIntento((n) => n + 1)} />;
  }
  if (!datos) return <EsqueletoTablero />;

  const ind = datos.indicadores;
  const hoy = new Date();

  return (
    <div className="space-y-16 escritorio:space-y-20">
      {/* ── 1. saludo, fecha y subir: en la franja de cabecera ───────────── */}
      <Cabecera>
      <section aria-labelledby="saludo" className="columnas-12 items-end">
        <div className="col-span-12 escritorio:col-span-5">
          <p className="t-meta text-gris">{fechaLarga(datos.hoy)}</p>
          <h1 id="saludo" className="t-display mt-4 text-tinta">
            {saludo(hoy.getHours())}
            {contador?.nombre_corto ? `, ${contador.nombre_corto}` : ""}.
          </h1>
          <p className="t-body mt-4 max-w-md text-grafito">
            {datos.tareas_total
              ? `Hay ${datos.tareas_total} ${datos.tareas_total === 1 ? "tarea" : "tareas"} en la cartera. Abajo, en orden de urgencia.`
              : "No hay nada pendiente en la cartera. Suba el archivo del próximo cliente."}
          </p>
          <div className="mt-6">
            <BotonSubirArchivo />
          </div>
        </div>
        <div className="col-span-12 escritorio:col-span-7">
          <ZonaSubida className="min-h-[220px]" />
        </div>
      </section>
      </Cabecera>

      {/* ── 2. cuatro indicadores ───────────────────────────────────────── */}
      <section aria-label="Indicadores de la cartera" className="grid grid-cols-2 gap-4 escritorio:grid-cols-4">
        <Indicador titulo="Clientes activos" a="/clientes">
          <span className="cifras t-kpi text-tinta">{ind.clientes_activos.toLocaleString("es-CO")}</span>
        </Indicador>
        <Indicador titulo="Honorarios mensuales">
          <Cifra valor={ind.honorarios_mensuales} tamano="h2" encajar />
        </Indicador>
        <Indicador titulo="Al día" detalle="Contabilizados dentro de su periodicidad">
          <span className="cifras t-kpi text-tinta">{ind.al_dia.toLocaleString("es-CO")}</span>
        </Indicador>
        <Indicador titulo="Atrasados" detalle={ind.atrasados ? "Con meses sin contabilizar" : "Ninguno"}>
          <span className={clases("cifras t-kpi", ind.atrasados ? "text-rojo" : "text-tinta")}>
            {ind.atrasados.toLocaleString("es-CO")}
          </span>
        </Indicador>
      </section>

      {/* ── 3. tareas sugeridas ─────────────────────────────────────────── */}
      <Tareas inicial={datos.tareas} total={datos.tareas_total} />

      {/* ── 4. la cartera mes a mes ─────────────────────────────────────── */}
      <CarteraPorMes meses={datos.meses} />

      {/* ── 5. clientes recientes ───────────────────────────────────────── */}
      <Recientes datos={datos} />

      {/* ── 6. actividad reciente ───────────────────────────────────────── */}
      <ActividadReciente datos={datos} />
    </div>
  );
}

function Indicador({ titulo, detalle, a, children }: { titulo: string; detalle?: string; a?: string; children: React.ReactNode }) {
  const contenido = (
    <>
      <p className="t-meta text-gris">{titulo}</p>
      <div className="mt-3 min-w-0">{children}</div>
      {detalle && <p className="t-small mt-2 text-grafito">{detalle}</p>}
    </>
  );
  const clase = "material-hoja @container block min-w-0 p-5";
  return a ? (
    <Link to={a} className={clases(clase, "transition-colors hover:bg-hoja-2")}>{contenido}</Link>
  ) : (
    <div className={clase}>{contenido}</div>
  );
}

/* ── tareas sugeridas ─────────────────────────────────────────────────────── */
function Tareas({ inicial, total }: { inicial: Tarea[]; total: number }) {
  const [tareas, setTareas] = useState(inicial);
  const [ocupada, setOcupada] = useState("");
  const navegar = useNavigate();
  const avisar = useAvisos();
  const bloque = useRef<HTMLElement>(null);
  useAparicion(bloque);
  useEffect(() => setTareas(inicial), [inicial]);

  const hacer = async (t: Tarea) => {
    setOcupada(t.clave);
    await analisis.hacerTarea(t.clave).catch(() => undefined);
    navegar(t.accion.ruta);
  };
  const posponer = async (t: Tarea) => {
    setOcupada(t.clave);
    try {
      await analisis.posponerTarea(t.clave);
      setTareas((ts) => ts.filter((x) => x.clave !== t.clave));
      avisar(`«${t.que}» de ${t.razon_social}: vuelve mañana.`);
    } catch (e) {
      avisar((e as Error).message, "rojo");
    } finally {
      setOcupada("");
    }
  };

  return (
    <section ref={bloque} aria-labelledby="titulo-tareas">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <EtiquetaSeccion indice={1}>Tareas sugeridas</EtiquetaSeccion>
          <h2 id="titulo-tareas" className="t-h1 mt-4 text-tinta">Qué hacer, en orden</h2>
        </div>
        {total > inicial.length && <p className="t-small text-gris">Mostrando {inicial.length} de {total}</p>}
      </div>

      {tareas.length === 0 ? (
        <p className="material-hoja t-body mt-8 p-6 text-grafito">
          Nada pendiente: todos los clientes están al día, cerrados y cuadrados.
        </p>
      ) : (
        <ol className="material-hoja mt-8 divide-y divide-linea">
          {tareas.map((t) => {
            const p = PRIORIDAD[t.prioridad];
            return (
              <li key={t.clave} className="grid gap-4 p-5 escritorio:grid-cols-[150px_minmax(0,1fr)_auto] escritorio:items-center">
                <span className="flex items-center gap-2">
                  <span aria-hidden className={clases("h-2.5 w-2.5 shrink-0 rounded-full", p.punto)} />
                  <span className={clases("t-meta", t.prioridad === "critica" ? "text-rojo" : "text-grafito")}>{p.texto}</span>
                </span>
                <div className="min-w-0">
                  <p className="t-body font-semibold text-tinta">
                    {t.que}
                    <span className="font-normal text-grafito"> · </span>
                    <Link to={`/clientes/${t.cliente_id}`} className="font-normal text-azul-tinta underline-offset-4 hover:underline">
                      {t.razon_social}
                    </Link>
                  </p>
                  <p className="t-small mt-1 text-grafito">
                    <span className="text-tinta">{t.titulo}.</span> {t.por_que}
                  </p>
                </div>
                <div className="flex flex-wrap gap-2">
                  <button
                    type="button"
                    disabled={ocupada === t.clave}
                    onClick={() => hacer(t)}
                    className="inline-flex h-9 items-center gap-1.5 rounded-full bg-tinta px-4 text-[13px] font-medium text-sobre-tinta transition-colors hover:bg-tinta-2 disabled:opacity-60"
                  >
                    Hacer ahora <ArrowRight size={14} strokeWidth={1.5} aria-hidden />
                  </button>
                  <button
                    type="button"
                    disabled={ocupada === t.clave}
                    onClick={() => posponer(t)}
                    className="inline-flex h-9 items-center gap-1.5 rounded-full border border-linea px-4 text-[13px] text-grafito transition-colors hover:bg-hoja-2 hover:text-tinta disabled:opacity-60"
                  >
                    <Clock size={14} strokeWidth={1.5} aria-hidden /> Posponer hasta mañana
                  </button>
                </div>
              </li>
            );
          })}
        </ol>
      )}
    </section>
  );
}

/* ── la cartera mes a mes (H13) ───────────────────────────────────────────── */
function CarteraPorMes({ meses }: { meses: MesTablero[] }) {
  const maximo = Math.max(1, ...meses.map((m) => m.cerrados + m.abiertos + m.sin_contabilizar));
  return (
    <section aria-labelledby="titulo-meses">
      <EtiquetaSeccion indice={2}>La cartera mes a mes</EtiquetaSeccion>
      <h2 id="titulo-meses" className="t-h1 mt-4 text-tinta">Cuántos clientes van cerrados cada mes</h2>
      <div className="material-hoja mt-8 p-5">
        <div className="barra-fina overflow-x-auto">
          <ol className="flex min-w-[640px] items-end gap-2" aria-label="Clientes por mes">
            {meses.map((m) => {
              const [a, mm] = m.mes.split("-");
              const total = m.cerrados + m.abiertos + m.sin_contabilizar;
              return (
                <li key={m.mes} className="flex min-w-0 flex-1 flex-col items-center gap-2">
                  <span className="codigo text-[11px] text-gris">{total || "·"}</span>
                  <span className="flex h-28 w-full max-w-[40px] flex-col-reverse overflow-hidden rounded-chip bg-hoja-2"
                    title={`${m.cerrados} cerrados · ${m.abiertos} abiertos · ${m.sin_contabilizar} sin contabilizar`}>
                    <span className="w-full bg-tinta" style={{ height: `${(m.cerrados / maximo) * 100}%` }} />
                    <span className="w-full bg-azul" style={{ height: `${(m.abiertos / maximo) * 100}%` }} />
                    <span className="w-full bg-rojo-cartel" style={{ height: `${(m.sin_contabilizar / maximo) * 100}%` }} />
                  </span>
                  <span className="t-meta text-gris">{MESES_CORTOS[Number(mm) - 1]}</span>
                  <span className="codigo -mt-1.5 text-[10px] text-gris">{a.slice(2)}</span>
                </li>
              );
            })}
          </ol>
        </div>
        <p className="t-small mt-4 flex flex-wrap gap-x-5 gap-y-1 text-grafito">
          <span className="inline-flex items-center gap-1.5"><span aria-hidden className="h-2.5 w-2.5 rounded-sm bg-tinta" /> Cerrados</span>
          <span className="inline-flex items-center gap-1.5"><span aria-hidden className="h-2.5 w-2.5 rounded-sm bg-azul" /> Calculados, por cerrar</span>
          <span className="inline-flex items-center gap-1.5"><span aria-hidden className="h-2.5 w-2.5 rounded-sm bg-rojo-cartel" /> Sin contabilizar</span>
        </p>
        <details className="mt-4">
          <summary className="t-meta cursor-pointer select-none text-gris">Ver los mismos datos en tabla</summary>
          <table className="t-tabla mt-3 w-full text-[13px]">
            <thead>
              <tr className="text-left">
                {["Mes", "Cerrados", "Por cerrar", "Sin contabilizar"].map((t, i) => (
                  <th key={t} scope="col" className={clases("t-meta border-b border-linea py-2 text-gris", i > 0 && "text-right")}>{t}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {meses.map((m) => (
                <tr key={m.mes}>
                  <td className="border-b border-linea py-1.5">{m.mes}</td>
                  <td className="cifras border-b border-linea py-1.5 text-right">{m.cerrados}</td>
                  <td className="cifras border-b border-linea py-1.5 text-right">{m.abiertos}</td>
                  <td className="cifras border-b border-linea py-1.5 text-right">{m.sin_contabilizar}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </details>
      </div>
    </section>
  );
}

/* ── clientes recientes ─────────────────────────────────────────────────── */
function Recientes({ datos }: { datos: DatosTablero }) {
  return (
    <section aria-labelledby="titulo-recientes">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <EtiquetaSeccion indice={3}>Clientes</EtiquetaSeccion>
          <h2 id="titulo-recientes" className="t-h1 mt-4 text-tinta">Expedientes recientes</h2>
        </div>
        <EnlaceSubrayado a="/clientes">Ver todos ({datos.clientes.activos})</EnlaceSubrayado>
      </div>
      <ul className="mt-8 grid gap-x-6 gap-y-10 pt-4 sm:grid-cols-2 escritorio:grid-cols-4">
        {datos.recientes.map((c, i) => (
          <li key={c.id} className="min-w-0">
            <Expediente
              variante="papel"
              etiqueta={`${c.sigla || "Cliente"} — ${String(i + 1).padStart(3, "0")}`}
              a={`/clientes/${c.id}`}
              className="h-full"
              etiquetaAccesible={`Abrir el expediente de ${c.razon_social}`}
            >
              <div className="flex items-center gap-3">
                <EsferaCliente nit={c.nit} nombre={c.razon_social} tamano={56} />
                <p className="t-small line-clamp-2 min-w-0 font-semibold text-tinta [overflow-wrap:normal] hyphens-auto">{c.razon_social}</p>
              </div>
              <div className="mt-4 flex flex-wrap items-center gap-2 border-t border-linea pt-3">
                {c.estado_trabajo === "atrasado" ? (
                  <InsigniaEstado estado="descuadre">Atrasado</InsigniaEstado>
                ) : (
                  <InsigniaEstado estado="cuadra" discreta>Al día</InsigniaEstado>
                )}
                <span className="t-meta text-gris">
                  {c.ultimo_periodo ? `Corte ${fecha(c.ultimo_periodo.hasta)}` : "Sin periodos"}
                </span>
              </div>
            </Expediente>
          </li>
        ))}
        <li className="min-w-0">
          <Link
            to="/clientes/nuevo"
            className="flex h-full min-h-[170px] flex-col items-center justify-center gap-3 rounded-hoja border border-dashed border-tinta/25 text-grafito transition-colors hover:border-tinta/50 hover:text-tinta"
          >
            <span className="grid h-11 w-11 place-items-center rounded-full border border-linea bg-hoja">
              <Plus size={18} strokeWidth={1.5} aria-hidden />
            </span>
            <span className="t-small font-medium">Cliente nuevo</span>
          </Link>
        </li>
      </ul>
    </section>
  );
}

/* ── actividad reciente ─────────────────────────────────────────────────── */
function ActividadReciente({ datos }: { datos: DatosTablero }) {
  return (
    <section aria-labelledby="titulo-actividad">
      <EtiquetaSeccion indice={4}>Actividad</EtiquetaSeccion>
      <h2 id="titulo-actividad" className="t-h1 mt-4 text-tinta">Lo último que se hizo</h2>
      {datos.actividad.length === 0 ? (
        <p className="t-body mt-6 text-grafito">Todavía no hay actividad.</p>
      ) : (
        <ol className="material-hoja mt-8 divide-y divide-linea">
          {datos.actividad.map((a) => (
            <li key={a.id} className="flex flex-wrap items-baseline gap-x-4 gap-y-1 px-5 py-3">
              <span className="codigo w-36 shrink-0 text-[12px] text-gris">{cuando(a.creado)}</span>
              <span className="t-small font-medium text-tinta">{a.titulo}</span>
              {a.razon_social &&
                (a.cliente_id ? (
                  <Link to={`/clientes/${a.cliente_id}`} className="t-small text-azul-tinta underline-offset-4 hover:underline">
                    {a.razon_social}
                  </Link>
                ) : (
                  <span className="t-small text-grafito">{a.razon_social}</span>
                ))}
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}

function cuando(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return `${d.getDate()} ${MESES_CORTOS[d.getMonth()]} · ${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
}
