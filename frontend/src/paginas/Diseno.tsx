import { Download, Plus } from "lucide-react";
import { colorCliente } from "../colorCliente";
import { Cabecera } from "../componentes/Marco";
import { useEffect, useMemo, useState, type ReactNode } from "react";
import { LEMA, Logotipo, Monograma } from "../componentes/Marca";
import { cmp, sumar } from "../formato";
import {
  BotonAcento,
  BotonFantasma,
  BotonPrimario,
  CarpetaVacia,
  Cifra,
  EsferaCliente,
  EsqueletoExpedientes,
  EstadoError,
  EtiquetaSeccion,
  Expediente,
  InsigniaEstado,
  Interruptor,
  MetaEncabezado,
  TablaContable,
  TituloPagina,
  avisoSaldoContrario,
  type EstadoInsignia,
  type FilaContable,
  useAvisos,
} from "../ui";

/**
 * /diseno — catálogo vivo del sistema (Fase 2 del spec).
 * Uso interno: no aparece en la navegación. Las cifras son de muestra y están
 * marcadas como tales; los totales se suman con aritmética exacta de texto.
 */

const COLORES = [
  "papel", "hoja", "hoja-2", "tinta", "tinta-2", "grafito", "gris",
  "azul", "azul-tinta", "azul-suave", "rojo", "rojo-cartel", "rojo-suave", "ambar", "ambar-suave",
  "esfera-1", "esfera-2", "esfera-3", "esfera-4", "esfera-5", "esfera-6",
];

const TIPOS: [string, string, string][] = [
  ["t-display-xl", "display-xl", "CUADRA."],
  ["t-display", "display", "Tablero"],
  ["t-h1", "h1", "Estado de situación financiera"],
  ["t-h2", "h2", "Gestión de periodos"],
  ["t-kpi", "kpi", "$ 2.666.661,49"],
  ["t-body", "body", "Débitos = Créditos. El periodo de enero está listo para firmar."],
  ["t-small", "small", "Descuadre de $ 50.000 en el comprobante CE-014."],
  ["t-meta", "meta", "01 • Resumen — Corte 31 ene 2025"],
  ["t-tabla", "tabla", "110505  Caja general  1.234.475,72"],
];

const NITS: [string, string][] = [
  ["900100158", "Droguería Ejemplo S.A.S."],
  ["900123456", "Distribuciones del Valle S.A.S."],
  ["805004321", "Ferretería La 14 Ltda."],
  ["1115066789", "María Gladys García"],
  ["901555222", "Panadería El Trigal"],
  ["830099887", "Transportes Guacarí"],
];

/** Balance de prueba de muestra. Cada cifra es texto; nada pasa por float. */
const MUESTRA: { codigo: string; nombre: string; naturaleza: "D" | "C"; debito: string; credito: string }[] = [
  { codigo: "1", nombre: "Activo", naturaleza: "D", debito: "38409022.21", credito: "0" },
  { codigo: "11", nombre: "Efectivo y equivalentes", naturaleza: "D", debito: "31697600.00", credito: "0" },
  { codigo: "1105", nombre: "Caja", naturaleza: "D", debito: "1234475.72", credito: "0" },
  { codigo: "110505", nombre: "Caja general", naturaleza: "D", debito: "1234475.72", credito: "0" },
  { codigo: "1110", nombre: "Bancos", naturaleza: "D", debito: "30463124.28", credito: "0" },
  { codigo: "1435", nombre: "Mercancías no fabricadas por la empresa", naturaleza: "D", debito: "4771000.00", credito: "0" },
  { codigo: "1524", nombre: "Equipo de oficina", naturaleza: "D", debito: "2000000.00", credito: "0" },
  { codigo: "1592", nombre: "Depreciación acumulada", naturaleza: "C", debito: "0", credito: "59577.79" },
  { codigo: "2", nombre: "Pasivo", naturaleza: "C", debito: "0", credito: "5742360.72" },
  { codigo: "2205", nombre: "Proveedores nacionales", naturaleza: "C", debito: "0", credito: "5629360.72" },
  { codigo: "2365", nombre: "Retención en la fuente", naturaleza: "C", debito: "0", credito: "128000.00" },
  { codigo: "2408", nombre: "IVA por pagar", naturaleza: "C", debito: "15000.00", credito: "0" },
  { codigo: "3", nombre: "Patrimonio", naturaleza: "C", debito: "0", credito: "29991200.00" },
  { codigo: "4", nombre: "Ingresos", naturaleza: "C", debito: "0", credito: "11000000.00" },
  { codigo: "5", nombre: "Gastos", naturaleza: "D", debito: "4035538.51", credito: "0" },
  { codigo: "6", nombre: "Costos de venta", naturaleza: "D", debito: "4289000.00", credito: "0" },
];

function Bloque({ indice, titulo, children, nota }: { indice: number; titulo: string; children: ReactNode; nota?: ReactNode }) {
  return (
    <section className="border-t border-linea pt-6">
      <div className="flex flex-wrap items-baseline justify-between gap-3">
        <EtiquetaSeccion indice={indice}>{titulo}</EtiquetaSeccion>
        {nota && <p className="t-small max-w-xl text-gris">{nota}</p>}
      </div>
      <div className="mt-6">{children}</div>
    </section>
  );
}

function Muestra({ nombre }: { nombre: string }) {
  const [valor, setValor] = useState("");
  useEffect(() => {
    setValor(getComputedStyle(document.documentElement).getPropertyValue(`--${nombre}`).trim().toUpperCase());
  }, [nombre]);
  return (
    <div className="min-w-0">
      <div className="h-16 rounded-control border border-linea" style={{ background: `var(--${nombre})` }} />
      <p className="codigo mt-2 truncate text-[12px] text-tinta">--{nombre}</p>
      <p className="codigo truncate text-[11px] text-gris">{valor}</p>
    </div>
  );
}

/** Ocho NIT distintos para ver el color de cliente (8.3). */
const MUESTRAS_CLIENTE = ["900100158", "900123456", "805004321", "900555111", "811222333", "890300279", "900777111", "1112223334"];

export function Diseno() {
  const avisar = useAvisos();
  const [vista, setVista] = useState<"expedientes" | "tabla">("expedientes");
  const [anio, setAnio] = useState<"2025" | "2026">("2026");
  const [periodo, setPeriodo] = useState<"mensual" | "trimestral" | "anual">("mensual");
  const [cifra, setCifra] = useState("2666661.49");
  const [cargando, setCargando] = useState(false);

  const filas: FilaContable[] = useMemo(
    () =>
      MUESTRA.map((m) => ({
        codigo: m.codigo,
        nombre: m.nombre,
        valores: { debito: m.debito, credito: m.credito },
        contraria: avisoSaldoContrario(m.naturaleza, m.debito, m.credito),
      })),
    [],
  );
  // Solo las cuentas de clase (un dígito) suman al total, como en el balance.
  const clases1 = MUESTRA.filter((m) => m.codigo.length === 1);
  const totalD = sumar(...clases1.map((m) => m.debito));
  const totalC = sumar(...clases1.map((m) => m.credito));

  return (
    <div className="space-y-14 pb-16">
      <Cabecera>
        <TituloPagina subtitulo="Cada componente de firma con todos sus estados. Si algo se ve distinto en otra pantalla, la fuente de verdad es esta página y styles/tokens.css.">
          Catálogo
        </TituloPagina>
      </Cabecera>

      <Bloque indice={0} titulo="Marca" nota="Monograma: «CC» en Geist 600 sobre tinta, con una cuenta T mínima debajo. Reglas en docs/diseno/MARCA.md.">
        <div className="flex flex-wrap items-end gap-10">
          <Monograma tamano={96} />
          <Monograma tamano={40} />
          <Monograma tamano={24} />
          <Logotipo />
          <p className="t-display text-tinta">{LEMA}</p>
        </div>
      </Bloque>

      <Bloque indice={1} titulo="Color" nota="Sin verde: lo positivo es tinta con ▲ o azul. El azul sólido aparece una sola vez por vista.">
        <div className="grid grid-cols-3 gap-4 sm:grid-cols-5 escritorio:grid-cols-7">
          {COLORES.map((c) => <Muestra key={c} nombre={c} />)}
        </div>
      </Bloque>

      <Bloque indice={2} titulo="Tipografía" nota="Geist Sans y Geist Mono, autoalojadas. Cifras en Sans con números tabulares.">
        <div className="material-hoja divide-y divide-linea">
          {TIPOS.map(([clase, nombre, ejemplo]) => (
            <div key={clase} className="grid gap-2 px-5 py-4 escritorio:grid-cols-[140px_1fr] escritorio:items-baseline">
              <span className="t-meta text-gris">{nombre}</span>
              <span className={`${clase} recortar text-tinta`}>{ejemplo}</span>
            </div>
          ))}
        </div>
      </Bloque>

      <Bloque indice={3} titulo="Materiales" nota="Solo cinco. El cristal necesita algo detrás: aquí, una esfera.">
        <div className="grid gap-6 sm:grid-cols-2 escritorio:grid-cols-5">
          <div className="material-hoja grid h-36 place-items-center t-small text-grafito">Hoja</div>
          <div className="material-expediente grid h-36 place-items-center t-small">Expediente</div>
          <div className="material-hundido grid h-36 place-items-center t-small text-grafito">Hundido</div>
          <div className="relative grid h-36 place-items-center overflow-hidden rounded-hoja">
            <div aria-hidden className="absolute -left-10 -top-16">
              <EsferaCliente nit="900100158" tamano={240} deriva={false} />
            </div>
            <div className="material-cristal relative grid h-24 w-[80%] place-items-center rounded-hoja t-small text-tinta">Cristal</div>
          </div>
          <div className="material-hoja brillo-cuadra grid h-36 place-items-center t-small text-azul">Brillo «Cuadra»</div>
        </div>
      </Bloque>

      <Bloque indice={4} titulo="Expediente" nota="Pase el cursor: la pestaña sube 4 px, la carpeta gira -0,6° y la flecha avanza.">
        <div className="grid gap-8 escritorio:grid-cols-12">
          <Expediente
            className="escritorio:col-span-7"
            etiqueta="01 • Resultado"
            a="/diseno"
            etiquetaAccesible="Resultado del periodo de muestra"
          >
            <p className="t-meta text-sobre-tinta-2">Utilidad neta · enero 2025 · muestra</p>
            <div className="mt-3 text-sobre-tinta">
              <Cifra valor={cifra} tamano="display" odometro encajar />
            </div>
            <div className="mt-8 grid gap-4 border-t border-sobre-tinta/15 pt-4 sm:grid-cols-3">
              {[
                ["Ingresos", "11000000"],
                ["Gastos", "8339538.51"],
                ["Margen", null],
              ].map(([t, v]) => (
                <div key={t as string} className="min-w-0">
                  <p className="text-sobre-tinta">
                    {v ? <Cifra valor={v} tamano="h2" /> : <span className="t-h2 cifras">24,2 %</span>}
                  </p>
                  <p className="t-meta mt-1 text-sobre-tinta-2">{t}</p>
                </div>
              ))}
            </div>
          </Expediente>
          <div className="grid gap-8 escritorio:col-span-5">
            <Expediente variante="papel" etiqueta="FANANT — 001" titulo="Droguería Ejemplo S.A.S." a="/diseno">
              <div className="flex items-center gap-3">
                <EsferaCliente nit="900100158" tamano={56} nombre="Droguería Ejemplo S.A.S." />
                <div className="min-w-0">
                  <p className="codigo text-[13px] text-tinta">NIT 900.100.158-9</p>
                  <p className="t-small text-gris">Guacarí, Valle del Cauca · Mensual</p>
                </div>
              </div>
            </Expediente>
            <Expediente variante="papel" flecha={false} titulo="Sin flecha, sin enlace">
              <p className="t-small">Variante papel estática: para agrupar contenido sin acción.</p>
            </Expediente>
          </div>
        </div>
      </Bloque>

      <Bloque indice={5} titulo="EsferaCliente" nota="Generada del NIT: el mismo NIT da siempre la misma esfera. A 240 px deriva lentamente.">
        <div className="flex flex-wrap items-end gap-10">
          <EsferaCliente nit="900100158" tamano={240} nombre="Droguería Ejemplo S.A.S." />
          <div className="grid grid-cols-3 gap-6">
            {NITS.map(([nit, nombre]) => (
              <div key={nit} className="flex flex-col items-center gap-2 text-center">
                <EsferaCliente nit={nit} nombre={nombre} tamano={56} />
                <span className="codigo text-[11px] text-gris">{nit}</span>
              </div>
            ))}
          </div>
          <div className="flex items-center gap-3">
            {NITS.map(([nit, nombre]) => <EsferaCliente key={nit} nit={nit} nombre={nombre} tamano={32} />)}
          </div>
        </div>
      </Bloque>

      <Bloque
        indice={5}
        titulo="Color de cliente"
        nota="Sacado de la esfera, en OKLCH (8.3): tono L 0,55 · profundo L 0,28 · velo · texto ajustado a 4,5:1. Nunca a menos de 20° del rojo. Arriba en claro, abajo en oscuro."
      >
        <div className="grid gap-4 sm:grid-cols-2 escritorio:grid-cols-4">
          {MUESTRAS_CLIENTE.map((nit) => {
            const c = colorCliente(nit);
            return (
              <div key={nit} data-cliente-color="" style={c.vars as React.CSSProperties} className="overflow-hidden rounded-hoja border border-linea">
                {(["c", "o"] as const).map((m) => (
                  <div key={m} className="space-y-2 p-4" style={{ background: m === "c" ? "var(--muestra-clara)" : "var(--muestra-oscura)" }}>
                    <div className="flex items-center gap-3">
                      <EsferaCliente nit={nit} tamano={32} />
                      <span className="codigo text-[11px]" style={{ color: `var(--cliente-texto-${m})` }}>
                        {nit} · {Math.round(c.tono)}° · {(m === "c" ? c.contrasteClaro : c.contrasteOscuro).toFixed(1)}:1
                      </span>
                    </div>
                    <div className="flex gap-1.5">
                      {["tono", "profundo", "velo", "texto"].map((k) => (
                        <span
                          key={k}
                          title={`--cliente-${k}`}
                          className="h-6 flex-1 rounded-chip border border-linea"
                          style={{ background: `var(--cliente-${k}-${m})` }}
                        />
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            );
          })}
        </div>
      </Bloque>

      <Bloque indice={6} titulo="Encabezados">
        <div className="space-y-6">
          <div className="flex flex-wrap gap-3">
            <EtiquetaSeccion indice={1}>Resumen</EtiquetaSeccion>
            <EtiquetaSeccion indice={2}>Periodos</EtiquetaSeccion>
            <EtiquetaSeccion indice="005">Estados financieros</EtiquetaSeccion>
          </div>
          <MetaEncabezado
            columnas={["Carlos Cruz — Contador Público", "T.P. 103028-T", "Índice 01 — Tablero", "Corte 31 ene 2025"]}
          />
        </div>
      </Bloque>

      <Bloque indice={7} titulo="Interruptor" nota="Flechas del teclado, Inicio y Fin. La píldora se desliza con Flip.">
        <div className="flex flex-wrap items-center gap-6">
          <Interruptor
            etiqueta="Vista de clientes"
            valor={vista}
            onCambio={setVista}
            opciones={[{ valor: "expedientes", texto: "Expedientes" }, { valor: "tabla", texto: "Tabla" }]}
          />
          <Interruptor
            etiqueta="Año de parámetros"
            valor={anio}
            onCambio={setAnio}
            opciones={[{ valor: "2025", texto: "2025" }, { valor: "2026", texto: "2026" }]}
          />
          <Interruptor
            etiqueta="Periodicidad"
            tamano="sm"
            valor={periodo}
            onCambio={setPeriodo}
            opciones={[
              { valor: "mensual", texto: "Mensual" },
              { valor: "trimestral", texto: "Trimestral" },
              { valor: "anual", texto: "Anual" },
            ]}
          />
        </div>
      </Bloque>

      <Bloque indice={8} titulo="Cifra" nota="Siempre exacta. Pérdida en rojo con ▼; en estados financieros, entre paréntesis.">
        <div className="material-hoja grid gap-x-10 gap-y-8 p-6 escritorio:grid-cols-2">
          <div><p className="t-meta text-gris">Positiva con indicador</p><Cifra valor="2666661.49" tamano="kpi" indicador /></div>
          <div><p className="t-meta text-gris">Pérdida con indicador</p><Cifra valor="-1234475.72" tamano="kpi" indicador /></div>
          <div><p className="t-meta text-gris">Estado financiero</p><Cifra valor="-1234475.72" tamano="kpi" parentesis simbolo={false} /></div>
          <div>
            <p className="t-meta text-gris">Odómetro</p>
            <Cifra valor={cifra} tamano="kpi" odometro />
            <div className="mt-3 flex gap-2">
              <BotonFantasma compacto onClick={() => setCifra((c) => (c === "2666661.49" ? "3108204.06" : "2666661.49"))}>
                Cambiar valor
              </BotonFantasma>
            </div>
          </div>
        </div>
      </Bloque>

      <Bloque indice={9} titulo="Insignia">
        <div className="flex flex-wrap gap-3">
          {(["cuadra", "descuadre", "por-cerrar", "cerrado", "activo", "inactivo", "archivado"] as EstadoInsignia[]).map((e) => (
            <InsigniaEstado key={e} estado={e} />
          ))}
          <InsigniaEstado estado="descuadre">Descuadre de $ 50.000 en CE-014</InsigniaEstado>
        </div>
      </Bloque>

      <Bloque indice={10} titulo="Botones y enlaces" nota="Un solo BotonAcento por vista: la acción principal.">
        <div className="space-y-6">
          <div className="flex flex-wrap items-center gap-3">
            <BotonPrimario flecha>Ver estados financieros</BotonPrimario>
            <BotonAcento icono={<Plus size={18} strokeWidth={1.5} aria-hidden />}>Nuevo periodo</BotonAcento>
            <BotonFantasma icono={<Download size={18} strokeWidth={1.5} aria-hidden />}>Descargar Excel</BotonFantasma>
            <BotonPrimario cargando={cargando} onClick={() => { setCargando(true); setTimeout(() => setCargando(false), 1600); }}>
              {cargando ? "Calculando" : "Calcular"}
            </BotonPrimario>
            <BotonPrimario disabled>Deshabilitado</BotonPrimario>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <BotonPrimario compacto flecha>Compacto</BotonPrimario>
            <BotonFantasma compacto>Fantasma compacto</BotonFantasma>
          </div>
          <p className="t-body text-grafito">
            Las fechas de vencimiento salen del calendario tributario que
            usted carga cada año.
          </p>
        </div>
      </Bloque>

      <Bloque indice={12} titulo="Estados" nota="Carga con la forma real, vacío con carpeta, error con detalle plegable y aviso en tira de papel.">
        <div className="grid gap-8 escritorio:grid-cols-2">
          <div className="space-y-3">
            <p className="t-meta text-gris">Cargando</p>
            <EsqueletoExpedientes cuantos={2} />
          </div>
          <div className="space-y-3">
            <p className="t-meta text-gris">Vacío</p>
            <div className="material-hoja">
              <CarpetaVacia titulo="Aún no hay expedientes" accion={<BotonPrimario flecha>Crear el primer cliente</BotonPrimario>}>
                Agregue fichas una a una o cargue todo su directorio desde un Excel.
              </CarpetaVacia>
            </div>
          </div>
          <div className="space-y-3 escritorio:col-span-2">
            <p className="t-meta text-gris">Error</p>
            <EstadoError
              titulo="No se pudo abrir el directorio"
              detalle="HTTP 503 · connection to server at db.example.supabase.co failed: timeout expired"
              onReintentar={() => avisar("Reintentando…")}
            />
          </div>
          <div className="flex flex-wrap gap-3 escritorio:col-span-2">
            <BotonFantasma onClick={() => avisar("Parámetros de 2026 guardados.")}>Mostrar aviso</BotonFantasma>
            <BotonFantasma onClick={() => avisar("Descuadre de $ 50.000 en el comprobante CE-014.", "rojo")}>Mostrar aviso de error</BotonFantasma>
          </div>
        </div>
      </Bloque>

      <Bloque indice={11} titulo="TablaContable" nota="Datos de muestra. Punto rojo: saldo contrario a la naturaleza de la cuenta.">
        <TablaContable
          titulo="Balance de prueba · muestra"
          columnas={[
            { clave: "debito", titulo: "Débito", grupo: "Saldo" },
            { clave: "credito", titulo: "Crédito", grupo: "Saldo" },
          ]}
          filas={filas}
          totales={{ debito: totalD, credito: totalC }}
          cuadra={cmp(totalD, totalC) === 0}
          alturaMaxima="520px"
        />
      </Bloque>
    </div>
  );
}
