# Guión de Prueba Rápida — Versión 2.4 (10 Minutos)

Este guión te permite comprobar en menos de 10 minutos todos los puntos reportados y corregidos en la versión v2.4.0, tanto en tu navegador desplegado como en tu equipo local.

---

## 1. Acceso a la aplicación (Nube y Local)

### A. En la nube (`https://carlos-cruz-contabilidad.vercel.app`)
1. Abre [carlos-cruz-contabilidad.vercel.app](https://carlos-cruz-contabilidad.vercel.app).
2. Si el servidor backend en Render estaba suspendido por inactividad (plan gratuito), verás el aviso claro:
   > *«Conectando con el servidor (si estaba inactivo, puede tardar hasta 45 segundos en despertar)…»*
3. En la pantalla inicial de instalación en la nube, escribe el código de instalación temporal `CC_CODIGO_INSTALACION` configurado en Render, o inicia sesión con tus credenciales.
4. **Verificación:** Ya no sale error 405. La sesión entra al Tablero de trabajo.

### B. En tu equipo local
1. Si olvidas tu usuario o contraseña en tu equipo, haz doble clic en `restablecer_acceso.bat` en la raíz de la carpeta.
2. Abre la app en local y pulsa **«Crear su acceso»**; define el usuario y contraseña que prefieras.

---

## 2. Clientes: Edición rápida del nombre y panel lateral

1. Ve a **Clientes** y entra al expediente de cualquier cliente (por ejemplo, *Farmacia Naturista Antares* o *María Elena*).
2. **Edición directa en 3 segundos:** Haz clic directamente sobre el nombre del cliente en el título principal. Escribe un cambio y pulsa `Enter` o el botón de guardar (✓). Verás que se actualiza en el acto con opción de «Deshacer».
3. **Panel lateral sin salir del expediente:** En la esquina superior derecha de la ficha, pulsa el botón **«Editar cliente»**.
   - Se despliega el panel lateral derecho con todos los campos (NIT, sigla, régimen, ubicación, socios con aportes y porcentaje, honorarios y notas del contador).
   - Modifica cualquier dato y pulsa **«Guardar cambios»**. La pantalla se actualiza de inmediato sin recargar.

---

## 3. Contabilidad: Subida inmediata y cambio de mes

1. En la pestaña **Contabilidad** del cliente:
   - Suelta un archivo de Excel o nómina en la zona de subida.
   - El sistema calcula inmediatamente con las respuestas sugeridas y muestra el balance y los estados financieros.
2. **Cambio de mes / periodo:** Usa el selector de periodos para alternar entre meses. Los estados financieros e indicadores se actualizan en el acto.

---

## 4. Excel Completo: Descarga con «EF formato contador» y «Cuentas T»

1. En el expediente del cliente, pulsa el botón **«Excel»** (Descargar libro completo).
2. Abre el archivo `.xlsx` descargado en Microsoft Excel.
3. **Comprobación de hojas:**
   - Hoja **«EF formato contador»**: contiene exactamente el formato de dos columnas que utiliza el contador, con fórmulas en vivo y sumas cuadradas.
   - Hoja **«Cuentas T»**: contiene el esquema gráfico de Libro Mayor en T con Debe, Haber y Saldo para cada cuenta activa.
   - Ambas hojas existen y son idénticas tanto si acabas de calcular el periodo como si descargas un periodo guardado meses atrás.

---

## 5. Renta: Entrada Universal para cualquier persona

1. Entra a la sección **Renta⁰³** en el menú principal.
2. Verás la nueva zona destacada: **«Suelte el reporte de exógena de cualquier persona»**.
3. Arrastra el archivo Excel o PDF de la DIAN de una persona natural (aunque NO esté registrada como cliente de contabilidad).
4. El sistema:
   - Extrae el NIT y nombre del encabezado.
   - Si no existe en la base de datos, la registra automáticamente como contribuyente de renta (persona natural).
   - Abre de inmediato su borrador del Formulario 210.

---

## 6. Renta Confiable: Protección contra cifras falsas (Casos A y B)

### Caso A (Exógena legible)
- Los patrimonios, deudas e ingresos se asignan con precisión a las casillas del Formulario 210.
- El resultado concuerda exactamente con la declaración oficial presentada (Saldo a favor $5.000).

### Caso B (Fotos giradas o lectura con baja confianza)
- El sistema **NUNCA inventa cifras falsas ni impuestos astronómicos**.
- Si los datos leídos no cuadran con los 5 topes del reporte de la DIAN o contienen líneas dudosas:
  - El sistema muestra el estado **«Borrador incompleto — Cálculo bloqueado por seguridad»**.
  - Lista exactamente los motivos (ej. diferencia entre suma de líneas y topes).
  - Permite corregir o digitar en limpio los 5 topes y líneas clave con la imagen al lado.

---

## 7. Diseño y Contraste Legible

1. En la esquina superior derecha, cambia entre modo **Claro** y modo **Oscuro**.
2. En modo claro, las franjas de cabecera ya no son oscuras; mantienen un fondo claro armónico con relación de contraste superior a 17:1 (muy por encima del estándar accesible de 4,5:1).
3. Todo el texto es nítido y legible en ambos modos.
