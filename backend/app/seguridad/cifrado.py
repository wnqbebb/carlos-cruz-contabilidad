"""Cifrado en disco con AES-256-GCM (controles C25 y C32).

Formato: `CC1` + nonce de 12 bytes + texto cifrado con su etiqueta de autenticación.
Un archivo alterado no se descifra (la etiqueta no cuadra): se rechaza en vez de leer basura.
"""
from __future__ import annotations

import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from . import secretos

CABECERA = b"CC1"


class CifradoInvalido(Exception):
    pass


def cifrar(datos: bytes, clave: bytes | None = None, contexto: bytes = b"") -> bytes:
    clave = clave or secretos.clave_datos()
    nonce = os.urandom(12)
    return CABECERA + nonce + AESGCM(clave).encrypt(nonce, datos, contexto or None)


def descifrar(datos: bytes, clave: bytes | None = None, contexto: bytes = b"") -> bytes:
    if not datos.startswith(CABECERA) or len(datos) < len(CABECERA) + 12 + 16:
        raise CifradoInvalido("El archivo no está cifrado por esta aplicación.")
    clave = clave or secretos.clave_datos()
    nonce = datos[len(CABECERA):len(CABECERA) + 12]
    try:
        return AESGCM(clave).decrypt(nonce, datos[len(CABECERA) + 12:], contexto or None)
    except Exception as ex:
        raise CifradoInvalido("El archivo cifrado fue alterado o la clave no corresponde.") from ex
