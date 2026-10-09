"""Entrar, salir y confirmar la contraseña (v2.3 · Fase 6)."""
from __future__ import annotations

from fastapi import APIRouter, Body, HTTPException, Request
from fastapi.responses import JSONResponse

from .. import sesion
from ..repositorio import bitacora
from ..seguridad import cuentas

router = APIRouter(prefix="/api", tags=["sesion"])

LOCALES = {"127.0.0.1", "::1", "localhost"}


def ip_de(request: Request) -> str:
    return request.client.host if request.client else "?"


def es_local(request: Request) -> bool:
    import os

    extra = {h.strip() for h in (os.getenv("CC_HOSTS_LOCALES") or "").split(",") if h.strip()}
    return ip_de(request) in LOCALES | extra


def _es_https(request: Request) -> bool:
    return request.url.scheme == "https" or request.headers.get("x-forwarded-proto", "").lower() == "https"


def poner_cookie(respuesta: JSONResponse, request: Request, token: str) -> None:
    respuesta.set_cookie(sesion.COOKIE, token, max_age=sesion.DURACION, httponly=True, samesite="lax",
                         secure=_es_https(request), path="/")


@router.get("/sesion")
def estado(request: Request):
    """¿Hay sesión? La pantalla de ingreso lo consulta al abrir la aplicación."""
    import os
    info = sesion.leer(request.cookies.get(sesion.COOKIE))
    u = cuentas.por_id(info["usuario_id"]) if info else None
    hay = cuentas.hay_usuario()
    codigo_env = bool((os.getenv("CC_CODIGO_INSTALACION") or "").strip())
    es_loc = es_local(request)
    return {
        "activa": bool(u), "usuario": u["usuario"] if u else None, "configurado": hay,
        # El primer uso solo se ofrece desde el mismo equipo o con código en la nube.
        "puede_crear": (not hay) and (es_loc or codigo_env),
        "requiere_codigo_instalacion": (not hay) and (not es_loc) and codigo_env,
        "csrf": info["csrf"] if u else None,
        "totp": bool(u and u["totp_activo"]),
        "reautenticacion_vigente": bool(u) and _reautenticada(info),
    }


def _reautenticada(info: dict) -> bool:
    from datetime import datetime, timedelta, timezone

    r = info.get("reautenticada")
    if r is None:
        return False
    r = r if r.tzinfo else r.replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc) - r < timedelta(seconds=sesion.REAUTENTICACION - 30)


@router.post("/sesion")
def entrar(request: Request, datos: dict = Body(...)):
    nombre = str(datos.get("usuario") or "").strip()
    clave = str(datos.get("clave") or "")
    codigo = str(datos.get("codigo") or "")
    if not cuentas.hay_usuario():
        raise HTTPException(503, {"codigo": "sin_usuario",
                                  "mensaje": "Todavía no hay un usuario creado. Abra la aplicación en este mismo "
                                             "equipo para crear su acceso."})
    ip = ip_de(request)
    falta = sesion.espera(ip, nombre)
    if falta:
        minutos = max(1, round(falta / 60))
        raise HTTPException(429, {"codigo": "demasiados_intentos", "segundos": falta,
                                  "mensaje": f"Demasiados intentos fallidos. Espere {minutos} minuto(s) y vuelva a intentar."})
    u = cuentas.verificar(nombre, clave)
    if not u:
        sesion.fallo(ip, nombre)
        bitacora.registrar("ingreso_fallido", None, usuario=nombre[:60], ip=ip)
        raise HTTPException(401, {"codigo": "credenciales", "mensaje": "Usuario o contraseña incorrectos."})
    if u["totp_activo"]:
        if not codigo:
            raise HTTPException(401, {"codigo": "requiere_totp",
                                      "mensaje": "Escriba el código de su aplicación de verificación."})
        if not cuentas.verificar_segundo_paso(u, codigo):
            sesion.fallo(ip, nombre)
            bitacora.registrar("ingreso_fallido", None, usuario=nombre[:60], ip=ip, motivo="segundo_paso")
            raise HTTPException(401, {"codigo": "totp_invalido", "mensaje": "El código de verificación no es válido."})
    sesion.acierto(ip, nombre)
    # Rotación: cualquier cookie anterior de este navegador queda sin efecto.
    sesion.cerrar(request.cookies.get(sesion.COOKIE))
    token, csrf = sesion.abrir(u["id"], ip, request.headers.get("user-agent", ""))
    bitacora.registrar("ingreso", None, usuario=u["usuario"], ip=ip)
    respuesta = JSONResponse({"activa": True, "usuario": u["usuario"], "csrf": csrf})
    poner_cookie(respuesta, request, token)
    return respuesta


@router.post("/sesion/salir")
def salir(request: Request):
    sesion.cerrar(request.cookies.get(sesion.COOKIE))
    respuesta = JSONResponse({"activa": False})
    respuesta.delete_cookie(sesion.COOKIE, path="/", httponly=True, samesite="lax", secure=_es_https(request))
    return respuesta


@router.post("/sesion/reautenticar")
def reautenticar(request: Request, datos: dict = Body(...)):
    """Confirma la contraseña (y el segundo paso) antes de una acción delicada."""
    info = request.state.sesion
    u = cuentas.por_id(info["usuario_id"])
    ip = ip_de(request)
    falta = sesion.espera(ip, u["usuario"])
    if falta:
        raise HTTPException(429, {"codigo": "demasiados_intentos", "segundos": falta,
                                  "mensaje": "Demasiados intentos fallidos. Espere unos minutos."})
    if not cuentas.verificar(u["usuario"], str(datos.get("clave") or "")) or \
            not cuentas.verificar_segundo_paso(u, str(datos.get("codigo") or "")):
        sesion.fallo(ip, u["usuario"])
        bitacora.registrar("reautenticacion_fallida", None, usuario=u["usuario"], ip=ip)
        raise HTTPException(401, {"codigo": "credenciales", "mensaje": "La contraseña o el código no son correctos."})
    sesion.marcar_reautenticada(info["id"])
    return {"ok": True}
