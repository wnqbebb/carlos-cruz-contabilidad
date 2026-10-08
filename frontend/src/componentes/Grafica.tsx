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
const SERIE_3 = "var(--esfera-3)";
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
  const idDeg = useId();

  const tope = px(maximo(puntos.flatMap((p) => [p.ingresos, p.gastos]))) || 1;
  const A = 100;   // ancho del lienzo
  const H = 150;   // alto
  const borde = 8;

  const coord = (i: number, v: Monto) => {
    const x = puntos.length === 1 ? A / 2 : (i / (puntos.length - 1)) * A;
    const y = H - borde - (px(v) / tope) * (H - borde * 2);
    return [x, y] as const;
  };

  const ruta = (clave: "ingresos" | "gastos") =>
    puntos.map((p, i) => {
      const [x, y] = coord(i, p[clave]);
      return `${i === 0 ? "M" : "L"}${x.toFixed(2)},${y.toFixed(2)}`;
    }).join(" ");

  const area = `${ruta("ingresos")} L${A},${H} L0,${H} Z`;

  return (
    <figure className="m-0 contener">
      <figcaption className="mb-3 flex flex-wrap items-center justify-between gap-3">
        <Rotulo id={idT}>Ingresos y gastos por periodo</Rotulo>
        <div className="flex items-center gap-4">
          <Leyenda color={SERIE_1} texto="Ingresos" />
          <Leyenda color={SERIE_2} texto="Gastos" />
        </div>
      </figcaption>

      <div className="relative" onMouseLeave={() => setActivo(null)}>
        <svg viewBox={`0 0 ${A} ${H}`} preserveAspectRatio="none" role="img" aria-labelledby={idT} className="h-[150px] w-full">
          <defs>
            <linearGradient id={idDeg} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="var(--serie-1)" stopOpacity="0.28" />
              <stop offset="100%" stopColor="var(--serie-1)" stopOpacity="0" />
            </linearGradient>
          </defs>

          {[0, 0.25, 0.5, 0.75, 1].map((f) => (
            <line key={f} x1="0" x2={A} y1={H - borde - f * (H - borde * 2)} y2={H - borde - f * (H - borde * 2)}
              stroke="var(--rejilla)" strokeWidth="1" vectorEffect="non-scaling-stroke" />
          ))}

          <path d={area} fill={`url(#${idDeg})`} />
          <path d={ruta("ingresos")} fill="none" stroke={SERIE_1} strokeWidth="2"
            vectorEffect="non-scaling-stroke" strokeLinejoin="round" strokeLinecap="round" />
          <path d={ruta("gastos")} fill="none" stroke={SERIE_2} strokeWidth="2" strokeDasharray="5 3"
            vectorEffect="non-scaling-stroke" strokeLinejoin="round" strokeLinecap="round" />

          {/* zonas sensibles y marcadores */}
          {puntos.map((p, i) => {
            const [xi, yi] = coord(i, p.ingresos);
            const [, yg] = coord(i, p.gastos);
            const ancho = A / puntos.length;
            return (
              <g key={i} onMouseEnter={() => setActivo(i)}>
                <rect x={xi - ancho / 2} y={0} width={ancho} height={H} fill="transparent" />
                {activo === i && (
                  <line x1={xi} x2={xi} y1={0} y2={H} stroke="var(--tinta)" strokeWidth="1"
                    strokeDasharray="3 3" vectorEffect="non-scaling-stroke" />
                )}
                <circle cx={xi} cy={yi} r={activo === i ? 3.2 : 2.2} fill={SERIE_1}
                  stroke="var(--papel)" strokeWidth="1.4" vectorEffect="non-scaling-stroke" />
                <circle cx={xi} cy={yg} r={activo === i ? 3.2 : 2.2} fill={SERIE_2}
                  stroke="var(--papel)" strokeWidth="1.4" vectorEffect="non-scaling-stroke" />
              </g>
            );
          })}

          <line x1="0" x2={A} y1={H} y2={H} stroke="var(--tinta)" strokeWidth="1.5" vectorEffect="non-scaling-stroke" />
        </svg>

        {activo !== null && (
          <Globo
            titulo={puntos[activo].etiqueta}
            posicion={puntos.length === 1 ? 0.5 : activo / (puntos.length - 1)}
            filas={[
              ["Ingresos", puntos[activo].ingresos, SERIE_1],
              ["Gastos", puntos[activo].gastos, SERIE_2],
              [esNegativo(puntos[activo].utilidad) ? "Pérdida" : "Utilidad",
               puntos[activo].utilidad,
               esNegativo(puntos[activo].utilidad) ? ROJO : POSITIVO],
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
   2. UTILIDAD · barras divergentes con línea de cero
   ═════════════════════════════════════════════════════════════════════════ */
export function GraficaUtilidad({ puntos }: { puntos: Punto[] }) {
  const [activo, setActivo] = useState<number | null>(null);
  const idT = useId();

  const tope = px(maximo(puntos.map((p) => p.utilidad))) || 1;
  const H = 130;
  const cero = H / 2;
  const grupo = 100 / puntos.length;

  return (
    <figure className="m-0 contener">
      <figcaption className="mb-3">
        <Rotulo id={idT}>Resultado de cada periodo</Rotulo>
        <p className="mt-1 text-xs text-grafito">
          Arriba del cero es utilidad; abajo, pérdida.
        </p>
      </figcaption>

      <div className="relative" onMouseLeave={() => setActivo(null)}>
        <svg viewBox={`0 0 100 ${H}`} preserveAspectRatio="none" role="img" aria-labelledby={idT} className="h-[130px] w-full">
          {puntos.map((p, i) => {
            const x = i * grupo;
            const ancho = grupo * 0.52;
            const v = px(p.utilidad);
            const alto = (Math.abs(v) / tope) * (cero - 5);
            const neg = v < 0;
            return (
              <g key={i} onMouseEnter={() => setActivo(i)}>
                <rect x={x} y={0} width={grupo} height={H} fill="transparent" />
                <rect
                  x={x + (grupo - ancho) / 2}
                  y={neg ? cero : cero - alto}
                  width={ancho}
                  height={Math.max(alto, 1.2)}
                  rx="1"
                  fill={neg ? ROJO : POSITIVO}
                  opacity={activo === null || activo === i ? 1 : 0.35}
                />
              </g>
            );
          })}
          <line x1="0" x2="100" y1={cero} y2={cero} stroke="var(--tinta)" strokeWidth="1.5" vectorEffect="non-scaling-stroke" />
        </svg>

        {activo !== null && (
          <Globo
            titulo={puntos[activo].etiqueta}
            posicion={(activo + 0.5) / puntos.length}
            filas={[[
              esNegativo(puntos[activo].utilidad) ? "Pérdida" : "Utilidad",
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
   3. ESTRUCTURA DEL BALANCE · anillo de dos porciones
      Pasivo + Patrimonio = Activo. Es la ecuación contable, dibujada.
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
  const idT = useId();
  const total = px(activo);
  if (total <= 0) {
    return (
      <p className="py-6 text-center text-sm text-grafito">
        Sin activo registrado en este periodo.
      </p>
    );
  }

  const fPasivo = Math.max(0, Math.min(1, px(pasivo) / total));
  const fPatrim = Math.max(0, Math.min(1, px(patrimonio) / total));
  const radio = 42;
  const circunf = 2 * Math.PI * radio;
  // 2 px de aire entre porciones, como pide el sistema de marcas.
  const hueco = 1.4;

  return (
    <figure className="m-0 contener">
      <figcaption className="mb-3">
        <Rotulo id={idT}>Estructura del balance</Rotulo>
      </figcaption>

      <div className="flex flex-wrap items-center gap-6">
        <div className="relative h-[150px] w-[150px] shrink-0">
          <svg viewBox="0 0 110 110" role="img" aria-labelledby={idT} className="h-full w-full -rotate-90">
            <circle cx="55" cy="55" r={radio} fill="none" stroke="var(--rejilla)" strokeWidth="13" />
            <circle
              cx="55" cy="55" r={radio} fill="none" stroke={SERIE_2} strokeWidth="13"
              strokeDasharray={`${Math.max(fPasivo * circunf - hueco, 0)} ${circunf}`}
              strokeLinecap="butt"
            />
            <circle
              cx="55" cy="55" r={radio} fill="none" stroke={POSITIVO} strokeWidth="13"
              strokeDasharray={`${Math.max(fPatrim * circunf - hueco, 0)} ${circunf}`}
              strokeDashoffset={-fPasivo * circunf}
              strokeLinecap="butt"
            />
          </svg>
          <div className="absolute inset-0 flex flex-col items-center justify-center text-center">
            <Rotulo className="!text-[9px]">Activo</Rotulo>
            <span className="cifras mt-0.5 text-[15px] font-bold leading-none">{pesos(activo)}</span>
          </div>
        </div>

        <dl className="contener min-w-[11rem] flex-1 space-y-2.5">
          <FilaAnillo color={SERIE_2} nombre="Pasivo" valor={pasivo} fraccion={fPasivo} />
          <FilaAnillo color={POSITIVO} nombre="Patrimonio" valor={patrimonio} fraccion={fPatrim} />
          <div className="flex items-baseline justify-between gap-3 border-t border-linea pt-2.5">
            <dt className="rotulo">Activo total</dt>
            <dd className="cifras text-sm font-bold">{pesos(activo)}</dd>
          </div>
        </dl>
      </div>
    </figure>
  );
}

function FilaAnillo({
  color, nombre, valor, fraccion,
}: { color: string; nombre: string; valor: Monto; fraccion: number }) {
  return (
    <div className="flex items-baseline justify-between gap-3">
      <dt className="flex min-w-0 items-center gap-2">
        <span aria-hidden className="h-2.5 w-2.5 shrink-0 rounded-sm" style={{ background: color }} />
        <span className="recortar text-sm text-grafito">{nombre}</span>
      </dt>
      <dd className="shrink-0 text-right">
        <span className="cifras text-sm font-semibold">{pesos(valor)}</span>
        <span className="rotulo ml-2">{porcentaje(String(fraccion))}</span>
      </dd>
    </div>
  );
}

/* ═════════════════════════════════════════════════════════════════════════
   4. DESGLOSE · barras horizontales de una sola medida
      Un solo tono: la identidad la da la etiqueta de cada fila, no el color.
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
   5. MEDIDOR · un indicador con su referencia
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
  /** 0 a 1: hasta dónde se llena la barra. */
  fraccion: number;
  /** Marca de referencia, también 0 a 1. */
  referencia?: number;
  /** Si "mayor" es mejor o peor, para decidir el color. */
  bueno?: "mayor" | "menor";
}) {
  const f = Math.max(0, Math.min(1, fraccion));
  const sano = bueno === "mayor" ? f >= (referencia ?? 0.5) : f <= (referencia ?? 0.5);
  return (
    <div className="contener rounded-2xl border border-linea bg-papel p-4">
      <Rotulo className="block">{nombre}</Rotulo>
      <p className={clases("cifras cifra-flexible mt-1.5 text-xl font-bold leading-none",
        sano ? "text-azul" : "text-ambar")}>
        {valor}
      </p>
      <div className="relative mt-3 h-2 overflow-hidden rounded-full bg-hoja">
        <div
          className="h-full rounded-full transition-[width] duration-500"
          style={{ width: `${f * 100}%`, background: sano ? "var(--azul-tinta)" : "var(--ambar)" }}
        />
        {referencia !== undefined && (
          <span
            aria-hidden
            className="absolute top-0 h-full w-[2px] bg-tinta"
            style={{ left: `${Math.max(0, Math.min(1, referencia)) * 100}%` }}
          />
        )}
      </div>
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
