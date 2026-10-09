import { FileUp, Search } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { renta } from "../api";
import { Cabecera } from "../componentes/Marco";
import { Procesando } from "../componentes/Procesando";
import { Aviso, Cargando, Insignia, Vacio, estiloCampoAuto } from "../componentes/ui";
import { clases, documentoEnLista, esNegativo, fecha, pesos } from "../formato";
import type { FilaCarteraRenta } from "../tipos";
import { TituloPagina } from "../ui";

/**
 * Renta⁰³ (v2.3 · Fase 5 / v2.4): la declaración de renta de cada persona natural de la cartera.
 * Incluye la puerta de entrada universal: «Suelte la exógena de cualquier persona».
 */

const ESTADOS: Record<string, { texto: string; tono: "neutro" | "ambar" | "azul" | "verde" }> = {
  sin_informacion: { texto: "Sin información", tono: "neutro" },
  incompleto: { texto: "Borrador incompleto", tono: "ambar" },
  borrador: { texto: "Borrador", tono: "ambar" },
  revisada: { texto: "Revisada", tono: "azul" },
  presentada: { texto: "Presentada", tono: "verde" },
};

type Orden = "vencimiento" | "nombre" | "estado" | "neto" | "ahorro";

export function Renta() {
  const navegar = useNavigate();
  const [anio, setAnio] = useState<number | null>(null);
  const [anios, setAnios] = useState<number[]>([]);
  const [filas, setFilas] = useState<FilaCarteraRenta[] | null>(null);
  const [error, setError] = useState("");
  const [q, setQ] = useState("");
  const [estado, setEstado] = useState("");
  const [orden, setOrden] = useState<Orden>("vencimiento");
  const [subiendo, setSubiendo] = useState(false);
  const [encima, setEncima] = useState(false);
  const entradaUniversal = useRef<HTMLInputElement>(null);

  useEffect(() => {
    renta.anios().then((r) => { setAnios(r.anios); setAnio(r.actual); }).catch((e) => setError((e as Error).message));
  }, []);
  useEffect(() => {
    if (anio === null) return;
    setFilas(null);
    renta.cartera(anio).then((r) => setFilas(r.declaraciones)).catch((e) => setError((e as Error).message));
  }, [anio]);

  const subirArchivos = async (archivos: File[]) => {
    if (!archivos.length) return;
    setSubiendo(true);
    setError("");
    try {
      const res = await renta.subirUniversal(archivos, anio ?? 2025);
      navegar(`/clientes/${res.cliente_id}?seccion=renta`);
    } catch (e) {
      setError((e as Error).message || "No se pudo procesar la exógena.");
      setSubiendo(false);
    }
  };

  const visibles = useMemo(() => {
    const t = q.trim().toLowerCase();
    const lista = (filas ?? []).filter((f) => (!estado || f.estado === estado) &&
      (!t || f.razon_social.toLowerCase().includes(t) || f.nit.includes(t)));
    const num = (v: string | null) => (v ? Number(v) : 0);
    const cmp: Record<Orden, (a: FilaCarteraRenta, b: FilaCarteraRenta) => number> = {
      vencimiento: (a, b) => (a.dias ?? 9999) - (b.dias ?? 9999),
      nombre: (a, b) => a.razon_social.localeCompare(b.razon_social),
      estado: (a, b) => Object.keys(ESTADOS).indexOf(a.estado) - Object.keys(ESTADOS).indexOf(b.estado),
      neto: (a, b) => num(b.neto) - num(a.neto),
      ahorro: (a, b) => num(b.ahorro) - num(a.ahorro),
    };
    return [...lista].sort(cmp[orden]);
  }, [filas, q, estado, orden]);

  const vencidas = (filas ?? []).filter((f) => f.dias !== null && f.dias < 0 && f.estado !== "presentada").length;

  return (
    <div className="space-y-10">
      <Cabecera>
        <TituloPagina subtitulo="Personas naturales de la cartera: quién debe declarar, cuándo vence y en qué va cada una.">
          Renta {anio ?? ""}
        </TituloPagina>
      </Cabecera>

      {error && <Aviso tono="rojo" onCerrar={() => setError("")}>{error}</Aviso>}
      {vencidas > 0 && (
        <Aviso tono="rojo" titulo={`${vencidas} ${vencidas === 1 ? "declaración vencida" : "declaraciones vencidas"} sin presentar`}>
          Cada mes de retardo suma sanción (art. 641 E.T.).
        </Aviso>
      )}

      {/* Zona universal de subida para cualquier contribuyente */}
      {subiendo ? (
        <div className="material-hoja mx-auto max-w-xl p-8">
          <Procesando
            titulo="Leyendo exógena y preparando la declaración"
            etapas={[
              "Enderezando fotos o analizando PDF",
              "Identificando al contribuyente",
              "Verificando topes del reporte",
              "Abriendo la declaración de renta",
            ]}
          />
        </div>
      ) : (
        <section
          role="button"
          tabIndex={0}
          aria-label="Suelte la exógena de cualquier persona para crearla o abrir su renta"
          onClick={() => entradaUniversal.current?.click()}
          onKeyDown={(e) => {
            if (e.key === "Enter" || e.key === " ") {
              e.preventDefault();
              entradaUniversal.current?.click();
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
            subirArchivos(Array.from(e.dataTransfer.files));
          }}
          className={clases(
            "material-hundido flex min-h-[170px] cursor-pointer flex-col items-center justify-center rounded-hoja border-2 border-dashed px-6 text-center transition-[border-color] duration-200 select-none",
            encima ? "border-azul bg-azul/5" : "border-tinta/20 hover:border-tinta/40 bg-hoja/50",
          )}
        >
          <FileUp size={28} strokeWidth={1.5} aria-hidden className="text-grafito" />
          <p className="t-h2 mt-3 text-tinta">
            {encima ? "Suelte la exógena aquí" : "Suelte la exógena de cualquier persona"}
          </p>
          <p className="t-body mt-1 text-gris">
            Fotos, PDF o Excel del portal de la DIAN · Si no está en clientes, se crea como contribuyente en el acto
          </p>
          <input
            ref={entradaUniversal}
            type="file"
            multiple
            accept="image/*,.pdf,.xlsx,.xls,.csv"
            className="hidden"
            aria-label="Archivos de exógena"
            onChange={(e) => {
              subirArchivos(Array.from(e.target.files ?? []));
              e.target.value = "";
            }}
          />
        </section>
      )}

      <div className="flex flex-wrap items-center gap-3">
        <label className="flex h-11 min-w-0 flex-1 items-center gap-2 rounded-full border border-borde-campo bg-campo px-4 sm:max-w-sm">
          <Search size={18} strokeWidth={1.5} aria-hidden className="shrink-0 text-gris" />
          <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Nombre o documento" aria-label="Buscar contribuyente"
            className="min-w-0 flex-1 bg-transparent text-tinta placeholder:text-gris focus:outline-none" />
        </label>
        <select aria-label="Estado" className={estiloCampoAuto} value={estado} onChange={(e) => setEstado(e.target.value)}>
          <option value="">Todos los estados</option>
          {Object.entries(ESTADOS).map(([k, v]) => <option key={k} value={k}>{v.texto}</option>)}
        </select>
        {anios.length > 1 && (
          <select aria-label="Año gravable" className={estiloCampoAuto} value={anio ?? ""} onChange={(e) => setAnio(Number(e.target.value))}>
            {anios.map((a) => <option key={a} value={a}>Año gravable {a}</option>)}
          </select>
        )}
      </div>

      {!filas && !error && !subiendo && <Cargando texto="Leyendo la cartera de renta" />}
      {filas && filas.length === 0 && !subiendo && (
        <Vacio titulo="No hay personas naturales en la cartera">
          Suelte arriba la exógena de cualquier persona para registrarla y preparar su formulario 210 de inmediato.
        </Vacio>
      )}
      {filas && filas.length > 0 && (
        <div className="barra-fina overflow-x-auto rounded-hoja border border-linea bg-hoja">
          <table className="t-tabla min-w-full text-[14px]">
            <thead className="bg-hoja-2 text-left text-gris">
              <tr>
                <Encabezado texto="Contribuyente" orden="nombre" actual={orden} onOrden={setOrden} />
                <th className="px-4 py-2.5 t-meta">¿Debe declarar?</th>
                <Encabezado texto="Vence" orden="vencimiento" actual={orden} onOrden={setOrden} />
                <Encabezado texto="Estado" orden="estado" actual={orden} onOrden={setOrden} />
                <Encabezado texto="Paga o le devuelven" orden="neto" actual={orden} onOrden={setOrden} derecha />
                <Encabezado texto="Ahorro frente a la DIAN" orden="ahorro" actual={orden} onOrden={setOrden} derecha />
              </tr>
            </thead>
            <tbody className="divide-y divide-linea">
              {visibles.map((f) => {
                const e = ESTADOS[f.estado];
                const vencida = f.dias !== null && f.dias < 0 && f.estado !== "presentada";
                return (
                  <tr key={f.cliente_id} className="transition-colors hover:bg-hoja-2">
                    <td className="px-4 py-3">
                      <Link to={`/clientes/${f.cliente_id}?seccion=renta`} className="font-medium text-tinta underline-offset-4 hover:underline">
                        {f.razon_social}
                      </Link>
                      <span className="codigo block text-[12px] text-gris">{documentoEnLista(f.nit, "natural")}</span>
                    </td>
                    <td className="max-w-xs px-4 py-3 text-grafito">
                      {f.obligado === null ? "Sin información" : f.obligado ? "Sí" : "No"}
                      {f.obligado && f.motivos.length > 0 && (
                        <span className="t-small block text-gris">Por {f.motivos.join(", ")}</span>
                      )}
                    </td>
                    <td className={clases("px-4 py-3", vencida ? "text-rojo" : "text-grafito")}>
                      {f.vencimiento ? fecha(f.vencimiento) : "—"}
                      {f.dias !== null && f.estado !== "presentada" && (
                        <span className="t-meta block">{f.dias < 0 ? `vencida hace ${-f.dias} d` : f.dias === 0 ? "vence hoy" : `faltan ${f.dias} d`}</span>
                      )}
                    </td>
                    <td className="px-4 py-3"><Insignia tono={e.tono}>{e.texto}</Insignia></td>
                    <td className="cifras px-4 py-3 text-right">
                      {f.neto === null ? "—" : esNegativo(f.neto) ? `Le devuelven ${pesos(f.neto.replace("-", ""))}` : pesos(f.neto)}
                    </td>
                    <td className="cifras px-4 py-3 text-right">{f.ahorro === null ? "—" : pesos(f.ahorro)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function Encabezado({ texto, orden, actual, onOrden, derecha }: {
  texto: string; orden: Orden; actual: Orden; onOrden: (o: Orden) => void; derecha?: boolean;
}) {
  return (
    <th className={clases("px-4 py-2.5", derecha && "text-right")} aria-sort={actual === orden ? "ascending" : "none"}>
      <button type="button" onClick={() => onOrden(orden)} className={clases("t-meta", actual === orden ? "text-tinta" : "text-gris hover:text-tinta")}>
        {texto}{actual === orden ? " ↓" : ""}
      </button>
    </th>
  );
}
