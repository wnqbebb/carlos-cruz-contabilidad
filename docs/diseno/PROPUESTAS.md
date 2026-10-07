# Propuestas fuera del spec

Cosas que noté y que el spec no pide. No se implementan sin su visto bueno.

1. **Comprobar el build al abrir la app.** El pie ya muestra el hash; se podría avisar
   «Hay una versión nueva, recargue» si el `index.html` del servidor trae otro hash que
   el que está corriendo. Útil cuando el cliente deja la pestaña abierta días.
2. **Rojo de cartel más profundo.** ref-02 mide #BE1005; el spec usa #D7261E. Se dejó el
   del spec. Si quiere el de la referencia, es cambiar un token.
3. **Ejecutable (.exe).** El instalador congela la interfaz del día en que se empaqueta.
   Hay que reempaquetarlo al terminar la Fase 9, no antes.
4. **Tablero a escala de cartera.** `/api/tablero` no trae Activo/Pasivo/Patrimonio
   agregados ni el estado de cada mes (cerrado/abierto). Hoy la ecuación muestra el
   corte más reciente de los 8 clientes recientes y la tira deduce el estado del mes de
   esos 8 más el total de periodos abiertos. Con miles de clientes conviene que el
   backend entregue por mes: periodos cerrados, abiertos y clientes sin contabilizar.
   Es un cambio de endpoint, por eso no se hizo.
5. **URGENTE — un cálculo puede sobrescribir un periodo cerrado (pérdida de datos).**
   El 2026-10-06 a las 18:12 alguien subió un archivo para FANANT desde «Trabajar» y
   pulsó calcular. El archivo no traía cuentas (0) y el resultado reemplazó al de enero
   2025, que estaba **cerrado**: activo, pasivo y patrimonio quedaron en $ 0 y el sistema
   ahora alerta «patrimonio por debajo de la mitad del capital».
   Causa: `repositorio/periodos.py · guardar_resultado` borra y reemplaza el resultado
   sin mirar si el periodo está cerrado ni si el cálculo trae cuentas.
   Propuesta (lógica de negocio, requiere su visto bueno):
   - rechazar el guardado si el periodo está cerrado («Reábralo primero»);
   - rechazar un resultado con 0 cuentas;
   - guardar el resultado anterior antes de reemplazarlo (historial) para poder volver.
   Los datos de enero 2025 se recuperan volviendo a cargar los archivos originales de
   FANANT y calculando de nuevo.
