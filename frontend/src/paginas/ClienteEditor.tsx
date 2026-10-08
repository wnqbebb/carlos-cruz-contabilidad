import { ArrowLeft, ChevronDown, Upload } from "lucide-react";
import { useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { Link, useLocation, useNavigate, useParams } from "react-router-dom";
import { clientes as api, puerta } from "../api";
import { clases, pesos } from "../formato";
import type { Cliente, ComparacionFicha, FichaExtraida, Socio } from "../tipos";
import { Aviso, Boton, Campo, Cargando, Dialogo, Insignia, Tarjeta, estiloCampo } from "../componentes/ui";
import { EnlaceSubrayado } from "../ui";

/**
 * Cliente: crear fácil, editar todo (spec v2.2 · Fase 6).
 *
 * · Nuevo: lo único visible es NIT o cédula (con su dígito de verificación
 *   calculado al escribir) y el nombre. Todo lo demás va plegado en «Más
 *   datos (opcional)». El camino normal no es digitar: es «Llenar desde
 *   documentos», que lee estatutos, RUT, cámara y cartas y muestra la ficha
 *   extraída con el origen y la confianza de cada dato antes de guardar.
 * · Editar: la ficha completa, y se pueden soltar documentos nuevos para ver
 *   qué campos cambiarían (nada se guarda sin confirmar).
 */

type Borrador = Partial<Cliente> & { socios?: Socio[] };

const VACIO: Borrador = {
  nit: "", razon_social: "", sigla: "", tipo_persona: "juridica", regimen: "responsable_iva", grupo_niif: 3,
  responsable_iva: true, tarifa_renta: "0.35", ciiu: "", direccion: "", municipio: "", departamento: "",
  telefono: "", email: "", rep_legal: "", rep_legal_cc: "", rep_legal_suplente: "", contador: "", contador_cc: "",
  contador_tp: "", fecha_constitucion: null, capital_suscrito: "0", valor_nominal_accion: "0", honorarios_mes: "0",
  periodicidad: "mensual", estado: "activo", etiquetas: [], notas: "", socios: [], tipo_sociedad: "",
  objeto_social: "", documento_constitucion: "", capital_autorizado: "0", capital_pagado: "0", numero_acciones: "0",
  rep_legal_suplente_cc: "", revisor_fiscal: "", revisor_fiscal_tp: "", matricula_mercantil: "",
  fecha_renovacion: null, ciiu_secundarios: "", responsabilidades: "",
};

/** Nombre legible de cada campo de la ficha, en el orden en que se muestran. */
export const ETIQUETAS: Record<string, string> = {
  razon_social: "Razón social", nit: "NIT o cédula", dv: "Dígito de verificación", sigla: "Sigla",
  tipo_sociedad: "Tipo de sociedad", tipo_persona: "Tipo de persona", municipio: "Municipio",
  departamento: "Departamento", direccion: "Dirección", telefono: "Teléfono", email: "Correo electrónico",
  ciiu: "CIIU principal", ciiu_secundarios: "CIIU secundarios", objeto_social: "Objeto social",
  fecha_constitucion: "Fecha de constitución", documento_constitucion: "Documento de constitución",
  capital_autorizado: "Capital autorizado", capital_suscrito: "Capital suscrito", capital_pagado: "Capital pagado",
  numero_acciones: "Número de acciones", valor_nominal_accion: "Valor nominal por acción",
  rep_legal: "Representante legal", rep_legal_cc: "Cédula del representante", rep_legal_suplente: "Suplente",
  rep_legal_suplente_cc: "Cédula del suplente", revisor_fiscal: "Revisor fiscal", revisor_fiscal_tp: "T.P. del revisor",
  contador: "Contador", contador_cc: "Cédula del contador", contador_tp: "T.P. del contador",
  matricula_mercantil: "Matrícula mercantil", fecha_renovacion: "Renovación de la matrícula",
  responsabilidades: "Responsabilidades tributarias", responsable_iva: "Responsable de IVA",
};
const DINERO = new Set(["capital_autorizado", "capital_suscrito", "capital_pagado", "valor_nominal_accion", "honorarios_mes"]);

const REGIMENES = [
  ["responsable_iva", "Responsable de IVA"], ["no_responsable_iva", "No responsable de IVA"],
  ["gran_contribuyente", "Gran contribuyente"], ["simple", "Régimen simple"], ["especial", "Régimen especial (ESAL)"],
];
const PERIODICIDADES = ["mensual", "bimestral", "trimestral", "cuatrimestral", "anual"];
const PRIMOS = [3, 7, 13, 17, 19, 23, 29, 37, 41, 43, 47, 53, 59, 67, 71];

/** Dígito de verificación del NIT (DIAN), igual que `utils/nit.py`. */
export function digitoVerificacion(nit: string): string {
  const base = (nit || "").replace(/\D/g, "");
  if (!base || base.length > PRIMOS.length) return "";
  const suma = base.split("").reverse().reduce((s, d, i) => s + Number(d) * PRIMOS[i], 0);
  const r = suma % 11;
  return String(r < 2 ? r : 11 - r);
}

/** Valor de la ficha extraída convertido al tipo del formulario. */
function aBorrador(campo: string, valor: string): unknown {
  if (campo === "responsable_iva") return valor === "true";
  return valor;
}

export function ClienteEditor() {
  const { id } = useParams<{ id: string }>();
  const esNuevo = !id || id === "nuevo";
  const navegar = useNavigate();
  const ubicacion = useLocation();

  const [datos, setDatos] = useState<Borrador>(VACIO);
  const [original, setOriginal] = useState<Borrador | null>(null);
  const [cargando, setCargando] = useState(!esNuevo);
  const [guardando, setGuardando] = useState(false);
  const [error, setError] = useState("");
  const [masDatos, setMasDatos] = useState(!esNuevo);
  const [extraida, setExtraida] = useState<FichaExtraida | null>(null);
  const [comparacion, setComparacion] = useState<ComparacionFicha | null>(null);
  const [leyendo, setLeyendo] = useState(false);
  const [confirmarNit, setConfirmarNit] = useState(false);

  useEffect(() => {
    if (esNuevo) {
      // La puerta única manda aquí la ficha que ya leyó de los documentos.
      const estado = ubicacion.state as { ficha?: Partial<Cliente>; extraida?: FichaExtraida } | null;
      if (estado?.extraida) setExtraida(estado.extraida);
      else if (estado?.ficha) setDatos((d) => ({ ...d, ...estado.ficha }));
      return;
    }
    api
      .obtener(id!)
      .then((c) => {
        const b = { ...VACIO, ...c, socios: c.socios ?? [] };
        setDatos(b);
        setOriginal(b);
      })
      .catch((e) => setError((e as Error).message))
      .finally(() => setCargando(false));
  }, [id, esNuevo, ubicacion.state]);

  const set = <K extends keyof Borrador>(campo: K, valor: Borrador[K]) => setDatos((d) => ({ ...d, [campo]: valor }));
  const dv = useMemo(() => digitoVerificacion(String(datos.nit ?? "")), [datos.nit]);
  const listo = !!String(datos.nit ?? "").replace(/\D/g, "") && !!String(datos.razon_social ?? "").trim();

  const leerDocumentos = async (archivos: File[]) => {
    if (!archivos.length) return;
    setLeyendo(true);
    setError("");
    try {
      if (esNuevo) setExtraida((await puerta.identidad(archivos)).ficha);
      else setComparacion(await api.compararFicha(id!, archivos));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLeyendo(false);
    }
  };

  const guardar = async (conNit = false) => {
    const cambiaNit = !esNuevo && original && String(original.nit) !== String(datos.nit).replace(/\D/g, "");
    if (cambiaNit && !conNit) {
      setConfirmarNit(true);
      return;
    }
    setConfirmarNit(false);
    setGuardando(true);
    setError("");
    try {
      const cuerpo = { ...datos };
      if (!cambiaNit && !esNuevo) delete cuerpo.nit;
      delete (cuerpo as Record<string, unknown>).ultimo_periodo;
      const cliente = esNuevo ? await api.crear(cuerpo) : await api.actualizar(id!, cuerpo);
      navegar(`/clientes/${cliente.id}`, { replace: true });
    } catch (e) {
      setError((e as Error).message);
      window.scrollTo({ top: 0, behavior: "smooth" });
    } finally {
      setGuardando(false);
    }
  };

  if (cargando) return <Cargando texto="Cargando la ficha" />;

  return (
    <div className="space-y-8">
      <div className="flex flex-wrap items-end justify-between gap-6">
        <div>
          <EnlaceSubrayado a={esNuevo ? "/clientes" : `/clientes/${id}`}>
            <ArrowLeft size={14} strokeWidth={1.5} aria-hidden /> {esNuevo ? "Clientes" : "Volver a la ficha"}
          </EnlaceSubrayado>
          <h1 className="t-display mt-5 text-tinta">{esNuevo ? "Nuevo cliente" : "Editar ficha"}</h1>
        </div>
      </div>

      {error && (
        <Aviso tono="rojo" titulo="No se pudo guardar" onCerrar={() => setError("")}>
          {error}
        </Aviso>
      )}

      {/* ── el camino normal: los documentos del cliente ───────────────── */}
      <ZonaDocumentos
        leyendo={leyendo}
        onArchivos={leerDocumentos}
        titulo={esNuevo ? "Llenar desde documentos" : "Actualizar con documentos nuevos"}
        texto={
          esNuevo
            ? "Suelte los estatutos, el RUT, el certificado de cámara o las cartas: la ficha se llena sola y usted revisa cada dato antes de guardar."
            : "Suelte un RUT o un certificado nuevo y le muestro qué campos cambiarían. No se guarda nada sin su visto bueno."
        }
      />

      {extraida && (
        <PanelFichaExtraida
          ficha={extraida}
          onUsar={(valores, socios) => {
            setDatos((d) => ({ ...d, ...valores, ...(socios.length ? { socios } : {}) }));
            setExtraida(null);
            setMasDatos(true);
          }}
          onDescartar={() => setExtraida(null)}
        />
      )}

      {comparacion && (
        <PanelCambios
          comparacion={comparacion}
          onAplicar={(valores, socios) => {
            setDatos((d) => ({ ...d, ...valores, ...(socios ? { socios } : {}) }));
            setComparacion(null);
          }}
          onDescartar={() => setComparacion(null)}
        />
      )}

      {/* ── lo mínimo: quién es ────────────────────────────────────────── */}
      <Tarjeta rotulo="Identificación" titulo={esNuevo ? "Lo único obligatorio" : "Quién es el cliente"}>
        <div className="grid gap-4 sm:grid-cols-[minmax(0,240px)_minmax(0,1fr)]">
          <Campo
            etiqueta="NIT o cédula"
            obligatorio
            ayuda={dv ? `Dígito de verificación: ${dv}` : "Solo los dígitos. El dígito de verificación se calcula solo."}
          >
            <input
              value={datos.nit ?? ""}
              onChange={(e) => set("nit", e.target.value)}
              inputMode="numeric"
              placeholder="900123456"
              className={clases(estiloCampo, "cifras")}
            />
          </Campo>
          <Campo etiqueta="Nombre o razón social" obligatorio>
            <input
              value={datos.razon_social ?? ""}
              onChange={(e) => set("razon_social", e.target.value)}
              placeholder="Nombre de la empresa o de la persona"
              className={estiloCampo}
            />
          </Campo>
        </div>
      </Tarjeta>

      <section>
        <button
          type="button"
          onClick={() => setMasDatos((v) => !v)}
          aria-expanded={masDatos}
          className="t-h2 flex items-center gap-2 text-tinta hover:text-azul-tinta"
        >
          <ChevronDown size={20} strokeWidth={1.5} aria-hidden className={clases("transition-transform", masDatos && "rotate-180")} />
          Más datos (opcional)
        </button>
        {masDatos && (
          <div className="mt-6 space-y-8">
            <MasDatos datos={datos} set={set} />
            <EditorSocios socios={datos.socios ?? []} onCambio={(s) => set("socios", s)} />
          </div>
        )}
      </section>

      <div className="flex flex-wrap justify-end gap-2 pb-4">
        <Link to={esNuevo ? "/clientes" : `/clientes/${id}`}>
          <Boton variante="fantasma">Cancelar</Boton>
        </Link>
        <Boton variante="solido" tamano="lg" cargando={guardando} disabled={!listo} onClick={() => guardar()}>
          {esNuevo ? "Crear cliente" : "Guardar ficha"}
        </Boton>
      </div>

      {confirmarNit && original && (
        <Dialogo
          rotulo="Cambio de NIT"
          titulo="¿Seguro que quiere cambiar el NIT?"
          onCerrar={() => setConfirmarNit(false)}
          pie={
            <>
              <Boton variante="fantasma" onClick={() => setConfirmarNit(false)}>Dejar el NIT como estaba</Boton>
              <Boton variante="peligro" cargando={guardando} onClick={() => guardar(true)}>Cambiar el NIT</Boton>
            </>
          }
        >
          <p className="t-body text-grafito">
            El NIT pasa de <span className="codigo text-tinta">{original.nit}</span> a{" "}
            <span className="codigo text-tinta">{String(datos.nit).replace(/\D/g, "")}-{dv}</span>. Es el dato con que se
            identifica al cliente ante la DIAN y el que llevan sus estados financieros. Si otro cliente ya usa ese NIT, no se
            guardará y se le dirá cuál es.
          </p>
        </Dialogo>
      )}
    </div>
  );
}

/* ── zona para soltar documentos (no abre la puerta única) ─────────────── */
function ZonaDocumentos({
  leyendo, onArchivos, titulo, texto,
}: {
  leyendo: boolean;
  onArchivos: (a: File[]) => void;
  titulo: string;
  texto: string;
}) {
  const entrada = useRef<HTMLInputElement>(null);
  const [encima, setEncima] = useState(false);
  // Se detiene la propagación: este recuadro tiene su propio destino y no debe
  // abrir la puerta única de toda la aplicación.
  const parar = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  };
  return (
    <div
      role="button"
      tabIndex={0}
      aria-label={`${titulo}: elegir documentos o soltarlos aquí`}
      onClick={() => entrada.current?.click()}
      onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && (e.preventDefault(), entrada.current?.click())}
      onDragEnter={(e) => (parar(e), setEncima(true))}
      onDragOver={parar}
      onDragLeave={(e) => (parar(e), setEncima(false))}
      onDrop={(e) => {
        parar(e);
        setEncima(false);
        onArchivos(Array.from(e.dataTransfer.files));
      }}
      className={clases(
        "material-hoja flex cursor-pointer flex-wrap items-center gap-5 rounded-hoja border-2 border-dashed px-6 py-5 transition-colors",
        encima ? "border-azul" : "border-tinta/20 hover:border-tinta/40",
      )}
    >
      <span className="grid h-12 w-12 shrink-0 place-items-center rounded-full bg-hoja-2">
        {leyendo ? (
          <span aria-hidden className="h-5 w-5 animate-spin rounded-full border-2 border-tinta border-t-transparent" />
        ) : (
          <Upload size={20} strokeWidth={1.5} aria-hidden className="text-grafito" />
        )}
      </span>
      <span className="min-w-0 flex-1">
        <span className="t-h2 block text-tinta">{leyendo ? "Leyendo los documentos…" : titulo}</span>
        <span className="t-small mt-1 block text-grafito">{texto}</span>
      </span>
      <span className="codigo text-[12px] text-gris">.docx · .pdf · .xlsx</span>
      <input
        ref={entrada}
        type="file"
        multiple
        accept=".docx,.pdf,.xlsx,.xls,.csv,.doc"
        className="hidden"
        onChange={(e) => {
          onArchivos(Array.from(e.target.files ?? []));
          e.target.value = "";
        }}
      />
    </div>
  );
}

function Confianza({ valor }: { valor: string }) {
  return valor === "seguro" ? <Insignia tono="tinta">seguro</Insignia> : <Insignia tono="ambar">por confirmar</Insignia>;
}

function mostrar(campo: string, valor: string): string {
  if (DINERO.has(campo) && /^-?\d+(\.\d+)?$/.test(valor)) return pesos(valor);
  if (campo === "responsable_iva") return valor === "true" ? "Sí" : "No";
  if (campo === "tipo_persona") return valor === "natural" ? "Natural" : "Jurídica";
  if (campo === "numero_acciones" && /^\d+(\.\d+)?$/.test(valor)) return Number(valor).toLocaleString("es-CO");
  return valor;
}

/* ── ficha extraída: cada dato con origen, confianza y conflictos ──────── */
function PanelFichaExtraida({
  ficha, onUsar, onDescartar,
}: {
  ficha: FichaExtraida;
  onUsar: (valores: Partial<Cliente>, socios: Socio[]) => void;
  onDescartar: () => void;
}) {
  const campos = Object.keys(ETIQUETAS).filter((c) => ficha.campos[c] && c !== "dv");
  const [usar, setUsar] = useState<Record<string, boolean>>(() => Object.fromEntries(campos.map((c) => [c, true])));
  const [elegido, setElegido] = useState<Record<string, string>>(
    () => Object.fromEntries(campos.map((c) => [c, ficha.campos[c].valor])),
  );
  const [conSocios, setConSocios] = useState(true);

  return (
    <Tarjeta
      rotulo={`${ficha.documentos.length} documento(s) · ${campos.length} datos`}
      titulo="Ficha extraída"
      subtitulo="Revise antes de guardar. Desmarque lo que no quiera usar; donde dos documentos no coinciden, elija."
      acciones={
        <>
          <Boton variante="fantasma" tamano="sm" onClick={onDescartar}>Descartar</Boton>
          <Boton
            variante="solido"
            tamano="sm"
            onClick={() =>
              onUsar(
                Object.fromEntries(campos.filter((c) => usar[c]).map((c) => [c, aBorrador(c, elegido[c])])) as Partial<Cliente>,
                conSocios ? ficha.socios : [],
              )
            }
          >
            Usar estos datos
          </Boton>
        </>
      }
    >
      <p className="t-small mb-4 text-grafito">
        Leídos: {ficha.documentos.map((d) => `${d.archivo} (${d.nombre_tipo.toLowerCase()})`).join(" · ")}
      </p>
      {campos.length === 0 && <p className="t-body text-grafito">Estos documentos no traen datos de la ficha.</p>}
      <ul className="divide-y divide-linea">
        {campos.map((c) => {
          const dato = ficha.campos[c];
          const otros = ficha.conflictos[c] ?? [];
          return (
            <li key={c} className="grid gap-2 py-3 sm:grid-cols-[24px_200px_minmax(0,1fr)] sm:items-start">
              <input
                type="checkbox"
                checked={usar[c]}
                onChange={(e) => setUsar({ ...usar, [c]: e.target.checked })}
                aria-label={`Usar ${ETIQUETAS[c]}`}
                className="mt-1 accent-azul"
              />
              <span className="t-small font-medium text-tinta">{ETIQUETAS[c]}</span>
              <span className="min-w-0">
                {otros.length > 1 ? (
                  <span className="block space-y-1.5">
                    <Insignia tono="rojo">Los documentos no coinciden: elija</Insignia>
                    {otros.map((o) => (
                      <label key={o.valor + o.origen} className="flex items-start gap-2">
                        <input
                          type="radio"
                          name={`conflicto-${c}`}
                          checked={elegido[c] === o.valor}
                          onChange={() => setElegido({ ...elegido, [c]: o.valor })}
                          className="mt-1 accent-azul"
                        />
                        <span className="t-body text-tinta">
                          {mostrar(c, o.valor)} <span className="t-meta text-gris">· {o.origen}</span>
                        </span>
                      </label>
                    ))}
                  </span>
                ) : (
                  <span className="block">
                    <span className="t-body break-words text-tinta">{mostrar(c, dato.valor)}</span>
                    <span className="t-meta mt-1 flex flex-wrap items-center gap-2 text-gris">
                      <Confianza valor={dato.confianza} /> {dato.origen}
                    </span>
                  </span>
                )}
              </span>
            </li>
          );
        })}
      </ul>
      {ficha.socios.length > 0 && (
        <div className="mt-5 border-t border-linea pt-4">
          <label className="flex items-center gap-2">
            <input type="checkbox" checked={conSocios} onChange={(e) => setConSocios(e.target.checked)} className="accent-azul" />
            <span className="t-body font-medium text-tinta">{ficha.socios.length} socio(s)</span>
            <span className="t-meta text-gris">· {ficha.socios_origen}</span>
          </label>
          <ul className="mt-2 space-y-1 pl-6">
            {ficha.socios.map((s) => (
              <li key={s.cedula + s.nombre} className="t-small text-grafito">
                {s.nombre} · <span className="codigo">{s.cedula}</span>
                {Number(s.acciones) ? ` · ${Number(s.acciones).toLocaleString("es-CO")} acciones` : ""}
              </li>
            ))}
          </ul>
        </div>
      )}
    </Tarjeta>
  );
}

/* ── documentos nuevos sobre una ficha existente: qué cambiaría ───────── */
function PanelCambios({
  comparacion, onAplicar, onDescartar,
}: {
  comparacion: ComparacionFicha;
  onAplicar: (valores: Partial<Cliente>, socios: Socio[] | null) => void;
  onDescartar: () => void;
}) {
  const [usar, setUsar] = useState<Record<string, boolean>>(
    () => Object.fromEntries(comparacion.cambios.map((c) => [c.campo, true])),
  );
  const [conSocios, setConSocios] = useState(!!comparacion.socios);
  const n = comparacion.cambios.length + (comparacion.socios ? 1 : 0);
  return (
    <Tarjeta
      rotulo={comparacion.documentos.map((d) => d.nombre_tipo).join(" · ")}
      titulo={n ? `${n} dato(s) cambiarían` : "Los documentos coinciden con la ficha"}
      subtitulo="Marque los que quiere aplicar. Se guardan al pulsar «Guardar ficha»."
      acciones={
        <>
          <Boton variante="fantasma" tamano="sm" onClick={onDescartar}>Descartar</Boton>
          {n > 0 && (
            <Boton
              variante="solido"
              tamano="sm"
              onClick={() =>
                onAplicar(
                  Object.fromEntries(
                    comparacion.cambios.filter((c) => usar[c.campo]).map((c) => [c.campo, aBorrador(c.campo, c.nuevo)]),
                  ) as Partial<Cliente>,
                  conSocios && comparacion.socios ? comparacion.socios.nuevo : null,
                )
              }
            >
              Aplicar a la ficha
            </Boton>
          )}
        </>
      }
    >
      <ul className="divide-y divide-linea">
        {comparacion.cambios.map((c) => (
          <li key={c.campo} className="grid gap-2 py-3 sm:grid-cols-[24px_200px_minmax(0,1fr)]">
            <input
              type="checkbox"
              checked={usar[c.campo]}
              onChange={(e) => setUsar({ ...usar, [c.campo]: e.target.checked })}
              aria-label={`Aplicar ${ETIQUETAS[c.campo] ?? c.campo}`}
              className="mt-1 accent-azul"
            />
            <span className="t-small font-medium text-tinta">{ETIQUETAS[c.campo] ?? c.campo}</span>
            <span className="min-w-0">
              <span className="t-body text-gris line-through">{c.actual ? mostrar(c.campo, c.actual) : "vacío"}</span>
              <span className="t-body mx-2 text-gris">→</span>
              <span className="t-body text-tinta">{mostrar(c.campo, c.nuevo)}</span>
              <span className="t-meta mt-1 flex flex-wrap items-center gap-2 text-gris">
                <Confianza valor={c.confianza} /> {c.origen}
              </span>
            </span>
          </li>
        ))}
        {comparacion.socios && (
          <li className="flex items-center gap-2 py-3">
            <input type="checkbox" checked={conSocios} onChange={(e) => setConSocios(e.target.checked)} className="accent-azul" />
            <span className="t-body text-tinta">
              Socios: {comparacion.socios.actual} registrados → {comparacion.socios.nuevo.length} en el documento
            </span>
            <span className="t-meta text-gris">· {comparacion.socios.origen}</span>
          </li>
        )}
      </ul>
    </Tarjeta>
  );
}

/* ── todos los demás campos ─────────────────────────────────────────────── */
function Texto({ campo, datos, set, className, mono }: {
  campo: keyof Cliente; datos: Borrador; set: (c: keyof Borrador, v: never) => void; className?: string; mono?: boolean;
}) {
  return (
    <Campo etiqueta={ETIQUETAS[campo] ?? String(campo)} className={className}>
      <input
        value={String(datos[campo] ?? "")}
        onChange={(e) => set(campo, e.target.value as never)}
        className={clases(estiloCampo, mono && "cifras")}
      />
    </Campo>
  );
}

function Grupo({ rotulo, titulo, children }: { rotulo: string; titulo: string; children: ReactNode }) {
  return (
    <Tarjeta rotulo={rotulo} titulo={titulo}>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">{children}</div>
    </Tarjeta>
  );
}

function MasDatos({ datos, set }: { datos: Borrador; set: <K extends keyof Borrador>(c: K, v: Borrador[K]) => void }) {
  const s = set as (c: keyof Borrador, v: never) => void;
  return (
    <>
      <Grupo rotulo="Sociedad" titulo="Constitución y capital">
        <Texto campo="sigla" datos={datos} set={s} />
        <Texto campo="tipo_sociedad" datos={datos} set={s} />
        <Campo etiqueta="Tipo de persona">
          <select value={datos.tipo_persona ?? "juridica"} onChange={(e) => set("tipo_persona", e.target.value as Cliente["tipo_persona"])}
            className={estiloCampo}>
            <option value="juridica">Jurídica</option>
            <option value="natural">Natural</option>
          </select>
        </Campo>
        <Campo etiqueta="Fecha de constitución">
          <input type="date" value={datos.fecha_constitucion ?? ""} onChange={(e) => set("fecha_constitucion", e.target.value || null)}
            className={estiloCampo} />
        </Campo>
        <Texto campo="documento_constitucion" datos={datos} set={s} className="lg:col-span-2" />
        <Texto campo="capital_autorizado" datos={datos} set={s} mono />
        <Texto campo="capital_suscrito" datos={datos} set={s} mono />
        <Texto campo="capital_pagado" datos={datos} set={s} mono />
        <Texto campo="numero_acciones" datos={datos} set={s} mono />
        <Texto campo="valor_nominal_accion" datos={datos} set={s} mono />
        <Texto campo="matricula_mercantil" datos={datos} set={s} mono />
        <Campo etiqueta="Renovación de la matrícula">
          <input type="date" value={datos.fecha_renovacion ?? ""} onChange={(e) => set("fecha_renovacion", e.target.value || null)}
            className={estiloCampo} />
        </Campo>
        <Campo etiqueta="Objeto social" className="sm:col-span-2 lg:col-span-3">
          <textarea value={datos.objeto_social ?? ""} onChange={(e) => set("objeto_social", e.target.value)} rows={3}
            className={estiloCampo} />
        </Campo>
      </Grupo>

      <Grupo rotulo="Tributario" titulo="Actividad y responsabilidades">
        <Texto campo="ciiu" datos={datos} set={s} mono />
        <Texto campo="ciiu_secundarios" datos={datos} set={s} mono />
        <Texto campo="responsabilidades" datos={datos} set={s} mono />
        <Campo etiqueta="Régimen tributario">
          <select value={datos.regimen ?? "responsable_iva"} onChange={(e) => set("regimen", e.target.value)} className={estiloCampo}>
            {REGIMENES.map(([v, t]) => <option key={v} value={v}>{t}</option>)}
          </select>
        </Campo>
        <Campo etiqueta="Responsable de IVA">
          <select value={datos.responsable_iva ? "si" : "no"} onChange={(e) => set("responsable_iva", e.target.value === "si")}
            className={estiloCampo}>
            <option value="si">Sí</option>
            <option value="no">No</option>
          </select>
        </Campo>
        <Campo etiqueta="Grupo NIIF" ayuda="1 plenas · 2 pymes · 3 microempresas">
          <select value={String(datos.grupo_niif ?? 3)} onChange={(e) => set("grupo_niif", Number(e.target.value))} className={estiloCampo}>
            <option value="1">Grupo 1 — NIIF plenas</option>
            <option value="2">Grupo 2 — NIIF para pymes</option>
            <option value="3">Grupo 3 — Microempresas</option>
          </select>
        </Campo>
        <Campo etiqueta="Tarifa de renta" ayuda="Como fracción: 0.35 equivale al 35 %">
          <input value={datos.tarifa_renta ?? "0.35"} onChange={(e) => set("tarifa_renta", e.target.value)} inputMode="decimal"
            className={clases(estiloCampo, "cifras")} />
        </Campo>
      </Grupo>

      <Grupo rotulo="Contacto" titulo="Dónde está y con quién se habla">
        <Texto campo="direccion" datos={datos} set={s} className="lg:col-span-2" />
        <Texto campo="municipio" datos={datos} set={s} />
        <Texto campo="departamento" datos={datos} set={s} />
        <Texto campo="telefono" datos={datos} set={s} mono />
        <Texto campo="email" datos={datos} set={s} />
      </Grupo>

      <Grupo rotulo="Personas" titulo="Representación, revisoría y contador">
        <Texto campo="rep_legal" datos={datos} set={s} />
        <Texto campo="rep_legal_cc" datos={datos} set={s} mono />
        <span className="hidden lg:block" />
        <Texto campo="rep_legal_suplente" datos={datos} set={s} />
        <Texto campo="rep_legal_suplente_cc" datos={datos} set={s} mono />
        <span className="hidden lg:block" />
        <Texto campo="revisor_fiscal" datos={datos} set={s} />
        <Texto campo="revisor_fiscal_tp" datos={datos} set={s} mono />
        <span className="hidden lg:block" />
        <Texto campo="contador" datos={datos} set={s} />
        <Texto campo="contador_cc" datos={datos} set={s} mono />
        <Texto campo="contador_tp" datos={datos} set={s} mono />
      </Grupo>

      <Grupo rotulo="Relación" titulo="Cómo se trabaja con este cliente">
        <Campo etiqueta="Honorarios mensuales" ayuda="Solo dígitos: 300000">
          <input value={datos.honorarios_mes ?? "0"} onChange={(e) => set("honorarios_mes", e.target.value)} inputMode="decimal"
            className={clases(estiloCampo, "cifras")} />
        </Campo>
        <Campo etiqueta="Periodicidad contable" ayuda="Define cuándo el sistema avisa que está atrasado">
          <select value={datos.periodicidad ?? "mensual"} onChange={(e) => set("periodicidad", e.target.value as Cliente["periodicidad"])}
            className={clases(estiloCampo, "capitalize")}>
            {PERIODICIDADES.map((p) => <option key={p} value={p}>{p}</option>)}
          </select>
        </Campo>
        <Campo etiqueta="Estado">
          <select value={datos.estado ?? "activo"} onChange={(e) => set("estado", e.target.value as Cliente["estado"])} className={estiloCampo}>
            <option value="activo">Activo</option>
            <option value="inactivo">Inactivo</option>
            <option value="archivado">Archivado</option>
          </select>
        </Campo>
        <Campo etiqueta="Etiquetas" ayuda="Separadas por coma" className="sm:col-span-2">
          <input value={(datos.etiquetas ?? []).join(", ")}
            onChange={(e) => set("etiquetas", e.target.value.split(",").map((t) => t.trim()).filter(Boolean))}
            className={estiloCampo} />
        </Campo>
        <Campo etiqueta="Notas" className="sm:col-span-2 lg:col-span-3">
          <textarea value={datos.notas ?? ""} onChange={(e) => set("notas", e.target.value)} rows={3} className={estiloCampo} />
        </Campo>
      </Grupo>
    </>
  );
}

function EditorSocios({ socios, onCambio }: { socios: Socio[]; onCambio: (s: Socio[]) => void }) {
  const nuevo = (): Socio => ({ nombre: "", cedula: "", cargo: "", acciones: "0", participacion: "0", comprometido: "0", pagado: "0" });
  const cambiar = (i: number, campo: keyof Socio, valor: string) =>
    onCambio(socios.map((s, j) => (i === j ? { ...s, [campo]: valor } : s)));

  return (
    <Tarjeta
      rotulo="Composición"
      titulo="Socios o accionistas"
      subtitulo="El sistema avisa cuando queda capital suscrito sin pagar."
      acciones={<Boton variante="contorno" tamano="sm" onClick={() => onCambio([...socios, nuevo()])}>+ Agregar socio</Boton>}
    >
      {socios.length === 0 ? (
        <p className="text-sm text-grafito">Sin socios registrados.</p>
      ) : (
        <div className="space-y-3">
          {socios.map((s, i) => (
            <div key={i} className="grid gap-3 rounded-control border border-linea p-3 sm:grid-cols-2 lg:grid-cols-6">
              <Campo etiqueta="Nombre" className="lg:col-span-2">
                <input value={s.nombre} onChange={(e) => cambiar(i, "nombre", e.target.value)} className={estiloCampo} />
              </Campo>
              <Campo etiqueta="Cédula">
                <input value={s.cedula} onChange={(e) => cambiar(i, "cedula", e.target.value)} className={clases(estiloCampo, "cifras")} />
              </Campo>
              <Campo etiqueta="Acciones">
                <input value={s.acciones} onChange={(e) => cambiar(i, "acciones", e.target.value)} inputMode="decimal"
                  className={clases(estiloCampo, "cifras")} />
              </Campo>
              <Campo etiqueta="Comprometido">
                <input value={s.comprometido} onChange={(e) => cambiar(i, "comprometido", e.target.value)} inputMode="decimal"
                  className={clases(estiloCampo, "cifras")} />
              </Campo>
              <Campo etiqueta="Pagado">
                <input value={s.pagado} onChange={(e) => cambiar(i, "pagado", e.target.value)} inputMode="decimal"
                  className={clases(estiloCampo, "cifras")} />
              </Campo>
              <div className="lg:col-span-6">
                <Boton variante="fantasma" tamano="sm" onClick={() => onCambio(socios.filter((_, j) => j !== i))}>
                  Quitar este socio
                </Boton>
              </div>
            </div>
          ))}
        </div>
      )}
    </Tarjeta>
  );
}

