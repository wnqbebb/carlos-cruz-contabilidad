import { ArrowLeft, Download, History, PenLine } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";
import { analisis, clientes as api, descargas, trabajo as apiTrabajo } from "../api";
import { useMetaPagina } from "../componentes/Marco";
import { BotonSubirArchivo } from "../componentes/Subir";
import { clases, esCero, esNegativo, fecha, fechaLarga, pesos, periodoCorto, restar } from "../formato";
import type {
  ArchivoImportado,
  Actividad as ActividadLinea,
  Cierre,
  Cliente,
  InformeSugerencias,
  Periodo,
  Resultado,
  Severidad,
  Sugerencia,
  VersionPeriodo,
} from "../tipos";
import { GraficaHistorico, TablaHistorico } from "../componentes/Grafica";
import { PanelMetricas } from "../componentes/PanelMetricas";
import { LibroDiario as LibroDiarioOficial } from "../componentes/LibroDiario";
import { ResultadoGuardado } from "../componentes/ResultadoGuardado";
import {
  Aviso,
  Boton,
  Cargando,
  Cifra,
  Dialogo,
  Dinero,
  Enlace,
  Insignia,
  Pestanas,
  Rotulo,
  Tabla,
  Tarjeta,
  Td,
  Th,
  Vacio,
  estiloCampo,
  type Tono,
} from "../componentes/ui";
import {
  BotonFantasma, BotonPrimario, CarpetaVacia, EnlaceSubrayado, EsferaCliente,
  EsqueletoFicha, EstadoError, InsigniaEstado, useAvisos,
} from "../ui";

/**
 * Ficha del cliente (spec 6.4).
 *
 * Cabecera Escaparate: esfera de 240 px que deriva, razón social en display y
 * metadatos en las esquinas como ref-04. Debajo, pestañas con índice:
 * Resumen⁰¹ Periodos⁰² Estados financieros⁰³ Inventario⁰⁴ Nómina⁰⁵ Socios⁰⁶,
 * y las dos que ya existían: Libro diario⁰⁷ y Datos⁰⁸.
 */

type Vista =
  | "resumen" | "periodos" | "estados" | "inventario" | "nomina"
  | "socios" | "movimientos" | "actividad" | "ficha";
const VISTAS: Vista[] = ["resumen", "periodos", "estados", "inventario", "nomina",
  "socios", "movimientos", "actividad", "ficha"];

const TONO: Record<Severidad, Tono> = {
  critica: "rojo",
  alta: "ambar",
  media: "neutro",
  informativa: "neutro",
};
const NOMBRE: Record<Severidad, string> = {
  critica: "Crítico",
  alta: "Importante",
  media: "Revisar",
  informativa: "Dato",
};

/** «2024-11-26» → «26 — 11 — 2024», como los metadatos de ref-04. */
const fechaEsquina = (iso: string | null | undefined) => {
  if (!iso) return "";
  const [a, m, d] = iso.slice(0, 10).split("-");
  return `${d} — ${m} — ${a}`;
};

export function ClienteFicha() {
  const { id = "" } = useParams<{ id: string }>();
  const navegar = useNavigate();

  const [cliente, setCliente] = useState<Cliente | null>(null);
  const [periodos, setPeriodos] = useState<Periodo[]>([]);
  const [cierres, setCierres] = useState<Cierre[]>([]);
  const [serie, setSerie] = useState<Periodo[]>([]);
  const [informe, setInforme] = useState<InformeSugerencias | null>(null);
  // `?vista=estados` permite llegar directo a una pestaña (p. ej. desde el Tablero).
  const [parametrosUrl] = useSearchParams();
  const [vista, setVista] = useState<Vista>(() => {
    const v = parametrosUrl.get("vista") as Vista | null;
    return v && VISTAS.includes(v) ? v : "resumen";
  });
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState("");
  const [confirmarBorrado, setConfirmarBorrado] = useState(false);

  const cargar = useCallback(async () => {
    setCargando(true);
    setError("");
    try {
      const [c, p, s, g] = await Promise.all([
        api.obtener(id),
        analisis.periodos(id),
        analisis.serie(id, 24),
        analisis.sugerencias(id).catch(() => null),
      ]);
      setCliente(c);
      setPeriodos(p.periodos);
      setCierres(p.cierres);
      setSerie(s.serie);
      setInforme(g);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setCargando(false);
    }
  }, [id]);

  useEffect(() => {
    cargar();
  }, [cargar]);

  const ultimo = serie.length ? serie[serie.length - 1] : null;
  useMetaPagina(ultimo ? `Corte ${fechaLarga(ultimo.hasta)}` : null);

  if (error && /no existe/i.test(error)) {
    // No es un fallo de conexión: el expediente no está (pudo haberse eliminado).
    return (
      <CarpetaVacia
        titulo="Ese expediente no existe"
        accion={<BotonPrimario a="/clientes" flecha>Ir al directorio</BotonPrimario>}
      >
        Puede que el cliente se haya eliminado o que el enlace esté incompleto.
      </CarpetaVacia>
    );
  }
  if (error) return <EstadoError titulo="No se pudo abrir el expediente" detalle={error} onReintentar={cargar} />;
  if (cargando) return <EsqueletoFicha />;
  if (!cliente) return null;

  const criticas = informe?.conteo.critica ?? 0;
  const altas = informe?.conteo.alta ?? 0;
  const calculados = periodos.filter((p) => p.estado !== "borrador").length;
  const socios = cliente.socios ?? [];

  return (
    <div className="space-y-12">
      <CabeceraCliente cliente={cliente} />

      {(criticas > 0 || altas > 0) && vista !== "resumen" && (
        <Aviso tono={criticas ? "rojo" : "ambar"}>
          Este cliente tiene {criticas + altas} {criticas + altas === 1 ? "asunto" : "asuntos"} por atender.{" "}
          <button type="button" onClick={() => setVista("resumen")} className="font-semibold underline underline-offset-4">
            Verlos en el resumen
          </button>
        </Aviso>
      )}

      <div className="space-y-8">
        <Pestanas<Vista>
          valor={vista}
          onCambio={setVista}
          opciones={[
            { id: "resumen", texto: "Resumen", cuenta: criticas + altas },
            { id: "periodos", texto: "Periodos", cuenta: periodos.length },
            { id: "estados", texto: "Estados financieros", cuenta: calculados },
            { id: "inventario", texto: "Inventario" },
            { id: "nomina", texto: "Nómina" },
            { id: "socios", texto: "Socios", cuenta: socios.length },
            { id: "movimientos", texto: "Libro diario" },
            { id: "actividad", texto: "Actividad" },
            { id: "ficha", texto: "Datos" },
          ]}
        />

        {/* ── 01 resumen ─────────────────────────────────────────────── */}
        {vista === "resumen" && (
          <div className="space-y-8">
            {ultimo ? (
              <div className="space-y-4">
                <div className="flex flex-wrap items-baseline justify-between gap-3">
                  <p className="t-body text-grafito">
                    Último periodo: <span className="font-semibold text-tinta">{periodoCorto(ultimo.desde, ultimo.hasta)}</span>
                    {" · "}
                    {ultimo.estado === "cerrado" ? "cerrado, listo para firmar" : "abierto"}
                  </p>
                  <EnlaceSubrayado href="#" onClick={(e) => { e.preventDefault(); setVista("estados"); }}>
                    Ver estados financieros y descargas
                  </EnlaceSubrayado>
                </div>
                <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 escritorio:grid-cols-4">
                  <Cifra rotulo={`Activo · ${periodoCorto(ultimo.desde, ultimo.hasta)}`} valor={pesos(ultimo.total_activo)} />
                  <Cifra rotulo="Pasivo total" valor={pesos(ultimo.total_pasivo)} />
                  <Cifra rotulo="Patrimonio" valor={pesos(ultimo.total_patrimonio)} />
                  <Cifra
                    rotulo={esNegativo(ultimo.utilidad) ? "Pérdida del periodo" : "Utilidad del periodo"}
                    valor={pesos(ultimo.utilidad)}
                    tono={esNegativo(ultimo.utilidad) ? "rojo" : undefined}
                    destacada={!esNegativo(ultimo.utilidad)}
                    detalle={ultimo.estado === "cerrado" ? "Periodo cerrado" : "Periodo abierto"}
                  />
                </div>
              </div>
            ) : (
              <Vacio
                titulo="Este cliente aún no tiene periodos"
                accion={<BotonPrimario a={`/trabajo?cliente=${id}`} flecha>Trabajar el primer periodo</BotonPrimario>}
              >
                Suba sus archivos contables y aquí quedan el balance, los estados financieros, la nómina y el inventario.
              </Vacio>
            )}

            {ultimo && <PanelMetricas cliente={cliente} periodo={ultimo} />}

            <ListaSugerencias informe={informe} />

            {serie.length >= 2 && (
              <Tarjeta rotulo="Evolución" titulo="Cómo viene el cliente">
                <GraficaHistorico serie={serie} />
                <details className="mt-6">
                  <summary className="t-meta cursor-pointer select-none text-gris">Ver los mismos datos en tabla</summary>
                  <div className="barra-fina mt-3 overflow-x-auto">
                    <TablaHistorico serie={serie} />
                  </div>
                </details>
              </Tarjeta>
            )}
          </div>
        )}

        {/* ── 02 periodos ────────────────────────────────────────────── */}
        {vista === "periodos" && <ListaPeriodos periodos={periodos} cierres={cierres} onCambio={cargar} />}

        {/* ── 03 estados financieros · 04 inventario · 05 nómina ─────── */}
        {vista === "estados" && <ResultadoGuardado periodos={periodos} excluir={["inventario", "nomina"]} />}
        {vista === "inventario" && <ResultadoGuardado periodos={periodos} grupos={["inventario"]} conPanel={false} />}
        {vista === "nomina" && <ResultadoGuardado periodos={periodos} grupos={["nomina"]} conPanel={false} />}

        {/* ── 06 socios ──────────────────────────────────────────────── */}
        {vista === "socios" && <Socios cliente={cliente} />}

        {/* ── 07 libro diario ────────────────────────────────────────── */}
        {vista === "movimientos" && <LibroDiarioFicha periodos={periodos} />}

        {/* ── 08 actividad ───────────────────────────────────────────── */}
        {vista === "actividad" && <Actividad clienteId={id} />}

        {/* ── 08 datos ───────────────────────────────────────────────── */}
        {vista === "ficha" && (
          <div className="space-y-8">
            <DatosCliente cliente={cliente} />
            <Tarjeta rotulo="Zona delicada" titulo="Archivar o eliminar este cliente">
              <p className="t-body text-grafito">
                Archivar lo saca de las listas pero conserva toda su contabilidad. Eliminar borra el cliente y{" "}
                <strong className="text-tinta">todos sus periodos, resultados y movimientos</strong>, y no se puede deshacer.
              </p>
              <div className="mt-5 flex flex-wrap gap-3">
                <Boton
                  variante="contorno"
                  onClick={async () => {
                    await api.archivar(id);
                    cargar();
                  }}
                >
                  Archivar
                </Boton>
                <Boton variante="peligro" onClick={() => setConfirmarBorrado(true)}>
                  Eliminar definitivamente
                </Boton>
              </div>
            </Tarjeta>
          </div>
        )}
      </div>

      {confirmarBorrado && (
        <DialogoBorrar
          cliente={cliente}
          periodos={periodos.length}
          onCerrar={() => setConfirmarBorrado(false)}
          onBorrado={() => navegar("/clientes", { replace: true })}
        />
      )}
    </div>
  );
}

/* ── cabecera Escaparate (ref-04: esfera + metadatos en las esquinas) ── */
function CabeceraCliente({ cliente }: { cliente: Cliente }) {
  const codigo = `${cliente.sigla || "Cliente"} — ${cliente.nit.slice(-3)}`;
  const desde = cliente.fecha_constitucion
    ? `Constituida ${fechaEsquina(cliente.fecha_constitucion)}`
    : `Ficha desde ${fechaEsquina(cliente.creado)}`;
  return (
    <header className="relative border-b border-linea pb-8">
      <div className="t-meta flex flex-wrap justify-between gap-3 text-gris">
        <span>{codigo}</span>
        <span>{cliente.turno_dian ? `Turno DIAN — ${String(cliente.turno_dian).padStart(2, "0")}` : "Sin turno DIAN"}</span>
      </div>

      <div className="mt-8 grid gap-10 escritorio:grid-cols-12 escritorio:items-center">
        <div className="min-w-0 escritorio:col-span-8">
          <EnlaceSubrayado a="/clientes">
            <ArrowLeft size={14} strokeWidth={1.5} aria-hidden /> Clientes
          </EnlaceSubrayado>
          <h1 className="t-display mt-5 text-balance text-tinta">{cliente.razon_social}</h1>
          <p className="mt-5 flex flex-wrap items-center gap-x-4 gap-y-2 text-grafito">
            {cliente.sigla && <span className="t-body font-semibold text-tinta">{cliente.sigla}</span>}
            <span className="codigo text-[13px]">NIT {cliente.nit_formateado}</span>
            {cliente.municipio && <span className="t-body">{cliente.municipio}</span>}
            <InsigniaEstado estado={cliente.estado} />
          </p>

          <dl className="mt-8 grid gap-x-8 gap-y-4 sm:grid-cols-2">
            {cliente.rep_legal && (
              <div className="min-w-0">
                <dt className="t-meta text-gris">Representante legal</dt>
                <dd className="t-body mt-1 text-tinta">{cliente.rep_legal}</dd>
              </div>
            )}
            {cliente.contador && (
              <div className="min-w-0">
                <dt className="t-meta text-gris">Contador</dt>
                <dd className="t-body mt-1 text-tinta">
                  {cliente.contador}
                  {cliente.contador_tp && <span className="codigo ml-2 text-[12px] text-gris">T.P. {cliente.contador_tp}</span>}
                </dd>
              </div>
            )}
          </dl>

          <div className="mt-8 flex flex-wrap gap-3">
            <BotonSubirArchivo />
            <BotonFantasma a={`/trabajo?cliente=${cliente.id}`} flecha>
              Trabajar un periodo
            </BotonFantasma>
            <BotonFantasma a={`/clientes/${cliente.id}/editar`} icono={<PenLine size={18} strokeWidth={1.5} aria-hidden />}>
              Editar ficha
            </BotonFantasma>
            <ArchivosDeMuestra cliente={cliente} />
          </div>
        </div>

        <div className="flex justify-center escritorio:col-span-4 escritorio:justify-end">
          <EsferaCliente nit={cliente.nit} nombre={cliente.razon_social} tamano={240} />
        </div>
      </div>

      <div className="t-meta mt-10 flex flex-wrap justify-between gap-3 text-gris">
        <span>{desde}</span>
        <span className="capitalize">Periodicidad — {cliente.periodicidad}</span>
      </div>
    </header>
  );
}

/* ── 06 socios ──────────────────────────────────────────────────────── */
function Socios({ cliente }: { cliente: Cliente }) {
  const socios = cliente.socios ?? [];
  if (!socios.length) {
    return (
      <Vacio
        titulo="Sin socios registrados"
        accion={<BotonFantasma a={`/clientes/${cliente.id}/editar`}>Registrar socios en la ficha</BotonFantasma>}
      >
        Con los socios y sus aportes, el sistema avisa si queda capital suscrito sin pagar.
      </Vacio>
    );
  }
  return (
    <Tarjeta
      rotulo="Composición"
      titulo={`${socios.length} ${socios.length === 1 ? "socio" : "socios"}`}
      subtitulo={`Capital suscrito ${pesos(cliente.capital_suscrito)} · valor nominal por acción ${pesos(cliente.valor_nominal_accion)}`}
      sinRelleno
    >
      <Tabla>
        <thead>
          <tr>
            <Th>Nombre</Th>
            <Th>Cédula</Th>
            <Th derecha>Comprometido</Th>
            <Th derecha>Pagado</Th>
            <Th derecha>Saldo</Th>
          </tr>
        </thead>
        <tbody>
          {socios.map((s, i) => {
            // Resta decimal exacta: con `Number(...)` el saldo podría salir con centavos fantasma.
            const saldo = restar(s.comprometido, s.pagado);
            return (
              <tr key={i} className="transition-colors duration-150 hover:bg-hoja-2">
                <Td className="text-tinta">{s.nombre}</Td>
                <Td className="codigo">{s.cedula || "—"}</Td>
                <Td derecha><Dinero valor={s.comprometido} /></Td>
                <Td derecha><Dinero valor={s.pagado} /></Td>
                <Td derecha className="font-semibold"><Dinero valor={saldo} /></Td>
              </tr>
            );
          })}
        </tbody>
      </Tabla>
    </Tarjeta>
  );
}

/* ── sugerencias ─────────────────────────────────────────────────────── */
function ListaSugerencias({ informe }: { informe: InformeSugerencias | null }) {
  if (!informe) return null;
  if (!informe.sugerencias.length) {
    return (
      <Tarjeta rotulo="Revisión" titulo="Todo en orden">
        <p className="text-sm text-grafito">
          No se encontró nada que corregir en los {informe.periodos_analizados} periodo(s) analizados.
        </p>
      </Tarjeta>
    );
  }
  return (
    <Tarjeta
      rotulo="Revisión automática"
      titulo={`${informe.sugerencias.length} cosa(s) por mirar`}
      subtitulo={`Analizados ${informe.periodos_analizados} periodo(s). Cada punto sale de un dato guardado.`}
      sinRelleno
    >
      <ul className="divide-y divide-linea">
        {informe.sugerencias.map((s) => (
          <FilaSugerencia key={s.codigo} sugerencia={s} />
        ))}
      </ul>
    </Tarjeta>
  );
}

function FilaSugerencia({ sugerencia }: { sugerencia: Sugerencia }) {
  return (
    <li className="px-4 py-4 sm:px-5">
      <div className="flex flex-wrap items-center gap-2">
        <Insignia tono={TONO[sugerencia.severidad]}>{NOMBRE[sugerencia.severidad]}</Insignia>
        <p className="font-medium text-tinta">{sugerencia.titulo}</p>
      </div>
      <p className="mt-1.5 text-sm text-grafito">{sugerencia.detalle}</p>
      <p className="mt-2 flex gap-2 text-sm text-tinta">
        <span aria-hidden className="text-gris">→</span>
        {sugerencia.accion}
      </p>
    </li>
  );
}

/* ── periodos ────────────────────────────────────────────────────────── */
function ListaPeriodos({
  periodos,
  cierres,
  onCambio,
}: {
  periodos: Periodo[];
  cierres: Cierre[];
  onCambio: () => void;
}) {
  const [trabajando, setTrabajando] = useState("");

  if (!periodos.length) {
    return (
      <Vacio titulo="Sin periodos todavía">
        Suba el primer archivo de este cliente desde «Trabajar un periodo» y aquí quedará su historia.
      </Vacio>
    );
  }

  const accion = async (fn: () => Promise<unknown>, id: string) => {
    setTrabajando(id);
    try {
      await fn();
      onCambio();
    } finally {
      setTrabajando("");
    }
  };

  return (
    <div className="space-y-4">
      <Tarjeta sinRelleno>
        <Tabla>
          <thead>
            <tr>
              <Th>Periodo</Th>
              <Th>Estado</Th>
              <Th derecha>Activo</Th>
              <Th derecha>Ingresos</Th>
              <Th derecha>Utilidad</Th>
              <Th derecha>Descuadre</Th>
              <Th derecha>Historial</Th>
              <Th derecha>Acciones</Th>
            </tr>
          </thead>
          <tbody>
            {periodos.map((p) => {
              // Se usa el booleano del servidor: comparar la cadena fallaba con "0.00".
              const descuadrado = p.cuadra === false;
              return (
                <tr key={p.id} className={clases("transition hover:bg-hoja", descuadrado && "bg-rojo-suave/40")}>
                  <Td>
                    <span className="font-medium">{periodoCorto(p.desde, p.hasta)}</span>
                    <Rotulo className="mt-0.5 block">
                      {fecha(p.desde)} – {fecha(p.hasta)} · {p.cuentas} cuentas
                    </Rotulo>
                  </Td>
                  <Td>
                    <Insignia tono={p.estado === "cerrado" ? "verde" : p.estado === "calculado" ? "ambar" : "neutro"}>
                      {p.estado}
                    </Insignia>
                  </Td>
                  <Td derecha><Dinero valor={p.total_activo} /></Td>
                  <Td derecha><Dinero valor={p.total_ingresos} /></Td>
                  <Td derecha className="font-semibold"><Dinero valor={p.utilidad} /></Td>
                  <Td derecha>
                    {descuadrado ? <Dinero valor={p.descuadre} /> : <span className="rotulo">cuadra</span>}
                  </Td>
                  <Td derecha>
                    <Versiones periodoId={p.id} onCambio={onCambio} />
                  </Td>
                  <Td derecha>
                    {p.estado === "cerrado" ? (
                      <Boton
                        variante="fantasma"
                        tamano="sm"
                        cargando={trabajando === p.id}
                        onClick={() => accion(() => analisis.reabrirPeriodo(p.id), p.id)}
                      >
                        Reabrir
                      </Boton>
                    ) : (
                      <Boton
                        variante="fantasma"
                        tamano="sm"
                        cargando={trabajando === p.id}
                        onClick={() => accion(() => analisis.eliminarPeriodo(p.id), p.id)}
                      >
                        Eliminar
                      </Boton>
                    )}
                  </Td>
                </tr>
              );
            })}
          </tbody>
        </Tabla>
      </Tarjeta>

      {cierres.length > 0 && (
        <Tarjeta rotulo="Cierres guardados" titulo="Saldos que abren el periodo siguiente">
          <ul className="space-y-1.5">
            {cierres.map((c) => (
              <li key={c.id} className="flex flex-wrap items-center justify-between gap-2 text-sm">
                <span>Corte al {fechaLarga(c.fecha_corte)}</span>
                <Rotulo>
                  {c.cuentas} cuentas · guardado {fecha(c.creado)}
                </Rotulo>
              </li>
            ))}
          </ul>
        </Tarjeta>
      )}
    </div>
  );
}

/* ── libro diario ────────────────────────────────────────────────────── */
function LibroDiarioFicha({ periodos }: { periodos: Periodo[] }) {
  const calculados = periodos.filter((p) => p.estado !== "borrador");
  const [periodoId, setPeriodoId] = useState(calculados[0]?.id ?? "");
  const [cuenta, setCuenta] = useState("");
  const [datos, setDatos] = useState<Resultado | null>(null);
  const [cargando, setCargando] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!calculados.length) return;
    if (!calculados.some((p) => p.id === periodoId)) setPeriodoId(calculados[0].id);
  }, [calculados, periodoId]);

  useEffect(() => {
    if (!periodoId) return;
    let vivo = true;
    setCargando(true);
    setError("");
    analisis
      .resultadoDePeriodo(periodoId)
      .then((r) => vivo && setDatos(r.resultado))
      .catch((e) => vivo && setError((e as Error).message))
      .finally(() => vivo && setCargando(false));
    return () => {
      vivo = false;
    };
  }, [periodoId]);

  if (!calculados.length) {
    return (
      <Vacio titulo="Sin libro diario todavía">
        Este cliente aún no tiene periodos calculados. Suba sus archivos y el libro diario se arma solo.
      </Vacio>
    );
  }

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div className="min-w-0">
          <Rotulo className="mb-2 block">Periodo</Rotulo>
          <div className="barra-fina flex gap-2 overflow-x-auto pb-1">
            {calculados.map((p) => (
              <button
                key={p.id}
                type="button"
                onClick={() => setPeriodoId(p.id)}
                aria-pressed={p.id === periodoId}
                className={clases(
                  "shrink-0 rounded-full px-4 py-2 text-[13px] font-medium transition-colors duration-200",
                  p.id === periodoId
                    ? "bg-tinta text-sobre-tinta"
                    : "border border-linea bg-hoja text-grafito hover:bg-hoja-2 hover:text-tinta",
                )}
              >
                {periodoCorto(p.desde, p.hasta)}
                {p.estado === "cerrado" && <span className="ml-1.5 text-[11px] opacity-70">· cerrado</span>}
              </button>
            ))}
          </div>
        </div>
        {periodoId && (
          <div className="flex flex-wrap gap-2">
            <Enlace href={descargas.libro(periodoId, "libro-diario", "excel")} variante="contorno" tamano="sm">
              <Download size={16} strokeWidth={1.5} aria-hidden /> Libro diario · Excel
            </Enlace>
            <Enlace href={descargas.libro(periodoId, "libro-diario", "pdf")} variante="contorno" tamano="sm">
              <Download size={16} strokeWidth={1.5} aria-hidden /> PDF
            </Enlace>
            <Enlace href={descargas.libro(periodoId, "mayor-balances", "excel")} variante="contorno" tamano="sm">
              <Download size={16} strokeWidth={1.5} aria-hidden /> Mayor y balances · Excel
            </Enlace>
            <Enlace href={descargas.libro(periodoId, "mayor-balances", "pdf")} variante="contorno" tamano="sm">
              <Download size={16} strokeWidth={1.5} aria-hidden /> PDF
            </Enlace>
          </div>
        )}
      </div>

      <input
        value={cuenta}
        onChange={(e) => setCuenta(e.target.value.replace(/\D/g, ""))}
        placeholder="Filtrar por cuenta PUC: 1, 11, 1105…"
        inputMode="numeric"
        aria-label="Filtrar por cuenta"
        className={clases(estiloCampo, "cifras max-w-xs")}
      />

      {error && <Aviso tono="rojo" titulo="No se pudo abrir el libro">{error}</Aviso>}
      {cargando && !datos && <Cargando texto="Abriendo el libro diario" />}
      {datos?.reportes?.libro_diario && (
        <LibroDiarioOficial rep={datos.reportes.libro_diario} origenes={datos.origenes} filtroCuenta={cuenta} />
      )}
    </div>
  );
}

/* ── datos de la ficha ───────────────────────────────────────────────── */
function DatosCliente({ cliente }: { cliente: Cliente }) {
  const grupos: [string, [string, string][]][] = [
    [
      "Identificación",
      [
        ["NIT", cliente.nit_formateado],
        ["Tipo", cliente.tipo_persona === "juridica" ? "Persona jurídica" : "Persona natural"],
        ["Régimen", cliente.regimen.replace(/_/g, " ")],
        ["Grupo NIIF", String(cliente.grupo_niif)],
        ["CIIU", cliente.ciiu],
        ["Constitución", cliente.fecha_constitucion ? fechaLarga(cliente.fecha_constitucion) : ""],
        ["Turno DIAN", cliente.turno_dian ? `${cliente.turno_dian} de 10` : ""],
      ],
    ],
    [
      "Contacto",
      [
        ["Dirección", cliente.direccion],
        ["Municipio", [cliente.municipio, cliente.departamento].filter(Boolean).join(", ")],
        ["Teléfono", cliente.telefono],
        ["Correo", cliente.email],
        ["Representante legal", cliente.rep_legal],
        ["Cédula del representante", cliente.rep_legal_cc],
        ["Suplente", cliente.rep_legal_suplente],
      ],
    ],
    [
      "Relación",
      [
        ["Honorarios mensuales", pesos(cliente.honorarios_mes)],
        ["Periodicidad", cliente.periodicidad],
        ["Capital suscrito", pesos(cliente.capital_suscrito)],
        ["Valor nominal por acción", pesos(cliente.valor_nominal_accion)],
        ["Creado", fecha(cliente.creado)],
        ["Actualizado", fecha(cliente.actualizado)],
      ],
    ],
  ];

  return (
    <div className="grid gap-4 lg:grid-cols-3">
      {grupos.map(([titulo, filas]) => (
        <Tarjeta key={titulo} rotulo={titulo} titulo="">
          <dl className="space-y-2.5">
            {filas
              .filter(([, v]) => v)
              .map(([k, v]) => (
                <div key={k} className="flex flex-wrap justify-between gap-2 border-b border-linea pb-2.5 last:border-0">
                  <dt className="rotulo">{k}</dt>
                  <dd className="text-right text-sm capitalize text-tinta">{v}</dd>
                </div>
              ))}
          </dl>
        </Tarjeta>
      ))}

      {cliente.notas && (
        <Tarjeta rotulo="Notas" titulo="" className="lg:col-span-3">
          <p className="whitespace-pre-wrap text-sm text-grafito">{cliente.notas}</p>
        </Tarjeta>
      )}
    </div>
  );
}

function DialogoBorrar({
  cliente,
  periodos,
  onCerrar,
  onBorrado,
}: {
  cliente: Cliente;
  periodos: number;
  onCerrar: () => void;
  onBorrado: () => void;
}) {
  const [texto, setTexto] = useState("");
  const [trabajando, setTrabajando] = useState(false);
  const [error, setError] = useState("");
  const confirmado = texto.trim().toUpperCase() === "ELIMINAR";

  return (
    <Dialogo
      rotulo="Acción irreversible"
      titulo={`Eliminar ${cliente.razon_social}`}
      onCerrar={onCerrar}
      ancho="max-w-lg"
      pie={
        <>
          <Boton variante="fantasma" onClick={onCerrar}>
            Cancelar
          </Boton>
          <Boton
            variante="peligro"
            disabled={!confirmado}
            cargando={trabajando}
            onClick={async () => {
              setTrabajando(true);
              try {
                await api.eliminar(cliente.id);
                onBorrado();
              } catch (e) {
                setError((e as Error).message);
                setTrabajando(false);
              }
            }}
          >
            Eliminar para siempre
          </Boton>
        </>
      }
    >
      <div className="space-y-4">
        <Aviso tono="rojo" titulo="Esto no se puede deshacer">
          Se borrarán la ficha, {periodos} periodo(s), sus estados financieros guardados y todos los
          movimientos del libro diario.
        </Aviso>
        <p className="text-sm text-grafito">
          Si solo quiere dejar de verlo en las listas, cierre esta ventana y use «Archivar».
        </p>
        <label className="block">
          <span className="rotulo mb-1.5 block !text-grafito">
            Escriba ELIMINAR para confirmar
          </span>
          <input
            value={texto}
            onChange={(e) => setTexto(e.target.value)}
            className={estiloCampo}
            autoComplete="off"
          />
        </label>
        {error && <Aviso tono="rojo">{error}</Aviso>}
      </div>
    </Dialogo>
  );
}


/* ── historial de versiones de un periodo (v2.2) ──────────────────────────
   Antes, recalcular borraba el resultado anterior sin dejar copia. Ahora cada
   versión queda guardada y desde aquí se puede ver y volver a ella. */
const MOTIVO: Record<string, string> = {
  recalculo: "Antes de recalcular",
  reapertura: "Al reabrir el cierre",
  restauracion: "Antes de restaurar",
  cierre: "Antes de cerrar de nuevo",
};

function Versiones({ periodoId, onCambio }: { periodoId: string; onCambio: () => void }) {
  const avisar = useAvisos();
  const [lista, setLista] = useState<VersionPeriodo[] | null>(null);
  const [abierto, setAbierto] = useState(false);
  const [trabajando, setTrabajando] = useState(0);
  const [detalle, setDetalle] = useState<VersionPeriodo | null>(null);

  const cargar = useCallback(() => {
    analisis.versiones(periodoId).then((r) => setLista(r.versiones)).catch(() => setLista([]));
  }, [periodoId]);

  useEffect(() => {
    cargar();
  }, [cargar]);

  if (!lista) return <span className="t-small text-gris">…</span>;
  if (!lista.length) return <span className="t-small text-gris">—</span>;

  return (
    <>
      <Boton variante="fantasma" tamano="sm" onClick={() => setAbierto(true)}>
        <History size={14} strokeWidth={1.5} aria-hidden />
        {lista.length} {lista.length === 1 ? "versión" : "versiones"}
      </Boton>

      {abierto && (
        <Dialogo
          rotulo="Historial del periodo"
          titulo="Versiones guardadas"
          onCerrar={() => setAbierto(false)}
          pie={<Boton variante="fantasma" onClick={() => setAbierto(false)}>Cerrar</Boton>}
        >
          <p className="t-body text-grafito">
            Cada vez que este periodo se recalcula, se cierra de nuevo o se reabre, lo anterior queda
            guardado aquí. Restaurar una versión no borra la actual: también la guarda.
          </p>
          <ul className="mt-6 divide-y divide-linea">
            {lista.map((v) => (
              <li key={v.id} className="flex flex-wrap items-center justify-between gap-4 py-4">
                <div className="min-w-0">
                  <p className="t-body font-medium text-tinta">{MOTIVO[v.motivo] ?? v.motivo}</p>
                  <p className="t-small mt-0.5 text-gris">
                    {fecha(v.creado)} · {v.cuentas} cuentas · {v.movimientos} movimientos
                    {v.con_cierre && " · con cierre"}
                  </p>
                  <p className="t-small mt-1 text-grafito">
                    Activo <Dinero valor={v.total_activo} /> · {esNegativo(v.utilidad) ? "pérdida" : "utilidad"}{" "}
                    <Dinero valor={v.utilidad} />
                  </p>
                </div>
                <div className="flex shrink-0 gap-2">
                  <Boton variante="fantasma" tamano="sm" onClick={() => setDetalle(v)}>
                    Ver
                  </Boton>
                  <Boton
                    variante="contorno"
                    tamano="sm"
                    cargando={trabajando === v.id}
                    onClick={async () => {
                      setTrabajando(v.id);
                      try {
                        await analisis.restaurarVersion(v.id);
                        avisar("Periodo restaurado a esa versión.");
                        setAbierto(false);
                        cargar();
                        onCambio();
                      } catch (e) {
                        avisar((e as Error).message, "rojo");
                      } finally {
                        setTrabajando(0);
                      }
                    }}
                  >
                    Restaurar esta versión
                  </Boton>
                </div>
              </li>
            ))}
          </ul>
        </Dialogo>
      )}

      {detalle && (
        <Dialogo
          rotulo={MOTIVO[detalle.motivo] ?? detalle.motivo}
          titulo={`Versión del ${fecha(detalle.creado)}`}
          onCerrar={() => setDetalle(null)}
          pie={<Boton variante="fantasma" onClick={() => setDetalle(null)}>Cerrar</Boton>}
        >
          <dl className="divide-y divide-linea">
            {[
              ["Estado de entonces", detalle.estado],
              ["Cuentas", String(detalle.cuentas)],
              ["Movimientos", String(detalle.movimientos)],
              ["Activo", pesos(detalle.total_activo)],
              ["Utilidad", pesos(detalle.utilidad)],
              ["Cierre guardado", detalle.con_cierre ? "Sí" : "No"],
            ].map(([k, v]) => (
              <div key={k} className="flex items-baseline justify-between gap-4 py-3">
                <dt className="t-meta text-gris">{k}</dt>
                <dd className="t-body capitalize text-tinta">{v}</dd>
              </div>
            ))}
          </dl>
        </Dialogo>
      )}
    </>
  );
}

/* ── 08 actividad: qué se hizo con este cliente y cuándo ───────────────── */
function Actividad({ clienteId }: { clienteId: string }) {
  const [datos, setDatos] = useState<{ actividad: ActividadLinea[]; importaciones: ArchivoImportado[] } | null>(null);
  const [error, setError] = useState("");

  const cargar = useCallback(() => {
    setError("");
    analisis.actividad(clienteId).then(setDatos).catch((e) => setError((e as Error).message));
  }, [clienteId]);

  useEffect(() => {
    cargar();
  }, [cargar]);

  if (error) return <EstadoError titulo="No se pudo leer la actividad" detalle={error} onReintentar={cargar} />;
  if (!datos) return <Cargando texto="Leyendo la actividad" />;
  if (!datos.actividad.length && !datos.importaciones.length) {
    return (
      <Vacio titulo="Todavía no hay actividad">
        Aquí queda constancia de cada cálculo, cierre, reapertura y cambio de ficha.
      </Vacio>
    );
  }

  return (
    <div className="grid gap-8 escritorio:grid-cols-12">
      <Tarjeta rotulo="Bitácora" titulo="Qué se hizo" className="escritorio:col-span-7" sinRelleno>
        <ul className="divide-y divide-linea">
          {datos.actividad.map((a) => (
            <li key={a.id} className="px-5 py-4">
              <div className="flex flex-wrap items-baseline justify-between gap-2">
                <p className="t-body font-medium text-tinta">{a.titulo}</p>
                <span className="t-meta text-gris">
                  {fecha(a.creado)} · {new Date(a.creado).toLocaleTimeString("es-CO", { hour: "2-digit", minute: "2-digit" })}
                </span>
              </div>
              {Object.keys(a.detalle || {}).length > 0 && (
                <p className="t-small mt-1 text-grafito">{resumirDetalle(a.detalle)}</p>
              )}
            </li>
          ))}
        </ul>
      </Tarjeta>

      <Tarjeta rotulo="Archivos" titulo="Lo que se subió" className="escritorio:col-span-5" sinRelleno>
        <ul className="divide-y divide-linea">
          {datos.importaciones.map((i) => (
            <li key={i.id} className="px-5 py-4">
              <p className="t-body truncate font-medium text-tinta">{i.archivo}</p>
              <p className="t-small mt-0.5 text-gris">
                {fecha(i.creado)} · {Math.ceil(i.bytes / 1024).toLocaleString("es-CO")} KB
                {i.formato && ` · ${i.formato}`}
              </p>
              <p className="codigo mt-1 truncate text-[11px] text-gris" title={i.sha256}>
                {i.sha256.slice(0, 16)}…
              </p>
            </li>
          ))}
          {!datos.importaciones.length && (
            <li className="px-5 py-4 t-small text-gris">Sin archivos registrados todavía.</li>
          )}
        </ul>
      </Tarjeta>
    </div>
  );
}

/** El detalle de la bitácora es un objeto libre: se resume en una línea legible. */
function resumirDetalle(d: Record<string, unknown>): string {
  return Object.entries(d)
    .filter(([, v]) => v !== null && v !== undefined && v !== "")
    .slice(0, 5)
    .map(([k, v]) => `${k.replace(/_/g, " ")}: ${Array.isArray(v) ? v.join(", ") : String(v)}`)
    .join(" · ");
}

/* ── archivos reales de ejemplo, SOLO en la ficha de quien los tiene (H10) ──
   Antes este botón salía en el paso «Subir» de cualquier cliente, así que
   podía meterse la contabilidad de una empresa en el expediente de otra. */
const NIT_CON_ARCHIVOS_DE_MUESTRA = "[NIT]";

function ArchivosDeMuestra({ cliente }: { cliente: Cliente }) {
  const navegar = useNavigate();
  const [cargando, setCargando] = useState(false);
  const avisar = useAvisos();

  const soloDigitos = (cliente.nit || "").replace(/\D/g, "");
  if (soloDigitos !== NIT_CON_ARCHIVOS_DE_MUESTRA) return null;

  return (
    <BotonFantasma
      compacto={false}
      cargando={cargando}
      onClick={async () => {
        setCargando(true);
        try {
          const importacion = await apiTrabajo.ejemplo(cliente.id);
          navegar(`/trabajo?cliente=${cliente.id}`, { state: { importacion } });
        } catch (e) {
          avisar((e as Error).message, "rojo");
        } finally {
          setCargando(false);
        }
      }}
    >
      Cargar sus archivos de ejemplo
    </BotonFantasma>
  );
}
