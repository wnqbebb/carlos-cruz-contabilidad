import { useEffect, useRef, useState } from "react";
import { acceso, ErrorApi, sesionApi } from "../api";
import { CodigosRecuperacion, MedidorClave, useEvaluacion } from "../componentes/Acceso";
import { LEMA, MARCA, Monograma } from "../componentes/Marca";
import { Aviso, Campo, estiloCampo } from "../componentes/ui";
import { clases } from "../formato";
import { BotonPrimario, EnlaceSubrayado } from "../ui";

/**
 * Pantalla de ingreso (A2, rehecha en la v2.3 · Fase 6). Es lo único que se ve sin sesión.
 *
 * - Entrar, con el código de verificación si el contador activó los dos pasos.
 * - «Crear su acceso» la primera vez, solo desde este mismo equipo, con 10 códigos de
 *   recuperación que se muestran una sola vez.
 * - «¿Olvidó la contraseña?» con un código de recuperación. Sin terminal ni comandos.
 */
type Modo = "entrar" | "crear" | "recuperar" | "codigos";

export function Ingreso({
  configurado,
  puedeCrear,
  requiereCodigoInstalacion = false,
}: {
  configurado: boolean;
  puedeCrear: boolean;
  requiereCodigoInstalacion?: boolean;
}) {
  const [modo, setModo] = useState<Modo>(!configurado && puedeCrear ? "crear" : "entrar");
  const [codigos, setCodigos] = useState<{ usuario: string; codigos: string[] } | null>(null);

  useEffect(() => {
    document.title = `Ingresar · ${MARCA}`;
  }, []);

  return (
    <main className="grid min-h-screen place-items-center bg-lienzo px-4 py-10">
      <div className="w-full max-w-[420px]">
        <div className="mb-8 flex items-center gap-3">
          <Monograma tamano={48} />
          <div>
            <p className="t-h2 text-tinta">{MARCA}</p>
            <p className="t-small text-grafito">{LEMA}</p>
          </div>
        </div>
        <div className="material-hoja px-6 py-7">
          {modo === "entrar" && (
            <Entrar
              configurado={configurado}
              puedeCrear={puedeCrear}
              onCrear={() => setModo("crear")}
              onRecuperar={() => setModo("recuperar")}
            />
          )}
          {modo === "crear" && (
            <Crear
              requiereCodigoInstalacion={requiereCodigoInstalacion}
              onCreado={(usuario, c) => {
                setCodigos({ usuario, codigos: c });
                setModo("codigos");
              }}
              onVolver={() => setModo("entrar")}
            />
          )}
          {modo === "recuperar" && <Recuperar onVolver={() => setModo("entrar")} />}
          {modo === "codigos" && codigos && (
            <div className="space-y-5">
              <h1 className="t-h1 text-tinta">Su acceso está listo</h1>
              <CodigosRecuperacion usuario={codigos.usuario} codigos={codigos.codigos} />
              <BotonPrimario className="w-full" onClick={() => window.location.reload()}>
                Ya los guardé: entrar
              </BotonPrimario>
            </div>
          )}
        </div>
      </div>
    </main>
  );
}

function Entrar({
  configurado,
  puedeCrear,
  onCrear,
  onRecuperar,
}: {
  configurado: boolean;
  puedeCrear: boolean;
  onCrear: () => void;
  onRecuperar: () => void;
}) {
  const [usuario, setUsuario] = useState("");
  const [clave, setClave] = useState("");
  const [codigo, setCodigo] = useState("");
  const [pideCodigo, setPideCodigo] = useState(false);
  const [error, setError] = useState("");
  const [trabajando, setTrabajando] = useState(false);
  const campoUsuario = useRef<HTMLInputElement>(null);
  useEffect(() => campoUsuario.current?.focus(), []);

  const entrar = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!usuario.trim() || !clave) {
      setError("Escriba su usuario y su contraseña.");
      return;
    }
    setTrabajando(true);
    setError("");
    try {
      await sesionApi.entrar(usuario.trim(), clave, codigo);
      window.location.reload();
    } catch (ex) {
      if (ex instanceof ErrorApi && ex.codigo === "requiere_totp") {
        setPideCodigo(true);
        setError("");
      } else {
        if (ex instanceof ErrorApi) {
          if (
            ex.codigo === "sin_conexion" ||
            ex.estado === 0 ||
            ex.estado === 502 ||
            ex.estado === 503 ||
            ex.estado === 504
          ) {
            setError("No hay conexión con el servidor; puede estar despertando, espere unos segundos.");
          } else if (ex.codigo === "demasiados_intentos" || ex.estado === 429) {
            setError(ex.message || "Demasiados intentos, espere 15 minutos.");
          } else if (ex.codigo === "credenciales" || ex.estado === 401) {
            setError("Usuario o contraseña incorrectos.");
          } else if (ex.estado === 405) {
            setError("No hay conexión con el servidor; puede estar despertando o reconfigurándose, espere unos segundos.");
          } else {
            setError(ex.message || "Usuario o contraseña incorrectos.");
          }
        } else {
          setError("No se pudo ingresar. Vuelva a intentar.");
        }
        if (!(ex instanceof ErrorApi && ex.codigo === "totp_invalido")) setClave("");
      }
      setTrabajando(false);
    }
  };

  return (
    <form onSubmit={entrar} className="space-y-5" noValidate>
      <div>
        <h1 className="t-h1 text-tinta">Ingresar</h1>
        <p className="t-small mt-1 text-grafito">La contabilidad de sus clientes queda detrás de esta puerta.</p>
      </div>
      {!configurado && puedeCrear && (
        <div className="rounded border border-dorado-300 bg-dorado-50 p-4 text-center">
          <p className="t-small font-medium text-tinta">Todavía no hay un acceso creado en este sistema.</p>
          <button
            type="button"
            onClick={onCrear}
            className="mt-2 text-sm font-semibold text-dorado-900 underline"
          >
            Crear su acceso ahora
          </button>
        </div>
      )}
      {!configurado && !puedeCrear && (
        <Aviso tono="ambar" titulo="Todavía no hay un acceso creado">
          Abra la aplicación en el computador donde está instalada para crear su usuario y su contraseña.
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
      {pideCodigo && (
        <Campo
          etiqueta="Código de verificación"
          ayuda="El de su aplicación de autenticación, o un código de recuperación."
        >
          <input
            autoFocus
            value={codigo}
            onChange={(e) => setCodigo(e.target.value.trim())}
            autoComplete="one-time-code"
            className={clases(estiloCampo, "cifras")}
          />
        </Campo>
      )}
      {error && (
        <p role="alert" className="t-small text-rojo">
          {error}
        </p>
      )}
      <BotonPrimario type="submit" cargando={trabajando} className="w-full">
        Entrar
      </BotonPrimario>
      {configurado && (
        <p className="text-center">
          <EnlaceSubrayado
            href="#"
            onClick={(e) => {
              e.preventDefault();
              onRecuperar();
            }}
          >
            ¿Olvidó la contraseña?
          </EnlaceSubrayado>
        </p>
      )}
    </form>
  );
}

function Crear({
  requiereCodigoInstalacion,
  onCreado,
  onVolver,
}: {
  requiereCodigoInstalacion: boolean;
  onCreado: (usuario: string, codigos: string[]) => void;
  onVolver: () => void;
}) {
  const [usuario, setUsuario] = useState("");
  const [clave, setClave] = useState("");
  const [repetida, setRepetida] = useState("");
  const [codigoInstalacion, setCodigoInstalacion] = useState("");
  const [error, setError] = useState("");
  const [trabajando, setTrabajando] = useState(false);
  const ev = useEvaluacion(clave, usuario);

  const crear = async (e: React.FormEvent) => {
    e.preventDefault();
    if (clave !== repetida) {
      setError("Las dos contraseñas no coinciden.");
      return;
    }
    if (requiereCodigoInstalacion && !codigoInstalacion.trim()) {
      setError("Escriba el código de instalación configurado en su servidor.");
      return;
    }
    setTrabajando(true);
    setError("");
    try {
      const r = await acceso.crear(usuario.trim(), clave, codigoInstalacion.trim());
      onCreado(r.usuario, r.codigos);
    } catch (ex) {
      setError(ex instanceof ErrorApi ? ex.message : "No se pudo crear el acceso.");
      setTrabajando(false);
    }
  };

  return (
    <form onSubmit={crear} className="space-y-5" noValidate>
      <div>
        <h1 className="t-h1 text-tinta">Crear su acceso</h1>
        <p className="t-small mt-1 text-grafito">
          {requiereCodigoInstalacion
            ? "Instalación en la nube: elija su usuario, una contraseña segura y el código de instalación de su servidor."
            : "Es la primera vez que se abre la aplicación en este equipo. Elija su usuario y una contraseña de al menos 12 caracteres; una frase larga es más segura y más fácil de recordar."}
        </p>
      </div>
      {requiereCodigoInstalacion && (
        <Campo
          etiqueta="Código de instalación"
          ayuda="Código configurado en las variables de entorno de su servidor (CC_CODIGO_INSTALACION)."
        >
          <input
            type="password"
            value={codigoInstalacion}
            onChange={(e) => setCodigoInstalacion(e.target.value)}
            placeholder="Código secreto del servidor"
            className={estiloCampo}
          />
        </Campo>
      )}
      <Campo etiqueta="Usuario">
        <input
          autoFocus
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
          autoComplete="new-password"
          className={estiloCampo}
        />
      </Campo>
      <MedidorClave ev={ev} />
      <Campo etiqueta="Repita la contraseña">
        <input
          type="password"
          value={repetida}
          onChange={(e) => setRepetida(e.target.value)}
          autoComplete="new-password"
          className={estiloCampo}
        />
      </Campo>
      {error && (
        <p role="alert" className="t-small text-rojo">
          {error}
        </p>
      )}
      <BotonPrimario
        type="submit"
        cargando={trabajando}
        className="w-full"
        disabled={
          !usuario.trim() ||
          !ev?.valida ||
          !repetida ||
          (requiereCodigoInstalacion && !codigoInstalacion.trim())
        }
      >
        Crear el acceso
      </BotonPrimario>
      <p className="text-center">
        <EnlaceSubrayado
          href="#"
          onClick={(e) => {
            e.preventDefault();
            onVolver();
          }}
        >
          Volver a ingresar
        </EnlaceSubrayado>
      </p>
    </form>
  );
}

function Recuperar({ onVolver }: { onVolver: () => void }) {
  const [usuario, setUsuario] = useState("");
  const [codigo, setCodigo] = useState("");
  const [nueva, setNueva] = useState("");
  const [error, setError] = useState("");
  const [listo, setListo] = useState<number | null>(null);
  const [trabajando, setTrabajando] = useState(false);
  const ev = useEvaluacion(nueva, usuario);

  const recuperar = async (e: React.FormEvent) => {
    e.preventDefault();
    setTrabajando(true);
    setError("");
    try {
      const r = await acceso.recuperar(usuario.trim(), codigo.trim(), nueva);
      setListo(r.codigos_restantes);
    } catch (ex) {
      setError(ex instanceof ErrorApi ? ex.message : "No se pudo cambiar la contraseña.");
    } finally {
      setTrabajando(false);
    }
  };

  if (listo !== null) {
    return (
      <div className="space-y-5">
        <h1 className="t-h1 text-tinta">Contraseña nueva lista</h1>
        <p className="t-body text-grafito">
          Se cerraron las sesiones abiertas. Le quedan {listo} códigos de recuperación; cuando le queden pocos, genere
          otros desde Sistema › Acceso.
        </p>
        <BotonPrimario className="w-full" onClick={onVolver}>Ingresar</BotonPrimario>
      </div>
    );
  }
  return (
    <form onSubmit={recuperar} className="space-y-5" noValidate>
      <div>
        <h1 className="t-h1 text-tinta">¿Olvidó la contraseña?</h1>
        <p className="t-small mt-1 text-grafito">Use uno de sus códigos de recuperación para poner una nueva.</p>
      </div>
      <Campo etiqueta="Usuario">
        <input autoFocus value={usuario} onChange={(e) => setUsuario(e.target.value)} autoComplete="username"
          autoCapitalize="none" spellCheck={false} className={estiloCampo} />
      </Campo>
      <Campo etiqueta="Código de recuperación">
        <input value={codigo} onChange={(e) => setCodigo(e.target.value.toUpperCase())} placeholder="XXXXX-XXXXX"
          autoComplete="off" className={clases(estiloCampo, "cifras tracking-wider")} />
      </Campo>
      <Campo etiqueta="Contraseña nueva">
        <input type="password" value={nueva} onChange={(e) => setNueva(e.target.value)} autoComplete="new-password"
          className={estiloCampo} />
      </Campo>
      <MedidorClave ev={ev} />
      {error && <p role="alert" className="t-small text-rojo">{error}</p>}
      <BotonPrimario type="submit" cargando={trabajando} className="w-full" disabled={!usuario || !codigo || !ev?.valida}>
        Poner la contraseña nueva
      </BotonPrimario>
      <p className="text-center">
        <EnlaceSubrayado href="#" onClick={(e) => { e.preventDefault(); onVolver(); }}>Volver a ingresar</EnlaceSubrayado>
      </p>
    </form>
  );
}
