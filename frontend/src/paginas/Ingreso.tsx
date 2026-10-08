import { useEffect, useRef, useState } from "react";
import { ErrorApi, sesionApi } from "../api";
import { LEMA, MARCA, Monograma } from "../componentes/Marca";
import { Aviso, Campo, estiloCampo } from "../componentes/ui";
import { BotonPrimario } from "../ui";

/**
 * Pantalla de ingreso (adición A2). Es lo único que se ve sin sesión: el resto
 * de la API responde 401. Usa los mismos tokens que toda la aplicación, así que
 * sigue el modo claro u oscuro que el contador eligió.
 */
export function Ingreso({ configurado }: { configurado: boolean }) {
  const [usuario, setUsuario] = useState("");
  const [clave, setClave] = useState("");
  const [error, setError] = useState("");
  const [trabajando, setTrabajando] = useState(false);
  const campoUsuario = useRef<HTMLInputElement>(null);

  useEffect(() => {
    document.title = `Ingresar · ${MARCA}`;
    campoUsuario.current?.focus();
  }, []);

  const entrar = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!usuario.trim() || !clave) {
      setError("Escriba su usuario y su contraseña.");
      return;
    }
    setTrabajando(true);
    setError("");
    try {
      await sesionApi.entrar(usuario.trim(), clave);
      // Se recarga para que todas las pantallas arranquen con la sesión ya abierta.
      window.location.reload();
    } catch (ex) {
      setError(ex instanceof ErrorApi ? ex.message : "No se pudo ingresar. Vuelva a intentar.");
      setClave("");
      setTrabajando(false);
    }
  };

  return (
    <main className="grid min-h-screen place-items-center bg-lienzo px-4 py-10">
      <div className="w-full max-w-[400px]">
        <div className="mb-8 flex items-center gap-3">
          <Monograma tamano={48} />
          <div>
            <p className="t-h2 text-tinta">{MARCA}</p>
            <p className="t-small text-grafito">{LEMA}</p>
          </div>
        </div>

        <form onSubmit={entrar} className="material-hoja space-y-5 px-6 py-7" noValidate>
          <div>
            <h1 className="t-h1 text-tinta">Ingresar</h1>
            <p className="t-small mt-1 text-grafito">La contabilidad de sus clientes queda detrás de esta puerta.</p>
          </div>

          {!configurado && (
            <Aviso tono="ambar" titulo="Todavía no hay un usuario creado">
              En la carpeta del programa ejecute <span className="codigo">python backend/crear_usuario.py</span>,
              elija usuario y contraseña, y vuelva a abrir la aplicación.
            </Aviso>
          )}

          <Campo etiqueta="Usuario">
            <input
              ref={campoUsuario}
              value={usuario}
              onChange={(e) => setUsuario(e.target.value)}
              autoComplete="username"
              autoCapitalize="none"
              spellCheck={false}
              className={estiloCampo}
            />
          </Campo>
          <Campo etiqueta="Contraseña">
            <input
              type="password"
              value={clave}
              onChange={(e) => setClave(e.target.value)}
              autoComplete="current-password"
              className={estiloCampo}
            />
          </Campo>

          {error && (
            <p role="alert" className="t-small text-rojo">
              {error}
            </p>
          )}

          <BotonPrimario type="submit" cargando={trabajando} className="w-full">
            Entrar
          </BotonPrimario>
        </form>
        <p className="t-meta mt-6 text-center text-gris">
          ¿Olvidó la contraseña? Cámbiela con <span className="codigo normal-case">python backend/crear_usuario.py</span>
        </p>
      </div>
    </main>
  );
}
