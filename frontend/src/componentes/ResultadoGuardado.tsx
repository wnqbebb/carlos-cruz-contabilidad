import { Download } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { analisis, descargas } from "../api";
import { clases, esNegativo, numero, pesos, periodoCorto, porcentaje, razon, restar, sumar } from "../formato";
import type { Periodo, Resultado } from "../tipos";
import { ListaAlertas } from "./Alertas";
import { CuentasT } from "./CuentasT";
import { AnilloBalance, BarrasDesglose, Medidor } from "./Grafica";
import { Reporte } from "./Reporte";
import { Cifra as CifraExacta, InsigniaEstado } from "../ui";
import {
  Aviso, Boton, Cargando, Enlace, Insignia, Pestanas, Rotulo, Tarjeta, Vacio,
} from "./ui";

/* Informes que se muestran, agrupados como los revisa un contador. */
const GRUPOS: { id: string; texto: string; claves: string[] }[] = [
  { id: "estados", texto: "Estados financieros",
    claves: ["situacion_financiera", "estado_resultados", "cambios_patrimonio", "flujo_efectivo"] },
  { id: "balances", texto: "Balances y Cierres",
    claves: ["balance_prueba", "balance_ajustado", "asiento_cierre", "balance_definitivo"] },
  { id: "trabajo", texto: "Hoja de trabajo (12 col)", claves: ["hoja_trabajo"] },
  { id: "indicadores", texto: "Indicadores financieros", claves: ["indicadores"] },
  { id: "inventario", texto: "Inventario y Kardex",
    claves: ["inventario_saldos", "inventario_vencimientos", "inventario_fisico"] },
  { id: "nomina", texto: "Nómina y Seguridad Social", claves: ["nomina_devengados", "nomina_apropiaciones"] },
  { id: "depreciacion", texto: "Depreciación de activos", claves: ["depreciacion"] },
  { id: "mayor", texto: "Libro mayor y cuentas T", claves: ["libro_mayor"] },
];

/**
 * Muestra un periodo YA CALCULADO tal como quedó guardado en Supabase o local.
 */
export function ResultadoGuardado({
  periodos,
  grupos,
  excluir,
  conPanel = true,
}: {
  periodos: Periodo[];
  /** Solo estos grupos de informes (p. ej. ["inventario"] en la pestaña Inventario). */
  grupos?: string[];
  /** Grupos que se muestran en otra pestaña. */
  excluir?: string[];
  /** Panel de cifras y gráficas del periodo. */
  conPanel?: boolean;
}) {
  const calculados = useMemo(
    () => periodos.filter((p) => p.estado !== "borrador"),
    [periodos],
  );
  const [periodoId, setPeriodoId] = useState(calculados[0]?.id ?? "");
  const [datos, setDatos] = useState<Resultado | null>(null);
  const [cargando, setCargando] = useState(false);
  const [error, setError] = useState("");
  const [vista, setVista] = useState(grupos?.[0] ?? "estados");

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
      .catch((e) => {
        if (!vivo) return;
        setError((e as Error).message);
        setDatos(null);
      })
      .finally(() => vivo && setCargando(false));
    return () => {
      vivo = false;
    };
  }, [periodoId]);

  if (!calculados.length) {
    return (
      <Vacio titulo="Todavía no hay periodos calculados para este cliente">
        Suba los archivos del cliente desde «Trabajar un periodo» y aquí se archivará automáticamente todo su expediente contable: estados financieros, balances, inventario y nómina.
      </Vacio>
    );
  }

  const periodo = calculados.find((p) => p.id === periodoId);
  const disponibles = GRUPOS.filter(
    (g) =>
      (!grupos || grupos.includes(g.id)) &&
      !excluir?.includes(g.id) &&
      g.claves.some((k) => datos?.reportes?.[k]),
  );
  // Si la vista guardada no existe en este periodo, se abre la primera disponible.
  const vistaVisible =
    vista === "alertas" || vista === "notas" || disponibles.some((g) => g.id === vista)
      ? vista
      : disponibles[0]?.id ?? "alertas";

  return (
    <div className="space-y-6">
      {/* ── selector de periodo y descargas rápidas ───────────────────── */}
      <div className="material-hoja p-5 flex flex-wrap items-center justify-between gap-4">
        <div>
          <Rotulo className="mb-2 block text-gris">Seleccionar Periodo Contable</Rotulo>
          <div className="barra-fina flex gap-2 overflow-x-auto pb-1">
            {calculados.map((p) => (
              <button
                key={p.id}
                onClick={() => setPeriodoId(p.id)}
                className={clases(
                  "shrink-0 rounded-full px-4 py-2 text-xs sm:text-sm font-semibold transition-all duration-200",
                  p.id === periodoId
                    ? "bg-tinta text-white shadow-md "
                    : "border border-linea bg-hoja text-grafito hover:bg-hoja-2 hover:text-tinta",
                )}
              >
                <span>{periodoCorto(p.desde, p.hasta)}</span>
                {p.estado === "cerrado" && (
                  <span className="ml-1.5 opacity-70 text-[11px] font-normal">· cerrado</span>
                )}
              </button>
            ))}
          </div>
        </div>

        {periodoId && (
          <div className="flex flex-wrap gap-2.5">
            <Enlace href={descargas.excelPeriodo(periodoId)} variante="lima" tamano="sm">
              <Download size={16} strokeWidth={1.5} aria-hidden /> Excel completo
            </Enlace>
            <Enlace href={descargas.pdfPeriodo(periodoId)} variante="solido" tamano="sm">
              <Download size={16} strokeWidth={1.5} aria-hidden /> PDF para firmar
            </Enlace>
            <Enlace href={descargas.saldosPeriodo(periodoId)} variante="contorno" tamano="sm">
              Saldos Siguientes
            </Enlace>
          </div>
        )}
      </div>

      {error && <Aviso tono="rojo" titulo="No se pudo abrir el periodo">{error}</Aviso>}
      {cargando && <Cargando texto="Abriendo estados financieros del expediente" />}

      {datos && periodo && (
        <>
          {conPanel && <PanelCifras datos={datos} periodo={periodo} />}

          {grupos && disponibles.length === 0 && (
            <Vacio titulo={`Este periodo no trae ${grupos.includes("nomina") ? "nómina" : "inventario"}`}>
              Los archivos de {periodoCorto(periodo.desde, periodo.hasta)} no incluyeron esa información. Si la
              cargó en otro periodo, elíjalo arriba.
            </Vacio>
          )}

          {disponibles.length > 0 || !grupos ? (
          <Tarjeta
            rotulo="Expediente contable"
            titulo={`Estados y balances — ${periodoCorto(periodo.desde, periodo.hasta)}`}
            subtitulo="Calculado con precisión decimal exacta y partida doble verificada."
            sinRelleno
          >
            <div className="px-5 pt-4 sm:px-6">
              <Pestanas
                valor={vistaVisible}
                onCambio={setVista}
                opciones={[
                  ...disponibles.map((g) => ({ id: g.id, texto: g.texto })),
                  ...(grupos
                    ? []
                    : [
                        { id: "alertas", texto: "Alertas", cuenta: datos.alertas?.length ?? 0 },
                        { id: "notas", texto: "Notas a los EF" },
                      ]),
                ]}
              />
            </div>

            <div className="p-5 sm:p-6 space-y-6">
              {vistaVisible === "alertas" && (
                <div className="max-w-4xl">
                  <ListaAlertas alertas={datos.alertas ?? []} limite={30} />
                </div>
              )}

              {vistaVisible === "notas" && (
                <div className="space-y-6 max-w-4xl">
                  {(datos.notas ?? []).map((n) => (
                    <article key={n.titulo} className="material-hoja p-5 bg-hoja">
                      <h3 className="subtitular text-base font-bold text-tinta">{n.titulo}</h3>
                      {n.parrafos.map((p, i) => (
                        <p key={i} className="mt-2 text-sm leading-relaxed text-grafito">
                          {p}
                        </p>
                      ))}
                    </article>
                  ))}
                  {!(datos.notas ?? []).length && (
                    <p className="text-sm text-gris">Este periodo no generó notas automáticas.</p>
                  )}
                </div>
              )}

              {disponibles
                .filter((g) => g.id === vistaVisible)
                .map((g) => (
                  <div key={g.id} className="space-y-8">
                    {g.claves
                      .filter((k) => datos.reportes[k])
                      .map((k) => (
                        <Reporte key={k} rep={datos.reportes[k]} />
                      ))}
                    {g.id === "mayor" && datos.cuentas_t?.length > 0 && (
                      <div className="pt-4">
                        <h3 className="subtitular mb-4 text-base font-bold text-tinta">
                          Esquemas de Mayor (Cuentas T)
                        </h3>
                        <CuentasT cuentas={datos.cuentas_t} />
                      </div>
                    )}
                  </div>
                ))}
            </div>
          </Tarjeta>
          ) : null}
        </>
      )}
    </div>
  );
}

/* ── panel de cifras y gráficas del periodo ──────────────────────────── */
function PanelCifras({ datos, periodo }: { datos: Resultado; periodo: Periodo }) {
  const r = datos.resumen ?? {};
  const activo = String(r.total_activo ?? "0");
  const pasivo = String(r.total_pasivo ?? "0");
  const patrimonio = String(r.total_patrimonio ?? "0");
  const ingresos = String(r.ingresos ?? "0");
  const utilidad = String(r.utilidad_neta ?? "0");
  const perdida = esNegativo(utilidad);

  // Razones exactas en texto (BigInt). `Number` solo para dibujar los medidores.
  const corriente = razon(String(r.activo_corriente ?? "0"), String(r.pasivo_corriente ?? "0"), 2);
  const endeudamiento = razon(pasivo, activo, 4);
  const margen = razon(utilidad, ingresos, 4);
  const fCorriente = corriente ? Number(corriente) : 0;
  const fEndeudamiento = endeudamiento ? Number(endeudamiento) : 0;
  const fMargen = margen ? Number(margen) : 0;

  return (
    <div className="space-y-5">
      {/* ── Fila de Cápsulas de Ecuación Contable FundFlow Style ─────────── */}
      <div className="grid gap-5 lg:grid-cols-[1.1fr_1fr]">
        <Tarjeta rotulo="Ecuación Contable NIIF" titulo="Estructura Patrimonial">
          <div className="py-2">
            <AnilloBalance activo={activo} pasivo={pasivo} patrimonio={patrimonio} />
          </div>
        </Tarjeta>

        <div className="grid gap-4 sm:grid-cols-2">
          <div
            className={clases("@container p-5", perdida ? "rounded-hoja bg-rojo-cartel text-white" : "material-expediente")}
          >
            <p className={clases("t-meta", perdida ? "text-white/85" : "text-sobre-tinta-2")}>
              {perdida ? "Pérdida del periodo" : "Utilidad del periodo"}
            </p>
            <p className="mt-3">
              <CifraExacta valor={utilidad} tamano="kpi" encajar indicador neutra={perdida} />
            </p>
          </div>

          <div className="@container material-hoja p-5">
            <p className="t-meta text-gris">Ingresos netos</p>
            <p className="mt-3 text-tinta">
              <CifraExacta valor={ingresos} tamano="kpi" encajar />
            </p>
          </div>

          {/* Desglose de Gastos */}
          <div className="sm:col-span-2 material-hoja p-5">
            <BarrasDesglose
              titulo="Distribución de Costos y Gastos"
              filas={[
                { nombre: "Costo de ventas", valor: String(r.costo_ventas ?? "0") },
                { nombre: "Gastos de administración", valor: String(r.gastos_admin ?? "0") },
                { nombre: "Gastos de ventas", valor: String(r.gastos_ventas ?? "0") },
                { nombre: "Gastos no operacionales", valor: String(r.gastos_no_op ?? "0") },
                { nombre: "Impuesto de renta", valor: String(r.impuesto_renta ?? "0") },
              ]}
            />
          </div>
        </div>
      </div>

      {/* ── Medidores e Indicadores Financieros ─────────────────────────── */}
      <div className="grid gap-4 sm:grid-cols-3">
        <Medidor
          nombre="Razón corriente"
          valor={corriente ? `${numero(corriente, 2)} veces` : "—"}
          texto="Activo corriente sobre pasivo corriente. Mayor a 1.0 garantiza liquidez inmediata."
          fraccion={Math.min(fCorriente / 3, 1)}
          referencia={1 / 3}
          bueno="mayor"
        />
        <Medidor
          nombre="Endeudamiento"
          valor={endeudamiento ? porcentaje(endeudamiento) : "—"}
          texto="Porcentaje del activo comprometido con acreedores y pasivos."
          fraccion={fEndeudamiento}
          referencia={0.7}
          bueno="menor"
        />
        <Medidor
          nombre="Margen neto"
          valor={margen ? porcentaje(margen) : "—"}
          texto="Rendimiento final sobre los ingresos operacionales totales."
          fraccion={Math.max(0, Math.min(fMargen, 1))}
          referencia={0.05}
          bueno="mayor"
        />
      </div>

      {!periodo.cuadra && (
        <Aviso tono="rojo" titulo="Aviso de Descuadre">
          El activo difiere del pasivo más el patrimonio en{" "}
          <strong className="cifras">{pesos(restar(activo, sumar(pasivo, patrimonio)))}</strong>.
          Revise los asientos de ajuste antes de expedir los estados financieros.
        </Aviso>
      )}

      {Boolean(r.causal_disolucion) && (
        <Aviso tono="rojo" titulo="Deterioro Patrimonial Grave">
          El patrimonio neto quedó por debajo del 50% del capital suscrito. Conforme al Código de Comercio debe informarse de inmediato a los accionistas.
        </Aviso>
      )}

      <div className="flex flex-wrap gap-2 pt-1">
        {([
          ["Balance de prueba", r.bp_cuadra],
          ["Balance ajustado", r.ajustado_cuadra],
          ["Hoja de trabajo", r.hoja_trabajo_cuadra],
          ["Activo = Pasivo + Patrimonio", r.esf_cuadra],
        ] as [string, unknown][]).map(([nombre, ok]) => (
          <InsigniaEstado key={nombre} estado={ok ? "cuadra" : "descuadre"} discreta>
            {nombre}
          </InsigniaEstado>
        ))}
      </div>
    </div>
  );
}
