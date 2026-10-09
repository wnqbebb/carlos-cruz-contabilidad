# Supuestos de la declaración de renta (formulario 210, AG 2025)

Lo que la aplicación hace y que no está escrito, palabra por palabra, en la norma o en el instructivo. Cada punto dice
qué se supuso y por qué. Si alguno resulta equivocado, se corrige en `data/renta/` o en `backend/app/renta/`.

## Fuentes verificadas

| Dato | Valor | Fuente |
|---|---|---|
| Formulario 210 | Casillas 1 a 141 | Resolución DIAN 000044 del 14-mar-2024 (AG 2023 y siguientes); instructivo compilado en la Resolución Única 000227 de 2025; PDF oficial `Formulario_210_2025.pdf` |
| UVT 2025 | $ 49.799 | Resolución DIAN 000193 de 2024 |
| UVT 2026 (sanciones) | $ 52.374 | Resolución DIAN 000238 de 2025 |
| Componente inflacionario AG 2025 | 55,43 % (rendimientos) · 28,35 % (costos financieros) | Decreto 898 del 29-jul-2026 |
| Calendario personas naturales | 12-ago a 26-oct de 2026 por los dos últimos dígitos del NIT | Art. 1.6.1.13.2.15 DUR 1625/2016 (Decreto 2229 de 2023) |
| Casillas contrastadas | 28 a 141 | Un 210 AG 2025 presentado (imagen 5, caso A): todas coinciden |

## Supuestos

1. **Aproximación.** Cada valor que va al formulario se aproxima al múltiplo de mil más cercano (art. 577 E.T.,
   mitad hacia arriba). Las fórmulas se aplican sobre los valores ya aproximados, como en el formulario.
2. **Calendario.** Se tomó la tabla publicada para 2026 (12-ago a 26-oct). Entre el 28 de septiembre y el 1 de
   octubre no hay fecha asignada; así aparece en las dos fuentes consultadas.
3. **Topes de obligación.** Ingresos brutos **iguales o mayores** a 1.400 UVT obligan (la norma exime a quien tiene
   ingresos *inferiores*); patrimonio, consumos con tarjeta, compras y consignaciones obligan cuando **superan** su
   tope. Se usan los topes del encabezado del reporte; si no los hay, se calculan con las líneas.
4. **1 % de compras con factura electrónica (casilla 28).** La aplicación propone el máximo (1 % de las compras del
   Tope 5, sin pasar de 240 UVT) solo si el contador confirma los cuatro requisitos del art. 336 num. 5; no revisa
   factura por factura. El contador puede bajar el valor (el caso A declaró 48.000 de un máximo de 78.000). Nunca
   genera pérdida.
5. **Beneficios personales** (intereses de vivienda, medicina prepagada, aportes voluntarios, GMF) se imputan a la
   primera columna de la cédula general con renta líquida, en el orden del instructivo: trabajo, trabajo no
   laboral, capital, no laborales.
6. **Renta exenta del 25 %.** Se calcula sobre la renta líquida de trabajo menos deducciones y otras rentas exentas,
   con tope de 790 UVT, solo en la columna de rentas de trabajo (casilla 36). Los honorarios **sin** costos van en
   esa columna; los honorarios **con** costos (casillas 43 a 57) no llevan el 25 %.
7. **Dependientes.** Con relación laboral se aplican las dos deducciones por el mismo dependiente (10 % hasta 32 UVT
   mensuales y 72 UVT adicionales, hasta 4). Sin relación laboral solo la adicional de 72 UVT (casilla 139), que no
   entra en el límite del 40 % y suele ser la más favorable.
8. **Límite del 40 % y 1.340 UVT** sobre los ingresos menos los no constitutivos, repartido en el orden del
   instructivo. No se manejan las rentas exentas que quedan por fuera del límite (art. 206 num. 6 a 9, primas,
   convenios, CAN): si un cliente las tiene, el contador las diligencia en el portal de la DIAN.
9. **Dividendos.** Se calcula la 1a subcédula 2017 y siguientes (casilla 107, sumada a la base del art. 241) con el
   descuento del art. 254-1. La 2a subcédula, los dividendos 2016 y anteriores y los del exterior no se calculan.
10. **Renta presuntiva:** 0 % desde 2021 (art. 188 E.T.).
11. **Anticipo (art. 807).** Se supone que el contribuyente declara por tercera vez o más (75 %) salvo que el
    contador indique otra cosa; el segundo procedimiento (promedio de dos años) solo se usa si se conoce el impuesto
    del año anterior. Se toma el menor.
12. **Sanción por extemporaneidad.** Estimación del art. 641 por meses o fracción, con la mínima de 10 UVT del año en
    que se impone (art. 639). No aplica la reducción del art. 640, que depende de hechos que la aplicación no
    conoce; se avisa que puede reducirse.
13. **Propuesta de la DIAN.** Se modela con lo que reportaron terceros: sin costos, sin beneficios que piden soporte
    y sin el 1 %. Los pagos por documentos soporte se suponen rentas de trabajo; la facturación electrónica emitida
    se toma como ingreso no laboral cuando no hay otro ingreso. La propuesta real de la DIAN puede variar.
14. **Patrimonio.** Se usa el valor reportado (saldos y avalúos). Cuando hay avalúo, se pide el costo fiscal, que
    suele ser distinto.
15. **Comparación patrimonial (art. 236).** Se avisa cuando el patrimonio bruto creció más que los ingresos del año;
    es una alerta para justificar, no un cálculo de renta gravable.
16. **Escritura a mano.** La letra cursiva no se puede leer con fiabilidad: se detecta que hay tinta fuera de la
    tabla y se avisa sin guardar nada. Si el OCR sí lee algo con forma de credencial (letras, cifras y símbolos, o
    un «@»), se descarta. Las cifras útiles escritas a mano («SF: …») se ofrecen como sugerencia, nunca como dato.
17. **Texto encimado.** Si el detalle de una fila no se puede leer, el valor se lee aparte (celda por celda) y la
    fila queda en ámbar para que el contador la clasifique con un clic. Una entidad que se repite en varias filas
    ilegibles se pregunta una sola vez como posible pagador, con la opción «no son ingresos».
18. **Diferencias pequeñas con los topes.** Hasta 1.000 pesos entre la suma de las filas y el encabezado se tratan
    como redondeo de la propia fuente (el caso A trae 3 pesos de diferencia en el Tope 4).
19. **Tipo de documento.** Si el encabezado de la foto no deja leer el tipo, se supone C.C. cuando el número tiene 10
    dígitos o menos.
20. **Personas jurídicas.** El formulario 110 no se prepara (ver `docs/PROPUESTAS.md`, P05).
