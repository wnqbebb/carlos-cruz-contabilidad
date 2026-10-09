"""Herramienta de DESARROLLO: crea o cambia el usuario del contador en la base (v2.3).

El contador no la necesita: la primera vez la aplicación muestra «Crear su acceso» en el
navegador, y si olvida la contraseña usa un código de recuperación. Esto sirve para la copia
aislada de pruebas y para automatizar:

    python backend/crear_usuario.py --usuario prueba --clave "…" [--archivo ruta/.env]

Guarda el usuario en la base que indique la configuración (CC_SQLITE / DATABASE_URL), con la
contraseña en Argon2id. Si se da `--archivo`, solo anota en él `CC_USUARIO=…` (nunca el hash
ni la contraseña) para que los scripts sepan que ya se creó.
"""
from __future__ import annotations

import argparse
import getpass
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Crea o cambia el usuario del contador (desarrollo).")
    ap.add_argument("--usuario")
    ap.add_argument("--clave")
    ap.add_argument("--archivo", help="Archivo donde anotar CC_USUARIO (opcional)")
    args = ap.parse_args(argv)

    from app import db
    from app.seguridad import claves, cuentas

    db.preparar()
    usuario = (args.usuario or input("Usuario: ")).strip().lower()
    clave = args.clave or getpass.getpass("Contraseña: ")
    evaluacion = claves.evaluar(clave, usuario)
    if not evaluacion["valida"]:
        print("La contraseña no sirve: " + " ".join(evaluacion["problemas"]))
        return 1
    existente = cuentas.obtener(usuario) or cuentas.unico()
    if existente:
        cuentas.cambiar_clave(existente["id"], clave)
        print(f"Contraseña de «{existente['usuario']}» cambiada.")
    else:
        _, codigos = cuentas.crear(usuario, clave)
        print(f"Usuario «{usuario}» creado. Códigos de recuperación (guárdelos):")
        for c in codigos:
            print("  " + c)
    if args.archivo:
        ruta = Path(args.archivo)
        lineas = ruta.read_text(encoding="utf-8").splitlines() if ruta.exists() else []
        lineas = [l for l in lineas if not l.startswith(("CC_USUARIO=", "CC_CLAVE_HASH=", "CLAVE_SESION="))]
        lineas.append(f"CC_USUARIO={usuario}")
        ruta.write_text("\n".join(lineas) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
