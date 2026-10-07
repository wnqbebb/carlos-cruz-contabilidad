import { useLayoutEffect, useRef } from "react";
import { clases } from "../formato";
import { gsap, sinMovimiento } from "./movimiento";

/**
 * EsferaCliente — avatar único generado del NIT (ref-04).
 *
 * El NIT se convierte en un número estable (hash FNV-1a) y de ahí salen tres
 * colores de la paleta `--esfera-1…6` y la posición de cada foco de luz. El
 * mismo NIT da siempre la misma esfera, en cualquier equipo.
 *
 * Tamaños del spec: 32, 56 y 240 px. A 240 px deriva lentamente (12–18 s)
 * — solo en cabeceras del Escaparate.
 */

type Tamano = 32 | 56 | 240;

function hash(texto: string): number {
  let h = 0x811c9dc5;
  for (const c of texto) {
    h ^= c.charCodeAt(0);
    h = Math.imul(h, 0x01000193) >>> 0;
  }
  return h >>> 0;
}

/** Tres índices distintos de 1 a 6 y tres posiciones, todos del hash. */
export function rasgosEsfera(nit: string) {
  const h = hash(nit.replace(/\D/g, "") || nit);
  const a = (h % 6) + 1;
  const b = ((a + 1 + ((h >>> 3) % 4)) % 6) + 1;
  let c = ((b + 1 + ((h >>> 7) % 4)) % 6) + 1;
  if (c === a) c = (c % 6) + 1;
  const pos = (desp: number) => 20 + ((h >>> desp) % 60); // 20 %…80 %
  return {
    colores: [a, b, c] as const,
    focos: [
      [pos(5), pos(9)],
      [pos(13), pos(17)],
      [pos(21), pos(25)],
    ] as const,
  };
}

export function EsferaCliente({
  nit,
  nombre,
  tamano = 56,
  deriva,
  className,
}: {
  nit: string;
  /** Razón social: es el nombre accesible del avatar. */
  nombre?: string;
  tamano?: Tamano;
  /** Por defecto deriva solo a 240 px. */
  deriva?: boolean;
  className?: string;
}) {
  const nucleo = useRef<HTMLDivElement>(null);
  const { colores, focos } = rasgosEsfera(nit);
  const conDeriva = deriva ?? tamano === 240;

  const fondo = colores
    .map(
      (c, i) =>
        `radial-gradient(circle at ${focos[i][0]}% ${focos[i][1]}%, var(--esfera-${c}) 0%, transparent ${i === 0 ? 72 : 58}%)`,
    )
    .join(", ");

  useLayoutEffect(() => {
    if (!conDeriva || !nucleo.current || sinMovimiento()) return;
    const ctx = gsap.context(() => {
      gsap.to(nucleo.current, { rotation: 360, duration: 18, ease: "none", repeat: -1 });
      gsap.to(nucleo.current, { x: tamano * 0.03, y: -tamano * 0.025, duration: 12, ease: "sine.inOut", yoyo: true, repeat: -1 });
    });
    return () => ctx.revert();
  }, [conDeriva, tamano]);

  // Desenfoques proporcionales: el borde difuso de ref-04 sin perder la forma.
  const difuso = Math.max(1, Math.round(tamano * 0.035));
  const halo = Math.round(tamano * 0.22);

  return (
    <div
      role="img"
      aria-label={nombre ? `Distintivo de ${nombre}` : `Distintivo del NIT ${nit}`}
      className={clases("relative shrink-0", className)}
      style={{ width: tamano, height: tamano }}
    >
      {tamano >= 56 && (
        <div
          aria-hidden
          className="absolute inset-[8%] rounded-full opacity-45"
          style={{ background: fondo, filter: `blur(${halo}px)` }}
        />
      )}
      <div className="absolute inset-0 overflow-hidden rounded-full" style={{ backgroundColor: `var(--esfera-${colores[0]})` }}>
        <div
          ref={nucleo}
          aria-hidden
          className="absolute -inset-[12%] rounded-full"
          style={{ background: fondo, filter: `blur(${difuso}px)` }}
        />
      </div>
    </div>
  );
}
