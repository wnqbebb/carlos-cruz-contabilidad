import type {
  Actividad,
  ArchivoImportado,
  CasoEjemplo,
  Cierre,
  Cliente,
  ComparacionFicha,
  Contador,
  FichaExtraida,
  Confirmacion,
  ConteoClientes,
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
  Salud,
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

async function pedir<T>(ruta: string, opciones?: RequestInit): Promise<T> {
  // Solo las lecturas se repiten: repetir una escritura podría hacerla dos veces.
  const esLectura = !opciones?.method || opciones.method === "GET";
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
  salud: () => pedir<Salud>("/api/salud"),
  contador: () => pedir<Contador>("/api/contador"),
  guardarContador: (datos: Partial<Contador>) =>
    pedir<Contador>("/api/contador", { method: "PUT", ...json(datos) }),
  puc: () => pedir<{ codigo: string; nombre: string }[]>("/api/puc"),
  parametros: () => pedir<Record<string, any>>("/api/parametros"),
  guardarParametros: (anio: number, valores: Record<string, unknown>) =>
    pedir<Record<string, any>>(`/api/parametros/${anio}`, { method: "PUT", ...json(valores) }),
};

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
  /** Los tres ejemplos: completo, mediocre y basico. */
  casos: () => pedir<CasoEjemplo[]>("/api/casos"),
  demo: (clienteId?: string | null, caso = "completo") =>
    pedir<Importacion>(`/api/importar/demo${qs({ cliente_id: clienteId ?? "", caso })}`, { method: "POST" }),
  calcular: (p: Peticion) => pedir<Resultado>("/api/calcular", { method: "POST", ...json(p) }),
  /** Vuelve a abrir una subida que quedó con preguntas sin responder. */
  verImportacion: (sid: string) => pedir<Importacion>(`/api/importar/${sid}`),
  guardarCierre: (sid: string) =>
    pedir<{ ok: boolean; mensaje: string }>(`/api/cierre/${sid}`, { method: "POST" }),
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

/* ── descargas ─────────────────────────────────────────────────────────── */
export const descargas = {
  excel: (sid: string) => `${BASE}/api/exportar/${sid}/excel`,
  pdf: (sid: string) => `${BASE}/api/exportar/${sid}/pdf`,
  saldos: (sid: string) => `${BASE}/api/exportar/${sid}/saldos`,
  plantilla: `${BASE}/api/plantilla`,
  plantillaCaso: (caso: string) => `${BASE}/api/plantilla-demo?caso=${caso}`,
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
