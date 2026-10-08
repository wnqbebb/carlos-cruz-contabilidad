# Mantenimiento

## Cuando cambia el año: valores legales de nómina

Los valores legales (salario mínimo, auxilio de transporte, UVT, jornada) viven en
`data/parametros_legales.json`, un bloque por año, cada uno con su fuente oficial.
No se editan desde la aplicación. Si el año en curso no está, el Tablero muestra
«Faltan los valores legales de AAAA» y la nómina de ese año no se calcula.

Para agregar un año:

1. Cuando el Gobierno publique los decretos de diciembre (salario mínimo y auxilio de
   transporte) y la DIAN la resolución de la UVT, copie el bloque del año anterior en
   `data/parametros_legales.json` con la clave del año nuevo.
2. Cambie `smmlv`, `aux_transporte` y `uvt` por los valores oficiales, y `_fuente` por
   los números de los decretos y la resolución.
3. Revise `jornada_tramos` (Ley 2101 de 2021: desde el 15 de julio de 2026 la jornada
   máxima es 42 horas; no hay más tramos) y las tasas, que solo cambian si cambia la ley.
4. Corra las pruebas: `cd backend && ../.venv/Scripts/python -m pytest -q`.
   Agregue el año a `tests/test_parametros_legales.py` con los valores esperados.
5. Vuelva a empaquetar o reinicie la aplicación.

## Cuando cambia el año: declaración de renta

Ver `data/renta/` (formulario 210 y parámetros tributarios por año gravable) y
`docs/v23/SUPUESTOS_RENTA.md`.
