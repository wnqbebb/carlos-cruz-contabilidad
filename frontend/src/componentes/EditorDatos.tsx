import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Copy, Download, FileX2, Plus, RefreshCw, Trash2, Undo2 } from "lucide-react";
import { analisis, datosPeriodo, sistema } from "../api";
import { clases, pesos } from "../formato";
import type { DatosPeriodo, FilaDatos, ProblemaDatos, TablaDatos, ValidacionDatos } from "../tipos";
import { InsigniaEstado, useAvisos } from "../ui";
import { Aviso, Boton, Cargando, Dialogo, Pestanas } from "./ui";

/**
 * «Datos del periodo»: un editor tipo Excel dentro del expediente (rescate H7 · J5).
 *
 * Lo que entró al cálculo —movimientos, saldos iniciales, inventario, nómina y activos fijos—
 * se edita aquí: cambiar valores y cuentas, agregar, duplicar y borrar filas, pegar varias
 * filas copiadas de Excel. Mientras escribe, valida la partida doble y las cuentas; cuando deja
 * de escribir, guarda: el servidor recalcula los estados, los libros y el Excel, y deja la
 * versión anterior en el historial («Deshacer» la recupera). Un periodo cerrado se reabre primero.
 */

type Columna = { campo: string; titulo: string; tipo?: "fecha" | "numero" | "cuenta" | "lista"; opciones?: [string, string][]; ancho?: string };

const TIPOS_INV: [string, string][] = [
  ["inventario_inicial", "Inventario inicial"], ["compra", "Compra"], ["venta", "Venta"],
  ["devolucion_compra", "Devolución compra"], ["devolucion_venta", "Devolución venta"], ["ajuste", "Ajuste"],
];
const MOV: Columna[] = [
  { campo: "fecha", titulo: "Fecha", tipo: "fecha", ancho: "w-36" },
  { campo: "comprobante", titulo: "Comprobante", ancho: "w-28" },
  { campo: "cuenta", titulo: "Cuenta", tipo: "cuenta", ancho: "w-28" },
  { campo: "nombre_cuenta", titulo: "Nombre de la cuenta", ancho: "w-48" },
  { campo: "tercero_id", titulo: "NIT tercero", ancho: "w-28" },
  { campo: "tercero_nombre", titulo: "Tercero", ancho: "w-44" },
  { campo: "descripcion", titulo: "Descripción", ancho: "w-56" },
  { campo: "debito", titulo: "Débito", tipo: "numero", ancho: "w-32" },
  { campo: "credito", titulo: "Crédito", tipo: "numero", ancho: "w-32" },
];
const COLUMNAS: Record<TablaDatos, Columna[]> = {
  movimientos: MOV,
  ajustes: MOV,
  saldos_iniciales: [
    { campo: "cuenta", titulo: "Cuenta", tipo: "cuenta", ancho: "w-28" },
    { campo: "nombre_cuenta", titulo: "Nombre de la cuenta", ancho: "w-64" },
    { campo: "debito", titulo: "Saldo débito", tipo: "numero", ancho: "w-36" },
    { campo: "credito", titulo: "Saldo crédito", tipo: "numero", ancho: "w-36" },
  ],
  inventario: [
    { campo: "fecha", titulo: "Fecha", tipo: "fecha", ancho: "w-36" },
    { campo: "documento", titulo: "Documento", ancho: "w-28" },
    { campo: "codigo", titulo: "Código", ancho: "w-24" },
    { campo: "descripcion", titulo: "Producto", ancho: "w-52" },
    { campo: "tipo", titulo: "Tipo", tipo: "lista", opciones: TIPOS_INV, ancho: "w-40" },
    { campo: "cantidad", titulo: "Cantidad", tipo: "numero", ancho: "w-24" },
    { campo: "costo_unitario", titulo: "Costo unitario", tipo: "numero", ancho: "w-32" },
    { campo: "precio_venta", titulo: "Precio de venta", tipo: "numero", ancho: "w-32" },
    { campo: "lote", titulo: "Lote", ancho: "w-24" },
    { campo: "vencimiento", titulo: "Vence", tipo: "fecha", ancho: "w-36" },
  ],
  conteo: [
    { campo: "codigo", titulo: "Código", ancho: "w-28" },
    { campo: "cantidad", titulo: "Cantidad contada", tipo: "numero", ancho: "w-36" },
    { campo: "fecha", titulo: "Fecha del conteo", tipo: "fecha", ancho: "w-36" },
  ],
  activos_fijos: [
    { campo: "descripcion", titulo: "Activo", ancho: "w-56" },
    { campo: "cuenta", titulo: "Cuenta", tipo: "cuenta", ancho: "w-28" },
    { campo: "fecha_compra", titulo: "Fecha de compra", tipo: "fecha", ancho: "w-36" },
    { campo: "costo", titulo: "Costo", tipo: "numero", ancho: "w-32" },
    { campo: "vida_util_meses", titulo: "Vida útil (meses)", tipo: "numero", ancho: "w-28" },
    { campo: "valor_residual", titulo: "Valor residual", tipo: "numero", ancho: "w-32" },
  ],
  nomina: [
    { campo: "nombre", titulo: "Empleado", ancho: "w-52" },
    { campo: "cedula", titulo: "Cédula", ancho: "w-28" },
    { campo: "cargo", titulo: "Cargo", ancho: "w-36" },
    { campo: "mes", titulo: "Mes", tipo: "numero", ancho: "w-16" },
    { campo: "año", titulo: "Año", tipo: "numero", ancho: "w-20" },
    { campo: "salario_basico", titulo: "Salario básico", tipo: "numero", ancho: "w-32" },
    { campo: "dias", titulo: "Días", tipo: "numero", ancho: "w-16" },
    { campo: "aux_transporte", titulo: "Aux. transporte", tipo: "lista", opciones: [["auto", "Automático"], ["si", "Sí"], ["no", "No"]], ancho: "w-32" },
    { campo: "horas_extra", titulo: "Horas extra ($)", tipo: "numero", ancho: "w-28" },
    { campo: "comisiones", titulo: "Comisiones", tipo: "numero", ancho: "w-28" },
  ],
};
const NOMBRES: Record<TablaDatos, string> = {
  movimientos: "Movimientos", saldos_iniciales: "Saldos iniciales", inventario: "Inventario", nomina: "Nómina",
  activos_fijos: "Activos fijos", ajustes: "Ajustes", conteo: "Conteo físico",
};
const PRINCIPALES: TablaDatos[] = ["movimientos", "saldos_iniciales", "inventario", "nomina", "activos_fijos"];
const POR_PAGINA = 100;
// Ancho mínimo de cada columna: sin esto la tabla se aplastaba y «512010» se veía «512».
const MINIMO: Record<string, number> = {
  "w-16": 64, "w-20": 80, "w-24": 96, "w-28": 116, "w-32": 132, "w-36": 150, "w-40": 164, "w-44": 180,
  "w-48": 200, "w-52": 216, "w-56": 232, "w-64": 264,
};
const ESPERA_GUARDAR = 2500;

type Filas = Record<TablaDatos, (FilaDatos & { _id: string })[]>;
let contador = 0;
const nuevoId = () => `f${Date.now().toString(36)}${(contador++).toString(36)}`;
const conIds = (t: DatosPeriodo["tablas"]): Filas =>
  Object.fromEntries(Object.entries(t).map(([k, filas]) => [k, filas.map((f) => ({ ...f, _id: nuevoId() }))])) as Filas;
const sinIds = (f: Filas) =>
  Object.fromEntries(Object.entries(f).map(([k, filas]) => [k, filas.map(({ _id, ...resto }) => resto)])) as Record<TablaDatos, FilaDatos[]>;

export function EditorDatos({ periodoId, onGuardado, onVolver }: {
  periodoId: string;
  onGuardado: () => Promise<void> | void;
  onVolver: () => void;
}) {
  const avisar = useAvisos();
  const [datos, setDatos] = useState<DatosPeriodo | null>(null);
  const [filas, setFilas] = useState<Filas | null>(null);
  const [tabla, setTabla] = useState<TablaDatos>("movimientos");
  const [validacion, setValidacion] = useState<ValidacionDatos | null>(null);
  const [estado, setEstado] = useState<"listo" | "cambios" | "guardando" | "guardado" | "error">("listo");
  const [error, setError] = useState("");
  const [buscar, setBuscar] = useState("");
  const [pagina, setPagina] = useState(0);
  const [puc, setPuc] = useState<{ codigo: string; nombre: string }[]>([]);
  const [quitar, setQuitar] = useState<string | null>(null);
  const [trabajando, setTrabajando] = useState(false);
  const temporizador = useRef<number>();
  const validando = useRef<number>();
  const version = useRef(0);

  const cargar = useCallback(async () => {
    setError("");
    const d = await datosPeriodo.ver(periodoId);
    setDatos(d);
    setFilas(conIds(d.tablas));
    setValidacion(d.validacion);
    setEstado("listo");
  }, [periodoId]);

  useEffect(() => {
    cargar().catch((e) => setError((e as Error).message));
    sistema.puc().then(setPuc).catch(() => setPuc([]));
    return () => {
      window.clearTimeout(temporizador.current);
      window.clearTimeout(validando.current);
    };
  }, [cargar]);

  const guardar = useCallback(async (actuales: Filas, mia: number) => {
    setEstado("guardando");
    try {
      const d = await datosPeriodo.guardar(periodoId, sinIds(actuales));
      if (mia !== version.current) return;           // ya hay cambios más nuevos: esos se guardan después
      setDatos(d);
      setValidacion(d.validacion);
      setEstado("guardado");
      await onGuardado();
    } catch (e) {
      setEstado("error");
      setError((e as Error).message);
    }
  }, [periodoId, onGuardado]);

  /** Cada cambio: valida enseguida (sin guardar) y guarda cuando deja de escribir. */
  const cambiar = (nuevas: Filas) => {
    setFilas(nuevas);
    setEstado("cambios");
    setError("");
    const mia = ++version.current;
    window.clearTimeout(validando.current);
    window.clearTimeout(temporizador.current);
    validando.current = window.setTimeout(async () => {
      try {
        const v = await datosPeriodo.validar(periodoId, sinIds(nuevas));
        if (mia !== version.current) return;
        setValidacion(v);
        if (!v.errores.length) temporizador.current = window.setTimeout(() => guardar(nuevas, mia), ESPERA_GUARDAR - 500);
      } catch (e) {
        setError((e as Error).message);
      }
    }, 500);
  };

  const accion = async (fn: () => Promise<DatosPeriodo>, mensaje: string) => {
    setTrabajando(true);
    try {
      const d = await fn();
      setDatos(d);
      setFilas(conIds(d.tablas));
      setValidacion(d.validacion);
      setEstado("guardado");
      avisar(mensaje);
      await onGuardado();
    } catch (e) {
      avisar((e as Error).message, "rojo");
    } finally {
      setTrabajando(false);
    }
  };

  const problemas = useMemo(() => {
    const m = new Map<string, ProblemaDatos>();
    for (const p of [...(validacion?.avisos ?? []), ...(validacion?.errores ?? [])]) {
      if (p.fila !== undefined) m.set(`${p.tabla}:${p.fila}:${p.campo ?? ""}`, p);
    }
    return m;
  }, [validacion]);

  if (error && !datos) return <Aviso tono="rojo" titulo="No se pudieron abrir los datos del periodo">{error}</Aviso>;
  if (!datos || !filas) return <Cargando texto="Abriendo los datos del periodo" />;

  const editable = datos.editable;
  const lista = filas[tabla] ?? [];
  const columnas = COLUMNAS[tabla];
  const filtro = buscar.trim().toLowerCase();
  const visibles = lista
    .map((f, i) => ({ f, i }))
    .filter(({ f }) => !filtro || Object.values(f).some((v) => String(v ?? "").toLowerCase().includes(filtro)));
  const paginas = Math.max(1, Math.ceil(visibles.length / POR_PAGINA));
  const pag = Math.min(pagina, paginas - 1);
  const enPantalla = visibles.slice(pag * POR_PAGINA, (pag + 1) * POR_PAGINA);
  const pestanas = [...PRINCIPALES, ...(["ajustes", "conteo"] as TablaDatos[]).filter((t) => (filas[t] ?? []).length)];

  const ponerCelda = (i: number, campo: string, valor: string) => {
    const copia = { ...filas, [tabla]: lista.map((f, j) => (j === i ? { ...f, [campo]: valor } : f)) };
    cambiar(copia);
  };
  const agregar = () => {
    const ultima = lista[lista.length - 1];
    const base: FilaDatos & { _id: string } = { _id: nuevoId() };
    if (tabla === "movimientos" || tabla === "ajustes") {
      Object.assign(base, { fecha: ultima?.fecha ?? datos.periodo.hasta, comprobante: ultima?.comprobante ?? "", debito: "0", credito: "0" });
    }
    cambiar({ ...filas, [tabla]: [...lista, base] });
    setPagina(Math.floor(lista.length / POR_PAGINA));
  };
  const duplicar = (i: number) => {
    const copia = [...lista];
    copia.splice(i + 1, 0, { ...lista[i], _id: nuevoId(), origen: "" });
    cambiar({ ...filas, [tabla]: copia });
  };
  const borrar = (i: number) => cambiar({ ...filas, [tabla]: lista.filter((_, j) => j !== i) });

  /** Pegar varias filas copiadas de Excel (texto con tabulaciones) a partir de la celda elegida. */
  const pegar = (e: React.ClipboardEvent, i: number, columna: number) => {
    const texto = e.clipboardData.getData("text/plain");
    if (!texto.includes("\t") && !texto.includes("\n")) return;
    e.preventDefault();
    const lineas = texto.replace(/\r/g, "").split("\n").filter((l) => l.length);
    const copia = [...lista];
    lineas.forEach((linea, k) => {
      const celdas = linea.split("\t");
      const destino = i + k;
      const fila = destino < copia.length ? { ...copia[destino] } : { _id: nuevoId() } as FilaDatos & { _id: string };
      celdas.forEach((v, c) => {
        const col = columnas[columna + c];
        if (col) fila[col.campo] = col.tipo === "numero" ? numeroDesdeExcel(v) : v.trim();
      });
      if (destino < copia.length) copia[destino] = fila;
      else copia.push(fila);
    });
    cambiar({ ...filas, [tabla]: copia });
  };

  const totales = validacion?.totales;
  return (
    <section aria-label="Datos del periodo" className="space-y-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="t-h2 text-tinta">Datos del periodo</h2>
          <p className="t-small text-grafito">
            Edite lo que entró al cálculo. Al dejar de escribir se guarda y los estados, los libros y el Excel se recalculan.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <EstadoGuardado estado={estado} validacion={validacion} />
          <Boton variante="fantasma" tamano="sm" disabled={!editable || trabajando || datos.versiones === 0}
            onClick={() => accion(() => datosPeriodo.deshacer(periodoId), "Se deshizo el último cambio.")}>
            <Undo2 size={16} strokeWidth={1.5} aria-hidden /> Deshacer
          </Boton>
          <a href={datosPeriodo.excel(periodoId)} className="inline-flex h-9 items-center gap-2 rounded-control px-3 text-[14px] text-azul-tinta hover:bg-hoja-2">
            <Download size={16} strokeWidth={1.5} aria-hidden /> Descargar datos para editar
          </a>
          <Boton variante="contorno" tamano="sm" onClick={onVolver}>Ver los informes</Boton>
        </div>
      </div>

      {!editable && (
        <Aviso tono="ambar" titulo="Periodo cerrado">
          <p>{datos.motivo_bloqueo}</p>
          <Boton className="mt-3" variante="contorno" tamano="sm" cargando={trabajando}
            onClick={() => accion(async () => { await analisis.reabrirPeriodo(periodoId); return datosPeriodo.ver(periodoId); },
              "El periodo quedó abierto: ya puede editarlo.")}>
            Reabrir para editar
          </Boton>
        </Aviso>
      )}
      {error && <Aviso tono="rojo" titulo="No se guardó" onCerrar={() => setError("")}>{error}</Aviso>}

      <Pestanas
        opciones={pestanas.map((t) => ({ id: t, texto: NOMBRES[t], cuenta: (filas[t] ?? []).length }))}
        valor={tabla}
        onCambio={(t) => { setTabla(t); setPagina(0); setBuscar(""); }}
      />

      <div className="flex flex-wrap items-center gap-3">
        <input type="search" value={buscar} onChange={(e) => { setBuscar(e.target.value); setPagina(0); }}
          placeholder="Buscar en la tabla" aria-label="Buscar en la tabla"
          className="h-9 w-64 max-w-full rounded-control border border-borde-campo bg-campo px-3 text-[14px] text-tinta" />
        <span className="t-small text-gris">{visibles.length} fila(s)</span>
        {editable && (
          <Boton variante="contorno" tamano="sm" onClick={agregar}>
            <Plus size={16} strokeWidth={1.5} aria-hidden /> Agregar fila
          </Boton>
        )}
        <span className="t-small text-gris">Puede pegar varias filas copiadas de Excel en cualquier celda.</span>
      </div>

      <div className="overflow-x-auto rounded-hoja border border-linea bg-hoja">
        <table className="min-w-full border-collapse text-[13px]" aria-label={NOMBRES[tabla]}>
          <thead className="bg-hoja-2 text-left text-grafito">
            <tr>
              <th className="w-10 px-2 py-2 font-medium">#</th>
              {columnas.map((c) => (
                <th key={c.campo} className="px-1 py-2 font-medium" style={{ minWidth: MINIMO[c.ancho ?? ""] ?? 120 }}>{c.titulo}</th>
              ))}
              {editable && <th className="w-20 px-2 py-2"><span className="sr-only">Acciones</span></th>}
            </tr>
          </thead>
          <tbody>
            {enPantalla.map(({ f, i }) => (
              <tr key={f._id} className="border-t border-linea align-top">
                <td className="px-2 py-1.5 text-gris">{i + 1}</td>
                {columnas.map((c, ci) => {
                  const p = problemas.get(`${tabla}:${i}:${c.campo}`);
                  const valor = f[c.campo] === null || f[c.campo] === undefined ? "" : String(f[c.campo]);
                  const comun = {
                    "aria-label": `${c.titulo} fila ${i + 1}`,
                    title: p?.mensaje,
                    disabled: !editable,
                    onPaste: (e: React.ClipboardEvent) => pegar(e, i, ci),
                    className: clases(
                      "h-8 w-full rounded-control border bg-campo px-2 text-tinta disabled:opacity-70",
                      c.tipo === "numero" && "cifras text-right",
                      p ? "border-rojo" : "border-borde-campo",
                    ),
                  };
                  return (
                    <td key={c.campo} className="px-1 py-1" style={{ minWidth: MINIMO[c.ancho ?? ""] ?? 120 }}>
                      {c.tipo === "lista" ? (
                        <select {...comun} value={valor} onChange={(e) => ponerCelda(i, c.campo, e.target.value)}>
                          <option value="" />
                          {c.opciones!.map(([v, t]) => <option key={v} value={v}>{t}</option>)}
                        </select>
                      ) : (
                        <input {...comun} value={valor} type={c.tipo === "fecha" ? "date" : "text"}
                          inputMode={c.tipo === "numero" ? "decimal" : undefined}
                          list={c.tipo === "cuenta" ? "puc-editor" : undefined}
                          onChange={(e) => ponerCelda(i, c.campo, e.target.value)} />
                      )}
                    </td>
                  );
                })}
                {editable && (
                  <td className="px-2 py-1 whitespace-nowrap">
                    <button type="button" onClick={() => duplicar(i)} aria-label={`Duplicar fila ${i + 1}`} title="Duplicar"
                      className="rounded-control p-1.5 text-grafito hover:bg-hoja-2 hover:text-tinta"><Copy size={15} strokeWidth={1.5} /></button>
                    <button type="button" onClick={() => borrar(i)} aria-label={`Borrar fila ${i + 1}`} title="Borrar"
                      className="rounded-control p-1.5 text-grafito hover:bg-rojo-suave hover:text-rojo"><Trash2 size={15} strokeWidth={1.5} /></button>
                  </td>
                )}
              </tr>
            ))}
            {enPantalla.length === 0 && (
              <tr><td colSpan={columnas.length + 2} className="px-4 py-8 text-center text-grafito">
                {lista.length ? "Ninguna fila coincide con la búsqueda." : `Este periodo no tiene ${NOMBRES[tabla].toLowerCase()}. ${editable ? "Use «Agregar fila» o pegue desde Excel." : ""}`}
              </td></tr>
            )}
          </tbody>
        </table>
      </div>
      <datalist id="puc-editor">
        {puc.map((c) => <option key={c.codigo} value={c.codigo}>{c.nombre}</option>)}
      </datalist>

      {paginas > 1 && (
        <div className="flex items-center gap-2">
          <Boton variante="fantasma" tamano="sm" disabled={pag === 0} onClick={() => setPagina(pag - 1)}>Anterior</Boton>
          <span className="t-small text-grafito">Página {pag + 1} de {paginas}</span>
          <Boton variante="fantasma" tamano="sm" disabled={pag >= paginas - 1} onClick={() => setPagina(pag + 1)}>Siguiente</Boton>
        </div>
      )}

      {(tabla === "movimientos" || tabla === "ajustes" || tabla === "saldos_iniciales") && totales && (
        <div className="flex flex-wrap gap-x-8 gap-y-2 rounded-hoja border border-linea bg-hoja px-4 py-3 text-[14px]">
          {tabla === "saldos_iniciales" ? (
            <>
              <span>Saldos débito <strong className="cifras text-tinta">{pesos(totales.saldos_debito)}</strong></span>
              <span>Saldos crédito <strong className="cifras text-tinta">{pesos(totales.saldos_credito)}</strong></span>
            </>
          ) : (
            <>
              <span>Débitos <strong className="cifras text-tinta">{pesos(totales.debito)}</strong></span>
              <span>Créditos <strong className="cifras text-tinta">{pesos(totales.credito)}</strong></span>
            </>
          )}
        </div>
      )}

      {validacion && (validacion.errores.length > 0 || validacion.descuadres.length > 0) && (
        <Aviso tono={validacion.errores.length ? "rojo" : "ambar"}
          titulo={validacion.errores.length ? "Hay que corregir antes de guardar" : "Comprobantes que no cumplen partida doble"}>
          <ul className="list-disc space-y-1 pl-5">
            {[...validacion.errores, ...validacion.avisos.filter((a) => a.comprobante)].slice(0, 8).map((p, k) => (
              <li key={k}>{p.fila !== undefined ? `Fila ${p.fila + 1}: ` : ""}{p.mensaje}</li>
            ))}
          </ul>
        </Aviso>
      )}

      <ArchivosDelPeriodo datos={datos} editable={editable} trabajando={trabajando}
        onVer={(a) => { setTabla("movimientos"); setBuscar(a); setPagina(0); }}
        onQuitar={setQuitar}
        onRecalcular={() => accion(() => datosPeriodo.recalcular(periodoId), "El periodo se volvió a procesar.")} />

      {quitar && (
        <Dialogo rotulo="Archivos del periodo" titulo={`Quitar «${quitar}»`} onCerrar={() => setQuitar(null)} ancho="max-w-lg"
          pie={<>
            <Boton variante="fantasma" onClick={() => setQuitar(null)}>Cancelar</Boton>
            <Boton variante="peligro" cargando={trabajando} onClick={async () => {
              const a = quitar;
              setQuitar(null);
              await accion(() => datosPeriodo.quitarArchivo(periodoId, a), `Se quitó lo que aportó «${a}».`);
            }}>Quitar del periodo</Boton>
          </>}>
          <p className="t-body text-grafito">
            Se sacan del periodo todas las filas que vinieron de este archivo y se recalcula. Queda una versión en el
            historial: «Deshacer» la recupera.
          </p>
        </Dialogo>
      )}
    </section>
  );
}

function EstadoGuardado({ estado, validacion }: { estado: string; validacion: ValidacionDatos | null }) {
  const texto = { listo: "", cambios: "Cambios sin guardar…", guardando: "Guardando y recalculando…", guardado: "Guardado", error: "No se guardó" }[estado] ?? "";
  return (
    <span className="flex items-center gap-2" role="status" aria-live="polite">
      {texto && <span className={clases("t-small", estado === "error" ? "text-rojo" : "text-grafito")}>{texto}</span>}
      {validacion && (validacion.cuadra
        ? <InsigniaEstado estado="cuadra">Cuadra</InsigniaEstado>
        : <InsigniaEstado estado="descuadre">Descuadre</InsigniaEstado>)}
    </span>
  );
}

function ArchivosDelPeriodo({ datos, editable, trabajando, onVer, onQuitar, onRecalcular }: {
  datos: DatosPeriodo;
  editable: boolean;
  trabajando: boolean;
  onVer: (archivo: string) => void;
  onQuitar: (archivo: string) => void;
  onRecalcular: () => void;
}) {
  return (
    <div className="space-y-3 rounded-hoja border border-linea bg-hoja p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h3 className="t-h3 text-tinta">Archivos del periodo</h3>
        <Boton variante="fantasma" tamano="sm" disabled={!editable || trabajando} onClick={onRecalcular}>
          <RefreshCw size={16} strokeWidth={1.5} aria-hidden /> Volver a procesar
        </Boton>
      </div>
      {datos.archivos.length === 0 ? (
        <p className="t-small text-grafito">Este periodo no tiene filas de archivos.</p>
      ) : (
        <ul className="divide-y divide-linea">
          {datos.archivos.map((a) => (
            <li key={a.archivo} className="flex flex-wrap items-center gap-3 py-2">
              <span className="min-w-0 flex-1 truncate text-tinta" title={a.archivo}>{a.archivo}</span>
              <span className="t-small text-gris">{a.filas} fila(s)</span>
              <Boton variante="fantasma" tamano="sm" onClick={() => onVer(a.archivo)}>Ver filas</Boton>
              {editable && !a.archivo.startsWith("(") && (
                <Boton variante="fantasma" tamano="sm" onClick={() => onQuitar(a.archivo)}>
                  <FileX2 size={15} strokeWidth={1.5} aria-hidden /> Quitar
                </Boton>
              )}
            </li>
          ))}
        </ul>
      )}
      <p className="t-small text-gris">
        Para reemplazar un archivo: quítelo y suba el nuevo con «Subir archivos». Para cambiar valores, use la tabla de arriba o
        «Descargar datos para editar».
      </p>
    </div>
  );
}

/** «1.234.567,50» o «$ 1,234,567.50» → «1234567.50». Lo que no se entienda queda tal cual (el servidor avisa). */
function numeroDesdeExcel(v: string): string {
  let t = v.replace(/[$\s]/g, "");
  if (!t) return "";
  if (/,\d{1,2}$/.test(t)) t = t.replace(/\./g, "").replace(",", ".");
  else t = t.replace(/,/g, "");
  return t;
}
