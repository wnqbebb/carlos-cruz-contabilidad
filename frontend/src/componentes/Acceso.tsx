import { Download, Printer, ShieldCheck } from "lucide-react";
import { useEffect, useRef, useState, type ReactNode } from "react";
import { acceso, alPedirContrasena, ErrorApi, sesionApi, type EvaluacionClave } from "../api";
import { clases } from "../formato";
import { Aviso, Boton, Campo, Dialogo, estiloCampo } from "./ui";

/**
 * Piezas del acceso (v2.3 · Fase 6): confirmación de contraseña para acciones
 * delicadas, medidor de fortaleza y códigos de recuperación.
 */

/* ── confirmación de contraseña (reautenticación) ───────────────────────
   Se monta una vez. Cuando el servidor responde «reautenticar», api.ts llama
   aquí: se pide la contraseña (y el código si hay verificación en dos pasos)
   y la petición original se repite sola. */
export function ProveedorReautenticacion({ children }: { children: ReactNode }) {
  const [abierto, setAbierto] = useState(false);
  const [totp, setTotp] = useState(false);
  const resolver = useRef<((ok: boolean) => void) | null>(null);

  useEffect(() => {
    alPedirContrasena(
      () =>
        new Promise<boolean>((ok) => {
          resolver.current = ok;
          sesionApi.estado().then((e) => setTotp(!!e.totp)).catch(() => setTotp(false));
          setAbierto(true);
        }),
    );
    return () => alPedirContrasena(null);
  }, []);

  const cerrar = (ok: boolean) => {
    setAbierto(false);
    resolver.current?.(ok);
    resolver.current = null;
  };

  return (
    <>
      {children}
      {abierto && <DialogoReautenticar totp={totp} onListo={() => cerrar(true)} onCancelar={() => cerrar(false)} />}
    </>
  );
}

function DialogoReautenticar({ totp, onListo, onCancelar }: { totp: boolean; onListo: () => void; onCancelar: () => void }) {
  const [clave, setClave] = useState("");
  const [codigo, setCodigo] = useState("");
  const [error, setError] = useState("");
  const [trabajando, setTrabajando] = useState(false);
  const enviar = async (e?: React.FormEvent) => {
    e?.preventDefault();
    setTrabajando(true);
    setError("");
    try {
      await sesionApi.reautenticar(clave, codigo);
      onListo();
    } catch (ex) {
      setError(ex instanceof ErrorApi ? ex.message : "No se pudo confirmar. Vuelva a intentar.");
      setTrabajando(false);
    }
  };
  return (
    <Dialogo
      rotulo="Seguridad"
      titulo="Confirme su contraseña"
      onCerrar={onCancelar}
      ancho="max-w-md"
      pie={
        <>
          <Boton variante="fantasma" onClick={onCancelar}>Cancelar</Boton>
          <Boton variante="solido" cargando={trabajando} disabled={!clave} onClick={() => enviar()}>Confirmar</Boton>
        </>
      }
    >
      <form onSubmit={enviar} className="space-y-4">
        <p className="t-small text-grafito">Esta acción es delicada. Por seguridad, escriba su contraseña.</p>
        <Campo etiqueta="Contraseña">
          <input type="password" autoFocus autoComplete="current-password" value={clave}
            onChange={(e) => setClave(e.target.value)} className={estiloCampo} />
        </Campo>
        {totp && (
          <Campo etiqueta="Código de verificación">
            <input inputMode="numeric" autoComplete="one-time-code" value={codigo}
              onChange={(e) => setCodigo(e.target.value.trim())} className={clases(estiloCampo, "cifras")} />
          </Campo>
        )}
        {error && <p role="alert" className="t-small text-rojo">{error}</p>}
        <button type="submit" hidden aria-hidden tabIndex={-1} />
      </form>
    </Dialogo>
  );
}

/* ── medidor de fortaleza ─────────────────────────────────────────────── */
const NIVELES = ["Muy débil", "Débil", "Aceptable", "Fuerte", "Muy fuerte"];

export function useEvaluacion(clave: string, usuario = "") {
  const [ev, setEv] = useState<EvaluacionClave | null>(null);
  useEffect(() => {
    if (!clave) {
      setEv(null);
      return;
    }
    const t = setTimeout(() => {
      acceso.politica(clave, usuario).then(setEv).catch(() => setEv(null));
    }, 250);
    return () => clearTimeout(t);
  }, [clave, usuario]);
  return ev;
}

export function MedidorClave({ ev }: { ev: EvaluacionClave | null }) {
  if (!ev) return null;
  return (
    <div className="space-y-1.5" aria-live="polite">
      <div className="flex gap-1" aria-hidden>
        {[0, 1, 2, 3].map((i) => (
          <span key={i} className={clases("h-1.5 flex-1 rounded-full",
            i < ev.puntaje ? (ev.valida ? "bg-azul" : "bg-ambar") : "bg-linea")} />
        ))}
      </div>
      <p className="t-small text-grafito">
        {NIVELES[ev.puntaje]}
        {ev.problemas.length > 0 && <span className="text-ambar"> · {ev.problemas.join(" ")}</span>}
      </p>
    </div>
  );
}

/* ── códigos de recuperación: se muestran UNA vez ─────────────────────── */
export function CodigosRecuperacion({ codigos, usuario }: { codigos: string[]; usuario: string }) {
  const texto = [
    "Carlos Cruz · códigos de recuperación",
    `Usuario: ${usuario}`,
    "Cada código sirve una sola vez para entrar si olvida la contraseña o pierde el celular.",
    "Guárdelos fuera del computador (impresos o en un lugar seguro).",
    "",
    ...codigos,
  ].join("\n");
  const descargar = () => {
    const url = URL.createObjectURL(new Blob([texto], { type: "text/plain;charset=utf-8" }));
    const a = document.createElement("a");
    a.href = url;
    a.download = "carlos-cruz-codigos-de-recuperacion.txt";
    a.click();
    URL.revokeObjectURL(url);
  };
  return (
    <div className="space-y-4">
      <Aviso tono="ambar" titulo="Guárdelos ahora: no se vuelven a mostrar">
        Cada código sirve una sola vez para entrar si olvida la contraseña. Guárdelos fuera de este computador.
      </Aviso>
      <ol className="codigos-impresion grid grid-cols-2 gap-2 rounded-hoja border border-linea bg-hoja-2 p-4">
        {codigos.map((c) => (
          <li key={c} className="codigo text-center text-[15px] tracking-wider text-tinta">{c}</li>
        ))}
      </ol>
      <div className="flex flex-wrap gap-2">
        <Boton variante="contorno" tamano="sm" onClick={descargar}>
          <Download size={16} strokeWidth={1.5} aria-hidden /> Descargar
        </Boton>
        <Boton variante="contorno" tamano="sm" onClick={() => window.print()}>
          <Printer size={16} strokeWidth={1.5} aria-hidden /> Imprimir
        </Boton>
      </div>
    </div>
  );
}

export function IconoSeguro() {
  return <ShieldCheck size={18} strokeWidth={1.5} aria-hidden className="text-azul" />;
}
