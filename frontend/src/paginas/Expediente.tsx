import { ArrowLeft, History, PenLine } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { Link, Navigate, useNavigate, useParams, useSearchParams } from "react-router-dom";
import { analisis, clientes as api, trabajo as apiTrabajo } from "../api";
import { Contabilidad } from "../componentes/Contabilidad";
import { RentaCliente } from "../componentes/RentaCliente";
import { EnLinea } from "../componentes/EnLinea";
import { PanelEditarCliente } from "../componentes/PanelEditarCliente";
import { Cabecera, useColorCliente, useMetaPagina } from "../componentes/Marco";
import { clases, esNegativo, fecha, fechaLarga, pesos, periodoCorto, restar } from "../formato";
import type {
  ArchivoImportado,
  Actividad as ActividadLinea,
  Cierre,
  Cliente,
  InformeSugerencias,
  Periodo,
  Severidad,
  Sugerencia,
  VersionPeriodo,
} from "../tipos";
import { GraficaHistorico, TablaHistorico } from "../componentes/Grafica";
import { PanelMetricas } from "../componentes/PanelMetricas";
import {
  Aviso,
  Boton,
  Cargando,
  Dialogo,
  Dinero,
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
 * Expediente del cliente (v2.3 · Fases 3 y 4). Clientes y Trabajar son ahora un
 * solo lugar con cinco secciones como máximo:
 *
 *   Resumen · Contabilidad · Renta · Archivos y actividad · Datos
 *
 * Contabilidad es la sección por defecto: con periodos abre el último; sin
 * periodos, la zona de subida. `?seccion=` lleva directo a una de ellas.
 */

type Seccion = "resumen" | "contabilidad" | "renta" | "archivos" | "datos";
const SECCIONES: Seccion[] = ["resumen", "contabilidad", "renta", "archivos", "datos"];

/** Enlaces viejos (`?vista=` de la ficha anterior) → sección y vista nuevas. */
const SECCION_ANTIGUA: Record<string, [Seccion, string | null]> = {
  resumen: ["resumen", null],
  periodos: ["archivos", null],
  actividad: ["archivos", null],
  estados: ["contabilidad", "situacion"],
  inventario: ["contabilidad", "inventario"],
  nomina: ["contabilidad", "nomina"],
  movimientos: ["contabilidad", "diario"],
  socios: ["datos", null],
  ficha: ["datos", null],
};

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

export function Expediente() {
  const { id = "" } = useParams<{ id: string }>();
  const navegar = useNavigate();
  const [params, setParams] = useSearchParams();

  const [cliente, setCliente] = useState<Cliente | null>(null);
  const [periodos, setPeriodos] = useState<Periodo[]>([]);
  const [cierres, setCierres] = useState<Cierre[]>([]);
  const [serie, setSerie] = useState<Periodo[]>([]);
  const [informe, setInforme] = useState<InformeSugerencias | null>(null);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState("");
  const [confirmarBorrado, setConfirmarBorrado] = useState(false);
  const [panelEditarAbierto, setPanelEditarAbierto] = useState(false);

  const antigua = params.get("vista");
  const pedida = params.get("seccion") as Seccion | null;
  const seccion: Seccion = pedida && SECCIONES.includes(pedida) ? pedida : "contabilidad";

  const cargar = useCallback(async () => {
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
    setCargando(true);
    cargar();
  }, [cargar]);

  const ultimo = serie.length ? serie[serie.length - 1] : null;
  useColorCliente(cliente?.nit);
  useMetaPagina(ultimo ? `Corte ${fechaLarga(ultimo.hasta)}` : null);

  // Un enlace viejo con ?vista= se traduce una vez y se reemplaza.
  if (antigua && !pedida) {
    const [s, v] = SECCION_ANTIGUA[antigua] ?? ["contabilidad", antigua];
    const n = new URLSearchParams(params);
    n.delete("vista");
    n.set("seccion", s);
    if (v) n.set("vista", v);
    return <Navigate to={`/clientes/${id}?${n.toString()}`} replace />;
  }

  if (error && /no existe/i.test(error)) {
    return (
      <CarpetaVacia
        titulo="Ese expediente no existe"
        accion={<BotonPrimario a="/clientes" flecha>Ir al directorio</BotonPrimario>}
      >
        Puede que el cliente se haya eliminado o que el enlace esté incompleto.
      </CarpetaVacia>
    );
  }
  if (error && !cliente) return <EstadoError titulo="No se pudo abrir el expediente" detalle={error} onReintentar={cargar} />;
  if (cargando) return <EsqueletoFicha />;
  if (!cliente) return null;

  const criticas = informe?.conteo.critica ?? 0;
  const altas = informe?.conteo.alta ?? 0;
  const irA = (s: Seccion) => {
    const n = new URLSearchParams();
    n.set("seccion", s);
    setParams(n);
  };

  return (
    <div className="space-y-8">
      <Cabecera>
        <CabeceraCliente
          cliente={cliente}
          onEditar={() => setPanelEditarAbierto(true)}
          onActualizar={setCliente}
        />
        <div className="mt-6">
          <Pestanas<Seccion>
            valor={seccion}
            onCambio={irA}
            opciones={[
              { id: "resumen", texto: "Resumen", cuenta: criticas + altas },
              { id: "contabilidad", texto: "Contabilidad" },
              { id: "renta", texto: "Renta" },
              { id: "archivos", texto: "Archivos y actividad" },
              { id: "datos", texto: "Datos" },
            ]}
          />
        </div>
      </Cabecera>

      {cliente.estado === "archivado" && (
        <Aviso tono="ambar" titulo="Este cliente está archivado">
          <p>No aparece en las listas ni en el tablero, pero toda su contabilidad sigue guardada.</p>
          <div className="mt-3">
            <Boton
              variante="solido"
              tamano="sm"
              onClick={async () => {
                setCliente(await api.restaurar(id));
              }}
            >
              Restaurar cliente
            </Boton>
          </div>
        </Aviso>
      )}

      {seccion === "resumen" && (
        <div className="space-y-8">
          {cliente.notas && (
            <Aviso tono="ambar" titulo="Nota de revisión del contador">
              <p className="whitespace-pre-line">{cliente.notas}</p>
            </Aviso>
          )}
          {ultimo ? (
            <div className="space-y-4">
              <p className="t-body text-grafito">
                Último periodo:{" "}
                <EnlaceSubrayado a={`/clientes/${id}?seccion=contabilidad`}>{periodoCorto(ultimo.desde, ultimo.hasta)}</EnlaceSubrayado>
                {" · "}
                {ultimo.estado === "cerrado" ? "cerrado, listo para firmar" : "abierto"}
              </p>
              {/* Una sola franja con las cuatro cifras: el detalle está en Contabilidad. */}
              <dl className="material-hoja grid grid-cols-2 gap-6 p-5 escritorio:grid-cols-4">
                {([
                  ["Activo", ultimo.total_activo],
                  ["Pasivo", ultimo.total_pasivo],
                  ["Patrimonio", ultimo.total_patrimonio],
                  [esNegativo(ultimo.utilidad) ? "Pérdida" : "Utilidad", ultimo.utilidad],
                ] as const).map(([k, v]) => (
                  <div key={k} className="min-w-0">
                    <dt className="t-meta text-gris">{k}</dt>
                    <dd className={clases("cifras t-h2 mt-1", k === "Pérdida" ? "text-rojo" : "text-tinta")}>{pesos(v)}</dd>
                  </div>
                ))}
              </dl>
            </div>
          ) : (
            <Vacio
              titulo="Este cliente aún no tiene periodos"
              accion={<BotonPrimario a={`/clientes/${id}?seccion=contabilidad`} flecha>Subir el primer periodo</BotonPrimario>}
            >
              Suba sus archivos contables y aquí quedan el balance, los estados financieros, la nómina y el inventario.
            </Vacio>
          )}

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

          {ultimo && (
            <details>
              <summary className="t-small cursor-pointer select-none text-azul-tinta underline underline-offset-4">
                Ver indicadores y gráficas del último periodo
              </summary>
              <div className="mt-6">
                <PanelMetricas cliente={cliente} periodo={ultimo} />
              </div>
            </details>
          )}
        </div>
      )}

      {seccion === "contabilidad" && <Contabilidad cliente={cliente} periodos={periodos} onCambio={cargar} />}

      {seccion === "renta" && <RentaCliente cliente={cliente} />}

      {seccion === "archivos" && (
        <div className="space-y-10">
          <ListaPeriodos clienteId={id} periodos={periodos} cierres={cierres} onCambio={cargar} />
          <Actividad clienteId={id} />
        </div>
      )}

      {seccion === "datos" && (
        <div className="space-y-8">
          <div className="flex flex-wrap gap-3">
            <BotonFantasma a={`/clientes/${cliente.id}/editar`} icono={<PenLine size={18} strokeWidth={1.5} aria-hidden />}>
              Editar ficha
            </BotonFantasma>
            <ArchivosDeMuestra cliente={cliente} />
          </div>
          <DatosCliente cliente={cliente} />
          <Socios cliente={cliente} />
          <details>
            <summary className="t-small cursor-pointer select-none text-azul-tinta underline underline-offset-4">
              Archivar o eliminar este cliente
            </summary>
            <div className="mt-4 space-y-4">
              <p className="t-body max-w-2xl text-grafito">
                Archivar lo saca de las listas pero conserva toda su contabilidad. Eliminar borra el cliente y{" "}
                <strong className="text-tinta">todos sus periodos, resultados y movimientos</strong>, y no se puede deshacer.
              </p>
              <div className="flex flex-wrap gap-3">
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
            </div>
          </details>
        </div>
      )}

      {confirmarBorrado && (
        <DialogoBorrar
          cliente={cliente}
          periodos={periodos.length}
          onCerrar={() => setConfirmarBorrado(false)}
          onBorrado={() => navegar("/clientes", { replace: true })}
        />
      )}

      <PanelEditarCliente
        abierto={panelEditarAbierto}
        onCerrar={() => setPanelEditarAbierto(false)}
        cliente={cliente}
        onGuardado={(actualizado) => setCliente(actualizado)}
      />
    </div>
  );
}

/* ── cabecera: quién es el cliente. Edición directa o en panel lateral. ── */
function CabeceraCliente({
  cliente,
  onEditar,
  onActualizar,
}: {
  cliente: Cliente;
  onEditar: () => void;
  onActualizar: (actualizado: Cliente) => void;
}) {
  const codigo = `${cliente.sigla || "Cliente"} — ${cliente.nit.slice(-3)}`;
  const desde = cliente.fecha_constitucion
    ? `Constituida ${fechaEsquina(cliente.fecha_constitucion)}`
    : `Ficha desde ${fechaEsquina(cliente.creado)}`;
  return (
    <header className="relative pb-2">
      <div className="t-meta flex flex-wrap justify-between gap-3 text-gris">
        <span>{codigo}</span>
        <div className="flex items-center gap-3">
          <span>{cliente.turno_dian ? `Turno DIAN — ${String(cliente.turno_dian).padStart(2, "0")}` : "Sin turno DIAN"}</span>
          <button
            type="button"
            onClick={onEditar}
            className="inline-flex items-center gap-1.5 rounded-full border border-linea bg-hoja px-3 py-1 text-xs font-medium text-tinta hover:bg-hoja-2 transition-colors cursor-pointer"
            title="Abrir panel de edición completa"
          >
            <PenLine size={13} strokeWidth={1.5} /> Editar cliente
          </button>
        </div>
      </div>

      <div className="mt-6 grid gap-8 escritorio:grid-cols-12 escritorio:items-center">
        <div className="min-w-0 escritorio:col-span-8">
          <EnlaceSubrayado a="/clientes">
            <ArrowLeft size={14} strokeWidth={1.5} aria-hidden /> Clientes
          </EnlaceSubrayado>
          <div className="mt-4">
            <h1 className="t-h1 text-balance text-tinta">
              <EnLinea
                valor={cliente.razon_social}
                etiqueta="Razón social"
                onGuardar={async (nuevo) => {
                  const act = await api.actualizar(cliente.id, { razon_social: nuevo });
                  onActualizar(act);
                }}
              >
                {cliente.razon_social}
              </EnLinea>
            </h1>
          </div>
          <p className="mt-5 flex flex-wrap items-center gap-x-4 gap-y-2 text-grafito">
            {cliente.sigla && <span className="t-body font-semibold text-tinta">{cliente.sigla}</span>}
            <span className="codigo text-[13px]">NIT {cliente.nit_formateado}</span>
            {cliente.municipio && <span className="t-body">{cliente.municipio}</span>}
            <InsigniaEstado estado={cliente.estado} />
          </p>

        </div>

        <div className="hidden justify-end escritorio:col-span-4 escritorio:flex">
          <EsferaCliente nit={cliente.nit} nombre={cliente.razon_social} tamano={56} />
        </div>
      </div>

      <div className="t-meta mt-6 hidden flex-wrap items-center justify-between gap-3 text-gris sm:flex">
        <span>{desde}</span>
        <span>
          Honorarios — {pesos(cliente.honorarios_mes)} · {cliente.periodicidad}
        </span>
      </div>
    </header>
  );
}

/* ── socios ──────────────────────────────────────────────────────── */
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

/* ── periodos: la historia del cliente. Abrir, cerrar, reabrir o anotar se hace
   en Contabilidad; aquí se ve el conjunto y las versiones guardadas. ── */
function ListaPeriodos({
  clienteId,
  periodos,
  cierres,
  onCambio,
}: {
  clienteId: string;
  periodos: Periodo[];
  cierres: Cierre[];
  onCambio: () => void;
}) {
  if (!periodos.length) {
    return (
      <Vacio titulo="Sin periodos todavía">
        Suba el primer archivo de este cliente en Contabilidad y aquí quedará su historia.
      </Vacio>
    );
  }
  return (
    <div className="space-y-4">
      <Tarjeta rotulo="Periodos" titulo={`${periodos.length} ${periodos.length === 1 ? "periodo" : "periodos"}`} sinRelleno>
        <Tabla>
          <thead>
            <tr>
              <Th>Periodo</Th>
              <Th>Estado</Th>
              <Th derecha>Activo</Th>
              <Th derecha>Utilidad</Th>
              <Th derecha>Historial</Th>
            </tr>
          </thead>
          <tbody>
            {periodos.map((p) => (
              <tr key={p.id} className={clases("transition hover:bg-hoja", p.cuadra === false && "bg-rojo-suave/40")}>
                <Td>
                  <Link
                    to={`/clientes/${clienteId}?seccion=contabilidad&periodo=${p.desde.slice(0, 7)}`}
                    className="font-medium text-tinta underline-offset-4 hover:underline"
                  >
                    {periodoCorto(p.desde, p.hasta)}
                  </Link>
                  {p.nota && <span className="t-small mt-0.5 block max-w-md text-ambar">{p.nota}</span>}
                </Td>
                <Td>
                  {p.estado}
                  {p.cuadra === false && <span className="text-rojo"> · no cuadra</span>}
                </Td>
                <Td derecha><Dinero valor={p.total_activo} /></Td>
                <Td derecha className="font-semibold"><Dinero valor={p.utilidad} /></Td>
                <Td derecha>
                  <Versiones periodoId={p.id} cantidad={p.versiones_n ?? 0} onCambio={onCambio} />
                </Td>
              </tr>
            ))}
          </tbody>
        </Tabla>
      </Tarjeta>

      {cierres.length > 0 && (
        <details>
          <summary className="t-small cursor-pointer select-none text-azul-tinta underline underline-offset-4">
            Ver los {cierres.length} cierres guardados (saldos que abren el periodo siguiente)
          </summary>
          <ul className="mt-3 space-y-1.5">
            {cierres.map((c) => (
              <li key={c.id} className="flex flex-wrap items-center justify-between gap-2 text-sm">
                <span>Corte al {fechaLarga(c.fecha_corte)}</span>
                <Rotulo>
                  {c.cuentas} cuentas · guardado {fecha(c.creado)}
                </Rotulo>
              </li>
            ))}
          </ul>
        </details>
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
    <Tarjeta rotulo="Ficha" titulo="Datos del cliente">
    <div className="grid gap-8 lg:grid-cols-3">
      {grupos.map(([titulo, filas]) => (
        <section key={titulo}>
          <h3 className="t-meta mb-3 text-gris">{titulo}</h3>
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
        </section>
      ))}
      {cliente.notas && (
        <section className="lg:col-span-3">
          <h3 className="t-meta mb-2 text-gris">Notas</h3>
          <p className="whitespace-pre-wrap text-sm text-grafito">{cliente.notas}</p>
        </section>
      )}
    </div>
    </Tarjeta>
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

function Versiones({ periodoId, cantidad, onCambio }: { periodoId: string; cantidad: number; onCambio: () => void }) {
  const avisar = useAvisos();
  const [lista, setLista] = useState<VersionPeriodo[] | null>(null);
  const [abierto, setAbierto] = useState(false);
  const [trabajando, setTrabajando] = useState(0);
  const [detalle, setDetalle] = useState<VersionPeriodo | null>(null);

  const cargar = useCallback(() => {
    analisis.versiones(periodoId).then((r) => setLista(r.versiones)).catch(() => setLista([]));
  }, [periodoId]);

  // La lista se pide al abrir el historial, no al pintar la tabla (una petición por periodo).
  useEffect(() => {
    if (abierto) cargar();
  }, [abierto, cargar]);

  if (!cantidad) return <span className="t-small text-gris">—</span>;

  return (
    <>
      <Boton variante="fantasma" tamano="sm" onClick={() => setAbierto(true)}>
        <History size={14} strokeWidth={1.5} aria-hidden />
        {cantidad} {cantidad === 1 ? "versión" : "versiones"}
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
          {!lista && <p className="t-small mt-6 text-gris">Cargando…</p>}
          <ul className="mt-6 divide-y divide-linea">
            {(lista ?? []).map((v) => (
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

/* ── actividad: qué se hizo con este cliente y cuándo ───────────────── */
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
          {datos.actividad.slice(0, VISIBLES).map((a) => (
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
        {datos.actividad.length > VISIBLES && (
          <details className="border-t border-linea px-5 py-3">
            <summary className="t-small cursor-pointer select-none text-azul-tinta underline underline-offset-4">
              Ver {datos.actividad.length - VISIBLES} más
            </summary>
            <ul className="mt-2 divide-y divide-linea">
              {datos.actividad.slice(VISIBLES).map((a) => (
                <li key={a.id} className="t-small flex flex-wrap justify-between gap-2 py-2">
                  <span className="text-tinta">{a.titulo}</span>
                  <span className="text-gris">{fecha(a.creado)}</span>
                </li>
              ))}
            </ul>
          </details>
        )}
      </Tarjeta>

      <Tarjeta rotulo="Archivos" titulo="Lo que se subió" className="escritorio:col-span-5" sinRelleno>
        <ul className="divide-y divide-linea">
          {datos.importaciones.slice(0, VISIBLES).map((i) => (
            <li key={i.id} className="px-5 py-4">
              <p className="t-body truncate font-medium text-tinta">{i.archivo}</p>
              <p className="t-small mt-0.5 text-gris">
                {fecha(i.creado)} · {Math.ceil(i.bytes / 1024).toLocaleString("es-CO")} KB
                {i.formato && ` · ${i.formato}`}
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

/** Cuántas líneas de actividad y de archivos se ven sin desplegar. */
const VISIBLES = 5;

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
   podía meterse la contabilidad de una empresa en el expediente de otra. El
   backend dice si este cliente tiene archivos de muestra en este equipo. */

function ArchivosDeMuestra({ cliente }: { cliente: Cliente }) {
  const navegar = useNavigate();
  const [cargando, setCargando] = useState(false);
  const avisar = useAvisos();

  if (!cliente.archivos_de_muestra) return null;

  return (
    <BotonFantasma
      compacto={false}
      cargando={cargando}
      onClick={async () => {
        setCargando(true);
        try {
          const importacion = await apiTrabajo.ejemplo(cliente.id);
          navegar(`/clientes/${cliente.id}?seccion=contabilidad`, { state: { importacion } });
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
