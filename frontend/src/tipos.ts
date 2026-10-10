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
  /** El backend tiene archivos de muestra de este cliente en este equipo (solo en GET de un cliente). */
  archivos_de_muestra?: boolean;
  /* v2.2 · Fase 6: lo que traen estatutos, RUT y cámara de comercio. */
  tipo_sociedad: string;
  objeto_social: string;
  documento_constitucion: string;
  capital_autorizado: Monto;
  capital_pagado: Monto;
  numero_acciones: Monto;
  rep_legal_suplente_cc: string;
  revisor_fiscal: string;
  revisor_fiscal_tp: string;
  matricula_mercantil: string;
  fecha_renovacion: string | null;
  ciiu_secundarios: string;
  responsabilidades: string;
  /** Último periodo calculado (solo en el listado). */
  ultimo_periodo?: UltimoPeriodo | null;
}

export interface UltimoPeriodo {
  id: string;
  desde: string;
  hasta: string;
  estado: "calculado" | "cerrado" | "borrador";
  ingresos: Monto;
  utilidad: Monto;
  /** Utilidad / ingresos × 100, con un decimal. Nulo si no hubo ingresos. */
  margen: Monto | null;
  cuadra: boolean;
}

/** La ficha que se puede sacar de los documentos del cliente. */
export interface FichaExtraida {
  campos: Record<string, CampoDetectado>;
  conflictos: Record<string, CampoDetectado[]>;
  socios: Socio[];
  socios_origen: string;
  documentos: { archivo: string; tipo: string; nombre_tipo: string }[];
}

export interface ComparacionFicha {
  cambios: { campo: string; actual: string; nuevo: string; origen: string; confianza: string; conflicto: CampoDetectado[] }[];
  documentos: FichaExtraida["documentos"];
  socios: { actual: number; nuevo: Socio[]; origen: string } | null;
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
  /** Cuántas versiones anteriores guardadas tiene (viene con el listado del cliente). */
  versiones_n?: number;
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
  /** Nota de revisión del contador (A6). */
  nota?: string;
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

/** Una tarea sugerida del tablero (spec v2.2 · Fase 7). */
export interface Tarea {
  /** codigo:cliente_id — estable, para posponerla. */
  clave: string;
  codigo: string;
  prioridad: "critica" | "alta" | "media";
  cliente_id: string;
  razon_social: string;
  nit: string;
  /** Qué hacer, en pocas palabras. */
  que: string;
  titulo: string;
  /** Por qué: el dato exacto que la sustenta. */
  por_que: string;
  /** «informar»: solo avisa (p. ej. faltan los valores legales del año); no hay pantalla a donde ir. */
  accion: { tipo: "ir" | "subir" | "informar"; etiqueta: string; ruta?: string };
}

export interface MesTablero {
  mes: string;
  cerrados: number;
  abiertos: number;
  sin_contabilizar: number;
}

export interface Tablero {
  generado: string;
  hoy: string;
  indicadores: { clientes_activos: number; honorarios_mensuales: Monto; al_dia: number; atrasados: number };
  tareas: Tarea[];
  tareas_total: number;
  /** H13: la cartera mes a mes, contada en el servidor. */
  meses: MesTablero[];
  recientes: (Cliente & { estado_trabajo: "al_dia" | "atrasado"; ultimo_periodo: Periodo | null })[];
  actividad: (Actividad & { razon_social: string })[];
  clientes: ConteoClientes;
  trabajo: { periodos: number; cerrados: number; pendientes: number; descuadrados: number; ultimo_corte: string };
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
  /** La misma pregunta en varios bloques (v2.3 · B3): se responde una vez; cada bloque se puede responder aparte. */
  bloques?: { id: string; lugar: string; titulo: string; detalle: string }[];
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

/* ── el contador dueño de la aplicación (H18) ──────────────────────────── */
export interface Contador {
  nombre: string;
  nombre_corto: string;
  cargo: string;
  tarjeta_profesional: string;
  municipio: string;
  departamento: string;
}

/* ── estado del sistema ────────────────────────────────────────────────── */
/** Panel «Sistema» y estado de la conexión: nada técnico (v2.3 · Fase 2). */
export interface EstadoSistema {
  conectado: boolean;
  en_la_nube: boolean;
  version: string;
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
  /** La ficha completa que traen los documentos. */
  ficha: FichaExtraida;
  hojas: HojaDetectada[];
  ilegibles: { archivo: string; motivo: string }[];
}

export type Confirmacion =
  | ({ clase: "directorio"; informe: InformeImportacionClientes })
  | ({ clase: "contabilidad"; cliente_id: string } & Importacion);

/* ── declaración de renta, formulario 210 (v2.3 · Fase 5) ──────────────── */
export type EstadoRenta = "sin_informacion" | "borrador" | "revisada" | "presentada";

export interface LineaRenta {
  id: string;
  entidad: string;
  titular: string;
  detalle: string;
  valor: Monto;
  uso: string;
  renglon: number | null;
  tope: number | null;
  no_titular: boolean;
  confianza: number;
  resaltada: boolean;
  encimada: boolean;
  alternativas: Monto[];
  corregida: boolean;
  validada: boolean;
  confirmada: boolean;
  documento: string;
  pagina: number;
  fila: number;
  recorte: string;
  categoria: string;
  categoria_texto: string;
  motivo: string;
  conflicto: boolean;
  incluida: boolean;
}

export interface PreguntaRenta {
  id: string;
  texto: string;
  opciones: { id: string; texto: string }[];
  defecto: string;
  respuesta: string | null;
  detalle: string;
  lineas: string[];
}

export interface BeneficioRenta {
  id: string;
  texto: string;
  soporte: string;
  ahorro_hasta: Monto;
  maximo: Monto;
  valor: string | number | boolean | null;
}

export interface CasillaRenta {
  casilla: number;
  nombre: string;
  seccion: string;
  columna: string;
  formula: string;
  dian: Monto;
  optimizada: Monto;
  explicacion: string;
}

export interface ResultadoRenta {
  anio: number;
  incompleto?: boolean;
  motivos_incompleto?: string[];
  ofrecer_digitar_esencial?: boolean;
  porcentaje_por_verificar?: number;
  obligacion: {
    obligado: boolean;
    veredicto: string;
    motivos: { tope: string; nombre: string; valor: Monto | null; umbral: Monto | null; supera: boolean }[];
    norma: string;
  } | null;
  cifras: {
    neto: Monto | null;
    a_pagar: Monto | null;
    a_favor: Monto | null;
    ahorro: Monto;
    dian_neto: Monto | null;
    bloqueado?: boolean;
    incompleto?: boolean;
    motivos?: string[];
  };
  vencimiento: { fecha: string | null; dias: number | null; texto: string; vencida?: boolean };
  sancion: { meses: number; valor: Monto; texto: string } | null;
  casillas: CasillaRenta[];
  diferencias: { casilla: number; dian: Monto; optimizada: Monto; motivo: string }[];
  preguntas: PreguntaRenta[];
  beneficios: BeneficioRenta[];
  marcas: { tipo: string; texto: string; linea?: string; lineas?: string[] }[];
  lineas: LineaRenta[];
  manuales: { id: string; categoria: string; descripcion: string; valor: Monto }[];
  avisos: string[];
  validacion: { tope: number; nombre: string; estado: string; texto: string; suma: Monto; encabezado: Monto }[];
  anotaciones_a_mano: boolean;
  confianza_alta: number | null;
  documentos_faltantes: string[];
  maximo_1pct: Monto;
}

export interface DeclaracionRenta {
  id: string;
  cliente_id: string;
  anio: number;
  estado: EstadoRenta;
  presentada: { numero: string; fecha: string } | null;
  resultado: ResultadoRenta | null;
  categorias: Record<string, string>;
  manuales_categorias: string[];
  actualizado: string | null;
  versiones: { id: number; motivo: string; creado: string }[];
  contribuyente: { nombre: string; nit: string };
}

export interface FilaCarteraRenta {
  cliente_id: string;
  razon_social: string;
  nit: string;
  anio: number;
  estado: EstadoRenta;
  obligado: boolean | null;
  veredicto: string;
  motivos: string[];
  vencimiento: string | null;
  dias: number | null;
  vencimiento_texto: string;
  neto: Monto | null;
  ahorro: Monto | null;
}

/* ── «Datos del periodo»: editar dentro de la aplicación (rescate H7) ───── */
export type TablaDatos = "movimientos" | "ajustes" | "saldos_iniciales" | "inventario" | "conteo" | "activos_fijos" | "nomina";
export type FilaDatos = Record<string, string | number | boolean | null | undefined>;

export interface ProblemaDatos {
  tabla: string;
  fila?: number;
  campo?: string;
  comprobante?: string;
  mensaje: string;
}

export interface ValidacionDatos {
  errores: ProblemaDatos[];
  avisos: ProblemaDatos[];
  descuadres: { comprobante: string; debito: Monto; credito: Monto; diferencia: Monto }[];
  totales: { debito: Monto; credito: Monto; saldos_debito: Monto; saldos_credito: Monto };
  cuadra: boolean;
}

export interface ArchivoDelPeriodo {
  archivo: string;
  filas: number;
  tablas: Record<string, number>;
  debito: Monto;
}

export interface DatosPeriodo {
  periodo: Periodo;
  editable: boolean;
  motivo_bloqueo: string;
  tablas: Record<TablaDatos, FilaDatos[]>;
  validacion: ValidacionDatos;
  archivos: ArchivoDelPeriodo[];
  versiones: number;
  guardado?: boolean;
  resumen?: Record<string, Monto | number | null>;
}
