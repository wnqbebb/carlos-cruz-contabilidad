import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { BrowserRouter, Navigate, Route, Routes, useLocation, useSearchParams } from "react-router-dom";
import { animarPantalla, gsap, salirPantalla } from "./animacion";
import { ProveedorReautenticacion } from "./componentes/Acceso";
import { Marco } from "./componentes/Marco";
import { Preloader } from "./componentes/Preloader";
import { Puerta } from "./componentes/Subir";
import { ClienteEditor } from "./paginas/ClienteEditor";
import { Clientes } from "./paginas/Clientes";
import { Diseno } from "./paginas/Diseno";
import { Expediente } from "./paginas/Expediente";
import { Renta } from "./paginas/Renta";
import { Tablero } from "./paginas/Tablero";
import { Ingreso } from "./paginas/Ingreso";
import { sesionApi } from "./api";
import { BotonFantasma, BotonPrimario, ProveedorAvisos } from "./ui";

/** Sin sesión solo se ve la pantalla de ingreso (A2); el resto de la API responde 401. */
export default function App() {
  const [estado, setEstado] = useState<"consultando" | "fuera" | "dentro">("consultando");
  const [configurado, setConfigurado] = useState(true);
  const [puedeCrear, setPuedeCrear] = useState(false);
  useEffect(() => {
    sesionApi
      .estado()
      .then((e) => {
        setConfigurado(e.configurado);
        setPuedeCrear(!!e.puede_crear);
        setEstado(e.activa ? "dentro" : "fuera");
      })
      .catch(() => setEstado("fuera"));
    const vencida = () => setEstado("fuera");
    window.addEventListener("cc:sesion-vencida", vencida);
    return () => window.removeEventListener("cc:sesion-vencida", vencida);
  }, []);
  if (estado === "consultando") return null;
  if (estado === "fuera") return <Ingreso configurado={configurado} puedeCrear={puedeCrear} />;
  return <Aplicacion />;
}

function Aplicacion() {
  return (
    <BrowserRouter>
      <ProveedorAvisos>
        {/* `Puerta` envuelve toda la aplicación: así se puede soltar un archivo
            sobre cualquier pantalla y el botón «Subir archivo» funciona desde
            donde sea (spec v2.2 · Fase 3). */}
        <ProveedorReautenticacion>
          <Puerta>
            <Marco>
              <Contenido />
            </Marco>
          </Puerta>
        </ProveedorReautenticacion>
        <Preloader />
      </ProveedorAvisos>
    </BrowserRouter>
  );
}

/**
 * Transición entre pantallas (spec 8): la pantalla que se va se funde en
 * 0,15 s y solo entonces se muestra la nueva, que entra escalonada. Los
 * cambios que no cambian de pantalla (filtros en la URL) no se animan.
 */
function Contenido() {
  const ubicacion = useLocation();
  const [mostrada, setMostrada] = useState(ubicacion);
  const caja = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (ubicacion.pathname === mostrada.pathname) {
      if (ubicacion !== mostrada) setMostrada(ubicacion);
      return;
    }
    let vigente = true;
    salirPantalla(caja.current).then(() => {
      if (!vigente) return;
      setMostrada(ubicacion);
      window.scrollTo({ top: 0 });
    });
    return () => {
      vigente = false;
    };
  }, [ubicacion, mostrada]);

  useLayoutEffect(() => {
    if (caja.current) gsap.set(caja.current, { opacity: 1 });
    const anim = animarPantalla(caja.current);
    return () => {
      anim?.kill();
    };
  }, [mostrada.pathname]);

  // Al terminar el preloader, el Tablero (que cargó detrás) entra escalonado.
  useEffect(() => {
    const entrar = () => animarPantalla(caja.current);
    window.addEventListener("cc:preloader-fin", entrar);
    return () => window.removeEventListener("cc:preloader-fin", entrar);
  }, []);

  return (
    <div ref={caja}>
      <Routes location={mostrada}>
        <Route path="/" element={<Tablero />} />
        <Route path="/clientes" element={<Clientes />} />
        <Route path="/clientes/nuevo" element={<ClienteEditor />} />
        <Route path="/clientes/:id" element={<Expediente />} />
        <Route path="/clientes/:id/editar" element={<ClienteEditor />} />
        {/* v2.3: Trabajar vive dentro del expediente del cliente */}
        <Route path="/trabajo" element={<RedirigirTrabajo />} />
        <Route path="/renta" element={<Renta />} />
        <Route path="/parametros" element={<Navigate to="/" replace />} />
        {/* Catálogo vivo del sistema de diseño: uso interno, fuera del menú */}
        <Route path="/diseno" element={<Diseno />} />
        {/* rutas del diseño anterior, para que los enlaces guardados sigan sirviendo */}
        <Route path="/inicio" element={<Navigate to="/clientes" replace />} />
        <Route path="*" element={<NoEncontrado />} />
      </Routes>
    </div>
  );
}

/** `/trabajo?cliente=X[&sesion=S]` → `/clientes/X?seccion=contabilidad[&sesion=S]`; sin cliente, al directorio. */
function RedirigirTrabajo() {
  const [params] = useSearchParams();
  const cliente = params.get("cliente");
  if (!cliente) return <Navigate to="/clientes" replace />;
  const n = new URLSearchParams({ seccion: "contabilidad" });
  const sesion = params.get("sesion");
  if (sesion) n.set("sesion", sesion);
  return <Navigate to={`/clientes/${cliente}?${n.toString()}`} replace />;
}

function NoEncontrado() {
  return (
    <div className="py-10">
      <p className="t-display-xl text-tinta">404.</p>
      <p className="t-h1 mt-8 text-tinta">Esa página no existe</p>
      <p className="t-body mt-3 max-w-md text-grafito">
        Puede que el enlace esté viejo o que el cliente se haya eliminado.
      </p>
      <div className="mt-8 flex flex-wrap gap-3">
        <BotonPrimario a="/" flecha>
          Ir al tablero
        </BotonPrimario>
        <BotonFantasma a="/clientes">Ver clientes</BotonFantasma>
      </div>
    </div>
  );
}
