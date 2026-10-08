import { ArrowLeft, ArrowRight, Check, TriangleAlert } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { api } from "../api";
import { ListaAlertas } from "../componentes/Alertas";
import { ETAPAS_CALCULO, Procesando } from "../componentes/Procesando";
import { EtiquetaSeccion } from "../ui";
import { Aviso, Boton, Campo, Dialogo, Insignia, Rotulo, Tarjeta, estiloCampoAuto, estiloInput } from "../componentes/ui";
import { clases, fecha, numero, pesos, sumar } from "../formato";
import type { Config, Empresa, Importacion, Peticion, Pregunta } from "../tipos";

function resumenHoja(r: Record<string, unknown>): string {
  const partes: string[] = [];
  // Los importes llegan como cadena decimal exacta y los conteos como número,
  // así que se aceptan los dos. Antes solo aceptaba `number` y, tras pasar los
  // importes a cadena, las líneas de dinero desaparecían del resumen.
  const num = (k: string): string | number | undefined => {
    const v = r[k];
    if (typeof v === "number") return v;
    if (typeof v === "string" && v !== "" && /^-?\d+(\.\d+)?$/.test(v)) return v;
    return undefined;
  };
  if (num("movimientos") !== undefined) partes.push(`${num("movimientos")} movimientos`);
  if (num("saldos_iniciales")) partes.push(`${num("saldos_iniciales")} saldos iniciales`);
  if (num("empleados") !== undefined) partes.push(`${num("empleados")} empleado(s)`);
  if (num("diferencias")) partes.push(`${num("diferencias")} diferencias en la liquidación`);
  if (num("socios") !== undefined) partes.push(`${num("socios")} socios · pagado ${pesos(num("pagado"))} de ${pesos(num("comprometido"))}`);
  if (num("hallazgos") !== undefined) partes.push(`${num("hallazgos")} hallazgos · utilidad archivo ${pesos(num("utilidad_archivo"))} → corregida ${pesos(num("utilidad_corregida"))}`);
  if (num("total_debito") !== undefined) partes.push(`sumas ${pesos(num("total_debito"))}`);
  if (num("productos_movs")) partes.push(`${num("productos_movs")} movimientos de inventario`);
  if (num("activos_fijos")) partes.push(`${num("activos_fijos")} activos fijos`);
  if (Array.isArray(r.bloques)) {
    for (const b of r.bloques as { titulo: string; filas: number; nombre_tipo: string }[]) {
      partes.push(`${b.titulo}: ${b.filas} fila(s) de ${b.nombre_tipo.toLowerCase()}`);
    }
  }
  if (num("comprobantes")) partes.push(`${num("comprobantes")} comprobantes`);
  if (typeof r.titulo === "string" && r.titulo) partes.push(`título: «${r.titulo}»`);
  return partes.join(" · ");
}

export function VistaPrevia({ datos, peticionPrevia, onCalcular, onVolver, calculando }: {
  datos: Importacion; peticionPrevia: Peticion | null; onCalcular: (p: Peticion) => void; onVolver: () => void; calculando: boolean;
}) {
  const [incluir, setIncluir] = useState<Record<string, boolean>>(
    () => peticionPrevia?.incluir ?? Object.fromEntries(datos.hojas.map((h) => [h.id, h.incluir])));
  const [mapeo, setMapeo] = useState<Record<string, string>>(
    () => peticionPrevia?.mapeo ?? Object.fromEntries(datos.mapeo.map((m) => [m.normalizado, m.codigo ?? ""])));
  const [empresa, setEmpresa] = useState<Empresa>(() => ({
    ...datos.empresa, ...(peticionPrevia?.empresa ?? {}),
  }) as Empresa);
  const [config, setConfig] = useState<Config>(() => peticionPrevia?.config ?? {
    exonerado_114_1: true, cuenta_provisiones: "25", metodo_inventario: "promedio", calcular_renta: false,
  });
  const [recordar, setRecordar] = useState(true);
  const [soloPendientes, setSoloPendientes] = useState(false);
  const [abierta, setAbierta] = useState<string | null>(null);
  const [confirmar, setConfirmar] = useState(false);
  const [puc, setPuc] = useState<{ codigo: string; nombre: string }[]>([]);
  const preguntas = datos.preguntas ?? [];
  const [respuestas, setRespuestas] = useState<Record<string, string>>(
    () => peticionPrevia?.respuestas ?? Object.fromEntries(preguntas.map((p) => [p.id, p.defecto])));
  const [periodizacion, setPeriodizacion] = useState<"por_periodo" | "unico">(
    () => peticionPrevia?.periodizacion ?? datos.periodizacion?.defecto ?? "unico");

  useEffect(() => { api.puc().then(setPuc).catch(() => undefined); }, []);
  const nombrePuc = useMemo(() => Object.fromEntries(puc.map((p) => [p.codigo, p.nombre])), [puc]);

  const hojasActivas = new Set(datos.hojas.filter((h) => incluir[h.id]).map((h) => h.id));
  const items = datos.mapeo.filter((m) => m.hojas.some((h) => hojasActivas.has(h)));
  const pendientes = items.filter((m) => !mapeo[m.normalizado]);
  const porConfirmar = items.filter((m) => m.estado === "confirmar");
  const visibles = soloPendientes ? items.filter((m) => m.estado !== "exacto" || !mapeo[m.normalizado]) : items;

  const cambiarEmpresa = (k: keyof Empresa, v: unknown) => setEmpresa({ ...empresa, [k]: v });

  // Se separa en dos: `calcular` decide si hace falta confirmar y `lanzar`
  // ejecuta. El `confirm()` del navegador se cambió por un diálogo propio, que
  // puede explicar QUÉ cuentas quedan fuera y cuánto dinero representan.
  const calcular = () => {
    if (pendientes.length) {
      setConfirmar(true);
      return;
    }
    lanzar();
  };

  const lanzar = (r: Record<string, string> = respuestas) => {
    setConfirmar(false);
    onCalcular({
      sesion_id: datos.sesion_id, incluir, mapeo, config, recordar_alias: recordar,
      respuestas: r, periodizacion,
      decisiones: peticionPrevia?.decisiones ?? {},
      empresa: {
        periodo_desde: empresa.periodo_desde, periodo_hasta: empresa.periodo_hasta, rep_legal: empresa.rep_legal,
        rep_legal_cc: empresa.rep_legal_cc, contador: empresa.contador, contador_tp: empresa.contador_tp, grupo_niif: Number(empresa.grupo_niif),
        capital_suscrito: String(empresa.capital_suscrito), responsable_iva: empresa.responsable_iva, razon_social: empresa.razon_social, nit: empresa.nit,
      },
    });
  };

  return (
    <div className="space-y-6">
      {/* ── qué falta para poder calcular ─────────────────────────────── */}
      <div className="contener">
        <EtiquetaSeccion indice={3}>Mapeo</EtiquetaSeccion>
        <h2 className="t-h1 mt-4 text-tinta">Revise y confirme</h2>
        <p className="mt-2 max-w-2xl text-sm text-grafito">
          El sistema ya reconoció las hojas y propuso un código PUC para cada cuenta.
          Usted solo confirma lo que esté en duda.
        </p>
      </div>

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Avance
          rotulo="Hojas incluidas"
          valor={`${hojasActivas.size} de ${datos.hojas.length}`}
          detalle="Las demás se revisan pero no suman"
        />
        <Avance
          rotulo="Cuentas reconocidas"
          valor={String(items.length - pendientes.length - porConfirmar.length)}
          detalle="Listas, no hay que tocarlas"
          tono="positivo"
        />
        <Avance
          rotulo="Por confirmar"
          valor={String(porConfirmar.length)}
          detalle={porConfirmar.length ? "Revise que el código sea el correcto" : "Nada que confirmar"}
          tono={porConfirmar.length ? "ambar" : undefined}
          onClick={porConfirmar.length ? () => setSoloPendientes(true) : undefined}
        />
        <Avance
          rotulo="Sin mapear"
          valor={String(pendientes.length)}
          detalle={pendientes.length ? "Quedarían fuera del balance" : "Todo mapeado"}
          tono={pendientes.length ? "rojo" : "positivo"}
          onClick={pendientes.length ? () => setSoloPendientes(true) : undefined}
        />
      </div>

      {(preguntas.length > 0 || datos.periodizacion?.posible) && (
        <PanelPreguntas
          preguntas={preguntas}
          respuestas={respuestas}
          onResponder={(id, v) => setRespuestas({ ...respuestas, [id]: v })}
          periodizacion={datos.periodizacion}
          modo={periodizacion}
          onModo={setPeriodizacion}
          calculando={calculando}
          onSugeridas={() => {
            const sugeridas = Object.fromEntries(preguntas.map((p) => [p.id, p.defecto]));
            setRespuestas(sugeridas);
            if (pendientes.length) {
              setConfirmar(true);
              return;
            }
            lanzar(sugeridas);
          }}
        />
      )}

      {pendientes.length > 0 && (
        <Aviso tono="ambar" titulo={`${pendientes.length} cuenta(s) sin código PUC`}>
          Si calcula así, esas cuentas <strong>no entran</strong> en los estados financieros y el balance
          puede quedar descuadrado.{" "}
          <button onClick={() => setSoloPendientes(true)} className="underline underline-offset-2">
            Ver solo las pendientes
          </button>
        </Aviso>
      )}

      <Tarjeta titulo="Hojas detectadas" subtitulo="Marque las hojas que entran en el cálculo. Las marcadas «solo auditoría» se revisan igual aunque no se incluyan.">
        <div className="divide-y divide-linea">
          {datos.hojas.map((h) => {
            const nErr = h.alertas.filter((a) => a.severidad === "error").length;
            const nAdv = h.alertas.filter((a) => a.severidad === "advertencia").length;
            return (
              <div key={h.id} className="py-3">
                <div className="flex flex-wrap items-start gap-3">
                  <input type="checkbox" className="mt-1 h-4 w-4 accent-azul" checked={!!incluir[h.id]} disabled={h.formato === "desconocido"}
                    onChange={(e) => setIncluir({ ...incluir, [h.id]: e.target.checked })} />
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="font-medium text-tinta">{h.hoja}</span>
                      <span className="text-xs text-gris">{h.archivo}</span>
                      <Insignia tono={h.formato === "desconocido" ? "gris" : "neutro"}>{h.formato_nombre}</Insignia>
                      {h.solo_auditoria && <Insignia tono="ambar">solo auditoría</Insignia>}
                      {nErr > 0 && <Insignia tono="rojo">{nErr} error(es)</Insignia>}
                      {nAdv > 0 && <Insignia tono="ambar">{nAdv} advertencia(s)</Insignia>}
                    </div>
                    <p className="mt-0.5 text-sm text-grafito">{resumenHoja(h.resumen)}</p>
                    {h.motivo && <p className={clases("mt-0.5 text-sm", incluir[h.id] ? "text-grafito" : "text-ambar")}>{h.motivo}</p>}
                  </div>
                  {(h.alertas.length > 0 || h.filas_ignoradas.length > 0) && (
                    <button className="text-sm text-tinta hover:underline" onClick={() => setAbierta(abierta === h.id ? null : h.id)}>
                      {abierta === h.id ? "Ocultar detalle" : "Ver detalle"}
                    </button>
                  )}
                </div>
                {abierta === h.id && (
                  <div className="mt-3 space-y-3 pl-7">
                    <ListaAlertas alertas={h.alertas} />
                    {h.filas_ignoradas.length > 0 && (
                      <div>
                        <p className="mb-1 text-xs font-semibold uppercase text-grafito">Filas ignoradas</p>
                        <ul className="space-y-1 text-xs text-grafito">
                          {h.filas_ignoradas.map((f, i) => <li key={i}><span className="text-gris">{f.origen}</span> — {f.motivo}</li>)}
                        </ul>
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </Tarjeta>

      <Tarjeta
        titulo={`Mapeo de cuentas al PUC (${items.length})`}
        subtitulo={`${items.length - pendientes.length - porConfirmar.length} exactas · ${porConfirmar.length} por confirmar · ${pendientes.length} sin mapear. Las decisiones se recuerdan para la próxima vez.`}
        acciones={
          <label className="flex items-center gap-2 text-sm text-grafito">
            <input type="checkbox" className="accent-azul" checked={soloPendientes} onChange={(e) => setSoloPendientes(e.target.checked)} />
            Solo pendientes
          </label>
        }
      >
        {items.length === 0 ? (
          <p className="text-sm text-grafito">Todas las cuentas vienen con código PUC: no hay nada que mapear.</p>
        ) : (
          <div className="overflow-x-auto">
            <datalist id="lista-puc">
              {puc.map((p) => <option key={p.codigo} value={p.codigo}>{p.nombre}</option>)}
            </datalist>
            <table className="t-tabla min-w-full border-separate border-spacing-0">
              <thead>
                <tr className="text-left">
                  {["Nombre en el archivo", "Veces", "Valor", "Estado", "Código PUC", "Cuenta PUC"].map((t, i) => (
                    <th
                      key={t}
                      scope="col"
                      className={clases("t-meta border-b border-linea py-2.5 pr-4 text-gris", (i === 1 || i === 2) && "text-right")}
                    >
                      {t}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {visibles.map((m) => {
                  const codigo = mapeo[m.normalizado] ?? "";
                  const activos = Object.entries(m.por_hoja).filter(([id]) => hojasActivas.has(id));
                  const veces = activos.reduce((s, [, x]) => s + x.veces, 0);
                  // `sumar` suma los importes como decimales exactos; con `+` se
                  // concatenarían las cadenas ("100" + "200" daría "100200").
                  const valor = sumar(...activos.map(([, x]) => x.valor));
                  const estado = !codigo ? "sin" : m.estado === "sin" ? "confirmar" : m.estado;
                  return (
                    <tr key={m.normalizado} className="align-top transition-colors duration-150 hover:bg-hoja-2">
                      <td className="border-b border-linea py-2.5 pr-4 font-medium text-tinta">
                        {m.nombre}
                        {m.bandera && <div className="flex items-center gap-1 text-xs font-normal text-ambar"><TriangleAlert size={12} strokeWidth={1.5} aria-hidden /> {m.bandera}: no es gasto de la empresa</div>}
                      </td>
                      <td className="cifras border-b border-linea py-2.5 pr-4 text-right">{veces}</td>
                      <td className="cifras border-b border-linea py-2.5 pr-4 text-right">{numero(valor)}</td>
                      <td className="border-b border-linea py-2.5 pr-4">
                        <Semaforo estado={estado} />
                      </td>
                      <td className="border-b border-linea py-2.5 pr-4">
                        <input list="lista-puc" value={codigo} placeholder="código"
                          className={clases(estiloInput, "codigo !h-9 w-28", !codigo && "ring-1 ring-rojo")}
                          onChange={(e) => setMapeo({ ...mapeo, [m.normalizado]: e.target.value.split(" ")[0] })} />
                        {m.estado !== "exacto" && m.candidatos.length > 0 && (
                          <div className="mt-1 flex flex-wrap gap-1">
                            {m.candidatos.slice(0, 3).map((c) => (
                              <button key={c.codigo} onClick={() => setMapeo({ ...mapeo, [m.normalizado]: c.codigo })}
                                className="codigo rounded-chip border border-linea px-1.5 py-0.5 text-[11px] text-grafito transition-colors hover:border-tinta/30 hover:text-tinta">
                                {c.codigo} ({c.puntaje}%)
                              </button>
                            ))}
                          </div>
                        )}
                      </td>
                      <td className="border-b border-linea py-2.5 text-grafito">{codigo ? nombrePuc[codigo] ?? nombrePuc[codigo.slice(0, 4)] ?? "(subcuenta propia)" : "—"}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </Tarjeta>

      <div className="grid gap-6 lg:grid-cols-2">
        <Tarjeta titulo="Empresa y periodo" subtitulo={`Periodo sugerido por: ${datos.periodo_sugerido.fuente}`}>
          <div className="grid gap-3 sm:grid-cols-2">
            <Campo etiqueta="Razón social"><input className={estiloInput} value={empresa.razon_social} onChange={(e) => cambiarEmpresa("razon_social", e.target.value)} /></Campo>
            <Campo etiqueta="NIT"><input className={estiloInput} value={empresa.nit} onChange={(e) => cambiarEmpresa("nit", e.target.value)} /></Campo>
            <Campo etiqueta="Periodo desde"><input type="date" className={estiloInput} value={empresa.periodo_desde} onChange={(e) => cambiarEmpresa("periodo_desde", e.target.value)} /></Campo>
            <Campo etiqueta="Periodo hasta"><input type="date" className={estiloInput} value={empresa.periodo_hasta} onChange={(e) => cambiarEmpresa("periodo_hasta", e.target.value)} /></Campo>
            <Campo etiqueta="Representante legal"><input className={estiloInput} value={empresa.rep_legal} onChange={(e) => cambiarEmpresa("rep_legal", e.target.value)} /></Campo>
            <Campo etiqueta="C.C. representante legal"><input className={estiloInput} value={empresa.rep_legal_cc} onChange={(e) => cambiarEmpresa("rep_legal_cc", e.target.value)} /></Campo>
            <Campo etiqueta="Contador"><input className={estiloInput} value={empresa.contador} onChange={(e) => cambiarEmpresa("contador", e.target.value)} /></Campo>
            <Campo etiqueta="Tarjeta profesional"><input className={estiloInput} value={empresa.contador_tp} onChange={(e) => cambiarEmpresa("contador_tp", e.target.value)} /></Campo>
            <Campo etiqueta="Grupo NIIF">
              <select className={estiloInput} value={empresa.grupo_niif} onChange={(e) => cambiarEmpresa("grupo_niif", Number(e.target.value))}>
                <option value={2}>Grupo 2 — NIIF para Pymes</option>
                <option value={3}>Grupo 3 — Microempresas</option>
              </select>
            </Campo>
            <Campo etiqueta="Capital suscrito (estatutos)" ayuda={pesos(String(empresa.capital_suscrito))}>
              <input type="number" className={estiloInput} value={empresa.capital_suscrito} onChange={(e) => cambiarEmpresa("capital_suscrito", e.target.value)} />
            </Campo>
          </div>
          <p className="mt-3 text-xs text-grafito">Periodo actual: {fecha(empresa.periodo_desde)} a {fecha(empresa.periodo_hasta)}</p>
        </Tarjeta>

        <Tarjeta titulo="Opciones de cálculo">
          <div className="space-y-4 text-sm">
            <label className="flex items-start gap-3">
              <input type="checkbox" className="mt-0.5 accent-azul" checked={config.exonerado_114_1} onChange={(e) => setConfig({ ...config, exonerado_114_1: e.target.checked })} />
              <span><b>Exoneración art. 114-1 E.T.</b><br /><span className="text-grafito">Sin salud 8,5 %, SENA ni ICBF para empleados con menos de 10 SMMLV. La caja 4 % se paga siempre.</span></span>
            </label>
            <label className="flex items-start gap-3">
              <input type="checkbox" className="mt-0.5 accent-azul" checked={config.calcular_renta} onChange={(e) => setConfig({ ...config, calcular_renta: e.target.checked })} />
              <span><b>Provisionar impuesto de renta</b> ({Math.round(Number(empresa.tarifa_renta) * 100)} %)<br /><span className="text-grafito">Úselo solo en el cierre anual.</span></span>
            </label>
            <div className="grid gap-3 sm:grid-cols-2">
              <Campo etiqueta="Provisiones de nómina van a">
                <select className={estiloInput} value={config.cuenta_provisiones} onChange={(e) => setConfig({ ...config, cuenta_provisiones: e.target.value as "25" | "26" })}>
                  <option value="25">25 — Obligaciones laborales</option>
                  <option value="26">26 — Pasivos estimados (2610)</option>
                </select>
              </Campo>
              <Campo etiqueta="Método de inventario">
                <select className={estiloInput} value={config.metodo_inventario} onChange={(e) => setConfig({ ...config, metodo_inventario: e.target.value as "promedio" | "peps" })}>
                  <option value="promedio">Promedio ponderado</option>
                  <option value="peps">PEPS (primeras en entrar)</option>
                </select>
              </Campo>
            </div>
            <label className="flex items-center gap-3">
              <input type="checkbox" className="accent-azul" checked={recordar} onChange={(e) => setRecordar(e.target.checked)} />
              Recordar el mapeo de cuentas para esta empresa
            </label>
          </div>
        </Tarjeta>
      </div>

      {/* Espacio para que la barra fija no tape el último bloque. */}
      <div className="h-40 escritorio:h-24" aria-hidden />

      {/* ── barra fija de acción ───────────────────────────────────────────
          Antes el botón de calcular estaba solo arriba: después de revisar
          cincuenta cuentas había que volver a subir. Ahora acompaña siempre. */}
      <div className="no-imprimir fixed inset-x-3 bottom-[92px] z-30 escritorio:inset-x-0 escritorio:bottom-4 escritorio:pl-[248px]">
        <div className="material-cristal mx-auto flex max-w-[1100px] flex-wrap items-center justify-between gap-3 rounded-hoja px-4 py-3 shadow-expediente sm:px-5">
          <div className="contener flex flex-wrap items-center gap-x-4 gap-y-1">
            <Rotulo>
              {hojasActivas.size} hoja(s) · {items.length - pendientes.length} de {items.length} cuentas listas
            </Rotulo>
            {pendientes.length > 0 && (
              <Insignia tono="rojo">{pendientes.length} sin mapear</Insignia>
            )}
            {pendientes.length === 0 && porConfirmar.length === 0 && items.length > 0 && (
              <Insignia tono="tinta">Todo listo</Insignia>
            )}
          </div>
          <div className="flex shrink-0 gap-2">
            <Boton variante="fantasma" onClick={onVolver}>
              <ArrowLeft size={16} strokeWidth={1.5} aria-hidden /> Otros archivos
            </Boton>
            <Boton variante="lima" cargando={calculando} onClick={calcular}>
              Calcular todo <ArrowRight size={16} strokeWidth={1.5} aria-hidden />
            </Boton>
          </div>
        </div>
      </div>

      {calculando && (
        <div className="no-imprimir fixed inset-0 z-50 grid place-items-center p-4">
          <div className="absolute inset-0 bg-[var(--velo)]" aria-hidden />
          <div className="material-cristal relative w-full max-w-md rounded-hoja px-6 py-8 shadow-expediente">
            <Procesando titulo="Calculando el periodo" etapas={ETAPAS_CALCULO} />
          </div>
        </div>
      )}

      {/* ── confirmación cuando quedan cuentas sin mapear ──────────────── */}
      {confirmar && (
        <Dialogo
          rotulo="Antes de calcular"
          titulo={`Quedan ${pendientes.length} cuenta(s) sin código PUC`}
          onCerrar={() => setConfirmar(false)}
          ancho="max-w-xl"
          pie={
            <>
              <Boton variante="fantasma" onClick={() => setConfirmar(false)}>
                Volver y mapearlas
              </Boton>
              <Boton variante="peligro" cargando={calculando} onClick={() => lanzar()}>
                Calcular sin ellas
              </Boton>
            </>
          }
        >
          <div className="space-y-4">
            <Aviso tono="ambar">
              Estas cuentas <strong>no entrarán</strong> en el balance ni en los estados financieros.
              Es muy probable que el resultado quede descuadrado.
            </Aviso>
            <div>
              <Rotulo className="mb-2 block">Cuentas que quedarían fuera</Rotulo>
              <ul className="max-h-60 space-y-1 overflow-y-auto">
                {pendientes.map((m) => {
                  const activos = Object.entries(m.por_hoja).filter(([id]) => hojasActivas.has(id));
                  return (
                    <li
                      key={m.normalizado}
                      className="flex items-baseline justify-between gap-3 rounded-lg bg-hoja px-3 py-2 text-sm"
                    >
                      <span className="recortar">{m.nombre}</span>
                      <span className="cifras shrink-0 text-xs text-grafito">
                        {pesos(sumar(...activos.map(([, x]) => x.valor)))}
                      </span>
                    </li>
                  );
                })}
              </ul>
            </div>
          </div>
        </Dialogo>
      )}
    </div>
  );
}

/* ── preguntas sobre este archivo (spec v2.2 · 4.2) ─────────────────────
   Todas juntas, con la respuesta sugerida ya marcada: el contador puede
   aceptarlas de un clic o cambiar solo la que no le convence. Nada de
   diálogos encadenados. */
const NOMBRE_PERIODICIDAD: Record<string, string> = {
  mensual: "mes a mes", bimestral: "bimestre a bimestre", trimestral: "trimestre a trimestre",
  cuatrimestral: "cuatrimestre a cuatrimestre", semestral: "semestre a semestre", anual: "año a año",
};

/** Detalle plegable de una pregunta agrupada: los bloques, y cada uno se puede responder aparte (B3). */
function BloquesDelGrupo({
  pregunta, respuestas, onResponder,
}: {
  pregunta: Pregunta;
  respuestas: Record<string, string>;
  onResponder: (id: string, valor: string) => void;
}) {
  const bloques = pregunta.bloques ?? [];
  const aparte = bloques.filter((b) => respuestas[b.id]).length;
  return (
    <details className="mt-3">
      <summary className="t-small cursor-pointer text-azul-tinta underline underline-offset-4">
        Ver los {bloques.length} bloques{aparte ? ` · ${aparte} con respuesta propia` : ""} y responder alguno aparte
      </summary>
      <ul className="mt-3 space-y-2">
        {bloques.map((b) => (
          <li key={b.id} className="flex flex-wrap items-center justify-between gap-2 border-b border-linea pb-2">
            <span className="t-small min-w-0 text-grafito">{b.lugar}</span>
            <select
              aria-label={`Respuesta para ${b.lugar}`}
              value={respuestas[b.id] ?? ""}
              onChange={(e) => onResponder(b.id, e.target.value)}
              className={estiloCampoAuto}
            >
              <option value="">Igual que todos</option>
              {pregunta.opciones.map((o) => (
                <option key={o.valor} value={o.valor}>{o.etiqueta}</option>
              ))}
            </select>
          </li>
        ))}
      </ul>
    </details>
  );
}

function PanelPreguntas({
  preguntas, respuestas, onResponder, periodizacion, modo, onModo, calculando, onSugeridas,
}: {
  preguntas: Pregunta[];
  respuestas: Record<string, string>;
  onResponder: (id: string, valor: string) => void;
  periodizacion?: Importacion["periodizacion"];
  modo: "por_periodo" | "unico";
  onModo: (m: "por_periodo" | "unico") => void;
  calculando: boolean;
  onSugeridas: () => void;
}) {
  const cambiadas = preguntas.filter((p) => (respuestas[p.id] ?? p.defecto) !== p.defecto).length
    + preguntas.reduce((n, p) => n + (p.bloques ?? []).filter((b) => respuestas[b.id]).length, 0);
  const total = preguntas.length + (periodizacion?.posible ? 1 : 0);
  const periodos = periodizacion?.periodos ?? [];
  return (
    <Tarjeta
      rotulo={`${total} ${total === 1 ? "decisión" : "decisiones"}`}
      titulo="Preguntas sobre este archivo"
      subtitulo="La respuesta sugerida ya está marcada. Cambie solo la que no corresponda."
      acciones={
        <Boton variante="lima" cargando={calculando} onClick={onSugeridas}>
          Usar las respuestas sugeridas y calcular <ArrowRight size={16} strokeWidth={1.5} aria-hidden />
        </Boton>
      }
    >
      <div className="space-y-6">
        {periodizacion?.posible && (
          <fieldset className="contener">
            <legend className="t-body font-semibold text-tinta">
              El archivo cubre {periodizacion.meses} meses. ¿Cómo lo proceso?
            </legend>
            <div className="mt-3 grid gap-2 sm:grid-cols-2">
              <Opcion
                nombre="periodizacion"
                marcada={modo === "por_periodo"}
                sugerida={periodizacion.defecto === "por_periodo"}
                onElegir={() => onModo("por_periodo")}
                etiqueta={`Procesar ${NOMBRE_PERIODICIDAD[periodizacion.periodicidad] ?? "mes a mes"}, cerrando cada uno`}
                detalle={`${periodos.length} periodos, según la periodicidad del cliente. El último queda calculado para que usted lo revise y lo cierre.`}
              />
              <Opcion
                nombre="periodizacion"
                marcada={modo === "unico"}
                sugerida={periodizacion.defecto === "unico"}
                onElegir={() => onModo("unico")}
                etiqueta="Un solo periodo"
                detalle={periodos.length
                  ? `Del ${fecha(periodos[0].desde)} al ${fecha(periodos[periodos.length - 1].hasta)}, en un solo juego de estados financieros.`
                  : "Todo el archivo en un solo juego de estados financieros."}
              />
            </div>
          </fieldset>
        )}
        {preguntas.map((p) => (
          <fieldset key={p.id} className="contener border-t border-linea pt-5 first:border-t-0 first:pt-0">
            <legend className="t-body font-semibold text-tinta">{p.titulo}</legend>
            <p className="t-small mt-1 text-grafito">{p.detalle}</p>
            <p className="t-meta mt-1 text-gris">{p.hoja}</p>
            <div className="mt-3 grid gap-2 sm:grid-cols-2">
              {p.opciones.map((o) => (
                <Opcion
                  key={o.valor}
                  nombre={p.id}
                  marcada={(respuestas[p.id] ?? p.defecto) === o.valor}
                  sugerida={o.valor === p.defecto}
                  onElegir={() => onResponder(p.id, o.valor)}
                  etiqueta={o.etiqueta}
                />
              ))}
            </div>
            {p.bloques && p.bloques.length > 1 && (
              <BloquesDelGrupo pregunta={p} respuestas={respuestas} onResponder={onResponder} />
            )}
          </fieldset>
        ))}
        {cambiadas > 0 && (
          <p className="t-small text-grafito">
            Cambió {cambiadas} {cambiadas === 1 ? "respuesta" : "respuestas"}: se usarán al pulsar «Calcular todo».
          </p>
        )}
      </div>
    </Tarjeta>
  );
}

function Opcion({
  nombre, marcada, sugerida, onElegir, etiqueta, detalle,
}: {
  nombre: string;
  marcada: boolean;
  sugerida: boolean;
  onElegir: () => void;
  etiqueta: string;
  detalle?: string;
}) {
  return (
    <label
      className={clases(
        "flex cursor-pointer items-start gap-3 rounded-control border px-3.5 py-3 transition-colors duration-150",
        marcada ? "border-tinta bg-hoja" : "border-linea hover:bg-hoja-2",
      )}
    >
      <input type="radio" name={nombre} checked={marcada} onChange={onElegir} className="mt-1 accent-azul" />
      <span className="min-w-0">
        <span className="t-body text-tinta">{etiqueta}</span>
        {sugerida && <span className="t-meta ml-2 text-azul">sugerida</span>}
        {detalle && <span className="t-small mt-0.5 block text-grafito">{detalle}</span>}
      </span>
    </label>
  );
}

/* ── tarjeta de avance de la cabecera ─────────────────────────────────── */
function Avance({
  rotulo, valor, detalle, tono, onClick,
}: {
  rotulo: string;
  valor: string;
  detalle: string;
  tono?: "positivo" | "ambar" | "rojo";
  onClick?: () => void;
}) {
  const Elemento = onClick ? "button" : "div";
  return (
    <Elemento
      onClick={onClick}
      className={clases(
        "contener material-hoja p-4 text-left",
        onClick && "cursor-pointer transition-colors hover:bg-hoja-2",
      )}
    >
      <Rotulo>{rotulo}</Rotulo>
      <p
        className={clases(
          "cifras cifra-flexible t-kpi mt-2 leading-none",
          tono === "rojo" && "text-rojo",
          tono === "ambar" && "text-ambar",
          tono === "positivo" && "text-tinta",
        )}
      >
        {valor}
      </p>
      <p className="t-small mt-2 text-grafito">{detalle}</p>
    </Elemento>
  );
}

/** Semáforo del mapeo: tinta con ✓ = exacto · ámbar = por confirmar · rojo = sin mapear. */
function Semaforo({ estado }: { estado: string }) {
  const e =
    estado === "exacto"
      ? { punto: "bg-tinta", texto: "Exacto", clase: "text-tinta" }
      : estado === "confirmar"
        ? { punto: "bg-ambar", texto: "Por confirmar", clase: "text-ambar" }
        : { punto: "bg-rojo", texto: "Sin mapear", clase: "text-rojo" };
  return (
    <span className={clases("inline-flex items-center gap-2 whitespace-nowrap text-[13px] font-medium", e.clase)}>
      <span aria-hidden className={clases("grid h-4 w-4 place-items-center rounded-full", e.punto)}>
        {estado === "exacto" && <Check size={10} strokeWidth={2.5} className="text-sobre-tinta" />}
      </span>
      {e.texto}
    </span>
  );
}
