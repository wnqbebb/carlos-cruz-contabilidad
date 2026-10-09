"""Endurecimiento HTTP (controles C9–C15).

Un solo middleware, en este orden:
1. **Host** permitido (contra *DNS rebinding*): `localhost`, `127.0.0.1`, `::1` y `CC_HOSTS`.
2. **Límite de solicitudes** por equipo (más estricto en subidas, cálculos y fotos).
3. **Sesión**: toda `/api/` la pide, salvo las rutas públicas.
4. **CSRF** en lo que modifica datos: el `Origin` (o `Referer`) debe ser la propia aplicación o
   un origen configurado, y las rutas con sesión exigen además el token `X-CSRF` de la sesión.
5. **Encabezados de seguridad** en toda respuesta y `Cache-Control: no-store` en la API.
"""
from __future__ import annotations

import os
import threading
import time
from urllib.parse import urlsplit

from fastapi import Request
from fastapi.responses import JSONResponse

from .. import sesion
from ..config import CORS_ORIGENES

MODIFICAN = {"POST", "PUT", "PATCH", "DELETE"}
HOSTS_BASE = {"localhost", "127.0.0.1", "::1", "[::1]"}

CSP = ("default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; "
       "font-src 'self' data:; connect-src 'self'; object-src 'none'; base-uri 'self'; form-action 'self'; "
       "frame-ancestors 'none'")
ENCABEZADOS = {
    "Content-Security-Policy": CSP,
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=(), payment=(), usb=(), interest-cohort=()",
    "Cross-Origin-Opener-Policy": "same-origin",
    "Cross-Origin-Resource-Policy": "same-origin",
}

# Rutas costosas: subir, leer fotos, calcular.
COSTOSAS = ("/api/subir", "/api/importar", "/api/calcular", "/api/identidad", "/api/clientes/importar")


def hosts_permitidos() -> set[str]:
    extra = {h.strip().lower() for h in (os.getenv("CC_HOSTS") or "").split(",") if h.strip()}
    return HOSTS_BASE | extra


def _host(valor: str) -> str:
    valor = (valor or "").strip().lower()
    if valor.startswith("["):                       # [::1]:8000
        return valor.split("]")[0] + "]"
    return valor.rsplit(":", 1)[0] if valor.count(":") == 1 else valor


def origen_permitido(origen: str, request: Request) -> bool:
    if not origen or origen == "null":
        return False
    partes = urlsplit(origen)
    propio = f"{partes.scheme}://{partes.netloc}".lower()
    if propio in {o.lower().rstrip("/") for o in CORS_ORIGENES}:
        return True
    return _host(partes.netloc) in hosts_permitidos() and _host(partes.netloc) == _host(request.headers.get("host", ""))


# ── límite de solicitudes ───────────────────────────────────────────────
_ventanas: dict[str, list[float]] = {}
_candado = threading.Lock()


def _limite(ruta: str, metodo: str) -> tuple[str, int]:
    costosa = metodo in MODIFICAN and (ruta.startswith(COSTOSAS) or ruta.endswith("/documentos"))
    if costosa:
        return "costosa", int(os.getenv("CC_LIMITE_COSTOSAS") or 30)
    return "general", int(os.getenv("CC_LIMITE_GENERAL") or 600)


def permitir(ip: str, ruta: str, metodo: str) -> int:
    """0 si puede seguir; si no, segundos a esperar. Ventana de un minuto."""
    clase, limite = _limite(ruta, metodo)
    clave = f"{clase}:{ip}"
    ahora = time.time()
    with _candado:
        v = [t for t in _ventanas.get(clave, []) if ahora - t < 60]
        if len(v) >= limite:
            _ventanas[clave] = v
            return max(1, int(60 - (ahora - v[0])))
        v.append(ahora)
        _ventanas[clave] = v
    return 0


def olvidar_limites() -> None:
    with _candado:
        _ventanas.clear()


def _rechazo(estado: int, codigo: str, mensaje: str, **extra) -> JSONResponse:
    return JSONResponse(status_code=estado, content={"detail": {"codigo": codigo, "mensaje": mensaje, **extra}})


def _con_encabezados(respuesta, request: Request):
    for k, v in ENCABEZADOS.items():
        respuesta.headers.setdefault(k, v)
    if request.url.scheme == "https" or request.headers.get("x-forwarded-proto", "").lower() == "https":
        respuesta.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
    if request.url.path.startswith("/api/"):
        respuesta.headers["Cache-Control"] = "no-store"
        respuesta.headers["Pragma"] = "no-cache"
    return respuesta


async def proteger(request: Request, siguiente):
    ruta = request.url.path
    metodo = request.method.upper()
    if _host(request.headers.get("host", "")) not in hosts_permitidos():
        return _con_encabezados(_rechazo(400, "host", "Solicitud rechazada."), request)
    es_api = ruta.startswith("/api/")
    if es_api and metodo != "OPTIONS":
        ip = request.client.host if request.client else "?"
        espera = permitir(ip, ruta, metodo)
        if espera:
            r = _rechazo(429, "demasiadas_solicitudes",
                         "Demasiadas solicitudes seguidas. Espere un momento y vuelva a intentar.", segundos=espera)
            r.headers["Retry-After"] = str(espera)
            return _con_encabezados(r, request)
        publica = ruta.rstrip("/") in sesion.PUBLICAS
        info = sesion.leer(request.cookies.get(sesion.COOKIE))
        request.state.sesion = info
        if not publica and not info:
            return _con_encabezados(_rechazo(401, "sin_sesion",
                                             "La sesión no está iniciada o venció. Ingrese de nuevo."), request)
        if metodo in MODIFICAN:
            origen = request.headers.get("origin") or ""
            referer = request.headers.get("referer") or ""
            if origen and not origen_permitido(origen, request):
                return _con_encabezados(_rechazo(403, "origen", "Solicitud rechazada."), request)
            if not origen and referer and not origen_permitido(referer, request):
                return _con_encabezados(_rechazo(403, "origen", "Solicitud rechazada."), request)
            if not publica and request.headers.get(sesion.ENCABEZADO_CSRF) != info["csrf"]:
                return _con_encabezados(_rechazo(403, "csrf",
                                                 "La página quedó desactualizada. Recárguela e intente de nuevo."), request)
    respuesta = await siguiente(request)
    # Toda descarga queda en la bitácora: quién (la sesión), qué y cuándo (C29).
    if (es_api and metodo == "GET" and "attachment" in respuesta.headers.get("content-disposition", "")
            and not ruta.startswith("/api/renta/")):
        from ..repositorio import bitacora

        bitacora.registrar("descarga", None, ruta=ruta[:200], ip=request.client.host if request.client else "?")
    return _con_encabezados(respuesta, request)
