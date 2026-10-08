# Fase 9 · Cinco clientes históricos de demostración

Generador: `backend/demo/generar_historicos.py` (semilla fija). Archivos generados: `docs/demo/<cliente>/` (68 archivos, 1,1 MB, todo ficticio).
Capturas: `privado/capturas/v22/fase-9/` (claro y oscuro; 1440 y 390 px). Probado en la copia aislada; **no se tocó la base real** (se carga en la sección 4.5).

```
cd backend
python -m demo.generar_historicos --url http://127.0.0.1:8001            # los cinco
python -m demo.generar_historicos --url http://127.0.0.1:8001 --solo 1,3 # algunos
python -m demo.generar_historicos --url … --usuario … --clave …          # con inicio de sesión (4.2)
```

Cada cliente se carga **por la API, como lo haría el contador**: subir → identificar (o crear) → revisar el mapeo → calcular → cerrar, mes a mes. Si un cliente ya está cargado (mismo NIT), el generador se detiene y pide borrarlo primero.

## Los cinco clientes (enero 2025 – septiembre 2026)

| # | Cliente | Cómo llega | Estado final |
|---|---|---|---|
| 1 | PANADERÍA LA ESPIGA DORADA S.A.S. · Tuluá · NIT 901.482.317-5 | **Se crea subiendo sus estatutos (.docx) y su RUT (.pdf)** con la plantilla de enero; luego una plantilla oficial por mes: kardex de insumos (salidas a producción), nómina de 4 con aportes y prestaciones, IVA bimestral, retenciones, depreciación. Pico de diciembre (×1,8). | 21 meses cerrados, todos cuadran. Al día. |
| 2 | FERRETERÍA EL TORNILLO S.A.S. · Buga · NIT 901.536.208-4 | Igual que el 1 (estatutos + RUT). Ventas a crédito a tres constructoras con cartera que crece (se recauda el 75 %), proveedores a crédito, camioneta y estanterías que se deprecian. | Enero 2025–julio 2026 cerrados; **agosto 2026 calculado sin cerrar; septiembre sin subir**. |
| 3 | CLÍNICA DENTAL SONRISA DEL VALLE S.A.S. · Cali · NIT 901.611.459-7 | Un libro por mes con **CUENTAS T** y **HOJA DE TRABAJO** (la hoja aporta los saldos iniciales y la cuenta T el detalle, H07). Servicios de salud (particulares y aseguradoras a crédito), honorarios con retención del 11 %, arriendo con retención del 3,5 %. El contador confirma el mapeo la primera vez; después el sistema lo recuerda. | 20 meses cerrados; **septiembre 2026 calculado con un descuadre de $50.000** (un pago de honorarios mal digitado). |
| 4 | TRANSPORTES RÍO CAUCA S.A.S. · Palmira · NIT 901.394.772-6 | **Un solo CSV de libro diario** con los 21 meses, procesado mes a mes y cerrando cada uno. Dos tractocamiones, préstamo bancario con intereses y abonos, depreciación, préstamos del socio, retención que le practican los clientes. | 21 meses cerrados; meses con utilidad en 2025 y pérdida casi siempre; en agosto 2026 **el patrimonio cae por debajo del 50 % del capital** (causal de disolución). |
| 5 | MARÍA ELENA ROJAS · persona natural · Guacarí · C.C. 29.874.553-7 | **Registros auxiliares desordenados** de su finca (ventas y gastos por meses, encabezados en distinto orden y con otros nombres, títulos sin año, totales mezclados, filas vacías y en cero, un valor escrito «$ 1.250.000», una fecha copiada del mes anterior). Periodicidad **bimestral**. Las preguntas del archivo se responden con la opción por defecto. | 9 bimestres cerrados hasta junio 2026: **atrasada 3 meses**. |

Todos con `demo = true`, etiqueta **«Demostración»** y la nota «Cliente de demostración: todos los datos son ficticios…», que se ve en su ficha.

**Reproducible:** cargado dos veces en bases nuevas, los 68 archivos salieron con el mismo contenido celda por celda. Algunos pagos (planilla PILA, retenciones, IVA del bimestre, prima, cesantías e intereses) se toman del cierre del mes anterior que devuelve la aplicación, como haría el contador; con la misma versión de la aplicación, los archivos son idénticos.

**Nombres ficticios:** se cambiaron nombres de terceros que podían coincidir con empresas reales (un banco, un ingenio, una central de abastos, un supermercado) y NIT de terceros que eran de entidades reales.

## Borrar los clientes de demostración
- `GET /api/clientes/demostracion` · `POST /api/clientes/demostracion/eliminar`. El filtro `demo = true` va **en la misma sentencia de borrado**: un cliente real no puede caer ahí. Se borra también su rastro en la bitácora y queda una línea «Clientes de demostración eliminados».
- **Parámetros › Sistema › Clientes de demostración**: dice cuántos hay; el botón «Eliminar clientes de demostración» abre una confirmación con la lista de nombres. Si no hay ninguno, no hay botón (no queda un botón muerto).
- Probado en la interfaz: con FANANT y los cinco demos cargados, se borraron los cinco y **quedó solo FANANT**.

## Defectos de la aplicación que aparecieron con los demos (corregidos)
- **Textos de los estatutos de FANANT aplicados a cualquier cliente.** La causal de disolución decía «art. 38-6 de los estatutos… 18 meses (art. 39)», la distribución de utilidades «art. 33 / art. 34 estatutos» y la alerta E17 «el art. 28 de los estatutos». Ahora citan la norma según el tipo de sociedad (S.A.S.: Ley 1258 de 2008, art. 34 num. 7 y art. 35; S.A.: C. de Co. art. 457 y 458; Ltda.: art. 370) y piden confirmar en los estatutos del cliente. A una persona natural no se le propone reserva legal ni causal de disolución.
- **La plantilla CSV de clientes traía datos reales de FANANT** (NIT, correo, cédula de la representante) como fila de ejemplo: ahora son filas inventadas.
- **Atraso contado de más:** contaba el mes en curso («4 meses» el 8 de octubre con corte a junio). Ahora cuenta meses terminados y avisa «a partir de» la tolerancia, como dice su propio texto.
- **Persona natural:** la ficha ya no pide «representante legal» y en las firmas del PDF y del Excel firma ella como **Titular**. Si la ficha no trae contador, firma el contador de la aplicación (Parámetros).
- **La subida que crea un cliente** quedaba en la bitácora sin cliente: ahora se le asigna.
- **Socios con porcentaje «60%»** en la tabla de los estatutos quedaban en 0 %: se lee el signo.
- **21 periodos en la ficha** ensanchaban la página (la fila de meses no se desplazaba): corregido.
- **«Turno DIAN 9 De 10»** (mayúscula en cada palabra) → «9 de 10». Los nombres largos en «Expedientes recientes» se partían a mitad de palabra. Los periodos de varios meses se rotulan «Enero – febrero 2025».
- La columna «Laboratorio» del kardex solo aparece si algún producto la trae.

## Verificación
| Comprobación | Resultado |
|---|---|
| Pruebas del backend | ✅ 236 (7 nuevas en `tests/test_demo.py`: documentos generados → ficha completa con socios al 60/40 %; NIT ficticios; María Elena bimestral de punta a punta con la API; borrado que no toca clientes reales ni deja bitácora huérfana; causal de disolución por ley; atraso por meses terminados; firmas de persona natural y contador por defecto) |
| `tsc --noEmit` | ✅ limpio |
| `npm run lint:diseno` | ✅ 0 infracciones |
| `npm run build` | ✅ |
| Carga completa en la copia aislada | ✅ 91 periodos; todos cuadran salvo el descuadre intencional de la clínica |
| Recorrido (`frontend/scripts/flujo-fase9.mjs`) | ✅ Tablero (7 tareas: descuadre, causal de disolución, dos periodos sin cerrar, atraso, ficha incompleta, FANANT sin periodos), Clientes, las 6 pestañas de cada ficha, Parámetros; claro y oscuro, 1440 y 390 px; **sin errores de consola, sin desbordes**; descargas Excel, PDF, libro diario y mayor de un periodo (200); borrado desde la interfaz |
| Registro del servidor | ✅ sin errores |
