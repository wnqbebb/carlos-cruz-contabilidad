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

Cada año gravable tiene dos archivos en `data/renta/`; la aplicación no inventa ninguno.

1. **Parámetros** — copie `parametros_ag2025.json` como `parametros_ag2026.json` y cambie, con su norma:
   - la UVT del año gravable (resolución de la DIAN de finales del año anterior) y la de sanciones;
   - el **componente inflacionario** (decreto de mediados del año siguiente; para 2025 fue el Decreto 898 de 2026);
   - el **calendario** de personas naturales por los dos últimos dígitos del NIT (decreto de plazos);
   - cualquier tope, tarifa o límite que haya cambiado una reforma tributaria.
2. **Formulario** — si la DIAN prescribe un 210 nuevo, copie `210_ag2025.json` como `210_ag2026.json` y ajuste la
   numeración y las fórmulas según el instructivo oficial. Si sigue vigente el mismo, copie el archivo igual.
3. Cambie `ANIO_ACTUAL` en `backend/app/renta/servicio.py` (año gravable que se declara ese año).
4. Agregue pruebas con valores calculados a mano en `backend/tests/test_renta_calculo.py`.
5. Lo que no se pueda confirmar va a `docs/v23/SUPUESTOS_RENTA.md`.

**Lector de fotos (Tesseract).** `iniciar.bat` lo deja listo la primera vez con `scripts/preparar_ocr.ps1`
(copia el programa a `datos_app/tesseract` y descarga los idiomas a `datos_app/tessdata`); `empaquetar/construir.bat`
lo mete dentro del `.exe`. Si falta, la renta sigue funcionando con PDF y Excel.

## Seguridad (detalle en `docs/SEGURIDAD.md`)

- **Una vez al mes**, `scripts\seguridad.bat`, o revise el resultado de GitHub Actions. Corre pip-audit, npm audit,
  bandit, semgrep, gitleaks y las pruebas de seguridad. Dependabot propone las actualizaciones.
- **Si cambia la contraseña de la base en Supabase**: escriba de nuevo la línea `DATABASE_URL=` en `backend/.env`
  y abra la aplicación. La nueva pasa sola al Administrador de credenciales y reemplaza a la anterior.
- **Si la base se pasa a otro computador**:
  - las copias cifradas de `respaldos/` solo se abren en el equipo que las hizo, así que lleve también el
    `carloscruz.db`;
  - si la verificación en dos pasos estaba activa, el primer ingreso pide un código de recuperación en lugar del
    código del teléfono. Después se puede activar de nuevo desde Sistema.
- **Copias aisladas de prueba**: siempre con su propio `CC_ENV`, como lo hace `scripts/copia_aislada.sh`. Una
  instancia sin `CC_ENV` lee `backend/.env` y es, para todo efecto, la instalación real.
