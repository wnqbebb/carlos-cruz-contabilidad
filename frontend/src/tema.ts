import { useEffect, useState } from "react";

/**
 * Modo claro, oscuro o el del sistema (spec v2.2 · 8.4).
 *
 * Se guarda en este navegador (es una comodidad personal, no un dato del
 * cliente). Por defecto, «Sistema»: sigue al sistema operativo y cambia solo
 * si este cambia. El atributo `data-tema` del <html> es lo único que leen los
 * tokens; `index.html` lo fija antes de pintar para que no haya destello.
 */
export type PreferenciaTema = "claro" | "oscuro" | "sistema";
const CLAVE = "cc-tema";
const consulta = () => window.matchMedia("(prefers-color-scheme: dark)");

export function preferenciaGuardada(): PreferenciaTema {
  try {
    const v = localStorage.getItem(CLAVE);
    return v === "claro" || v === "oscuro" ? v : "sistema";
  } catch {
    return "sistema";
  }
}

export function aplicarTema(p: PreferenciaTema): void {
  const oscuro = p === "oscuro" || (p === "sistema" && consulta().matches);
  document.documentElement.setAttribute("data-tema", oscuro ? "oscuro" : "claro");
}

export function useTema(): [PreferenciaTema, (p: PreferenciaTema) => void] {
  const [pref, setPref] = useState<PreferenciaTema>(preferenciaGuardada);

  useEffect(() => {
    aplicarTema(pref);
    if (pref !== "sistema") return;
    const mq = consulta();
    const cambio = () => aplicarTema("sistema");
    mq.addEventListener("change", cambio);
    return () => mq.removeEventListener("change", cambio);
  }, [pref]);

  const elegir = (p: PreferenciaTema) => {
    try {
      localStorage.setItem(CLAVE, p);
    } catch {
      /* navegador sin almacenamiento: el cambio vale para esta visita */
    }
    setPref(p);
  };
  return [pref, elegir];
}
