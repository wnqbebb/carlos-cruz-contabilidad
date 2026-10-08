import { ChevronDown, FileSpreadsheet } from "lucide-react";
import { Fragment, useMemo, useState } from "react";
import { clases, esCero, fecha, numero } from "../formato";
import type { Reporte as TReporte } from "../tipos";
import { InsigniaEstado } from "../ui";

/**
 * Libro diario oficial (H05): cada comprobante con sus líneas, su total y la
 * insignia de partida doble; al final el total del periodo.
 *
 * El origen de cada línea («archivo › hoja › fila 12») es un botón: al pulsarlo
 * se ve la fila tal como venía en el archivo del cliente, para comprobar de
 * dónde salió cada peso sin abrir el Excel.
 */
export function LibroDiario({
  rep,
  origenes,
  filtroCuenta = "",
}: {
  rep: TReporte;
  origenes?: Record<string, string[]>;
  /** Prefijo PUC: solo los comprobantes que tocan esa cuenta. */
  filtroCuenta?: string;
}) {
  const [abierto, setAbierto] = useState<string | null>(null);

  // Las filas vienen en orden: sección (comprobante), líneas, subtotal; al final el total.
  const comprobantes = useMemo(() => {
    const salida: { titulo: string; lineas: Record<string, any>[]; total: Record<string, any> | null }[] = [];
    for (const f of rep.filas) {
      if (f.tipo === "seccion") salida.push({ titulo: String(f.valores.descripcion ?? ""), lineas: [], total: null });
      else if (f.tipo === "linea" && salida.length) salida[salida.length - 1].lineas.push(f.valores);
      else if (f.tipo === "subtotal" && salida.length) salida[salida.length - 1].total = f.valores;
    }
    return filtroCuenta
      ? salida.filter((c) => c.lineas.some((l) => String(l.codigo ?? "").startsWith(filtroCuenta)))
      : salida;
  }, [rep, filtroCuenta]);

  const total = rep.filas.find((f) => f.tipo === "total")?.valores;
  const nota = rep.filas.find((f) => f.tipo === "nota")?.valores;
  const verif = rep.verificacion ?? {};

  if (nota && !comprobantes.length) {
    return <p className="t-body text-grafito">{String(nota.descripcion)}</p>;
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div className="min-w-0">
          <h3 className="t-h2 text-tinta">Libro diario</h3>
          <p className="t-small mt-1 text-gris">
            {rep.subtitulo} · {contar(Number(verif.comprobantes ?? comprobantes.length), "comprobante", "comprobantes")} ·{" "}
            {contar(Number(verif.lineas ?? 0), "línea", "líneas")}
          </p>
        </div>
        {verif.cuadra !== undefined &&
          (verif.cuadra ? (
            <InsigniaEstado estado="cuadra" discreta>Partida doble verificada</InsigniaEstado>
          ) : (
            <InsigniaEstado estado="descuadre">Hay comprobantes que no cuadran</InsigniaEstado>
          ))}
      </div>

      <div className="barra-fina overflow-x-auto rounded-control border border-linea">
        <table className="t-tabla w-full min-w-[960px] border-separate border-spacing-0 text-[13px]">
          <thead className="sticky top-0 z-10 bg-hoja">
            <tr className="text-left">
              {["Fecha", "Cuenta", "Tercero", "Descripción", "Débito", "Crédito", "Origen"].map((t, i) => (
                <th
                  key={t}
                  scope="col"
                  className={clases("t-meta border-b border-linea px-3 py-2.5 text-gris", (i === 4 || i === 5) && "text-right")}
                >
                  {t}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {comprobantes.map((c, ic) => {
              const cuadra = c.total ? numero(c.total.debito) === numero(c.total.credito) : true;
              return (
                <Fragment key={`${c.titulo}-${ic}`}>
                  <tr>
                    <th
                      scope="rowgroup"
                      colSpan={7}
                      className="border-b border-linea bg-hoja-2 px-3 py-2 text-left font-semibold text-tinta"
                    >
                      <span className="codigo">{c.titulo.split(" · ")[0]}</span>
                      <span className="ml-2 font-normal text-grafito">{c.titulo.split(" · ").slice(1).join(" · ")}</span>
                    </th>
                  </tr>
                  {c.lineas.map((l, il) => {
                    const clave = `${ic}-${il}`;
                    const fila = origenes?.[String(l.origen ?? "")];
                    return (
                      <Fragment key={clave}>
                        <tr className="align-top transition-colors duration-150 hover:bg-hoja-2">
                          <td className="cifras whitespace-nowrap border-b border-linea px-3 py-2 text-grafito">
                            {fecha(l.fecha) || "—"}
                          </td>
                          <td className="border-b border-linea px-3 py-2">
                            <span className="codigo text-tinta">{l.codigo}</span>
                            <span className="ml-2 text-grafito">{l.cuenta}</span>
                          </td>
                          <td className="border-b border-linea px-3 py-2 text-grafito">{l.tercero || "—"}</td>
                          <td className="border-b border-linea px-3 py-2 text-grafito">{l.descripcion || "—"}</td>
                          <td className="cifras border-b border-linea px-3 py-2 text-right text-tinta">
                            {l.debito && !esCero(l.debito) ? numero(l.debito) : ""}
                          </td>
                          <td className="cifras border-b border-linea px-3 py-2 text-right text-tinta">
                            {l.credito && !esCero(l.credito) ? numero(l.credito) : ""}
                          </td>
                          <td className="border-b border-linea px-3 py-2">
                            {l.origen ? (
                              fila ? (
                                <button
                                  type="button"
                                  onClick={() => setAbierto(abierto === clave ? null : clave)}
                                  aria-expanded={abierto === clave}
                                  className="inline-flex items-center gap-1 text-left text-azul-tinta underline decoration-1 underline-offset-2 hover:text-tinta"
                                >
                                  {String(l.origen).split(" › ").slice(-2).join(" › ")}
                                  <ChevronDown
                                    size={12}
                                    strokeWidth={1.5}
                                    aria-hidden
                                    className={clases("shrink-0 transition-transform", abierto === clave && "rotate-180")}
                                  />
                                </button>
                              ) : (
                                <span className="text-gris">{String(l.origen).split(" › ").slice(-2).join(" › ")}</span>
                              )
                            ) : (
                              <span className="text-gris">—</span>
                            )}
                          </td>
                        </tr>
                        {abierto === clave && fila && (
                          <tr>
                            <td colSpan={7} className="border-b border-linea bg-hoja px-3 py-3">
                              <p className="t-meta flex items-center gap-1.5 text-gris">
                                <FileSpreadsheet size={13} strokeWidth={1.5} aria-hidden /> Fila original · {String(l.origen)}
                              </p>
                              <div className="barra-fina mt-2 flex gap-1 overflow-x-auto">
                                {fila.map((celda, i) => (
                                  <span
                                    key={i}
                                    className="codigo shrink-0 rounded-chip border border-linea bg-hoja-2 px-2 py-1 text-[12px] text-tinta"
                                  >
                                    {celda || "·"}
                                  </span>
                                ))}
                              </div>
                            </td>
                          </tr>
                        )}
                      </Fragment>
                    );
                  })}
                  {c.total && (
                    <tr>
                      <td colSpan={4} className="border-b border-linea px-3 py-2 text-right font-semibold text-tinta">
                        {cuadra ? `Total ${c.titulo.split(" · ")[0]}` : String(c.total.descripcion)}
                      </td>
                      <td className={clases("cifras border-b border-linea px-3 py-2 text-right font-semibold", cuadra ? "text-tinta" : "text-rojo")}>
                        {numero(c.total.debito)}
                      </td>
                      <td className={clases("cifras border-b border-linea px-3 py-2 text-right font-semibold", cuadra ? "text-tinta" : "text-rojo")}>
                        {numero(c.total.credito)}
                      </td>
                      <td className="border-b border-linea px-3 py-2">
                        {cuadra ? (
                          <span className="t-meta text-gris">cuadra</span>
                        ) : (
                          <span className="t-meta text-rojo">no cuadra</span>
                        )}
                      </td>
                    </tr>
                  )}
                </Fragment>
              );
            })}
          </tbody>
          {total && !filtroCuenta && (
            <tfoot>
              <tr>
                <td colSpan={4} className="border-t-2 border-tinta px-3 py-3 text-right font-semibold text-tinta">
                  Total del periodo
                </td>
                <td className="cifras border-t-2 border-tinta px-3 py-3 text-right font-semibold text-tinta">
                  {numero(total.debito)}
                </td>
                <td className="cifras border-t-2 border-tinta px-3 py-3 text-right font-semibold text-tinta">
                  {numero(total.credito)}
                </td>
                <td className="border-t-2 border-tinta px-3 py-3" />
              </tr>
            </tfoot>
          )}
        </table>
      </div>
      {filtroCuenta && (
        <p className="t-small text-gris">
          Mostrando {contar(comprobantes.length, "comprobante", "comprobantes")} que mueven cuentas que empiezan por{" "}
          {filtroCuenta}.
        </p>
      )}
    </div>
  );
}

const contar = (n: number, uno: string, varios: string) => `${n.toLocaleString("es-CO")} ${n === 1 ? uno : varios}`;
