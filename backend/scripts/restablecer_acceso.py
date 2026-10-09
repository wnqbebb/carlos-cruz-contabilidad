"""Script para restablecer el acceso en local (v2.4).

Borra los usuarios y sesiones actuales para que la aplicación vuelva al estado «Crear su acceso».
Solo debe ejecutarse localmente por el administrador.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Agregar backend al path
raiz_backend = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(raiz_backend))

from app.db import conexion
from app.esquema import usuarios as TU
from app.esquema import codigos_recuperacion as TC
from app.esquema import sesiones_acceso as TS
from app.config import archivo_env
from app.seguridad import secretos
from sqlalchemy import delete

def restablecer():
    print("=" * 60)
    print("CARLOS CRUZ · Restablecer acceso local")
    print("=" * 60)
    try:
        with conexion() as cn:
            n_ses = cn.execute(delete(TS)).rowcount
            n_cod = cn.execute(delete(TC)).rowcount
            n_usu = cn.execute(delete(TU)).rowcount
        print(f"-> Sesiones eliminadas: {n_ses}")
        print(f"-> Códigos de recuperación eliminados: {n_cod}")
        print(f"-> Usuarios eliminados: {n_usu}")
        
        env = archivo_env()
        if env and env.is_file():
            secretos.quitar_lineas(env, ("CC_USUARIO", "CC_CLAVE_HASH"))
            print(f"-> Limpiadas variables de usuario previas en {env.name}")

        print("\n¡ÉXITO! El acceso ha sido restablecido.")
        print("Ahora puede abrir la aplicación en su navegador:")
        print("  http://localhost:8000  o  http://localhost:5173")
        print("y verá la pantalla para «Crear su acceso» con el usuario y contraseña que elija.\n")
    except Exception as ex:
        print(f"\n[ERROR] No se pudo restablecer el acceso: {ex}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    restablecer()
