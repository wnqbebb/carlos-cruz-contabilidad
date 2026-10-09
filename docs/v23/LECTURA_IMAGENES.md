# Lectura de las 5 imágenes de renta (versión anonimizada)

Las imágenes reales y su lectura completa están solo en `privado/renta/` (fuera de git). Aquí no hay nombres,
cédulas ni notas manuscritas. Las entidades se generalizan (BANCO A, BANCO B…).

## Lo que enseñan las fotos (y la aplicación debe resolver sola)

| Imagen | Qué es | Dificultad |
|---|---|---|
| 1 | Página 1 del reporte de exógena del **Contribuyente B**, fotografiada | Texto **encimado** (impresa dos veces), filas **resaltadas en rosa**, notas **a mano** arriba (incluida una cadena con aspecto de **contraseña**) y abajo («SF: …»), y en el margen texto de un **recetario médico** ajeno al reporte |
| 2 | Página 2 del mismo reporte, **girada 90°** | Muchas filas resaltadas y encimadas; la línea «Tope 6: Responsable IVA» |
| 3 | Página 3, **girada 90°**, casi vacía | Un **dedo** tapa parte; un papel ajeno en la esquina; patrimonio bruto del año anterior |
| 4 | Reporte de exógena del **Contribuyente A**, legible | Perspectiva leve, dedo en el borde, **nota manuscrita con aspecto de contraseña** junto al nombre |
| 5 | **Formulario 210 AG 2025** del Contribuyente A, presentado | El resultado contra el que se comprueba la aplicación |

## Caso A (imágenes 4 y 5)

Transcripción completa en [`backend/tests/renta/caso_a.json`](../../backend/tests/renta/caso_a.json).

**Topes del encabezado:** 1 · Ingresos 117.144 · 2 · Patrimonio 4.600.014 · 3 · Consumo TC 14.536.332 ·
4 · Movimiento 93.121.224 · 5 · Compras 7.763.109.

**Columnas:** entidad · titular (el contribuyente, o «NO REGISTRA NO» en 2 filas) · detalle · valor · uso sugerido
(`R29`, `R30`, `R58`, `R132`, «Tope N»).

**Comprobaciones hechas a mano sobre la imagen:**

| Grupo | Filas | Suma | Encabezado |
|---|---|---|---|
| R29 patrimonio (saldos y fondos) | 4 | 4.600.014 | Tope 2 = 4.600.014 ✓ |
| R30 deudas | 6 | 52.201.487 | — |
| Consumos con tarjeta | 4 | 14.536.332 | Tope 3 = 14.536.332 ✓ |
| Compras con factura electrónica | 1 | 7.763.109 | Tope 5 = 7.763.109 ✓ |
| R58 rendimientos | 1 | 117.144 | Tope 1 = 117.144 ✓ |
| R132 retención | 1 | 4.920 | — |
| Movimientos en cuentas | 3 | **93.121.227** | Tope 4 = **93.121.224** |

**El dígito del Tope 4:** con zoom, los cuatro valores están impresos tal cual (920.233; 7.612.546; 84.588.448;
93.121.224). No hay dígito mal leído: la diferencia de **3 pesos es del propio reporte**. La aplicación trata una
diferencia tan pequeña como redondeo de la fuente (aviso informativo), no como error de lectura. Las dos filas de
fondos de inversión colectiva marcadas «Tope 4» (750.000 y 5.350.000) no forman parte del total del encabezado.

**Formulario 210 presentado (imagen 5):** 28 = 48.000 · 29 = 4.600.000 · 30 = 52.201.000 · 31 = 0 ·
58 = 117.000 · 59 = 65.000 · 61 = 52.000 · 73 = 52.000 · 74 = 65.400.000 · 77 = 32.800.000 · 78 = 32.600.000 ·
90 = 32.600.000 · 91 = 32.652.000 · 92 = 48.000 · 93 = 32.604.000 · 97 = 32.604.000 · 111 = 32.604.000 ·
impuesto 0 · 132 = 5.000 · 137 = 5.000.

La casilla 59 (65.000) es el componente inflacionario: 117.144 × 55,43 % (Decreto 898 de 2026) = 64.933 → 65.000.

## Caso B (imágenes 1, 2 y 3)

Solo en `privado/`. Lo que la aplicación debe encontrar:
- Topes: ingresos 82.535.904 · patrimonio 226.543.936 · consumo con tarjeta 19.977.892 · movimiento 125.053.184 ·
  compras 12.910.068 · Tope 6: responsable de IVA.
- Obligado por ingresos, patrimonio, consignaciones y por ser responsable de IVA.
- Saldo a favor del año anterior (6.275.000) y patrimonio bruto declarado el año anterior (página 3).
- Una sola pregunta para los ≈ 12 pagos de una misma empresa por «documentos soporte».
- La nota manuscrita con aspecto de contraseña **no se guarda**; se avisa.
