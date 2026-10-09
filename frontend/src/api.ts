import type {
  Actividad,
  ArchivoImportado,
  Cierre,
  Cliente,
  ComparacionFicha,
  DeclaracionRenta,
  FilaCarteraRenta,
  Contador,
  FichaExtraida,
  Confirmacion,
  IdentidadDetectada,
  Importacion,
  InformeImportacionClientes,
  InformeSugerencias,
  PaginaClientes,
  PaginaMovimientos,
  Periodo,
  Peticion,
  Propuesta,
  Resultado,
  ResultadoBusqueda,
  EstadoSistema,
  Tablero,
  VersionPeriodo,
} from "./tipos";

/**
 * Base del API. En local el proxy de Vite manda /api al backend.
 * Al desplegar el frontend en Vercel se define VITE_API en las variables de
 * entorno con la URL pública del backend.
 */
const BASE = (import.meta.env?.VITE_API as string | undefined)?.replace(/\/$/, "") ?? "";

/**
 * Error del servidor con su código, para que la pantalla ofrezca la salida en
 * vez de un texto suelto. Por ejemplo, `periodo_cerrado` permite mostrar el
 * botón «Reabrir y recalcular» en lugar de dejar al contador bloqueado.
 */
export class ErrorApi extends Error {
  constructor(
    mensaje: string,
    readonly estado: number,
    readonly codigo = "",
    readonly datos: Record<string, unknown> = {},
  ) {
    super(mensaje);
    this.name = "ErrorApi";
  }
}

/** Esperas antes de reintentar una LECTURA que no obtuvo respuesta (H20). */
const ESPERAS_REINTENTO = [800, 2000];
const dormir = (ms: number) => new Promise((ok) => setTimeout(ok, ms));

/* ── v2.3 · Fase 6: token CSRF de la sesión y confirmación de contraseña ──
   Toda petición que modifica datos lleva el token de la sesión en `X-CSRF`.
   Si el servidor pide confirmar la contraseña (acciones delicadas), se abre el
   diálogo registrado con `alPedirContrasena` y, si el contador la confirma, la
   petición se repite una vez. */
let tokenCsrf: string | null = null;
let pedirContrasena: (() => Promise<boolean>) | null = null;

export function fijarCsrf(token: string | null | undefined) {
  tokenCsrf = token ?? null;
}

export function alPedirContrasena(fn: (() => Promise<boolean>) | null) {
  pedirContrasena = fn;
}

async function pedir<T>(ruta: string, opciones?: RequestInit, reintento = true): Promise<T> {
  // Solo las lecturas se repiten: repetir una escritura podría hacerla dos veces.
  const esLectura = !opciones?.method || opciones.method === "GET";
  if (!esLectura && tokenCsrf) {
    const encabezados = new Headers(opciones?.headers);
    encabezados.set("X-CSRF", tokenCsrf);
    opciones = { ...opciones, headers: encabezados };
  }
  let r: Response | null = null;
  for (let intento = 0; ; intento++) {
    try {
      r = await fetch(BASE + ruta, opciones);
      if (!(esLectura && r.status === 503 && intento < ESPERAS_REINTENTO.length)) break;
    } catch {
      if (!(esLectura && intento < ESPERAS_REINTENTO.length)) {
        throw new ErrorApi(
          "No se pudo contactar el servidor. Revise que el programa esté abierto y vuelva a intentar.",
          0,
          "sin_conexion",
        );
      }
    }
    await dormir(ESPERAS_REINTENTO[intento]);
  }
  if (!r.ok) {
    let detalle = `${r.status} ${r.statusText}`;
    let codigo = "";
    let datos: Record<string, unknown> = {};
    try {
      const j = await r.json();
      const d = j.detail ?? j;
      if (typeof d === "string") {
        detalle = d;
      } else if (d && typeof d === "object") {
        // El backend manda {codigo, mensaje, …} cuando la pantalla puede actuar.
        datos = d as Record<string, unknown>;
        codigo = String(datos.codigo ?? "");
        detalle = String(datos.mensaje ?? JSON.stringify(d));
      }
    } catch {
      /* la respuesta no era JSON */
    }
    // Sin sesión (venció o se cerró en otra pestaña): la aplicación vuelve a la pantalla de ingreso.
    if (r.status === 401 && codigo === "sin_sesion") window.dispatchEvent(new Event("cc:sesion-vencida"));
    if (r.status === 403 && reintento) {
      // La página guardaba un token viejo: se toma el de la sesión y se repite una vez.
      if (codigo === "csrf") {
        const e = await fetch(BASE + "/api/sesion").then((x) => x.json()).catch(() => null);
        if (e?.csrf) {
          fijarCsrf(e.csrf);
          return pedir<T>(ruta, opciones, false);
        }
      }
      if (codigo === "reautenticar" && pedirContrasena && (await pedirContrasena())) {
        return pedir<T>(ruta, opciones, false);
      }
    }
    throw new ErrorApi(detalle, r.status, codigo, datos);
  }
  if (r.status === 204) return undefined as T;
  return (await r.json()) as T;
}

const json = (cuerpo: unknown): RequestInit => ({
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(cuerpo),
});

const qs = (p: Record<string, string | number | boolean | undefined>) => {
  const u = new URLSearchParams();
  for (const [k, v] of Object.entries(p)) {
    if (v !== undefined && v !== "" && v !== false) u.set(k, String(v));
  }
  const s = u.toString();
  return s ? `?${s}` : "";
};

/* ── sistema ───────────────────────────────────────────────────────────── */
export const sistema = {
  estado: () => pedir<EstadoSistema>("/api/sistema"),
  contador: () => pedir<Contador>("/api/contador"),
  puc: () => pedir<{ codigo: string; nombre: string }[]>("/api/puc"),
};

/* ── sesión del contador (A2) ──────────────────────────────────────────── */
export interface EstadoSesion {
  activa: boolean;
  usuario: string | null;
  configurado: boolean;
  puede_crear?: boolean;
  csrf?: string | null;
  totp?: boolean;
  reautenticacion_vigente?: boolean;
}
export interface EvaluacionClave {
  valida: boolean;
  problemas: string[];
  puntaje: number;
}
export interface EstadoAcceso {
  usuario: string;
  totp_activo: boolean;
  codigos_restantes: number;
  sesiones: number;
  fallidos_24h: number;
}
export const sesionApi = {
  async estado() {
    const e = await pedir<EstadoSesion>("/api/sesion");
    fijarCsrf(e.csrf);
    return e;
  },
  async entrar(usuario: string, clave: string, codigo = "") {
    const e = await pedir<EstadoSesion>("/api/sesion", { method: "POST", ...json({ usuario, clave, codigo }) });
    fijarCsrf(e.csrf);
    return e;
  },
  salir: () => pedir<EstadoSesion>("/api/sesion/salir", { method: "POST" }),
  reautenticar: (clave: string, codigo = "") =>
    pedir<{ ok: boolean }>("/api/sesion/reautenticar", { method: "POST", ...json({ clave, codigo }) }, false),
};

/* ── la cuenta del contador (v2.3 · Fase 6) ────────────────────────────── */
export const acceso = {
  politica: (clave: string, usuario = "") =>
    pedir<EvaluacionClave>("/api/acceso/politica", { method: "POST", ...json({ clave, usuario }) }),
  async crear(usuario: string, clave: string) {
    const r = await pedir<{ usuario: string; codigos: string[]; csrf: string }>("/api/acceso/primer-uso", {
      method: "POST",
      ...json({ usuario, clave }),
    });
    fijarCsrf(r.csrf);
    return r;
  },
  recuperar: (usuario: string, codigo: string, nueva: string) =>
    pedir<{ ok: boolean; codigos_restantes: number }>("/api/acceso/recuperar", {
      method: "POST",
      ...json({ usuario, codigo, nueva }),
    }),
  estado: () => pedir<EstadoAcceso>("/api/acceso/estado"),
  cambiarClave: (actual: string, nueva: string) =>
    pedir<{ ok: boolean; sesiones_cerradas: number }>("/api/acceso/clave", { method: "POST", ...json({ actual, nueva }) }),
  nuevosCodigos: () => pedir<{ codigos: string[] }>("/api/acceso/codigos", { method: "POST" }),
  iniciarTotp: () => pedir<{ qr: string; secreto: string }>("/api/acceso/totp/iniciar", { method: "POST" }),
  confirmarTotp: (codigo: string) =>
    pedir<{ codigos: string[] }>("/api/acceso/totp/confirmar", { method: "POST", ...json({ codigo }) }),
  desactivarTotp: () => pedir<{ ok: boolean }>("/api/acceso/totp/desactivar", { method: "POST" }),
  cerrarOtrasSesiones: () => pedir<{ cerradas: number }>("/api/acceso/sesiones/cerrar-todas", { method: "POST" }),
};

/** Descargas que piden confirmar la contraseña: se confirma antes de abrir el enlace. */
export async function descargarConfirmando(url: string) {
  const e = await sesionApi.estado();
  if (!e.reautenticacion_vigente) {
    if (!pedirContrasena || !(await pedirContrasena())) return;
  }
  window.location.href = url;
}

/* ── directorio de clientes ────────────────────────────────────────────── */
export const clientes = {
  listar: (p: {
    q?: string;
    estado?: string;
    etiqueta?: string;
    orden?: string;
    descendente?: boolean;
    pagina?: number;
    por_pagina?: number;
  } = {}) => pedir<PaginaClientes>(`/api/clientes${qs(p)}`),

  obtener: (id: string) => pedir<Cliente>(`/api/clientes/${id}`),
  /** Clientes marcados como demostración: los únicos que borra «Eliminar clientes de demostración». */
  demostracion: () => pedir<{ clientes: { id: string; razon_social: string; nit: string }[] }>("/api/clientes/demostracion"),
  eliminarDemostracion: () =>
    pedir<{ eliminados: number; clientes: string[] }>("/api/clientes/demostracion/eliminar", { method: "POST" }),
  crear: (datos: Partial<Cliente>) => pedir<Cliente>("/api/clientes", { method: "POST", ...json(datos) }),
  actualizar: (id: string, datos: Partial<Cliente>) =>
    pedir<Cliente>(`/api/clientes/${id}`, { method: "PATCH", ...json(datos) }),
  archivar: (id: string) => pedir<{ ok: boolean }>(`/api/clientes/${id}`, { method: "DELETE" }),
  eliminar: (id: string) =>
    pedir<{ ok: boolean; razon_social: string; periodos_borrados: number }>(
      `/api/clientes/${id}?definitivo=true`,
      { method: "DELETE" },
    ),
  restaurar: (id: string) => pedir<Cliente>(`/api/clientes/${id}/restaurar`, { method: "POST" }),
  /** Qué cambiaría en la ficha con estos documentos. No guarda nada. */
  compararFicha(id: string, archivos: File[]) {
    const fd = new FormData();
    archivos.forEach((a) => fd.append("archivos", a));
    return pedir<ComparacionFicha>(`/api/clientes/${id}/ficha/comparar`, { method: "POST", body: fd });
  },
  buscar: (q: string, limite = 8) =>
    pedir<{ q: string; resultados: ResultadoBusqueda[] }>(`/api/buscar${qs({ q, limite })}`),

  importar: (archivo: File, opciones: { actualizar_existentes?: boolean; solo_revisar?: boolean } = {}) => {
    const fd = new FormData();
    fd.append("archivo", archivo);
    return pedir<InformeImportacionClientes>(`/api/clientes/importar${qs(opciones)}`, {
      method: "POST",
      body: fd,
    });
  },
};

/* ── histórico y análisis ──────────────────────────────────────────────── */
export const analisis = {
  tablero: () => pedir<Tablero>("/api/tablero"),
  posponerTarea: (clave: string) =>
    pedir<{ ok: boolean; hasta: string }>(`/api/tareas/${encodeURIComponent(clave)}/posponer`, { method: "POST" }),
  hacerTarea: (clave: string) =>
    pedir<{ ok: boolean }>(`/api/tareas/${encodeURIComponent(clave)}/hacer`, { method: "POST" }),
  periodos: (clienteId: string) =>
    pedir<{ periodos: Periodo[]; cierres: Cierre[] }>(`/api/clientes/${clienteId}/periodos`),
  serie: (clienteId: string, limite = 24) =>
    pedir<{ serie: Periodo[] }>(`/api/clientes/${clienteId}/serie${qs({ limite })}`),
  movimientos: (
    clienteId: string,
    p: { cuenta?: string; desde?: string; hasta?: string; pagina?: number; por_pagina?: number } = {},
  ) => pedir<PaginaMovimientos>(`/api/clientes/${clienteId}/movimientos${qs(p)}`),
  sugerencias: (clienteId: string) =>
    pedir<InformeSugerencias>(`/api/clientes/${clienteId}/sugerencias`),
  resultadoDePeriodo: (periodoId: string) =>
    pedir<{ resultado: Resultado; peticion: Peticion; creado: string }>(
      `/api/periodos/${periodoId}/resultado`,
    ),
  versiones: (periodoId: string) =>
    pedir<{ versiones: VersionPeriodo[] }>(`/api/periodos/${periodoId}/versiones`),
  restaurarVersion: (versionId: number) =>
    pedir<Periodo>(`/api/versiones/${versionId}/restaurar`, { method: "POST" }),
  actividad: (clienteId: string, limite = 40) =>
    pedir<{ actividad: Actividad[]; importaciones: ArchivoImportado[] }>(
      `/api/clientes/${clienteId}/actividad${qs({ limite })}`,
    ),

  notaPeriodo: (periodoId: string, nota: string) =>
    pedir<Periodo>(`/api/periodos/${periodoId}`, { method: "PATCH", ...json({ nota }) }),
  eliminarPeriodo: (periodoId: string) =>
    pedir<{ ok: boolean }>(`/api/periodos/${periodoId}`, { method: "DELETE" }),
  reabrirPeriodo: (periodoId: string) =>
    pedir<{ ok: boolean; mensaje: string }>(`/api/periodos/${periodoId}/reabrir`, { method: "POST" }),
  /** Cierra con los saldos guardados: no hace falta la sesión de trabajo (v2.3). */
  cerrarPeriodo: (periodoId: string) =>
    pedir<{ ok: boolean; fecha_corte: string; cuentas: number }>(`/api/periodos/${periodoId}/cerrar`, { method: "POST" }),
};

/* ── flujo de trabajo contable ─────────────────────────────────────────── */
export const trabajo = {
  importar(archivos: File[], clienteId?: string | null) {
    const fd = new FormData();
    archivos.forEach((a) => fd.append("archivos", a));
    return pedir<Importacion>(`/api/importar${qs({ cliente_id: clienteId ?? "" })}`, {
      method: "POST",
      body: fd,
    });
  },
  ejemplo: (clienteId?: string | null) =>
    pedir<Importacion>(`/api/importar/ejemplo${qs({ cliente_id: clienteId ?? "" })}`, { method: "POST" }),
  calcular: (p: Peticion) => pedir<Resultado>("/api/calcular", { method: "POST", ...json(p) }),
  /** Vuelve a abrir una subida que quedó con preguntas sin responder. */
  verImportacion: (sid: string) => pedir<Importacion>(`/api/importar/${sid}`),
};

/* ── una sola puerta: se sube lo que sea y el backend decide ───────────── */
export const puerta = {
  /** Lee los archivos y propone qué son y de quién. No guarda nada todavía. */
  subir(archivos: File[], clienteId?: string | null) {
    const fd = new FormData();
    archivos.forEach((a) => fd.append("archivos", a));
    return pedir<Propuesta>(`/api/subir${qs({ cliente_id: clienteId ?? "" })}`, { method: "POST", body: fd });
  },
  /**
   * Sigue adelante con lo que ya se subió. El archivo NUNCA se vuelve a pedir:
   * los bytes siguen en la sesión del servidor.
   */
  confirmar(
    subidaId: string,
    cuerpo: {
      cliente_id?: string;
      crear?: { nit: string; razon_social: string; dv?: string };
      clase?: string;
      actualizar_existentes?: boolean;
    } = {},
  ) {
    return pedir<Confirmacion>(`/api/subir/${subidaId}/confirmar`, { method: "POST", ...json(cuerpo) });
  },
  /** Solo identidad: lo usa el formulario de cliente nuevo para llenarse solo. */
  identidad(archivos: File[]) {
    const fd = new FormData();
    archivos.forEach((a) => fd.append("archivos", a));
    return pedir<{ identidad: IdentidadDetectada; ficha: FichaExtraida; sugerido_del_nombre: string }>("/api/identidad", {
      method: "POST",
      body: fd,
    });
  },
};

/* ── declaración de renta, formulario 210 (v2.3 · Fase 5) ─────────────── */
export type CambioRenta =
  | { tipo: "respuesta"; id: string; valor: string; extra?: string }
  | { tipo: "beneficio"; id: string; valor: string | number | boolean | null; uno_por_ciento?: string }
  | { tipo: "reclasificar"; linea: string; categoria: string }
  | { tipo: "valor"; linea: string; valor: string }
  | { tipo: "excluir"; linea: string }
  | { tipo: "confirmar"; lineas: string[] }
  | { tipo: "agregar"; categoria: string; valor: string; descripcion?: string }
  | { tipo: "quitar_agregado"; id: string };

export const renta = {
  anios: () => pedir<{ anios: number[]; actual: number }>("/api/renta/anios"),
  cartera: (anio: number) => pedir<{ anio: number; declaraciones: FilaCarteraRenta[] }>(`/api/renta/cartera${qs({ anio })}`),
  ver: (clienteId: string, anio: number) => pedir<DeclaracionRenta>(`/api/renta/${clienteId}/${anio}`),
  subir(clienteId: string, anio: number, archivos: File[]) {
    const fd = new FormData();
    archivos.forEach((a) => fd.append("archivos", a));
    return pedir<DeclaracionRenta>(`/api/renta/${clienteId}/${anio}/documentos`, { method: "POST", body: fd });
  },
  cambiar: (clienteId: string, anio: number, cambio: CambioRenta) =>
    pedir<DeclaracionRenta>(`/api/renta/${clienteId}/${anio}/cambio`, { method: "POST", ...json(cambio) }),
  marcar: (clienteId: string, anio: number, estado: "revisada" | "borrador" | "presentada", numero = "", fecha = "") =>
    pedir<DeclaracionRenta>(`/api/renta/${clienteId}/${anio}/estado`, { method: "POST", ...json({ estado, numero, fecha }) }),
  recorte: (clienteId: string, anio: number, id: string) => `${BASE}/api/renta/${clienteId}/${anio}/recorte/${id}`,
  descarga: (clienteId: string, anio: number, que: "todo" | "pdf" | "excel" | "resumen") =>
    `${BASE}/api/renta/${clienteId}/${anio}/descargar/${que}`,
};

/* ── descargas ─────────────────────────────────────────────────────────── */
export const descargas = {
  excel: (sid: string) => `${BASE}/api/exportar/${sid}/excel`,
  pdf: (sid: string) => `${BASE}/api/exportar/${sid}/pdf`,
  saldos: (sid: string) => `${BASE}/api/exportar/${sid}/saldos`,
  plantilla: `${BASE}/api/plantilla`,
  plantillaClientes: `${BASE}/api/clientes/plantilla`,
  // Descargas de un periodo ya guardado: no hace falta volver a subir los Excel.
  excelPeriodo: (periodoId: string) => `${BASE}/api/periodos/${periodoId}/excel`,
  pdfPeriodo: (periodoId: string) => `${BASE}/api/periodos/${periodoId}/pdf`,
  saldosPeriodo: (periodoId: string) => `${BASE}/api/periodos/${periodoId}/saldos`,
  /** Un libro oficial suelto: «libro-diario» o «mayor-balances», en «excel» o «pdf». */
  libro: (periodoId: string, libro: "libro-diario" | "mayor-balances", formato: "excel" | "pdf") =>
    `${BASE}/api/periodos/${periodoId}/${libro}/${formato}`,
};

/** Alias de compatibilidad con las pantallas del flujo antiguo. */
export const api = { ...trabajo, ...sistema };
