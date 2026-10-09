import { useId, useMemo, useState } from "react";
import { clases, cmp, esNegativo, pesos, pesosCorto, periodoCorto, porcentaje, restar, sumar } from "../formato";
import type { Monto, Periodo } from "../tipos";
import { Rotulo } from "./ui";

/* ═══════════════════════════════════════════════════════════════════════════
   GRÁFICAS. Dibujadas en SVG, sin librerías.

   Reglas que se respetan en todas:
   · UN SOLO EJE por gráfica. Nunca dos escalas en el mismo dibujo.
   · Máximo TRES series categóricas. El validador de paletas rechazó el cuarto
     color: contra el azul daba ΔE 1,2 bajo protanopía, o sea indistinguible.
     Los desgloses de una sola medida van en un tono único con etiqueta directa.
   · El signo se lee por POSICIÓN además de por color (barras sobre o bajo el
     cero), para que también funcione sin distinguir colores.
   · Toda gráfica tiene su tabla equivalente.
   · Los importes se comparan como DECIMAL EXACTO; a número solo se pasa para
     calcular píxeles, nunca para mostrar una cifra.
   ═══════════════════════════════════════════════════════════════════════════ */

// Las series toman el color del cliente dentro de su ficha (8.3): --serie-1.
const SERIE_1 = "var(--serie-1)";
const SERIE_2 = "var(--ambar)";
const POSITIVO = "var(--azul-tinta)";
const ROJO = "var(--rojo)";

/** A número SOLO para geometría. Nunca para mostrar un importe. */
function px(v: Monto | null | undefined): number {
  if (v === null || v === undefined || v === "") return 0;
  const n = Number(v);
  return Number.isFinite(n) ? n : 0;
}

function absTexto(v: Monto | null | undefined): Monto {
  return String(v ?? "0").replace("-", "");
}

function maximo(valores: (Monto | null | undefined)[]): Monto {
  let mejor: Monto = "0";
  for (const v of valores) {
    const a = absTexto(v);
    if (cmp(a, mejor) > 0) mejor = a;
  }
  return mejor;
}

/* ═════════════════════════════════════════════════════════════════════════
   1. EVOLUCIÓN · dos líneas sobre el mismo eje (ingresos y gastos son pesos)
   ═════════════════════════════════════════════════════════════════════════ */
interface Punto {
  etiqueta: string;
  ingresos: Monto;
  gastos: Monto;
  utilidad: Monto;
}

export function GraficaEvolucion({ puntos }: { puntos: Punto[] }) {
  const [activo, setActivo] = useState<number | null>(null);
  const idT = useId();

  const tope = px(maximo(puntos.flatMap((p) => [p.ingresos, p.gastos]))) || 1;
  const H = 140;
  const borde = 12;
  const grupo = 100 / puntos.length;
  const anchoBarra = grupo * 0.36;

  return (
    <figure className="m-0 contener">
      <figcaption className="mb-3 flex flex-wrap items-center justify-between gap-3">
        <Rotulo id={idT}>Ingresos vs. Gastos (barras comparativas)</Rotulo>
        <div className="flex items-center gap-4">
          <Leyenda color={SERIE_1} texto="Ingresos" />
          <Leyenda color={SERIE_2} texto="Gastos" />
        </div>
      </figcaption>

      <div className="relative" onMouseLeave={() => setActivo(null)}>
        <svg viewBox={`0 0 100 ${H}`} preserveAspectRatio="none" role="img" aria-labelledby={idT} className="h-[140px] w-full">
          {[0, 0.25, 0.5, 0.75, 1].map((f) => (
            <line
              key={f}
              x1="0"
              x2="100"
              y1={H - borde - f * (H - borde * 2)}
              y2={H - borde - f * (H - borde * 2)}
              stroke="var(--rejilla)"
              strokeWidth="1"
              vectorEffect="non-scaling-stroke"
            />
          ))}

          {puntos.map((p, i) => {
            const xCentro = i * grupo + grupo / 2;
            const xIng = xCentro - anchoBarra - 0.5;
            const xGas = xCentro + 0.5;
            const hIng = Math.max((px(p.ingresos) / tope) * (H - borde * 2), 1.5);
            const hGas = Math.max((px(p.gastos) / tope) * (H - borde * 2), 1.5);
            const yIng = H - borde - hIng;
            const yGas = H - borde - hGas;
            const seleccionado = activo === i;

            return (
              <g key={i} onMouseEnter={() => setActivo(i)} className="cursor-pointer">
                {/* Zona de captura transparente */}
                <rect x={i * grupo} y={0} width={grupo} height={H} fill="transparent" />
                {/* Barra Ingresos */}
                <rect
                  x={xIng}
                  y={yIng}
                  width={anchoBarra}
                  height={hIng}
                  rx="1.5"
                  fill={SERIE_1}
                  opacity={activo === null || seleccionado ? 1 : 0.4}
                />
                {/* Barra Gastos */}
                <rect
                  x={xGas}
                  y={yGas}
                  width={anchoBarra}
                  height={hGas}
                  rx="1.5"
                  fill={SERIE_2}
                  opacity={activo === null || seleccionado ? 1 : 0.4}
                />
              </g>
            );
          })}

          <line x1="0" x2="100" y1={H - borde} y2={H - borde} stroke="var(--tinta)" strokeWidth="1.5" vectorEffect="non-scaling-stroke" />
        </svg>

        {activo !== null && (
          <Globo
            titulo={puntos[activo].etiqueta}
            posicion={(activo + 0.5) / puntos.length}
            filas={[
              ["Ingresos", puntos[activo].ingresos, SERIE_1],
              ["Gastos", puntos[activo].gastos, SERIE_2],
              [
                esNegativo(restar(puntos[activo].ingresos, puntos[activo].gastos)) ? "Déficit" : "Margen neto",
                restar(puntos[activo].ingresos, puntos[activo].gastos),
                esNegativo(restar(puntos[activo].ingresos, puntos[activo].gastos)) ? ROJO : POSITIVO,
              ],
            ]}
          />
        )}
      </div>

      <EjeX puntos={puntos} />
      <Rotulo className="mt-2 block">
        Tope del eje: {pesosCorto(maximo(puntos.flatMap((p) => [p.ingresos, p.gastos])))}
      </Rotulo>
    </figure>
  );
}

/* ═════════════════════════════════════════════════════════════════════════
   2. UTILIDAD · línea con cero de referencia
   ═════════════════════════════════════════════════════════════════════════ */
export function GraficaUtilidad({ puntos }: { puntos: Punto[] }) {
  const [activo, setActivo] = useState<number | null>(null);
  const idT = useId();

  const maxAbs = px(maximo(puntos.map((p) => p.utilidad))) || 1;
  const H = 140;
  const cero = H / 2;
  const A = 100;
  const margen = 10;

  const coord = (i: number, v: Monto) => {
    const x = puntos.length === 1 ? A / 2 : (i / (puntos.length - 1)) * (A - margen * 2) + margen;
    const num = px(v);
    const y = cero - (num / maxAbs) * (cero - 15);
    return [x, y] as const;
  };

  const ruta = puntos.map((p, i) => {
    const [x, y] = coord(i, p.utilidad);
    return `${i === 0 ? "M" : "L"}${x.toFixed(2)},${y.toFixed(2)}`;
  }).join(" ");

  return (
    <figure className="m-0 contener">
      <figcaption className="mb-3">
        <Rotulo id={idT}>Utilidad o pérdida neta (línea mensual)</Rotulo>
        <p className="mt-1 text-xs text-grafito">
          Sobre la línea central es utilidad neta; bajo la línea es pérdida.
        </p>
      </figcaption>

      <div className="relative" onMouseLeave={() => setActivo(null)}>
        <svg viewBox={`0 0 ${A} ${H}`} preserveAspectRatio="none" role="img" aria-labelledby={idT} className="h-[140px] w-full">
          {/* Línea cero */}
          <line x1="0" x2={A} y1={cero} y2={cero} stroke="var(--tinta)" strokeWidth="1.2" strokeDasharray="3 3" vectorEffect="non-scaling-stroke" />

          {/* Línea de utilidad */}
          <path
            d={ruta}
            fill="none"
            stroke="var(--azul-tinta)"
            strokeWidth="2.5"
            vectorEffect="non-scaling-stroke"
            strokeLinejoin="round"
            strokeLinecap="round"
          />

          {/* Marcadores circulares y zonas interactivas */}
          {puntos.map((p, i) => {
            const [x, y] = coord(i, p.utilidad);
            const neg = esNegativo(p.utilidad);
            const anchoZona = A / puntos.length;
            const seleccionado = activo === i;

            return (
              <g key={i} onMouseEnter={() => setActivo(i)} className="cursor-pointer">
                <rect x={x - anchoZona / 2} y={0} width={anchoZona} height={H} fill="transparent" />
                {seleccionado && (
                  <line x1={x} x2={x} y1={0} y2={H} stroke="var(--linea)" strokeWidth="1" vectorEffect="non-scaling-stroke" />
                )}
                <circle
                  cx={x}
                  cy={y}
                  r={seleccionado ? 4.5 : 3}
                  fill={neg ? ROJO : POSITIVO}
                  stroke="var(--papel)"
                  strokeWidth="1.5"
                  vectorEffect="non-scaling-stroke"
                />
              </g>
            );
          })}
        </svg>

        {activo !== null && (
          <Globo
            titulo={puntos[activo].etiqueta}
            posicion={puntos.length === 1 ? 0.5 : (activo / (puntos.length - 1))}
            filas={[[
              esNegativo(puntos[activo].utilidad) ? "Pérdida neta" : "Utilidad neta",
              puntos[activo].utilidad,
              esNegativo(puntos[activo].utilidad) ? ROJO : POSITIVO,
            ]]}
          />
        )}
      </div>

      <EjeX puntos={puntos} />
    </figure>
  );
}

/* ═════════════════════════════════════════════════════════════════════════
   3. ESTRUCTURA DEL BALANCE · desglose proporcional claro
      Pasivo + Patrimonio = Activo.
   ═════════════════════════════════════════════════════════════════════════ */
export function AnilloBalance({
  activo,
  pasivo,
  patrimonio,
}: {
  activo: Monto;
  pasivo: Monto;
  patrimonio: Monto;
}) {
  const total = px(activo);
  if (total <= 0) {
    return (
      <p className="py-6 text-center text-sm text-grafito">
        Sin activo registrado en este periodo.
      </p>
    );
  }

  const pctPasivo = Math.max(0, Math.min(100, (px(pasivo) / total) * 100));
  const pctPatrim = Math.max(0, Math.min(100, (px(patrimonio) / total) * 100));

  return (
    <figure className="m-0 contener">
      <figcaption className="mb-3">
        <Rotulo>Ecuación contable (Activo = Pasivo + Patrimonio)</Rotulo>
      </figcaption>

      {/* Barra proporcional horizontal limpia */}
      <div className="h-4 w-full overflow-hidden rounded-full bg-hoja flex border border-linea">
        <div
          style={{ width: `${pctPasivo}%`, background: SERIE_2 }}
          title={`Pasivo: ${pesos(pasivo)} (${pctPasivo.toFixed(1)}%)`}
          className="h-full transition-all"
        />
        <div
          style={{ width: `${pctPatrim}%`, background: POSITIVO }}
          title={`Patrimonio: ${pesos(patrimonio)} (${pctPatrim.toFixed(1)}%)`}
          className="h-full transition-all"
        />
      </div>

      <dl className="mt-4 grid grid-cols-1 gap-3 text-left sm:grid-cols-3">
        <div className="rounded-xl border border-linea bg-papel p-3">
          <dt className="rotulo flex items-center gap-1.5 text-grafito">
            <span className="h-2 w-2 rounded-full" style={{ background: SERIE_2 }} />
            Pasivo
          </dt>
          <dd className="cifras mt-1 text-base font-bold text-tinta">{pesos(pasivo)}</dd>
          <span className="t-small text-gris">{pctPasivo.toFixed(1)}%</span>
        </div>
        <div className="rounded-xl border border-linea bg-papel p-3">
          <dt className="rotulo flex items-center gap-1.5 text-grafito">
            <span className="h-2 w-2 rounded-full" style={{ background: POSITIVO }} />
            Patrimonio
          </dt>
          <dd className="cifras mt-1 text-base font-bold text-tinta">{pesos(patrimonio)}</dd>
          <span className="t-small text-gris">{pctPatrim.toFixed(1)}%</span>
        </div>
        <div className="rounded-xl border border-linea bg-hoja p-3">
          <dt className="rotulo text-tinta">Activo total</dt>
          <dd className="cifras mt-1 text-base font-bold text-azul">{pesos(activo)}</dd>
          <span className="t-small text-gris">100.0%</span>
        </div>
      </dl>
    </figure>
  );
}

/* ═════════════════════════════════════════════════════════════════════════
   4. DESGLOSE · barras horizontales de una sola medida
   ═════════════════════════════════════════════════════════════════════════ */
export function BarrasDesglose({
  titulo,
  filas,
  color = SERIE_1,
}: {
  titulo: string;
  filas: { nombre: string; valor: Monto }[];
  color?: string;
}) {
  const idT = useId();
  const utiles = filas.filter((f) => cmp(absTexto(f.valor), "0") > 0);
  if (!utiles.length) {
    return (
      <figure className="m-0">
        <Rotulo>{titulo}</Rotulo>
        <p className="mt-2 text-sm text-grafito">Sin valores en este periodo.</p>
      </figure>
    );
  }
  const tope = px(maximo(utiles.map((f) => f.valor))) || 1;
  const total = sumar(...utiles.map((f) => f.valor));

  return (
    <figure className="m-0 contener">
      <figcaption className="mb-3">
        <Rotulo id={idT}>{titulo}</Rotulo>
      </figcaption>
      <ul className="space-y-2.5" aria-labelledby={idT}>
        {utiles.map((f) => {
          const ancho = Math.max((px(f.valor) / tope) * 100, 1.5);
          return (
            <li key={f.nombre} className="contener">
              <div className="flex items-baseline justify-between gap-3">
                <span className="recortar text-sm text-grafito">{f.nombre}</span>
                <span className="cifras shrink-0 text-sm font-semibold">{pesos(f.valor)}</span>
              </div>
              <div className="mt-1 h-2 overflow-hidden rounded-full bg-hoja">
                <div className="h-full rounded-full" style={{ width: `${ancho}%`, background: color }} />
              </div>
            </li>
          );
        })}
      </ul>
      <div className="mt-3 flex items-baseline justify-between gap-3 border-t border-linea pt-2.5">
        <span className="rotulo">Total</span>
        <span className="cifras text-sm font-bold">{pesos(total)}</span>
      </div>
    </figure>
  );
}

/* ═════════════════════════════════════════════════════════════════════════
   5. MEDIDOR · indicador claro con estado
   ═════════════════════════════════════════════════════════════════════════ */
export function Medidor({
  nombre,
  valor,
  texto,
  fraccion,
  referencia,
  bueno = "mayor",
}: {
  nombre: string;
  valor: string;
  texto?: string;
  fraccion: number;
  referencia?: number;
  bueno?: "mayor" | "menor";
}) {
  const f = Math.max(0, Math.min(1, fraccion));
  const sano = bueno === "mayor" ? f >= (referencia ?? 0.5) : f <= (referencia ?? 0.5);
  return (
    <div className="contener rounded-2xl border border-linea bg-papel p-4">
      <div className="flex items-center justify-between">
        <Rotulo className="block">{nombre}</Rotulo>
        <span className={clases("inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-medium",
          sano ? "bg-azul-suave text-azul-tinta" : "bg-ambar-suave text-ambar")}>
          {sano ? "Normal" : "Atención"}
        </span>
      </div>
      <p className={clases("cifras mt-2 text-2xl font-bold leading-none",
        sano ? "text-tinta" : "text-ambar")}>
        {valor}
      </p>
      {texto && <p className="mt-2 text-xs text-grafito">{texto}</p>}
    </div>
  );
}

/* ═════════════════════════════════════════════════════════════════════════
   Piezas compartidas
   ═════════════════════════════════════════════════════════════════════════ */
function Leyenda({ color, texto }: { color: string; texto: string }) {
  return (
    <span className="flex items-center gap-1.5">
      <span aria-hidden className="h-2.5 w-2.5 rounded-sm" style={{ background: color }} />
      <span className="rotulo">{texto}</span>
    </span>
  );
}

function EjeX({ puntos }: { puntos: { etiqueta: string }[] }) {
  // Con muchos periodos solo se rotulan algunos, para que no se encimen.
  const salto = Math.max(1, Math.ceil(puntos.length / 6));
  return (
    <div className="mt-1.5 flex" aria-hidden>
      {puntos.map((p, i) => (
        <span
          key={i}
          className="rotulo flex-1 truncate text-center !text-[9px]"
          style={{ visibility: i % salto === 0 || i === puntos.length - 1 ? "visible" : "hidden" }}
        >
          {p.etiqueta}
        </span>
      ))}
    </div>
  );
}

function Globo({
  titulo, posicion, filas,
}: {
  titulo: string;
  posicion: number;
  filas: [string, Monto, string][];
}) {
  const izquierda = posicion > 0.55;
  return (
    <div
      role="tooltip"
      className="material-hoja pointer-events-none absolute top-1 z-10 w-max max-w-[15rem] rounded-xl px-3 py-2"
      style={izquierda ? { right: `${(1 - posicion) * 100}%` } : { left: `${posicion * 100}%` }}
    >
      <Rotulo className="block">{titulo}</Rotulo>
      <table className="mt-1.5">
        <tbody>
          {filas.map(([nombre, valor, color]) => (
            <tr key={nombre}>
              <td className="pr-3">
                <span className="flex items-center gap-1.5 text-xs text-grafito">
                  <span aria-hidden className="h-2 w-2 rounded-sm" style={{ background: color }} />
                  {nombre}
                </span>
              </td>
              <td className="cifras text-right text-xs font-semibold text-tinta">{pesos(valor)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/* ═════════════════════════════════════════════════════════════════════════
   Panel completo del histórico + su tabla equivalente
   ═════════════════════════════════════════════════════════════════════════ */
export function GraficaHistorico({ serie }: { serie: Periodo[] }) {
  const puntos: Punto[] = useMemo(
    () => serie.map((p) => ({
      etiqueta: periodoCorto(p.desde, p.hasta),
      ingresos: p.total_ingresos ?? "0",
      gastos: p.total_gastos ?? "0",
      utilidad: p.utilidad ?? "0",
    })),
    [serie],
  );

  if (puntos.length < 2) {
    return (
      <p className="py-8 text-center text-sm text-grafito">
        Hace falta más de un periodo calculado para dibujar la evolución.
      </p>
    );
  }

  const ultimo = serie[serie.length - 1];
  const anterior = serie[serie.length - 2];
  const variacion = restar(ultimo.total_ingresos ?? "0", anterior.total_ingresos ?? "0");

  return (
    <div className="space-y-8">
      <GraficaEvolucion puntos={puntos} />
      <GraficaUtilidad puntos={puntos} />
      <div className="flex flex-wrap items-center gap-2 border-t border-linea pt-4">
        <Rotulo>Contra el periodo anterior</Rotulo>
        <span className={clases("cifras text-sm font-semibold", esNegativo(variacion) ? "text-rojo" : "text-azul")}>
          {esNegativo(variacion) ? "" : "+"}{pesos(variacion)} en ingresos
        </span>
      </div>
    </div>
  );
}

export function TablaHistorico({ serie }: { serie: Periodo[] }) {
  return (
    <table className="w-full border-collapse text-sm">
      <thead>
        <tr>
          {["Periodo", "Ingresos", "Gastos", "Utilidad"].map((t, i) => (
            <th key={t} className={clases(
              "rotulo border-b border-tinta/20 px-3 py-2 !text-tinta",
              i === 0 ? "text-left" : "text-right",
            )}>
              {t}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {serie.map((p) => (
          <tr key={p.id}>
            <td className="border-b border-linea px-3 py-2">{periodoCorto(p.desde, p.hasta)}</td>
            <td className="cifras border-b border-linea px-3 py-2 text-right">{pesos(p.total_ingresos)}</td>
            <td className="cifras border-b border-linea px-3 py-2 text-right">{pesos(p.total_gastos)}</td>
            <td className={clases(
              "cifras border-b border-linea px-3 py-2 text-right font-semibold",
              esNegativo(p.utilidad) ? "text-rojo" : "text-azul",
            )}>
              {pesos(p.utilidad)}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
