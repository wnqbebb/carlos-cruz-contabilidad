import { ArrowDownWideNarrow, ArrowLeft, ArrowRight, ArrowUpNarrowWide, Search, Upload } from "lucide-react";
import { useCallback, useEffect, useRef, useState, type ReactNode } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { clientes as api, descargas } from "../api";
import { clases, fecha } from "../formato";
import type { Cliente, InformeImportacionClientes, PaginaClientes } from "../tipos";
import { Aviso, Boton, Cargando, Dialogo, Insignia, Rotulo } from "../componentes/ui";
import { BotonSubirArchivo, usePuerta } from "../componentes/Subir";
import {
  BotonFantasma,
  BotonPrimario,
  CarpetaVacia,
  Cifra,
  Desplegable,
  EsferaCliente,
  EsqueletoExpedientes,
  EstadoError,
  Expediente,
  InsigniaEstado,
  Interruptor,
  TituloPagina,
} from "../ui";

/**
 * Clientes (spec 6.3). Dos vistas con el Interruptor: Expedientes⁰¹ (rejilla
 * de carpetas, por defecto) y Tabla⁰². Filtro de estado como Interruptor y
 * orden con un desplegable propio. La vista elegida se recuerda en este
 * navegador (comodidad personal, no dato compartido).
 */

type Estado = "activo" | "inactivo" | "archivado" | "todos";
type Vista = "expedientes" | "tabla";
type Orden = "razon_social" | "nit" | "municipio" | "honorarios_mes" | "actualizado";

const ESTADOS: { valor: Estado; texto: string }[] = [
  { valor: "activo", texto: "Activos" },
  { valor: "inactivo", texto: "Inactivos" },
  { valor: "archivado", texto: "Archivados" },
  { valor: "todos", texto: "Todos" },
];

const ORDENES: { valor: Orden; texto: string }[] = [
  { valor: "razon_social", texto: "Nombre" },
  { valor: "nit", texto: "NIT" },
  { valor: "municipio", texto: "Municipio" },
  { valor: "honorarios_mes", texto: "Honorarios" },
  { valor: "actualizado", texto: "Movimiento reciente" },
];

const POR_PAGINA = 50;
const CLAVE_VISTA = "cc-clientes-vista";

function vistaGuardada(): Vista {
  try {
    return localStorage.getItem(CLAVE_VISTA) === "tabla" ? "tabla" : "expedientes";
  } catch {
    return "expedientes";
  }
}

export function Clientes() {
  const [parametros, setParametros] = useSearchParams();
  const [q, setQ] = useState(parametros.get("q") ?? "");
  const [estado, setEstado] = useState<Estado>(() => {
    const e = parametros.get("estado");
    if (e === "inactivo" || e === "archivado") return e;
    return e === "" || e === "todos" ? "todos" : "activo";
  });
  const [orden, setOrden] = useState<Orden>("razon_social");
  const [descendente, setDescendente] = useState(false);
  const [pagina, setPagina] = useState(1);
  const [vista, setVista] = useState<Vista>(vistaGuardada);
  const [datos, setDatos] = useState<PaginaClientes | null>(null);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState("");
  const [importando, setImportando] = useState(parametros.get("importar") === "1");

  const cargar = useCallback(async () => {
    setCargando(true);
    setError("");
    try {
      setDatos(
        await api.listar({
          q,
          estado: estado === "todos" ? "" : estado,
          orden,
          descendente,
          pagina,
          por_pagina: POR_PAGINA,
        }),
      );
    } catch (e) {
      setError((e as Error).message);
      setDatos(null);
    } finally {
      setCargando(false);
    }
  }, [q, estado, orden, descendente, pagina]);

  // Freno de 250 ms: al escribir no se consulta en cada tecla.
  useEffect(() => {
    const t = setTimeout(cargar, q ? 250 : 0);
    return () => clearTimeout(t);
  }, [cargar, q]);

  useEffect(() => setPagina(1), [q, estado, orden, descendente]);

  useEffect(() => {
    const nuevos = new URLSearchParams();
    if (q) nuevos.set("q", q);
    if (estado !== "activo") nuevos.set("estado", estado);
    setParametros(nuevos, { replace: true });
  }, [q, estado, setParametros]);

  const cambiarVista = (v: Vista) => {
    setVista(v);
    try {
      localStorage.setItem(CLAVE_VISTA, v);
    } catch {
      /* sin almacenamiento: la próxima vez vuelve a Expedientes */
    }
  };

  const total = datos?.total ?? 0;

  return (
    <div className="space-y-10">
      {/* ── título y acciones ───────────────────────────────────────── */}
      <div className="flex flex-wrap items-end justify-between gap-6">
        <TituloPagina
          subtitulo={
            datos ? (
              <>
                {total.toLocaleString("es-CO")} {total === 1 ? "expediente" : "expedientes"}
                {q && <> que coinciden con «{q}»</>}
              </>
            ) : (
              "Directorio de la cartera"
            )
          }
        >
          Clientes
        </TituloPagina>
        <div className="flex flex-wrap items-center gap-3">
          {/* «Importar directorio de clientes» dice lo que hace: una LISTA de
              clientes. Antes se llamaba «Importar Excel» y ahí acababa la
              contabilidad de un cliente, que no es eso. */}
          <BotonFantasma
            icono={<Upload size={18} strokeWidth={1.5} aria-hidden />}
            onClick={() => setImportando(true)}
          >
            Importar directorio de clientes
          </BotonFantasma>
          <BotonFantasma a="/clientes/nuevo">Nuevo cliente</BotonFantasma>
          <BotonSubirArchivo />
        </div>
      </div>

      {/* ── controles ───────────────────────────────────────────────── */}
      <div className="space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <Interruptor
            etiqueta="Vista del directorio"
            valor={vista}
            onCambio={cambiarVista}
            opciones={[
              { valor: "expedientes", texto: "Expedientes" },
              { valor: "tabla", texto: "Tabla" },
            ]}
          />
          <Interruptor etiqueta="Estado de los clientes" tamano="sm" valor={estado} onCambio={setEstado} opciones={ESTADOS} />
        </div>

        <div className="flex flex-col gap-3 escritorio:flex-row escritorio:items-center">
          <label className="material-hundido flex h-11 min-w-0 shrink-0 items-center gap-3 rounded-full px-4 escritorio:flex-1">
            <Search size={18} strokeWidth={1.5} aria-hidden className="shrink-0 text-gris" />
            <input
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder="Nombre, NIT, municipio o representante"
              aria-label="Buscar clientes"
              className="t-body min-w-0 flex-1 bg-transparent text-tinta placeholder:text-gris focus:outline-none focus-visible:shadow-none"
            />
          </label>
          <div className="flex min-w-0 items-center gap-2">
            <Desplegable
              etiqueta="Ordenar por"
              prefijo="Ordenar por"
              valor={orden}
              opciones={ORDENES}
              onCambio={setOrden}
              className="min-w-0"
            />
            <button
              type="button"
              onClick={() => setDescendente((d) => !d)}
              aria-label={descendente ? "Orden de mayor a menor. Cambiar" : "Orden de menor a mayor. Cambiar"}
              title={descendente ? "Mayor a menor" : "Menor a mayor"}
              className="grid h-11 w-11 shrink-0 place-items-center rounded-full border border-linea bg-hoja text-tinta transition-colors hover:border-tinta/30"
            >
              {descendente ? (
                <ArrowDownWideNarrow size={18} strokeWidth={1.5} aria-hidden />
              ) : (
                <ArrowUpNarrowWide size={18} strokeWidth={1.5} aria-hidden />
              )}
            </button>
          </div>
        </div>
      </div>

      {error && <EstadoError titulo="No se pudo abrir el directorio" detalle={error} onReintentar={cargar} />}
      {cargando && !datos && !error && (vista === "expedientes" ? <EsqueletoExpedientes /> : <Cargando texto="Abriendo el directorio" />)}

      {datos && datos.clientes.length === 0 && !cargando &&
        (q ? (
          <CarpetaVacia
            titulo="Ningún expediente coincide"
            accion={<BotonFantasma onClick={() => setQ("")}>Limpiar búsqueda</BotonFantasma>}
          >
            Pruebe con el NIT sin puntos o con una parte del nombre.
          </CarpetaVacia>
        ) : (
          <CarpetaVacia
            titulo="Aún no hay expedientes"
            accion={
              <BotonPrimario a="/clientes/nuevo" flecha>
                Crear el primer cliente
              </BotonPrimario>
            }
          >
            Agregue fichas una a una o cargue todo su directorio desde un Excel.
          </CarpetaVacia>
        ))}

      {datos && datos.clientes.length > 0 && (
        <div className={clases("space-y-8 transition-opacity duration-200", cargando && "opacity-60")}>
          {vista === "expedientes" ? (
            <RejillaExpedientes clientes={datos.clientes} desde={(datos.pagina - 1) * datos.por_pagina} />
          ) : (
            <TablaClientes clientes={datos.clientes} />
          )}
          <Paginador
            pagina={datos.pagina}
            paginas={datos.paginas}
            total={datos.total}
            porPagina={datos.por_pagina}
            onCambio={setPagina}
          />
        </div>
      )}

      {importando && (
        <DialogoImportar
          onCerrar={() => setImportando(false)}
          onListo={() => {
            setImportando(false);
            cargar();
          }}
        />
      )}
    </div>
  );
}

/* ── vista Expedientes ──────────────────────────────────────────────── */
function RejillaExpedientes({ clientes, desde }: { clientes: Cliente[]; desde: number }) {
  return (
    <ul className="grid gap-x-6 gap-y-10 pt-4 sm:grid-cols-2 escritorio:grid-cols-3">
      {clientes.map((c, i) => (
        <li key={c.id} className="min-w-0">
          <Expediente
            variante="papel"
            etiqueta={`${c.sigla || "Cliente"} — ${String(desde + i + 1).padStart(3, "0")}`}
            a={`/clientes/${c.id}`}
            className="h-full"
            etiquetaAccesible={`Abrir el expediente de ${c.razon_social}`}
          >
            <div className="flex items-start gap-3">
              <EsferaCliente nit={c.nit} nombre={c.razon_social} tamano={56} />
              <div className="min-w-0">
                <p className="t-body line-clamp-2 font-semibold text-tinta">{c.razon_social}</p>
                <p className="codigo mt-1 text-[12px] text-gris">NIT {c.nit_formateado}</p>
              </div>
            </div>
            <dl className="mt-5 grid grid-cols-2 gap-x-4 gap-y-3 border-t border-linea pt-4">
              <Dato nombre="Municipio">{c.municipio || "—"}</Dato>
              <Dato nombre="Periodicidad">
                <span className="capitalize">{c.periodicidad}</span>
              </Dato>
              <Dato nombre="Honorarios/mes">
                <Cifra valor={c.honorarios_mes} tamano="body" encajar />
              </Dato>
              <Dato nombre="Actualizado">
                <span className="tabular-nums">{fecha(c.actualizado)}</span>
              </Dato>
            </dl>
            <div className="mt-4 flex flex-wrap items-center gap-2">
              <InsigniaEstado estado={c.estado} />
              {c.etiquetas.slice(0, 2).map((e) => (
                <span key={e} className="t-small rounded-full border border-linea px-2.5 py-0.5 text-grafito">
                  {e}
                </span>
              ))}
            </div>
          </Expediente>
        </li>
      ))}
    </ul>
  );
}

function Dato({ nombre, children }: { nombre: string; children: ReactNode }) {
  return (
    <div className="@container min-w-0">
      <dt className="t-meta text-gris">{nombre}</dt>
      <dd className="t-small mt-1 truncate text-tinta">{children}</dd>
    </div>
  );
}

/* ── vista Tabla (registro Taller: sin animación de entrada) ────────── */
const COLUMNAS = ["Cliente", "NIT", "Municipio", "Periodicidad", "Honorarios/mes", "Estado", "Actualizado"];

function TablaClientes({ clientes }: { clientes: Cliente[] }) {
  return (
    <section className="material-hoja contener overflow-hidden">
      <div className="barra-fina max-h-[70vh] overflow-auto">
        <table className="t-tabla w-full min-w-[860px] border-separate border-spacing-0">
          <thead className="sticky top-0 z-10 bg-hoja">
            <tr>
              {COLUMNAS.map((t, i) => (
                <th
                  key={t}
                  scope="col"
                  className={clases(
                    "t-meta border-b border-linea px-4 py-3 text-gris",
                    i === 0 && "pl-5",
                    i === 4 || i === 6 ? "text-right" : "text-left",
                  )}
                >
                  {t}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {clientes.map((c) => (
              <tr key={c.id} className="transition-colors duration-150 hover:bg-hoja-2">
                <td className="border-b border-linea py-3 pr-4 pl-5">
                  <Link to={`/clientes/${c.id}`} className="flex items-center gap-3">
                    <EsferaCliente nit={c.nit} nombre={c.razon_social} tamano={32} />
                    <span className="min-w-0">
                      <span className="block truncate font-medium text-tinta">{c.razon_social}</span>
                      {c.sigla && <span className="t-small block text-gris">{c.sigla}</span>}
                    </span>
                  </Link>
                </td>
                <td className="codigo border-b border-linea px-4 py-3 whitespace-nowrap text-grafito">{c.nit_formateado}</td>
                <td className="border-b border-linea px-4 py-3 text-grafito">{c.municipio || "—"}</td>
                <td className="border-b border-linea px-4 py-3 capitalize text-grafito">{c.periodicidad}</td>
                <td className="border-b border-linea px-4 py-3 text-right">
                  <Cifra valor={c.honorarios_mes} tamano="tabla" />
                </td>
                <td className="border-b border-linea px-4 py-3">
                  <InsigniaEstado estado={c.estado} />
                </td>
                <td className="border-b border-linea px-4 py-3 text-right whitespace-nowrap text-gris tabular-nums">
                  {fecha(c.actualizado)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function Paginador({
  pagina,
  paginas,
  total,
  porPagina,
  onCambio,
}: {
  pagina: number;
  paginas: number;
  total: number;
  porPagina: number;
  onCambio: (p: number) => void;
}) {
  if (paginas <= 1) return null;
  const primero = (pagina - 1) * porPagina + 1;
  const ultimo = Math.min(pagina * porPagina, total);
  return (
    <nav aria-label="Páginas del directorio" className="flex flex-wrap items-center justify-between gap-3 border-t border-linea pt-5">
      <span className="t-meta text-gris">
        {primero.toLocaleString("es-CO")}–{ultimo.toLocaleString("es-CO")} de {total.toLocaleString("es-CO")}
      </span>
      <div className="flex items-center gap-3">
        <BotonFantasma
          compacto
          disabled={pagina <= 1}
          onClick={() => onCambio(pagina - 1)}
          icono={<ArrowLeft size={16} strokeWidth={1.5} aria-hidden />}
        >
          Anterior
        </BotonFantasma>
        <span className="t-meta text-gris">
          {pagina} / {paginas}
        </span>
        <BotonFantasma compacto disabled={pagina >= paginas} onClick={() => onCambio(pagina + 1)} flecha>
          Siguiente
        </BotonFantasma>
      </div>
    </nav>
  );
}

/* ── importación masiva ──────────────────────────────────────────────── */
function DialogoImportar({ onCerrar, onListo }: { onCerrar: () => void; onListo: () => void }) {
  const { abrir } = usePuerta();
  const [archivo, setArchivo] = useState<File | null>(null);
  const [actualizar, setActualizar] = useState(true);
  const [informe, setInforme] = useState<InformeImportacionClientes | null>(null);
  const [trabajando, setTrabajando] = useState(false);
  const [error, setError] = useState("");
  const entrada = useRef<HTMLInputElement>(null);

  const ejecutar = async (soloRevisar: boolean) => {
    if (!archivo) return;
    setTrabajando(true);
    setError("");
    try {
      setInforme(
        await api.importar(archivo, { actualizar_existentes: actualizar, solo_revisar: soloRevisar }),
      );
    } catch (e) {
      setError((e as Error).message);
      setInforme(null);
    } finally {
      setTrabajando(false);
    }
  };

  const yaEscribio = informe && !informe.solo_revisar && !!informe.columnas_reconocidas.length;
  // Se leyó el archivo pero no tenía las dos columnas: no es un directorio.
  const noEsUnDirectorio = !!informe && informe.columnas_reconocidas.length === 0;

  return (
    <Dialogo
      rotulo="Carga masiva"
      titulo="Importar clientes desde un archivo"
      onCerrar={onCerrar}
      pie={
        <>
          <Boton variante="fantasma" onClick={onCerrar}>
            {yaEscribio ? "Cerrar" : "Cancelar"}
          </Boton>
          {!yaEscribio && (
            <>
              <Boton
                variante="contorno"
                disabled={!archivo}
                cargando={trabajando}
                onClick={() => ejecutar(true)}
              >
                Revisar sin guardar
              </Boton>
              <Boton variante="lima" disabled={!archivo} cargando={trabajando} onClick={() => ejecutar(false)}>
                Importar de verdad
              </Boton>
            </>
          )}
          {yaEscribio && (
            <Boton variante="lima" onClick={onListo}>
              Ver el directorio
            </Boton>
          )}
        </>
      }
    >
      <div className="space-y-5">
        <p className="text-sm text-grafito">
          Acepta <strong className="text-tinta">.xlsx</strong>, <strong className="text-tinta">.xls</strong> y{" "}
          <strong className="text-tinta">.csv</strong>. Solo hacen falta dos columnas:{" "}
          <strong className="text-tinta">NIT</strong> y <strong className="text-tinta">RAZÓN SOCIAL</strong>; las
          demás se reconocen solas si están. Siempre puede revisar primero sin guardar nada.
        </p>

        <a
          href={descargas.plantillaClientes}
          className="inline-flex items-center gap-2 text-sm text-tinta underline underline-offset-4"
        >
          Descargar plantilla de ejemplo (CSV)
        </a>

        <div
          onClick={() => entrada.current?.click()}
          onDragOver={(e) => e.preventDefault()}
          onDrop={(e) => {
            e.preventDefault();
            const f = e.dataTransfer.files?.[0];
            if (f) {
              setArchivo(f);
              setInforme(null);
            }
          }}
          className="cursor-pointer rounded-2xl border-2 border-dashed border-linea bg-hoja/50 px-6 py-8 text-center transition hover:border-tinta"
        >
          <input
            ref={entrada}
            type="file"
            accept=".xlsx,.xls,.csv,.txt"
            className="hidden"
            onChange={(e) => {
              const f = e.target.files?.[0];
              if (f) {
                setArchivo(f);
                setInforme(null);
              }
            }}
          />
          {archivo ? (
            <>
              <p className="font-medium text-tinta">{archivo.name}</p>
              <Rotulo className="mt-1.5 block">
                {(archivo.size / 1024).toLocaleString("es-CO", { maximumFractionDigits: 0 })} KB · toque para
                cambiar
              </Rotulo>
            </>
          ) : (
            <>
              <p className="font-medium text-tinta">Suelte el archivo aquí o toque para elegirlo</p>
              <Rotulo className="mt-1.5 block">Máximo 40 MB</Rotulo>
            </>
          )}
        </div>

        <label className="flex items-center gap-2.5 text-sm text-tinta">
          <input
            type="checkbox"
            checked={actualizar}
            onChange={(e) => setActualizar(e.target.checked)}
            className="h-4 w-4 accent-[var(--tinta)]"
          />
          Actualizar los clientes que ya existan (se identifican por el NIT)
        </label>

        {error && <Aviso tono="rojo" titulo="No se pudo importar">{error}</Aviso>}

        {/* «No se encontraron las columnas obligatorias NIT y RAZÓN SOCIAL»
            casi nunca significa que el archivo esté mal: significa que es la
            contabilidad de UN cliente y entró por la puerta del directorio.
            Ese mensaje era el final del camino; ahora es una bifurcación, y
            el archivo no hay que volver a subirlo. */}
        {noEsUnDirectorio && archivo && (
          <Aviso tono="ambar" titulo="Esto no parece una lista de clientes">
            <p>
              No encontré columnas de NIT y razón social, así que no puedo darlos de alta en bloque. Pero el
              archivo puede estar perfectamente bien: si es la contabilidad de un cliente, la proceso ahora
              mismo sin que la vuelva a subir.
            </p>
            <p className="mt-3">
              <Boton
                variante="contorno"
                onClick={() => {
                  const f = archivo;
                  onCerrar();
                  abrir([f]);
                }}
              >
                Ver qué trae este archivo
              </Boton>
            </p>
          </Aviso>
        )}

        {informe && !noEsUnDirectorio && <ResumenImportacion informe={informe} />}
      </div>
    </Dialogo>
  );
}

function ResumenImportacion({ informe }: { informe: InformeImportacionClientes }) {
  return (
    <div className="space-y-4 rounded-2xl border border-linea bg-hoja/40 p-4">
      <div>
        <Insignia tono={informe.solo_revisar ? "azul" : "verde"}>
          {informe.solo_revisar ? "Simulacro · no se guardó nada" : "Importación realizada"}
        </Insignia>
        <p className="mt-2 text-sm font-medium text-tinta">{informe.mensaje}</p>
      </div>

      <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
        {[
          ["Filas leídas", informe.filas_leidas],
          ["Nuevos", informe.insertados],
          ["Actualizados", informe.actualizados],
          ["Rechazados", informe.rechazados],
        ].map(([r, v]) => (
          <div key={r as string} className="rounded-xl border border-linea bg-papel px-3 py-2.5">
            <Rotulo>{r}</Rotulo>
            <p className="cifras mt-1 text-xl font-bold">{Number(v).toLocaleString("es-CO")}</p>
          </div>
        ))}
      </div>

      {informe.columnas_reconocidas.length > 0 && (
        <div>
          <Rotulo className="block">Columnas reconocidas</Rotulo>
          <p className="mt-1 text-xs text-grafito">{informe.columnas_reconocidas.join(" · ")}</p>
        </div>
      )}

      {informe.rechazos.length > 0 && (
        <div>
          <Rotulo className="block">
            Filas rechazadas{informe.rechazos_omitidos > 0 && ` (se muestran las primeras ${informe.rechazos.length})`}
          </Rotulo>
          <ul className="mt-2 max-h-56 space-y-1.5 overflow-y-auto">
            {informe.rechazos.map((r, i) => (
              <li key={i} className="rounded-lg bg-rojo-suave px-3 py-2 text-xs text-rojo">
                <strong className="cifras">Fila {r.fila}</strong>
                {r.razon_social && <> · {r.razon_social}</>} — {r.motivo}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
