"""Crea o cambia el usuario y la contraseña del contador (adición A2).

Uso, desde la carpeta del programa:

    .venv\\Scripts\\python backend\\crear_usuario.py

Pregunta el usuario y la contraseña (dos veces) y guarda en el archivo de
configuración (`backend/.env`, o el que indique `CC_ENV`):

    CC_USUARIO=…          el nombre de usuario
    CC_CLAVE_HASH=…       el hash bcrypt de la contraseña (la contraseña no se guarda)
    CLAVE_SESION=…        la clave que firma las sesiones; se crea si falta

Para automatizar (por ejemplo, la copia aislada de pruebas):

    python backend/crear_usuario.py --usuario prueba --clave "…" --archivo ruta/.env

Después de cambiarlo, reinicie la aplicación (cierre la ventana de iniciar.bat
y ábrala otra vez). Cambiar la contraseña cierra las sesiones abiertas solo si
también cambia CLAVE_SESION: use --nueva-clave-sesion para eso.
"""
from __future__ import annotations

import argparse
import getpass
import os
import secrets
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))

MINIMO = 8


def _archivo(pedido: str | None) -> Path:
    if pedido:
        return Path(pedido)
    propio = (os.getenv("CC_ENV") or "").strip()
    return Path(propio) if propio else AQUI / ".env"


def _leer(ruta: Path) -> list[str]:
    if ruta.exists():
        return ruta.read_text(encoding="utf-8-sig").splitlines()
    ejemplo = AQUI / ".env.example"
    return ejemplo.read_text(encoding="utf-8-sig").splitlines() if ejemplo.exists() and ruta == AQUI / ".env" else []


def _poner(lineas: list[str], clave: str, valor: str) -> list[str]:
    salida, puesto = [], False
    for linea in lineas:
        if linea.split("=", 1)[0].strip() == clave and not linea.lstrip().startswith("#"):
            if not puesto:
                salida.append(f"{clave}={valor}")
                puesto = True
            continue
        salida.append(linea)
    if not puesto:
        salida.append(f"{clave}={valor}")
    return salida


def _valor(lineas: list[str], clave: str) -> str:
    for linea in lineas:
        if linea.split("=", 1)[0].strip() == clave and not linea.lstrip().startswith("#"):
            return linea.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


def main(argv: list[str] | None = None) -> int:
    from app.sesion import CLAVE_DE_EJEMPLO, hash_de

    ap = argparse.ArgumentParser(description="Crea o cambia el usuario del contador.")
    ap.add_argument("--usuario", help="Nombre de usuario (si no se da, se pregunta)")
    ap.add_argument("--clave", help="Contraseña (si no se da, se pregunta sin mostrarla)")
    ap.add_argument("--archivo", help="Archivo de configuración (por defecto backend/.env)")
    ap.add_argument("--nueva-clave-sesion", action="store_true", help="Cambia también la clave de las sesiones (cierra las abiertas)")
    args = ap.parse_args(argv)

    ruta = _archivo(args.archivo)
    lineas = _leer(ruta)
    actual = _valor(lineas, "CC_USUARIO")

    nombre = (args.usuario or "").strip()
    if not nombre:
        nombre = input(f"Usuario [{actual or 'carlos'}]: ").strip() or actual or "carlos"
    clave = args.clave
    if clave is None:
        clave = getpass.getpass("Contraseña nueva: ")
        if getpass.getpass("Repítala: ") != clave:
            print("Las dos contraseñas no coinciden. No se cambió nada.")
            return 1
    if len(clave) < MINIMO:
        print(f"La contraseña debe tener al menos {MINIMO} caracteres. No se cambió nada.")
        return 1

    lineas = _poner(lineas, "CC_USUARIO", nombre)
    lineas = _poner(lineas, "CC_CLAVE_HASH", hash_de(clave))
    firma = _valor(lineas, "CLAVE_SESION")
    if args.nueva_clave_sesion or len(firma) < 32 or firma == CLAVE_DE_EJEMPLO:
        lineas = _poner(lineas, "CLAVE_SESION", secrets.token_urlsafe(48))
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text("\n".join(lineas) + "\n", encoding="utf-8")
    print(f"Listo: usuario «{nombre}» guardado en {ruta}.")
    print("Reinicie la aplicación para que tome el cambio.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
