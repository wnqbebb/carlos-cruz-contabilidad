# Datos reales: carpeta `privado/` (fuera de git)

Desde la v2.2.0 el repositorio **no versiona datos reales de clientes**. Todo lo
que tenía cédulas, NIT o documentos de un cliente real se movió a `privado/`,
que está en `.gitignore`. La carpeta existe solo en el equipo del contador.

| En `privado/` | Antes en | Qué es |
|---|---|---|
| `fuentes/` | `docs/fuentes/` | Archivos reales de FANANT (contabilidad, nómina, estados, estatutos, cartas, cuentas de cobro) |
| `empresa_fanant.json` | `data/empresa_fanant.json` | Ficha de FANANT con socios y cédulas; la usan `backend/sembrar.py` y las pruebas de FANANT |
| `respaldos/` | `docs/v22/respaldo-*.json` | Respaldo del cierre de FANANT enero 2025 |
| `PROMPT.md`, `docs/ANALISIS_FUENTES.md` | raíz y `docs/` | Encargo original y análisis de las fuentes, con datos de personas |
| `capturas/` | `docs/diseno/capturas/`, `docs/v22/capturas/`, `docs/informe/` | Capturas de pantalla tomadas con los datos de FANANT |

Rutas: `CC_PRIVADO` cambia la carpeta (por defecto `privado/` en la raíz); `CC_FUENTES` apunta a los archivos fuente (por defecto `privado/fuentes`).

## Qué pasa si `privado/` no está
- La aplicación funciona igual. El botón «Cargar sus archivos de ejemplo» de la ficha de FANANT no aparece, y `backend/sembrar.py` solo siembra los parámetros legales.
- Las pruebas que necesitan esos archivos **se saltan con un aviso** («Faltan los archivos reales de FANANT en privado/…»). El resto pasa: `pytest -rs` muestra cuáles se saltaron y por qué.
- Ni el ejecutable (`empaquetar/`) ni la imagen de Docker incluyen `privado/`.

## El historial de git (limpiado en la v2.3)
En la v2.3 se reescribió el historial con `git filter-repo`:
- se quitaron de todos los commits `docs/fuentes/`, `docs/diseno/capturas/`, `docs/informe/`,
  `docs/v22/capturas/fase-*`, `docs/v22/respaldo-fanant-enero-2025.json`, `data/empresa_fanant.json`,
  `PROMPT.md` y `docs/ANALISIS_FUENTES.md`;
- en el resto se reemplazaron las cédulas y el NIT reales por `[CEDULA]` y `[NIT]`, y la cadena de conexión
  de la guía de credenciales por marcadores.

`gitleaks` sobre todo el historial queda sin hallazgos. La copia completa de antes de limpiar está en
`privado/respaldo-repo/` (fuera de git). Las capturas de `docs/v22/capturas/final/` se conservan porque solo
muestran clientes de demostración.

Quien tenga otra copia del repositorio debe clonarlo de nuevo: los identificadores de los commits cambiaron.
