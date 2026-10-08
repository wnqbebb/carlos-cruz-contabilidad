import { Check, Download } from "lucide-react";
import { descargas } from "../api";
import { ZonaSubida } from "./Subir";
import { EnlaceSubrayado } from "../ui";

const FORMATOS = [
  "Plantilla oficial de Carlos Cruz (.xlsx)",
  "Mayor en cuentas T horizontales",
  "Hoja de trabajo (saldo inicial + movimientos)",
  "Libro de aportes y socios",
  "Nómina (liquidación, aportes y retenciones)",
  "Estados financieros anteriores (auditoría automática)",
  "Balances en PDF generados por un programa contable",
];

/**
 * Subir los archivos de un periodo (v2.3 · Fase 3). La zona es la misma puerta
 * única de toda la aplicación: al confirmar, el archivo vuelve a este cliente ya
 * leído y se pasa a las preguntas. Lo demás (formatos, plantilla) va plegado.
 */
export function SubirPeriodo() {
  return (
    <section aria-labelledby="titulo-subir" className="space-y-5">
      <div>
        <h2 id="titulo-subir" className="t-h2 text-tinta">Suba los archivos del periodo</h2>
        <p className="t-body mt-1 max-w-2xl text-grafito">
          El sistema reconoce cada hoja y le pregunta solo lo que no pudo deducir.
        </p>
      </div>
      <ZonaSubida />
      <details>
        <summary className="t-small cursor-pointer select-none text-azul-tinta underline underline-offset-4">
          Qué archivos sirven
        </summary>
        <ul className="mt-4 space-y-2">
          {FORMATOS.map((f) => (
            <li key={f} className="t-small flex items-start gap-2.5 text-grafito">
              <Check size={16} strokeWidth={1.5} aria-hidden className="mt-0.5 shrink-0 text-tinta" />
              <span>{f}</span>
            </li>
          ))}
        </ul>
        <p className="t-small mt-4 max-w-2xl text-gris">
          Los PDF se leen cuando los generó un programa contable. Un PDF escaneado es una foto: pida el Excel.
        </p>
        <p className="mt-4">
          <EnlaceSubrayado href={descargas.plantilla}>
            <Download size={14} strokeWidth={1.5} aria-hidden /> Plantilla para que el cliente digite (.xlsx)
          </EnlaceSubrayado>
        </p>
      </details>
    </section>
  );
}
