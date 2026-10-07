import type { Resultado } from "../tipos";
import { clases, numero } from "../formato";

export function CuentasT({ cuentas }: { cuentas: Resultado["cuentas_t"] }) {
  return (
    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
      {cuentas.map((c) => {
        const filas = Math.max(c.debitos.length, c.creditos.length);
        return (
          <div key={c.codigo} className={clases("rounded-lg border bg-papel", c.contraria ? "border-ambar" : "border-linea")}>
            <div className="border-b-2 border-tinta/20 px-3 py-2 text-center">
              <div className="text-xs text-grafito">{c.codigo}</div>
              <div className="text-sm font-semibold text-tinta">{c.nombre}</div>
            </div>
            <div className="grid grid-cols-2 text-[12px] cifras">
              <div className="border-r-2 border-tinta/20">
                <div className="bg-hoja px-2 py-1 text-center font-medium text-grafito">Debe</div>
                {Array.from({ length: filas }).map((_, i) => (
                  <div key={i} className="flex justify-between gap-2 px-2 py-0.5" title={c.debitos[i]?.ref}>
                    <span className="truncate text-gris">{c.debitos[i]?.ref ? c.debitos[i].ref.slice(0, 14) : ""}</span>
                    <span>{c.debitos[i] ? numero(c.debitos[i].valor) : ""}</span>
                  </div>
                ))}
                <div className="flex justify-end border-t border-linea px-2 py-1 font-semibold">{numero(c.total_d)}</div>
              </div>
              <div>
                <div className="bg-hoja px-2 py-1 text-center font-medium text-grafito">Haber</div>
                {Array.from({ length: filas }).map((_, i) => (
                  <div key={i} className="flex justify-between gap-2 px-2 py-0.5" title={c.creditos[i]?.ref}>
                    <span className="truncate text-gris">{c.creditos[i]?.ref ? c.creditos[i].ref.slice(0, 14) : ""}</span>
                    <span>{c.creditos[i] ? numero(c.creditos[i].valor) : ""}</span>
                  </div>
                ))}
                <div className="flex justify-end border-t border-linea px-2 py-1 font-semibold">{numero(c.total_c)}</div>
              </div>
            </div>
            <div className={clases("border-t px-3 py-1.5 text-right text-sm font-semibold", c.contraria ? "bg-ambar-suave text-ambar" : "bg-hoja text-tinta")}>
              Saldo {c.naturaleza === "D" ? "débito" : "crédito"}: {numero(c.saldo)}
              {c.contraria && <span className="ml-1 text-xs font-normal">(contrario a su naturaleza)</span>}
            </div>
          </div>
        );
      })}
    </div>
  );
}
