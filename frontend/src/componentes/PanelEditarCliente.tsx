import { useEffect, useState } from "react";
import { X, Save, Undo2, Plus, Trash2 } from "lucide-react";
import { clientes as api } from "../api";
import { Aviso, Boton, Campo, estiloCampo, estiloCampoAuto } from "./ui";
import { BotonPrimario, BotonFantasma, useAvisos } from "../ui";
import type { Cliente, Socio } from "../tipos";

interface Props {
  abierto: boolean;
  onCerrar: () => void;
  cliente: Cliente;
  onGuardado: (actualizado: Cliente) => void;
}

export function PanelEditarCliente({ abierto, onCerrar, cliente, onGuardado }: Props) {
  const avisar = useAvisos();
  const [datos, setDatos] = useState<Partial<Cliente>>({});
  const [socios, setSocios] = useState<Socio[]>([]);
  const [guardando, setGuardando] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (abierto) {
      setDatos({
        razon_social: cliente.razon_social || "",
        sigla: cliente.sigla || "",
        nit: cliente.nit || "",
        dv: cliente.dv || "",
        tipo_persona: cliente.tipo_persona || "juridica",
        regimen: cliente.regimen || "responsable_iva",
        municipio: cliente.municipio || "",
        departamento: cliente.departamento || "",
        direccion: cliente.direccion || "",
        telefono: cliente.telefono || "",
        email: cliente.email || "",
        honorarios_mes: cliente.honorarios_mes || "0",
        periodicidad: cliente.periodicidad || "mensual",
        responsable_iva: cliente.responsable_iva ?? true,
        notas: cliente.notas || "",
      });
      setSocios(cliente.socios ? [...cliente.socios] : []);
      setError("");
    }
  }, [abierto, cliente]);

  if (!abierto) return null;

  const setCampo = (campo: keyof Cliente, valor: any) => {
    setDatos((prev) => ({ ...prev, [campo]: valor }));
  };

  const guardar = async (e: React.FormEvent) => {
    e.preventDefault();
    setGuardando(true);
    setError("");
    try {
      const previo = { ...cliente };
      const cuerpo = { ...datos, socios };
      const actualizado = await api.actualizar(cliente.id, cuerpo);
      onGuardado(actualizado);
      onCerrar();
      avisar("Ficha del cliente actualizada exitosamente.");
    } catch (ex) {
      setError((ex as Error).message || "No se pudo actualizar la ficha.");
    } finally {
      setGuardando(false);
    }
  };

  const agregarSocio = () => {
    setSocios([
      ...socios,
      {
        id: Date.now(),
        nombre: "",
        identificacion: "",
        tipo_identificacion: "CC",
        porcentaje: "0",
        acciones: 0,
        aporte: "0",
        es_rep_legal: false,
      },
    ]);
  };

  const actualizarSocio = (index: number, campo: keyof Socio, valor: any) => {
    const copia = [...socios];
    copia[index] = { ...copia[index], [campo]: valor };
    setSocios(copia);
  };

  const eliminarSocio = (index: number) => {
    setSocios(socios.filter((_, i) => i !== index));
  };

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-black/40 backdrop-blur-sm transition-opacity">
      <div className="flex h-full w-full max-w-2xl flex-col bg-lienzo shadow-2xl overflow-hidden border-l border-linea animate-in slide-in-from-right duration-200">
        {/* Cabecera del panel */}
        <div className="flex items-center justify-between border-b border-linea px-6 py-4 bg-hoja">
          <div>
            <h2 className="t-h2 text-tinta">Editar cliente</h2>
            <p className="t-small text-grafito">Modifique los datos de la ficha sin salir del expediente</p>
          </div>
          <button
            type="button"
            onClick={onCerrar}
            className="rounded-full p-2 text-grafito hover:bg-hoja-2 hover:text-tinta transition-colors"
            aria-label="Cerrar panel"
          >
            <X size={20} />
          </button>
        </div>

        {/* Contenido scrolleable */}
        <form onSubmit={guardar} className="flex-1 overflow-y-auto p-6 space-y-6">
          {error && <Aviso tono="rojo" onCerrar={() => setError("")}>{error}</Aviso>}

          {/* 1. Identificación */}
          <section className="space-y-4">
            <h3 className="t-meta text-gris uppercase tracking-wider">Identificación</h3>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <div className="sm:col-span-2">
                <Campo etiqueta="Razón social o nombre completo">
                  <input
                    value={datos.razon_social || ""}
                    onChange={(e) => setCampo("razon_social", e.target.value)}
                    required
                    className={estiloCampo}
                  />
                </Campo>
              </div>
              <Campo etiqueta="Sigla o nombre corto">
                <input
                  value={datos.sigla || ""}
                  onChange={(e) => setCampo("sigla", e.target.value)}
                  className={estiloCampo}
                />
              </Campo>
              <Campo etiqueta="NIT o Cédula">
                <input
                  value={datos.nit || ""}
                  onChange={(e) => setCampo("nit", e.target.value)}
                  required
                  className={estiloCampo}
                />
              </Campo>
              <Campo etiqueta="Tipo de persona">
                <select
                  value={datos.tipo_persona || "juridica"}
                  onChange={(e) => setCampo("tipo_persona", e.target.value)}
                  className={estiloCampoAuto}
                >
                  <option value="juridica">Persona jurídica</option>
                  <option value="natural">Persona natural</option>
                </select>
              </Campo>
              <Campo etiqueta="Régimen tributario">
                <select
                  value={datos.regimen || "responsable_iva"}
                  onChange={(e) => setCampo("regimen", e.target.value)}
                  className={estiloCampoAuto}
                >
                  <option value="responsable_iva">Responsable de IVA</option>
                  <option value="no_responsable_iva">No responsable de IVA</option>
                  <option value="gran_contribuyente">Gran contribuyente</option>
                  <option value="simple">Régimen Simple</option>
                  <option value="especial">Régimen Especial (ESAL)</option>
                </select>
              </Campo>
            </div>
          </section>

          {/* 2. Ubicación y Contacto */}
          <section className="space-y-4 pt-4 border-t border-linea">
            <h3 className="t-meta text-gris uppercase tracking-wider">Ubicación y Contacto</h3>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <Campo etiqueta="Municipio">
                <input
                  value={datos.municipio || ""}
                  onChange={(e) => setCampo("municipio", e.target.value)}
                  className={estiloCampo}
                />
              </Campo>
              <Campo etiqueta="Departamento">
                <input
                  value={datos.departamento || ""}
                  onChange={(e) => setCampo("departamento", e.target.value)}
                  className={estiloCampo}
                />
              </Campo>
              <div className="sm:col-span-2">
                <Campo etiqueta="Dirección">
                  <input
                    value={datos.direccion || ""}
                    onChange={(e) => setCampo("direccion", e.target.value)}
                    className={estiloCampo}
                  />
                </Campo>
              </div>
              <Campo etiqueta="Teléfono">
                <input
                  value={datos.telefono || ""}
                  onChange={(e) => setCampo("telefono", e.target.value)}
                  className={estiloCampo}
                />
              </Campo>
              <Campo etiqueta="Correo electrónico">
                <input
                  type="email"
                  value={datos.email || ""}
                  onChange={(e) => setCampo("email", e.target.value)}
                  className={estiloCampo}
                />
              </Campo>
            </div>
          </section>

          {/* 3. Honorarios */}
          <section className="space-y-4 pt-4 border-t border-linea">
            <h3 className="t-meta text-gris uppercase tracking-wider">Honorarios contables</h3>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <Campo etiqueta="Honorarios acordados">
                <input
                  type="number"
                  value={datos.honorarios_mes || "0"}
                  onChange={(e) => setCampo("honorarios_mes", e.target.value)}
                  className={estiloCampo}
                />
              </Campo>
              <Campo etiqueta="Periodicidad">
                <select
                  value={datos.periodicidad || "mensual"}
                  onChange={(e) => setCampo("periodicidad", e.target.value)}
                  className={estiloCampoAuto}
                >
                  <option value="mensual">Mensual</option>
                  <option value="bimestral">Bimestral</option>
                  <option value="trimestral">Trimestral</option>
                  <option value="cuatrimestral">Cuatrimestral</option>
                  <option value="anual">Anual</option>
                </select>
              </Campo>
            </div>
          </section>

          {/* 4. Socios */}
          <section className="space-y-4 pt-4 border-t border-linea">
            <div className="flex items-center justify-between">
              <h3 className="t-meta text-gris uppercase tracking-wider">Socios o accionistas</h3>
              <button
                type="button"
                onClick={agregarSocio}
                className="inline-flex items-center gap-1 text-xs font-semibold text-azul hover:underline"
              >
                <Plus size={14} /> Agregar socio
              </button>
            </div>
            {socios.length === 0 ? (
              <p className="t-small text-gris italic">No hay socios registrados en esta ficha.</p>
            ) : (
              <div className="space-y-3">
                {socios.map((socio, idx) => (
                  <div key={socio.id || idx} className="rounded-hoja border border-linea bg-hoja p-3 space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="t-small font-medium text-tinta">Socio #{idx + 1}</span>
                      <button
                        type="button"
                        onClick={() => eliminarSocio(idx)}
                        className="text-rojo hover:opacity-75"
                        title="Quitar socio"
                      >
                        <Trash2 size={15} />
                      </button>
                    </div>
                    <div className="grid grid-cols-2 gap-2">
                      <input
                        placeholder="Nombre completo"
                        value={socio.nombre}
                        onChange={(e) => actualizarSocio(idx, "nombre", e.target.value)}
                        className={estiloCampo}
                      />
                      <input
                        placeholder="Identificación / Cédula"
                        value={socio.identificacion}
                        onChange={(e) => actualizarSocio(idx, "identificacion", e.target.value)}
                        className={estiloCampo}
                      />
                      <input
                        placeholder="Porcentaje (%)"
                        value={socio.porcentaje}
                        onChange={(e) => actualizarSocio(idx, "porcentaje", e.target.value)}
                        className={estiloCampo}
                      />
                      <input
                        placeholder="Aporte ($)"
                        value={socio.aporte}
                        onChange={(e) => actualizarSocio(idx, "aporte", e.target.value)}
                        className={estiloCampo}
                      />
                    </div>
                  </div>
                ))}
              </div>
            )}
          </section>

          {/* 5. Notas */}
          <section className="space-y-4 pt-4 border-t border-linea">
            <h3 className="t-meta text-gris uppercase tracking-wider">Notas del contador</h3>
            <Campo etiqueta="Anotaciones privadas">
              <textarea
                rows={3}
                value={datos.notas || ""}
                onChange={(e) => setCampo("notas", e.target.value)}
                placeholder="Observaciones sobre la empresa, acuerdos especiales, etc."
                className={estiloCampo}
              />
            </Campo>
          </section>

          {/* Barra de botones inferior */}
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
