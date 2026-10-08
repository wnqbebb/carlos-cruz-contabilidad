"""Entrar y salir (adición A2)."""
from __future__ import annotations

from fastapi import APIRouter, Body, HTTPException, Request
from fastapi.responses import JSONResponse

from .. import sesion
from ..repositorio import bitacora

router = APIRouter(prefix="/api", tags=["sesion"])


def _ip(request: Request) -> str:
    return request.client.host if request.client else "?"


def _es_https(request: Request) -> bool:
    return request.url.scheme == "https" or request.headers.get("x-forwarded-proto", "").lower() == "https"


@router.get("/sesion")
def estado(request: Request):
    """¿Hay sesión? La pantalla de ingreso lo consulta al abrir la aplicación."""
    nombre = sesion.leer(request.cookies.get(sesion.COOKIE))
    return {"activa": bool(nombre), "usuario": nombre, "configurado": sesion.configurado()}


@router.post("/sesion")
def entrar(request: Request, datos: dict = Body(...)):
    nombre = str(datos.get("usuario") or "").strip()
    clave = str(datos.get("clave") or "")
    if not sesion.configurado():
        raise HTTPException(503, {
            "codigo": "sin_usuario",
            "mensaje": "Todavía no hay un usuario creado. En la carpeta del programa ejecute: "
                       "python backend/crear_usuario.py",
        })
    falta = sesion.espera(_ip(request), nombre)
    if falta:
        minutos = max(1, round(falta / 60))
        raise HTTPException(429, {
            "codigo": "demasiados_intentos",
            "mensaje": f"Demasiados intentos fallidos. Espere {minutos} minuto(s) y vuelva a intentar.",
            "segundos": falta,
        })
    if not sesion.verificar(nombre, clave):
        sesion.fallo(_ip(request), nombre)
        bitacora.registrar("ingreso_fallido", None, usuario=nombre[:60], ip=_ip(request))
        raise HTTPException(401, {"codigo": "credenciales", "mensaje": "Usuario o contraseña incorrectos."})
    sesion.acierto(_ip(request), nombre)
    respuesta = JSONResponse({"activa": True, "usuario": sesion.usuario()})
    respuesta.set_cookie(sesion.COOKIE, sesion.emitir(sesion.usuario()), max_age=sesion.DURACION, httponly=True,
                         samesite="lax", secure=_es_https(request), path="/")
    return respuesta


@router.post("/sesion/salir")
def salir(request: Request):
    respuesta = JSONResponse({"activa": False})
    respuesta.delete_cookie(sesion.COOKIE, path="/", httponly=True, samesite="lax", secure=_es_https(request))
    return respuesta
