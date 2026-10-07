import { Plus, X } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { sistema } from "../api";
import { Campo, estiloCampo, estiloCampoAuto } from "../componentes/ui";
import { clases, fecha, fechaLarga, numero, pesos, sumar } from "../formato";
import type { Salud } from "../tipos";
import {
  BotonFantasma,
  BotonPrimario,
  Cifra,
  EsqueletoPagina,
  EstadoError,
  EtiquetaSeccion,
  InsigniaEstado,
  Interruptor,
  TituloPagina,
  useAvisos,
} from "../ui";

/**
 * Parámetros legales de nómina por año (spec 6.6).
 *
 * El sistema NO inventa estos valores: el SMMLV y el auxilio de transporte los
 * fija un decreto cada año y los registra el contador. Las tasas de aportes y
 * prestaciones se copian del año anterior al crear un año nuevo.
 *
 * El contrato con el backend no cambió: se envían `smmlv` y `aux_transporte`
 * como dígitos y `jornada_tramos` como lista de {desde, horas_semana}, igual
 * que cuando el tramo se escribía a mano como «AAAA-MM-DD=horas; …».
 */

type Tramo = { desde: string; horas: string };

const soloDigitos = (t: string) => t.replace(/\D/g, "");

export function Parametros() {
  const avisar = useAvisos();
  const [datos, setDatos] = useState<Record<string, any> | null>(null);
  const [errorCarga, setErrorCarga] = useState("");
  const [anio, setAnio] = useState(String(new Date().getFullYear()));
  const [nuevoAnio, setNuevoAnio] = useState<string | null>(null);
  const [smmlv, setSmmlv] = useState("");
  const [aux, setAux] = useState("");
  const [tramos, setTramos] = useState<Tramo[]>([]);
  const [error, setError] = useState("");
  const [guardando, setGuardando] = useState(false);

  const cargar = useCallback(() => {
    setErrorCarga("");
    return sistema
      .parametros()
      .then((d) => {
        setDatos(d);
        const anios = Object.keys(d).filter((k) => /^\d{4}$/.test(k)).sort();
        setAnio((a) => (anios.includes(a) ? a : anios[anios.length - 1] ?? a));
      })
      .catch((e) => setErrorCarga((e as Error).message));
  }, []);

  useEffect(() => {
    cargar();
  }, [cargar]);

  const editando = nuevoAnio ?? anio;

  useEffect(() => {
    const p = datos?.[editando];
    setSmmlv(p ? soloDigitos(String(p.smmlv)) : "");
    setAux(p ? soloDigitos(String(p.aux_transporte)) : "");
    setTramos(p ? p.jornada_tramos.map((t: any) => ({ desde: t.desde, horas: String(t.horas_semana) })) : []);
    setError("");
  }, [editando, datos]);

  const guardar = async () => {
    setError("");
    if (!/^\d{4}$/.test(editando)) return setError("El año debe tener cuatro dígitos.");
    if (!smmlv || !aux) return setError("Faltan el SMMLV o el auxilio de transporte.");
    const malos = tramos.filter((t) => !/^\d{4}-\d{2}-\d{2}$/.test(t.desde) || !Number(t.horas));
    if (malos.length) return setError("Cada tramo de jornada necesita una fecha y un número de horas.");
    setGuardando(true);
    try {
      await sistema.guardarParametros(Number(editando), {
        smmlv,
        aux_transporte: aux,
        ...(tramos.length
          ? { jornada_tramos: tramos.map((t) => ({ desde: t.desde, horas_semana: Number(t.horas) })) }
          : {}),
      });
      avisar(`Parámetros de ${editando} guardados.`);
      setAnio(editando);
      setNuevoAnio(null);
      await cargar();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setGuardando(false);
    }
  };

  if (errorCarga) {
    return <EstadoError titulo="No se pudieron leer los parámetros" detalle={errorCarga} onReintentar={cargar} />;
  }
  if (!datos) return <EsqueletoPagina texto="Leyendo parámetros" bloques={2} />;

  const anios = Object.keys(datos).filter((k) => /^\d{4}$/.test(k)).sort();
  const existe = Boolean(datos[editando]);
  const p = datos[anio];

  return (
    <div className="space-y-14">
      <TituloPagina subtitulo="Base con la que se liquida la nómina de todos los clientes. El SMMLV y el auxilio de transporte los fija un decreto cada año; aquí se registran.">
        Parámetros
      </TituloPagina>

      {/* ── valores vigentes por año ──────────────────────────────────── */}
      <section aria-labelledby="titulo-vigentes" className="space-y-6">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <EtiquetaSeccion indice={1}>Valores vigentes</EtiquetaSeccion>
            <h2 id="titulo-vigentes" className="t-h1 mt-4 text-tinta">Año {anio}</h2>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            {anios.length > 0 && (
              <Interruptor
                etiqueta="Año de los parámetros"
                valor={anio}
                onCambio={(a) => {
                  setAnio(a);
                  setNuevoAnio(null);
                }}
                opciones={anios.map((a) => ({ valor: a, texto: a }))}
              />
            )}
            <BotonFantasma
              compacto
              icono={<Plus size={16} strokeWidth={1.5} aria-hidden />}
              onClick={() => setNuevoAnio(String(Number(anios[anios.length - 1] ?? new Date().getFullYear()) + 1))}
            >
              Cargar otro año
            </BotonFantasma>
          </div>
        </div>

        {p ? (
          <div className="material-hoja grid gap-px overflow-hidden bg-linea sm:grid-cols-2 escritorio:grid-cols-4">
            <Valor titulo="SMMLV"><Cifra valor={p.smmlv} tamano="kpi" encajar /></Valor>
            <Valor titulo="Auxilio de transporte"><Cifra valor={p.aux_transporte} tamano="kpi" encajar /></Valor>
            <Valor titulo="SMMLV + auxilio"><Cifra valor={sumar(p.smmlv, p.aux_transporte)} tamano="kpi" encajar /></Valor>
            <Valor titulo="Jornada máxima">
              <ul className="space-y-1">
                {p.jornada_tramos.map((t: any) => (
                  <li key={t.desde} className="t-body text-tinta">
                    <span className="font-semibold tabular-nums">{t.horas_semana} h</span>
                    <span className="text-grafito"> desde {fechaLarga(t.desde)}</span>
                  </li>
                ))}
              </ul>
            </Valor>
          </div>
        ) : (
          <p className="t-body text-grafito">Todavía no hay años cargados.</p>
        )}
        {p?._fuente && <p className="t-small max-w-3xl text-gris">Fuente: {p._fuente}</p>}
      </section>

      {/* ── formulario ────────────────────────────────────────────────── */}
      <section aria-labelledby="titulo-editar" className="material-hoja p-6 sm:p-8">
        <EtiquetaSeccion indice={2}>{existe ? "Editar" : "Crear"}</EtiquetaSeccion>
        <h2 id="titulo-editar" className="t-h2 mt-4 text-tinta">
          {existe ? `Modificar el año ${editando}` : `Cargar el año ${editando}`}
        </h2>
        {!existe && (
          <p className="t-small mt-1 text-gris">
            Las tasas de aportes y prestaciones se copian del año anterior más cercano.
          </p>
        )}

        <div className="mt-8 grid gap-6 sm:grid-cols-3">
          <Campo etiqueta="Año" obligatorio>
            <input
              value={editando}
              inputMode="numeric"
              maxLength={4}
              readOnly={nuevoAnio === null}
              onChange={(e) => setNuevoAnio(soloDigitos(e.target.value).slice(0, 4))}
              className={clases(estiloCampo, "cifras", nuevoAnio === null && "text-grafito")}
            />
          </Campo>
          <Campo etiqueta="SMMLV" obligatorio ayuda="Se agrupa en miles mientras escribe">
            <input
              value={numero(smmlv || "")}
              onChange={(e) => setSmmlv(soloDigitos(e.target.value))}
              placeholder="1.750.905"
              inputMode="numeric"
              className={clases(estiloCampo, "cifras text-right")}
            />
          </Campo>
          <Campo etiqueta="Auxilio de transporte" obligatorio ayuda="Se agrupa en miles mientras escribe">
            <input
              value={numero(aux || "")}
              onChange={(e) => setAux(soloDigitos(e.target.value))}
              placeholder="249.095"
              inputMode="numeric"
              className={clases(estiloCampo, "cifras text-right")}
            />
          </Campo>
        </div>

        <p className="t-body mt-4 rounded-control bg-hoja-2 px-4 py-3 text-grafito" aria-live="polite">
          SMMLV + auxilio ={" "}
          <span className="cifras font-semibold text-tinta">{smmlv && aux ? pesos(sumar(smmlv, aux)) : "—"}</span>
        </p>

        {/* Jornada por tramos: filas en vez del texto crudo «2026-01-01=44; …» */}
        <fieldset className="mt-8">
          <legend className="t-meta text-gris">Jornada máxima por tramos (Ley 2101 de 2021)</legend>
          <ul className="mt-3 space-y-3">
            {tramos.map((t, i) => (
              <li key={i} className="flex flex-wrap items-center gap-3">
                <label className="flex items-center gap-2">
                  <span className="t-small text-grafito">Desde</span>
                  <input
                    type="date"
                    value={t.desde}
                    onChange={(e) => setTramos(tramos.map((x, j) => (j === i ? { ...x, desde: e.target.value } : x)))}
                    className={estiloCampoAuto}
                    aria-label={`Fecha del tramo ${i + 1}`}
                  />
                </label>
                <label className="flex items-center gap-2">
                  <input
                    value={t.horas}
                    inputMode="numeric"
                    maxLength={2}
                    onChange={(e) => setTramos(tramos.map((x, j) => (j === i ? { ...x, horas: soloDigitos(e.target.value) } : x)))}
                    className={clases(estiloCampoAuto, "cifras w-20 text-right")}
                    aria-label={`Horas por semana del tramo ${i + 1}`}
                  />
                  <span className="t-small text-grafito">horas por semana</span>
                </label>
                <button
                  type="button"
                  onClick={() => setTramos(tramos.filter((_, j) => j !== i))}
                  aria-label={`Quitar el tramo ${i + 1}`}
                  className="grid h-9 w-9 place-items-center rounded-full text-gris transition-colors hover:bg-hoja-2 hover:text-rojo"
                >
                  <X size={16} strokeWidth={1.5} aria-hidden />
                </button>
              </li>
            ))}
          </ul>
          <div className="mt-4">
            <BotonFantasma
              compacto
              icono={<Plus size={16} strokeWidth={1.5} aria-hidden />}
              onClick={() => setTramos([...tramos, { desde: `${editando}-01-01`, horas: "" }])}
            >
              Agregar tramo
            </BotonFantasma>
          </div>
        </fieldset>

        {error && (
          <p role="alert" className="t-body mt-6 rounded-control border border-rojo/30 bg-rojo-suave px-4 py-3 text-rojo">
            {error}
          </p>
        )}

        <div className="mt-8 flex flex-wrap justify-end gap-3 border-t border-linea pt-6">
          {nuevoAnio !== null && (
            <BotonFantasma onClick={() => setNuevoAnio(null)}>Cancelar</BotonFantasma>
          )}
          <BotonPrimario cargando={guardando} onClick={guardar}>
            Guardar {editando}
          </BotonPrimario>
        </div>
      </section>

      <Sistema />
    </div>
  );
}

function Valor({ titulo, children }: { titulo: string; children: React.ReactNode }) {
  return (
    <div className="@container min-w-0 bg-hoja p-6">
      <p className="t-meta text-gris">{titulo}</p>
      <div className="mt-3 text-tinta">{children}</div>
    </div>
  );
}

/* ── Sistema: el único lugar con el estado técnico de la base (spec 6.1) ── */
function Sistema() {
  const [salud, setSalud] = useState<Salud | null>(null);
  const [error, setError] = useState("");
  const comprobar = useCallback(() => {
    setError("");
    sistema.salud().then(setSalud).catch((e) => setError((e as Error).message));
  }, []);
  useEffect(() => {
    comprobar();
  }, [comprobar]);

  const a = salud?.almacenamiento;
  const filas: [string, React.ReactNode][] = a
    ? [
        ["Almacenamiento", a.es_postgres ? "Supabase (PostgreSQL en la nube)" : "Este equipo (SQLite)"],
        ["Estado", a.conectado ? <InsigniaEstado estado="cuadra" discreta>Conectado</InsigniaEstado> : <InsigniaEstado estado="descuadre">Sin conexión</InsigniaEstado>],
        ["Motor", <span className="codigo text-[13px]">{a.motor || "—"}</span>],
        ["Proyecto de Supabase", <span className="codigo text-[13px]">{a.proyecto || "—"}</span>],
        ["Sesiones de trabajo abiertas", <span className="tabular-nums">{salud!.sesiones_abiertas}</span>],
        ["Versión", <span className="codigo text-[13px]">v{__VERSION__} · build {__BUILD__} · {__FECHA_BUILD__}</span>],
      ]
    : [];

  return (
    <section aria-labelledby="titulo-sistema" className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <EtiquetaSeccion indice={3}>Sistema</EtiquetaSeccion>
          <h2 id="titulo-sistema" className="t-h1 mt-4 text-tinta">Dónde viven los datos</h2>
          <p className="t-small mt-1 text-gris">Información técnica para soporte. El cliente no necesita verla.</p>
        </div>
        <BotonFantasma compacto onClick={comprobar}>Comprobar de nuevo</BotonFantasma>
      </div>
      {error && <EstadoError titulo="No se pudo consultar el estado" detalle={error} onReintentar={comprobar} />}
      {a && (
        <dl className="material-hoja divide-y divide-linea">
          {filas.map(([k, v]) => (
            <div key={k} className="grid gap-1 px-6 py-4 sm:grid-cols-[260px_1fr] sm:items-center">
              <dt className="t-meta text-gris">{k}</dt>
              <dd className="t-body min-w-0 break-all text-tinta">{v}</dd>
            </div>
          ))}
          {a.error && (
            <div className="px-6 py-4">
              <dt className="t-meta text-gris">Último error de conexión</dt>
              <dd className="codigo mt-2 whitespace-pre-wrap text-[12px] text-rojo">{a.error}</dd>
            </div>
          )}
          <div className="px-6 py-4">
            <dt className="t-meta text-gris">Comprobado</dt>
            <dd className="t-small mt-1 text-grafito">{fecha(new Date().toISOString())} · {new Date().toLocaleTimeString("es-CO")}</dd>
          </div>
        </dl>
      )}
    </section>
  );
}
