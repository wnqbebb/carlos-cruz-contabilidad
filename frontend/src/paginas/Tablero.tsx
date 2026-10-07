import { ArrowLeft, ArrowRight, ArrowUpRight, Plus } from "lucide-react";
import { useEffect, useLayoutEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { Link } from "react-router-dom";
import { marcarTableroListo, useAparicion } from "../animacion";
import { analisis, clientes as apiClientes, sistema } from "../api";
import { useMetaPagina } from "../componentes/Marco";
import { BotonSubirArchivo } from "../componentes/Subir";
import { clases, cmp, esCero, fechaLarga, pesos, porcentaje, razon, restar, sumar } from "../formato";
import type { Cliente, Periodo, Severidad, Tablero as DatosTablero } from "../tipos";
import {
  BotonPrimario,
  Cifra,
  DURACION,
  EnlaceSubrayado,
  EsferaCliente,
  EsqueletoTablero,
  EstadoError,
  EtiquetaSeccion,
  Expediente,
  InsigniaEstado,
  TituloPagina,
  gsap,
  sinMovimiento,
} from "../ui";

/**
 * Tablero (spec 6.2). Orden de lectura:
 *   1. Título y subtítulo con el último corte.
 *   2. Fila héroe: Expediente con el resultado del mes · ecuación contable.
 *   3. Fila de estado: tira de 12 meses · nómina y seguridad social vigentes.
 *   4. Cola de operaciones.
 *   5. Clientes recientes en carrusel.
 *
 * Fuentes de datos (todas existentes, ningún endpoint nuevo):
 *   /api/tablero ............ conteos, pendientes y serie mensual de la cartera
 *   /api/parametros ......... SMMLV, auxilio y jornada (antes estaban escritos a mano)
 *   /api/clientes ........... los 8 clientes activos más recientes
 *   /api/clientes/:id/periodos  periodos de esos 8 (ecuación, carrusel y tira)
 */

const MESES_CORTOS = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"];
const MESES_LARGOS = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
  "septiembre", "octubre", "noviembre", "diciembre"];

/**
 * Tolerancia antes de considerar un mes «en mora». Es la misma del backend
 * (`MESES_SIN_TRABAJO["mensual"]` en inteligencia/sugerencias.py): un mes se
 * pinta en rojo solo si además el backend reporta una alerta ATRASADO.
 */
const TOLERANCIA_MESES = 2;

type Reciente = { cliente: Cliente; periodos: Periodo[]; ultimo: Periodo | null };

const COLOR_SEVERIDAD: Record<Severidad, string> = {
  critica: "bg-rojo-cartel",
  alta: "bg-ambar",
  media: "bg-tinta",
  informativa: "bg-tinta/20",
};
const NOMBRE_SEVERIDAD: Record<Severidad, string> = {
  critica: "Crítico",
  alta: "Importante",
  media: "Revisar",
  informativa: "Dato",
};

const mesLargo = (clave: string) => {
  const [a, m] = clave.split("-");
  return `${MESES_LARGOS[Number(m) - 1] ?? m} ${a}`;
};
const corteCorto = (iso: string) => {
  const [a, m, d] = iso.slice(0, 10).split("-");
  return `${Number(d)} ${MESES_CORTOS[Number(m) - 1] ?? m} ${a}`;
};
const soloDigitos = (t: string) => t.replace(/\D/g, "");

export function Tablero() {
  const [datos, setDatos] = useState<DatosTablero | null>(null);
  const [parametros, setParametros] = useState<Record<string, any> | null>(null);
  const [recientes, setRecientes] = useState<Reciente[] | null>(null);
  const [error, setError] = useState("");

  const [intento, setIntento] = useState(0);

  useEffect(() => {
    setError("");
    analisis.tablero().then(setDatos).catch((e) => setError((e as Error).message));
    sistema.parametros().then(setParametros).catch(() => setParametros({}));
    apiClientes
      .listar({ estado: "activo", orden: "actualizado", descendente: true, por_pagina: 8 })
      .then((pag) =>
        Promise.all(
          pag.clientes.map(async (cliente) => {
            const periodos = await analisis.periodos(cliente.id).then((r) => r.periodos).catch(() => [] as Periodo[]);
            const ordenados = [...periodos].sort((a, b) => b.hasta.localeCompare(a.hasta));
            return { cliente, periodos: ordenados, ultimo: ordenados[0] ?? null };
          }),
        ),
      )
      .then(setRecientes)
      .catch(() => setRecientes([]));
  }, [intento]);

  useMetaPagina(datos?.trabajo.ultimo_corte ? `Corte ${corteCorto(datos.trabajo.ultimo_corte)}` : null);

  // El preloader espera esta señal (o se rinde a los 4 s): no se alarga si los datos llegan antes.
  useEffect(() => {
    if (datos || error) marcarTableroListo();
  }, [datos, error]);

  // El periodo más reciente entre los clientes recientes: base de la ecuación.
  const masReciente = useMemo(() => {
    const conPeriodo = (recientes ?? []).filter((r) => r.ultimo);
    conPeriodo.sort((a, b) => b.ultimo!.hasta.localeCompare(a.ultimo!.hasta));
    return conPeriodo[0] ?? null;
  }, [recientes]);

  if (error) {
    return <EstadoError titulo="No se pudo abrir el tablero" detalle={error} onReintentar={() => setIntento((n) => n + 1)} />;
  }
  if (!datos) return <EsqueletoTablero />;

  const activos = datos.clientes.activos;
  const mes = datos.serie[datos.serie.length - 1] ?? null;

  return (
    <div className="space-y-16 escritorio:space-y-20">
      <div className="flex flex-wrap items-end justify-between gap-6">
        <TituloPagina
          subtitulo={
            <>
              {activos} {activos === 1 ? "cliente activo" : "clientes activos"}
              {datos.trabajo.ultimo_corte && <> · último corte {fechaLarga(datos.trabajo.ultimo_corte)}</>}
            </>
          }
        >
          Tablero
        </TituloPagina>
        {/* La acción de partida del contador: soltar un archivo. No tiene que
            elegir cliente ni pantalla primero. */}
        <BotonSubirArchivo />
      </div>

      {/* ── 1. Fila héroe ────────────────────────────────────────────── */}
      <section aria-label="Resultado y ecuación contable" className="columnas-12">
        <div className="col-span-12 escritorio:col-span-7">
          <Heroe mes={mes} reciente={masReciente} />
        </div>
        <div className="col-span-12 escritorio:col-span-5">
          <Ecuacion reciente={masReciente} cargando={recientes === null} />
        </div>
      </section>

      {/* ── 2. Fila de estado ────────────────────────────────────────── */}
      <section aria-label="Estado de los periodos y parámetros legales" className="columnas-12">
        <div className="col-span-12 escritorio:col-span-7">
          <TiraPeriodos datos={datos} recientes={recientes} />
        </div>
        <div className="col-span-12 escritorio:col-span-5">
          <Nomina parametros={parametros} />
        </div>
      </section>

      {/* ── 3. Cola de operaciones ───────────────────────────────────── */}
      <ColaOperaciones datos={datos} />

      {/* ── 4. Clientes recientes ────────────────────────────────────── */}
      <ClientesRecientes recientes={recientes} total={datos.clientes.total} />
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════════════════
   1 · Expediente héroe — resultado del último mes de toda la cartera
   ═══════════════════════════════════════════════════════════════════════════ */
function Heroe({ mes, reciente }: { mes: DatosTablero["serie"][number] | null; reciente: Reciente | null }) {
  if (!mes) {
    return (
      <Expediente etiqueta="01 • Resultado" flecha={false} titulo="Aún no hay periodos calculados">
        <p className="t-body max-w-md">
          Cuando trabaje el primer periodo de un cliente, aquí aparece su resultado con la cifra exacta.
        </p>
        <div className="mt-6">
          <BotonPrimario a="/trabajo" flecha className="!bg-sobre-tinta !text-tinta">
            Trabajar el primer periodo
          </BotonPrimario>
        </div>
      </Expediente>
    );
  }
  const margen = razon(mes.utilidad, mes.total_ingresos, 4);
  const destino = reciente?.cliente ? `/clientes/${reciente.cliente.id}?vista=estados` : "/clientes";
  return (
    <Expediente
      etiqueta="01 • Resultado"
      a={destino}
      etiquetaAccesible={`Resultado de ${mesLargo(mes.mes)}: ${pesos(mes.utilidad)}. Ver estado de resultados`}
      className="h-full"
    >
      <p className="t-meta text-sobre-tinta-2">
        {esNegativoTexto(mes.utilidad) ? "Pérdida neta" : "Utilidad neta"} · {mesLargo(mes.mes)} · toda la cartera ·{" "}
        {mes.periodos} {mes.periodos === 1 ? "periodo" : "periodos"}
      </p>
      <div className="mt-4 text-sobre-tinta">
        <Cifra valor={mes.utilidad} tamano="display-xl" odometro encajar indicador />
      </div>
      <dl className="mt-10 grid gap-6 border-t border-sobre-tinta/15 pt-5 sm:grid-cols-3">
        <Metrica titulo="Ingresos"><Cifra valor={mes.total_ingresos} tamano="h2" /></Metrica>
        <Metrica titulo="Gastos"><Cifra valor={mes.total_gastos} tamano="h2" /></Metrica>
        <Metrica titulo="Margen neto">
          <span className="t-h2 cifras">{margen === null ? "—" : porcentaje(margen).replace("%", " %")}</span>
        </Metrica>
      </dl>
    </Expediente>
  );
}

const esNegativoTexto = (v: string) => v.trim().startsWith("-") && !esCero(v);

function Metrica({ titulo, children }: { titulo: string; children: ReactNode }) {
  return (
    <div className="min-w-0">
      <dd className="text-sobre-tinta">{children}</dd>
      <dt className="t-meta mt-1.5 text-sobre-tinta-2">{titulo}</dt>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════════════════
   2 · Ecuación contable tipográfica con balanza
   ═══════════════════════════════════════════════════════════════════════════ */
function Ecuacion({ reciente, cargando }: { reciente: Reciente | null; cargando: boolean }) {
  const viga = useRef<HTMLDivElement>(null);
  const p = reciente?.ultimo ?? null;
  const activo = p?.total_activo ?? "0";
  const pasivo = p?.total_pasivo ?? "0";
  const patrimonio = p?.total_patrimonio ?? "0";

  // Proporciones SOLO para dibujar las barras; las cifras se muestran exactas.
  const total = Math.abs(Number(activo)) || 1;
  const anchoPasivo = Math.max(0, Math.min(100, (Math.abs(Number(pasivo)) / total) * 100));
  const anchoPatrimonio = Math.max(0, Math.min(100 - anchoPasivo, (Math.abs(Number(patrimonio)) / total) * 100));

  // Balanza: la viga entra inclinada y se nivela con un leve asentamiento (spec 8).
  useLayoutEffect(() => {
    if (!viga.current || !p || sinMovimiento()) return;
    const ctx = gsap.context(() => {
      gsap.fromTo(viga.current, { rotation: -3.5 }, { rotation: 0, duration: DURACION.balanza, ease: "back.out(1.4)", delay: 0.15 });
    });
    return () => ctx.revert();
  }, [p?.id]);

  return (
    <section className="material-hoja flex h-full flex-col p-6 sm:p-7">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <EtiquetaSeccion indice={2}>Ecuación contable</EtiquetaSeccion>
        {p && (p.cuadra ? (
          <InsigniaEstado estado="cuadra" />
        ) : (
          <InsigniaEstado estado="descuadre">
            Descuadre de {pesos(restar(activo, sumar(pasivo, patrimonio)).replace("-", ""))}
          </InsigniaEstado>
        ))}
      </div>

      {cargando && <p className="t-small mt-8 text-gris">Leyendo el último corte…</p>}
      {!cargando && !p && (
        <p className="t-body mt-8 text-grafito">
          Todavía no hay un periodo calculado. La ecuación Activo = Pasivo + Patrimonio aparece con el primer cierre.
        </p>
      )}

      {p && reciente && (
        <>
          <p className="t-small mt-4 text-gris">
            {reciente.cliente.sigla || reciente.cliente.razon_social} · corte {fechaLarga(p.hasta)}
          </p>

          <div className="mt-7 space-y-4">
            <FilaEcuacion signo="" nombre="Activo" valor={activo} fuerte />
            <FilaEcuacion signo="=" nombre="Pasivo" valor={pasivo} />
            <FilaEcuacion signo="+" nombre="Patrimonio" valor={patrimonio} />
          </div>

          <div ref={viga} className="mt-auto origin-center space-y-1.5 pt-8" aria-hidden>
            <div className="h-2.5 w-full rounded-full bg-tinta" />
            <div className="flex h-2.5 w-full overflow-hidden rounded-full bg-hoja-2">
              <div className="h-full bg-grafito" style={{ width: `${anchoPasivo}%` }} />
              <div className="h-full border-l-2 border-hoja bg-gris" style={{ width: `${anchoPatrimonio}%` }} />
            </div>
          </div>
          <div className="t-meta mt-2 flex justify-between text-gris">
            <span>Activo</span>
            <span>Pasivo | Patrimonio</span>
          </div>
        </>
      )}
    </section>
  );
}

function FilaEcuacion({ signo, nombre, valor, fuerte }: { signo: string; nombre: string; valor: string; fuerte?: boolean }) {
  return (
    <div className="flex items-baseline gap-3 border-b border-linea pb-3 last:border-b-0">
      <span aria-hidden className="w-4 shrink-0 text-center t-h2 text-gris">{signo}</span>
      <span className={clases("t-body min-w-0 flex-1", fuerte ? "font-semibold text-tinta" : "text-grafito")}>{nombre}</span>
      <Cifra valor={valor} tamano={fuerte ? "h2" : "body"} className={fuerte ? undefined : "font-medium"} />
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════════════════
   3 · Tira de 12 meses
   ═══════════════════════════════════════════════════════════════════════════ */
type EstadoMes = "cerrado" | "abierto" | "pendiente" | "mora";

const ESTILO_MES: Record<EstadoMes, { clase: string; texto: string }> = {
  cerrado: { clase: "bg-tinta", texto: "Cerrado" },
  abierto: { clase: "border-2 border-azul bg-azul-suave", texto: "Abierto" },
  pendiente: { clase: "rayado border border-linea", texto: "Sin contabilizar" },
  mora: { clase: "bg-rojo-cartel", texto: "En mora" },
};

function TiraPeriodos({ datos, recientes }: { datos: DatosTablero; recientes: Reciente[] | null }) {
  const hoy = new Date();
  const indiceHoy = hoy.getFullYear() * 12 + hoy.getMonth();
  const hayAtraso = datos.pendientes.clientes.some((c) => c.principal.codigo === "ATRASADO");
  const atrasado = datos.pendientes.clientes.find((c) => c.principal.codigo === "ATRASADO");
  const periodos = (recientes ?? []).flatMap((r) => r.periodos);

  const meses = Array.from({ length: 12 }, (_, i) => {
    const idx = indiceHoy - 11 + i;
    const anio = Math.floor(idx / 12);
    const m = (idx % 12) + 1;
    const clave = `${anio}-${String(m).padStart(2, "0")}`;
    const delMes = periodos.filter((p) => p.hasta.slice(0, 7) === clave);
    const enSerie = datos.serie.some((s) => s.mes === clave && s.periodos > 0);
    let estado: EstadoMes;
    if (delMes.length) estado = delMes.some((p) => p.estado !== "cerrado") ? "abierto" : "cerrado";
    else if (enSerie) estado = datos.trabajo.pendientes > 0 ? "abierto" : "cerrado";
    else estado = hayAtraso && indiceHoy - idx > TOLERANCIA_MESES ? "mora" : "pendiente";
    return { clave, anio, m, estado };
  });

  const conteo = (e: EstadoMes) => meses.filter((x) => x.estado === e).length;

  return (
    <section className="material-hoja h-full p-6 sm:p-7">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <EtiquetaSeccion indice={3}>Gestión de periodos</EtiquetaSeccion>
        <span className="t-small text-gris">
          {datos.trabajo.cerrados} {datos.trabajo.cerrados === 1 ? "cerrado" : "cerrados"} · {datos.trabajo.pendientes}{" "}
          {datos.trabajo.pendientes === 1 ? "abierto" : "abiertos"}
          {datos.trabajo.descuadrados > 0 && <span className="text-rojo"> · {datos.trabajo.descuadrados} con descuadre</span>}
        </span>
      </div>

      <h2 className="t-h2 mt-5 text-tinta">Últimos 12 meses de la cartera</h2>
      {atrasado && (
        <p className="t-body mt-1 text-rojo">
          {atrasado.principal.titulo} — {atrasado.razon_social}
        </p>
      )}

      <ol className="mt-6 grid grid-cols-6 gap-2 sm:grid-cols-12" aria-label="Estado de cada mes">
        {meses.map((x) => (
          <li key={x.clave} className="min-w-0">
            <div
              className={clases("h-14 rounded-chip", ESTILO_MES[x.estado].clase)}
              title={`${mesLargo(x.clave)}: ${ESTILO_MES[x.estado].texto}`}
            />
            <p className="t-meta mt-1.5 text-center text-gris">
              {MESES_CORTOS[x.m - 1]}
              {x.m === 1 && <span className="block text-[10px]">{x.anio}</span>}
            </p>
            <span className="sr-only">{`${mesLargo(x.clave)}: ${ESTILO_MES[x.estado].texto}`}</span>
          </li>
        ))}
      </ol>

      <ul className="t-small mt-5 flex flex-wrap gap-x-5 gap-y-2 text-grafito">
        {(Object.keys(ESTILO_MES) as EstadoMes[]).map((e) => (
          <li key={e} className="flex items-center gap-2">
            <span aria-hidden className={clases("h-3 w-5 rounded-[3px]", ESTILO_MES[e].clase)} />
            {ESTILO_MES[e].texto} <span className="text-gris">({conteo(e)})</span>
          </li>
        ))}
      </ul>
    </section>
  );
}

/* ═══════════════════════════════════════════════════════════════════════════
   3b · Nómina y seguridad social vigentes (de /api/parametros)
   ═══════════════════════════════════════════════════════════════════════════ */
function Nomina({ parametros }: { parametros: Record<string, any> | null }) {
  const anioHoy = String(new Date().getFullYear());
  const anios = Object.keys(parametros ?? {}).filter((k) => /^\d{4}$/.test(k)).sort();
  const anio = anios.includes(anioHoy) ? anioHoy : anios[anios.length - 1];
  const p = anio ? parametros?.[anio] : null;

  const hoyIso = new Date().toISOString().slice(0, 10);
  const tramos: { desde: string; horas_semana: number }[] = p?.jornada_tramos ?? [];
  const vigente = [...tramos].filter((t) => t.desde <= hoyIso).sort((a, b) => b.desde.localeCompare(a.desde))[0] ?? tramos[0];

  return (
    <section className="material-hoja flex h-full flex-col p-6 sm:p-7">
      <EtiquetaSeccion indice={4}>Nómina y seguridad social</EtiquetaSeccion>
      <h2 className="t-h2 mt-5 text-tinta">Valores vigentes {anio ?? ""}</h2>

      {parametros === null && <p className="t-small mt-6 text-gris">Leyendo parámetros…</p>}
      {parametros !== null && !p && (
        <p className="t-body mt-6 text-grafito">No hay parámetros legales cargados. Regístrelos en Parámetros.</p>
      )}
      {p && (
        <dl className="mt-5 divide-y divide-linea">
          <Renglon nombre="SMMLV" valor={<Cifra valor={p.smmlv} />} />
          <Renglon nombre="Auxilio de transporte" valor={<Cifra valor={p.aux_transporte} />} />
          <Renglon nombre="SMMLV + auxilio" valor={<Cifra valor={sumar(p.smmlv, p.aux_transporte)} className="font-semibold" />} />
          {vigente && (
            <Renglon
              nombre="Jornada máxima"
              valor={
                <span className="t-body tabular-nums">
                  {vigente.horas_semana} h/semana <span className="block text-gris sm:inline">desde {fechaLarga(vigente.desde)}</span>
                </span>
              }
            />
          )}
        </dl>
      )}

      <div className="mt-auto flex items-end justify-between gap-4 pt-6">
        {p?._fuente && (
          <details className="t-small max-w-[40ch] text-gris">
            <summary className="cursor-pointer select-none">Fuente legal</summary>
            <p className="mt-2">{p._fuente}</p>
          </details>
        )}
        <EnlaceSubrayado a="/parametros">Ajustar <ArrowRight size={14} strokeWidth={1.5} aria-hidden /></EnlaceSubrayado>
      </div>
    </section>
  );
}

function Renglon({ nombre, valor }: { nombre: string; valor: ReactNode }) {
  return (
    <div className="flex items-baseline justify-between gap-4 py-2.5">
      <dt className="t-body text-grafito">{nombre}</dt>
      <dd className="min-w-0 text-right text-tinta">{valor}</dd>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════════════════
   4 · Cola de operaciones
   ═══════════════════════════════════════════════════════════════════════════ */
function ColaOperaciones({ datos }: { datos: DatosTablero }) {
  const c = datos.pendientes;
  const bloque = useRef<HTMLElement>(null);
  useAparicion(bloque);
  return (
    <section ref={bloque} aria-labelledby="titulo-cola">
      <div className="flex flex-wrap items-end justify-between gap-4 border-b border-linea pb-4">
        <div>
          <EtiquetaSeccion indice={5}>Cola de operaciones</EtiquetaSeccion>
          <h2 id="titulo-cola" className="t-h1 mt-4 text-tinta">
            {c.con_pendientes === 0
              ? "Nada pendiente"
              : `${c.con_pendientes} ${c.con_pendientes === 1 ? "cliente requiere" : "clientes requieren"} atención`}
          </h2>
        </div>
        <div className="flex flex-wrap gap-2">
          {c.criticas > 0 && <InsigniaEstado estado="descuadre">{c.criticas} {c.criticas === 1 ? "crítico" : "críticos"}</InsigniaEstado>}
          {c.altas > 0 && <InsigniaEstado estado="por-cerrar">{c.altas} {c.altas === 1 ? "importante" : "importantes"}</InsigniaEstado>}
        </div>
      </div>

      {c.clientes.length === 0 ? (
        <p className="t-body py-8 text-grafito">Todos los clientes revisados están al día.</p>
      ) : (
        <ul>
          {c.clientes.map((p) => (
            <li key={p.cliente_id} className="relative border-b border-linea">
              <span aria-hidden className={clases("absolute inset-y-4 left-0 w-1 rounded-full", COLOR_SEVERIDAD[p.principal.severidad])} />
              <div className="grid gap-4 py-5 pl-6 sm:grid-cols-[auto_1fr_auto] sm:items-start">
                <EsferaCliente nit={soloDigitos(p.nit_formateado)} nombre={p.razon_social} tamano={32} />
                <div className="min-w-0">
                  <p className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
                    <span className="t-body font-semibold text-tinta">{p.razon_social}</span>
                    <span className="codigo text-[12px] text-gris">{p.nit_formateado}</span>
                    <span className={clases("t-meta", p.principal.severidad === "critica" ? "text-rojo" : p.principal.severidad === "alta" ? "text-ambar" : "text-gris")}>
                      {NOMBRE_SEVERIDAD[p.principal.severidad]}
                    </span>
                  </p>
                  <p className="t-body mt-1 font-medium text-tinta">{p.principal.titulo}</p>
                  <p className="t-small mt-0.5 text-grafito">{p.principal.detalle}</p>
                </div>
                <EnlaceSubrayado a={`/clientes/${p.cliente_id}`} className="justify-self-start sm:mt-1">
                  Ver ficha <ArrowUpRight size={14} strokeWidth={1.5} aria-hidden />
                </EnlaceSubrayado>
              </div>
            </li>
          ))}
        </ul>
      )}
      {c.truncado && (
        <p className="t-small mt-3 text-gris">
          Se revisaron {c.clientes_revisados} de {c.clientes_totales} clientes. Los demás se revisan en su ficha.
        </p>
      )}
    </section>
  );
}

/* ═══════════════════════════════════════════════════════════════════════════
   5 · Clientes recientes: carrusel con la tarjeta vecina asomando (ref-03)
   ═══════════════════════════════════════════════════════════════════════════ */
function ClientesRecientes({ recientes, total }: { recientes: Reciente[] | null; total: number }) {
  const pista = useRef<HTMLDivElement>(null);
  const bloque = useRef<HTMLElement>(null);
  useAparicion(bloque);
  const mover = (dir: 1 | -1) => {
    const el = pista.current;
    if (!el) return;
    const tarjeta = el.querySelector<HTMLElement>("[data-tarjeta]");
    el.scrollBy({ left: dir * ((tarjeta?.offsetWidth ?? 320) + 24), behavior: sinMovimiento() ? "auto" : "smooth" });
  };

  return (
    <section ref={bloque} aria-labelledby="titulo-recientes">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <EtiquetaSeccion indice={6}>Clientes recientes</EtiquetaSeccion>
          <h2 id="titulo-recientes" className="t-h1 mt-4 text-tinta">Expedientes abiertos hace poco</h2>
        </div>
        <div className="flex items-center gap-3">
          <EnlaceSubrayado a="/clientes">Ver los {total}</EnlaceSubrayado>
          <button type="button" onClick={() => mover(-1)} aria-label="Anteriores"
            className="grid h-11 w-11 place-items-center rounded-full bg-tinta text-sobre-tinta transition-colors hover:bg-tinta-2">
            <ArrowLeft size={18} strokeWidth={1.5} aria-hidden />
          </button>
          <button type="button" onClick={() => mover(1)} aria-label="Siguientes"
            className="grid h-11 w-11 place-items-center rounded-full bg-tinta text-sobre-tinta transition-colors hover:bg-tinta-2">
            <ArrowRight size={18} strokeWidth={1.5} aria-hidden />
          </button>
        </div>
      </div>

      {recientes === null ? (
        <p className="t-small mt-8 text-gris">Abriendo expedientes…</p>
      ) : (
        <div
          ref={pista}
          className="barra-fina -mx-[var(--margen)] mt-8 flex snap-x snap-mandatory gap-6 overflow-x-auto px-[var(--margen)] pt-6 pb-6"
          style={{ scrollPaddingInline: "var(--margen)" }}
        >
          {recientes.map(({ cliente, ultimo }, i) => (
            <div key={cliente.id} data-tarjeta className="w-[min(320px,82vw)] shrink-0 snap-start">
              <Expediente
                variante="papel"
                etiqueta={`${cliente.sigla || "Cliente"} — ${String(i + 1).padStart(3, "0")}`}
                a={`/clientes/${cliente.id}`}
                className="h-full"
              >
                <div className="flex items-center gap-3">
                  <EsferaCliente nit={cliente.nit} nombre={cliente.razon_social} tamano={56} />
                  <div className="min-w-0">
                    <p className="t-body line-clamp-2 font-semibold text-tinta">{cliente.razon_social}</p>
                    <p className="codigo mt-0.5 text-[12px] text-gris">NIT {cliente.nit_formateado}</p>
                  </div>
                </div>
                <p className="t-small mt-4 text-grafito">
                  {cliente.municipio || "Sin municipio"} · {cliente.periodicidad}
                </p>
                <div className="mt-4 border-t border-linea pt-4">
                  {ultimo ? (
                    <>
                      <div className="flex items-center justify-between gap-2">
                        <span className="t-meta text-gris">Corte {corteCorto(ultimo.hasta)}</span>
                        <InsigniaEstado estado={ultimo.estado === "cerrado" ? "cerrado" : "por-cerrar"}>
                          {ultimo.estado === "cerrado" ? "Cerrado" : "Por cerrar"}
                        </InsigniaEstado>
                      </div>
                      <div className="mt-2 flex items-baseline justify-between gap-2">
                        <span className="t-small text-grafito">{cmp(ultimo.utilidad, "0") < 0 ? "Pérdida" : "Utilidad"}</span>
                        <Cifra valor={ultimo.utilidad} tamano="h2" encajar />
                      </div>
                    </>
                  ) : (
                    <p className="t-small text-gris">Sin periodos todavía</p>
                  )}
                </div>
              </Expediente>
            </div>
          ))}

          <div data-tarjeta className="w-[min(320px,82vw)] shrink-0 snap-start">
            <Link
              to="/clientes/nuevo"
              className="flex h-full min-h-[260px] flex-col items-center justify-center gap-3 rounded-hoja border border-dashed border-tinta/25 text-grafito transition-colors hover:border-tinta/50 hover:text-tinta"
            >
              <span className="grid h-12 w-12 place-items-center rounded-full border border-linea bg-hoja">
                <Plus size={20} strokeWidth={1.5} aria-hidden />
              </span>
              <span className="t-body font-medium">Abrir un expediente nuevo</span>
            </Link>
          </div>
        </div>
      )}
    </section>
  );
}
