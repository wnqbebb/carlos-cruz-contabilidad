import { Check, Download } from "lucide-react";
import { useEffect, useState } from "react";
import { descargas, trabajo as api } from "../api";
import { Aviso, Insignia } from "../componentes/ui";
import { ZonaSubida } from "../componentes/Subir";
import { BotonFantasma, BotonPrimario, EnlaceSubrayado, EtiquetaSeccion } from "../ui";
import type { CasoEjemplo, Importacion } from "../tipos";

const FORMATOS = [
  "Plantilla oficial de Carlos Cruz (.xlsx)",
  "Mayor en cuentas T horizontales",
  "Hoja de trabajo (saldo inicial + movimientos)",
  "Libro de aportes y socios",
  "Nómina (liquidación, aportes y retenciones)",
  "Estados financieros anteriores (auditoría automática)",
  "Balances en PDF generados por un programa contable",
];

/** Paso 1 del trabajo contable: subir los archivos del cliente. */
export function Inicio({
  clienteId,
  onImportado,
}: {
  clienteId: string;
  onImportado: (d: Importacion) => void;
}) {
  const [cargando, setCargando] = useState<string | null>(null);
  const [error, setError] = useState("");
  const [casos, setCasos] = useState<CasoEjemplo[]>([]);

  useEffect(() => {
    api.casos().then(setCasos).catch(() => setCasos([]));
  }, []);

  const ejecutar = async (clave: string, fn: () => Promise<Importacion>) => {
    setError("");
    setCargando(clave);
    try {
      onImportado(await fn());
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setCargando(null);
    }
  };

  return (
    <div className="grid gap-10 escritorio:grid-cols-12">
      <div className="space-y-10 escritorio:col-span-8">
        <section aria-labelledby="titulo-subir" className="space-y-5">
          <div>
            <EtiquetaSeccion indice={2}>Subir</EtiquetaSeccion>
            <h2 id="titulo-subir" className="t-h1 mt-4 text-tinta">Cargue los archivos del cliente</h2>
            <p className="t-body mt-2 max-w-2xl text-grafito">
              Cada hoja se reconoce sola: el sistema detecta el formato, lleva las cuentas al PUC y las deja
              listas para revisar antes de calcular.
            </p>
          </div>

          {/* Una sola puerta: la misma zona de `componentes/Subir.tsx` que hay en
              el resto de la aplicación. Acepta cualquier archivo y el backend
              decide qué es; por eso aquí ya no se filtra ni se lee aparte. */}
          <ZonaSubida />

          {error && (
            <Aviso tono="rojo" onCerrar={() => setError("")}>
              {error}
            </Aviso>
          )}
        </section>

        {/* ── tres ejemplos para probar sin datos reales ─────────────── */}
        <section aria-labelledby="titulo-ejemplos" className="space-y-5">
          <div>
            <h3 id="titulo-ejemplos" className="t-h2 text-tinta">Tres ejemplos para conocer la aplicación</h3>
            <p className="t-small mt-1 text-gris">
              Datos ficticios. Sirven para probar antes de subir los archivos de un cliente real.
            </p>
          </div>
          <div className="grid gap-4 sm:grid-cols-3">
            {casos.map((c) => (
              <article key={c.id} className="material-hoja flex flex-col p-5">
                <div className="flex items-start justify-between gap-2">
                  <h4 className="t-body font-semibold text-tinta">{c.nombre}</h4>
                  {c.id === "mediocre" && <Insignia tono="ambar">con errores</Insignia>}
                </div>
                <p className="t-small mt-2 flex-1 text-grafito">{c.descripcion}</p>
                <p className="t-meta mt-4 text-gris">
                  {c.movimientos} movimientos
                  {c.con_inventario && " · inventario"}
                  {c.con_nomina && " · nómina"}
                  {c.con_activos && " · activos"}
                </p>
                <div className="mt-5 flex flex-wrap items-center gap-4">
                  <BotonPrimario
                    compacto
                    disabled={!!cargando}
                    cargando={cargando === `caso-${c.id}`}
                    onClick={() => ejecutar(`caso-${c.id}`, () => api.demo(clienteId, c.id))}
                  >
                    Cargar
                  </BotonPrimario>
                  <EnlaceSubrayado href={descargas.plantillaCaso(c.id)}>
                    <Download size={14} strokeWidth={1.5} aria-hidden /> Descargar Excel
                  </EnlaceSubrayado>
                </div>
              </article>
            ))}
          </div>
        </section>
      </div>

      {/* ── ayuda: formatos y plantilla ─────────────────────────────── */}
      <aside className="space-y-6 escritorio:col-span-4">
        <section className="material-hoja p-6">
          <h3 className="t-meta text-gris">Lo que puede subir</h3>
          <ul className="mt-4 space-y-2.5">
            {FORMATOS.map((f) => (
              <li key={f} className="t-small flex items-start gap-2.5 text-grafito">
                <Check size={16} strokeWidth={1.5} aria-hidden className="mt-0.5 shrink-0 text-tinta" />
                <span>{f}</span>
              </li>
            ))}
          </ul>
          {/* Decir la verdad sobre el PDF evita que el contador crea que falló
              la aplicación cuando lo que subió es un escaneo. */}
          <p className="t-small mt-5 border-t border-linea pt-4 text-gris">
            <strong className="font-semibold text-grafito">Sobre los PDF:</strong> se leen los que genera un programa
            contable, porque traen texto. Un PDF escaneado es una foto del papel y no tiene nada que leer; en ese caso
            pida el archivo en Excel. Lo que se extrae de un PDF siempre pasa por la revisión antes de entrar a la
            contabilidad.
          </p>
        </section>

        <section className="material-hoja p-6">
          <h3 className="t-meta text-gris">Plantilla para el cliente</h3>
          <p className="t-small mt-3 text-grafito">
            Si el cliente no tiene un formato fijo, entréguele esta plantilla para que digite sus movimientos.
          </p>
          <div className="mt-5">
            <BotonFantasma compacto href={descargas.plantilla} icono={<Download size={16} strokeWidth={1.5} aria-hidden />}>
              Descargar plantilla (.xlsx)
            </BotonFantasma>
          </div>
        </section>
      </aside>
    </div>
  );
}
