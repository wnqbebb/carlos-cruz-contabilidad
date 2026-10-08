"""Punto de entrada del ejecutable instalado en el computador del cliente.

Levanta el servidor, abre el navegador y deja una ventana con el estado. Es lo
que arranca cuando se hace doble clic en CarlosCruz.exe.

Diferencias con correrlo desde el código fuente:

* Los archivos de datos (PUC, parámetros, interfaz compilada) viajan DENTRO del
  ejecutable y PyInstaller los descomprime en una carpeta temporal, que cambia
  en cada arranque. Por eso aquí se le dice a la aplicación dónde quedaron.
* La base de datos y el `.env` NO pueden vivir ahí: se perderían al cerrar. Van
  en `Documentos\\Carlos Cruz`, que es del usuario y sobrevive a las
  actualizaciones del programa.
"""
from __future__ import annotations

import os
import socket
import sys
import threading
import time
import webbrowser
from pathlib import Path


def _empaquetado() -> bool:
    return getattr(sys, "frozen", False)


def _raiz_recursos() -> Path:
    """Carpeta donde quedaron los archivos incluidos en el ejecutable."""
    if _empaquetado():
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    return Path(__file__).resolve().parents[1]


def _carpeta_datos() -> Path:
    """Dónde se guardan la base y la configuración: en los documentos del usuario."""
    base = Path(os.environ.get("USERPROFILE") or Path.home())
    carpeta = base / "Documents" / "Carlos Cruz"
    try:
        carpeta.mkdir(parents=True, exist_ok=True)
    except OSError:
        carpeta = Path.home() / "Carlos Cruz"
        carpeta.mkdir(parents=True, exist_ok=True)
    return carpeta


def _preparar_entorno() -> tuple[Path, Path]:
    recursos = _raiz_recursos()
    datos = _carpeta_datos()

    # La aplicación lee estas variables al importar `app.config`, así que hay
    # que fijarlas ANTES de importarla.
    os.environ.setdefault("CC_SQLITE", str(datos / "carloscruz.db"))

    env_usuario = datos / "configuracion.env"
    if env_usuario.exists():
        os.environ.setdefault("CC_ENV", str(env_usuario))
    else:
        env_usuario.write_text(
            "# Configuracion de Carlos Cruz\n"
            "# Si deja esto como esta, los datos se guardan solo en este computador,\n"
            "# en la carpeta Documentos\\Carlos Cruz. Es lo recomendado.\n"
            "#\n"
            "# Para guardar en linea (Supabase), llene DATABASE_URL y ponga\n"
            "# ALMACENAMIENTO=supabase\n"
            "ALMACENAMIENTO=local\n"
            "DATABASE_URL=\n",
            encoding="utf-8",
        )

    if _empaquetado():
        # `app.config` resuelve las rutas a partir del archivo del módulo, que
        # dentro del ejecutable no sirve. Se le indican explícitamente.
        os.environ.setdefault("CC_DATA", str(recursos / "data"))
        os.environ.setdefault("CC_FRONTEND", str(recursos / "frontend" / "dist"))
        sys.path.insert(0, str(recursos))
    else:
        sys.path.insert(0, str(recursos / "backend"))

    return recursos, datos


def _puerto_libre(preferido: int = 8000) -> int:
    for puerto in [preferido, 8001, 8002, 8080, 8765, 0]:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", puerto))
                return s.getsockname()[1]
            except OSError:
                continue
    return 8000


def _abrir_navegador(url: str) -> None:
    def tarea() -> None:
        time.sleep(2.0)
        try:
            webbrowser.open(url)
        except Exception:
            pass

    threading.Thread(target=tarea, daemon=True).start()


def main() -> int:
    recursos, datos = _preparar_entorno()

    import uvicorn

    from app.config import MARCA, VERSION
    from app.db import diagnostico
    from app.repositorio import parametros as repo_parametros

    puerto = _puerto_libre()
    url = f"http://localhost:{puerto}"

    print("=" * 62)
    print(f"  {MARCA}  v{VERSION}  -  Contabilidad que cuadra")
    print("=" * 62)
    print(f"  Sus datos:     {datos}")
    print(f"  Configuracion: {datos / 'configuracion.env'}")

    estado = diagnostico()
    if estado["conectado"]:
        print(f"  Base de datos: OK ({estado['motor']})")
        try:
            repo_parametros.sembrar_si_vacio()
        except Exception as ex:
            print(f"  Aviso: no se pudieron sembrar los parametros legales ({ex})")
    else:
        print(f"  Base de datos: ERROR - {estado['error']}")

    print()
    print(f"  Abriendo en:   {url}")
    print("  Para cerrar la aplicacion, cierre esta ventana.")
    print("=" * 62)
    print()

    _abrir_navegador(url)

    from app.main import app

    uvicorn.run(app, host="127.0.0.1", port=puerto, log_level="warning")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        pass
    except Exception as ex:  # una ventana que se cierra sola no dice nada útil
        import traceback

        print("\n" + "=" * 62)
        print("  No se pudo iniciar Carlos Cruz.")
        print("=" * 62)
        traceback.print_exc()
        print()
        input("Presione Enter para cerrar...")
        raise SystemExit(1) from ex
