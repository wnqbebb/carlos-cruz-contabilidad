# Fase 0 · Por qué los cambios de diseño no se veían

Medido el 06-oct-2026 sobre el código y el servidor en marcha, no supuesto.

## Las causas, de la que más pesa a la que menos

### 1. Hay 387 colores escritos a mano que ignoran los tokens — **es la causa principal**

Cada vez que se cambió la paleta, se cambiaron las variables de `index.css`.
Pero las pantallas no usan esas variables: usan clases de color fijas de
Tailwind directamente en el JSX.

| Clase | Usos |
|---|---|
| `text-slate-*` | 193 |
| `bg-slate-*` | 35 |
| `border-slate-*` | 33 |
| `text-indigo-*` / `bg-indigo-*` / `border-indigo-*` | 48 |
| `text-rose-*` / `bg-rose-*` / `border-rose-*` | 27 |
| `shadow-indigo-*`, `from-indigo-*`, `text-blue-*`, `*-amber-*` … | 51 |
| **Total** | **387**, en 9 archivos |

Archivos: `Marco.tsx`, `ui.tsx`, `Tablero.tsx`, `ClienteFicha.tsx`, `Inicio.tsx`,
`Resultados.tsx`, `PanelMetricas.tsx`, `ResultadoGuardado.tsx`, `Reporte.tsx`.

Además: 13 colores hex o `rgb()` sueltos en componentes y 7 degradados
(`bg-gradient-to-*`) en tarjetas.

**Consecuencia:** cambiar un token no cambia casi nada en pantalla. Por eso «el
resultado visual casi no cambia». Se arregla en la Fase 1 sacando esas clases y
haciendo que el `lint:diseno` impida que vuelvan.

### 2. Otro agente reescribió el diseño entre una sesión y otra

Durante esta conversación el sistema avisó varias veces de archivos «modificados
en disco» que yo no había tocado (`index.css`, `ui.tsx`, `Tablero.tsx`,
`Marco.tsx`, `Inicio.tsx`…). Entre dos turnos el sistema de diseño pasó de
Archivo + índigo a **Plus Jakarta Sans + azul cristal**, y volvió el verde que
se había quitado a pedido suyo. Ese mismo cambio dejó tres llamadas rotas en
`Inicio.tsx` (`api.importarEjemplo`, `api.importarDemo`, `descargas.plantilla()`)
que impedían cargar los ejemplos.

**Consecuencia:** dos agentes escribiendo en la misma carpeta se pisan; lo que
uno arregla el otro lo revierte. **Mientras duren estas fases, conviene que
solo un agente trabaje sobre `sistema-contable-fanant`.**

### 3. `iniciar.bat` nunca recompila si ya existe una compilación

```bat
if not exist "frontend\dist\index.html" ( ...compilar... )
```

Si alguien edita `frontend/src/` y no ejecuta `npm run build`, `iniciar.bat`
sigue sirviendo la compilación anterior. El servidor que está corriendo ahora
sí sirve la última (`index-By5BLG9L.js`, 16:12), pero cualquier cambio sin
compilar es invisible desde `iniciar.bat`.

### 4. El navegador puede quedarse con el `index.html` viejo

El servidor entrega `index.html` **sin cabecera `Cache-Control`**, solo con
`Last-Modified` y `ETag`. Sin esa cabecera el navegador aplica caché heurística
y puede mostrar un `index.html` anterior que apunta al paquete JS anterior.
(Los `.js` con hash sí deben cachearse; el `index.html` no.)

### 5. El ejecutable `.exe` congela el diseño del mediodía

`empaquetar/salida/CarlosCruz/CarlosCruz.exe` se compiló a las 12:25 con el
paquete `index-DXJPHUWN.js`. Quien abra el `.exe` ve el diseño de ese momento,
no el actual. Hay que recompilarlo al final (Fase 9).

### 6. `index.css` acumuló capas que compiten

374 líneas con 11 clases de superficie para el mismo papel (`glass-panel`,
`glass-pill`, `glass-dock`, `vidrio`, `vidrio-tinta`, `lamina`, cuatro
`capsule-*`, `hover-lift` definido dos veces), 9 alias que redirigen `lima` y
`verde` a índigo, y animaciones huérfanas de un componente ya borrado
(`aurora`, `vagar`, `flotar`, `grano`). Variables con nombre engañoso:
`--color-papel` vale `#ffffff` y `--color-lienzo` es un `rgba` translúcido.

## Cuál era «la» causa real

La 1 explica por qué **cambiar la paleta no cambiaba la pantalla**. La 2
explica por qué **lo que sí cambiaba luego volvía atrás**. Las 3, 4 y 5 pueden
haber hecho que usted viera una versión vieja según cómo abrió la aplicación
(`iniciar.bat`, el navegador o el `.exe`); no puedo saber cuál usó, así que la
Fase 1 corrige las tres.

## Qué se corrige en la Fase 1 para que no vuelva a pasar

| Causa | Corrección |
|---|---|
| 1 | Quitar las 387 clases; `tokens.css` como única fuente; `npm run lint:diseno` falla si reaparecen |
| 2 | Pedirle a usted un solo agente por carpeta durante las fases |
| 3 | `iniciar.bat` recompila si `src/` es más nuevo que `dist/` |
| 4 | `Cache-Control: no-cache` en `index.html` (los `.js` con hash siguen cacheados) |
| 5 | Recompilar el `.exe` en la Fase 9 |
| 6 | `index.css` se reemplaza por `tokens.css` + una base corta; se borra lo huérfano |
| todas | Pie de página con `v2.1.0 · build <hash> · <fecha-hora>` para confirmar a simple vista qué versión se está viendo |

## De dónde salen hoy los estilos

| Fuente | Qué aporta | Destino |
|---|---|---|
| `index.html` | Google Fonts: Plus Jakarta Sans, Inter, JetBrains Mono | Se reemplazan por Geist autoalojada |
| `src/index.css` `@theme` | Variables de color y fuentes de Tailwind v4 | Pasan a `src/styles/tokens.css` |
| `src/index.css` resto | 11 superficies, alias, animaciones | Se reducen a los 5 materiales del spec |
| JSX (9 archivos) | 387 clases de paleta fija | Se eliminan |
| JSX | 13 hex/`rgb()` sueltos, 7 degradados | Se eliminan |
| No hay `tailwind.config` | Tailwind v4 se configura desde CSS con `@theme` | `tokens.css` será ese `@theme` |

Línea base capturada en `capturas/fase-0/` (cinco pantallas, escritorio y
móvil). Las cuatro imágenes `actual-0X` que menciona el spec no venían
adjuntas, así que se tomaron directamente de la aplicación en marcha.
