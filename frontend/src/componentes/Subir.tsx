import { FileSpreadsheet, FileText, Upload } from "lucide-react";
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { ErrorApi, puerta } from "../api";
import { clases } from "../formato";
import { BotonAcento, BotonFantasma, BotonPrimario } from "../ui";
import type {
  CampoDetectado,
  Confirmacion,
  Importacion,
  InformeImportacionClientes,
  Propuesta,
} from "../tipos";
import { ETAPAS_LECTURA, Procesando } from "./Procesando";
import { Aviso, Campo, Dialogo, estiloInput, Insignia } from "./ui";

/**
 * Una sola puerta (spec v2.2 · Fase 3).
 *
 * POR QUÉ EXISTE
 * Hasta la v2.1 había dos entradas —«Importar Excel» en Clientes y «Subir» en
 * Trabajar— y el contador tenía que acertar cuál. Si subía la contabilidad de
 * un cliente en la carga masiva veía «No se encontraron las columnas
 * obligatorias NIT y RAZÓN SOCIAL» y se quedaba ahí, sin saber que el archivo
 * estaba bien y la pantalla era la otra.
 *
 * Ahora cualquier zona de la aplicación acepta cualquier archivo: se manda a
 * `/api/subir`, el backend mira el CONTENIDO y responde qué es y de quién. Esta
 * pantalla solo muestra lo encontrado, de dónde salió, y pide lo que falte.
 *
 * El archivo nunca se vuelve a pedir: los bytes quedan en la sesión del
 * servidor hasta que se confirma.
 */

const EXTENSIONES = /\.(xlsx|xlsm|xls|csv|txt|pdf|docx|doc)$/i;
const ACEPTA = ".xlsx,.xlsm,.xls,.csv,.txt,.pdf,.docx,.doc";

type Abrir = (archivos: File[]) => void;

const ContextoPuerta = createContext<{ abrir: Abrir; elegir: () => void }>({
  abrir: () => {},
  elegir: () => {},
});

/** Desde cualquier pantalla: abrir la puerta con archivos ya elegidos. */
export function usePuerta() {
  return useContext(ContextoPuerta);
}

/** De qué cliente estamos hablando según la ruta, si es que hay uno. */
function clienteDeLaRuta(pathname: string, search: string): string {
  const enRuta = pathname.match(/^\/clientes\/([0-9a-f-]{8,})/i);
  if (enRuta) return enRuta[1];
  return new URLSearchParams(search).get("cliente") ?? "";
}

/* ── proveedor: input oculto, arrastre global y diálogo ─────────────────── */
export function Puerta({ children }: { children: ReactNode }) {
  const entrada = useRef<HTMLInputElement>(null);
  const [archivos, setArchivos] = useState<File[]>([]);
  const [arrastrando, setArrastrando] = useState(false);
  const ubicacion = useLocation();
  const clienteId = clienteDeLaRuta(ubicacion.pathname, ubicacion.search);

  const abrir = useCallback<Abrir>((lista) => {
    const validos = lista.filter((f) => EXTENSIONES.test(f.name));
    if (validos.length) setArchivos(validos);
  }, []);

  const elegir = useCallback(() => entrada.current?.click(), []);

  /* Soltar sobre CUALQUIER pantalla, no solo sobre la zona de arrastre.
     El contador no tiene por qué buscar el recuadro correcto. */
  useEffect(() => {
    let dentro = 0;
    const traeArchivos = (e: DragEvent) => !!e.dataTransfer?.types?.includes("Files");
    const entrar = (e: DragEvent) => {
      if (!traeArchivos(e)) return;
      dentro += 1;
      setArrastrando(true);
    };
    const salir = () => {
      dentro = Math.max(0, dentro - 1);
      if (!dentro) setArrastrando(false);
    };
    const encima = (e: DragEvent) => traeArchivos(e) && e.preventDefault();
    const soltar = (e: DragEvent) => {
      if (!traeArchivos(e)) return;
      e.preventDefault();
      dentro = 0;
      setArrastrando(false);
      abrir(Array.from(e.dataTransfer?.files ?? []));
    };
    window.addEventListener("dragenter", entrar);
    window.addEventListener("dragleave", salir);
    window.addEventListener("dragover", encima);
    window.addEventListener("drop", soltar);
    return () => {
      window.removeEventListener("dragenter", entrar);
      window.removeEventListener("dragleave", salir);
      window.removeEventListener("dragover", encima);
      window.removeEventListener("drop", soltar);
    };
  }, [abrir]);

  const valor = useMemo(() => ({ abrir, elegir }), [abrir, elegir]);

  return (
    <ContextoPuerta.Provider value={valor}>
      {children}

      <input
        ref={entrada}
        type="file"
        multiple
        accept={ACEPTA}
        className="hidden"
        onChange={(e) => {
          abrir(Array.from(e.target.files ?? []));
          e.target.value = "";
        }}
      />

      {arrastrando && !archivos.length && (
        <div
          aria-hidden
          className="no-imprimir pointer-events-none fixed inset-0 z-[70] flex items-center justify-center bg-[var(--velo)]"
        >
          <div className="material-cristal flex flex-col items-center rounded-hoja px-10 py-8 text-center shadow-expediente">
            <Upload size={32} strokeWidth={1.5} aria-hidden className="text-azul" />
            <p className="t-h2 mt-4 text-tinta">Suelte aquí</p>
            <p className="t-small mt-1 text-grafito">
              Excel, PDF o Word. Da igual de qué sea: yo miro qué trae.
            </p>
          </div>
        </div>
      )}

      {archivos.length > 0 && (
        <DialogoSubida
          archivos={archivos}
          clienteId={clienteId}
          onCerrar={() => setArchivos([])}
        />
      )}
    </ContextoPuerta.Provider>
  );
}

/** El botón principal de toda la aplicación. */
export function BotonSubirArchivo({
  children = "Subir archivo",
  variante = "primario",
  compacto,
  className,
}: {
  children?: ReactNode;
  variante?: "primario" | "acento" | "fantasma";
  compacto?: boolean;
  className?: string;
}) {
  const { elegir } = usePuerta();
  const Boton = variante === "acento" ? BotonAcento : variante === "fantasma" ? BotonFantasma : BotonPrimario;
  return (
    <Boton
      compacto={compacto}
      className={className}
      onClick={elegir}
      icono={<Upload size={compacto ? 16 : 18} strokeWidth={1.5} aria-hidden />}
    >
      {children}
    </Boton>
  );
}

/* ── el diálogo: leer, mostrar lo encontrado, confirmar ────────────────── */
type Fase = "leyendo" | "confirmar" | "guardando" | "importado";

function DialogoSubida({
  archivos,
  clienteId,
  onCerrar,
}: {
  archivos: File[];
  clienteId: string;
  onCerrar: () => void;
}) {
  const navegar = useNavigate();
  const [fase, setFase] = useState<Fase>("leyendo");
  const [propuesta, setPropuesta] = useState<Propuesta | null>(null);
  const [clase, setClase] = useState("");
  const [error, setError] = useState("");
  const [hecho, setHecho] = useState<Confirmacion | null>(null);
  // Lo que el contador puede corregir antes de seguir.
  const [nombre, setNombre] = useState("");
  const [nit, setNit] = useState("");

  useEffect(() => {
    let vivo = true;
    setFase("leyendo");
    setError("");
    puerta
      .subir(archivos, clienteId)
      .then((p) => {
        if (!vivo) return;
        setPropuesta(p);
        setClase(p.clase);
        setNombre(p.identidad.campos.razon_social?.valor ?? "");
        setNit(p.identidad.campos.nit?.valor ?? "");
        setFase("confirmar");
      })
      .catch((e) => {
        if (!vivo) return;
        setError((e as Error).message);
        setFase("confirmar");
      });
    return () => {
      vivo = false;
    };
  }, [archivos, clienteId]);

  const confirmar = async (forzar?: string) => {
    if (!propuesta) return;
    const elegida = forzar ?? clase;
    setFase("guardando");
    setError("");
    try {
      const r = await puerta.confirmar(propuesta.subida_id, {
        clase: elegida,
        ...(propuesta.cliente ? { cliente_id: propuesta.cliente.id } : {}),
        ...(elegida === "contabilidad" && !propuesta.cliente
          ? { crear: { nit, razon_social: nombre, dv: propuesta.identidad.campos.dv?.valor } }
          : {}),
      });
      if (r.clase === "directorio") {
        setHecho(r);
        setFase("importado");
        return;
      }
      // Contabilidad: se entra directo a revisar, con el archivo ya leído.
      const { clase: _, ...importacion } = r;
      onCerrar();
      navegar(`/trabajo?cliente=${r.cliente_id}`, { state: { importacion: importacion as Importacion } });
    } catch (e) {
      const err = e as ErrorApi;
      setError(err.message);
      setFase("confirmar");
    }
  };

  const titulo =
    fase === "leyendo"
      ? "Leyendo los archivos"
      : fase === "importado"
        ? "Clientes importados"
        : TITULO[clase] ?? "Esto fue lo que encontré";

  return (
    <Dialogo
      titulo={titulo}
      rotulo={archivos.map((a) => a.name).join(" · ")}
      onCerrar={onCerrar}
      ancho="max-w-3xl"
      pie={
        fase === "confirmar" && propuesta ? (
          <Acciones
            clase={clase}
            propuesta={propuesta}
            listo={clase !== "contabilidad" || !!(propuesta.cliente || (nombre.trim() && nit.trim()))}
            onElegirClase={setClase}
            onConfirmar={confirmar}
            onCerrar={onCerrar}
          />
        ) : fase === "importado" ? (
          <>
            <BotonFantasma compacto onClick={onCerrar}>Cerrar</BotonFantasma>
            <BotonPrimario
              compacto
              flecha
              onClick={() => {
                onCerrar();
                navegar("/clientes");
              }}
            >
              Ver los clientes
            </BotonPrimario>
          </>
        ) : undefined
      }
    >
      {(fase === "leyendo" || fase === "guardando") && (
        <Procesando
          titulo={fase === "leyendo" ? "Mirando qué trae cada hoja" : "Preparando el trabajo"}
          etapas={ETAPAS_LECTURA}
        />
      )}

      {error && fase === "confirmar" && (
        <Aviso tono="rojo" titulo="No se pudo leer" onCerrar={() => setError("")}>
          {error}
        </Aviso>
      )}

      {fase === "importado" && hecho?.clase === "directorio" && (
        <InformeDirectorio informe={hecho.informe} />
      )}

      {fase === "confirmar" && propuesta && (
        <div className="space-y-6">
          <Explicacion clase={clase} propuesta={propuesta} />

          {clase === "contabilidad" && (
            <QuienEs
              propuesta={propuesta}
              nombre={nombre}
              nit={nit}
              onNombre={setNombre}
              onNit={setNit}
            />
          )}

          {clase === "documentos" && <QuienEs propuesta={propuesta} nombre={nombre} nit={nit} soloLectura />}

          <QueTraeCadaHoja propuesta={propuesta} />
        </div>
      )}
    </Dialogo>
  );
}

const TITULO: Record<string, string> = {
  contabilidad: "Esto es la contabilidad de un cliente",
  directorio: "Esto es una lista de clientes",
  documentos: "Esto identifica a un cliente",
  ambiguo: "¿Qué quiere que haga con esto?",
  desconocido: "No reconocí lo que trae",
};

/* ── qué es y por qué ──────────────────────────────────────────────────── */
function Explicacion({ clase, propuesta }: { clase: string; propuesta: Propuesta }) {
  if (clase === "ambiguo") {
    return (
      <p className="t-body text-grafito">
        El archivo tiene una lista de clientes y también movimientos contables. Dígame cuál de las dos
        cosas quiere y sigo; el archivo no hay que volverlo a subir.
      </p>
    );
  }
  if (clase === "desconocido") {
    return (
      <div className="space-y-3">
        <p className="t-body text-grafito">
          Abrí los archivos, pero ninguna hoja tenía ni movimientos contables, ni una lista de clientes,
          ni datos de identificación. Abajo está lo que vi en cada una.
        </p>
        {propuesta.ilegibles.map((i) => (
          <Aviso key={i.archivo} tono="ambar" titulo={i.archivo}>
            {i.motivo}
          </Aviso>
        ))}
      </div>
    );
  }
  if (clase === "directorio") {
    const filas = propuesta.hojas.filter((h) => h.clase === "directorio").reduce((s, h) => s + h.filas, 0);
    return (
      <p className="t-body text-grafito">
        Encontré {filas.toLocaleString("es-CO")} clientes con NIT y razón social. Los que ya existan se
        actualizan; los nuevos entran al directorio.
      </p>
    );
  }
  if (clase === "documentos") {
    return (
      <p className="t-body text-grafito">
        Estos documentos no traen cifras, pero sí dicen de quién son. Con esto puedo abrir la ficha del
        cliente ya llena; las cifras las sube después.
      </p>
    );
  }
  return (
    <div className="space-y-3">
      <p className="t-body text-grafito">
        {propuesta.contenido.length
          ? `Encontré ${listar(propuesta.contenido)}`
          : "Encontré movimientos contables"}
        {propuesta.periodo ? ` de ${propuesta.periodo.texto}.` : "."}{" "}
        Confirme de quién es y sigo hasta el balance.
      </p>
      {propuesta.ilegibles.map((i) => (
        <Aviso key={i.archivo} tono="ambar" titulo={`${i.archivo}: no se pudo leer`}>
          {i.motivo}
        </Aviso>
      ))}
    </div>
  );
}

const listar = (xs: string[]) =>
  xs.length <= 1 ? xs.join("") : `${xs.slice(0, -1).join(", ")} y ${xs[xs.length - 1]}`;

/* ── de quién es: lo detectado, con su procedencia y editable ──────────── */
function QuienEs({
  propuesta,
  nombre,
  nit,
  onNombre,
  onNit,
  soloLectura,
}: {
  propuesta: Propuesta;
  nombre: string;
  nit: string;
  onNombre?: (v: string) => void;
  onNit?: (v: string) => void;
  soloLectura?: boolean;
}) {
  const campos = propuesta.identidad.campos;

  if (propuesta.cliente) {
    return (
      <section className="material-hoja rounded-control px-5 py-4">
        <p className="t-meta text-gris">Cliente</p>
        <p className="t-h2 mt-1 text-tinta">{propuesta.cliente.razon_social}</p>
        <p className="codigo mt-1 text-[13px] text-gris">NIT {propuesta.cliente.nit_formateado}</p>
        {campos.nit && (
          <p className="t-small mt-3 text-grafito">
            Lo reconocí por el NIT que venía en {campos.nit.origen}.
          </p>
        )}
      </section>
    );
  }

  return (
    <section className="space-y-4">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h3 className="t-h2 text-tinta">¿De quién es?</h3>
        <p className="t-meta text-gris">Cliente nuevo</p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <DatoDetectado
          etiqueta="Nombre o razón social"
          valor={nombre}
          campo={campos.razon_social}
          onCambio={onNombre}
          soloLectura={soloLectura}
        />
        <DatoDetectado
          etiqueta="NIT o cédula"
          valor={nit}
          campo={campos.nit ?? campos.cedula}
          onCambio={onNit}
          soloLectura={soloLectura}
          mono
        />
      </div>

      {propuesta.coincidencias.length > 0 && (
        <Aviso tono="ambar" titulo="Puede que ya exista">
          <p>
            {propuesta.coincidencias.length === 1
              ? "Hay un cliente con un nombre casi igual:"
              : "Hay clientes con nombres casi iguales:"}
          </p>
          <ul className="mt-1.5 space-y-1">
            {propuesta.coincidencias.map((c) => (
              <li key={c.id}>
                <span className="font-semibold">{c.titulo}</span>{" "}
                <span className="codigo text-[12px]">{c.subtitulo}</span>
              </li>
            ))}
          </ul>
          <p className="mt-1.5">
            Si es el mismo, escriba su NIT aquí arriba y el trabajo entra en su expediente.
          </p>
        </Aviso>
      )}
    </section>
  );
}

/** Un dato con su procedencia: el contador tiene que poder desconfiar. */
function DatoDetectado({
  etiqueta,
  valor,
  campo,
  onCambio,
  soloLectura,
  mono,
}: {
  etiqueta: string;
  valor: string;
  campo?: CampoDetectado;
  onCambio?: (v: string) => void;
  soloLectura?: boolean;
  mono?: boolean;
}) {
  return (
    <div>
      <Campo etiqueta={etiqueta} obligatorio={!soloLectura}>
        <input
          value={valor}
          disabled={soloLectura}
          onChange={(e) => onCambio?.(e.target.value)}
          className={clases(estiloInput, mono && "codigo")}
        />
      </Campo>
      <p className="t-meta mt-1.5 flex flex-wrap items-center gap-x-2 gap-y-1 text-gris">
        {campo ? (
          <>
            <Insignia tono={campo.confianza === "seguro" ? "verde" : campo.confianza === "probable" ? "azul" : "gris"}>
              {campo.confianza}
            </Insignia>
            <span>Salió de {campo.origen}</span>
          </>
        ) : (
          <span>No venía en los archivos. Escríbalo y seguimos.</span>
        )}
      </p>
    </div>
  );
}

/* ── qué trae cada hoja ────────────────────────────────────────────────── */
function QueTraeCadaHoja({ propuesta }: { propuesta: Propuesta }) {
  if (!propuesta.hojas.length) return null;
  return (
    <section>
      <h3 className="t-meta text-gris">Lo que trae cada hoja</h3>
      <ul className="material-hoja mt-3 rounded-control">
        {propuesta.hojas.map((h, i) => (
          <li
            key={`${h.archivo}-${h.hoja}-${i}`}
            className="flex flex-wrap items-center gap-x-3 gap-y-1 border-b border-linea px-4 py-3 last:border-b-0"
          >
            {h.clase === "texto" ? (
              <FileText size={16} strokeWidth={1.5} aria-hidden className="shrink-0 text-gris" />
            ) : (
              <FileSpreadsheet size={16} strokeWidth={1.5} aria-hidden className="shrink-0 text-gris" />
            )}
            <span className="t-small min-w-0 truncate text-tinta">{h.hoja}</span>
            <span className="t-small min-w-0 flex-1 truncate text-grafito">
              {h.razon === propuesta.hojas[i - 1]?.razon ? "" : h.razon || "Sin nada reconocible"}
            </span>
            {h.filas > 0 && (
              <span className="codigo shrink-0 text-[12px] text-gris">
                {h.filas.toLocaleString("es-CO")} filas
              </span>
            )}
          </li>
        ))}
      </ul>
    </section>
  );
}

/* ── botones del pie, según lo que se encontró ─────────────────────────── */
function Acciones({
  clase,
  propuesta,
  listo,
  onElegirClase,
  onConfirmar,
  onCerrar,
}: {
  clase: string;
  propuesta: Propuesta;
  listo: boolean;
  onElegirClase: (c: string) => void;
  onConfirmar: (forzar?: string) => void;
  onCerrar: () => void;
}) {
  const navegar = useNavigate();

  if (clase === "ambiguo") {
    return (
      <>
        <BotonFantasma compacto onClick={() => onElegirClase("directorio")}>
          Son clientes para el directorio
        </BotonFantasma>
        <BotonPrimario compacto onClick={() => onElegirClase("contabilidad")}>
          Es la contabilidad de un cliente
        </BotonPrimario>
      </>
    );
  }

  if (clase === "desconocido") {
    return <BotonFantasma compacto onClick={onCerrar}>Entendido</BotonFantasma>;
  }

  if (clase === "documentos") {
    const campos = propuesta.identidad.campos;
    return (
      <>
        <BotonFantasma compacto onClick={onCerrar}>Cerrar</BotonFantasma>
        <BotonPrimario
          compacto
          flecha
          onClick={() => {
            onCerrar();
            if (propuesta.cliente) {
              navegar(`/clientes/${propuesta.cliente.id}`);
              return;
            }
            // La ficha completa que traen los documentos: el editor la muestra
            // con el origen y la confianza de cada dato antes de guardar.
            navegar("/clientes/nuevo", {
              state: {
                extraida: propuesta.ficha,
                ficha: {
                  razon_social: campos.razon_social?.valor ?? "",
                  nit: (campos.nit ?? campos.cedula)?.valor ?? "",
                },
              },
            });
          }}
        >
          {propuesta.cliente ? "Abrir su expediente" : "Crear la ficha con estos datos"}
        </BotonPrimario>
      </>
    );
  }

  return (
    <>
      <BotonFantasma compacto onClick={onCerrar}>Cancelar</BotonFantasma>
      <BotonPrimario compacto flecha disabled={!listo} onClick={() => onConfirmar()}>
        {clase === "directorio"
          ? "Importar al directorio"
          : propuesta.cliente
            ? "Calcular"
            : "Crear cliente y calcular"}
      </BotonPrimario>
    </>
  );
}

/* ── resultado de la carga masiva ──────────────────────────────────────── */
function InformeDirectorio({ informe }: { informe: InformeImportacionClientes }) {
  return (
    <div className="space-y-5">
      <p className="t-body text-grafito">{informe.mensaje}</p>
      <dl className="grid grid-cols-3 gap-3">
        {[
          ["Nuevos", informe.insertados],
          ["Actualizados", informe.actualizados],
          ["Rechazados", informe.rechazados],
        ].map(([t, n]) => (
          <div key={String(t)} className="material-hoja rounded-control px-4 py-3">
            <dt className="t-meta text-gris">{t}</dt>
            <dd className="codigo mt-1 text-[22px] text-tinta">{Number(n).toLocaleString("es-CO")}</dd>
          </div>
        ))}
      </dl>
      {informe.rechazos?.length > 0 && (
        <section>
          <h3 className="t-meta text-gris">Filas que no entraron</h3>
          <ul className="material-hoja mt-3 rounded-control">
            {informe.rechazos.slice(0, 8).map((r) => (
              <li key={r.fila} className="flex flex-wrap gap-x-3 border-b border-linea px-4 py-2.5 last:border-b-0">
                <span className="codigo text-[12px] text-gris">Fila {r.fila}</span>
                <span className="t-small text-tinta">{r.razon_social || "(sin nombre)"}</span>
                <span className="t-small text-grafito">{r.motivo}</span>
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}

/* ── zona de arrastre visible, para las pantallas que la quieran ───────── */
export function ZonaSubida({ className }: { className?: string }) {
  const { abrir, elegir } = usePuerta();
  const [encima, setEncima] = useState(false);

  return (
    <div
      role="button"
      tabIndex={0}
      aria-label="Elegir archivos o soltarlos aquí"
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          elegir();
        }
      }}
      onDragOver={(e) => {
        e.preventDefault();
        setEncima(true);
      }}
      onDragLeave={() => setEncima(false)}
      onDrop={(e) => {
        e.preventDefault();
        e.stopPropagation();
        setEncima(false);
        abrir(Array.from(e.dataTransfer.files));
      }}
      onClick={elegir}
      className={clases(
        "material-hundido flex min-h-[280px] cursor-pointer flex-col items-center justify-center rounded-hoja border-2 border-dashed px-6 text-center transition-[border-color,box-shadow] duration-200 select-none",
        encima ? "brillo-cuadra border-azul" : "border-tinta/20 hover:border-tinta/40",
        className,
      )}
    >
      <Upload size={28} strokeWidth={1.5} aria-hidden className={encima ? "text-azul" : "text-grafito"} />
      <p className="t-h2 mt-5 text-tinta">{encima ? "Suelte para leer" : "Suelte aquí los archivos"}</p>
      <p className="t-body mt-1 text-gris">
        Excel, PDF o Word · varios a la vez · yo decido qué es cada uno
      </p>
      <div className="mt-6 flex flex-wrap justify-center gap-2">
        {[".xlsx", ".xls", ".csv", ".pdf", ".docx"].map((f) => (
          <span key={f} className="codigo rounded-chip border border-linea bg-hoja px-2.5 py-1 text-[12px] text-grafito">
            {f}
          </span>
        ))}
      </div>
    </div>
  );
}
