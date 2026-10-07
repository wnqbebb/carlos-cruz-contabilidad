import { useState, type ReactNode } from "react";
import { clases, cmp, type Importe } from "../formato";
import { Cifra } from "./Cifra";
import { InsigniaEstado } from "./Insignia";
import { Interruptor } from "./Interruptor";

/**
 * TablaContable (spec 6.5) — balance de prueba, ajustes, definitivo, mayor.
 *
 * · Encabezado pegajoso; columnas D/H agrupadas bajo una cabecera común.
 * · Cifras a la derecha con tabular-nums; código PUC en mono.
 * · Sangría por nivel PUC (clase / grupo / cuenta / subcuenta / auxiliar) con
 *   peso tipográfico decreciente.
 * · Hover de fila en --hoja-2, sin cebra.
 * · Totales con doble línea inferior y la insignia Cuadra / Descuadre al lado.
 * · Saldo contrario a la naturaleza: punto rojo con explicación.
 * · Selector de densidad cómoda / compacta.
 *
 * Registro «Taller»: sin animación de entrada.
 */

export type ColumnaContable = {
  clave: string;
  titulo: string;
  /** Columnas con el mismo grupo comparten cabecera (p. ej. «Movimiento»). */
  grupo?: string;
};

export type FilaContable = {
  codigo?: string;
  nombre: ReactNode;
  valores: Record<string, Importe>;
  /** Si se omite, sale del largo del código PUC. */
  nivel?: number;
  /** Texto del aviso cuando el saldo va contra la naturaleza de la cuenta. */
  contraria?: string;
};

/** Nivel PUC por largo del código: 1 clase · 2 grupo · 4 cuenta · 6 subcuenta · 8+ auxiliar. */
export function nivelPuc(codigo?: string): number {
  const n = (codigo ?? "").replace(/\D/g, "").length;
  if (n <= 1) return 0;
  if (n <= 2) return 1;
  if (n <= 4) return 2;
  if (n <= 6) return 3;
  return 4;
}

/**
 * ¿El saldo va contra la naturaleza de la cuenta? La naturaleza NO se calcula
 * aquí: la manda el backend («D» / «C»), que ya conoce las excepciones del PUC
 * (1592 depreciación, 1299 provisiones, 4175 devoluciones…). Se compara texto
 * con `cmp`, sin floats. Devuelve el aviso listo para mostrar, o undefined.
 */
export function avisoSaldoContrario(
  naturaleza: "D" | "C" | string | undefined,
  debito: Importe,
  credito: Importe,
): string | undefined {
  const orden = cmp(debito, credito);
  if (naturaleza === "D" && orden < 0) return "Saldo crédito en una cuenta de naturaleza débito. Revise el registro.";
  if (naturaleza === "C" && orden > 0) return "Saldo débito en una cuenta de naturaleza crédito. Revise el registro.";
  return undefined;
}

const PESO = ["font-semibold text-tinta", "font-semibold text-tinta", "font-medium text-tinta", "text-grafito", "text-gris"];

export function TablaContable({
  columnas,
  filas,
  totales,
  cuadra,
  textoDescuadre,
  titulo,
  alturaMaxima = "70vh",
  parentesis = false,
  vacio = "No hay movimientos para mostrar.",
}: {
  columnas: ColumnaContable[];
  filas: FilaContable[];
  totales?: Record<string, Importe>;
  /** true → insignia Cuadra; false → Descuadre; undefined → sin insignia. */
  cuadra?: boolean;
  textoDescuadre?: string;
  titulo?: ReactNode;
  alturaMaxima?: string;
  /** Negativos entre paréntesis (estados financieros). */
  parentesis?: boolean;
  vacio?: string;
}) {
  const [densidad, setDensidad] = useState<"comoda" | "compacta">("comoda");
  const celda = densidad === "comoda" ? "py-2.5" : "py-1";

  // Grupos consecutivos para la primera fila de cabecera.
  const grupos: { titulo?: string; span: number }[] = [];
  for (const c of columnas) {
    const ult = grupos[grupos.length - 1];
    if (ult && c.grupo && ult.titulo === c.grupo) ult.span += 1;
    else grupos.push({ titulo: c.grupo, span: 1 });
  }
  const hayGrupos = columnas.some((c) => c.grupo);

  return (
    <section className="material-hoja contener overflow-hidden">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-linea px-5 py-3">
        <div className="t-h2 min-w-0 text-tinta">{titulo}</div>
        <Interruptor
          etiqueta="Densidad de la tabla"
          tamano="sm"
          valor={densidad}
          onCambio={setDensidad}
          opciones={[
            { valor: "comoda", texto: "Cómoda" },
            { valor: "compacta", texto: "Compacta" },
          ]}
        />
      </div>

      <div className="barra-fina overflow-auto" style={{ maxHeight: alturaMaxima }}>
        <table className="t-tabla w-full min-w-[640px] border-separate border-spacing-0">
          <thead className="sticky top-0 z-10 bg-hoja">
            {hayGrupos && (
              <tr>
                <th colSpan={2} className="border-b border-linea" />
                {grupos.map((g, i) => (
                  <th
                    key={i}
                    colSpan={g.span}
                    scope="colgroup"
                    className={clases(
                      "t-meta px-4 pt-3 pb-1 text-center text-gris",
                      g.titulo && "border-b border-linea",
                    )}
                  >
                    {g.titulo}
                  </th>
                ))}
              </tr>
            )}
            <tr>
              <th scope="col" className="t-meta w-[110px] border-b border-linea px-5 py-2.5 text-left text-gris">Código</th>
              <th scope="col" className="t-meta border-b border-linea px-4 py-2.5 text-left text-gris">Cuenta</th>
              {columnas.map((c) => (
                <th key={c.clave} scope="col" className="t-meta border-b border-linea px-4 py-2.5 text-right text-gris whitespace-nowrap">
                  {c.titulo}
                </th>
              ))}
            </tr>
          </thead>

          <tbody>
            {filas.length === 0 && (
              <tr>
                <td colSpan={columnas.length + 2} className="px-5 py-10 text-center text-gris">{vacio}</td>
              </tr>
            )}
            {filas.map((f, i) => {
              const nivel = f.nivel ?? nivelPuc(f.codigo);
              return (
                <tr key={(f.codigo ?? "") + i} className="transition-colors duration-150 hover:bg-hoja-2">
                  <td className={clases("codigo border-b border-linea px-5 align-top text-grafito", celda)}>
                    {f.codigo}
                  </td>
                  <td className={clases("border-b border-linea px-4 align-top", celda, PESO[nivel])}>
                    <span className="flex items-center gap-2" style={{ paddingLeft: nivel * 16 }}>
                      <span className="min-w-0">{f.nombre}</span>
                      {f.contraria && (
                        <span
                          className="inline-flex h-2 w-2 shrink-0 rounded-full bg-rojo"
                          title={f.contraria}
                          role="img"
                          aria-label={f.contraria}
                        />
                      )}
                    </span>
                  </td>
                  {columnas.map((c) => (
                    <td key={c.clave} className={clases("border-b border-linea px-4 text-right align-top", celda)}>
                      <Cifra valor={f.valores[c.clave]} tamano="tabla" simbolo={false} parentesis={parentesis} />
                    </td>
                  ))}
                </tr>
              );
            })}
          </tbody>

          {totales && (
            <tfoot>
              <tr className="fila-totales">
                <td className="px-5 py-3" />
                <td className="px-4 py-3 font-semibold text-tinta">
                  <span className="flex flex-wrap items-center gap-2">
                    Totales
                    {cuadra === true && <InsigniaEstado estado="cuadra" />}
                    {cuadra === false && <InsigniaEstado estado="descuadre">{textoDescuadre ?? "Descuadre"}</InsigniaEstado>}
                  </span>
                </td>
                {columnas.map((c) => (
                  <td key={c.clave} className="px-4 py-3 text-right font-semibold">
                    <Cifra valor={totales[c.clave]} tamano="tabla" simbolo={false} parentesis={parentesis} neutra />
                  </td>
                ))}
              </tr>
            </tfoot>
          )}
        </table>
      </div>
    </section>
  );
}
