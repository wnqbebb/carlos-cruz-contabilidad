import { useEffect, useState } from "react";
import { sistema } from "./api";
import type { Contador } from "./tipos";

/**
 * Los datos del contador dueño de la aplicación (H18): nombre, tarjeta
 * profesional y municipio. Salen del servidor (`/api/contador`), no del
 * código: se piden una sola vez y todas las pantallas comparten la respuesta.
 */
let cache: Contador | null = null;
let pedido: Promise<Contador> | null = null;
const oyentes = new Set<(c: Contador) => void>();

export function cargarContador(forzar = false): Promise<Contador> {
  if (!pedido || forzar) {
    pedido = sistema.contador().then((c) => {
      cache = c;
      oyentes.forEach((f) => f(c));
      return c;
    });
    pedido.catch(() => {
      pedido = null;
    });
  }
  return pedido;
}

export function useContador(): Contador | null {
  const [c, setC] = useState<Contador | null>(cache);
  useEffect(() => {
    oyentes.add(setC);
    if (!cache) cargarContador().catch(() => undefined);
    return () => {
      oyentes.delete(setC);
    };
  }, []);
  return c;
}
