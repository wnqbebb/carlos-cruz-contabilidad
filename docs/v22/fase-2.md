# Fase 2 · Recuperar FANANT enero 2025 (H02)

**Resultado: recuperado y verificado. El cierre nuevo coincide centavo a centavo con el original.**

## Antes de tocar nada
1. **Respaldo** en `docs/v22/respaldo-fanant-enero-2025.json` (46 KB): ficha, periodo, resultado guardado, versiones y —leídos de la base en solo lectura, porque la API no los expone— **los 13 saldos del cierre original**.
2. **Ensayo completo en la copia aislada** (puerto 8001, SQLite desechable) antes de ejecutar en la base real:

| Ensayo | Saldos | Utilidad | ¿Coincide? |
|---|---|---|---|
| Con la causación de nómina aceptada | 13 | −2.857.975,72 | ✅ centavo a centavo |
| Con los ajustes por defecto | 11 | −1.234.475,72 | ❌ faltan 237005 y 2505; 238030 y 3610 distintos |

El ensayo confirmó lo que decía el informe: **el cierre original incluía la causación de nómina**.

## Ejecución en la base real (por la misma puerta que usa el contador, vía API)
1. `POST /api/periodos/{id}/reabrir` → el cierre de 13 saldos **quedó guardado en el historial** (versión 1, motivo «reapertura»), no se borró.
2. `POST /api/importar` con `CONTABILIDAD.xls` y `NOMINA__enero__2025.xlsx`. Periodo sugerido: 1 a 31 de enero de 2025 (del mes de la nómina «#002»). Hojas por defecto: hoja de trabajo, libro de aportes y nómina «#002».
3. `POST /api/calcular` con `decisiones: {"nomina_causacion": true}`.
4. Comparación automática contra los 13 saldos: **coincide**.
5. `POST /api/cierre/{sesion}` → cierre guardado.

Si no hubiera coincidido, el script restauraba la versión del historial y no cerraba nada.

## Estado final, leído de la base real

| Dato | Valor |
|---|---|
| Periodo | 2025-01-01 a 2025-01-31, **cerrado** |
| Activo | 37.144.505,00 |
| Pasivo | 2.202.480,72 |
| Patrimonio | 34.942.024,28 |
| Ingresos | 22.641,00 |
| Resultado | **−2.857.975,72** (pérdida) |
| Cuadra | ✅ |
| Cuentas | 23 |
| Libro diario | 25 movimientos · débitos 10.705.537,72 = créditos 10.705.537,72 |
| Cierre | 13 cuentas · **idéntico al original, cuenta por cuenta** |
| Historial | 2 versiones (reapertura con el cierre bueno · recálculo) |
| Bitácora | reabierto → archivos subidos → calculado → cerrado |
| Importaciones | `CONTABILIDAD.xls` (39.936 B) y `NOMINA__enero__2025.xlsx` (13.202 B), con su sha256 |

Las cifras de control del informe quedan confirmadas: caja 37.144.505 · capital 37.800.000 · pérdida 2.857.975,72.

## Lo que ya no puede volver a pasar
El mismo archivo vacío que causó el incidente hoy sería rechazado dos veces: por estar el periodo cerrado (409) y por no aportar cuentas (422). Y aunque se forzara, el estado anterior quedaría en el historial.
