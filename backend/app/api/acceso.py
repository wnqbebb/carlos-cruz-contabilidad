"""La cuenta del contador (v2.3 · Fase 6): primer uso, recuperación, contraseña, TOTP y sesiones."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Body, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy import func, select

from .. import sesion
from ..db import lectura
from ..esquema import bitacora as TB
from ..repositorio import bitacora
from ..seguridad import claves, cuentas
from .sesion import es_local, ip_de, poner_cookie

router = APIRouter(prefix="/api/acceso", tags=["acceso"])


def _error(ex: cuentas.ErrorCuenta, estado: int = 422):
    return HTTPException(estado, {"codigo": ex.codigo, "mensaje": str(ex)})


@router.post("/politica")
def politica(datos: dict = Body(...)):
    """Medidor de fortaleza de la pantalla: problemas y puntaje, sin guardar nada."""
    return claves.evaluar(str(datos.get("clave") or ""), str(datos.get("usuario") or ""))


@router.post("/primer-uso")
def primer_uso(request: Request, datos: dict = Body(...)):
    """«Crear su acceso»: solo si no hay usuario."""
    import os
    codigo_env = (os.getenv("CC_CODIGO_INSTALACION") or "").strip()
    es_loc = es_local(request)
    if not es_loc:
        if not codigo_env:
            raise HTTPException(403, {"codigo": "solo_local",
                                      "mensaje": "El acceso se crea desde el computador donde está instalada la aplicación."})
        codigo_dado = str(datos.get("codigo_instalacion") or "").strip()
        if codigo_dado != codigo_env:
            raise HTTPException(403, {"codigo": "codigo_instalacion_invalido",
                                      "mensaje": "El código de instalación no es correcto."})
    if cuentas.hay_usuario():
        raise HTTPException(409, {"codigo": "ya_existe", "mensaje": "Ya hay un usuario creado."})
    try:
        u, codigos = cuentas.crear(str(datos.get("usuario") or ""), str(datos.get("clave") or ""))
    except cuentas.ErrorCuenta as ex:
        raise _error(ex) from ex
    token, csrf = sesion.abrir(u["id"], ip_de(request), request.headers.get("user-agent", ""))
    bitacora.registrar("acceso_creado", None, usuario=u["usuario"], ip=ip_de(request))
    respuesta = JSONResponse({"usuario": u["usuario"], "codigos": codigos, "csrf": csrf})
    poner_cookie(respuesta, request, token)
    return respuesta


@router.post("/recuperar")
def recuperar(request: Request, datos: dict = Body(...)):
    """«¿Olvidó la contraseña?»: un código de recuperación deja poner una nueva (control C2)."""
    nombre = str(datos.get("usuario") or "").strip()
    ip = ip_de(request)
    falta = sesion.espera(ip, nombre)
    if falta:
        raise HTTPException(429, {"codigo": "demasiados_intentos", "segundos": falta,
                                  "mensaje": "Demasiados intentos fallidos. Espere unos minutos y vuelva a intentar."})
    u = cuentas.obtener(nombre)
    if not u or not cuentas.usar_codigo(u["id"], str(datos.get("codigo") or "")):
        sesion.fallo(ip, nombre)
        bitacora.registrar("recuperacion_fallida", None, usuario=nombre[:60], ip=ip)
        raise HTTPException(401, {"codigo": "codigo_invalido", "mensaje": "El usuario o el código de recuperación no son válidos."})
    try:
        cuentas.cambiar_clave(u["id"], str(datos.get("nueva") or ""))
    except cuentas.ErrorCuenta as ex:
        raise _error(ex) from ex
    sesion.cerrar_todas(u["id"])
    sesion.acierto(ip, nombre)
    bitacora.registrar("clave_recuperada", None, usuario=u["usuario"], ip=ip)
    return {"ok": True, "codigos_restantes": cuentas.codigos_restantes(u["id"])}


@router.get("/estado")
def estado(request: Request):
    """Lo que muestra el panel Sistema › Acceso."""
    info = request.state.sesion
    u = cuentas.por_id(info["usuario_id"])
    desde = datetime.now(timezone.utc) - timedelta(hours=24)
    with lectura() as cn:
        fallidos = int(cn.execute(select(func.count()).select_from(TB).where(
            TB.c.accion.in_(("ingreso_fallido", "reautenticacion_fallida", "recuperacion_fallida")),
            TB.c.creado >= desde)).scalar() or 0)
    return {
        "usuario": u["usuario"], "totp_activo": bool(u["totp_activo"]),
        "codigos_restantes": cuentas.codigos_restantes(u["id"]),
        "sesiones": len(sesion.abiertas(u["id"])), "fallidos_24h": fallidos,
    }


@router.post("/clave")
def cambiar_clave(request: Request, datos: dict = Body(...)):
    """Cambiar la contraseña: pide la actual y cierra las demás sesiones."""
    info = request.state.sesion
    u = cuentas.por_id(info["usuario_id"])
    if not cuentas.verificar(u["usuario"], str(datos.get("actual") or "")):
        sesion.fallo(ip_de(request), u["usuario"])
        raise HTTPException(401, {"codigo": "credenciales", "mensaje": "La contraseña actual no es correcta."})
    try:
        cuentas.cambiar_clave(u["id"], str(datos.get("nueva") or ""))
    except cuentas.ErrorCuenta as ex:
        raise _error(ex) from ex
    cerradas = sesion.cerrar_todas(u["id"], excepto=info["id"])
    bitacora.registrar("clave_cambiada", None, usuario=u["usuario"], ip=ip_de(request), sesiones_cerradas=cerradas)
    return {"ok": True, "sesiones_cerradas": cerradas}


@router.post("/codigos")
def nuevos_codigos(request: Request):
    sesion.exigir_reautenticacion(request)
    info = request.state.sesion
    bitacora.registrar("codigos_regenerados", None, ip=ip_de(request))
    return {"codigos": cuentas.nuevos_codigos(info["usuario_id"])}


@router.post("/totp/iniciar")
def totp_iniciar(request: Request):
    sesion.exigir_reautenticacion(request)
    return cuentas.iniciar_totp(request.state.sesion["usuario_id"])


@router.post("/totp/confirmar")
def totp_confirmar(request: Request, datos: dict = Body(...)):
    try:
        codigos = cuentas.confirmar_totp(request.state.sesion["usuario_id"], str(datos.get("codigo") or ""))
    except cuentas.ErrorCuenta as ex:
        raise _error(ex) from ex
    bitacora.registrar("totp_activado", None, ip=ip_de(request))
    return {"codigos": codigos}


@router.post("/totp/desactivar")
def totp_desactivar(request: Request):
    sesion.exigir_reautenticacion(request)
    cuentas.desactivar_totp(request.state.sesion["usuario_id"])
    bitacora.registrar("totp_desactivado", None, ip=ip_de(request))
    return {"ok": True}


@router.post("/sesiones/cerrar-todas")
def cerrar_todas(request: Request):
    info = request.state.sesion
    n = sesion.cerrar_todas(info["usuario_id"], excepto=info["id"])
    bitacora.registrar("sesiones_cerradas", None, ip=ip_de(request), cantidad=n)
    return {"cerradas": n}
