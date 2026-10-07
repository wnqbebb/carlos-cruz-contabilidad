# Carlos Cruz — Contabilidad que cuadra

Mini-SaaS contable para Colombia. El contador sube los Excel de un cliente y
obtiene, al instante, balance de prueba, ajustes, hoja de trabajo, balance
definitivo con cierre, estados financieros completos (ESF, resultados, cambios
en el patrimonio, flujo de efectivo, notas e indicadores), kardex de inventario
y nómina liquidada — todo descargable en Excel y en PDF listo para firmar.

Pensado para llevar **decenas de miles de clientes** en un mismo directorio, con
su historia contable completa y a un buscador de distancia.

## Lo que lo distingue

**Las cuentas cuadran al peso.** Ningún importe pasa jamás por un `float`:

- el motor calcula con `decimal.Decimal`;
- la base los guarda como `NUMERIC(20,2)` en Postgres y como texto decimal en
  SQLite (ver `backend/app/esquema.py`);
- la API los transporta como **cadena** decimal, no como número JSON
  (ver `backend/app/exactitud.py`, que explica por qué);
- el navegador los formatea y los suma manipulando texto con `BigInt`
  (ver `frontend/src/formato.ts`).

Una prueba recorre **toda** la respuesta del cálculo y falla si encuentra un solo
float: `test_la_respuesta_del_calculo_no_contiene_ni_un_float`.

**Sugerencias que se sustentan en datos.** El sistema avisa de descuadres,
periodos sin cerrar, huecos en la secuencia, atrasos según la periodicidad
pactada, rachas de pérdidas, endeudamiento alto, capital suscrito sin pagar y
deterioro patrimonial. Cada aviso trae el dato exacto que lo origina. Lo que no
puede sustentar, no lo dice: por eso calcula el *turno* DIAN por el último
dígito del NIT, pero no inventa fechas de vencimiento, que las fija un decreto
cada año.

## Arrancar

**Windows:** doble clic en `iniciar.bat` → <http://localhost:8000>

Funciona de inmediato con base local, sin internet y sin configurar nada.

| Quiero… | Ver |
|---|---|
| Instalarlo en el computador de un cliente | [docs/INSTALAR_EN_EL_CLIENTE.md](docs/INSTALAR_EN_EL_CLIENTE.md) |
| Conseguir las credenciales de Supabase | [docs/GUIA_CREDENCIALES.md](docs/GUIA_CREDENCIALES.md) |
| Publicarlo en internet | [docs/DESPLIEGUE.md](docs/DESPLIEGUE.md) |
| Usarlo (para el contador) | [docs/MANUAL_USUARIO.md](docs/MANUAL_USUARIO.md) |

```bash
# desarrollo
py -3.12 -m venv .venv && .venv/Scripts/pip install -r backend/requirements.txt
.venv/Scripts/python backend/sembrar.py                 # base + primer cliente
.venv/Scripts/python -m pytest backend/tests            # 83 pruebas
.venv/Scripts/python -m uvicorn app.main:app --app-dir backend --port 8000
cd frontend && npm install && npm run dev               # :5173, con proxy a :8000
npm run build                                           # compila a frontend/dist
npx tsc --noEmit                                        # revisa tipos
```

## Pantallas

| Ruta | Qué hace |
|---|---|
| `/` | Tablero: cifras de la cartera y lo que pide atención hoy |
| `/clientes` | Directorio paginado, con búsqueda e importación masiva desde Excel |
| `/clientes/:id` | Ficha: resumen, periodos, libro diario y datos del cliente |
| `/trabajo` | Subir archivos → revisar y mapear → resultados |
| `/parametros` | SMMLV, auxilio de transporte y aportes por año |

`Ctrl + K` abre el buscador desde cualquier pantalla. Todo responde en móvil: en
pantalla pequeña el menú lateral se convierte en barra inferior y las tablas en
tarjetas.

## Estructura

```
backend/app/
  api/            rutas HTTP: sistema, clientes, trabajo, analisis
  repositorio/    acceso a datos: clientes, periodos, alias, sesiones, parametros
  importadores/   lector, detector, plantilla, cuenta_t, hoja_trabajo, aportes,
                  nomina, estados_existentes, clientes_excel (carga masiva)
  contabilidad/   puc, mayor, ajustes, cierre, estados, validaciones, reportes
  inventario/     kardex (promedio ponderado / PEPS, lotes, vencimientos, conteo)
  nomina/         parametros, calculo, asiento, auditoria
  inteligencia/   sugerencias (reglas sobre los datos guardados)
  exportar/       excel, pdf, plantilla (oficial + demo)
  esquema.py      tablas, portables entre Postgres y SQLite
  exactitud.py    serialización sin floats — leer antes de tocar importes
  motor.py        orquestador    config.py entorno    db.py conexión
  main.py         aplicación FastAPI    sembrar.py datos iniciales

supabase/migraciones/   001_esquema.sql · 002_seguridad.sql (RLS)
data/                   puc.json, parametros_legales.json, empresa_fanant.json
docs/                   DESPLIEGUE.md, MANUAL_USUARIO.md, PROMPT.md (especificación),
                        ANALISIS_FUENTES.md, SUPUESTOS.md, fuentes/
frontend/src/
  componentes/    ui (sistema de diseño), Marco, Buscador, Marca, Grafica,
                  Reporte, CuentasT, Alertas
  paginas/        Tablero, Clientes, ClienteFicha, ClienteEditor, Trabajo,
                  Inicio, VistaPrevia, Resultados, Parametros
  formato.ts      formateo y suma exactos sobre texto — no usar Number() con dinero
  api.ts · tipos.ts · index.css (tokens de diseño)
```

## El Excel que entrega

Un solo libro de ~12 hojas, no 18 sueltas:

- **Portada** con la ficha del cliente, las cifras clave, las verificaciones y
  un índice con enlaces a cada hoja.
- **Estados financieros**: los cuatro en una sola hoja, uno debajo del otro,
  como los revisa un contador.
- **Balances**: prueba, ajustado, asiento de cierre y definitivo juntos.
- **Inventario**: saldos, vencimientos, conteo físico y kardex en la misma hoja.
- Los totales son **fórmulas de Excel**, no números pegados: se puede auditar de
  dónde sale cada suma.
- Color con significado: tinta en cabeceras, lima en totales, verde y rojo solo
  para «cuadra» y «no cuadra».

Se descarga desde el cálculo en vivo **y desde un periodo ya guardado**, sin
volver a subir los archivos. Una prueba comprueba que los dos caminos producen
el mismo libro al peso.

## Diseño

Papel muy claro, tinta casi negra, reglas finas de 1 px y un solo acento ácido
que marca lo que hay que hacer. Tres familias: **Archivo** para titulares,
**Inter** para la interfaz y **JetBrains Mono** para etiquetas y cifras, con
numeración tabular para que las columnas de dinero no bailen.

Los colores de señal están **comprobados con un validador**: el par verde/rojo
de utilidad y pérdida separa ΔE 10,5 bajo deuteranopía, y todos superan 4,5:1 de
contraste sobre blanco. El verde anterior fallaba esa prueba: era
indistinguible del rojo para un contador daltónico.

## Base legal

PUC Decreto 2650/1993 · NIIF Decreto 2420/2015 · jornada máxima Ley 2101/2021.
Los parámetros laborales de cada año los carga el contador: el sistema no los
inventa.
