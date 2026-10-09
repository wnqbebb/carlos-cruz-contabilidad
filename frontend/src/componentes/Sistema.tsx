import { useCallback, useEffect, useState } from "react";
import { acceso, clientes as apiClientes, sistema, type EstadoAcceso } from "../api";
import { clases } from "../formato";
import { CodigosRecuperacion, MedidorClave, useEvaluacion } from "./Acceso";
import type { EstadoSistema } from "../tipos";
import { useAvisos } from "../ui";
import { Aviso, Boton, Campo, Dialogo, estiloCampo } from "./ui";

/**
 * Panel «Sistema» (v2.3 · Fase 2), en el menú de la cuenta. Solo lo que el
 * contador necesita: si está conectado, la versión y las acciones de su cuenta.
 * Nunca el proyecto, el motor de la base, rutas, variables ni comandos.
 */
export function DialogoSistema({ onCerrar }: { onCerrar: () => void }) {
  const [estado, setEstado] = useState<EstadoSistema | null>(null);
  useEffect(() => {
    sistema.estado().then(setEstado).catch(() => setEstado({ conectado: false, en_la_nube: false, version: __VERSION__ }));
  }, []);
  const conexion = !estado
    ? "Comprobando…"
    : !estado.conectado
      ? "Sin conexión"
      : estado.en_la_nube
        ? "En la nube · conectado"
        : "En este equipo · funcionando";
  return (
    <Dialogo rotulo="Cuenta" titulo="Sistema" onCerrar={onCerrar} ancho="max-w-lg">
      <div className="space-y-6">
        <dl className="grid grid-cols-[auto_1fr] gap-x-6 gap-y-3">
          <dt className="t-meta text-gris">Datos</dt>
          <dd className="t-body text-tinta">{conexion}</dd>
          <dt className="t-meta text-gris">Versión</dt>
          <dd className="t-body text-tinta">{estado?.version ?? __VERSION__}</dd>
        </dl>
        <AccesoSeguro />
        <ClientesDemostracion />
      </div>
    </Dialogo>
  );
}

/* ── acceso: contraseña, dos pasos, códigos y sesiones (v2.3 · Fase 6) ── */
type Tarea = "clave" | "totp" | "codigos" | null;

function AccesoSeguro() {
  const [estado, setEstado] = useState<EstadoAcceso | null>(null);
  const [tarea, setTarea] = useState<Tarea>(null);
  const [error, setError] = useState("");
  const avisar = useAvisos();
  const cargar = useCallback(() => {
    acceso.estado().then(setEstado).catch((e) => setError((e as Error).message));
  }, []);
  useEffect(() => cargar(), [cargar]);

  const accion = async (fn: () => Promise<unknown>, mensaje: string) => {
    setError("");
    try {
      await fn();
      avisar(mensaje);
      cargar();
    } catch (e) {
      setError((e as Error).message);
    }
  };

  return (
    <section aria-labelledby="titulo-acceso" className="space-y-3 border-t border-linea pt-5">
      <h3 id="titulo-acceso" className="t-body font-semibold text-tinta">Acceso</h3>
      {estado && estado.fallidos_24h > 0 && (
        <Aviso tono="ambar" titulo={`${estado.fallidos_24h} intento(s) fallido(s) en las últimas 24 horas`}>
          Si no fue usted, cambie la contraseña y cierre las demás sesiones.
        </Aviso>
      )}
      {estado && (
        <dl className="grid grid-cols-[auto_1fr] gap-x-6 gap-y-2">
          <dt className="t-meta text-gris">Usuario</dt>
          <dd className="t-body text-tinta">{estado.usuario}</dd>
          <dt className="t-meta text-gris">Dos pasos</dt>
          <dd className="t-body text-tinta">{estado.totp_activo ? "Activada" : "No activada"}</dd>
          <dt className="t-meta text-gris">Códigos</dt>
          <dd className="t-body text-tinta">{estado.codigos_restantes} de recuperación sin usar</dd>
          <dt className="t-meta text-gris">Sesiones</dt>
          <dd className="t-body text-tinta">{estado.sesiones} abierta(s)</dd>
        </dl>
      )}
      <div className="flex flex-wrap gap-2">
        <Boton variante="contorno" tamano="sm" onClick={() => setTarea("clave")}>Cambiar la contraseña</Boton>
        {estado?.totp_activo ? (
          <Boton variante="contorno" tamano="sm"
            onClick={() => accion(() => acceso.desactivarTotp(), "Verificación en dos pasos desactivada.")}>
            Desactivar dos pasos
          </Boton>
        ) : (
          <Boton variante="contorno" tamano="sm" onClick={() => setTarea("totp")}>Activar dos pasos</Boton>
        )}
        <Boton variante="contorno" tamano="sm" onClick={() => setTarea("codigos")}>Códigos nuevos</Boton>
        {estado && estado.sesiones > 1 && (
          <Boton variante="contorno" tamano="sm"
            onClick={() => accion(() => acceso.cerrarOtrasSesiones(), "Se cerraron las demás sesiones.")}>
            Cerrar las demás sesiones
          </Boton>
        )}
      </div>
      {error && <p className="t-small text-rojo">{error}</p>}
      {tarea === "clave" && <CambiarClave onListo={() => { setTarea(null); cargar(); }} />}
      {tarea === "totp" && <ActivarTotp usuario={estado?.usuario ?? ""} onListo={() => { setTarea(null); cargar(); }} />}
      {tarea === "codigos" && <NuevosCodigos usuario={estado?.usuario ?? ""} onListo={() => { setTarea(null); cargar(); }} />}
    </section>
  );
}

function CambiarClave({ onListo }: { onListo: () => void }) {
  const [actual, setActual] = useState("");
  const [nueva, setNueva] = useState("");
  const [error, setError] = useState("");
  const [trabajando, setTrabajando] = useState(false);
  const ev = useEvaluacion(nueva);
  const avisar = useAvisos();
  const guardar = async (e: React.FormEvent) => {
    e.preventDefault();
    setTrabajando(true);
    setError("");
    try {
      const r = await acceso.cambiarClave(actual, nueva);
      avisar(r.sesiones_cerradas ? `Contraseña cambiada. Se cerraron ${r.sesiones_cerradas} sesión(es) más.` : "Contraseña cambiada.");
      onListo();
    } catch (ex) {
      setError((ex as Error).message);
    } finally {
      setTrabajando(false);
    }
  };
  return (
    <form className="space-y-3 rounded-hoja border border-linea p-4" onSubmit={guardar}>
      <Campo etiqueta="Contraseña actual">
        <input type="password" autoComplete="current-password" value={actual} onChange={(e) => setActual(e.target.value)} className={estiloCampo} />
      </Campo>
      <Campo etiqueta="Contraseña nueva">
        <input type="password" autoComplete="new-password" value={nueva} onChange={(e) => setNueva(e.target.value)} className={estiloCampo} />
      </Campo>
      <MedidorClave ev={ev} />
      {error && <p className="t-small text-rojo">{error}</p>}
      <Boton type="submit" variante="solido" tamano="sm" cargando={trabajando} disabled={!actual || !ev?.valida}>Guardar</Boton>
    </form>
  );
}

function ActivarTotp({ usuario, onListo }: { usuario: string; onListo: () => void }) {
  const [datos, setDatos] = useState<{ qr: string; secreto: string } | null>(null);
  const [codigo, setCodigo] = useState("");
  const [codigos, setCodigos] = useState<string[] | null>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    acceso.iniciarTotp().then(setDatos).catch((e) => setError((e as Error).message));
  }, []);
  const activar = async () => {
    setError("");
    try {
      setCodigos((await acceso.confirmarTotp(codigo)).codigos);
    } catch (e) {
      setError((e as Error).message);
    }
  };
  if (codigos) {
    return (
      <div className="space-y-3 rounded-hoja border border-linea p-4">
        <p className="t-body text-tinta">Verificación en dos pasos activada.</p>
        <CodigosRecuperacion usuario={usuario} codigos={codigos} />
        <Boton variante="solido" tamano="sm" onClick={onListo}>Listo</Boton>
      </div>
    );
  }
  return (
    <div className="space-y-3 rounded-hoja border border-linea p-4">
      <p className="t-small text-grafito">
        Escanee el código con una aplicación de autenticación (Google Authenticator, Microsoft Authenticator…) y
        escriba el número de 6 dígitos que muestra.
      </p>
      {datos && <img src={datos.qr} alt="Código QR para la aplicación de autenticación" className="h-44 w-44 rounded-sm border border-linea bg-hoja" />}
      {datos && <p className="codigo break-all text-[12px] text-gris">Clave manual: {datos.secreto}</p>}
      <div className="flex flex-wrap items-end gap-2">
        <Campo etiqueta="Código">
          <input inputMode="numeric" autoComplete="one-time-code" value={codigo} onChange={(e) => setCodigo(e.target.value.trim())}
            className={clases(estiloCampo, "cifras w-36")} />
        </Campo>
        <Boton variante="solido" tamano="sm" disabled={codigo.length < 6} onClick={activar}>Activar</Boton>
      </div>
      {error && <p className="t-small text-rojo">{error}</p>}
    </div>
  );
}

function NuevosCodigos({ usuario, onListo }: { usuario: string; onListo: () => void }) {
  const [codigos, setCodigos] = useState<string[] | null>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    acceso.nuevosCodigos().then((r) => setCodigos(r.codigos)).catch((e) => setError((e as Error).message));
  }, []);
  return (
    <div className="space-y-3 rounded-hoja border border-linea p-4">
      {codigos && <CodigosRecuperacion usuario={usuario} codigos={codigos} />}
      {error && <p className="t-small text-rojo">{error}</p>}
      <Boton variante="solido" tamano="sm" onClick={onListo}>Listo</Boton>
    </div>
  );
}

/* ── clientes de demostración: se borran todos juntos, nunca un cliente real ── */
function ClientesDemostracion() {
  const [lista, setLista] = useState<{ id: string; razon_social: string }[] | null>(null);
  const [confirmar, setConfirmar] = useState(false);
  const [trabajando, setTrabajando] = useState(false);
  const [error, setError] = useState("");
  const avisar = useAvisos();
  const cargar = useCallback(() => {
    apiClientes.demostracion().then((r) => setLista(r.clientes)).catch((e) => setError((e as Error).message));
  }, []);
  useEffect(() => {
    cargar();
  }, [cargar]);

  const eliminar = async () => {
    setTrabajando(true);
    setError("");
    try {
      const r = await apiClientes.eliminarDemostracion();
      avisar(`Se eliminaron ${r.eliminados} cliente(s) de demostración.`);
      setConfirmar(false);
      cargar();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setTrabajando(false);
    }
  };

  return (
    <section aria-labelledby="titulo-demo" className="border-t border-linea pt-5">
      <h3 id="titulo-demo" className="t-body font-semibold text-tinta">Clientes de demostración</h3>
      <p className="t-small mt-1 text-grafito">
        {lista === null
          ? "Consultando…"
          : lista.length
            ? `Hay ${lista.length} con datos inventados para mostrar la aplicación.`
            : "No hay clientes de demostración cargados."}
      </p>
      {!!lista?.length && !confirmar && (
        <Boton variante="peligro" className="mt-3" onClick={() => setConfirmar(true)}>
          Eliminar clientes de demostración
        </Boton>
      )}
      {confirmar && lista && (
        <div className="mt-3 space-y-3">
          <Aviso tono="rojo" titulo="Esto no se puede deshacer">
            Se borran estos clientes con sus periodos, movimientos y su rastro en la bitácora. Ningún otro cliente se
            toca.
          </Aviso>
          <ul className="t-small list-disc space-y-1 pl-5 text-tinta">
            {lista.map((c) => (
              <li key={c.id}>{c.razon_social}</li>
            ))}
          </ul>
          <div className="flex flex-wrap justify-end gap-2">
            <Boton variante="fantasma" onClick={() => setConfirmar(false)}>
              Cancelar
            </Boton>
            <Boton variante="peligro" cargando={trabajando} onClick={eliminar}>
              Eliminar {lista.length} cliente(s)
            </Boton>
          </div>
        </div>
      )}
      {error && <p className="t-small mt-2 text-rojo">{error}</p>}
    </section>
  );
}
