"""Mantiene despierto el proyecto de Supabase.

EL PROBLEMA
-----------
El plan gratuito de Supabase **pausa** un proyecto que pasa unos días sin
actividad. Para un contador que trabaja por temporadas eso es inaceptable: si el
cliente se va dos meses, al volver la aplicación no encuentra la base y hay que
entrar al panel de Supabase a despausarla a mano.

LA SOLUCIÓN
-----------
Una consulta trivial cada pocos días cuenta como actividad y el proyecto nunca
se pausa. Este script hace exactamente eso y no escribe nada: solo lee.

CÓMO PROGRAMARLO (elija una)

1. En el computador donde queda instalada la aplicación (Windows):

   programar.bat        ← lo deja corriendo cada 3 días automáticamente

   O a mano, en el Programador de tareas de Windows:
     Acción:   <carpeta>\\.venv\\Scripts\\python.exe
     Argumentos: backend\\mantener_vivo.py
     Iniciar en: <carpeta del proyecto>
     Repetir cada 3 días

2. En GitHub, sin depender de ningún computador encendido:
   ya está el archivo `.github/workflows/mantener-supabase-vivo.yml`.
   Solo hay que guardar `DATABASE_URL` en *Settings → Secrets → Actions*.

Si la aplicación trabaja en modo local (SQLite), este script no hace falta: una
base local nunca se pausa.
"""
from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from sqlalchemy import func, select, text  # noqa: E402

from app import db  # noqa: E402
from app.config import ES_POSTGRES, MARCA  # noqa: E402
from app.esquema import clientes  # noqa: E402


def main() -> int:
    sello = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{sello}] {MARCA} - manteniendo viva la base")

    if not ES_POSTGRES:
        print("  La base es local (SQLite): no se pausa nunca. Nada que hacer.")
        return 0

    try:
        with db.lectura() as cn:
            cn.execute(text("select 1"))
            cuantos = cn.execute(select(func.count()).select_from(clientes)).scalar_one()
        print(f"  OK. Supabase respondio. Clientes en la base: {cuantos}.")
        print("  El proyecto queda marcado como activo.")
        return 0
    except Exception as ex:
        print(f"  ERROR: no se pudo consultar la base.\n  {ex}")
        print("  Si el proyecto ya estaba pausado, despauselo una vez desde")
        print("  https://supabase.com/dashboard y vuelva a ejecutar esto.")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
