import { ChevronLeft, ChevronRight, Download, MoreHorizontal, PenLine, Upload } from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { useLocation, useNavigate, useSearchParams } from "react-router-dom";
import { analisis, descargas, trabajo as apiTrabajo, ErrorApi } from "../api";
import { clases, periodoCorto } from "../formato";
import type { Cliente, Importacion, Peticion, Periodo, Resultado } from "../tipos";
import { InsigniaEstado, useAvisos } from "../ui";
import { VistaPrevia } from "../paginas/VistaPrevia";
import { EditorDatos } from "./EditorDatos";
import { SubirPeriodo } from "./SubirPeriodo";
import { Aviso, Boton, Cargando, Dialogo, estiloCampo } from "./ui";
import { GRUPOS_VISTA, VISTAS, VISTA_INICIAL, VistaContable, type VistaId } from "./VistaContable";

/**
 * Contabilidad del cliente (v2.3 · Fase 3): Clientes y Trabajar en un solo lugar.
 *
 * - Sin periodos, o al pulsar «Subir otro periodo»: zona de subida → preguntas.
 * - Con periodos: el último abierto, con el selector «‹ Enero 2025 ▾ ›» pegajoso.
 *   Cambiar de mes conserva el informe que se está mirando y la posición en la
 *   página (`?periodo=AAAA-MM&vista=…`).
 * - Un solo botón principal: «Cerrar periodo». Descargas y lo demás, en menús.
 */

type Fase = "ver" | "subir" | "revisar";

/** El mes con que se nombra el periodo en la dirección: «2025-01». */
const clavePeriodo = (p: Periodo) => p.desde.slice(0, 7);

/** Nombres que usaban las pestañas antiguas, por si llega un enlace viejo. */
const VISTA_ANTIGUA: Record<string, VistaId> = {
  estados: "situacion",
  resumen: "situacion",
  notas: "situacion",
  indicadores: "resultados",
  trabajo: "hoja",
  mayorbal: "mayor",
  auditoria: "alertas",
  movimientos: "diario",
};

export function leerVista(v: string | null): VistaId {
  if (!v) return VISTA_INICIAL;
  if ((VISTAS as string[]).includes(v)) return v as VistaId;
  return VISTA_ANTIGUA[v] ?? VISTA_INICIAL;
}

interface SesionViva {
  periodoId: string;
  peticion: Peticion;
}

export function Contabilidad({
  cliente,
  periodos,
  onCambio,
}: {
  cliente: Cliente;
  periodos: Periodo[];
  onCambio: () => Promise<void>;
}) {
  const [params, setParams] = useSearchParams();
  const ubicacion = useLocation();
  const navegar = useNavigate();
  const avisar = useAvisos();

  // Del más viejo al más reciente: «‹» va hacia atrás en el tiempo.
  const calculados = useMemo(
    () => periodos.filter((p) => p.estado !== "borrador").sort((a, b) => a.desde.localeCompare(b.desde)),
    [periodos],
  );
  const pedido = params.get("periodo");
  const periodo = calculados.find((p) => clavePeriodo(p) === pedido) ?? calculados[calculados.length - 1] ?? null;
  const vista = leerVista(params.get("vista"));

  const [fase, setFase] = useState<Fase>(calculados.length ? "ver" : "subir");
  const [importacion, setImportacion] = useState<Importacion | null>(null);
  const [peticionPrevia, setPeticionPrevia] = useState<Peticion | null>(null);
  const [calculando, setCalculando] = useState(false);
  const [error, setError] = useState("");
  const [cerradoAntes, setCerradoAntes] = useState<{ mensaje: string; periodoId: string; peticion: Peticion } | null>(null);
  const [procesados, setProcesados] = useState<Resultado["periodos_procesados"]>(undefined);
  // La sesión de trabajo del último cálculo: con ella los ajustes se pueden cambiar y recalcular.
  const [sesion, setSesion] = useState<SesionViva | null>(null);

  /* Resultados ya abiertos: cambiar de mes y volver no los pide de nuevo. Se
     sigue mostrando el anterior mientras llega el nuevo, así la página no
     salta y el contador no pierde el sitio donde estaba leyendo. */
  const cache = useRef(new Map<string, Resultado>());
  const [datos, setDatos] = useState<{ periodoId: string; res: Resultado } | null>(null);
  const [cargando, setCargando] = useState(false);
  const [errorCarga, setErrorCarga] = useState("");
  // Sube cada vez que el editor guarda: el informe se vuelve a pedir con las cifras nuevas.
  const [recarga, setRecarga] = useState(0);

  const cambiar = useCallback(
    (cambios: Record<string, string | null>, reemplazar = false) => {
      const n = new URLSearchParams(params);
      Object.entries(cambios).forEach(([k, v]) => (v === null ? n.delete(k) : n.set(k, v)));
      setParams(n, { replace: reemplazar, preventScrollReset: true });
    },
    [params, setParams],
  );

  /* La puerta única deja aquí el archivo ya leído: se pasa directo a las preguntas. */
  useEffect(() => {
    const traida = (ubicacion.state as { importacion?: Importacion } | null)?.importacion;
    if (!traida) return;
    setImportacion(traida);
    setPeticionPrevia(null);
    setFase("revisar");
    navegar(`${ubicacion.pathname}${ubicacion.search}`, { replace: true, state: null });
  }, [ubicacion, navegar]);

  /* Desde el Tablero: «Responder las preguntas del archivo» (?sesion=). */
  const sesionEnRuta = params.get("sesion") ?? "";
  useEffect(() => {
    if (!sesionEnRuta) return;
    apiTrabajo
      .verImportacion(sesionEnRuta)
      .then((imp) => {
        setImportacion(imp);
        setPeticionPrevia(null);
        setFase("revisar");
      })
      .catch(() => setError("La subida con preguntas pendientes ya caducó (dura 8 horas). Vuelva a subir el archivo."))
      .finally(() => cambiar({ sesion: null }, true));
    // Solo al entrar con ?sesion=
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sesionEnRuta]);

  /* Sin periodos no hay nada que ver: se ofrece subir. */
  useEffect(() => {
    if (!calculados.length && fase === "ver") setFase("subir");
  }, [calculados.length, fase]);

  const periodoId = periodo?.id ?? "";
  useEffect(() => {
    if (!periodoId) return;
    const guardado = cache.current.get(periodoId);
    if (guardado) {
      setDatos({ periodoId, res: guardado });
      return;
    }
    let vivo = true;
    setCargando(true);
    setErrorCarga("");
    analisis
      .resultadoDePeriodo(periodoId)
      .then((r) => {
        cache.current.set(periodoId, r.resultado);
        if (vivo) setDatos({ periodoId, res: r.resultado });
      })
      .catch((e) => vivo && setErrorCarga((e as Error).message))
      .finally(() => vivo && setCargando(false));
    return () => {
      vivo = false;
    };
  }, [periodoId, recarga]);

  const calcular = useCallback(
    async (p: Peticion) => {
      setCalculando(true);
      setError("");
      try {
        const r = await apiTrabajo.calcular({ ...p, cliente_id: cliente.id });
        if (r.guardado === false || !r.periodo) {
          setError(r.aviso_guardado || "El cálculo salió bien pero no se pudo guardar. Intente de nuevo.");
          return;
        }
        cache.current.set(r.periodo.id, r);
        setDatos({ periodoId: r.periodo.id, res: r });
        setSesion({ periodoId: r.periodo.id, peticion: p });
        setPeticionPrevia(p);
        // Solo cuentan los periodos que quedaron guardados (los meses sin movimientos no).
        setProcesados(r.periodos_procesados?.filter((x) => x.periodo_id));
        await onCambio();
        setFase("ver");
        cambiar({ periodo: r.periodo.desde.slice(0, 7) });
        window.scrollTo({ top: 0, behavior: "smooth" });
      } catch (e) {
        const err = e as ErrorApi;
        if (err.codigo === "periodo_cerrado") {
          setCerradoAntes({ mensaje: err.message, periodoId: String(err.datos.periodo_id ?? ""), peticion: p });
        } else {
          setError(err.message);
        }
      } finally {
        setCalculando(false);
      }
    },
    [cliente.id, onCambio, cambiar],
  );

  const avisos = (
    <>
      {error && (
        <Aviso tono="rojo" titulo="No se pudo calcular" onCerrar={() => setError("")}>
          {error}
        </Aviso>
      )}
      {cerradoAntes && (
        <ReabrirYRecalcular
          info={cerradoAntes}
          onListo={() => setCerradoAntes(null)}
          onRecalcular={calcular}
          onError={setError}
        />
      )}
    </>
  );

  if (fase === "subir") {
    return (
      <div className="space-y-6">
        {avisos}
        {calculados.length > 0 && (
          <Boton variante="fantasma" tamano="sm" onClick={() => setFase("ver")}>
            <ChevronLeft size={16} strokeWidth={1.5} aria-hidden /> Volver a los periodos
          </Boton>
        )}
        <SubirPeriodo />
      </div>
    );
  }

  if (fase === "revisar" && importacion) {
    return (
      <div className="space-y-6">
        {avisos}
        <VistaPrevia
          key={importacion.sesion_id}
          datos={importacion}
          peticionPrevia={peticionPrevia}
          calculando={calculando}
          onCalcular={calcular}
          onVolver={() => setFase(calculados.length ? "ver" : "subir")}
        />
      </div>
    );
  }

  if (!periodo) return <Cargando texto="Abriendo la contabilidad" />;

  const indice = calculados.indexOf(periodo);
  const anterior = calculados[indice - 1];
  const siguiente = calculados[indice + 1];
  const res = datos?.periodoId === periodo.id ? datos.res : datos?.res ?? null;
  const conSesion = sesion?.periodoId === periodo.id;

  return (
    <div className="space-y-6">
      {avisos}

      {procesados && procesados.length > 1 && (
        <Aviso tono="azul" titulo={`Se procesaron ${procesados.length} periodos`} onCerrar={() => setProcesados(undefined)}>
          {procesados.filter((p) => p.estado === "cerrado").length} quedaron cerrados y el último está abierto para que
          lo revise. Use las flechas para pasar de uno a otro.
        </Aviso>
      )}

      {/* ── barra pegajosa: periodo, estado y el botón principal ───────── */}
      <div className="no-imprimir sticky top-[68px] z-20 escritorio:top-[80px]">
        <div className="material-cristal flex flex-wrap items-center gap-2 rounded-hoja px-2 py-2 sm:gap-3 sm:px-3">
          {/* En el celular el mes va en su propia fila: antes el selector quedaba de 30 px y sin texto. */}
          <div className="flex min-w-0 flex-1 basis-full items-center gap-1 sm:flex-none sm:basis-auto">
            <Boton
              variante="fantasma"
              tamano="sm"
              aria-label="Periodo anterior"
              disabled={!anterior}
              onClick={() => anterior && cambiar({ periodo: clavePeriodo(anterior) })}
            >
              <ChevronLeft size={18} strokeWidth={1.5} aria-hidden />
            </Boton>
            <select
              aria-label="Periodo"
              value={periodo.id}
              onChange={(e) => {
                const p = calculados.find((x) => x.id === e.target.value);
                if (p) cambiar({ periodo: clavePeriodo(p) });
              }}
              className={clases(estiloCampo, "h-10 min-w-0 flex-1 font-semibold sm:w-auto sm:flex-none sm:min-w-[10rem]")}
            >
              {[...calculados].reverse().map((p) => (
                <option key={p.id} value={p.id}>
                  {periodoCorto(p.desde, p.hasta)}
                  {p.estado === "cerrado" ? " · cerrado" : ""}
                </option>
              ))}
            </select>
            <Boton
              variante="fantasma"
              tamano="sm"
              aria-label="Periodo siguiente"
              disabled={!siguiente}
              onClick={() => siguiente && cambiar({ periodo: clavePeriodo(siguiente) })}
            >
              <ChevronRight size={18} strokeWidth={1.5} aria-hidden />
            </Boton>
          </div>

          {/* El estado ya va en el selector («· cerrado»); aquí solo lo que pide atención. */}
          {!periodo.cuadra && <InsigniaEstado estado="descuadre" discreta>No cuadra</InsigniaEstado>}
          {cargando && <span className="t-small text-gris" role="status">Abriendo…</span>}

          <div className="ml-auto flex flex-wrap items-center gap-2">
            {vista !== "datos" && (
              <Boton variante="fantasma" tamano="sm" onClick={() => cambiar({ vista: "datos" })} aria-label="Editar los datos del periodo">
                <PenLine size={16} strokeWidth={1.5} aria-hidden />
                <span className="hidden sm:inline">Editar datos</span>
              </Boton>
            )}
            <Boton variante="fantasma" tamano="sm" onClick={() => setFase("subir")} aria-label="Subir archivos de otro periodo">
              <Upload size={16} strokeWidth={1.5} aria-hidden />
              <span className="hidden sm:inline">Subir archivos</span>
            </Boton>
            <MenuDescargas periodoId={periodo.id} />
            <MenuMas
              periodo={periodo}
              onCambio={async () => {
                cache.current.delete(periodo.id);
                await onCambio();
              }}
              onEliminado={async () => {
                cache.current.delete(periodo.id);
                cambiar({ periodo: null });
                await onCambio();
              }}
            />
            {periodo.estado !== "cerrado" && res && (
              <BotonCerrar
                periodo={periodo}
                res={res}
                onCerrado={async () => {
                  avisar(`${periodoCorto(periodo.desde, periodo.hasta)} quedó cerrado; sus saldos abren el siguiente.`);
                  await onCambio();
                }}
              />
            )}
          </div>
        </div>
      </div>

      {periodo.nota && (
        <Aviso tono="ambar" titulo="Nota de revisión">
          {periodo.nota}
        </Aviso>
      )}
      {errorCarga && <Aviso tono="rojo" titulo="No se pudo abrir el periodo">{errorCarga}</Aviso>}

      {/* ── lista agrupada de informes + el informe ──────────────────── */}
      {/* Al editar los datos, la tabla usa todo el ancho; «Ver los informes» vuelve a la lista. */}
      <div className={clases("grid gap-6", vista !== "datos" && "escritorio:grid-cols-[220px_minmax(0,1fr)]")}>
        {vista !== "datos" && <ListaVistas vista={vista} onVista={(v) => cambiar({ vista: v })} />}
        <div className="min-w-0">
          {vista === "datos" ? (
            <EditorDatos
              key={periodo.id}
              periodoId={periodo.id}
              onVolver={() => cambiar({ vista: VISTA_INICIAL })}
              onGuardado={async () => {
                cache.current.delete(periodo.id);
                setRecarga((n) => n + 1);
                await onCambio();
              }}
            />
          ) : (<>
          {!res && !errorCarga && <Cargando texto="Abriendo el periodo" />}
          {res && (
            <VistaContable
              key={`${periodo.id}:${vista}`}
              res={res}
              vista={vista}
              periodoId={periodo.id}
              sesion={
                conSesion && sesion
                  ? { peticion: sesion.peticion, calculando, onRecalcular: calcular }
                  : null
              }
            />
          )}
          </>)}
        </div>
      </div>
    </div>
  );
}

/* ── lista lateral agrupada (en el celular, un selector) ─────────────── */
function ListaVistas({ vista, onVista }: { vista: VistaId; onVista: (v: VistaId) => void }) {
  return (
    <>
      <label className="block escritorio:hidden">
        <span className="t-meta mb-1 block text-gris">Informe</span>
        <select
          value={vista}
          onChange={(e) => onVista(e.target.value as VistaId)}
          className={estiloCampo}
          aria-label="Informe del periodo"
        >
          {GRUPOS_VISTA.map((g) => (
            <optgroup key={g.titulo} label={g.titulo}>
              {g.vistas.map((v) => (
                <option key={v.id} value={v.id}>{v.texto}</option>
              ))}
            </optgroup>
          ))}
        </select>
      </label>
      <nav aria-label="Informes del periodo" className="hidden escritorio:block">
        <div className="sticky top-[150px] space-y-5">
          {GRUPOS_VISTA.map((g) => (
            <div key={g.titulo}>
              <p className="t-meta text-gris">{g.titulo}</p>
              <ul className="mt-1.5 space-y-0.5">
                {g.vistas.map((v) => (
                  <li key={v.id}>
                    <button
                      type="button"
                      onClick={() => onVista(v.id)}
                      aria-current={v.id === vista ? "page" : undefined}
                      className={clases(
                        "t-small w-full rounded-[10px] px-3 py-1.5 text-left transition-colors duration-150",
                        v.id === vista ? "bg-tinta text-sobre-tinta" : "text-grafito hover:bg-hoja-2 hover:text-tinta",
                      )}
                    >
                      {v.texto}
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </nav>
    </>
  );
}

/* ── menú desplegable sencillo ───────────────────────────────────────── */
function Menu({ rotulo, boton, children }: { rotulo: string; boton: ReactNode; children: (cerrar: () => void) => ReactNode }) {
  const [abierto, setAbierto] = useState(false);
  const caja = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!abierto) return;
    const fuera = (e: MouseEvent) => !caja.current?.contains(e.target as Node) && setAbierto(false);
    const tecla = (e: KeyboardEvent) => e.key === "Escape" && setAbierto(false);
    document.addEventListener("mousedown", fuera);
    document.addEventListener("keydown", tecla);
    return () => {
      document.removeEventListener("mousedown", fuera);
      document.removeEventListener("keydown", tecla);
    };
  }, [abierto]);
  return (
    <div ref={caja} className="relative">
      <Boton variante="contorno" tamano="sm" aria-haspopup="menu" aria-expanded={abierto} aria-label={rotulo} onClick={() => setAbierto(!abierto)}>
        {boton}
      </Boton>
      {abierto && (
        <div role="menu" className="material-hoja absolute right-0 z-30 mt-2 min-w-[240px] p-1.5 shadow-expediente">
          {children(() => setAbierto(false))}
        </div>
      )}
    </div>
  );
}

const estiloOpcion =
  "t-body flex w-full items-center gap-2 rounded-[10px] px-3 py-2 text-left text-tinta transition-colors hover:bg-hoja-2";

function MenuDescargas({ periodoId }: { periodoId: string }) {
  return (
    <Menu rotulo="Descargar" boton={<><Download size={16} strokeWidth={1.5} aria-hidden /><span className="hidden sm:inline">Descargar</span></>}>
      {(cerrar) => (
        <>
          <a role="menuitem" href={descargas.pdfPeriodo(periodoId)} onClick={cerrar} className={estiloOpcion}>PDF para firmar</a>
          <a role="menuitem" href={descargas.excelPeriodo(periodoId)} onClick={cerrar} className={estiloOpcion}>Excel completo</a>
          <a role="menuitem" href={descargas.saldosPeriodo(periodoId)} onClick={cerrar} className={estiloOpcion}>Saldos para el periodo siguiente</a>
        </>
      )}
    </Menu>
  );
}

function MenuMas({
  periodo,
  onCambio,
  onEliminado,
}: {
  periodo: Periodo;
  onCambio: () => Promise<void>;
  onEliminado: () => Promise<void>;
}) {
  const avisar = useAvisos();
  const [dialogo, setDialogo] = useState<"nota" | "eliminar" | null>(null);
  const [nota, setNota] = useState(periodo.nota ?? "");
  const [trabajando, setTrabajando] = useState(false);
  const nombre = periodoCorto(periodo.desde, periodo.hasta);

  const hacer = async (fn: () => Promise<unknown>, mensaje: string, despues: () => Promise<void> = onCambio) => {
    setTrabajando(true);
    try {
      await fn();
      avisar(mensaje);
      setDialogo(null);
      await despues();
    } catch (e) {
      avisar((e as Error).message, "rojo");
    } finally {
      setTrabajando(false);
    }
  };

  return (
    <>
      <Menu rotulo="Más acciones del periodo" boton={<MoreHorizontal size={18} strokeWidth={1.5} aria-hidden />}>
        {(cerrar) => (
          <>
            <button type="button" role="menuitem" className={estiloOpcion} onClick={() => { cerrar(); setNota(periodo.nota ?? ""); setDialogo("nota"); }}>
              {periodo.nota ? "Editar la nota de revisión" : "Agregar nota de revisión"}
            </button>
            {periodo.estado === "cerrado" ? (
              <button
                type="button"
                role="menuitem"
                className={estiloOpcion}
                onClick={() => { cerrar(); hacer(() => analisis.reabrirPeriodo(periodo.id), `${nombre} quedó abierto de nuevo.`); }}
              >
                Reabrir el periodo
              </button>
            ) : (
              <button type="button" role="menuitem" className={clases(estiloOpcion, "text-rojo")} onClick={() => { cerrar(); setDialogo("eliminar"); }}>
                Eliminar el periodo
              </button>
            )}
          </>
        )}
      </Menu>

      {dialogo === "nota" && (
        <Dialogo
          rotulo={nombre}
          titulo="Nota de revisión"
          onCerrar={() => setDialogo(null)}
          ancho="max-w-lg"
          pie={
            <>
              <Boton variante="fantasma" onClick={() => setDialogo(null)}>Cancelar</Boton>
              <Boton variante="solido" cargando={trabajando} onClick={() => hacer(() => analisis.notaPeriodo(periodo.id, nota.trim()), "Nota guardada.")}>
                Guardar
              </Boton>
            </>
          }
        >
          <textarea
            value={nota}
            onChange={(e) => setNota(e.target.value)}
            rows={4}
            aria-label="Nota de revisión"
            className={clases(estiloCampo, "h-auto py-3")}
            placeholder="Lo que hay que revisar de este periodo"
          />
        </Dialogo>
      )}

      {dialogo === "eliminar" && (
        <Dialogo
          rotulo="No se puede deshacer"
          titulo={`Eliminar ${nombre}`}
          onCerrar={() => setDialogo(null)}
          ancho="max-w-lg"
          pie={
            <>
              <Boton variante="fantasma" onClick={() => setDialogo(null)}>Cancelar</Boton>
              <Boton
                variante="peligro"
                cargando={trabajando}
                onClick={() => hacer(() => analisis.eliminarPeriodo(periodo.id), `${nombre} se eliminó.`, onEliminado)}
              >
                Eliminar el periodo
              </Boton>
            </>
          }
        >
          <p className="t-body text-grafito">
            Se borran el cálculo, los estados financieros y los movimientos de {nombre}. Los demás periodos no se tocan.
          </p>
        </Dialogo>
      )}
    </>
  );
}

/* ── el botón principal: cerrar el periodo ───────────────────────────── */
function BotonCerrar({ periodo, res, onCerrado }: { periodo: Periodo; res: Resultado; onCerrado: () => Promise<void> }) {
  const [trabajando, setTrabajando] = useState(false);
  const [confirmar, setConfirmar] = useState(false);
  const avisar = useAvisos();
  // A4: la causación de nómina aceptada con sueldos que ya estaban en el diario.
  const dobleNomina = res.alertas.find((a) => a.codigo === "DOBLE-NOMINA");

  const cerrar = async () => {
    setTrabajando(true);
    try {
      await analisis.cerrarPeriodo(periodo.id);
      setConfirmar(false);
      await onCerrado();
    } catch (e) {
      avisar((e as Error).message, "rojo");
    } finally {
      setTrabajando(false);
    }
  };

  return (
    <>
      <Boton variante="lima" tamano="sm" cargando={trabajando && !confirmar} onClick={() => (dobleNomina || !periodo.cuadra ? setConfirmar(true) : cerrar())}>
        Cerrar periodo
      </Boton>
      {confirmar && (
        <Dialogo
          rotulo={periodoCorto(periodo.desde, periodo.hasta)}
          titulo="Antes de cerrar"
          onCerrar={() => setConfirmar(false)}
          ancho="max-w-lg"
          pie={
            <>
              <Boton variante="fantasma" onClick={() => setConfirmar(false)}>Revisar primero</Boton>
              <Boton variante="solido" cargando={trabajando} onClick={cerrar}>Cerrar de todos modos</Boton>
            </>
          }
        >
          <div className="space-y-3">
            {dobleNomina && <Aviso tono="ambar" titulo="Nómina posiblemente doble">{dobleNomina.mensaje}</Aviso>}
            {!periodo.cuadra && (
              <Aviso tono="rojo" titulo="El periodo no cuadra">
                Activo no es igual a pasivo más patrimonio. Revise los ajustes antes de cerrar.
              </Aviso>
            )}
          </div>
        </Dialogo>
      )}
    </>
  );
}

/* ── el periodo que se quiso recalcular estaba cerrado ───────────────── */
function ReabrirYRecalcular({
  info,
  onListo,
  onRecalcular,
  onError,
}: {
  info: { mensaje: string; periodoId: string; peticion: Peticion };
  onListo: () => void;
  onRecalcular: (p: Peticion) => Promise<void>;
  onError: (m: string) => void;
}) {
  const [trabajando, setTrabajando] = useState(false);
  return (
    <Aviso tono="ambar" titulo="Ese periodo ya está cerrado">
      <p>{info.mensaje}</p>
      <p className="t-small mt-2">Si lo reabre, el cierre actual queda guardado en el historial del periodo.</p>
      <div className="mt-4 flex flex-wrap gap-3">
        <Boton
          variante="solido"
          tamano="sm"
          cargando={trabajando}
          onClick={async () => {
            setTrabajando(true);
            try {
              await analisis.reabrirPeriodo(info.periodoId);
              onListo();
              await onRecalcular(info.peticion);
            } catch (e) {
              onError((e as Error).message);
            } finally {
              setTrabajando(false);
            }
          }}
        >
          Reabrir y recalcular
        </Boton>
        <Boton variante="fantasma" tamano="sm" onClick={onListo}>Dejarlo como está</Boton>
      </div>
    </Aviso>
  );
}
