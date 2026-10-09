"""Punto de entrada del ejecutable instalado en el computador del cliente (v2.3).

Levanta el servidor en 127.0.0.1, abre el navegador y deja un ícono en la bandeja del
sistema (Abrir · Cerrar). No hay ventana negra, no se pide nada por consola y no se
muestran rutas ni configuración: la primera vez el navegador muestra «Crear su acceso».

* Los archivos de datos (PUC, parámetros, interfaz compilada, lector de fotos) viajan DENTRO
  del ejecutable; PyInstaller los descomprime en una carpeta temporal y aquí se le dice a la
  aplicación dónde quedaron.
* La base y la configuración viven en `Documentos\\Carlos Cruz`, que sobrevive a las
  actualizaciones. Los secretos (conexión a la base, clave de cifrado) no van en archivos de
  texto: los guarda la aplicación en el Administrador de credenciales de Windows.
* Si algo falla al arrancar, el detalle va al registro local y se muestra un aviso corto.
"""
from __future__ import annotations

import logging
import multiprocessing
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

    # La aplicación lee estas variables al importar `app.config`: hay que fijarlas ANTES.
    os.environ.setdefault("CC_SQLITE", str(datos / "carloscruz.db"))
    os.environ.setdefault("CC_DATOS_APP", str(datos / "datos"))
    os.environ.setdefault("CC_RESPALDOS", str(datos / "respaldos"))
    env_usuario = datos / "configuracion.env"
    if not env_usuario.exists():
        env_usuario.write_text(
            "# Configuracion de Carlos Cruz\n"
            "# Si deja esto como esta, los datos se guardan solo en este computador. Es lo recomendado.\n"
            "# Para guardar en linea (Supabase), escriba DATABASE_URL y ALMACENAMIENTO=supabase: al abrir\n"
            "# la aplicacion, la conexion se mueve al Administrador de credenciales de Windows y se borra de aqui.\n"
            "ALMACENAMIENTO=local\n",
            encoding="utf-8",
        )
    os.environ.setdefault("CC_ENV", str(env_usuario))

    if _empaquetado():
        os.environ.setdefault("CC_DATA", str(recursos / "data"))
        os.environ.setdefault("CC_FRONTEND", str(recursos / "frontend" / "dist"))
        os.environ.setdefault("CC_OCR", str(recursos / "ocr"))
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


def _icono(recursos: Path):
    from PIL import Image, ImageDraw

    ico = recursos / "empaquetar" / "carloscruz.ico"
    if ico.exists():
        return Image.open(ico)
    imagen = Image.new("RGBA", (64, 64), (20, 20, 20, 255))
    d = ImageDraw.Draw(imagen)
    d.rounded_rectangle([4, 4, 60, 60], radius=12, fill=(20, 20, 20, 255))
    d.text((14, 20), "CC", fill=(245, 243, 238, 255))
    return imagen


def _aviso(titulo: str, texto: str) -> None:
    """Un aviso corto de Windows (sin consola)."""
    try:
        import ctypes

        ctypes.windll.user32.MessageBoxW(None, texto, titulo, 0x40)
    except Exception:
        pass


def main() -> int:
    recursos, datos = _preparar_entorno()
    import uvicorn

    from app.config import MARCA
    from app.main import app

    puerto = _puerto_libre()
    url = f"http://localhost:{puerto}"
    configuracion = uvicorn.Config(app, host="127.0.0.1", port=puerto, log_level="warning", log_config=None)
    servidor = uvicorn.Server(configuracion)
    hilo = threading.Thread(target=servidor.run, name="servidor", daemon=True)
    hilo.start()

    def abrir(*_):
        webbrowser.open(url)

    def cerrar(icono, *_):
        servidor.should_exit = True
        icono.stop()

    for _ in range(100):  # hasta 10 s para que el servidor responda
        if servidor.started:
            break
        time.sleep(0.1)
    abrir()
    try:
        import pystray

        menu = pystray.Menu(pystray.MenuItem("Abrir", abrir, default=True), pystray.MenuItem("Cerrar", cerrar))
        pystray.Icon("CarlosCruz", _icono(recursos), f"{MARCA} · contabilidad que cuadra", menu).run()
    except Exception:
        logging.getLogger("carloscruz").exception("Sin ícono en la bandeja; el servidor sigue abierto")
        hilo.join()
    servidor.should_exit = True
    hilo.join(timeout=10)
    return 0


if __name__ == "__main__":
    multiprocessing.freeze_support()  # la lectura aislada de archivos usa procesos aparte
    try:
        raise SystemExit(main())
    except Exception:
        logging.getLogger("carloscruz").exception("No se pudo iniciar Carlos Cruz")
        _aviso("Carlos Cruz", "No se pudo iniciar Carlos Cruz. Cierre otras copias abiertas e intente de nuevo. "
                              "Si sigue pasando, comparta con soporte el registro de la carpeta Documentos\\Carlos Cruz.")
        raise SystemExit(1)
