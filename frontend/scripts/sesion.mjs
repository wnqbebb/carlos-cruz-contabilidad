/**
 * Inicio de sesión para los scripts de recorrido (A2; v2.3 · Fase 6: con token CSRF).
 *
 *   import { conSesion } from "./sesion.mjs";
 *   const navegador = await chromium.launch(...);
 *   await conSesion(navegador, base);
 *
 * Entra con el usuario de prueba de la copia aislada (scripts/copia_aislada.sh)
 * o con el que digan CC_PRUEBA_USUARIO y CC_PRUEBA_CLAVE. Desde ahí, cada
 * `fetch` del script lleva la cookie (y el token CSRF si modifica datos) y
 * cada contexto nuevo del navegador lleva la cookie.
 */
export const USUARIO = process.env.CC_PRUEBA_USUARIO ?? "prueba";
export const CLAVE = process.env.CC_PRUEBA_CLAVE ?? "prueba-aislada-2026";

export async function iniciarSesion(base) {
  const r = await fetch(`${base}/api/sesion`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Origin: base },
    body: JSON.stringify({ usuario: USUARIO, clave: CLAVE }),
  });
  if (!r.ok) throw new Error(`No se pudo iniciar sesión en ${base}: ${r.status} ${await r.text()}`);
  const cookie = (r.headers.get("set-cookie") ?? "").split(";")[0];
  const i = cookie.indexOf("=");
  const { csrf } = await r.json();
  return { nombre: cookie.slice(0, i), valor: cookie.slice(i + 1), csrf };
}

let galleta = null;

/** Inicia la sesión y hace que cada `fetch` del script la lleve. Se puede llamar antes de abrir el navegador. */
export async function prepararSesion(base) {
  if (galleta) return galleta;
  galleta = await iniciarSesion(base);
  const original = globalThis.fetch;
  const c = galleta;
  globalThis.fetch = (url, opciones = {}) => {
    const metodo = (opciones.method ?? "GET").toUpperCase();
    const extra = metodo === "GET" ? {} : { "X-CSRF": c.csrf, Origin: base };
    return original(url, { ...opciones, headers: { ...(opciones.headers ?? {}), cookie: `${c.nombre}=${c.valor}`, ...extra } });
  };
  return galleta;
}

export async function conSesion(navegador, base) {
  const c = await prepararSesion(base);
  const nuevo = navegador.newContext.bind(navegador);
  navegador.newContext = async (opciones) => {
    const contexto = await nuevo(opciones);
    await contexto.addCookies([{ name: c.nombre, value: c.valor, url: base }]);
    return contexto;
  };
  return c;
}
