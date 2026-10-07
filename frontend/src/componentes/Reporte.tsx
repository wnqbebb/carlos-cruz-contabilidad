import { Info } from "lucide-react";
import { useState } from "react";
import type { Reporte as TReporte } from "../tipos";
import { cant, clases, esNegativo, numero } from "../formato";
import { InsigniaEstado, Interruptor } from "../ui";

/**
 * Informe contable con el lenguaje de TablaContable (spec 6.5).
 *
 * · Encabezado pegajoso; columnas «… débito / … crédito» agrupadas bajo una
 *   cabecera común («Saldo inicial», «Movimiento»…).
 * · Código PUC en mono, sangría por nivel, peso tipográfico según el tipo de
 *   fila. Hover en --hoja-2, sin cebra.
 * · Totales con línea superior y doble línea inferior, como el libro.
 * · Negativos en rojo y entre paréntesis (convención de estados financieros).
 * · Saldo contrario a la naturaleza: punto rojo. El dato lo da el backend
 *   (`cuentas_t[].contraria`); aquí solo se dibuja.
 * · `documento`: sin cabecera ni selector, para el estado financiero en hoja.
 */
export function Reporte({
  rep,
  compacto,
  documento,
  contrarias,
  destacarCuadra,
}: {
  rep: TReporte;
  compacto?: boolean;
  documento?: boolean;
  /** Códigos PUC con saldo contrario a su naturaleza. */
  contrarias?: Set<string>;
  /** Insignia «Cuadra» en azul sólido (solo una por vista). */
  destacarCuadra?: boolean;
}) {
  const [densidad, setDensidad] = useState<"comoda" | "compacta">("comoda");
  if (!rep) return null;
  const cuadra = rep.verificacion?.cuadra;
  const celda = densidad === "comoda" || documento ? "py-2.5" : "py-1";

  // Agrupar «Saldo inicial débito» + «Saldo inicial crédito» bajo «Saldo inicial».
  const partes = rep.columnas.map((c) => {
    const m = /^(.*\S)\s+(débito|crédito|debito|credito)$/i.exec(c.titulo.trim());
    return m ? { grupo: m[1], corto: m[2][0].toUpperCase() + m[2].slice(1).toLowerCase() } : { grupo: "", corto: c.titulo };
  });
  const grupos: { titulo: string; span: number }[] = [];
  partes.forEach((p) => {
    const ult = grupos[grupos.length - 1];
    if (ult && p.grupo && ult.titulo === p.grupo) ult.span += 1;
    else grupos.push({ titulo: p.grupo, span: 1 });
  });
  const hayGrupos = partes.some((p) => p.grupo);
  const claveCodigo = rep.columnas.find((c) => c.clave === "codigo")?.clave;

  const insignia =
    cuadra === undefined ? null : cuadra ? (
      <InsigniaEstado estado="cuadra" discreta={!destacarCuadra} />
    ) : (
      <InsigniaEstado estado="descuadre">Requiere revisión</InsigniaEstado>
    );

  return (
    <div className="space-y-4">
      {!compacto && !documento && (
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div className="min-w-0">
            <h3 className="t-h2 text-tinta">{tituloLegible(rep.titulo)}</h3>
            {rep.subtitulo && <p className="t-small mt-1 text-gris">{rep.subtitulo}</p>}
          </div>
          <div className="flex flex-wrap items-center gap-3">
            {insignia}
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
        </div>
      )}

      <div className={clases("barra-fina overflow-x-auto", !documento && "material-hoja max-h-[72vh] overflow-y-auto")}>
        <table className="t-tabla w-full min-w-[640px] border-separate border-spacing-0">
          <thead className={clases(!documento && "sticky top-0 z-10", "bg-hoja")}>
            {hayGrupos && (
              <tr>
                {grupos.map((g, i) => (
                  <th
                    key={i}
                    colSpan={g.span}
                    scope={g.titulo ? "colgroup" : undefined}
                    className={clases("t-meta px-4 pt-3 pb-1 text-center text-gris", g.titulo && "border-b border-linea")}
                  >
                    {g.titulo}
                  </th>
                ))}
              </tr>
            )}
            <tr>
              {rep.columnas.map((c, i) => (
                <th
                  key={c.clave}
                  scope="col"
                  className={clases(
                    "t-meta border-b border-tinta/30 px-4 py-2.5 text-gris",
                    c.tipo === "texto" ? "text-left" : "text-right whitespace-nowrap",
                    i === 0 && "pl-5",
                  )}
                >
                  {partes[i].corto}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rep.filas.map((f, i) => {
              if (f.tipo === "vacia") {
                return (
                  <tr key={i} aria-hidden>
                    <td colSpan={rep.columnas.length} className="h-3" />
                  </tr>
                );
              }
              const esTotal = f.tipo === "total";
              const etiqueta = rep.columnas
                .filter((c) => c.tipo === "texto" && c.clave !== claveCodigo)
                .map((c) => String(f.valores[c.clave] ?? ""))
                .join(" ");
              const esResultado = /utilidad|p[ée]rdida|resultado|excedente|d[ée]ficit/i.test(etiqueta);
              const codigo = claveCodigo ? String(f.valores[claveCodigo] ?? "") : "";
              const contraria = !!(codigo && contrarias?.has(codigo));
              return (
                <tr
                  key={i}
                  className={clases(
                    esTotal && "fila-totales",
                    f.tipo === "linea" && "transition-colors duration-150 hover:bg-hoja-2",
                  )}
                >
                  {rep.columnas.map((c, j) => {
                    const v = f.valores[c.clave];
                    const esNum = c.tipo !== "texto";
                    const negativo = esNum && esNegativo(v);
                    let texto: string;
                    if (c.tipo === "dinero") texto = negativo ? `(${numero(String(v).replace("-", ""))})` : numero(v);
                    else if (c.tipo === "numero") texto = cant(v);
                    else texto = v == null ? "" : String(v);
                    const esCodigo = c.clave === claveCodigo;
                    return (
                      <td
                        key={c.clave}
                        className={clases(
                          "px-4 align-top",
                          celda,
                          !esTotal && "border-b border-linea",
                          j === 0 && "pl-5",
                          esNum ? "cifras text-right" : "text-left",
                          esCodigo && "codigo text-grafito",
                          negativo && (!documento || esResultado) && "text-rojo",
                          f.tipo === "seccion" && "t-meta pt-5 text-tinta",
                          f.tipo === "subtotal" && "font-semibold text-tinta",
                          esTotal && "py-3 font-semibold text-tinta",
                          f.tipo === "linea" && !esNum && !esCodigo && "text-grafito",
                          f.tipo === "nota" && "t-small italic text-rojo",
                        )}
                        style={
                          !esNum && !esCodigo && f.tipo === "linea"
                            ? { paddingLeft: 16 + (f.nivel || 0) * 16 }
                            : undefined
                        }
                      >
                        <span className={clases(contraria && j === 1 && "inline-flex items-center gap-2")}>
                          {texto}
                          {contraria && !esNum && !esCodigo && j <= 1 && (
                            <span
                              role="img"
                              aria-label="Saldo contrario a la naturaleza de la cuenta"
                              title="Saldo contrario a la naturaleza de la cuenta. Revise el registro."
                              className="inline-block h-2 w-2 shrink-0 rounded-full bg-rojo"
                            />
                          )}
                        </span>
                        {esTotal && j === 1 && insignia && !documento && <span className="ml-3 inline-flex align-middle">{insignia}</span>}
                      </td>
                    );
                  })}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {rep.notas?.length > 0 && (
        <ul className="space-y-2">
          {rep.notas.map((n, i) => (
            <li key={i} className="t-small flex items-start gap-2 rounded-control border border-ambar/30 bg-ambar-suave px-3.5 py-2.5 text-ambar">
              <Info size={16} strokeWidth={1.5} aria-hidden className="mt-0.5 shrink-0" />
              <span>{n}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

/** «BALANCE DE PRUEBA (ANTES DE AJUSTES)» → «Balance de prueba (antes de ajustes)». */
export function tituloLegible(t: string): string {
  if (t !== t.toUpperCase()) return t;
  const s = t.toLowerCase();
  return s.charAt(0).toUpperCase() + s.slice(1);
}
