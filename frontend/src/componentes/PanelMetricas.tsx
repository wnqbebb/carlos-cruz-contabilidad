import { useEffect, useMemo, useState } from "react";
import { analisis } from "../api";
import { clases, esCero, esNegativo, numero, pesos, porcentaje, restar, sumar } from "../formato";
import type { Cliente, Periodo, Resultado } from "../tipos";
import { AnilloBalance, BarrasDesglose, Medidor } from "./Grafica";
import { Rotulo, Tarjeta } from "./ui";

/* ═══════════════════════════════════════════════════════════════════════════
   Panel de métricas del cliente.

   Toma el ÚLTIMO periodo calculado y despliega todo lo que el contador quiere
   ver de un golpe: la ecuación contable dibujada, los indicadores con su
   referencia, a dónde se fue el dinero, el efectivo, la nómina y el inventario.

   Los importes nunca pasan por `float`: se comparan y suman como texto decimal
   con las funciones de `formato.ts`. A número solo se convierte para calcular
   la LONGITUD de una barra, nunca para mostrar una cifra.
   ═══════════════════════════════════════════════════════════════════════════ */

/** A número SOLO para geometría de barras y razones. Nunca para mostrar dinero. */
function n(v: unknown): number {
  const x = Number(String(v ?? "0"));
  return Number.isFinite(x) ? x : 0;
}

function razon(a: unknown, b: unknown): number | null {
  const d = n(b);
  return d === 0 ? null : n(a) / d;
}

export function PanelMetricas({ cliente, periodo }: { cliente: Cliente; periodo: Periodo }) {
  const [datos, setDatos] = useState<Resultado | null>(null);
  const [cargando, setCargando] = useState(true);

  useEffect(() => {
    let vivo = true;
    setCargando(true);
    analisis
      .resultadoDePeriodo(periodo.id)
      .then((r) => vivo && setDatos(r.resultado))
      .catch(() => vivo && setDatos(null))
      .finally(() => vivo && setCargando(false));
    return () => {
      vivo = false;
    };
  }, [periodo.id]);

  const r = (datos?.resumen ?? {}) as Record<string, unknown>;

  const m = useMemo(() => {
    const activo = String(r.total_activo ?? periodo.total_activo ?? "0");
    const pasivo = String(r.total_pasivo ?? periodo.total_pasivo ?? "0");
    const patrimonio = String(r.total_patrimonio ?? periodo.total_patrimonio ?? "0");
    const ingresos = String(r.ingresos ?? periodo.total_ingresos ?? "0");
    const utilidad = String(r.utilidad_neta ?? periodo.utilidad ?? "0");
    const activoCorr = String(r.activo_corriente ?? "0");
    const pasivoCorr = String(r.pasivo_corriente ?? "0");
    const inventario = String(r.inventario_final ?? "0");
    return {
      activo, pasivo, patrimonio, ingresos, utilidad, activoCorr, pasivoCorr, inventario,
      efectivo: String(r.efectivo ?? "0"),
      costoVentas: String(r.costo_ventas ?? "0"),
      utilidadBruta: String(r.utilidad_bruta ?? "0"),
      utilidadOper: String(r.utilidad_operacional ?? "0"),
      // Capital de trabajo = activo corriente − pasivo corriente, resta exacta.
      capitalTrabajo: restar(activoCorr, pasivoCorr),
      corriente: razon(activoCorr, pasivoCorr),
      acida: razon(restar(activoCorr, inventario), pasivoCorr),
      endeudamiento: razon(pasivo, activo),
      margen: razon(utilidad, ingresos),
      margenBruto: razon(String(r.utilidad_bruta ?? "0"), ingresos),
    };
  }, [r, periodo]);

  const nomina = (datos?.nomina?.liquidaciones ?? []) as Record<string, unknown>[];
  const costoNomina = useMemo(
    () => (nomina.length ? sumar(...nomina.map((l) => String(l.costo_total ?? "0"))) : "0"),
    [nomina],
  );
  const productos = datos?.inventario?.productos ?? [];

  if (cargando) {
    return (
      <Tarjeta rotulo="Indicadores" titulo="Cargando el detalle del periodo…">
        <div className="grid gap-3 sm:grid-cols-4">
          {[0, 1, 2, 3].map((i) => (
            <div key={i} className="h-24 animate-pulse rounded-2xl bg-hoja-2" />
          ))}
        </div>
      </Tarjeta>
    );
  }
  if (!datos) return null;

  return (
    <div className="space-y-4">
      {/* ── ecuación contable + a dónde se fue el dinero ─────────────── */}
      <div className="grid gap-4 xl:grid-cols-[1.05fr_1fr]">
        <Tarjeta rotulo="Ecuación contable" titulo="">
          <AnilloBalance activo={m.activo} pasivo={m.pasivo} patrimonio={m.patrimonio} />
        </Tarjeta>

        <Tarjeta rotulo="Estructura del resultado" titulo="">
          <BarrasDesglose
            titulo="A dónde se fue el dinero"
            filas={[
              { nombre: "Costo de ventas", valor: m.costoVentas },
              { nombre: "Gastos de administración", valor: String(r.gastos_admin ?? "0") },
              { nombre: "Gastos de ventas", valor: String(r.gastos_ventas ?? "0") },
              { nombre: "Gastos no operacionales", valor: String(r.gastos_no_op ?? "0") },
              { nombre: "Impuesto de renta", valor: String(r.impuesto_renta ?? "0") },
            ]}
          />
          <div className="mt-4 grid grid-cols-2 gap-3 border-t border-linea pt-4">
            <Mini rotulo="Utilidad bruta" valor={m.utilidadBruta} />
            <Mini rotulo="Utilidad operacional" valor={m.utilidadOper} />
          </div>
        </Tarjeta>
      </div>

      {/* ── indicadores con su referencia ─────────────────────────────── */}
      <Tarjeta
        rotulo="Indicadores financieros"
        titulo="Cómo está parado el cliente"
        subtitulo="La marca negra en cada barra es el valor de referencia. El detalle con la fórmula de cada uno está en la pestaña «Estados financieros»."
      >
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <Medidor
            nombre="Razón corriente"
            valor={m.corriente === null ? "sin pasivo" : `${numero(m.corriente.toFixed(2))} veces`}
            texto="Activo corriente sobre pasivo corriente. Por debajo de 1 hay riesgo de no poder pagar."
            fraccion={m.corriente === null ? 1 : Math.min(m.corriente / 3, 1)}
            referencia={1 / 3}
            bueno="mayor"
          />
          <Medidor
            nombre="Prueba ácida"
            valor={m.acida === null ? "sin pasivo" : `${numero(m.acida.toFixed(2))} veces`}
            texto={
              n(m.inventario) === 0
                ? "Igual a la razón corriente porque este periodo no tiene inventario."
                : "Lo mismo pero sin contar el inventario: liquidez sin depender de vender."
            }
            fraccion={m.acida === null ? 1 : Math.min(Math.max(m.acida, 0) / 3, 1)}
            referencia={1 / 3}
            bueno="mayor"
          />
          <Medidor
            nombre="Endeudamiento"
            valor={m.endeudamiento === null ? "—" : porcentaje(String(m.endeudamiento))}
            texto="Qué parte del activo está financiada con deuda. Se avisa por encima del 70 %."
            fraccion={m.endeudamiento === null ? 0 : Math.min(Math.max(m.endeudamiento, 0), 1)}
            referencia={0.7}
            bueno="menor"
          />
          <Medidor
            nombre="Margen neto"
            valor={m.margen === null ? "sin ingresos" : porcentaje(String(m.margen))}
            texto="Utilidad neta sobre los ingresos del periodo."
            fraccion={m.margen === null ? 0 : Math.max(0, Math.min(m.margen, 1))}
            referencia={0.05}
            bueno="mayor"
          />
        </div>
      </Tarjeta>

      {/* ── liquidez, nómina e inventario ─────────────────────────────── */}
      <div className="grid gap-4 lg:grid-cols-3">
        <Tarjeta rotulo="Liquidez" titulo="">
          <dl className="space-y-3">
            <Fila nombre="Efectivo al cierre" valor={m.efectivo} />
            <Fila nombre="Activo corriente" valor={m.activoCorr} />
            <Fila nombre="Pasivo corriente" valor={m.pasivoCorr} />
            <Fila nombre="Capital de trabajo" valor={m.capitalTrabajo} resaltar />
          </dl>
        </Tarjeta>

        <Tarjeta rotulo="Nómina del periodo" titulo="">
          {nomina.length === 0 ? (
            <p className="text-sm text-gris">Este periodo no trae nómina.</p>
          ) : (
            <dl className="space-y-3">
              <Fila nombre="Empleados liquidados" texto={String(nomina.length)} />
              <Fila nombre="Costo total de nómina" valor={costoNomina} resaltar />
              <Fila
                nombre="Diferencias halladas"
                texto={String((datos.nomina?.auditoria ?? []).length)}
                alerta={(datos.nomina?.auditoria ?? []).length > 0}
              />
            </dl>
          )}
        </Tarjeta>

        <Tarjeta rotulo="Inventario" titulo="">
          {productos.length === 0 ? (
            <p className="text-sm text-gris">Este periodo no trae inventario.</p>
          ) : (
            <dl className="space-y-3">
              <Fila nombre="Productos en kardex" texto={String(productos.length)} />
              <Fila nombre="Saldo valorizado" valor={String(datos.inventario?.saldo_total ?? "0")} resaltar />
              <Fila nombre="Costo de ventas (kardex)" valor={String(datos.inventario?.costo_ventas ?? "0")} />
              <Fila
                nombre="Método"
                texto={datos.inventario?.metodo === "peps" ? "PEPS" : "Promedio ponderado"}
              />
            </dl>
          )}
        </Tarjeta>
      </div>

      {/* ── datos de la relación con el cliente ───────────────────────── */}
      <Tarjeta rotulo="Relación con el cliente" titulo="">
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <Mini rotulo="Honorarios mensuales" valor={cliente.honorarios_mes} />
          <Mini rotulo="Capital suscrito" valor={cliente.capital_suscrito} />
          <MiniTexto rotulo="Periodicidad pactada" texto={cliente.periodicidad} />
          <MiniTexto
            rotulo="Turno DIAN"
            texto={cliente.turno_dian ? `${cliente.turno_dian} de 10` : "—"}
            nota="Las fechas las fija un decreto cada año"
          />
        </div>
        {cliente.socios && cliente.socios.length > 0 && (
          <SociosDelCliente socios={cliente.socios} />
        )}
      </Tarjeta>
    </div>
  );
}

/* ── piezas ──────────────────────────────────────────────────────────── */
function Fila({
  nombre, valor, texto, resaltar, alerta,
}: {
  nombre: string;
  valor?: string;
  texto?: string;
  resaltar?: boolean;
  alerta?: boolean;
}) {
  return (
    <div className="flex items-baseline justify-between gap-3 border-b border-linea pb-2.5 last:border-0 last:pb-0">
      <dt className="recortar text-sm text-grafito">{nombre}</dt>
      <dd
        className={clases(
          "cifras shrink-0 text-sm",
          resaltar ? "font-bold text-tinta" : "text-grafito",
          valor !== undefined && esNegativo(valor) && "text-rojo",
          alerta && "font-bold text-ambar",
        )}
      >
        {valor !== undefined ? pesos(valor) : texto}
      </dd>
    </div>
  );
}

function Mini({ rotulo, valor }: { rotulo: string; valor: string }) {
  return (
    <div className="contener">
      <Rotulo className="block">{rotulo}</Rotulo>
      <p
        className={clases(
          "cifras cifra-flexible mt-1.5 text-lg font-bold leading-none",
          esNegativo(valor) ? "text-rojo" : "text-tinta",
        )}
      >
        {pesos(valor)}
      </p>
    </div>
  );
}

function MiniTexto({ rotulo, texto, nota }: { rotulo: string; texto: string; nota?: string }) {
  return (
    <div className="contener">
      <Rotulo className="block">{rotulo}</Rotulo>
      <p className="mt-1.5 text-lg font-bold capitalize leading-none text-tinta">{texto}</p>
      {nota && <p className="mt-1 text-[11px] text-gris">{nota}</p>}
    </div>
  );
}


/**
 * Socios del cliente. Si ninguno tiene capital registrado, se muestran solo los
 * nombres: una columna de "$ 0 de $ 0" no informa nada y ensucia la pantalla.
 */
function SociosDelCliente({ socios }: { socios: NonNullable<Cliente["socios"]> }) {
  // OJO: hay que usar `esCero`, no comparar la cadena. La base devuelve los
  // importes cuantizados a dos decimales, así que un cero llega como "0.00" y
  // `"0.00" !== "0"` da verdadero: con eso se pintaba una columna de "$ 0 de $ 0".
  const hayCapital = socios.some((s) => !esCero(s.comprometido) || !esCero(s.pagado));
  const totalPorPagar = hayCapital
    ? socios.reduce((acc, s) => {
        const saldo = restar(s.comprometido, s.pagado);
        return esNegativo(saldo) || esCero(saldo) ? acc : sumar(acc, saldo);
      }, "0")
    : "0";

  return (
    <div className="mt-5 border-t border-linea pt-4">
      <div className="mb-3 flex flex-wrap items-baseline justify-between gap-2">
        <Rotulo>{hayCapital ? "Socios y capital por pagar" : `Socios (${socios.length})`}</Rotulo>
        {hayCapital && !esCero(totalPorPagar) && (
          <span className="cifras text-sm font-semibold text-rojo">
            por cobrar {pesos(totalPorPagar)}
          </span>
        )}
      </div>

      {!hayCapital && (
        <p className="mb-3 text-xs text-gris">
          No hay aportes registrados en la ficha. Cárguelos para que el sistema avise si queda
          capital suscrito sin pagar.
        </p>
      )}

      <ul className={clases("gap-x-6 gap-y-2", hayCapital ? "space-y-2" : "grid sm:grid-cols-2")}>
        {socios.map((s, i) => {
          const saldo = restar(s.comprometido, s.pagado);
          const debe = hayCapital && !esNegativo(saldo) && !esCero(saldo);
          return (
            <li key={i} className="flex flex-wrap items-baseline justify-between gap-2 text-sm">
              <span className="recortar text-grafito">{s.nombre}</span>
              {hayCapital ? (
                <span className="shrink-0">
                  <span className="cifras text-gris">{pesos(s.pagado)}</span>
                  <span className="mx-1.5 text-gris">de</span>
                  <span className="cifras text-grafito">{pesos(s.comprometido)}</span>
                  {debe && (
                    <span className="cifras ml-2 font-semibold text-rojo">debe {pesos(saldo)}</span>
                  )}
                </span>
              ) : (
                s.cedula && <span className="cifras shrink-0 text-xs text-gris">C.C. {s.cedula}</span>
              )}
            </li>
          );
        })}
      </ul>
    </div>
  );
}
