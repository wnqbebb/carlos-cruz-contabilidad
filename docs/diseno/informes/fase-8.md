# Fase 8 · Preloader y animación — informe

Capturas: `capturas/fase-8/preloader-0300ms…2450ms(-movil).png` (la línea de tiempo), `preloader-reducido.png`, `despues-preloader*.png`.

## Preloader «La cuenta T» (spec 7)
| Tramo | Qué pasa |
|---|---|
| 0,0–0,5 s | Papel con grano; la rejilla se dibuja de arriba abajo (escalonado 0,03); esquinas: «Carlos Cruz — Contador Público», «T.P. 103028-T», «Guacarí, Valle del Cauca», «Abriendo expedientes 000→100» |
| 0,4–1,3 s | La T se traza (horizontal, luego vertical); DEBE y HABER; las columnas de cifras ruedan |
| 1,3–1,8 s | «=» con brillo «Cuadra»; «CUADRA.» en display-xl entra con máscara desde abajo |
| 1,8–2,6 s | La T vuela al monograma de la barra; una carpeta negra se abre desde el centro; el Tablero entra escalonado |

- **Solo la primera carga de la sesión** (verificado: al recargar no aparece).
- **Atado a la carga real**: espera la señal del Tablero; si ya llegó, no se alarga; si tarda, la T late suave; **tope 4 s**. Medido: termina a ~2,8–3,1 s desde que se pide la página.
- **Saltable** con clic, Esc o cualquier tecla («Saltar ↵»). Medido: Esc a los 0,7 s → cierra a 1,08 s.
- **Menos movimiento**: monograma + lema con fundido y nada más (~1 s).
- Accesible: `role="status"`, «Cargando el tablero». El scroll se bloquea mientras está y se libera al cerrar (verificado).
- **Decisión:** DEBE y HABER ruedan hasta **100,00 = 100,00**, el mismo 100 % del contador. No se muestran importes que pudieran parecer de un cliente.

## Sistema de animación (spec 8)
Todo vive en `src/animacion/`: GSAP, Flip y ScrollTrigger se registran una sola vez y los componentes lo usan desde ahí.

| Movimiento | Estado |
|---|---|
| Entrada de página (y 12→0, 0,45 s power3.out, escalonado 0,04) | ✅ en todas las pantallas |
| Salida de página (opacidad 1→0, 0,15 s) | ✅ la ruta nueva se muestra al terminar el fundido (medido fotograma a fotograma) |
| Odómetro (0,9 s expo.out) | ✅ Cifra · ya desde la Fase 2 |
| Hover Expediente (−4 px, −0,6°, flecha +3 px) | ✅ desde la Fase 2 |
| Interruptor / navegación con Flip (0,35 s) | ✅ interruptores, pestañas, barra lateral y barra móvil |
| Balanza (back.out 1.4, 0,6 s) | ✅ ecuación del Tablero |
| Deriva de esferas (12–18 s) | ✅ esfera de 240 px |
| Aparición por scroll (una vez, y 16, 0,5 s) | ✅ cola de operaciones y clientes recientes del Tablero |
| Taller sin animación de entrada | ✅ tablas y formularios solo cambian de estado (≤ 0,2 s) |

Todo respeta «menos movimiento» y se limpia con `gsap.context()`. Sin Lenis ni cursores personalizados. Se eliminó `animarCifra`, que interpolaba importes con números flotantes.

## Corregido durante la revisión
- Una «píldora» negra en el centro del preloader: `fromTo` aplicaba el estado inicial de la carpeta desde el segundo cero (`immediateRender`).
- La T con `stroke-dasharray` se pintaba mal en Edge: ahora son dos barras con `scale` (solo transform, como pide el spec).
- Con «100,00» casi todo es cero y las columnas no se movían: ahora ruedan desde el 9.
- «Saltar» se montaba sobre el contador en móvil.

## Verificación
| Comprobación | Resultado |
|---|---|
| build · tsc · lint | ✅ · ✅ · ✅ 0 |
| Pruebas | ✅ 111 |
| Consola durante preloader y navegación | ✅ sin errores |
| 390 px | ✅ (fotogramas móviles revisados) |
