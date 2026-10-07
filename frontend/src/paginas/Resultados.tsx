import { ArrowLeft, ArrowRight, Download, Printer, Save, TriangleAlert } from "lucide-react";
import { useMemo, useState } from "react";
import { api, descargas } from "../api";
import { ListaAlertas } from "../componentes/Alertas";
import { CuentasT } from "../componentes/CuentasT";
import { Reporte, tituloLegible } from "../componentes/Reporte";
import { AnilloBalance, BarrasDesglose, Medidor } from "../componentes/Grafica";
import { Boton, Enlace, Insignia, Pestanas, Rotulo, Tarjeta, Vacio } from "../componentes/ui";
import { cant, clases, esCero, esNegativo, fecha, fechaLarga, numero, pesos, porcentaje } from "../formato";
import type { Monto, Peticion, Resultado } from "../tipos";
import { BotonFantasma, Cifra as CifraExacta, InsigniaEstado, useAvisos } from "../ui";

export type Pestaña =
  | "resumen" | "prueba" | "ajustes" | "trabajo" | "definitivo"
  | "estados" | "inventario" | "nomina" | "auditoria" | "mayor";

function Kpi({ titulo, valor }: { titulo: string; valor: Monto }) {
  return (
    <div className="@container material-hoja min-w-0 p-4">
      <Rotulo className="block">{titulo}</Rotulo>
      <p className="mt-2 text-tinta">
        <CifraExacta valor={valor} tamano="h2" encajar />
      </p>
    </div>
  );
}

function Estado({ ok, texto }: { ok: boolean; texto: string }) {
  return (
    <InsigniaEstado estado={ok ? "cuadra" : "descuadre"} discreta>
      {texto}
    </InsigniaEstado>
  );
}

export function Resultados({
  res,
  peticion,
  onRecalcular,
  onEditar,
  calculando,
  pestaña: pestañaControlada,
  onPestaña,
}: {
  res: Resultado;
  peticion: Peticion;
  onRecalcular: (p: Peticion) => void;
  onEditar: () => void;
  calculando: boolean;
  /** Si llega, la pestaña la decide el paso a paso de Trabajo (04–07). */
  pestaña?: Pestaña;
  onPestaña?: (p: Pestaña) => void;
}) {
  const [pestañaInterna, setPestañaInterna] = useState<Pestaña>("resumen");
  const pestaña = pestañaControlada ?? pestañaInterna;
  const setPestaña = onPestaña ?? setPestañaInterna;
  // Saldos contrarios a la naturaleza: el backend ya los marca en cuentas_t.
  const contrarias = useMemo(
    () => new Set(res.cuentas_t.filter((c) => c.contraria).map((c) => c.codigo)),
    [res],
  );
  const [mensaje, setMensaje] = useState("");
  const r = res.resumen;
  const sid = peticion.sesion_id;
  const hayInventario = res.inventario.productos.length > 0;

  const avisar = useAvisos();
  const guardarCierre = async () => {
    try {
      const x = await api.guardarCierre(sid);
      setMensaje(x.mensaje);
      avisar(x.mensaje);
    } catch (e) {
      setMensaje((e as Error).message);
      avisar((e as Error).message, "rojo");
    }
  };

  const opciones: { id: Pestaña; texto: string; cuenta?: number }[] = [
    { id: "resumen", texto: "Resumen y alertas", cuenta: res.alertas.length },
    { id: "prueba", texto: "Balance de prueba" },
    { id: "ajustes", texto: "Ajustes", cuenta: res.ajustes.length },
    { id: "trabajo", texto: "Hoja de trabajo" },
    { id: "definitivo", texto: "Balance definitivo" },
    { id: "estados", texto: "Estados financieros" },
    { id: "inventario", texto: "Inventarios", cuenta: res.inventario.productos.length },
    { id: "nomina", texto: "Nómina", cuenta: res.nomina.auditoria.length },
    { id: "auditoria", texto: "Auditoría EF", cuenta: res.auditoria_ef.reduce((s, a) => s + a.hallazgos.length, 0) },
    { id: "mayor", texto: "Libro mayor y cuentas T" },
  ];

  return (
    <div className="space-y-6">
      <div className="no-imprimir flex flex-wrap items-end justify-between gap-6">
        <div className="min-w-0">
          <p className="t-meta text-gris">Resultado del periodo · {r.periodo}</p>
          <div className="mt-3 flex flex-wrap gap-2">
            <Estado ok={r.bp_cuadra} texto="Balance de prueba" />
            <Estado ok={r.ajustado_cuadra} texto="Balance ajustado" />
            <Estado ok={r.hoja_trabajo_cuadra} texto="Hoja de trabajo" />
            <Estado ok={r.esf_cuadra} texto="Activo = Pasivo + Patrimonio" />
            {r.causal_disolucion && (
              <Insignia tono="rojo">
                <TriangleAlert size={12} strokeWidth={1.5} aria-hidden /> Causal de disolución
              </Insignia>
            )}
            {res.empresa.demo && <Insignia tono="ambar">Datos de demostración</Insignia>}
          </div>
        </div>
        <div className="flex flex-wrap gap-3">
          <BotonFantasma compacto onClick={onEditar} icono={<ArrowLeft size={16} strokeWidth={1.5} aria-hidden />}>
            Revisar mapeo
          </BotonFantasma>
          <BotonFantasma compacto href={descargas.excel(sid)} icono={<Download size={16} strokeWidth={1.5} aria-hidden />}>
            Excel completo
          </BotonFantasma>
          <BotonFantasma compacto href={descargas.pdf(sid)} icono={<Download size={16} strokeWidth={1.5} aria-hidden />}>
            PDF oficial
          </BotonFantasma>
        </div>
      </div>

      {/* Grid de 6 KPIs Financieros */}
      <div className="no-imprimir grid grid-cols-2 gap-3 sm:grid-cols-3 escritorio:grid-cols-6">
        <Kpi titulo="Total activo" valor={r.total_activo} />
        <Kpi titulo="Total pasivo" valor={r.total_pasivo} />
        <Kpi titulo="Patrimonio" valor={r.total_patrimonio} />
        <Kpi titulo="Ingresos netos" valor={r.ingresos} />
        <Kpi titulo={esNegativo(r.utilidad_neta) ? "Pérdida neta" : "Utilidad neta"} valor={r.utilidad_neta} />
        <Kpi titulo="Inventario final" valor={r.inventario_final} />
      </div>

      {/* Tarjeta de Contenido con Pestañas Segmentadas */}
      <Tarjeta sinRelleno>
        <div className="px-5 pt-4 sm:px-6">
          <Pestanas opciones={opciones} valor={pestaña} onCambio={setPestaña} />
        </div>

        <div className="p-5 sm:p-6">
          {pestaña === "resumen" && (
            <div className="space-y-6">
            {/* ── lo que se acaba de calcular, en imágenes ──────────────── */}
            <PanelVisual res={res} />

            <div className="grid gap-6 lg:grid-cols-[1fr_320px]">
              <div>
                <h3 className="mb-3 text-base font-bold text-tinta">Alertas y validaciones automáticas</h3>
                <ListaAlertas alertas={res.alertas} limite={25} />
              </div>

              <div className="space-y-4">
                <div className="material-hoja p-5 bg-hoja text-sm">
                  <p className="font-bold text-tinta">Resumen del Proceso</p>
                  <ul className="mt-3 space-y-2 text-xs sm:text-sm text-grafito">
                    <li className="flex justify-between">
                      <span>Movimientos:</span> <b className="font-mono text-tinta">{r.movimientos}</b>
                    </li>
                    <li className="flex justify-between">
                      <span>Cuentas con saldo:</span> <b className="font-mono text-tinta">{r.cuentas}</b>
                    </li>
                    <li className="flex justify-between">
                      <span>Ajustes aplicados:</span>{" "}
                      <b className="font-mono text-tinta">
                        {r.ajustes_aceptados} de {r.ajustes_propuestos}
                      </b>
                    </li>
                    <li className="flex justify-between">
                      <span>Costo de ventas:</span> <b className="font-mono text-tinta">{pesos(r.costo_ventas)}</b>
                    </li>
                    <li className="flex justify-between">
                      <span>Efectivo al cierre:</span> <b className="font-mono text-tinta">{pesos(r.efectivo)}</b>
                    </li>
                  </ul>
                </div>

                <div className="material-hoja p-5 bg-hoja text-sm">
                  <p className="font-bold text-tinta">Cierre de Periodo</p>
                  <p className="mt-1 text-xs text-gris leading-relaxed">
                    Guarde el cierre para que estos saldos alimenten automáticamente el periodo siguiente.
                  </p>
                  <div className="mt-4 flex flex-col gap-2">
                    <Boton variante="lima" tamano="sm" onClick={guardarCierre}>
                      <Save size={16} strokeWidth={1.5} aria-hidden /> Guardar cierre definitivo
                    </Boton>
                    <Enlace href={descargas.saldos(sid)} variante="contorno" tamano="sm">
                      <Download size={16} strokeWidth={1.5} aria-hidden /> Saldos siguiente periodo
                    </Enlace>
                  </div>
                  {mensaje && <p className="mt-2 text-xs font-bold text-azul">{mensaje}</p>}
                </div>
              </div>
            </div>
            </div>
          )}

          {pestaña === "prueba" && <Reporte rep={res.reportes.balance_prueba} contrarias={contrarias} destacarCuadra />}
          {pestaña === "ajustes" && (
            <Ajustes res={res} peticion={peticion} onRecalcular={onRecalcular} calculando={calculando} />
          )}
          {pestaña === "trabajo" && <Reporte rep={res.reportes.hoja_trabajo} contrarias={contrarias} />}
          {pestaña === "definitivo" && (
            <div className="space-y-8">
              <Reporte rep={res.reportes.balance_ajustado} />
              <Reporte rep={res.reportes.asiento_cierre} />
              <Reporte rep={res.reportes.balance_definitivo} contrarias={contrarias} />
            </div>
          )}
          {pestaña === "estados" && <Estados res={res} sid={sid} />}
          {pestaña === "inventario" &&
            (hayInventario ? (
              <Inventario res={res} />
            ) : (
              <Vacio titulo="Sin movimientos de inventario">
                Los archivos cargados no traen movimientos detallados de inventario. Puede cargar la hoja{" "}
                <b>INVENTARIO_MOVS</b> de la plantilla o usar los <b>datos de demostración</b> para ver el kardex.
              </Vacio>
            ))}
          {pestaña === "nomina" && <Nomina res={res} />}
          {pestaña === "auditoria" && <AuditoriaEF res={res} />}
          {pestaña === "mayor" && (
            <div className="space-y-8">
              <div>
                <h3 className="t-h2 mb-4 text-tinta">Cuentas T · movimientos del periodo antes de ajustes</h3>
                <CuentasT cuentas={res.cuentas_t} />
              </div>
              <Reporte rep={res.reportes.libro_mayor} />
            </div>
          )}
        </div>
      </Tarjeta>
    </div>
  );
}

function Ajustes({
  res,
  peticion,
  onRecalcular,
  calculando,
}: {
  res: Resultado;
  peticion: Peticion;
  onRecalcular: (p: Peticion) => void;
  calculando: boolean;
}) {
  const [decisiones, setDecisiones] = useState<Record<string, boolean>>(() =>
    Object.fromEntries(res.ajustes.map((a) => [a.id, a.aceptado])),
  );
  const cambiados = res.ajustes.some((a) => decisiones[a.id] !== a.aceptado);
  if (!res.ajustes.length) return <Vacio titulo="Sin ajustes">No hay ajustes propuestos para este periodo.</Vacio>;

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-2xl bg-azul-suave border border-azul/30 p-4 text-xs sm:text-sm text-tinta">
        <span>
          Los ajustes <b>automáticos</b> vienen aceptados; los <b>sugeridos</b> (reclasificaciones) puede aprobarlos
          o desactivarlos.
        </span>
        <Boton
          variante="lima"
          tamano="sm"
          disabled={!cambiados}
          cargando={calculando}
          onClick={() => onRecalcular({ ...peticion, decisiones })}
        >
          Recalcular con estas decisiones
        </Boton>
      </div>

      {res.ajustes.map((a) => (
        <div
          key={a.id}
          className={clases(
            "rounded-2xl border p-5 transition-all",
            decisiones[a.id] ? "border-azul/30 bg-hoja shadow-sm" : "border-linea bg-hoja-2",
          )}
        >
          <div className="flex flex-wrap items-start justify-between gap-3">
            <label className="flex cursor-pointer items-start gap-3">
              <input
                type="checkbox"
                className="mt-1 h-4 w-4 rounded text-azul focus:ring-azul"
                checked={!!decisiones[a.id]}
                onChange={(e) => setDecisiones({ ...decisiones, [a.id]: e.target.checked })}
              />
              <div>
                <span className="font-bold text-tinta">{a.titulo}</span>{" "}
                <Insignia tono={a.tipo === "automatico" ? "azul" : a.tipo === "sugerido" ? "ambar" : "neutro"}>
                  {a.tipo}
                </Insignia>
                <span className="mt-1 block text-xs text-gris leading-relaxed">{a.explicacion}</span>
              </div>
            </label>
            <span className="text-sm font-bold cifras text-tinta">{pesos(a.total)}</span>
          </div>

          <div className="barra-fina mt-4 overflow-x-auto rounded-xl border border-linea bg-hoja-2">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-linea text-left text-gris">
                  <th className="p-2">Código</th>
                  <th>Cuenta</th>
                  <th>Descripción</th>
                  <th className="text-right p-2">Débito</th>
                  <th className="text-right p-2">Crédito</th>
                </tr>
              </thead>
              <tbody>
                {a.lineas.map((l, i) => (
                  <tr key={i} className="border-b border-linea last:border-0">
                    <td className="p-2 text-gris font-mono">{l.codigo}</td>
                    <td className="p-2 font-medium">{l.cuenta}</td>
                    <td className="p-2 text-gris">{l.descripcion}</td>
                    <td className="text-right cifras p-2">{esCero(l.debito) ? "" : numero(l.debito)}</td>
                    <td className="text-right cifras p-2">{esCero(l.credito) ? "" : numero(l.credito)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ))}
    </div>
  );
}

/**
 * 07 Estados (spec 6.5): cada estado es un documento sobre hoja, proporción
 * carta, con encabezado (razón social, NIT, nombre del estado, corte), cuerpo
 * y firmas del representante legal y del contador con T.P. Barra flotante de
 * cristal abajo al centro: Excel · PDF · Imprimir · anterior / siguiente.
 */
const DOCUMENTOS = [
  { clave: "situacion_financiera", texto: "Situación financiera" },
  { clave: "estado_resultados", texto: "Resultados" },
  { clave: "cambios_patrimonio", texto: "Cambios en el patrimonio" },
  { clave: "flujo_efectivo", texto: "Flujo de efectivo" },
  { clave: "indicadores", texto: "Indicadores" },
  { clave: "notas", texto: "Notas" },
];

function Estados({ res, sid }: { res: Resultado; sid: string }) {
  const disponibles = DOCUMENTOS.filter((d) => d.clave === "notas" || res.reportes[d.clave]);
  const [i, setI] = useState(0);
  const doc = disponibles[Math.min(i, disponibles.length - 1)];
  const e = res.empresa;
  const rep = doc.clave === "notas" ? null : res.reportes[doc.clave];

  return (
    <div className="space-y-8 pb-24">
      <div className="no-imprimir">
        <Pestanas
          valor={doc.clave}
          onCambio={(c) => setI(disponibles.findIndex((d) => d.clave === c))}
          opciones={disponibles.map((d) => ({ id: d.clave, texto: d.texto }))}
        />
      </div>

      <article
        className="documento-impresion mx-auto w-full max-w-[816px] rounded-hoja border border-linea bg-hoja px-[clamp(20px,7%,72px)] py-[clamp(28px,8%,80px)] [aspect-ratio:8.5/11] shadow-documento"
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
                    <p key={k} className="t-small mt-2 text-grafito">
                      {p}
                    </p>
                  ))}
                </section>
              ))}
              {!res.notas.length && <p className="t-small text-gris">Este periodo no generó notas automáticas.</p>}
            </div>
          )}
        </div>

        {(rep?.firmas || !rep) && <Firmas res={res} />}
      </article>

      {/* Barra flotante de cristal: hay contenido detrás, así que el cristal se ve. */}
      <div className="no-imprimir fixed inset-x-0 bottom-[92px] z-30 flex justify-center px-4 escritorio:bottom-6 escritorio:pl-[248px]">
        <div className="material-cristal flex max-w-full items-center gap-1 overflow-x-auto rounded-full p-1.5 shadow-expediente">
          <BotonBarra href={descargas.excel(sid)} icono={<Download size={16} strokeWidth={1.5} aria-hidden />}>Excel</BotonBarra>
          <BotonBarra href={descargas.pdf(sid)} icono={<Download size={16} strokeWidth={1.5} aria-hidden />}>PDF</BotonBarra>
          <BotonBarra onClick={() => window.print()} icono={<Printer size={16} strokeWidth={1.5} aria-hidden />}>Imprimir</BotonBarra>
          <span aria-hidden className="mx-1 h-6 w-px bg-linea" />
          <button
            type="button"
            aria-label="Estado anterior"
            disabled={i === 0}
            onClick={() => setI((x) => Math.max(0, x - 1))}
            className="grid h-9 w-9 shrink-0 place-items-center rounded-full text-tinta transition-colors hover:bg-hoja disabled:opacity-35"
          >
            <ArrowLeft size={16} strokeWidth={1.5} aria-hidden />
          </button>
          <span className="t-meta shrink-0 px-1 text-grafito">
            {Math.min(i, disponibles.length - 1) + 1} / {disponibles.length}
          </span>
          <button
            type="button"
            aria-label="Estado siguiente"
            disabled={i >= disponibles.length - 1}
            onClick={() => setI((x) => Math.min(disponibles.length - 1, x + 1))}
            className="grid h-9 w-9 shrink-0 place-items-center rounded-full text-tinta transition-colors hover:bg-hoja disabled:opacity-35"
          >
            <ArrowRight size={16} strokeWidth={1.5} aria-hidden />
          </button>
        </div>
      </div>
    </div>
  );
}

function BotonBarra({
  href,
  onClick,
  icono,
  children,
}: {
  href?: string;
  onClick?: () => void;
  icono: React.ReactNode;
  children: React.ReactNode;
}) {
  const clase = "flex h-9 shrink-0 items-center gap-2 rounded-full px-3.5 text-[14px] font-medium text-tinta transition-colors hover:bg-hoja";
  return href ? (
    <a href={href} className={clase}>
      {icono}
      {children}
    </a>
  ) : (
    <button type="button" onClick={onClick} className={clase}>
      {icono}
      {children}
    </button>
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

function Inventario({ res }: { res: Resultado }) {
  const inv = res.inventario;
  const [codigo, setCodigo] = useState(inv.productos[0]?.codigo ?? "");
  const prod = inv.productos.find((p) => p.codigo === codigo);
  const c = inv.conciliacion;

  return (
    <div className="space-y-8">
      {c && (
        <div
          className={clases(
            "grid gap-4 rounded-2xl p-5 text-sm sm:grid-cols-4 backdrop-blur-md",
            esCero(c.diferencia) ? "bg-azul-suave border border-azul/30" : "bg-ambar-suave border border-ambar/30",
          )}
        >
          <div>
            <div className="text-xs text-gris">Cuenta 1435 antes de ajustes</div>
            <b className="font-mono text-tinta">{pesos(c.libros_antes)}</b>
          </div>
          <div>
            <div className="text-xs text-gris">Ajustes (costo ventas)</div>
            <b className="font-mono text-tinta">{pesos(c.efecto_ajustes)}</b>
          </div>
          <div>
            <div className="text-xs text-gris">Saldo según Kardex</div>
            <b className="font-mono text-tinta">{pesos(c.kardex)}</b>
          </div>
          <div>
            <div className="text-xs text-gris">Diferencia de conciliación</div>
            <b className={clases("font-mono font-bold", esCero(c.diferencia) ? "text-azul" : "text-ambar")}>
              {esCero(c.diferencia) ? "✓ Conciliado al 100%" : pesos(c.diferencia)}
            </b>
          </div>
        </div>
      )}

      {res.reportes.inventario_saldos && <Reporte rep={res.reportes.inventario_saldos} />}
      {res.reportes.inventario_vencimientos && <Reporte rep={res.reportes.inventario_vencimientos} />}
      {res.reportes.inventario_fisico && <Reporte rep={res.reportes.inventario_fisico} />}

      <div>
        <div className="mb-4 flex flex-wrap items-center gap-3">
          <h3 className="font-bold text-tinta">
            KARDEX ({inv.metodo === "promedio" ? "promedio ponderado" : "PEPS"})
          </h3>
          <select
            className="rounded-full border border-linea bg-hoja px-4 py-1.5 text-xs font-semibold text-grafito shadow-sm"
            value={codigo}
            onChange={(e) => setCodigo(e.target.value)}
          >
            {inv.productos.map((p) => (
              <option key={p.codigo} value={p.codigo}>
                {p.codigo} — {p.descripcion}
              </option>
            ))}
          </select>
        </div>

        {prod && (
          <div className="barra-fina overflow-x-auto rounded-2xl border border-linea bg-hoja shadow-sm">
            <table className="min-w-full text-xs cifras">
              <thead className="bg-hoja-2 text-gris">
                <tr>
                  <th rowSpan={2} className="px-3 py-2 text-left">Fecha</th>
                  <th rowSpan={2} className="px-3 text-left">Documento</th>
                  <th rowSpan={2} className="px-3 text-left">Tipo</th>
                  <th rowSpan={2} className="px-3 text-left">Lote</th>
                  <th colSpan={3} className="border-l border-linea px-3 text-center">Entradas</th>
                  <th colSpan={3} className="border-l border-linea px-3 text-center">Salidas</th>
                  <th colSpan={3} className="border-l border-linea px-3 text-center">Saldo</th>
                </tr>
                <tr className="text-[10px]">
                  {["Cant.", "C/u", "Total", "Cant.", "C/u", "Total", "Cant.", "C/u", "Total"].map((t, i) => (
                    <th key={i} className={clases("px-3 py-1.5 text-right", i % 3 === 0 && "border-l border-linea")}>
                      {t}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-linea">
                {prod.filas.map((f, i) => (
                  <tr key={i} className="hover:bg-hoja-2">
                    <td className="px-3 py-2">{fecha(f.fecha)}</td>
                    <td className="px-3">{f.documento}</td>
                    <td className="px-3">{String(f.tipo).replace("_", " ")}</td>
                    <td className="px-3">{f.lote}</td>
                    <td className="border-l border-linea px-3 text-right">{cant(f.ent_cant)}</td>
                    <td className="px-3 text-right">{numero(f.ent_cu)}</td>
                    <td className="px-3 text-right">{numero(f.ent_total)}</td>
                    <td className="border-l border-linea px-3 text-right">{cant(f.sal_cant)}</td>
                    <td className="px-3 text-right">{numero(f.sal_cu)}</td>
                    <td className="px-3 text-right">{numero(f.sal_total)}</td>
                    <td className="border-l border-linea px-3 text-right font-bold">{cant(f.saldo_cant)}</td>
                    <td className="px-3 text-right">{numero(f.saldo_cu)}</td>
                    <td className="px-3 text-right font-bold text-tinta">{numero(f.saldo_total)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

function Nomina({ res }: { res: Resultado }) {
  const porHoja = useMemo(() => {
    const g: Record<string, Record<string, any>[]> = {};
    res.nomina.auditoria.forEach((x) => {
      (g[`${x.libro} › ${x.hoja}`] ??= []).push(x);
    });
    return g;
  }, [res]);

  return (
    <div className="space-y-8">
      {res.reportes.nomina_devengados ? (
        <>
          <Reporte rep={res.reportes.nomina_devengados} />
          <Reporte rep={res.reportes.nomina_apropiaciones} />
        </>
      ) : (
        <Vacio titulo="Sin nómina causada">
          No hay nómina causada en este periodo (verifique que la hoja de nómina esté incluida y dentro del rango de
          fechas).
        </Vacio>
      )}

      {Object.keys(porHoja).length > 0 && (
        <div>
          <h3 className="mb-1 font-bold text-tinta">AUDITORÍA DE LA NÓMINA DEL CLIENTE</h3>
          <p className="mb-4 text-xs text-gris">
            Comparativa contra liquidación de ley (SMMLV 2026, auxilio de transporte, aportes y prestaciones).
          </p>
          {Object.entries(porHoja).map(([hoja, lista]) => (
            <div key={hoja} className="mb-6">
              <p className="mb-2 text-xs font-bold text-grafito">
                {hoja} — {lista.length} diferencia(s) identificadas
              </p>
              <div className="barra-fina overflow-x-auto rounded-2xl border border-linea bg-hoja shadow-sm">
                <table className="min-w-full text-xs">
                  <thead className="bg-hoja-2 text-left text-gris">
                    <tr>
                      <th className="px-3 py-2">Código</th>
                      <th className="px-3">Concepto</th>
                      <th className="px-3">Celda</th>
                      <th className="px-3 text-right">Valor en archivo</th>
                      <th className="px-3 text-right">Correcto legal</th>
                      <th className="px-3 text-right">Diferencia</th>
                      <th className="px-3">Explicación</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-linea">
                    {lista.map((x, i) => (
                      <tr key={i} className="align-top hover:bg-hoja-2">
                        <td className="px-3 py-2">
                          <Insignia tono="ambar">{x.codigo}</Insignia>
                        </td>
                        <td className="px-3 py-2 font-semibold text-tinta">{x.concepto}</td>
                        <td className="px-3 text-gris font-mono">{x.celda}</td>
                        <td className="px-3 text-right cifras">{numero(x.archivo)}</td>
                        <td className="px-3 text-right cifras font-bold text-azul">{numero(x.correcto)}</td>
                        <td className="px-3 text-right cifras font-bold text-rojo">{numero(x.diferencia)}</td>
                        <td className="max-w-md px-3 text-xs text-gris">{x.explicacion}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function AuditoriaEF({ res }: { res: Resultado }) {
  if (!res.auditoria_ef.length)
    return <Vacio titulo="Sin hallazgos">No se cargaron estados financieros anteriores para auditar.</Vacio>;

  return (
    <div className="space-y-6">
      {res.auditoria_ef.map((a) => (
        <Tarjeta
          key={a.hoja}
          titulo={`${a.archivo} › ${a.hoja}`}
          subtitulo={`${a.hallazgos.length} hallazgo(s) detectados · Utilidad corregida: ${pesos(a.utilidad_corregida)}`}
        >
          <div className="grid gap-6 xl:grid-cols-[1fr_420px]">
            <ul className="space-y-2.5">
              {a.hallazgos.map((h, i) => (
                <li
                  key={i}
                  className={clases(
                    "rounded-xl border p-3 text-xs",
                    h.severidad === "error"
                      ? "border-rojo/30 bg-rojo-suave text-rojo"
                      : "border-ambar/30 bg-ambar-suave text-ambar",
                  )}
                >
                  <Insignia tono={h.severidad === "error" ? "rojo" : "ambar"}>{h.codigo}</Insignia>{" "}
                  {h.celda && <span className="font-mono text-[11px] text-gris">[{h.celda}] </span>}
                  <span className="font-medium">{h.hallazgo}</span>
                </li>
              ))}
            </ul>

            <div className="barra-fina overflow-x-auto rounded-xl border border-linea bg-hoja">
              <table className="w-full text-xs">
                <thead className="bg-hoja-2 text-gris">
                  <tr>
                    <th className="px-3 py-2 text-left">Concepto</th>
                    <th className="px-3 text-right">En Archivo</th>
                    <th className="px-3 text-right">Corregido</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-linea">
                  {a.comparativo.map((c, i) => (
                    <tr key={i} className={clases(c.archivo !== c.correcto && "bg-ambar-suave")}>
                      <td className="px-3 py-2 font-medium">{c.concepto}</td>
                      <td className="px-3 text-right cifras text-gris">{numero(c.archivo)}</td>
                      <td
                        className={clases(
                          "px-3 text-right font-bold cifras",
                          c.archivo !== c.correcto ? "text-azul" : "text-tinta",
                        )}
                      >
                        {numero(c.correcto)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </Tarjeta>
      ))}
    </div>
  );
}


/* ═══════════════════════════════════════════════════════════════════════════
   Panel visual del resultado recién calculado.
   La ecuación contable dibujada, a dónde se fue el dinero y los tres
   indicadores que un contador mira primero.
   ═══════════════════════════════════════════════════════════════════════════ */
function PanelVisual({ res }: { res: Resultado }) {
  const r = (res.resumen ?? {}) as Record<string, unknown>;
  const t = (k: string) => String(r[k] ?? "0");
  const num = (k: string) => {
    const x = Number(t(k));
    return Number.isFinite(x) ? x : 0;
  };

  const activo = t("total_activo");
  const corriente = num("pasivo_corriente") === 0 ? null : num("activo_corriente") / num("pasivo_corriente");
  const endeudamiento = num("total_activo") === 0 ? null : num("total_pasivo") / num("total_activo");
  const margen = num("ingresos") === 0 ? null : num("utilidad_neta") / num("ingresos");

  return (
    <div className="space-y-4">
      <div className="grid gap-4 xl:grid-cols-[1.05fr_1fr]">
        <div className="material-hoja p-5">
          <AnilloBalance activo={activo} pasivo={t("total_pasivo")} patrimonio={t("total_patrimonio")} />
        </div>
        <div className="material-hoja p-5">
          <BarrasDesglose
            titulo="A dónde se fue el dinero"
            filas={[
              { nombre: "Costo de ventas", valor: t("costo_ventas") },
              { nombre: "Gastos de administración", valor: t("gastos_admin") },
              { nombre: "Gastos de ventas", valor: t("gastos_ventas") },
              { nombre: "Gastos no operacionales", valor: t("gastos_no_op") },
              { nombre: "Impuesto de renta", valor: t("impuesto_renta") },
            ]}
          />
        </div>
      </div>

      <div className="grid gap-3 sm:grid-cols-3">
        <Medidor
          nombre="Razón corriente"
          valor={corriente === null ? "sin pasivo" : `${numero(corriente.toFixed(2))} veces`}
          texto="Activo corriente sobre pasivo corriente."
          fraccion={corriente === null ? 1 : Math.min(corriente / 3, 1)}
          referencia={1 / 3}
          bueno="mayor"
        />
        <Medidor
          nombre="Endeudamiento"
          valor={endeudamiento === null ? "—" : porcentaje(String(endeudamiento))}
          texto="Qué parte del activo está financiada con deuda."
          fraccion={endeudamiento === null ? 0 : Math.min(Math.max(endeudamiento, 0), 1)}
          referencia={0.7}
          bueno="menor"
        />
        <Medidor
          nombre="Margen neto"
          valor={margen === null ? "sin ingresos" : porcentaje(String(margen))}
          texto="Utilidad neta sobre los ingresos del periodo."
          fraccion={margen === null ? 0 : Math.max(0, Math.min(margen, 1))}
          referencia={0.05}
          bueno="mayor"
        />
      </div>
    </div>
  );
}
