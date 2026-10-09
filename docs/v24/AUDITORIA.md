# Auditoría Completa del Sistema · Carlos Cruz v2.4

> Fecha: 9 de octubre de 2026  
> Referencias: `PROMPT_V24.md`, commit `a48cf1e` (v2.2.0) y commit `909ed6d` (v2.3.0).

---

## 1. DESPLIEGUE Y ACCESO

### 1.1 Estado Actual del Despliegue
| Componente | Plataforma | URL / Host | Estado Técnico |
|---|---|---|---|
| **Frontend** | Vercel | `https://carlos-cruz-contabilidad.vercel.app` | Desplegado (Vite SPA estática). |
| **Backend** | Ninguno en la nube / Local | Local: `http://127.0.0.1:8000` | No hay servicio backend activo en Render. |
| **Base de Datos** | Supabase Postgres | `aws-0-sa-east-1.pooler.supabase.com:6543` | 14 tablas base + migraciones 005 y 006 aplicadas. |

### 1.2 Causa Raíz del Error 405 en Vercel
1. **Reescritura Estática Ciega:** En `frontend/vercel.json`, la regla de reescritura es:
   ```json
   { "source": "/(.*)", "destination": "/index.html" }
   ```
   Cualquier petición a `/api/*` (como `POST /api/sesion`) es enviada internamente por Vercel hacia el archivo estático `/index.html`.
2. **Rechazo de Método HTTP:** Los servidores de borde de Vercel solo admiten métodos `GET` y `HEAD` sobre archivos estáticos. Al recibir un `POST /api/sesion`, responden de inmediato con:
   ```http
   HTTP/1.1 405 Method Not Allowed
   ```
3. **Ausencia de `VITE_API` y Backend en la Nube:** El bundle del frontend se compiló con `BASE = ""`. Las llamadas HTTP van al propio dominio de Vercel (`carlos-cruz-contabilidad.vercel.app`), donde no existe ningún servidor FastAPI.
4. **Barrera de Cookies entre Dominios (`SameSite=Lax`):** Si simplemente se configurara `VITE_API = https://carloscruz-api.onrender.com` sin proxy, las cookies de sesión con `SameSite=Lax` se considerarían de terceros y el navegador no las enviaría en peticiones cruzadas `fetch`.

**Solución Arquitectónica:**
Configurar en `frontend/vercel.json` una regla de proxy inverso hacia el backend en Render **antes** del comodín SPA:
```json
{
  "rewrites": [
    { "source": "/api/(.*)", "destination": "https://carloscruz-api.onrender.com/api/$1" },
    { "source": "/(.*)", "destination": "/index.html" }
  ]
}
```
Esto garantiza:
* Las llamadas a `/api/*` son del mismo origen para el navegador (primer nivel).
* La cookie `carloscruz_sesion` viaja con `SameSite=Lax` y `Secure`.
* Sin fricciones de CORS ni rechazos de métodos HTTP.

---

## 2. MATRIZ DE REGRESIONES: v2.2.0 vs v2.3.0

Auditoría detallada comparando el árbol de `a48cf1e` contra `HEAD`:

| Función / Elemento | v2.2.0 (`a48cf1e`) | v2.3.0 (`HEAD`) | ¿Se perdió? | Diagnóstico y Ubicación |
|---|---|---|---|---|
| **Edición en cabecera de cliente** | `EnLinea.tsx` activo en `ClienteFicha.tsx` (razón social, sigla, municipio, honorarios). | Desconectado. El componente `EnLinea.tsx` quedó huérfano sin un solo import. | **SÍ** | La cabecera en `Expediente.tsx` muestra solo texto plano. Obliga a navegar a `ClienteEditor.tsx`. |
| **Panel lateral de edición rápida** | No existía (formulario separado). | No existe. | **Falta** | Requiere crearse en `Expediente.tsx` para editar sin salir de la vista. |
| **Excel cálculo nuevo (`/exportar/{sid}/excel`)** | 14 hojas, incluye «EF formato contador». | 14 hojas, incluye «EF formato contador». | No | Funciona sólo en memoria inmediata. |
| **Excel periodo guardado (`/periodos/{id}/excel`)** | 13 hojas. Omitía «EF formato contador» si faltaba `mayor_ajustado`. | Omitía «EF formato contador» porque el docstring exigía cálculo en vivo. | **SÍ** | Falta persistir o reconstruir `mayor_ajustado` en el resultado guardado. |
| **Hoja Cuentas T en Excel** | No existía en el Excel descargable. | No existía en el Excel descargable. | **Falta** | El componente web `CuentasT.tsx` existe, pero nunca se exportaba a Excel. |
| **Pantalla Trabajar** | Pantalla independiente `/trabajo` con 3 pasos (subir, mapear, resultados). | Integrada dentro de `Expediente.tsx` (pestaña Contabilidad y drop zone). | Reemplazo | Simplificada, pero sin previsualización de supuestos clave. |
| **Pantalla Parámetros** | Pantalla independiente `/parametros` (SMMLV, auxilio, porcentajes). | Fusionada en `/sistema` modal. Valores legales embebidos en código. | Reemplazo | Aceptable según spec v2.3. |
| **Gráficas del cliente** | Gráfica de evolución simple de ingresos/utilidad. | Indicadores con diales/anillos más densos. | Degeneración | Gráficas confusas; el usuario pide barras y líneas limpias. |
| **Puerta de entrada en Renta** | No existía módulo Renta. | Solo lista personas naturales previamente registradas en clientes. | **Grave** | No permite soltar una exógena de un tercero para crear contribuyente al vuelo. |

---

## 3. AUDITORÍA DE RECORRIDOS REALES DE USUARIO

| Recorrido | Clics requeridos | Tiempo promedio | Errores / Bloqueos identificados |
|---|---|---|---|
| **(a) Crear cliente subiendo archivos** | 4 clics | ~18 s | Si el archivo no tiene NIT evidente, pide reescribir. El cálculo en vivo no muestra de inmediato los supuestos aplicados. |
| **(b) Ver estados financieros y cambiar mes** | 2 clics | ~3 s | Fluido en local; en Vercel bloqueado por falta de backend. |
| **(c) Editar nombre del cliente** | 5 clics (v2.3) vs 1 clic (v2.2) | 22 s vs 4 s | En v2.3 requiere ir a «Datos» → «Editar ficha» → scroll al campo → guardar → volver. En v2.2 era un clic directo sobre el texto con `EnLinea`. |
| **(d) Descargar Excel completo** | 1 clic | ~2 s | El archivo descargado del periodo guardado **no trae la hoja EF formato contador** ni **Cuentas T**. |
| **(e) Renta de persona no registrada** | Imposible | Bloqueo total | `Renta.tsx` no tiene drop zone ni botón «Subir exógena». Exige registrar a la persona primero como cliente contable ficticio. |
| **(f) Renta Casos A y B** | 3 clics (Caso A) / Indeterminado (Caso B) | 16 s (A) / Error (B) | Caso A cuadra. Caso B produce texto distorsionado e impone un impuesto de $289M sin validación de topes. |

---

## 4. AUDITORÍA TÉCNICA DEL MÓDULO RENTA

### 4.1 Evidencia en Fotos Reales (`privado/renta/imagenes/`)
1. **Caso A (`4.png` y `5.png`):**
   * Reporte exógena legible con leve inclinación.
   * Cifras extraídas: Patrimonio $4.600.014, Deudas $52.201.487, Tope 3 $14.536.332, Tope 5 $7.763.109.
   * Resultado: Cuadra con el Formulario 210 presentado ante la DIAN (casillas 29, 30, 58, 74, 91).
2. **Caso B (`1.png`, `2.png`, `3.png`):**
   * Hoja impresa dos veces (doble impresión con desfase milimétrico), girada 90°, márgenes con notas manuscritas y recetario médico.
   * Topes impresos en el encabezado:
     - Tope 1 (Ingresos): $82.535.904
     - Tope 2 (Patrimonio): $226.543.936
     - Tope 3 (Consumo TC): $19.977.892
     - Tope 4 (Movimiento bancario): $125.053.184
     - Tope 5 (Compras): $12.910.068
   * **Falla Crítica de la Lógica Actual:**
     - El OCR leyó líneas distorsionadas asignándolas a «trabajo personal».
     - Sumó $627.024.000 en rentas de trabajo, superando por más de 7 veces el **Tope 1 ($82.535.904)** que el mismo OCR leyó en el encabezado.
     - Puso patrimonio en $0, ignorando que el **Tope 2 marcaba $226.543.936**.
     - La función `calcular()` en `backend/app/renta/servicio.py` no detuvo el proceso y generó un impuesto de **$289.321.000** con sanción por extemporaneidad de **$16.891.000**.

### 4.2 Causa del Descuadre y Reglas de Bloqueo
* **Causa:** `backend/app/renta/servicio.py` calcula liquidación tributaria aunque existan advertencias graves de lectura o inconsistencias aritméticas entre la suma de líneas y los topes declarados.
* **Solución Obligatoria:** Si la suma de renglones supera el tope del encabezado (fuera de tolerancia explicada), si hay líneas con baja confianza afectando casillas, o si existen preguntas clave sin confirmar por el contador, el sistema **DEBE BLOQUEAR** la cifra final de impuesto y mostrar:
  ```
  ESTADO: Borrador incompleto
  Motivo: La suma de líneas ($627.024.000) excede el Tope 1 del reporte ($82.535.904).
  Acción requerida: Revisar filas dudosas o digitar los 5 topes directamente.
  ```

---

## 5. EXPORTACIONES (EXCEL Y PDF)

1. **Excel de Periodo Guardado (`backend/app/exportar/excel.py`):**
   * En `_resultado_guardado(periodo_id)` se recupera el JSON guardado en `resultados`.
   * En `excel.libro_completo()` la línea 997 verifica: `if res.get("mayor_ajustado"):`.
   * En cálculos en vivo, `mayor_ajustado` está presente en memoria; en resultados guardados se serializa como `reportes.mayor_balances`, provocando que la condición falle y la hoja **«EF formato contador»** se omita.
   * **Corrección:** Adaptar `hoja_formato_contador` para que opere tanto sobre `mayor_ajustado` como reconstruido a partir del balance ajustado o cuentas de mayor guardadas.
2. **Cuentas T en Excel:**
   * Nunca fue agregada al generador openpyxl.
   * **Corrección:** Crear la hoja `Cuentas T` en `excel.py`, formateada en dos columnas clásicas (Débito / Crédito) agrupadas por cuenta mayor.

---

## 6. DISEÑO Y CONTRASTES VISUALES

### 6.1 El Error de la Cabecera Oscura en Modo Claro
* En `frontend/src/styles/tokens.css` (línea 250):
  ```css
  [data-seccion="renta"] {
    --cabecera-fondo: var(--banda-taller); /* #24221f */
    --acento: var(--grafito);
    --sobre-acento: var(--sobre-tinta);
  }
  ```
* En modo claro, `--banda-taller` es `#24221f` (un gris casi negro).
* El componente `TituloPagina` renderiza el texto con `text-tinta` (`#141414`).
* **Contraste resultante:** `#141414` sobre `#24221f` = **1.16:1**.
* El estándar WCAG AA exige **4.50:1**. El texto queda negro sobre fondo negro, haciendo la interfaz completamente ilegible.

**Corrección:**
En modo claro, `--cabecera-fondo` para Renta debe usar un fondo suave y distinguible (por ejemplo, `--hoja` o un tinte sutil acorde al índice 03), reservando tonos oscuros únicamente cuando `:root[data-tema="oscuro"]` esté activo.

---

## 7. SEGURIDAD EN LA NUBE vs WINDOWS

* `backend/app/seguridad/secretos.py` asume la disponibilidad de Windows DPAPI (`keyring` backend de Windows).
* En Linux o Docker (entorno de Render):
  - `keyring` devuelve `KeyringFail`.
  - El fallback `_leer_reserva()` escribe un archivo binario dentro de `datos_app/secretos/`, pero en entornos efímeros (contenedores) este disco puede perderse en redeploys si no hay persistencia montada.
* **Solución limpia para Render/Linux:**
  - Si una variable existe en `os.environ` (ej. `DATABASE_URL`, `CLAVE_SESION`), el backend debe leerla directamente del entorno con máxima prioridad, sin intentar migrarla o borrarla de archivos inexistentes.
  - El uso de DPAPI/Keyring debe activarse únicamente cuando el sistema operativo es Windows y no se está ejecutando dentro de un contenedor Docker.

---

## 8. DATOS REALES Y CLIENTES EN LA BASE DE DATOS

1. **Supabase:**
   * La tabla `clientes` contiene 7 empresas legítimas (Farmacia Antares, Panadería La Espiga Dorada, Clínica Sonrisa del Valle, Transportes Río Cauca, María Elena Rojas, Fernando Silva PYME, Fernando Silva).
   * No contiene al contador como cliente.
2. **SQLite Local:**
   * Contiene 3 clientes: Antares, Droguería La Economía y `CRUZ CAICEDO CARLOS ARTURO` (NIT 19228087, tipo persona natural).
   * **Causa:** El script de pruebas o sembrado local inicial insertó al contador como cliente natural para pruebas de renta de la Fase 5.
   * **Corrección:** En el listado de Renta se debe permitir distinguir entre clientes contables habituales y contribuyentes exclusivos de renta, y no registrar datos del contador como cliente contable salvo que él mismo lo decida.

---

## 9. PLAN DE ACCIÓN Y VERIFICACIÓN POR BLOQUES

1. **Bloque 1:** Reescritura proxy `/api/*` en `vercel.json`, configuración del servicio backend en Render / Docker con Tesseract español, y soporte de `restablecer_acceso.bat` y `CC_CODIGO_INSTALACION`.
2. **Bloque 2:** Bloqueo de renta no confiable (Borrador Incompleto ante descuadre de topes), zona de subida universal en Renta, y OCR asistido para casos difíciles.
3. **Bloque 3:** Restauración de `EnLinea` y panel lateral en `Expediente.tsx`, hojas «EF formato contador» y «Cuentas T» en el Excel del periodo guardado, y gráficas limpias de barras/líneas.
4. **Bloque 4:** Normalización de `--cabecera-fondo` en modo claro para contraste > 4.5:1 en todas las páginas.
5. **Bloque 5:** Higiene de tokens y comprobación final.
