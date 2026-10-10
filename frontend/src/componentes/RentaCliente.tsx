import { Check, Download, FileUp, TriangleAlert } from "lucide-react";
import { Fragment, useCallback, useEffect, useRef, useState, type ReactNode } from "react";
import { descargarConfirmando, renta, type CambioRenta } from "../api";
import { clases, esNegativo, fecha, pesos } from "../formato";
import type { BeneficioRenta, CasillaRenta, Cliente, DeclaracionRenta, LineaRenta, PreguntaRenta, ResultadoRenta } from "../tipos";
import { InsigniaEstado, useAvisos } from "../ui";
import { Procesando } from "./Procesando";
import { Aviso, Boton, Campo, Cargando, Dialogo, Insignia, Vacio, estiloCampo, estiloCampoAuto } from "./ui";

/**
 * Declaración de renta del cliente (v2.3 · Fase 5): tres pasos y nada más.
 *
 *   1 · Suelte todo  — fotos, PDF o Excel, en cualquier orden.
 *   2 · Revise       — veredicto, tres cifras, máximo 5 preguntas, beneficios y el detalle plegado.
 *   3 · Descargue    — un botón: borrador del 210, papel de trabajo y resumen para el cliente.
 *
 * La app prepara el borrador; no presenta la declaración (se hace en el portal de la
 * DIAN con la firma electrónica del contribuyente).
 */

const ANIO = 2025;
const ESTADO: Record<string, { texto: string; tono: "neutro" | "ambar" | "azul" | "verde" }> = {
  sin_informacion: { texto: "Sin información", tono: "neutro" },
  borrador: { texto: "Borrador", tono: "ambar" },
  revisada: { texto: "Revisada", tono: "azul" },
  presentada: { texto: "Presentada", tono: "verde" },
};

export function RentaCliente({ cliente }: { cliente: Cliente }) {
  const [decl, setDecl] = useState<DeclaracionRenta | null>(null);
  const [error, setError] = useState("");
  const [subiendo, setSubiendo] = useState(false);
  const [agregando, setAgregando] = useState(false);
  const avisar = useAvisos();

  const cargar = useCallback(() => {
    setError("");
    renta.ver(cliente.id, ANIO).then(setDecl).catch((e) => setError((e as Error).message));
  }, [cliente.id]);
  useEffect(() => {
    if (cliente.tipo_persona !== "juridica") cargar();
  }, [cargar, cliente.tipo_persona]);

  const subir = async (archivos: File[]) => {
    if (!archivos.length) return;
    setSubiendo(true);
    setError("");
    try {
      setDecl(await renta.subir(cliente.id, ANIO, archivos));
      setAgregando(false);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSubiendo(false);
    }
  };

  const cambiar = async (c: CambioRenta) => {
    try {
      setDecl(await renta.cambiar(cliente.id, ANIO, c));
    } catch (e) {
      avisar((e as Error).message, "rojo");
    }
  };

  if (cliente.tipo_persona === "juridica") {
    return (
      <Vacio titulo="Las personas jurídicas declaran en el formulario 110">
        Esa declaración todavía no se prepara aquí: está anotada para una próxima versión. Esta sección prepara el
        formulario 210 de las personas naturales.
      </Vacio>
    );
  }
  if (error && !decl) return <Aviso tono="rojo" titulo="No se pudo abrir la renta">{error}</Aviso>;
  if (!decl) return <Cargando texto="Abriendo la declaración de renta" />;

  const res = decl.resultado;
  const sinDatos = !res || (!res.lineas.length && !res.manuales.length);

  if (subiendo) {
    return (
      <div className="material-hoja mx-auto max-w-xl p-8">
        <Procesando
          titulo="Leyendo los documentos"
          etapas={["Enderezando las fotos", "Encontrando la tabla", "Leyendo fila por fila", "Separando por contribuyente",
            "Cuadrando con los topes", "Armando el formulario 210"]}
        />
      </div>
    );
  }

  if (sinDatos || agregando) {
    return (
      <div className="space-y-6">
        {error && <Aviso tono="rojo" onCerrar={() => setError("")}>{error}</Aviso>}
        {agregando && (
          <Boton variante="fantasma" tamano="sm" onClick={() => setAgregando(false)}>Volver a la declaración</Boton>
        )}
        <SoltarTodo onArchivos={subir} anio={ANIO} />
      </div>
    );
  }

  return (
    <Revision
      decl={decl}
      res={res!}
      cliente={cliente}
      onCambio={cambiar}
      onAgregar={() => setAgregando(true)}
      onMarcar={async (estado, numero, fechaP) => {
        try {
          setDecl(await renta.marcar(cliente.id, ANIO, estado, numero, fechaP));
          avisar(estado === "presentada" ? "Declaración marcada como presentada." : "Declaración marcada como revisada.");
        } catch (e) {
          avisar((e as Error).message, "rojo");
        }
      }}
      onRecargar={(nueva) => setDecl(nueva)}
    />
  );
}

/* ── paso 1 · suelte todo ────────────────────────────────────────────── */
function SoltarTodo({ onArchivos, anio }: { onArchivos: (a: File[]) => void; anio: number }) {
  const entrada = useRef<HTMLInputElement>(null);
  const [encima, setEncima] = useState(false);
  return (
    <section aria-labelledby="titulo-renta-subir" className="space-y-5">
      <div>
        <h2 id="titulo-renta-subir" className="t-h2 text-tinta">Declaración de renta {anio}</h2>
        <p className="t-body mt-1 max-w-2xl text-grafito">
          Suelte todo lo que tenga del cliente: fotos del reporte de exógena (aunque estén giradas o en varias
          páginas), el PDF o Excel del portal de la DIAN, la declaración del año anterior, certificados.
        </p>
      </div>
      <div
        role="button"
        tabIndex={0}
        aria-label="Elegir los documentos de renta o soltarlos aquí"
        onClick={() => entrada.current?.click()}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            entrada.current?.click();
          }
        }}
        onDragOver={(e) => {
          e.preventDefault();
          e.stopPropagation();
          setEncima(true);
        }}
        onDragLeave={() => setEncima(false)}
        onDrop={(e) => {
          e.preventDefault();
          e.stopPropagation();
          setEncima(false);
          onArchivos(Array.from(e.dataTransfer.files));
        }}
        className={clases(
          "material-hundido flex min-h-[260px] cursor-pointer flex-col items-center justify-center rounded-hoja border-2 border-dashed px-6 text-center transition-[border-color] duration-200 select-none",
          encima ? "border-azul" : "border-tinta/20 hover:border-tinta/40",
        )}
      >
        <FileUp size={28} strokeWidth={1.5} aria-hidden className="text-grafito" />
        <p className="t-h2 mt-5 text-tinta">{encima ? "Suelte para leer" : "Suelte aquí todo junto"}</p>
        <p className="t-body mt-1 text-gris">Fotos, PDF o Excel · en cualquier orden · yo los ordeno</p>
      </div>
      <input
        ref={entrada}
        type="file"
        multiple
        accept="image/*,.pdf,.xlsx,.xls,.csv"
        className="hidden"
        aria-label="Documentos de renta"
        onChange={(e) => {
          onArchivos(Array.from(e.target.files ?? []));
          e.target.value = "";
        }}
      />
      <p className="t-small text-gris">
        Las fotos se leen en este equipo. No se guardan completas: solo el recorte de cada fila del reporte, para
        que usted compare. Las notas escritas a mano no se guardan.
      </p>
    </section>
  );
}

/* ── paso 2 y 3 ─────────────────────────────────────────────────────── */
function Revision({
  decl,
  res,
  cliente,
  onCambio,
  onAgregar,
  onMarcar,
  onRecargar,
}: {
  decl: DeclaracionRenta;
  res: ResultadoRenta;
  cliente: Cliente;
  onCambio: (c: CambioRenta) => Promise<void>;
  onAgregar: () => void;
  onMarcar: (estado: "revisada" | "borrador" | "presentada", numero?: string, fecha?: string) => Promise<void>;
  onRecargar: (decl: DeclaracionRenta) => void;
}) {
  const [presentar, setPresentar] = useState(false);
  const [abiertoEsencial, setAbiertoEsencial] = useState(false);
  const [confirmando, setConfirmando] = useState<string[] | null>(null);
  const estaIncompleto = Boolean(res.incompleto || res.cifras.bloqueado);
  const neto = res.cifras.neto;
  const paga = neto !== null && !esNegativo(neto) && neto !== "0";
  const estado = estaIncompleto
    ? { texto: "Faltan datos para calcular", tono: "ambar" as const }
    : { texto: "Datos completos y validados", tono: "verde" as const };
  const obligado = res.obligacion?.obligado;
  return (
    <div className="space-y-10">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="flex items-center gap-2">
          <span className="t-meta text-gris">Renta {decl.anio}</span>
          <Insignia tono={estado.tono}>{estado.texto}</Insignia>
          {decl.presentada?.numero && (
            <span className="t-small text-grafito">
              Formulario {decl.presentada.numero} · {fecha(decl.presentada.fecha)}
            </span>
          )}
        </p>
        <div className="flex items-center gap-2">
          {(estaIncompleto || res.ofrecer_digitar_esencial) && (
            <Boton variante="solido" tamano="sm" onClick={() => setAbiertoEsencial(true)}>
              Digitar lo esencial
            </Boton>
          )}
          <Boton variante="fantasma" tamano="sm" onClick={onAgregar}>
            <FileUp size={16} strokeWidth={1.5} aria-hidden /> Agregar documentos
          </Boton>
        </div>
      </div>

      {/* 1 · veredicto */}
      <section aria-label="Veredicto">
        <p className={clases("t-h1 text-balance", obligado === false ? "text-tinta" : "text-tinta")}>
          {res.obligacion?.veredicto ?? "Falta información para saber si debe declarar"}
        </p>
      </section>

      {/* Rescate H5: lo que falta, arriba y siempre visible, con un botón por cada cosa. */}
      {estaIncompleto && (
        <CajaPendientes
          res={res}
          onConfirmarFilas={(ids) => setConfirmando(ids)}
          onDigitar={() => setAbiertoEsencial(true)}
        />
      )}

      {/* 2 · tres cifras */}
      <section aria-label="Cifras de la declaración" className="grid gap-4 sm:grid-cols-3">
        <CifraGrande
          rotulo={estaIncompleto ? "Impuesto o saldo a favor" : paga ? "Paga" : neto === "0" ? "Ni paga ni le devuelven" : "Le devuelven"}
          valor={
            estaIncompleto
              ? "Se calculará cuando se completen los datos"
              : paga
              ? pesos(neto!)
              : neto === "0"
              ? "$ 0"
              : pesos(String(neto).replace("-", ""))
          }
          detalle={estaIncompleto ? "Requiere datos completos y validados" : undefined}
        />
        <CifraGrande
          rotulo="Ahorro frente a la propuesta de la DIAN"
          valor={estaIncompleto ? "Se calculará cuando se completen los datos" : pesos(res.cifras.ahorro)}
          detalle={
            estaIncompleto
              ? "Disponible al completar las preguntas"
              : res.cifras.ahorro === "0"
              ? "La DIAN no dejó beneficios por fuera"
              : undefined
          }
        />
        <CifraGrande
          rotulo="Vencimiento"
          valor={res.vencimiento.texto.split(" · ")[0]}
          detalle={res.vencimiento.texto.split(" · ")[1]}
          alerta={!!res.vencimiento.vencida}
        />
      </section>
      {!estaIncompleto && res.sancion && res.sancion.valor !== "0" && (
        <Aviso tono="rojo" titulo={`Sanción estimada por extemporaneidad: ${pesos(res.sancion.valor)}`}>
          {res.sancion.texto}
        </Aviso>
      )}
      {res.anotaciones_a_mano && (
        <Aviso tono="ambar" titulo="La foto tiene anotaciones escritas a mano">
          No se guardaron. Si eran datos de acceso (usuario o contraseña), recomiende al cliente cambiar esa contraseña.
        </Aviso>
      )}

      {/* 3 · por confirmar */}
      {res.preguntas.length > 0 && (
        <section aria-labelledby="titulo-confirmar" className="space-y-4">
          <h2 id="titulo-confirmar" className="t-h2 text-tinta">Por confirmar</h2>
          <ul className="space-y-4">
            {res.preguntas.map((q) => (
              <PreguntaUnToque key={q.id} q={q} onResponder={(v) => onCambio({ tipo: "respuesta", id: q.id, valor: v })} />
            ))}
          </ul>
        </section>
      )}

      {/* 4 · lo que solo usted sabe: el negocio y los beneficios con soporte */}
      {(res.negocio?.senales || res.beneficios.length > 0) && (
        <section aria-labelledby="titulo-solo-usted" className="space-y-4">
          <div>
            <h2 id="titulo-solo-usted" className="t-h2 text-tinta">Lo que solo usted sabe</h2>
            <p className="t-small mt-1 text-grafito">
              La DIAN solo conoce lo que reportaron terceros. Lo que usted escriba aquí recalcula al instante.
            </p>
          </div>
          {res.negocio?.senales && <Negocio res={res} onCambio={onCambio} />}
        </section>
      )}
      {res.beneficios.length > 0 && (
        <section aria-labelledby="titulo-menos" className="space-y-4">
          <div>
            <h3 id="titulo-menos" className="t-h3 text-tinta">¿Podemos pagar menos?</h3>
            <p className="t-small mt-1 text-grafito">Cada «sí» pide el soporte y recalcula al instante.</p>
          </div>
          <ul className="divide-y divide-linea rounded-hoja border border-linea bg-hoja">
            {res.beneficios.map((b) => (
              <Beneficio key={b.id} b={b} maximo1={res.maximo_1pct} onCambio={onCambio} />
            ))}
          </ul>
        </section>
      )}

      {res.marcas.length > 0 && (
        <section aria-labelledby="titulo-marcas" className="space-y-3">
          <h2 id="titulo-marcas" className="t-h2 text-tinta">Cosas a mirar</h2>
          <ul className="space-y-2">
            {res.marcas.map((m, i) => (
              <li key={i} className="t-small flex gap-2 text-grafito">
                <TriangleAlert size={16} strokeWidth={1.5} aria-hidden className="mt-0.5 shrink-0 text-ambar" />
                <span>{m.texto}</span>
              </li>
            ))}
          </ul>
        </section>
      )}

      {/* 5 · detalle plegado */}
      <Plegable titulo={`Ver las ${res.lineas.length} líneas leídas y lo agregado a mano`} id="detalle-lineas">
        <DetalleLineas decl={decl} res={res} cliente={cliente} onCambio={onCambio} />
      </Plegable>
      <Diferencias res={res} />
      <Plegable titulo="Ver las casillas del formulario 210: lo que propondría la DIAN y su declaración">
        <Casillas res={res} onCambio={onCambio} />
      </Plegable>
      {(res.avisos.length > 0 || res.validacion.length > 0) && (
        <Plegable titulo="Ver cómo se leyeron los documentos">
          <ul className="space-y-1.5">
            {res.validacion.map((v) => (
              <li key={v.tope} className="t-small text-grafito">
                <InsigniaEstado estado={v.estado === "no_cuadra" ? "descuadre" : "cuadra"} discreta>
                  Tope {v.tope}
                </InsigniaEstado>{" "}
                {v.texto || `${v.nombre}: las filas cuadran con el encabezado.`}
              </li>
            ))}
            {res.avisos.map((a, i) => (
              <li key={i} className="t-small text-grafito">{a}</li>
            ))}
          </ul>
        </Plegable>
      )}

      {/* paso 3 · descargue */}
      <section aria-labelledby="titulo-descargue" className="space-y-4 border-t border-linea pt-8">
        <h2 id="titulo-descargue" className="t-h2 text-tinta">Descargue</h2>
        <div className="flex flex-wrap items-center gap-3">
          {/* Descargar todo pide confirmar la contraseña (v2.3 · C8). */}
          <Boton variante="solido" onClick={() => descargarConfirmando(renta.descarga(cliente.id, decl.anio, "todo"))}>
            <Download size={16} strokeWidth={1.5} aria-hidden />
            <span className="sm:hidden">Descargar todo</span>
            <span className="hidden sm:inline">Descargar borrador, papel de trabajo y resumen</span>
          </Boton>
          {decl.estado !== "presentada" && decl.estado !== "revisada" && (
            <Boton variante="fantasma" onClick={() => onMarcar("revisada")}>
              <Check size={16} strokeWidth={1.5} aria-hidden /> Marcar como revisada
            </Boton>
          )}
          {decl.estado !== "presentada" && (
            <Boton variante="fantasma" onClick={() => setPresentar(true)}>Marcar como presentada</Boton>
          )}
        </div>
        <p className="t-small max-w-2xl text-gris">
          Es un borrador: la declaración se diligencia en el portal de la DIAN con la firma electrónica del
          contribuyente. La aplicación no la presenta.
        </p>
      </section>

      {presentar && (
        <DialogoPresentada
          onCerrar={() => setPresentar(false)}
          onGuardar={async (numero, f) => {
            await onMarcar("presentada", numero, f);
            setPresentar(false);
          }}
        />
      )}

      {confirmando && (
        <ConfirmarFilas
          res={res}
          ids={confirmando}
          cliente={cliente}
          anio={decl.anio}
          onCerrar={() => setConfirmando(null)}
          onCambio={onCambio}
        />
      )}

      {abiertoEsencial && (
        <ModalDigitarEsencial
          cliente={cliente}
          res={res}
          onCerrar={() => setAbiertoEsencial(false)}
          onGuardado={(nueva) => onRecargar(nueva)}
        />
      )}
    </div>
  );
}

function CifraGrande({ rotulo, valor, detalle, alerta }: { rotulo: string; valor: string; detalle?: string; alerta?: boolean }) {
  return (
    <div className="material-hoja min-w-0 p-5">
      <p className="t-meta text-gris">{rotulo}</p>
      <p className={clases("cifras t-h2 mt-2 text-balance break-words", alerta ? "text-rojo" : "text-tinta")}>{valor}</p>
      {detalle && <p className={clases("t-small mt-1", alerta ? "text-rojo" : "text-grafito")}>{detalle}</p>}
    </div>
  );
}

function Plegable({ titulo, children, id }: { titulo: string; children: ReactNode; id?: string }) {
  return (
    <details>
      <summary id={id} className="t-small cursor-pointer select-none text-azul-tinta underline underline-offset-4">{titulo}</summary>
      <div className="mt-4">{children}</div>
    </details>
  );
}

function PreguntaUnToque({ q, onResponder }: { q: PreguntaRenta; onResponder: (v: string) => void }) {
  const actual = q.respuesta ?? q.defecto;
  return (
    <li className="space-y-2">
      <p className="t-body text-tinta">{q.texto}</p>
      <div role="group" aria-label={q.texto} className="flex flex-wrap gap-2">
        {q.opciones.map((o) => (
          <button
            key={o.id}
            type="button"
            aria-pressed={actual === o.id}
            // La sugerida también se puede confirmar con un toque (antes solo cambiando de opción).
            onClick={() => (actual !== o.id || !q.confirmada) && onResponder(o.id)}
            className={clases(
              "t-small rounded-full border px-3.5 py-1.5 transition-colors duration-150",
              actual === o.id ? "border-tinta bg-tinta text-sobre-tinta" : "border-linea text-grafito hover:bg-hoja-2 hover:text-tinta",
            )}
          >
            {o.texto}
          </button>
        ))}
      </div>
    </li>
  );
}

function Beneficio({ b, maximo1, onCambio }: { b: BeneficioRenta; maximo1: string; onCambio: (c: CambioRenta) => Promise<void> }) {
  const activo = b.valor !== null && b.valor !== undefined && b.valor !== "" && b.valor !== false;
  const [valor, setValor] = useState(String(b.id === "compras_fe" ? maximo1 : b.valor && b.valor !== true ? b.valor : ""));
  const guardar = (v: string) => {
    if (b.id === "compras_fe") return onCambio({ tipo: "beneficio", id: b.id, valor: true, uno_por_ciento: v });
    return onCambio({ tipo: "beneficio", id: b.id, valor: v || null });
  };
  return (
    <li className="flex flex-wrap items-center justify-between gap-3 px-4 py-3.5">
      <div className="min-w-0 flex-1">
        <p className="t-body text-tinta">{b.texto}</p>
        <p className="t-small text-grafito">
          {b.ahorro_hasta && b.ahorro_hasta !== "0"
            ? <>Ahorro posible: hasta <span className="cifras font-semibold text-tinta">{pesos(b.ahorro_hasta)}</span> · </>
            : <>Este año no cambia el impuesto · </>}
          soporte: {b.soporte}
        </p>
      </div>
      <div className="flex flex-wrap items-center gap-2">
        {activo && b.id !== "compras_fe" && (
          b.id === "dependientes" ? (
            <select aria-label="Número de dependientes" className={estiloCampoAuto} value={valor}
              onChange={(e) => { setValor(e.target.value); guardar(e.target.value); }}>
              {[1, 2, 3, 4].map((n) => <option key={n} value={n}>{n}</option>)}
            </select>
          ) : (
            <input aria-label={`Valor: ${b.texto}`} inputMode="numeric" placeholder="Valor del certificado"
              className={clases(estiloCampoAuto, "cifras w-44")} value={valor}
              onChange={(e) => setValor(e.target.value.replace(/\D/g, ""))} onBlur={() => guardar(valor)} />
          )
        )}
        {activo && b.id === "compras_fe" && (
          <input aria-label="Valor del 1 % de compras" inputMode="numeric" className={clases(estiloCampoAuto, "cifras w-36")}
            value={valor} onChange={(e) => setValor(e.target.value.replace(/\D/g, ""))} onBlur={() => guardar(valor)} />
        )}
        <div role="group" aria-label={b.texto} className="flex gap-1">
          {(["si", "no"] as const).map((op) => (
            <button key={op} type="button" aria-pressed={(op === "si") === activo}
              onClick={() => {
                if (op === "si" && !activo) {
                  const inicial = b.id === "dependientes" ? "1" : b.id === "compras_fe" ? maximo1 : "";
                  setValor(inicial);
                  if (b.id === "dependientes" || b.id === "compras_fe") guardar(inicial);
                  else onCambio({ tipo: "beneficio", id: b.id, valor: true });
                }
                if (op === "no" && activo) onCambio({ tipo: "beneficio", id: b.id, valor: null });
              }}
              className={clases("t-small rounded-full border px-3 py-1",
                (op === "si") === activo ? "border-tinta bg-tinta text-sobre-tinta" : "border-linea text-grafito hover:bg-hoja-2")}>
              {op === "si" ? "Sí" : "No"}
            </button>
          ))}
        </div>
      </div>
    </li>
  );
}

function DetalleLineas({ decl, res, cliente, onCambio }: {
  decl: DeclaracionRenta; res: ResultadoRenta; cliente: Cliente; onCambio: (c: CambioRenta) => Promise<void>;
}) {
  const seguras = res.lineas.filter((l) => !l.confirmada && !l.encimada && (l.validada || l.confianza >= 0.85));
  const [editando, setEditando] = useState<string | null>(null);
  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="t-small max-w-2xl text-grafito">
          Nada leído de una foto entra sin que usted lo vea. Las filas en ámbar tienen texto superpuesto o una lectura
          dudosa: confírmelas. Cada fila se reclasifica con un clic.
        </p>
        {seguras.length > 0 && (
          <Boton variante="contorno" tamano="sm" onClick={() => onCambio({ tipo: "confirmar", lineas: seguras.map((l) => l.id) })}>
            Confirmar {seguras.length} valores seguros
          </Boton>
        )}
      </div>
      <div className="barra-fina overflow-x-auto rounded-hoja border border-linea bg-hoja">
        <table className="t-tabla min-w-full text-[13px]">
          <thead className="bg-hoja-2 text-left text-gris">
            <tr>
              <th className="px-3 py-2">En la foto</th>
              <th className="px-3">Entidad · detalle</th>
              <th className="px-3 text-right">Valor</th>
              <th className="px-3">Clasificación</th>
              <th className="px-3">Incluir</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-linea">
            {res.lineas.map((l) => (
              <FilaLinea key={l.id} l={l} decl={decl} cliente={cliente} editando={editando === l.id}
                onEditar={() => setEditando(l.id)} onFin={() => setEditando(null)} onCambio={onCambio} />
            ))}
          </tbody>
        </table>
      </div>
      <AgregarDato decl={decl} onCambio={onCambio} />
      {res.manuales.length > 0 && (
        <ul className="space-y-1.5">
          {res.manuales.map((m) => (
            <li key={m.id} className="t-small flex flex-wrap items-center gap-3 text-grafito">
              <span className="text-tinta">{decl.categorias[m.categoria] ?? ETIQUETA_MANUAL[m.categoria] ?? m.categoria}</span>
              <span className="cifras font-semibold text-tinta">{pesos(m.valor)}</span>
              {m.descripcion && <span>{m.descripcion}</span>}
              <button type="button" className="underline underline-offset-4" onClick={() => onCambio({ tipo: "quitar_agregado", id: m.id })}>
                Quitar
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function FilaLinea({ l, decl, cliente, editando, onEditar, onFin, onCambio }: {
  l: LineaRenta; decl: DeclaracionRenta; cliente: Cliente; editando: boolean;
  onEditar: () => void; onFin: () => void; onCambio: (c: CambioRenta) => Promise<void>;
}) {
  const [valor, setValor] = useState(l.valor);
  const ambar = l.encimada && !l.confirmada;
  return (
    <tr className={clases("align-top", ambar && "bg-ambar-suave", !l.incluida && "opacity-60")}>
      <td className="px-3 py-2">
        {l.recorte ? (
          <img src={renta.recorte(cliente.id, decl.anio, l.recorte)} alt={`Fila ${l.fila} de ${l.documento}`} loading="lazy"
            className="max-h-10 max-w-[260px] rounded-sm border border-linea object-contain" />
        ) : (
          <span className="t-meta text-gris">{l.documento}</span>
        )}
      </td>
      <td className="max-w-[340px] px-3 py-2">
        <p className="font-medium text-tinta">{l.entidad || "—"}</p>
        <p className="text-grafito">{l.detalle}</p>
        <p className="mt-1 flex flex-wrap gap-1">
          {l.resaltada && <Insignia tono="lima">Marcada en el papel</Insignia>}
          {l.no_titular && <Insignia tono="ambar">No es el titular principal</Insignia>}
          {ambar && <Insignia tono="ambar">Texto superpuesto: confirme este valor</Insignia>}
          {l.corregida && <Insignia tono="ambar">Corregida para cuadrar: verifique</Insignia>}
          {l.validada && !l.corregida && <Insignia tono="azul">Cuadra con el tope</Insignia>}
          {l.conflicto && <Insignia tono="ambar">La DIAN sugiere otro renglón</Insignia>}
        </p>
      </td>
      <td className="px-3 py-2 text-right">
        {editando ? (
          <input autoFocus aria-label="Valor" inputMode="numeric" className={clases(estiloCampoAuto, "cifras w-36 text-right")}
            value={valor} onChange={(e) => setValor(e.target.value.replace(/\D/g, ""))}
            onBlur={async () => { if (valor !== l.valor) await onCambio({ tipo: "valor", linea: l.id, valor }); onFin(); }} />
        ) : (
          <button type="button" onClick={onEditar} className="cifras font-semibold text-tinta underline-offset-4 hover:underline"
            aria-label={`Editar el valor ${pesos(l.valor)}`}>
            {pesos(l.valor)}
          </button>
        )}
        {l.alternativas.length > 0 && !editando && (
          <button type="button" className="t-meta mt-1 block text-azul-tinta underline underline-offset-4"
            onClick={() => onCambio({ tipo: "valor", linea: l.id, valor: l.alternativas[0] })}>
            ¿Era {pesos(l.alternativas[0])}?
          </button>
        )}
      </td>
      <td className="px-3 py-2">
        <select aria-label="Clasificación" className={clases(estiloCampo, "min-w-[220px]")} value={l.categoria}
          onChange={(e) => onCambio({ tipo: "reclasificar", linea: l.id, categoria: e.target.value })}>
          {Object.entries(decl.categorias).map(([k, t]) => <option key={k} value={k}>{t}</option>)}
        </select>
        <p className="t-meta mt-1 text-gris">{l.motivo}</p>
      </td>
      <td className="px-3 py-2">
        <input type="checkbox" aria-label="Incluir esta línea" checked={l.incluida} className="h-4 w-4"
          onChange={() => onCambio({ tipo: "excluir", linea: l.id })} />
      </td>
    </tr>
  );
}

const ETIQUETA_MANUAL: Record<string, string> = {
  ingreso_no_laboral: "Ingresos no laborales (ventas, negocio)",
  costo_no_laboral: "Costos y gastos del negocio",
  ingreso_trabajo: "Salarios",
  ingreso_honorarios: "Honorarios con costos",
  costo_honorarios: "Costos de los honorarios",
  ingreso_capital_otro: "Arrendamientos y otras rentas de capital",
  costo_capital: "Costos de las rentas de capital",
  incr_trabajo: "Aportes obligatorios",
  patrimonio: "Patrimonio",
  deuda: "Deudas",
  retencion: "Retenciones",
  pension: "Pensiones",
  dividendo: "Dividendos",
  ganancia_ocasional: "Ganancias ocasionales",
};

function AgregarDato({ decl, onCambio }: { decl: DeclaracionRenta; onCambio: (c: CambioRenta) => Promise<void> }) {
  const [categoria, setCategoria] = useState(decl.manuales_categorias[0] ?? "ingreso_no_laboral");
  const [valor, setValor] = useState("");
  const [descripcion, setDescripcion] = useState("");
  return (
    <form
      className="flex flex-wrap items-end gap-2"
      onSubmit={async (e) => {
        e.preventDefault();
        if (!valor) return;
        const dato = { tipo: "agregar" as const, categoria, valor, descripcion };
        // Se limpia al enviar: si se limpia al volver la respuesta, se borra lo que ya se escribió después.
        setValor("");
        setDescripcion("");
        await onCambio(dato);
      }}
    >
      <label className="block">
        <span className="t-meta mb-1 block text-gris">Agregar un dato que no está en la exógena</span>
        <select aria-label="Qué es" className={estiloCampoAuto} value={categoria} onChange={(e) => setCategoria(e.target.value)}>
          {decl.manuales_categorias.map((c) => <option key={c} value={c}>{ETIQUETA_MANUAL[c] ?? c}</option>)}
        </select>
      </label>
      <input aria-label="Valor del dato" inputMode="numeric" placeholder="Valor" className={clases(estiloCampoAuto, "cifras w-40")}
        value={valor} onChange={(e) => setValor(e.target.value.replace(/\D/g, ""))} />
      <input aria-label="Descripción" placeholder="Descripción (opcional)" className={clases(estiloCampoAuto, "w-56")}
        value={descripcion} onChange={(e) => setDescripcion(e.target.value)} />
      <Boton type="submit" variante="contorno" tamano="sm" disabled={!valor}>Agregar</Boton>
    </form>
  );
}

function irA(id: string) {
  const el = document.getElementById(id);
  if (!el) return;
  const plegable = el.closest("details");
  if (plegable) plegable.open = true;
  el.scrollIntoView({ behavior: "smooth", block: "start" });
}

/** «Para terminar faltan N cosas»: arriba y siempre visible, con un botón por cada cosa. */
function CajaPendientes({ res, onConfirmarFilas, onDigitar }: {
  res: ResultadoRenta; onConfirmarFilas: (ids: string[]) => void; onDigitar: () => void;
}) {
  const lista = res.pendientes ?? [];
  const n = lista.length || (res.motivos_incompleto ?? []).length;
  return (
    <section aria-labelledby="titulo-pendientes" className="space-y-4 rounded-hoja border border-ambar bg-ambar-suave p-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 id="titulo-pendientes" className="t-h2 text-tinta">
          Para terminar {n === 1 ? "falta 1 cosa" : `faltan ${n} cosas`}
        </h2>
        {res.ofrecer_digitar_esencial && (
          <Boton variante="contorno" tamano="sm" onClick={onDigitar}>Digitar lo esencial</Boton>
        )}
      </div>
      <p className="t-small text-grafito">
        Mientras falte algo, la aplicación no muestra impuesto ni sanción: así nunca hay una cifra equivocada.
      </p>
      <ul className="space-y-2">
        {lista.map((p, i) => (
          <li key={i} className="flex flex-wrap items-center justify-between gap-3 rounded-control bg-hoja px-4 py-3">
            <div className="min-w-0 flex-1">
              <p className="t-body font-medium text-tinta">{p.texto}</p>
              {p.comparacion && <p className="t-small cifras text-grafito">{p.comparacion}</p>}
            </div>
            <Boton
              variante="solido"
              tamano="sm"
              onClick={() => {
                if (p.tipo === "confirmar_filas") onConfirmarFilas(p.lineas ?? []);
                else if (p.tipo === "preguntas") irA("titulo-confirmar");
                else if (p.tipo === "negocio") irA("titulo-solo-usted");
                else irA("detalle-lineas");
              }}
            >
              {p.accion}
            </Boton>
          </li>
        ))}
        {!lista.length && (res.motivos_incompleto ?? []).map((m, i) => (
          <li key={i} className="t-small rounded-control bg-hoja px-4 py-3 text-tinta">{m}</li>
        ))}
      </ul>
    </section>
  );
}

/** Confirmar las filas dudosas: el recorte de la foto al lado de cada valor; se puede corregir antes. */
function ConfirmarFilas({ res, ids, cliente, anio, onCerrar, onCambio }: {
  res: ResultadoRenta; ids: string[]; cliente: Cliente; anio: number; onCerrar: () => void;
  onCambio: (c: CambioRenta) => Promise<void>;
}) {
  const filas = res.lineas.filter((l) => ids.includes(l.id));
  const [valores, setValores] = useState<Record<string, string>>(() => Object.fromEntries(filas.map((l) => [l.id, l.valor])));
  const [trabajando, setTrabajando] = useState(false);
  const confirmar = async () => {
    setTrabajando(true);
    try {
      for (const l of filas) {
        if (valores[l.id] !== l.valor) await onCambio({ tipo: "valor", linea: l.id, valor: valores[l.id] });
      }
      await onCambio({ tipo: "confirmar", lineas: filas.map((l) => l.id) });
      onCerrar();
    } finally {
      setTrabajando(false);
    }
  };
  return (
    <Dialogo
      rotulo="Filas leídas de la foto"
      titulo={`Confirmar ${filas.length} fila(s)`}
      onCerrar={onCerrar}
      ancho="max-w-3xl"
      pie={
        <>
          <Boton variante="fantasma" onClick={onCerrar}>Cancelar</Boton>
          <Boton variante="solido" cargando={trabajando} onClick={confirmar}>Confirmar todas</Boton>
        </>
      }
    >
      <p className="t-small mb-4 text-grafito">
        Compare cada valor con el recorte de la foto. Si alguno está mal, corríjalo aquí antes de confirmar.
      </p>
      <ul className="divide-y divide-linea">
        {filas.map((l) => (
          <li key={l.id} className="grid gap-3 py-3 sm:grid-cols-[1fr_auto] sm:items-center">
            <div className="min-w-0 space-y-1">
              {l.recorte ? (
                <img src={renta.recorte(cliente.id, anio, l.recorte)} alt={`Fila ${l.fila} de ${l.documento}`}
                  className="max-h-14 w-full rounded-sm border border-linea object-contain object-left" />
              ) : (
                <p className="t-meta text-gris">{l.documento} · fila {l.fila}</p>
              )}
              <p className="t-small text-tinta">{l.entidad || "—"} · {l.detalle}</p>
            </div>
            <input aria-label={`Valor de ${l.detalle}`} inputMode="numeric" value={valores[l.id] ?? ""}
              onChange={(e) => setValores({ ...valores, [l.id]: e.target.value.replace(/\D/g, "") })}
              className={clases(estiloCampoAuto, "cifras w-40 text-right")} />
          </li>
        ))}
      </ul>
    </Dialogo>
  );
}

/** «Ingresos y costos del negocio»: con la comparación que explica por qué se piden. */
function Negocio({ res, onCambio }: { res: ResultadoRenta; onCambio: (c: CambioRenta) => Promise<void> }) {
  const senales = res.negocio!.senales!;
  const actual = res.negocio?.valor ?? null;
  const [ingresos, setIngresos] = useState(String(actual?.ingresos ?? "").replace(/\.0+$/, ""));
  const [costos, setCostos] = useState(String(actual?.costos ?? "").replace(/\.0+$/, ""));
  const [nota, setNota] = useState(actual?.nota ?? "");
  const [trabajando, setTrabajando] = useState(false);
  const guardar = async (c: CambioRenta) => {
    setTrabajando(true);
    try { await onCambio(c); } finally { setTrabajando(false); }
  };
  return (
    <div className="material-hoja space-y-4 p-5">
      <div>
        <h3 className="t-h3 text-tinta">Ingresos y costos del negocio</h3>
        <p className="t-small mt-1 text-grafito">Se piden porque hay {senales.motivos.join("; ")}.</p>
        <p className="cifras t-body mt-2 text-tinta">{senales.comparacion}</p>
      </div>
      {actual?.sin_negocio ? (
        <p className="t-small text-grafito">Usted indicó que no tiene negocio: se usa lo que reportaron terceros.</p>
      ) : null}
      <div className="grid gap-3 sm:grid-cols-3">
        <Campo etiqueta="Ingresos del negocio en el año">
          <input inputMode="numeric" value={ingresos} onChange={(e) => setIngresos(e.target.value.replace(/\D/g, ""))}
            className={clases(estiloCampo, "cifras")} placeholder="65400000" />
        </Campo>
        <Campo etiqueta="Costos y gastos del negocio">
          <input inputMode="numeric" value={costos} onChange={(e) => setCostos(e.target.value.replace(/\D/g, ""))}
            className={clases(estiloCampo, "cifras")} placeholder="32800000" />
        </Campo>
        <Campo etiqueta="Nota (opcional)">
          <input value={nota} onChange={(e) => setNota(e.target.value)} className={estiloCampo}
            placeholder="De dónde salen las cifras" />
        </Campo>
      </div>
      <div className="flex flex-wrap gap-2">
        <Boton variante="solido" tamano="sm" cargando={trabajando} disabled={!ingresos}
          onClick={() => guardar({ tipo: "negocio", ingresos, costos: costos || "0", nota })}>
          Guardar ingresos y costos
        </Boton>
        <Boton variante="fantasma" tamano="sm" disabled={trabajando} onClick={() => guardar({ tipo: "negocio", sin_negocio: true })}>
          No tiene negocio
        </Boton>
      </div>
    </div>
  );
}

/** Las dos columnas explicadas: cada diferencia con su razón en una línea. */
function Diferencias({ res }: { res: ResultadoRenta }) {
  const lista = res.diferencias.filter((d) => d.dian !== d.optimizada);
  if (!lista.length || res.incompleto) return null;
  return (
    <section aria-labelledby="titulo-diferencias" className="space-y-3">
      <h2 id="titulo-diferencias" className="t-h2 text-tinta">Por qué su declaración es distinta a la de la DIAN</h2>
      <ul className="divide-y divide-linea rounded-hoja border border-linea bg-hoja">
        {lista.slice(0, 12).map((d) => {
          const c = res.casillas.find((x) => x.casilla === d.casilla);
          return (
            <li key={d.casilla} className="grid gap-1 px-4 py-3 sm:grid-cols-[5rem_1fr_auto] sm:items-baseline sm:gap-4">
              <span className="codigo text-gris">Casilla {d.casilla}</span>
              <span className="t-small text-tinta">
                {c?.nombre}{c?.columna ? ` — ${c.columna}` : ""}
                <span className="block text-grafito">{d.por_que || d.motivo}</span>
              </span>
              <span className="cifras t-small whitespace-nowrap text-right">
                <span className="text-grafito">DIAN {pesos(d.dian)}</span> · <strong className="text-tinta">Usted {pesos(d.optimizada)}</strong>
              </span>
            </li>
          );
        })}
      </ul>
    </section>
  );
}

function Casillas({ res, onCambio }: { res: ResultadoRenta; onCambio: (c: CambioRenta) => Promise<void> }) {
  const conValor = res.casillas.filter((c) => c.dian !== "0" || c.optimizada !== "0" || c.ajuste);
  const [abierta, setAbierta] = useState<number | null>(null);
  return (
    <div className="barra-fina overflow-x-auto rounded-hoja border border-linea bg-hoja">
      <table className="t-tabla min-w-full text-[13px]">
        <thead className="bg-hoja-2 text-left text-gris">
          <tr>
            <th className="px-3 py-2">Casilla</th>
            <th className="px-3">Concepto</th>
            <th className="px-3 text-right">Lo que propondría la DIAN</th>
            <th className="px-3 text-right">Su declaración</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-linea">
          {conValor.map((c) => {
            const distinta = c.dian !== c.optimizada;
            const dif = res.diferencias.find((d) => d.casilla === c.casilla);
            return (
              <Fragment key={c.casilla}>
                <tr className={clases("cursor-pointer hover:bg-hoja-2", distinta && "bg-azul-suave/40")}
                  onClick={() => setAbierta(abierta === c.casilla ? null : c.casilla)}
                  aria-expanded={abierta === c.casilla}>
                  <td className="codigo px-3 py-2 text-gris">{c.casilla}</td>
                  <td className="px-3 py-2">
                    <p className="text-tinta">
                      {c.nombre}{c.columna ? ` — ${c.columna}` : ""}
                      {c.ajuste && <Insignia tono="ambar">Ajuste manual</Insignia>}
                    </p>
                    {(dif?.por_que || c.explicacion) && <p className="t-meta text-gris">{dif?.por_que || c.explicacion}</p>}
                  </td>
                  <td className="cifras px-3 py-2 text-right text-grafito">{pesos(c.dian)}</td>
                  <td className="cifras px-3 py-2 text-right font-semibold text-tinta">{pesos(c.optimizada)}</td>
                </tr>
                {abierta === c.casilla && (
                  <tr className="bg-hoja-2">
                    <td />
                    <td colSpan={3} className="px-3 py-3">
                      <DetalleCasilla c={c} res={res} onCambio={onCambio} />
                    </td>
                  </tr>
                )}
              </Fragment>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

/** Clic en una casilla: de dónde sale y, si es un dato, el ajuste manual con nota obligatoria. */
function DetalleCasilla({ c, res, onCambio }: { c: CasillaRenta; res: ResultadoRenta; onCambio: (c: CambioRenta) => Promise<void> }) {
  const [valor, setValor] = useState(String(c.ajuste?.valor ?? c.optimizada).replace(/\.0+$/, ""));
  const [nota, setNota] = useState(c.ajuste?.nota ?? "");
  const lineas = res.lineas.filter((l) => l.incluida && l.renglon === c.casilla);
  return (
    <div className="space-y-3">
      <p className="t-small text-grafito">
        {c.formula ? <>Cómo se calcula: <span className="text-tinta">{c.formula}</span>. </> : null}
        {c.explicacion}
      </p>
      {lineas.length > 0 && (
        <ul className="t-small space-y-0.5 text-grafito">
          {lineas.map((l) => <li key={l.id}>{l.entidad} · {l.detalle}: <span className="cifras text-tinta">{pesos(l.valor)}</span></li>)}
        </ul>
      )}
      {c.editable ? (
        <div className="flex flex-wrap items-end gap-2">
          <Campo etiqueta="Ajuste manual">
            <input inputMode="numeric" value={valor} onChange={(e) => setValor(e.target.value.replace(/\D/g, ""))}
              className={clases(estiloCampoAuto, "cifras w-40 text-right")} aria-label={`Ajuste de la casilla ${c.casilla}`} />
          </Campo>
          <Campo etiqueta="Nota (obligatoria)">
            <input value={nota} onChange={(e) => setNota(e.target.value)} className={clases(estiloCampoAuto, "w-72")}
              aria-label={`Nota del ajuste de la casilla ${c.casilla}`} placeholder="Por qué se ajusta" />
          </Campo>
          <Boton variante="solido" tamano="sm" disabled={!nota.trim() || !valor}
            onClick={() => onCambio({ tipo: "ajuste_casilla", casilla: c.casilla, valor, nota: nota.trim() })}>
            Guardar ajuste
          </Boton>
          {c.ajuste && (
            <Boton variante="fantasma" tamano="sm" onClick={() => onCambio({ tipo: "quitar_ajuste_casilla", casilla: c.casilla })}>
              Quitar ajuste
            </Boton>
          )}
        </div>
      ) : (
        <p className="t-meta text-gris">Esta casilla se calcula con otras: ajuste la casilla de donde sale.</p>
      )}
    </div>
  );
}

function DialogoPresentada({ onCerrar, onGuardar }: { onCerrar: () => void; onGuardar: (numero: string, fecha: string) => Promise<void> }) {
  const [numero, setNumero] = useState("");
  const [f, setF] = useState(() => {
    const hoy = new Date();  // fecha local: con toISOString saldría el día siguiente después de las 7 p. m.
    return `${hoy.getFullYear()}-${String(hoy.getMonth() + 1).padStart(2, "0")}-${String(hoy.getDate()).padStart(2, "0")}`;
  });
  const [trabajando, setTrabajando] = useState(false);
  return (
    <Dialogo
      rotulo="Renta"
      titulo="Marcar como presentada"
      onCerrar={onCerrar}
      ancho="max-w-md"
      pie={
        <>
          <Boton variante="fantasma" onClick={onCerrar}>Cancelar</Boton>
          <Boton variante="solido" cargando={trabajando} disabled={!numero.trim()}
            onClick={async () => { setTrabajando(true); await onGuardar(numero, f); setTrabajando(false); }}>
            Guardar
          </Boton>
        </>
      }
    >
      <div className="space-y-4">
        <label className="block">
          <span className="t-meta mb-1 block text-gris">Número de formulario</span>
          <input className={clases(estiloCampo, "cifras")} value={numero} onChange={(e) => setNumero(e.target.value.replace(/\D/g, ""))} />
        </label>
        <label className="block">
          <span className="t-meta mb-1 block text-gris">Fecha de presentación</span>
          <input type="date" className={estiloCampo} value={f} onChange={(e) => setF(e.target.value)} />
        </label>
        <p className="t-small text-grafito">Estos valores alimentan la declaración del año siguiente.</p>
      </div>
    </Dialogo>
  );
}

function ModalDigitarEsencial({
  cliente,
  res,
  onCerrar,
  onGuardado,
}: {
  cliente: Cliente;
  res: ResultadoRenta;
  onCerrar: () => void;
  onGuardado: (decl: DeclaracionRenta) => void;
}) {
  const avisar = useAvisos();
  const [guardando, setGuardando] = useState(false);

  const topesDict: Record<string, string> = {};
  for (const v of res.validacion || []) {
    topesDict[String(v.tope)] = String(v.encabezado || "");
  }

  const [tope1, setTope1] = useState(topesDict["1"] || "");
  const [tope2, setTope2] = useState(topesDict["2"] || "");
  const [tope3, setTope3] = useState(topesDict["3"] || "");
  const [tope4, setTope4] = useState(topesDict["4"] || "");
  const [tope5, setTope5] = useState(topesDict["5"] || "");
  const [tope6, setTope6] = useState(true);

  const [ingresos, setIngresos] = useState(topesDict["1"] || "");
  const [patrimonio, setPatrimonio] = useState(topesDict["2"] || "");
  const [deudas, setDeudas] = useState("0");
  const [retenciones, setRetenciones] = useState("0");
  // Rescate: antes venían fijos los valores de un contribuyente real. Ahora salen de lo leído (la nota
  // «SF» escrita a mano o la línea del año anterior) o quedan vacíos.
  const sugeridoSaldo = String(res.preguntas.find((q) => q.id === "saldo_favor")?.detalle ?? "").replace(/\D/g, "");
  const [saldoFavorAnterior, setSaldoFavorAnterior] = useState(sugeridoSaldo);
  const [patrimonioAnterior, setPatrimonioAnterior] = useState("");

  const guardar = async () => {
    setGuardando(true);
    try {
      const datos = {
        topes: {
          "1": tope1.replace(/\D/g, "") || "0",
          "2": tope2.replace(/\D/g, "") || "0",
          "3": tope3.replace(/\D/g, "") || "0",
          "4": tope4.replace(/\D/g, "") || "0",
          "5": tope5.replace(/\D/g, "") || "0",
          "6": tope6,
        },
        esenciales: [
          { categoria: "ingreso_no_laboral", valor: ingresos.replace(/\D/g, "") || "0", detalle: "Ingresos documentos soporte / actividades ordinarias", tope: 1 },
          { categoria: "patrimonio", valor: patrimonio.replace(/\D/g, "") || "0", detalle: "Bienes, avalúos catastrales y saldos", tope: 2 },
          { categoria: "deuda", valor: deudas.replace(/\D/g, "") || "0", detalle: "Total deudas a 31 de diciembre" },
          { categoria: "retencion", valor: retenciones.replace(/\D/g, "") || "0", detalle: "Retenciones practicadas" },
        ],
        anterior_saldo_favor: saldoFavorAnterior.replace(/\D/g, "") || "0",
        anterior_patrimonio: patrimonioAnterior.replace(/\D/g, "") || "0",
        respuestas: { saldo_favor: saldoFavorAnterior.replace(/\D/g, "") ? "si" : "no" },
      };
      const nueva = await renta.digitarEsencial(cliente.id, ANIO, datos);
      avisar("Datos esenciales validados y liquidados exitosamente.");
      onGuardado(nueva);
      onCerrar();
    } catch (e) {
      avisar((e as Error).message, "rojo");
    } finally {
      setGuardando(false);
    }
  };

  return (
    <Dialogo
      rotulo="Entrada rápida"
      titulo="Digitar lo esencial"
      onCerrar={onCerrar}
      ancho="max-w-2xl"
      pie={
        <>
          <Boton variante="fantasma" onClick={onCerrar}>Cancelar</Boton>
          <Boton variante="solido" cargando={guardando} onClick={guardar}>
            Validar y liquidar formulario 210
          </Boton>
        </>
      }
    >
      <div className="space-y-6 text-sm">
        <p className="t-body text-grafito">
          Escriba los 6 topes y las cifras clave de la exógena con la foto o reporte al lado. La aplicación validará las sumas y liquidará el formulario 210 inmediatamente.
        </p>

        <div className="rounded-hoja border border-linea bg-hoja p-4 space-y-4">
          <h3 className="font-semibold text-tinta">1. Topes del reporte oficial</h3>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
            <label className="block">
              <span className="t-meta mb-1 block text-gris">Tope 1 · Ingresos</span>
              <input className={clases(estiloCampo, "cifras")} value={tope1} onChange={(e) => setTope1(e.target.value)} placeholder="Valor del reporte" />
            </label>
            <label className="block">
              <span className="t-meta mb-1 block text-gris">Tope 2 · Patrimonio</span>
              <input className={clases(estiloCampo, "cifras")} value={tope2} onChange={(e) => setTope2(e.target.value)} placeholder="Valor del reporte" />
            </label>
            <label className="block">
              <span className="t-meta mb-1 block text-gris">Tope 3 · Tarjeta crédito</span>
              <input className={clases(estiloCampo, "cifras")} value={tope3} onChange={(e) => setTope3(e.target.value)} placeholder="Valor del reporte" />
            </label>
            <label className="block">
              <span className="t-meta mb-1 block text-gris">Tope 4 · Movimientos</span>
              <input className={clases(estiloCampo, "cifras")} value={tope4} onChange={(e) => setTope4(e.target.value)} placeholder="Valor del reporte" />
            </label>
            <label className="block">
              <span className="t-meta mb-1 block text-gris">Tope 5 · Compras</span>
              <input className={clases(estiloCampo, "cifras")} value={tope5} onChange={(e) => setTope5(e.target.value)} placeholder="Valor del reporte" />
            </label>
            <label className="flex items-center gap-2 pt-6">
              <input type="checkbox" checked={tope6} onChange={(e) => setTope6(e.target.checked)} className="h-4 w-4 rounded border-linea text-azul" />
              <span className="t-meta text-tinta">Responsable de IVA (Tope 6)</span>
            </label>
          </div>
        </div>

        <div className="rounded-hoja border border-linea bg-hoja p-4 space-y-4">
          <h3 className="font-semibold text-tinta">2. Cifras clave a declarar</h3>
          <div className="grid grid-cols-2 gap-3">
            <label className="block">
              <span className="t-meta mb-1 block text-gris">Ingresos del año ($)</span>
              <input className={clases(estiloCampo, "cifras")} value={ingresos} onChange={(e) => setIngresos(e.target.value)} />
            </label>
            <label className="block">
              <span className="t-meta mb-1 block text-gris">Patrimonio bruto ($)</span>
              <input className={clases(estiloCampo, "cifras")} value={patrimonio} onChange={(e) => setPatrimonio(e.target.value)} />
            </label>
            <label className="block">
              <span className="t-meta mb-1 block text-gris">Deudas a 31 dic ($)</span>
              <input className={clases(estiloCampo, "cifras")} value={deudas} onChange={(e) => setDeudas(e.target.value)} />
            </label>
            <label className="block">
              <span className="t-meta mb-1 block text-gris">Retenciones en la fuente ($)</span>
              <input className={clases(estiloCampo, "cifras")} value={retenciones} onChange={(e) => setRetenciones(e.target.value)} />
            </label>
          </div>
        </div>

        <div className="rounded-hoja border border-linea bg-hoja p-4 space-y-4">
          <h3 className="font-semibold text-tinta">3. Datos del año anterior</h3>
          <div className="grid grid-cols-2 gap-3">
            <label className="block">
              <span className="t-meta mb-1 block text-gris">Saldo a favor año anterior ($)</span>
              <input className={clases(estiloCampo, "cifras")} value={saldoFavorAnterior} onChange={(e) => setSaldoFavorAnterior(e.target.value)} />
            </label>
            <label className="block">
              <span className="t-meta mb-1 block text-gris">Patrimonio bruto año anterior ($)</span>
              <input className={clases(estiloCampo, "cifras")} value={patrimonioAnterior} onChange={(e) => setPatrimonioAnterior(e.target.value)} />
            </label>
          </div>
        </div>
      </div>
    </Dialogo>
  );
}

