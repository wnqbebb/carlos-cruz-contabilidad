import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { useLocation } from "react-router-dom";
import { estaTableroListo, gsap, sinMovimiento } from "../animacion";
import { CARGO, LEMA, MARCA, Monograma, TARJETA_PROFESIONAL } from "./Marca";

/**
 * Preloader «La cuenta T» (spec 7).
 *
 * · Solo en la primera carga de la sesión (sessionStorage).
 * · Duración objetivo 2,6 s. Se salta con clic, Esc o cualquier tecla.
 * · Atado a la carga real del Tablero: si los datos llegan antes, no se
 *   alarga; si tardan, la cuenta T queda en un bucle sutil, y nunca bloquea
 *   más de 4 s.
 * · DEBE y HABER ruedan hasta 100,00 = 100,00, el mismo 100 % del contador
 *   de la esquina: no se muestran cifras que parezcan de un cliente.
 * · Con «menos movimiento»: monograma + lema con fundido de 300 ms y nada más.
 *
 * Línea de tiempo:
 *   0,0–0,5  rejilla que se dibuja de arriba abajo + textos de esquina
 *   0,4–1,3  la T se traza (horizontal, luego vertical); DEBE / HABER;
 *            ruedan las columnas de cifras
 *   1,3–1,8  «=» y brillo «Cuadra»; «CUADRA.» entra con máscara desde abajo
 *   1,8–2,6  la T vuela al monograma de la barra; una carpeta negra se abre
 *            desde el centro y revela el Tablero, que entra escalonado
 */

const CLAVE = "cc-preloader-visto";
const TOTAL = "100,00";

function yaVisto(): boolean {
  try {
    return !!sessionStorage.getItem(CLAVE);
  } catch {
    return false;
  }
}

export function Preloader() {
  const { pathname } = useLocation();
  const [activo, setActivo] = useState(() => !yaVisto());
  const raiz = useRef<HTMLDivElement>(null);
  const linea = useRef<gsap.core.Timeline | null>(null);
  const terminado = useRef(false);

  const terminar = () => {
    if (terminado.current) return;
    terminado.current = true;
    document.documentElement.style.overflow = "";
    setActivo(false);
    window.dispatchEvent(new Event("cc:preloader-fin"));
  };

  // Saltar: clic, Esc o cualquier tecla → salida rápida.
  const saltar = () => {
    if (terminado.current || !raiz.current) return;
    linea.current?.kill();
    gsap.to(raiz.current, { opacity: 0, duration: 0.2, onComplete: terminar });
  };

  useEffect(() => {
    if (!activo) return;
    try {
      sessionStorage.setItem(CLAVE, "1");
    } catch {
      /* sin almacenamiento: se verá de nuevo en la próxima carga, nada más */
    }
    document.documentElement.style.overflow = "hidden";
    const tecla = () => saltar();
    window.addEventListener("keydown", tecla);
    return () => window.removeEventListener("keydown", tecla);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activo]);

  useLayoutEffect(() => {
    if (!activo || !raiz.current) return;
    const el = raiz.current;
    const q = gsap.utils.selector(el);
    const inicio = performance.now();
    // Solo se espera al Tablero si la sesión empezó en el Tablero.
    const hayQueEsperar = pathname === "/";
    const listo = () => !hayQueEsperar || estaTableroListo();

    const ctx = gsap.context(() => {
      if (sinMovimiento()) {
        gsap
          .timeline({ onComplete: terminar })
          .from(q("[data-reducido]"), { opacity: 0, duration: 0.3 })
          .to(el, { opacity: 0, duration: 0.3, delay: 0.4 });
        return;
      }

      const contador = { n: 0 };
      const textoContador = q("[data-contador]")[0] as HTMLElement | undefined;
      const tl = gsap.timeline({ onComplete: terminar });
      linea.current = tl;

      // 0,0–0,5 · rejilla y esquinas
      tl.from(q("[data-rejilla] span"), { scaleY: 0, transformOrigin: "top", duration: 0.5, ease: "power2.out", stagger: 0.03 }, 0)
        .from(q("[data-esquina]"), { opacity: 0, y: 6, duration: 0.4, ease: "power2.out", stagger: 0.05 }, 0.05)
        .to(contador, {
          n: 100,
          duration: 2.2,
          ease: "power1.inOut",
          onUpdate: () => {
            if (textoContador) textoContador.textContent = String(Math.round(contador.n)).padStart(3, "0");
          },
        }, 0)

        // 0,4–1,3 · la cuenta T
        .fromTo(q("[data-t-h]"), { scaleX: 0 }, { scaleX: 1, transformOrigin: "left center", duration: 0.4, ease: "power2.inOut" }, 0.4)
        .fromTo(q("[data-t-v]"), { scaleY: 0 }, { scaleY: 1, transformOrigin: "center top", duration: 0.35, ease: "power2.inOut" }, 0.72)
        .from(q("[data-lado]"), { opacity: 0, y: 6, duration: 0.3, stagger: 0.08 }, 0.7)
        .from(q("[data-total]"), { opacity: 0, duration: 0.2 }, 0.8);
      q("[data-digito]").forEach((col, i) => {
        const d = Number((col as HTMLElement).dataset.digito);
        // Rueda desde el 9 hasta su dígito: con «100,00» casi todo es 0 y sin esto no se movería.
        tl.fromTo(col, { yPercent: -90 }, { yPercent: -d * 10, duration: 0.55, ease: "expo.out" }, 0.8 + (i % 5) * 0.04);
      });

      // 1,3–1,8 · «=», brillo «Cuadra» y «CUADRA.»
      tl.from(q("[data-igual]"), { opacity: 0, scale: 0.6, duration: 0.25, ease: "back.out(2)" }, 1.3)
        .from(q("[data-brillo]"), { opacity: 0, duration: 0.35 }, 1.35)
        .from(q("[data-palabra]"), { yPercent: 105, duration: 0.5, ease: "power4.out" }, 1.3)
        .addLabel("salida", 1.8);

      // Espera a los datos del Tablero sin alargar si ya llegaron; tope 4 s.
      tl.add(() => {
        if (listo()) return;
        tl.pause();
        const latido = gsap.to(q("[data-t]"), { opacity: 0.55, duration: 0.6, yoyo: true, repeat: -1, ease: "sine.inOut" });
        const seguir = () => {
          window.removeEventListener("cc:tablero-listo", seguir);
          clearTimeout(tope);
          latido.kill();
          gsap.set(q("[data-t]"), { opacity: 1 });
          tl.play();
        };
        const restante = Math.max(0, 3200 - (performance.now() - inicio));
        const tope = window.setTimeout(seguir, restante);
        window.addEventListener("cc:tablero-listo", seguir);
      }, "salida");

      // 1,8–2,6 · la T vuela al monograma; la carpeta negra se abre y revela
      tl.add(() => {
        const t = q("[data-t]")[0] as HTMLElement | undefined;
        const destino = Array.from(document.querySelectorAll<SVGElement>(".monograma")).find(
          (m) => m.getBoundingClientRect().width > 0 && !el.contains(m),
        );
        if (!t || !destino) return;
        const a = t.getBoundingClientRect();
        const b = destino.getBoundingClientRect();
        gsap.to(t, {
          x: b.left + b.width / 2 - (a.left + a.width / 2),
          y: b.top + b.height / 2 - (a.top + a.height / 2),
          scale: Math.max(0.06, b.width / a.width),
          duration: 0.45,
          ease: "power3.inOut",
        });
      }, "salida")
        .to(q("[data-palabra], [data-esquina], [data-total], [data-lado], [data-igual], [data-brillo]"), { opacity: 0, duration: 0.25 }, "salida")
        .fromTo(
          q("[data-carpeta]"),
          { clipPath: "inset(48% 48% 48% 48% round 26px)", autoAlpha: 1 },
          // immediateRender: false — si no, la carpeta aparece desde el segundo cero.
          { clipPath: "inset(0% 0% 0% 0% round 0px)", duration: 0.4, ease: "power3.inOut", immediateRender: false },
          "salida+=0.3",
        )
        .to(el, { opacity: 0, duration: 0.25, ease: "power1.out" }, "salida+=0.62");
    }, el);

    return () => ctx.revert();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activo]);

  if (!activo) return null;

  const columna = (texto: string) =>
    texto.split("").map((c, i) =>
      /\d/.test(c) ? (
        <span key={i} className="relative inline-block h-[1em] overflow-hidden leading-none">
          <span data-digito={c} className="flex flex-col">
            {"0123456789".split("").map((n) => (
              <span key={n} className="block h-[1em] leading-none">{n}</span>
            ))}
          </span>
        </span>
      ) : (
        <span key={i} className="leading-none">{c}</span>
      ),
    );

  return (
    <div
      ref={raiz}
      data-preloader
      onClick={saltar}
      className="fixed inset-0 z-[100] cursor-pointer overflow-hidden bg-papel select-none"
    >
      <span role="status" aria-live="polite" className="sr-only">
        Cargando el tablero
      </span>
      <div className="grano" aria-hidden />

      {sinMovimiento() ? (
        <div data-reducido className="grid h-full place-items-center">
          <div className="flex flex-col items-center gap-4">
            <Monograma tamano={72} />
            <p className="t-h2 text-tinta">{LEMA}</p>
          </div>
        </div>
      ) : (
        <>
          {/* rejilla */}
          <div data-rejilla aria-hidden className="rejilla">
            <div>
              {Array.from({ length: 12 }, (_, i) => (
                <span key={i} />
              ))}
            </div>
          </div>

          {/* textos de esquina (ref-06) */}
          <div aria-hidden className="t-meta absolute inset-x-0 top-0 flex justify-between gap-4 p-[var(--margen)] pt-6 text-grafito">
            <span data-esquina>{MARCA} — {CARGO}</span>
            <span data-esquina>{TARJETA_PROFESIONAL}</span>
          </div>
          <div aria-hidden className="t-meta absolute inset-x-0 bottom-0 flex items-end justify-between gap-4 p-[var(--margen)] pb-6 text-grafito">
            <span data-esquina>Guacarí, Valle del Cauca</span>
            <span data-esquina>
              Abriendo expedientes <span data-contador className="codigo text-tinta">000</span>
            </span>
          </div>

          {/* centro: CUADRA. + cuenta T */}
          <div aria-hidden className="absolute inset-0 flex flex-col items-center justify-center px-[var(--margen)]">
            <div className="overflow-hidden pb-[0.06em]">
              <p data-palabra className="t-display-xl text-tinta">CUADRA.</p>
            </div>

            <div data-t className="relative mt-8 w-[min(560px,86vw)] will-change-transform">
              <div className="t-meta flex justify-between px-2 text-gris">
                <span data-lado>Debe</span>
                <span data-lado>Haber</span>
              </div>
              {/* La T: dos barras que crecen con transform (horizontal, luego vertical). */}
              <div className="relative mt-2 h-[200px]">
                <span data-t-h className="absolute inset-x-0 top-0 h-[3px] rounded-full bg-tinta" />
                <span data-t-v className="absolute top-0 bottom-0 left-1/2 w-[3px] -translate-x-1/2 rounded-full bg-tinta" />
              </div>
              <div className="absolute inset-x-0 top-[38%] grid grid-cols-[1fr_auto_1fr] items-center gap-4 px-2">
                <span data-total className="cifras t-kpi flex justify-center text-tinta">{columna(TOTAL)}</span>
                <span data-igual className="relative grid h-11 w-11 place-items-center rounded-full bg-hoja text-tinta">
                  <span data-brillo className="brillo-cuadra absolute inset-0 rounded-full" />
                  <span className="t-h2 relative">=</span>
                </span>
                <span data-total className="cifras t-kpi flex justify-center text-tinta">{columna(TOTAL)}</span>
              </div>
            </div>
          </div>

          {/* carpeta negra que se abre desde el centro (ref-01) */}
          <div
            data-carpeta
            aria-hidden
            className="invisible absolute inset-0 bg-tinta"
            style={{ clipPath: "inset(50% 50% 50% 50%)" }}
          />

          <p className="t-meta pointer-events-none absolute bottom-[88px] left-1/2 -translate-x-1/2 text-gris escritorio:bottom-6">Saltar ↵</p>
        </>
      )}
    </div>
  );
}
