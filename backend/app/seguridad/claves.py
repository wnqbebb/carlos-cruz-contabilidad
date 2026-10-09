"""Contraseñas: Argon2id, política y migración de los hashes bcrypt anteriores (control C3)."""
from __future__ import annotations

import os
import re
from functools import lru_cache

import bcrypt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

from ..config import DATA

MINIMO = 12


@lru_cache(maxsize=1)
def _hasher() -> PasswordHasher:
    if os.getenv("CC_ARGON_RAPIDO") == "1":  # solo pruebas: el mismo algoritmo con menos costo
        return PasswordHasher(time_cost=1, memory_cost=1024, parallelism=1)
    return PasswordHasher()  # Argon2id, 64 MiB, 3 pasadas (recomendación de la RFC 9106)


def hash_clave(clave: str) -> str:
    return _hasher().hash(clave)


def verificar(guardado: str, clave: str) -> tuple[bool, bool]:
    """(correcta, hay que volver a calcular el hash). Acepta hashes bcrypt de la v2.2."""
    if not guardado:
        return False, False
    if guardado.startswith("$2"):
        try:
            return bcrypt.checkpw(clave.encode("utf-8"), guardado.encode("ascii")), True
        except ValueError:
            return False, False
    try:
        _hasher().verify(guardado, clave)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False, False
    return True, _hasher().check_needs_rehash(guardado)


@lru_cache(maxsize=1)
def _comunes() -> frozenset[str]:
    ruta = DATA / "seguridad" / "contrasenas_comunes.txt"
    if not ruta.exists():
        return frozenset()
    return frozenset(l.strip().lower() for l in ruta.read_text(encoding="utf-8").splitlines() if l.strip())


def evaluar(clave: str, usuario: str = "") -> dict:
    """Problemas de la contraseña y un puntaje de 0 a 4 para el medidor de la pantalla."""
    problemas: list[str] = []
    c = clave or ""
    if len(c) < MINIMO:
        problemas.append(f"Use al menos {MINIMO} caracteres.")
    bajo = c.lower()
    if bajo in _comunes() or re.sub(r"\d+$", "", bajo) in _comunes() and len(re.sub(r"\d+$", "", bajo)) >= 6:
        problemas.append("Es una contraseña muy común: la prueban primero.")
    if usuario and usuario.lower() in bajo:
        problemas.append("No use su nombre de usuario dentro de la contraseña.")
    if re.fullmatch(r"(.)\1+", c) or re.search(r"(0123|1234|2345|3456|4567|5678|6789|abcd|qwer|asdf)", bajo) and len(set(bajo)) < 8:
        problemas.append("Evite secuencias o caracteres repetidos.")
    clases = sum(bool(re.search(p, c)) for p in (r"[a-z]", r"[A-Z]", r"\d", r"[^A-Za-z0-9]"))
    puntaje = 0
    if len(c) >= MINIMO:
        puntaje = 1 + (len(c) >= 16) + (clases >= 3) + (len(c) >= 20 or clases == 4)
    if problemas:
        puntaje = min(puntaje, 1)
    return {"valida": not problemas, "problemas": problemas, "puntaje": min(puntaje, 4)}
