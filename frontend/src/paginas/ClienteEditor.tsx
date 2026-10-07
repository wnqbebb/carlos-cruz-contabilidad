import { ArrowLeft } from "lucide-react";
import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { clientes as api } from "../api";
import { clases } from "../formato";
import type { Cliente, Socio } from "../tipos";
import { Aviso, Boton, Campo, Cargando, Rotulo, Tarjeta, estiloCampo } from "../componentes/ui";
import { EnlaceSubrayado } from "../ui";

type Borrador = Partial<Cliente> & { socios?: Socio[] };

const VACIO: Borrador = {
  nit: "",
  razon_social: "",
  sigla: "",
  tipo_persona: "juridica",
  regimen: "responsable_iva",
  grupo_niif: 3,
  responsable_iva: true,
  tarifa_renta: "0.35",
  ciiu: "",
  direccion: "",
  municipio: "",
  departamento: "",
  telefono: "",
  email: "",
  rep_legal: "",
  rep_legal_cc: "",
  rep_legal_suplente: "",
  contador: "",
  contador_cc: "",
  contador_tp: "",
  fecha_constitucion: null,
  capital_suscrito: "0",
  valor_nominal_accion: "0",
  honorarios_mes: "0",
  periodicidad: "mensual",
  estado: "activo",
  etiquetas: [],
  notas: "",
  socios: [],
};

const REGIMENES = [
  ["responsable_iva", "Responsable de IVA"],
  ["no_responsable_iva", "No responsable de IVA"],
  ["gran_contribuyente", "Gran contribuyente"],
  ["simple", "Régimen simple"],
  ["especial", "Régimen especial (ESAL)"],
];

const PERIODICIDADES = ["mensual", "bimestral", "trimestral", "cuatrimestral", "anual"];

export function ClienteEditor() {
  const { id } = useParams<{ id: string }>();
  const esNuevo = !id || id === "nuevo";
  const navegar = useNavigate();

  const [datos, setDatos] = useState<Borrador>(VACIO);
  const [cargando, setCargando] = useState(!esNuevo);
  const [guardando, setGuardando] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (esNuevo) return;
    api
      .obtener(id!)
      .then((c) => setDatos({ ...c, socios: c.socios ?? [] }))
      .catch((e) => setError((e as Error).message))
      .finally(() => setCargando(false));
  }, [id, esNuevo]);

  const set = <K extends keyof Borrador>(campo: K, valor: Borrador[K]) =>
    setDatos((d) => ({ ...d, [campo]: valor }));

  const guardar = async () => {
    setGuardando(true);
    setError("");
    try {
      const cliente = esNuevo ? await api.crear(datos) : await api.actualizar(id!, datos);
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
        <div className="flex gap-2">
          <Link to={esNuevo ? "/clientes" : `/clientes/${id}`}>
            <Boton variante="fantasma">Cancelar</Boton>
          </Link>
          <Boton variante="solido" cargando={guardando} onClick={guardar}>
            Guardar
          </Boton>
        </div>
      </div>

      {error && (
        <Aviso tono="rojo" titulo="No se pudo guardar" onCerrar={() => setError("")}>
          {error}
        </Aviso>
      )}

      {/* ── identificación ──────────────────────────────────────────── */}
      <Tarjeta rotulo="Identificación" titulo="Quién es el cliente">
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <Campo
            etiqueta="NIT o cédula"
            obligatorio
            ayuda="Solo los dígitos, sin puntos ni dígito de verificación. El sistema lo calcula."
          >
            <input
              value={datos.nit ?? ""}
              onChange={(e) => set("nit", e.target.value)}
              inputMode="numeric"
              placeholder="[NIT]"
              className={clases(estiloCampo, "cifras")}
            />
          </Campo>

          <Campo etiqueta="Razón social o nombre" obligatorio className="lg:col-span-2">
            <input
              value={datos.razon_social ?? ""}
              onChange={(e) => set("razon_social", e.target.value)}
              placeholder="FARMACIA NATURISTA ANTARES S.A.S."
              className={estiloCampo}
            />
          </Campo>

          <Campo etiqueta="Sigla">
            <input value={datos.sigla ?? ""} onChange={(e) => set("sigla", e.target.value)} className={estiloCampo} />
          </Campo>

          <Campo etiqueta="Tipo de persona">
            <select
              value={datos.tipo_persona ?? "juridica"}
              onChange={(e) => set("tipo_persona", e.target.value as Cliente["tipo_persona"])}
              className={estiloCampo}
            >
              <option value="juridica">Jurídica</option>
              <option value="natural">Natural</option>
            </select>
          </Campo>

          <Campo etiqueta="Régimen tributario">
            <select
              value={datos.regimen ?? "responsable_iva"}
              onChange={(e) => set("regimen", e.target.value)}
              className={estiloCampo}
            >
              {REGIMENES.map(([v, t]) => (
                <option key={v} value={v}>
                  {t}
                </option>
              ))}
            </select>
          </Campo>

          <Campo etiqueta="Actividad CIIU">
            <input
              value={datos.ciiu ?? ""}
              onChange={(e) => set("ciiu", e.target.value)}
              placeholder="4773"
              className={clases(estiloCampo, "cifras")}
            />
          </Campo>

          <Campo etiqueta="Fecha de constitución">
            <input
              type="date"
              value={datos.fecha_constitucion ?? ""}
              onChange={(e) => set("fecha_constitucion", e.target.value || null)}
              className={estiloCampo}
            />
          </Campo>

          <Campo etiqueta="Grupo NIIF" ayuda="1 plenas · 2 pymes · 3 microempresas">
            <select
              value={String(datos.grupo_niif ?? 3)}
              onChange={(e) => set("grupo_niif", Number(e.target.value))}
              className={estiloCampo}
            >
              <option value="1">Grupo 1 — NIIF plenas</option>
              <option value="2">Grupo 2 — NIIF para pymes</option>
              <option value="3">Grupo 3 — Microempresas</option>
            </select>
          </Campo>
        </div>
      </Tarjeta>

      {/* ── contacto ────────────────────────────────────────────────── */}
      <Tarjeta rotulo="Contacto" titulo="Dónde está y con quién se habla">
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <Campo etiqueta="Dirección" className="lg:col-span-2">
            <input value={datos.direccion ?? ""} onChange={(e) => set("direccion", e.target.value)} className={estiloCampo} />
          </Campo>
          <Campo etiqueta="Municipio">
            <input value={datos.municipio ?? ""} onChange={(e) => set("municipio", e.target.value)} className={estiloCampo} />
          </Campo>
          <Campo etiqueta="Departamento">
            <input value={datos.departamento ?? ""} onChange={(e) => set("departamento", e.target.value)} className={estiloCampo} />
          </Campo>
          <Campo etiqueta="Teléfono">
            <input value={datos.telefono ?? ""} onChange={(e) => set("telefono", e.target.value)} className={estiloCampo} />
          </Campo>
          <Campo etiqueta="Correo electrónico">
            <input type="email" value={datos.email ?? ""} onChange={(e) => set("email", e.target.value)} className={estiloCampo} />
          </Campo>
          <Campo etiqueta="Representante legal">
            <input value={datos.rep_legal ?? ""} onChange={(e) => set("rep_legal", e.target.value)} className={estiloCampo} />
          </Campo>
          <Campo etiqueta="Cédula del representante">
            <input
              value={datos.rep_legal_cc ?? ""}
              onChange={(e) => set("rep_legal_cc", e.target.value)}
              className={clases(estiloCampo, "cifras")}
            />
          </Campo>
          <Campo etiqueta="Representante suplente">
            <input
              value={datos.rep_legal_suplente ?? ""}
              onChange={(e) => set("rep_legal_suplente", e.target.value)}
              className={estiloCampo}
            />
          </Campo>
        </div>
      </Tarjeta>

      {/* ── relación comercial ──────────────────────────────────────── */}
      <Tarjeta rotulo="Relación" titulo="Cómo se trabaja con este cliente">
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <Campo etiqueta="Honorarios mensuales" ayuda="Solo dígitos: 300000">
            <input
              value={datos.honorarios_mes ?? "0"}
              onChange={(e) => set("honorarios_mes", e.target.value)}
              inputMode="decimal"
              className={clases(estiloCampo, "cifras")}
            />
          </Campo>
          <Campo etiqueta="Periodicidad contable" ayuda="Define cuándo el sistema avisa que está atrasado">
            <select
              value={datos.periodicidad ?? "mensual"}
              onChange={(e) => set("periodicidad", e.target.value as Cliente["periodicidad"])}
              className={clases(estiloCampo, "capitalize")}
            >
              {PERIODICIDADES.map((p) => (
                <option key={p} value={p} className="capitalize">
                  {p}
                </option>
              ))}
            </select>
          </Campo>
          <Campo etiqueta="Estado">
            <select
              value={datos.estado ?? "activo"}
              onChange={(e) => set("estado", e.target.value as Cliente["estado"])}
              className={estiloCampo}
            >
              <option value="activo">Activo</option>
              <option value="inactivo">Inactivo</option>
              <option value="archivado">Archivado</option>
            </select>
          </Campo>
          <Campo etiqueta="Capital suscrito">
            <input
              value={datos.capital_suscrito ?? "0"}
              onChange={(e) => set("capital_suscrito", e.target.value)}
              inputMode="decimal"
              className={clases(estiloCampo, "cifras")}
            />
          </Campo>
          <Campo etiqueta="Valor nominal por acción">
            <input
              value={datos.valor_nominal_accion ?? "0"}
              onChange={(e) => set("valor_nominal_accion", e.target.value)}
              inputMode="decimal"
              className={clases(estiloCampo, "cifras")}
            />
          </Campo>
          <Campo etiqueta="Tarifa de renta" ayuda="Como fracción: 0.35 equivale al 35%">
            <input
              value={datos.tarifa_renta ?? "0.35"}
              onChange={(e) => set("tarifa_renta", e.target.value)}
              inputMode="decimal"
              className={clases(estiloCampo, "cifras")}
            />
          </Campo>
          <Campo etiqueta="Etiquetas" ayuda="Separadas por coma" className="sm:col-span-2">
            <input
              value={(datos.etiquetas ?? []).join(", ")}
              onChange={(e) =>
                set(
                  "etiquetas",
                  e.target.value.split(",").map((t) => t.trim()).filter(Boolean),
                )
              }
              placeholder="Farmacia, Guacarí, Mensual"
              className={estiloCampo}
            />
          </Campo>
          <Campo etiqueta="Notas" className="sm:col-span-2 lg:col-span-3">
            <textarea
              value={datos.notas ?? ""}
              onChange={(e) => set("notas", e.target.value)}
              rows={3}
              className={estiloCampo}
            />
          </Campo>
        </div>
      </Tarjeta>

      {/* ── socios ──────────────────────────────────────────────────── */}
      <EditorSocios socios={datos.socios ?? []} onCambio={(s) => set("socios", s)} />

      <div className="flex justify-end gap-2 pb-4">
        <Link to={esNuevo ? "/clientes" : `/clientes/${id}`}>
          <Boton variante="fantasma">Cancelar</Boton>
        </Link>
        <Boton variante="solido" tamano="lg" cargando={guardando} onClick={guardar}>
          Guardar ficha
        </Boton>
      </div>
    </div>
  );
}

function EditorSocios({ socios, onCambio }: { socios: Socio[]; onCambio: (s: Socio[]) => void }) {
  const nuevo = (): Socio => ({
    nombre: "",
    cedula: "",
    cargo: "",
    acciones: "0",
    participacion: "0",
    comprometido: "0",
    pagado: "0",
  });

  const cambiar = (i: number, campo: keyof Socio, valor: string) =>
    onCambio(socios.map((s, j) => (i === j ? { ...s, [campo]: valor } : s)));

  return (
    <Tarjeta
      rotulo="Composición"
      titulo="Socios o accionistas"
      subtitulo="El sistema avisa cuando queda capital suscrito sin pagar."
      acciones={
        <Boton variante="contorno" tamano="sm" onClick={() => onCambio([...socios, nuevo()])}>
          + Agregar socio
        </Boton>
      }
    >
      {socios.length === 0 ? (
        <p className="text-sm text-grafito">Sin socios registrados.</p>
      ) : (
        <div className="space-y-3">
          {socios.map((s, i) => (
            <div key={i} className="grid gap-3 rounded-xl border border-linea p-3 sm:grid-cols-2 lg:grid-cols-5">
              <Campo etiqueta="Nombre" className="lg:col-span-2">
                <input value={s.nombre} onChange={(e) => cambiar(i, "nombre", e.target.value)} className={estiloCampo} />
              </Campo>
              <Campo etiqueta="Cédula">
                <input
                  value={s.cedula}
                  onChange={(e) => cambiar(i, "cedula", e.target.value)}
                  className={clases(estiloCampo, "cifras")}
                />
              </Campo>
              <Campo etiqueta="Comprometido">
                <input
                  value={s.comprometido}
                  onChange={(e) => cambiar(i, "comprometido", e.target.value)}
                  inputMode="decimal"
                  className={clases(estiloCampo, "cifras")}
                />
              </Campo>
              <Campo etiqueta="Pagado">
                <input
                  value={s.pagado}
                  onChange={(e) => cambiar(i, "pagado", e.target.value)}
                  inputMode="decimal"
                  className={clases(estiloCampo, "cifras")}
                />
              </Campo>
              <div className="lg:col-span-5">
                <Boton
                  variante="fantasma"
                  tamano="sm"
                  onClick={() => onCambio(socios.filter((_, j) => j !== i))}
                >
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
