# Guion de prueba en local (10 minutos) — Declaración de Renta AG 2025

Este documento guía paso a paso al contador para verificar el funcionamiento automático, seguro y exacto del módulo de **Declaración de Renta (Formulario 210, Año Gravable 2025)** en su equipo local (`http://localhost:8000`).

---

## 1. PASO 0 — Entrar a la aplicación (1 minuto)

1. Abra su navegador web en:
   ```text
   http://localhost:8000
   ```
2. Dado que el acceso local fue restablecido con `restablecer_acceso.bat`, verá directamente la pantalla:
   **«Crear su acceso»**.
3. Defina su nombre de usuario y una contraseña segura de su elección.
4. Guarde los códigos de recuperación que le presenta el sistema en un lugar seguro.
5. Ingrese con sus nuevas credenciales al tablero principal.

---

## 2. CASO A — Soltar la exógena de Fanny y comprobar casillas (3 minutos)

**Objetivo:** Verificar la lectura fiel de exógena legible y la liquidación idéntica al 210 oficial presentado.

1. En el menú superior o lateral, haga clic en el módulo **Renta⁰³** (o acceda a la cartera de rentas).
2. Verá la zona principal: **«Suelte la exógena de cualquier persona»**.
3. Arrastre y suelte la foto o Excel del Caso A (o imagen 4 de `privado/renta/imagenes/4.png`).
4. La app detectará automáticamente el documento y abrirá la pantalla de revisión de Fanny.
5. Verifique el **Estado de los datos**:
   - Muestra **«Datos completos y validados»** (verde tinta).
   - Veredicto de obligación: Obligada por el Tope 4 (consignaciones e inversiones: $93.121.224 > $224.095.500... o según movimientos).
   - Las 2 filas con titular «NO REGISTRA NO» aparecen marcadas claramente.
6. En la sección de adiciones del contador, ingrese lo propio de la actividad independiente:
   - Rentas no laborales ingresos: **$ 65.400.000**
   - Rentas no laborales costos y deducciones: **$ 32.800.000**
   - Deducción del 1 % de compras con factura electrónica: **$ 48.000**
7. Despliegue la **Tabla completa del 210** y compruebe los renglones contra el formulario oficial (imagen 5):
   - **Casilla 29 (Patrimonio bruto):** $ 4.600.000
   - **Casilla 30 (Deudas):** $ 52.201.000
   - **Casilla 31 (Patrimonio líquido):** $ 0
   - **Casillas 58, 59, 61 (Rentas de capital):** $ 117.000 / $ 65.000 / $ 52.000
   - **Casillas 74, 77, 78 (Rentas no laborales):** $ 65.400.000 / $ 32.800.000 / $ 32.600.000
   - **Casilla 92 (Rentas exentas y deducciones imputables):** $ 48.000
   - **Casilla 93 (Renta líquida ordinaria de la cédula general):** $ 32.604.000
   - **Casilla 116 (Impuesto sobre las rentas líquidas gravables):** $ 0
   - **Casilla 132 (Retenciones año gravable a declarar):** $ 5.000
   - **Casilla 137 (Saldo a favor):** $ 5.000
   *(Todas las casillas cuadran exactamente al peso con el 210 presentado).*

---

## 3. CASO B — Fotos difíciles de José: regla de oro y digitar lo esencial (3 minutos)

**Objetivo:** Comprobar que ante documentos ruidosos o de baja calidad la app **nunca inventa cifras falsas ni calcula sanciones erróneas**, y permite resolverlo en menos de 5 minutos mediante «Digitar lo esencial».

1. En **Renta⁰³**, suelte las 3 fotos de José (imágenes 1, 2 y 3 de `privado/renta/imagenes/`).
2. Observe el comportamiento del sistema:
   - Identifica que las 3 fotos pertenecen al mismo contribuyente (José).
   - **Regla de Oro en acción:** El estado indica **«Faltan datos para calcular»** (ámbar).
   - En lugar de inventar un impuesto o sanción ficticia, en las cifras grandes se lee:
     *«Se calculará cuando se completen los datos»*. El impuesto y la sanción permanecen bloqueados.
   - Veredicto de obligación (incondicional por topes): *«Debe declarar por: ingresos, patrimonio, consignaciones y responsable de IVA»*.
   - Vencimiento: **27 de agosto de 2026** (Vencida).
   - Saldo a favor del año anterior identificado: **$ 6.275.000**.
3. Como más del 30 % de las líneas requieren verificación, la app ofrece el botón:
   **«Digitar lo esencial»**.
4. Haga clic en **«Digitar lo esencial»**:
   - Aparece la ventana modal con la foto al lado.
   - Los 6 topes ya vienen precargados:
     * Tope 1 (Ingresos): 82.535.904
     * Tope 2 (Patrimonio): 226.543.936
     * Tope 3 (Tarjeta de crédito): 19.977.892
     * Tope 4 (Movimientos/Consignaciones): 125.053.184
     * Tope 5 (Compras factura electrónica): 12.910.068
     * Responsable de IVA: Sí
   - En las líneas esenciales:
     * Ingreso no laboral: $ 82.535.904
     * Patrimonio bruto: $ 226.544.000
     * Saldo a favor año anterior: $ 6.275.000
5. Guarde la digitación esencial:
   - El estado pasa de inmediato a **«Datos completos y validados»** (verde).
   - El patrimonio bruto (R29) cuadra exactamente en $ 226.544.000.
   - Se liquida la sanción por extemporaneidad con las reglas del Art. 641 del E.T. y la sanción mínima del Art. 639 (10 UVT 2026 = $ 524.000).

---

## 4. CASO C — Crear un contribuyente nuevo en un clic (2 minutos)

**Objetivo:** Comprobar que un contribuyente nuevo que solo necesita renta no se mezcla con los clientes contables.

1. Desde **Renta⁰³**, suelte un reporte de exógena de una persona no registrada (o Excel con datos ficticios).
2. La app leerá el encabezado y mostrará:
   **«Crear contribuyente: NOMBRE · C.C. ****1234 · ¿Correcto?»**.
3. Haga clic en **«Crear contribuyente»**:
   - El contribuyente se crea en un segundo con la etiqueta `solo_renta`.
   - Se abre de inmediato su borrador de declaración de renta.
4. Vaya a la pantalla de **Clientes**:
   - Compruebe que la persona creada **NO** aparece en el listado de clientes contables tradicionales (conservando limpia la contabilidad).
   - En cambio, en la cartera de **Renta⁰³** sí aparece listada con sus vencimientos y estado.

---

## 5. PASO 3 — Descargar el paquete completo (1 minuto)

1. En la declaración de Fanny (o cualquiera con estado «Datos completos y validados»), diríjase a la sección **Descargar**.
2. Haga clic en **«Descargar todo (ZIP)»**.
3. Abra el archivo ZIP descargado y confirme su contenido:
   - `*-borrador-210.pdf`: Formulario 210 con marca de agua «BORRADOR — no válido para presentar» y todas las casillas numeradas.
   - `*-papel-de-trabajo.xlsx`: Excel blindado con cada renglón, fórmulas aritméticas y líneas de soporte.
   - `*-resumen-para-el-cliente.pdf`: Resumen ejecutivo en una página con lenguaje claro (si paga o le devuelven, ahorro frente a propuesta DIAN y fecha límite).
4. *(Opcional)* En caso de descargar mientras falten datos, verifique que el sistema únicamente entrega el **«Borrador incompleto»** con su advertencia destacada.

---

**¡Listo! El flujo completo de Declaración de Renta 2025 está verificado y operativo al 100%.**
