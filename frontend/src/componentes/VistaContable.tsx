import { useMemo, useState } from "react";
import { descargas } from "../api";
import { cant, clases, esCero, fecha, fechaLarga, numero, pesos } from "../formato";
import type { Peticion, Resultado } from "../tipos";
import { InsigniaEstado } from "../ui";
import { ListaAlertas } from "./Alertas";
import { CuentasT } from "./CuentasT";
import { LibroDiario } from "./LibroDiario";
import { Reporte, tituloLegible } from "./Reporte";
import { Boton, Enlace, Insignia, Vacio, estiloCampo } from "./ui";

/**
 * Una sola vista del resultado contable (v2.3 · Fase 3): la misma para lo recién
 * calculado y para lo guardado. Reemplaza a `Resultados` y `ResultadoGuardado`.
 *
 * Sin pestañas dentro de pestañas (Fase 4): cada informe es una «vista» de la
 * lista lateral agrupada. Lo avanzado va plegado en «Ver detalle».
 */

export type VistaId =
  | "situacion" | "resultados" | "patrimonio" | "flujo"
  | "prueba" | "ajustes" | "hoja" | "definitivo"
  | "diario" | "mayor" | "cuentas_t"
  | "inventario" | "nomina" | "alertas"
  | "datos";

export const GRUPOS_VISTA: { titulo: string; vistas: { id: VistaId; texto: string }[] }[] = [
  {
    titulo: "Estados financieros",
    vistas: [
      { id: "situacion", texto: "Situación financiera" },
      { id: "resultados", texto: "Resultados" },
      { id: "patrimonio", texto: "Cambios en el patrimonio" },
      { id: "flujo", texto: "Flujo de efectivo" },
    ],
  },
  {
    titulo: "Balances",
    vistas: [
      { id: "prueba", texto: "Balance de prueba" },
      { id: "ajustes", texto: "Ajustes" },
      { id: "hoja", texto: "Hoja de trabajo" },
      { id: "definitivo", texto: "Balance definitivo" },
    ],
  },
  {
    titulo: "Libros",
    vistas: [
      { id: "diario", texto: "Libro diario" },
      { id: "mayor", texto: "Mayor y balances" },
      { id: "cuentas_t", texto: "Cuentas T" },
    ],
  },
  {
    titulo: "Detalle",
    vistas: [
      { id: "inventario", texto: "Inventario" },
      { id: "nomina", texto: "Nómina" },
      { id: "alertas", texto: "Alertas" },
    ],
  },
  {
    titulo: "Editar",
    vistas: [{ id: "datos", texto: "Datos del periodo" }],
  },
];
export const VISTAS: VistaId[] = GRUPOS_VISTA.flatMap((g) => g.vistas.map((v) => v.id));
export const VISTA_INICIAL: VistaId = "situacion";

const DOCUMENTO: Partial<Record<VistaId, string>> = {
  situacion: "situacion_financiera",
  resultados: "estado_resultados",
  patrimonio: "cambios_patrimonio",
  flujo: "flujo_efectivo",
};

/** Lo recién calculado trae la sesión de trabajo: con ella se pueden cambiar los ajustes y recalcular. */
export interface SesionCalculo {
  peticion: Peticion;
  calculando: boolean;
  onRecalcular: (p: Peticion) => void;
}

export function VistaContable({
  res,
  vista,
  periodoId,
  sesion,
}: {
  res: Resultado;
  vista: VistaId;
  periodoId: string;
  sesion?: SesionCalculo | null;
}) {
  const contrarias = useMemo(() => new Set(res.cuentas_t.filter((c) => c.contraria).map((c) => c.codigo)), [res]);
  const clave = DOCUMENTO[vista];
  if (clave) {
    return (
      <div className="space-y-6">
        <Documento res={res} clave={clave} />
        {vista === "situacion" && (
          <VerDetalle titulo="Ver las notas a los estados financieros">
            <Documento res={res} clave={null} />
          </VerDetalle>
        )}
        {vista === "resultados" && res.reportes.indicadores && (
          <VerDetalle titulo="Ver los indicadores financieros">
            <Reporte rep={res.reportes.indicadores} />
          </VerDetalle>
        )}
      </div>
    );
  }

  switch (vista) {
    case "prueba":
      return <Reporte rep={res.reportes.balance_prueba} contrarias={contrarias} destacarCuadra />;
    case "ajustes":
      return <Ajustes res={res} sesion={sesion ?? null} />;
    case "hoja":
      return <Reporte rep={res.reportes.hoja_trabajo} contrarias={contrarias} />;
    case "definitivo":
      return (
        <div className="space-y-6">
          <Reporte rep={res.reportes.balance_definitivo} contrarias={contrarias} />
          <VerDetalle titulo="Ver el asiento de cierre">
            <Reporte rep={res.reportes.asiento_cierre} />
          </VerDetalle>
        </div>
      );
    case "diario":
      return <Diario res={res} periodoId={periodoId} />;
    case "mayor":
      return (
        <div className="space-y-6">
          <DescargasLibro periodoId={periodoId} libro="mayor-balances" />
          {res.reportes.mayor_balances && <Reporte rep={res.reportes.mayor_balances} contrarias={contrarias} />}
          <VerDetalle titulo="Ver el libro mayor por cuenta">
            <Reporte rep={res.reportes.libro_mayor} />
          </VerDetalle>
        </div>
      );
    case "cuentas_t":
      return <CuentasT cuentas={res.cuentas_t} />;
    case "inventario":
      return res.inventario.productos.length ? (
        <Inventario res={res} />
      ) : (
        <Vacio titulo="Este periodo no trae inventario">Los archivos del periodo no tenían movimientos de inventario.</Vacio>
      );
    case "nomina":
      return <Nomina res={res} />;
    case "alertas":
      return <Alertas res={res} />;
    default:
      return null;
  }
}

/* ── plegable para lo avanzado ───────────────────────────────────────── */
function VerDetalle({ titulo, children }: { titulo: string; children: React.ReactNode }) {
  return (
    <details className="group">
      <summary className="t-small cursor-pointer select-none text-azul-tinta underline underline-offset-4">{titulo}</summary>
      <div className="mt-4">{children}</div>
    </details>
  );
}

/* ── estado financiero en hoja, con firmas ───────────────────────────── */
function Documento({ res, clave }: { res: Resultado; clave: string | null }) {
  const e = res.empresa;
  const rep = clave ? res.reportes[clave] : null;
  if (clave && !rep) return <Vacio titulo="Este periodo no trae ese estado">Elija otro en la lista.</Vacio>;
  return (
    <article
      className="documento-impresion mx-auto w-full max-w-[816px] rounded-hoja border border-linea bg-hoja px-[clamp(20px,7%,72px)] py-[clamp(28px,8%,80px)] shadow-documento"
      aria-label={`${rep ? tituloLegible(rep.titulo) : "Notas a los estados financieros"} de ${e.razon_social}`}
    >
      <header className="border-b border-tinta pb-6 text-center">
        <p className="t-body font-semibold tracking-[0.02em] text-tinta uppercase">{e.razon_social}</p>
        <p className="codigo mt-1 text-[12px] text-grafito">NIT {e.nit}</p>
        <h2 className="t-h2 mt-5 text-tinta">{rep ? tituloLegible(rep.titulo) : "Notas a los estados financieros"}</h2>
        <p className="t-small mt-1 text-grafito">
          {rep?.subtitulo || `Periodo ${fecha(e.periodo_desde)} – ${fecha(e.periodo_hasta)}`}
        </p>
        <p className="t-meta mt-3 text-gris">Cifras en pesos colombianos · corte {fechaLarga(e.periodo_hasta)}</p>
      </header>
      <div className="mt-6">
        {rep ? (
          <Reporte rep={rep} documento />
        ) : (
          <div className="space-y-6">
            {res.notas.map((n) => (
              <section key={n.titulo}>
                <h3 className="t-body font-semibold text-tinta">{n.titulo}</h3>
                {n.parrafos.map((p, k) => (
                  <p key={k} className="t-small mt-2 text-grafito">{p}</p>
                ))}
              </section>
            ))}
            {!res.notas.length && <p className="t-small text-gris">Este periodo no generó notas automáticas.</p>}
          </div>
        )}
      </div>
      {(rep?.firmas || !rep) && <Firmas res={res} />}
    </article>
  );
}

function Firmas({ res }: { res: Resultado }) {
  const e = res.empresa;
  return (
    <div className="mt-16 grid grid-cols-1 gap-12 text-center sm:grid-cols-2">
      {[
        [e.rep_legal, "Representante legal", e.rep_legal_cc ? `C.C. ${e.rep_legal_cc}` : ""],
        [e.contador, "Contador público", e.contador_tp ? `T.P. ${e.contador_tp}` : ""],
      ].map(([nombre, cargo, doc]) => (
        <div key={cargo}>
          <div className="mx-auto h-12 max-w-[240px] border-b border-tinta" aria-hidden />
          <p className="t-small mt-2 font-semibold text-tinta">{nombre || "—"}</p>
          <p className="t-small text-grafito">{cargo}</p>
          {doc && <p className="codigo text-[12px] text-gris">{doc}</p>}
        </div>
      ))}
    </div>
  );
}

/* ── ajustes: con la sesión abierta se aprueban o quitan y se recalcula ── */
function Ajustes({ res, sesion }: { res: Resultado; sesion: SesionCalculo | null }) {
  const [decisiones, setDecisiones] = useState<Record<string, boolean>>(() =>
    Object.fromEntries(res.ajustes.map((a) => [a.id, a.aceptado])),
  );
  const cambiados = res.ajustes.some((a) => decisiones[a.id] !== a.aceptado);
  return (
    <div className="space-y-6">
      {!res.ajustes.length && <Vacio titulo="Sin ajustes">No hubo ajustes propuestos en este periodo.</Vacio>}
      {res.ajustes.length > 0 && (
        <div className="flex flex-wrap items-center justify-between gap-3">
          <p className="t-small max-w-2xl text-grafito">
            {sesion
              ? "Los automáticos vienen aceptados; los sugeridos puede aprobarlos o quitarlos y recalcular."
              : "Así quedaron los ajustes de este periodo. Para cambiarlos, vuelva a subir el archivo."}
          </p>
          {sesion && (
            <Boton
              variante="lima"
              tamano="sm"
              disabled={!cambiados}
              cargando={sesion.calculando}
              onClick={() => sesion.onRecalcular({ ...sesion.peticion, decisiones })}
            >
              Recalcular con estas decisiones
            </Boton>
          )}
        </div>
      )}
      {res.ajustes.map((a) => (
        <div
          key={a.id}
          className={clases("rounded-2xl border p-5", decisiones[a.id] ? "border-azul/30 bg-hoja" : "border-linea bg-hoja-2")}
        >
          <div className="flex flex-wrap items-start justify-between gap-3">
            <label className={clases("flex items-start gap-3", sesion && "cursor-pointer")}>
              <input
                type="checkbox"
                className="mt-1 h-4 w-4 rounded"
                checked={!!decisiones[a.id]}
                disabled={!sesion}
                onChange={(e) => setDecisiones({ ...decisiones, [a.id]: e.target.checked })}
              />
              <span>
                <span className="font-semibold text-tinta">{a.titulo}</span>{" "}
                <Insignia tono={a.tipo === "automatico" ? "azul" : a.tipo === "sugerido" ? "ambar" : "neutro"}>{a.tipo}</Insignia>
                <span className="t-small mt-1 block text-gris">{a.explicacion}</span>
              </span>
            </label>
            <span className="cifras text-sm font-semibold text-tinta">{pesos(a.total)}</span>
          </div>
          <VerDetalle titulo="Ver el asiento">
            <div className="barra-fina overflow-x-auto rounded-xl border border-linea bg-hoja-2">
              <table className="w-full text-xs">
                <thead>
                  <tr className="border-b border-linea text-left text-gris">
                    <th className="p-2">Código</th>
                    <th>Cuenta</th>
                    <th>Descripción</th>
                    <th className="p-2 text-right">Débito</th>
                    <th className="p-2 text-right">Crédito</th>
                  </tr>
                </thead>
                <tbody>
                  {a.lineas.map((l, i) => (
                    <tr key={i} className="border-b border-linea last:border-0">
                      <td className="codigo p-2 text-gris">{l.codigo}</td>
                      <td className="p-2 font-medium">{l.cuenta}</td>
                      <td className="p-2 text-gris">{l.descripcion}</td>
                      <td className="cifras p-2 text-right">{esCero(l.debito) ? "" : numero(l.debito)}</td>
                      <td className="cifras p-2 text-right">{esCero(l.credito) ? "" : numero(l.credito)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </VerDetalle>
        </div>
      ))}
      {res.reportes.balance_ajustado && (
        <VerDetalle titulo="Ver el balance de prueba ajustado">
          <Reporte rep={res.reportes.balance_ajustado} />
        </VerDetalle>
      )}
      {res.reportes.depreciacion && (
        <VerDetalle titulo="Ver la depreciación del periodo">
          <Reporte rep={res.reportes.depreciacion} />
        </VerDetalle>
      )}
    </div>
  );
}

/* ── libros ──────────────────────────────────────────────────────────── */
function DescargasLibro({ periodoId, libro }: { periodoId: string; libro: "libro-diario" | "mayor-balances" }) {
  return (
    <div className="flex flex-wrap gap-2">
      <Enlace href={descargas.libro(periodoId, libro, "excel")} variante="contorno" tamano="sm">Excel</Enlace>
      <Enlace href={descargas.libro(periodoId, libro, "pdf")} variante="contorno" tamano="sm">PDF</Enlace>
    </div>
  );
}

function Diario({ res, periodoId }: { res: Resultado; periodoId: string }) {
  const [cuenta, setCuenta] = useState("");
  if (!res.reportes.libro_diario) return <Vacio titulo="Sin libro diario">Este periodo no tiene libro diario.</Vacio>;
  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <input
          value={cuenta}
          onChange={(e) => setCuenta(e.target.value.replace(/\D/g, ""))}
          placeholder="Filtrar por cuenta PUC: 1, 11, 1105…"
          inputMode="numeric"
          aria-label="Filtrar por cuenta"
          className={clases(estiloCampo, "cifras max-w-xs")}
        />
        <DescargasLibro periodoId={periodoId} libro="libro-diario" />
      </div>
      <LibroDiario rep={res.reportes.libro_diario} origenes={res.origenes} filtroCuenta={cuenta} />
    </div>
  );
}

/* ── alertas: lo que el sistema revisó ───────────────────────────────── */
function Alertas({ res }: { res: Resultado }) {
  const r = res.resumen;
  const verificaciones: [string, unknown][] = [
    ["Balance de prueba", r.bp_cuadra],
    ["Balance ajustado", r.ajustado_cuadra],
    ["Hoja de trabajo", r.hoja_trabajo_cuadra],
    ["Activo = Pasivo + Patrimonio", r.esf_cuadra],
  ];
  const hallazgos = res.auditoria_ef.reduce((n, a) => n + a.hallazgos.length, 0);
  return (
    <div className="space-y-6">
      <div className="flex flex-wrap gap-2">
        {verificaciones.map(([nombre, ok]) => (
          <InsigniaEstado key={nombre} estado={ok ? "cuadra" : "descuadre"} discreta>
            {nombre}
          </InsigniaEstado>
        ))}
      </div>
      <ListaAlertas alertas={res.alertas ?? []} limite={40} />
      {hallazgos > 0 && (
        <VerDetalle titulo={`Ver la auditoría de los estados financieros anteriores (${hallazgos} hallazgos)`}>
          <AuditoriaEF res={res} />
        </VerDetalle>
      )}
    </div>
  );
}

function AuditoriaEF({ res }: { res: Resultado }) {
  return (
    <div className="space-y-6">
      {res.auditoria_ef.map((a) => (
        <section key={a.hoja} className="space-y-3">
          <h3 className="t-body font-semibold text-tinta">{a.archivo} › {a.hoja}</h3>
          <ul className="space-y-2">
            {a.hallazgos.map((h, i) => (
              <li
                key={i}
                className={clases(
                  "rounded-xl border p-3 text-xs",
                  h.severidad === "error" ? "border-rojo/30 bg-rojo-suave text-rojo" : "border-ambar/30 bg-ambar-suave text-ambar",
                )}
              >
                <Insignia tono={h.severidad === "error" ? "rojo" : "ambar"}>{h.codigo}</Insignia>{" "}
                {h.celda && <span className="codigo text-[11px] text-gris">[{h.celda}] </span>}
                <span className="font-medium">{h.hallazgo}</span>
              </li>
            ))}
          </ul>
          <div className="barra-fina overflow-x-auto rounded-xl border border-linea bg-hoja">
            <table className="w-full text-xs">
              <thead className="bg-hoja-2 text-gris">
                <tr>
                  <th className="px-3 py-2 text-left">Concepto</th>
                  <th className="px-3 text-right">En el archivo</th>
                  <th className="px-3 text-right">Corregido</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-linea">
                {a.comparativo.map((c, i) => (
                  <tr key={i}>
                    <td className="px-3 py-2 font-medium">{c.concepto}</td>
                    <td className="cifras px-3 text-right text-gris">{numero(c.archivo)}</td>
                    <td className="cifras px-3 text-right font-semibold text-tinta">{numero(c.correcto)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      ))}
    </div>
  );
}

/* ── inventario y kardex ─────────────────────────────────────────────── */
function Inventario({ res }: { res: Resultado }) {
  const inv = res.inventario;
  const [codigo, setCodigo] = useState(inv.productos[0]?.codigo ?? "");
  const prod = inv.productos.find((p) => p.codigo === codigo);
  const c = inv.conciliacion;
  return (
    <div className="space-y-8">
      {c && (
        <p className={clases("t-small rounded-2xl border p-4", esCero(c.diferencia) ? "border-azul/30 bg-azul-suave text-tinta" : "border-ambar/30 bg-ambar-suave text-ambar")}>
          {esCero(c.diferencia)
            ? `La cuenta 1435 cuadra con el kardex: ${pesos(c.kardex)}.`
            : `La cuenta 1435 difiere del kardex en ${pesos(c.diferencia)} (libros ${pesos(c.libros_antes)}, kardex ${pesos(c.kardex)}).`}
        </p>
      )}
      {res.reportes.inventario_saldos && <Reporte rep={res.reportes.inventario_saldos} />}
      {res.reportes.inventario_vencimientos && <Reporte rep={res.reportes.inventario_vencimientos} />}
      {res.reportes.inventario_fisico && <Reporte rep={res.reportes.inventario_fisico} />}
      <VerDetalle titulo={`Ver el kardex por producto (${inv.metodo === "promedio" ? "promedio ponderado" : "PEPS"})`}>
        <select
          aria-label="Producto del kardex"
          className={clases(estiloCampo, "mb-4 max-w-md")}
          value={codigo}
          onChange={(e) => setCodigo(e.target.value)}
        >
          {inv.productos.map((p) => (
            <option key={p.codigo} value={p.codigo}>{p.codigo} — {p.descripcion}</option>
          ))}
        </select>
        {prod && (
          <div className="barra-fina overflow-x-auto rounded-2xl border border-linea bg-hoja">
            <table className="cifras min-w-full text-xs">
              <thead className="bg-hoja-2 text-gris">
                <tr>
                  <th rowSpan={2} className="px-3 py-2 text-left">Fecha</th>
                  <th rowSpan={2} className="px-3 text-left">Documento</th>
                  <th rowSpan={2} className="px-3 text-left">Tipo</th>
                  <th colSpan={3} className="border-l border-linea px-3 text-center">Entradas</th>
                  <th colSpan={3} className="border-l border-linea px-3 text-center">Salidas</th>
                  <th colSpan={3} className="border-l border-linea px-3 text-center">Saldo</th>
                </tr>
                <tr className="text-[10px]">
                  {["Cant.", "C/u", "Total", "Cant.", "C/u", "Total", "Cant.", "C/u", "Total"].map((t, i) => (
                    <th key={i} className={clases("px-3 py-1.5 text-right", i % 3 === 0 && "border-l border-linea")}>{t}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-linea">
                {prod.filas.map((f, i) => (
                  <tr key={i}>
                    <td className="px-3 py-2">{fecha(f.fecha)}</td>
                    <td className="px-3">{f.documento}</td>
                    <td className="px-3">{String(f.tipo).replace("_", " ")}</td>
                    <td className="border-l border-linea px-3 text-right">{cant(f.ent_cant)}</td>
                    <td className="px-3 text-right">{numero(f.ent_cu)}</td>
                    <td className="px-3 text-right">{numero(f.ent_total)}</td>
                    <td className="border-l border-linea px-3 text-right">{cant(f.sal_cant)}</td>
                    <td className="px-3 text-right">{numero(f.sal_cu)}</td>
                    <td className="px-3 text-right">{numero(f.sal_total)}</td>
                    <td className="border-l border-linea px-3 text-right font-semibold">{cant(f.saldo_cant)}</td>
                    <td className="px-3 text-right">{numero(f.saldo_cu)}</td>
                    <td className="px-3 text-right font-semibold text-tinta">{numero(f.saldo_total)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </VerDetalle>
    </div>
  );
}

/* ── nómina ──────────────────────────────────────────────────────────── */
function Nomina({ res }: { res: Resultado }) {
  const auditoria = res.nomina.auditoria;
  if (!res.reportes.nomina_devengados) {
    return <Vacio titulo="Este periodo no trae nómina">Los archivos del periodo no tenían una hoja de nómina.</Vacio>;
  }
  return (
    <div className="space-y-8">
      <Reporte rep={res.reportes.nomina_devengados} />
      <Reporte rep={res.reportes.nomina_apropiaciones} />
      {auditoria.length > 0 && (
        <VerDetalle titulo={`Ver la auditoría de la nómina del cliente (${auditoria.length} diferencias)`}>
          <div className="barra-fina overflow-x-auto rounded-2xl border border-linea bg-hoja">
            <table className="min-w-full text-xs">
              <thead className="bg-hoja-2 text-left text-gris">
                <tr>
                  <th className="px-3 py-2">Código</th>
                  <th className="px-3">Concepto</th>
                  <th className="px-3">Celda</th>
                  <th className="px-3 text-right">En el archivo</th>
                  <th className="px-3 text-right">Según la ley</th>
                  <th className="px-3 text-right">Diferencia</th>
                  <th className="px-3">Explicación</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-linea">
                {auditoria.map((x, i) => (
                  <tr key={i} className="align-top">
                    <td className="px-3 py-2"><Insignia tono="ambar">{x.codigo}</Insignia></td>
                    <td className="px-3 py-2 font-semibold text-tinta">{x.concepto}</td>
                    <td className="codigo px-3 text-gris">{x.celda}</td>
                    <td className="cifras px-3 text-right">{numero(x.archivo)}</td>
                    <td className="cifras px-3 text-right font-semibold text-tinta">{numero(x.correcto)}</td>
                    <td className="cifras px-3 text-right font-semibold text-rojo">{numero(x.diferencia)}</td>
                    <td className="max-w-md px-3 text-gris">{x.explicacion}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </VerDetalle>
      )}
    </div>
  );
}
