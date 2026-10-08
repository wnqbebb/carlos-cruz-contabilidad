/**
 * Tipos del API.
 *
 * `Monto` es `string` a propósito: el backend manda los importes como cadena
 * decimal exacta para no perder precisión al pasar por JSON. Nunca los
 * convierta a `number`; use las funciones de `formato.ts`.
 */
export type Monto = string;
export type Valor = string | number | null | undefined;

/* ── informes genéricos del motor ──────────────────────────────────────── */
export interface Columna {
  clave: string;
  titulo: string;
  tipo: "texto" | "dinero" | "numero";
  ancho?: number | null;
}

export interface Fila {
  tipo: "seccion" | "linea" | "subtotal" | "total" | "nota" | "vacia";
  valores: Record<string, Valor>;
  nivel: number;
}

export interface Reporte {
  id: string;
  titulo: string;
  subtitulo: string;
  columnas: Columna[];
  filas: Fila[];
  firmas: boolean;
  horizontal: boolean;
  notas: string[];
  verificacion?: { cuadra?: boolean; [k: string]: unknown } | null;
}

export interface Alerta {
  codigo: string;
  severidad: "error" | "advertencia" | "info";
  mensaje: string;
  detalle: string;
  origen: string;
}

/* ── empresa que consume el motor ──────────────────────────────────────── */
export interface Empresa {
  razon_social: string;
  sigla: string;
  nit: string;
  direccion: string;
  municipio: string;
  rep_legal: string;
  rep_legal_cc: string;
  contador: string;
  contador_cc: string;
  contador_tp: string;
  grupo_niif: number;
  responsable_iva: boolean;
  tarifa_renta: Monto;
  capital_suscrito: Monto;
  periodo_desde: string;
  periodo_hasta: string;
  demo: boolean;
  [k: string]: unknown;
}

/* ── ejemplos para probar sin datos reales ─────────────────────────────── */
export interface CasoEjemplo {
  id: "completo" | "mediocre" | "basico" | string;
  nombre: string;
  descripcion: string;
  empresa: string;
  nit: string;
  movimientos: number;
  con_inventario: boolean;
  con_nomina: boolean;
  con_activos: boolean;
}

/* ── directorio de clientes ────────────────────────────────────────────── */
export type EstadoCliente = "activo" | "inactivo" | "archivado";
export type Periodicidad = "mensual" | "bimestral" | "trimestral" | "cuatrimestral" | "anual";

export interface Socio {
  id?: number;
  nombre: string;
  cedula: string;
  cargo: string;
  acciones: Monto;
  participacion: Monto;
  comprometido: Monto;
  pagado: Monto;
}

export interface Cliente {
  id: string;
  nit: string;
  dv: string;
  nit_formateado: string;
  turno_dian: number;
  razon_social: string;
  sigla: string;
  tipo_persona: "juridica" | "natural";
  regimen: string;
  grupo_niif: number;
  responsable_iva: boolean;
  tarifa_renta: Monto;
  ciiu: string;
  direccion: string;
  municipio: string;
  departamento: string;
  telefono: string;
  email: string;
  rep_legal: string;
  rep_legal_cc: string;
  rep_legal_suplente: string;
  contador: string;
  contador_cc: string;
  contador_tp: string;
  fecha_constitucion: string | null;
  capital_suscrito: Monto;
  valor_nominal_accion: Monto;
  honorarios_mes: Monto;
  periodicidad: Periodicidad;
  estado: EstadoCliente;
  etiquetas: string[];
  notas: string;
  demo: boolean;
  creado: string;
  actualizado: string;
  socios?: Socio[];
}

export interface PaginaClientes {
  total: number;
  pagina: number;
  por_pagina: number;
  paginas: number;
  clientes: Cliente[];
}

export interface ConteoClientes {
  total: number;
  activos: number;
  inactivos: number;
  archivados: number;
}

/* ── periodos contables ────────────────────────────────────────────────── */
export type EstadoPeriodo = "borrador" | "calculado" | "cerrado";

export interface Periodo {
  id: string;
  cliente_id: string;
  desde: string;
  hasta: string;
  etiqueta: string;
  estado: EstadoPeriodo;
  total_activo: Monto | null;
  total_pasivo: Monto | null;
  total_patrimonio: Monto | null;
  total_ingresos: Monto | null;
  total_gastos: Monto | null;
  utilidad: Monto | null;
  descuadre: Monto;
  cuadra: boolean;
  cuentas: number;
  calculado_en: string | null;
  cerrado_en: string | null;
}

export interface Cierre {
  id: number;
  fecha_corte: string;
  cuentas: number;
  creado: string;
  periodo_id: string | null;
}

export interface Movimiento {
  id: number;
  fecha: string | null;
  cuenta: string;
  nombre_cuenta: string;
  debito: Monto;
  credito: Monto;
  comprobante: string;
  tipo: string;
  tercero_id: string;
  tercero_nombre: string;
  descripcion: string;
  origen: string;
}

export interface PaginaMovimientos {
  total: number;
  pagina: number;
  por_pagina: number;
  paginas: number;
  suma_debito: Monto;
  suma_credito: Monto;
  movimientos: Movimiento[];
}

/* ── sugerencias ───────────────────────────────────────────────────────── */
export type Severidad = "critica" | "alta" | "media" | "informativa";

export interface Sugerencia {
  codigo: string;
  severidad: Severidad;
  titulo: string;
  detalle: string;
  accion: string;
  dato: Record<string, unknown>;
}

export interface InformeSugerencias {
  cliente_id: string;
  razon_social: string;
  generado: string;
  periodos_analizados: number;
  sugerencias: Sugerencia[];
  conteo: Record<Severidad, number>;
}

export interface ClientePendiente {
  cliente_id: string;
  razon_social: string;
  nit_formateado: string;
  municipio: string;
  criticas: number;
  altas: number;
  principal: Sugerencia;
}

export interface Cartera {
  generado: string;
  clientes_revisados: number;
  clientes_totales: number;
  truncado: boolean;
  con_pendientes: number;
  criticas: number;
  altas: number;
  clientes: ClientePendiente[];
}

export interface MesCartera {
  mes: string;
  total_ingresos: Monto;
  total_gastos: Monto;
  utilidad: Monto;
  periodos: number;
}

export interface Tablero {
  clientes: ConteoClientes;
  trabajo: {
    periodos: number;
    cerrados: number;
    pendientes: number;
    descuadrados: number;
    ultimo_corte: string;
  };
  pendientes: Cartera;
  /** Totales de toda la cartera por mes de corte, para la gráfica del tablero. */
  serie: MesCartera[];
}

/* ── importación masiva del directorio ─────────────────────────────────── */
export interface InformeImportacionClientes {
  archivo: string;
  solo_revisar: boolean;
  filas_leidas: number;
  insertados: number;
  actualizados: number;
  rechazados: number;
  columnas_reconocidas: string[];
  mensaje: string;
  muestra_insertados: { fila: number; nit: string; razon_social: string }[];
  muestra_actualizados: { fila: number; nit: string; razon_social: string }[];
  rechazos: { fila: number; nit: string; razon_social: string; motivo: string }[];
  rechazos_omitidos: number;
}

/* ── flujo de trabajo contable ─────────────────────────────────────────── */
export interface Hoja {
  id: string;
  archivo: string;
  hoja: string;
  formato: string;
  formato_nombre: string;
  incluir: boolean;
  motivo: string;
  resumen: Record<string, unknown>;
  solo_auditoria: boolean;
  alertas: Alerta[];
  filas_ignoradas: { origen: string; motivo: string }[];
}

export interface ItemMapeo {
  nombre: string;
  normalizado: string;
  codigo: string | null;
  estado: "exacto" | "confirmar" | "sin";
  fuente: string;
  bandera: string | null;
  candidatos: { codigo: string; nombre: string; puntaje: number }[];
  veces: number;
  valor: Monto;
  hojas: string[];
  por_hoja: Record<string, { veces: number; valor: Monto }>;
}

/** Una decisión que el archivo no permite tomar solo (spec v2.2 · 4.2). */
export interface Pregunta {
  id: string;
  /** archivo › hoja › bloque */
  hoja: string;
  /** tipo · fechas · repetir · terceros · inventario */
  clase: string;
  titulo: string;
  detalle: string;
  opciones: { valor: string; etiqueta: string }[];
  defecto: string;
}

export interface Periodizacion {
  posible: boolean;
  meses: number;
  periodicidad: string;
  meses_por_periodo: number;
  periodos: { desde: string; hasta: string }[];
  defecto: "por_periodo" | "unico";
}

export interface Importacion {
  sesion_id: string;
  cliente_id: string | null;
  cliente: Cliente | null;
  empresa: Empresa;
  periodo_sugerido: { desde: string; hasta: string; fuente: string };
  periodizacion?: Periodizacion;
  preguntas?: Pregunta[];
  mapeo: ItemMapeo[];
  hojas: Hoja[];
}

export interface Config {
  exonerado_114_1: boolean;
  cuenta_provisiones: "25" | "26";
  metodo_inventario: "promedio" | "peps";
  calcular_renta: boolean;
}

export interface Peticion {
  sesion_id: string;
  cliente_id?: string | null;
  incluir: Record<string, boolean>;
  mapeo: Record<string, string>;
  empresa: Partial<Empresa>;
  config: Config;
  decisiones: Record<string, boolean>;
  recordar_alias: boolean;
  /** Respuestas al panel «Preguntas sobre este archivo». */
  respuestas?: Record<string, string>;
  /** «por_periodo»: mes a mes (o según la periodicidad), cerrando cada uno. */
  periodizacion?: "por_periodo" | "unico";
  cerrar_ultimo?: boolean;
}

export interface Ajuste {
  id: string;
  titulo: string;
  tipo: "automatico" | "sugerido" | "manual";
  explicacion: string;
  aceptado: boolean;
  aceptado_defecto: boolean;
  cuadra: boolean;
  total: Monto;
  lineas: { codigo: string; cuenta: string; debito: Monto; credito: Monto; descripcion: string }[];
}

export interface Resultado {
  empresa: Empresa;
  resumen: Record<string, any>;
  alertas: Alerta[];
  ajustes: Ajuste[];
  reportes: Record<string, Reporte>;
  notas: { titulo: string; parrafos: string[] }[];
  cuentas_t: {
    codigo: string;
    nombre: string;
    naturaleza: string;
    saldo: Monto;
    contraria: boolean;
    total_d: Monto;
    total_c: Monto;
    debitos: { valor: Monto; ref: string }[];
    creditos: { valor: Monto; ref: string }[];
  }[];
  saldos_siguiente: { codigo: string; nombre: string; debito: Monto; credito: Monto }[];
  inventario: {
    productos: {
      codigo: string;
      descripcion: string;
      laboratorio: string;
      saldo_cant: Monto;
      costo_promedio: Monto;
      saldo_total: Monto;
      costo_ventas: Monto;
      filas: Record<string, any>[];
    }[];
    vencimientos: Record<string, any>[];
    fisico: Record<string, any>[];
    conciliacion: Record<string, Monto> | null;
    metodo: string;
    costo_ventas: Monto;
    saldo_total: Monto;
  };
  nomina: { liquidaciones: Record<string, any>[]; auditoria: Record<string, any>[] };
  auditoria_ef: {
    archivo: string;
    hoja: string;
    hallazgos: Record<string, any>[];
    comparativo: Record<string, any>[];
    utilidad_corregida: Monto;
  }[];
  depreciacion: Record<string, any>[];
  /** Presentes solo cuando el trabajo se guardó contra un cliente del directorio. */
  guardado?: boolean;
  periodo?: Periodo;
  movimientos_guardados?: number;
  aviso_guardado?: string;
  /** Fila original de cada registro (origen → celdas), para verla desde el libro diario. */
  origenes?: Record<string, string[]>;
  /** Cuando se procesó periodo a periodo: qué pasó con cada uno. */
  periodos_procesados?: {
    desde: string;
    hasta: string;
    estado: "cerrado" | "calculado" | "ya_cerrado" | "sin_movimientos";
    periodo_id?: string;
    utilidad?: Monto;
    cuadra?: boolean;
  }[];
}

/* ── estado del sistema ────────────────────────────────────────────────── */
export interface Salud {
  ok: boolean;
  marca: string;
  lema: string;
  version: string;
  almacenamiento: {
    modo: "local" | "supabase";
    es_postgres: boolean;
    supabase_configurado: boolean;
    proyecto: string;
    conectado: boolean;
    motor: string;
    error: string;
  };
  sesiones_abiertas: number;
}

export interface ResultadoBusqueda {
  tipo: "cliente";
  id: string;
  titulo: string;
  subtitulo: string;
  estado: string;
}

/* ── historial y bitácora (v2.2) ────────────────────────────────────────── */
export interface VersionPeriodo {
  id: number;
  /** recalculo · reapertura · restauracion · cierre */
  motivo: string;
  cuentas: number;
  movimientos: number;
  creado: string;
  estado: string;
  total_activo: Monto | null;
  utilidad: Monto | null;
  con_cierre: boolean;
}

export interface Actividad {
  id: number;
  cliente_id: string | null;
  accion: string;
  titulo: string;
  detalle: Record<string, unknown>;
  creado: string;
}

export interface ArchivoImportado {
  id: string;
  cliente_id: string | null;
  archivo: string;
  hoja: string;
  formato: string;
  sha256: string;
  bytes: number;
  filas: number;
  alertas: number;
  creado: string;
}

/* ── una sola puerta: se sube lo que sea y el backend decide (v2.2) ─────── */

/** Dato de identidad detectado en los archivos, con su procedencia. */
export interface CampoDetectado {
  valor: string;
  /** Archivo y hoja, página o párrafo de donde salió. Se muestra siempre. */
  origen: string;
  /** seguro · probable · sugerido */
  confianza: string;
}

export interface IdentidadDetectada {
  campos: Record<string, CampoDetectado>;
  /** Otros valores que se vieron para el mismo campo, por si el primero falla. */
  conflictos: Record<string, CampoDetectado[]>;
}

export interface HojaDetectada {
  archivo: string;
  hoja: string;
  /** directorio · contabilidad · texto · desconocido */
  clase: string;
  formato: string;
  razon: string;
  filas: number;
}

/** Lo que el backend propone tras leer la subida. Nada se ha guardado aún. */
export interface Propuesta {
  subida_id: string;
  /** directorio · contabilidad · documentos · ambiguo · desconocido */
  clase: string;
  cliente: Cliente | null;
  /** Clientes que ya existen y se parecen al nombre encontrado. */
  coincidencias: (ResultadoBusqueda & { parecido: number })[];
  identidad: IdentidadDetectada;
  /** Campos que hay que pedirle al contador: solo «razon_social» y «nit». */
  falta: string[];
  /** Formatos contables reconocidos, en español, para la tarjeta. */
  contenido: string[];
  /** Meses que cubren los registros, si traen fechas. */
  periodo: { desde: string; hasta: string; texto: string } | null;
  hojas: HojaDetectada[];
  ilegibles: { archivo: string; motivo: string }[];
}

export type Confirmacion =
  | ({ clase: "directorio"; informe: InformeImportacionClientes })
  | ({ clase: "contabilidad"; cliente_id: string } & Importacion);
