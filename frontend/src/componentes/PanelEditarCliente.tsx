import { useEffect, useMemo, useState } from "react";
import { X, Save } from "lucide-react";
import { clientes as api } from "../api";
import { Aviso, Campo, estiloCampo } from "./ui";
import { BotonPrimario, BotonFantasma, useAvisos } from "../ui";
import { clases } from "../formato";
import { digitoVerificacion, EditorSocios, MasDatos, type Borrador } from "../paginas/ClienteEditor";
import type { Cliente } from "../tipos";

interface Props {
  abierto: boolean;
  onCerrar: () => void;
  cliente: Cliente;
  onGuardado: (actualizado: Cliente) => void;
}

/**
 * Panel lateral del expediente: la ficha COMPLETA y los socios, sin salir de la página.
 *
 * Usa los mismos bloques que la página «Editar ficha» (MasDatos y EditorSocios), así los dos
 * caminos guardan exactamente los mismos campos. Rescate H3: antes el panel mandaba socios con
 * campos que no existen (identificacion, porcentaje, aporte) y la cédula y el porcentaje se perdían.
 */
export function PanelEditarCliente({ abierto, onCerrar, cliente, onGuardado }: Props) {
  const avisar = useAvisos();
  const [datos, setDatos] = useState<Borrador>({});
  const [guardando, setGuardando] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (abierto) {
      setDatos({ ...cliente, socios: cliente.socios ? cliente.socios.map((s) => ({ ...s })) : [] });
      setError("");
    }
  }, [abierto, cliente]);

  const dv = useMemo(() => digitoVerificacion(String(datos.nit ?? "")), [datos.nit]);

  if (!abierto) return null;

  const set = <K extends keyof Borrador>(campo: K, valor: Borrador[K]) => setDatos((d) => ({ ...d, [campo]: valor }));

  const guardar = async (e: React.FormEvent) => {
    e.preventDefault();
    setGuardando(true);
    setError("");
    try {
      const cuerpo: Record<string, unknown> = { ...datos };
      for (const k of ["id", "dv", "creado", "actualizado", "ultimo_periodo", "archivos_de_muestra", "buscable"]) delete cuerpo[k];
      if (String(cliente.nit) === String(datos.nit ?? "").replace(/\D/g, "")) delete cuerpo.nit;
      const actualizado = await api.actualizar(cliente.id, cuerpo as Partial<Cliente>);
      onGuardado(actualizado);
      onCerrar();
      avisar("Ficha del cliente guardada.");
    } catch (ex) {
      setError((ex as Error).message || "No se pudo guardar la ficha.");
    } finally {
      setGuardando(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-black/40 backdrop-blur-sm transition-opacity">
      <div
        role="dialog"
        aria-modal="true"
        aria-label="Editar cliente"
        className="flex h-full w-full max-w-3xl flex-col overflow-hidden border-l border-linea bg-lienzo shadow-2xl"
      >
        <div className="flex items-center justify-between border-b border-linea bg-hoja px-6 py-4">
          <div>
            <h2 className="t-h2 text-tinta">Editar cliente</h2>
            <p className="t-small text-grafito">Todos los datos de la ficha y los socios, sin salir del expediente.</p>
          </div>
          <button
            type="button"
            onClick={onCerrar}
            className="rounded-full p-2 text-grafito transition-colors hover:bg-hoja-2 hover:text-tinta"
            aria-label="Cerrar panel"
          >
            <X size={20} />
          </button>
        </div>

        <form onSubmit={guardar} className="flex-1 space-y-6 overflow-y-auto p-6">
          {error && <Aviso tono="rojo" onCerrar={() => setError("")}>{error}</Aviso>}

          <section className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <Campo etiqueta="Razón social o nombre completo" className="sm:col-span-2">
              <input
                value={datos.razon_social ?? ""}
                onChange={(e) => set("razon_social", e.target.value)}
                required
                className={estiloCampo}
              />
            </Campo>
            <Campo etiqueta="NIT o cédula" ayuda={dv ? `Dígito de verificación: ${dv}` : undefined}>
              <input
                value={datos.nit ?? ""}
                onChange={(e) => set("nit", e.target.value)}
                required
                inputMode="numeric"
                className={clases(estiloCampo, "cifras")}
              />
            </Campo>
          </section>

          <MasDatos datos={datos} set={set} />
          <EditorSocios socios={datos.socios ?? []} onCambio={(s) => set("socios", s)} />

          <div className="sticky bottom-0 -mx-6 -mb-6 flex items-center justify-end gap-3 border-t border-linea bg-hoja px-6 py-4">
            <BotonFantasma type="button" onClick={onCerrar}>Cancelar</BotonFantasma>
            <BotonPrimario type="submit" cargando={guardando}>
              <Save size={16} /> Guardar cambios
            </BotonPrimario>
          </div>
        </form>
      </div>
    </div>
  );
}
