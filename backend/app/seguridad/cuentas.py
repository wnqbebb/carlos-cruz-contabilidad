"""El usuario del contador: creación, contraseña, códigos de recuperación y TOTP (controles C1–C4).

Un solo usuario por instalación. Los códigos de recuperación se muestran una vez y en la base
queda solo su hash (Argon2id). El secreto TOTP se guarda cifrado con la clave de datos.
"""
from __future__ import annotations

import base64
import os
import secrets
from datetime import datetime, timezone

import pyotp
import segno
from sqlalchemy import delete, func, insert, select, update

from ..db import conexion, lectura
from ..esquema import codigos_recuperacion as TC
from ..esquema import usuarios as TU
from . import cifrado, claves

CANTIDAD_CODIGOS = 10
EMISOR = "Carlos Cruz"


class ErrorCuenta(Exception):
    def __init__(self, codigo: str, mensaje: str):
        super().__init__(mensaje)
        self.codigo = codigo


def ahora() -> datetime:
    return datetime.now(timezone.utc)


def hay_usuario() -> bool:
    asegurar_desde_entorno()
    with lectura() as cn:
        return bool(cn.execute(select(func.count()).select_from(TU)).scalar())


def asegurar_desde_entorno() -> None:
    """Instalaciones de la v2.2: el usuario estaba en el archivo de configuración (hash bcrypt).

    Si la tabla está vacía y el entorno trae `CC_USUARIO` y `CC_CLAVE_HASH`, se importa tal cual;
    el hash se pasa a Argon2id la primera vez que el contador ingresa.
    """
    nombre = (os.getenv("CC_USUARIO") or "").strip()
    hash_ = (os.getenv("CC_CLAVE_HASH") or "").strip()
    if not nombre or not hash_:
        return
    with conexion() as cn:
        if cn.execute(select(func.count()).select_from(TU)).scalar():
            return
        cn.execute(insert(TU).values(usuario=nombre.lower(), hash=hash_, totp_activo=False))


def obtener(nombre: str) -> dict | None:
    with lectura() as cn:
        f = cn.execute(select(TU).where(TU.c.usuario == (nombre or "").strip().lower())).first()
    return dict(f._mapping) if f else None


def por_id(usuario_id: int) -> dict | None:
    with lectura() as cn:
        f = cn.execute(select(TU).where(TU.c.id == usuario_id)).first()
    return dict(f._mapping) if f else None


def unico() -> dict | None:
    with lectura() as cn:
        f = cn.execute(select(TU).order_by(TU.c.id)).first()
    return dict(f._mapping) if f else None


def _validar_clave(clave: str, usuario: str) -> None:
    ev = claves.evaluar(clave, usuario)
    if not ev["valida"]:
        raise ErrorCuenta("clave_debil", " ".join(ev["problemas"]))


def crear(nombre: str, clave: str) -> tuple[dict, list[str]]:
    """Primer uso: crea el único usuario y devuelve sus códigos de recuperación (se muestran una vez)."""
    nombre = (nombre or "").strip().lower()
    if not (3 <= len(nombre) <= 40) or not nombre.replace(".", "").replace("_", "").replace("-", "").isalnum():
        raise ErrorCuenta("usuario_invalido", "El usuario debe tener entre 3 y 40 letras o números.")
    _validar_clave(clave, nombre)
    if hay_usuario():
        raise ErrorCuenta("ya_existe", "Ya hay un usuario creado en esta instalación.")
    with conexion() as cn:
        cn.execute(insert(TU).values(usuario=nombre, hash=claves.hash_clave(clave), totp_activo=False,
                                     clave_cambiada=ahora()))
    u = obtener(nombre)
    return u, nuevos_codigos(u["id"])  # type: ignore[index]


def verificar(nombre: str, clave: str) -> dict | None:
    u = obtener(nombre)
    if not u:
        claves.verificar(claves.hash_clave("x" * 12), clave)  # mismo tiempo exista o no el usuario
        return None
    ok, rehacer = claves.verificar(u["hash"], clave)
    if not ok:
        return None
    if rehacer:  # bcrypt de la v2.2 → Argon2id
        with conexion() as cn:
            cn.execute(update(TU).where(TU.c.id == u["id"]).values(hash=claves.hash_clave(clave)))
    return u


def cambiar_clave(usuario_id: int, nueva: str) -> None:
    u = por_id(usuario_id)
    _validar_clave(nueva, u["usuario"] if u else "")
    with conexion() as cn:
        cn.execute(update(TU).where(TU.c.id == usuario_id).values(hash=claves.hash_clave(nueva), clave_cambiada=ahora()))


# ── códigos de recuperación ─────────────────────────────────────────────
def _codigo() -> str:
    alfabeto = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"   # sin 0/O ni 1/I
    crudo = "".join(secrets.choice(alfabeto) for _ in range(10))
    return f"{crudo[:5]}-{crudo[5:]}"


def nuevos_codigos(usuario_id: int) -> list[str]:
    codigos = [_codigo() for _ in range(CANTIDAD_CODIGOS)]
    with conexion() as cn:
        cn.execute(delete(TC).where(TC.c.usuario_id == usuario_id))
        cn.execute(insert(TC), [{"usuario_id": usuario_id, "hash": claves.hash_clave(c)} for c in codigos])
    return codigos


def usar_codigo(usuario_id: int, codigo: str) -> bool:
    limpio = (codigo or "").strip().upper().replace(" ", "")
    if len(limpio) == 10:
        limpio = f"{limpio[:5]}-{limpio[5:]}"
    with lectura() as cn:
        filas = cn.execute(select(TC.c.id, TC.c.hash).where(TC.c.usuario_id == usuario_id, TC.c.usado.is_(None))).all()
    for f in filas:
        if claves.verificar(f.hash, limpio)[0]:
            with conexion() as cn:
                cn.execute(update(TC).where(TC.c.id == f.id).values(usado=ahora()))
            return True
    return False


def codigos_restantes(usuario_id: int) -> int:
    with lectura() as cn:
        return int(cn.execute(select(func.count()).select_from(TC)
                              .where(TC.c.usuario_id == usuario_id, TC.c.usado.is_(None))).scalar() or 0)


# ── verificación en dos pasos (TOTP) ───────────────────────────────────
def _abrir(cifrado_b64: str | None) -> str | None:
    if not cifrado_b64:
        return None
    return cifrado.descifrar(base64.b64decode(cifrado_b64), contexto=b"totp").decode("ascii")


def _sellar(secreto: str) -> str:
    return base64.b64encode(cifrado.cifrar(secreto.encode("ascii"), contexto=b"totp")).decode("ascii")


def iniciar_totp(usuario_id: int) -> dict:
    u = por_id(usuario_id)
    secreto = pyotp.random_base32()
    with conexion() as cn:
        cn.execute(update(TU).where(TU.c.id == usuario_id).values(totp_pendiente=_sellar(secreto)))
    uri = pyotp.TOTP(secreto).provisioning_uri(name=u["usuario"], issuer_name=EMISOR)
    qr = segno.make(uri, error="m").svg_data_uri(scale=5, border=2, dark="#141414", light="#ffffff")
    return {"qr": qr, "secreto": secreto}


def confirmar_totp(usuario_id: int, codigo: str) -> list[str]:
    u = por_id(usuario_id)
    secreto = _abrir(u.get("totp_pendiente"))
    if not secreto or not pyotp.TOTP(secreto).verify((codigo or "").strip(), valid_window=1):
        raise ErrorCuenta("totp_invalido", "Ese código no es válido. Escriba el que muestra la aplicación ahora.")
    with conexion() as cn:
        cn.execute(update(TU).where(TU.c.id == usuario_id).values(totp_secreto=_sellar(secreto), totp_pendiente=None,
                                                                 totp_activo=True))
    return nuevos_codigos(usuario_id)


def desactivar_totp(usuario_id: int) -> None:
    with conexion() as cn:
        cn.execute(update(TU).where(TU.c.id == usuario_id).values(totp_secreto=None, totp_pendiente=None,
                                                                 totp_activo=False))


def verificar_segundo_paso(u: dict, codigo: str) -> bool:
    """TOTP vigente, o un código de recuperación (de un solo uso)."""
    if not u.get("totp_activo"):
        return True
    secreto = _abrir(u.get("totp_secreto"))
    limpio = (codigo or "").strip().replace(" ", "")
    if secreto and limpio.isdigit() and pyotp.TOTP(secreto).verify(limpio, valid_window=1):
        return True
    return bool(limpio) and usar_codigo(u["id"], limpio)
