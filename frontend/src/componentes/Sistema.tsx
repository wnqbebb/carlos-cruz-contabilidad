import { useCallback, useEffect, useState } from "react";
import { clientes as apiClientes, sistema } from "../api";
import type { EstadoSistema } from "../tipos";
import { useAvisos } from "../ui";
import { Aviso, Boton, Dialogo } from "./ui";

/**
 * Panel «Sistema» (v2.3 · Fase 2), en el menú de la cuenta. Solo lo que el
 * contador necesita: si está conectado, la versión y las acciones de su cuenta.
 * Nunca el proyecto, el motor de la base, rutas, variables ni comandos.
 */
export function DialogoSistema({ onCerrar }: { onCerrar: () => void }) {
  const [estado, setEstado] = useState<EstadoSistema | null>(null);
  useEffect(() => {
    sistema.estado().then(setEstado).catch(() => setEstado({ conectado: false, en_la_nube: false, version: __VERSION__ }));
  }, []);
  const conexion = !estado
    ? "Comprobando…"
    : !estado.conectado
      ? "Sin conexión"
      : estado.en_la_nube
        ? "En la nube · conectado"
        : "En este equipo · funcionando";
  return (
    <Dialogo rotulo="Cuenta" titulo="Sistema" onCerrar={onCerrar} ancho="max-w-lg">
      <div className="space-y-6">
        <dl className="grid grid-cols-[auto_1fr] gap-x-6 gap-y-3">
          <dt className="t-meta text-gris">Datos</dt>
          <dd className="t-body text-tinta">{conexion}</dd>
          <dt className="t-meta text-gris">Versión</dt>
          <dd className="t-body text-tinta">{estado?.version ?? __VERSION__}</dd>
        </dl>
        <ClientesDemostracion />
      </div>
    </Dialogo>
  );
}

/* ── clientes de demostración: se borran todos juntos, nunca un cliente real ── */
function ClientesDemostracion() {
  const [lista, setLista] = useState<{ id: string; razon_social: string }[] | null>(null);
  const [confirmar, setConfirmar] = useState(false);
  const [trabajando, setTrabajando] = useState(false);
  const [error, setError] = useState("");
  const avisar = useAvisos();
  const cargar = useCallback(() => {
    apiClientes.demostracion().then((r) => setLista(r.clientes)).catch((e) => setError((e as Error).message));
  }, []);
  useEffect(() => {
    cargar();
  }, [cargar]);

  const eliminar = async () => {
    setTrabajando(true);
    setError("");
    try {
      const r = await apiClientes.eliminarDemostracion();
      avisar(`Se eliminaron ${r.eliminados} cliente(s) de demostración.`);
      setConfirmar(false);
      cargar();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setTrabajando(false);
    }
  };

  return (
    <section aria-labelledby="titulo-demo" className="border-t border-linea pt-5">
      <h3 id="titulo-demo" className="t-body font-semibold text-tinta">Clientes de demostración</h3>
      <p className="t-small mt-1 text-grafito">
        {lista === null
          ? "Consultando…"
          : lista.length
            ? `Hay ${lista.length} con datos inventados para mostrar la aplicación.`
            : "No hay clientes de demostración cargados."}
      </p>
      {!!lista?.length && !confirmar && (
        <Boton variante="peligro" className="mt-3" onClick={() => setConfirmar(true)}>
          Eliminar clientes de demostración
        </Boton>
      )}
      {confirmar && lista && (
        <div className="mt-3 space-y-3">
          <Aviso tono="rojo" titulo="Esto no se puede deshacer">
            Se borran estos clientes con sus periodos, movimientos y su rastro en la bitácora. Ningún otro cliente se
            toca.
          </Aviso>
          <ul className="t-small list-disc space-y-1 pl-5 text-tinta">
            {lista.map((c) => (
              <li key={c.id}>{c.razon_social}</li>
            ))}
          </ul>
          <div className="flex flex-wrap justify-end gap-2">
            <Boton variante="fantasma" onClick={() => setConfirmar(false)}>
              Cancelar
            </Boton>
            <Boton variante="peligro" cargando={trabajando} onClick={eliminar}>
              Eliminar {lista.length} cliente(s)
            </Boton>
          </div>
        </div>
      )}
      {error && <p className="t-small mt-2 text-rojo">{error}</p>}
    </section>
  );
}
