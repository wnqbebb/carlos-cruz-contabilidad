# -*- mode: python ; coding: utf-8 -*-
"""Receta de PyInstaller para dejar la aplicación como un solo .exe.

El ejecutable lleva dentro Python, el motor contable y la interfaz ya compilada.
En el computador del cliente no hay que instalar Python, ni Node, ni nada.

Se construye con  empaquetar\\construir.bat
"""
from pathlib import Path

RAIZ = Path(SPECPATH).parent

datos = [
    # Catálogo PUC, parámetros legales y datos del contador.
    (str(RAIZ / "data"), "data"),
    # Interfaz compilada: la sirve el propio backend.
    (str(RAIZ / "frontend" / "dist"), "frontend/dist"),
]
# Lector de fotos para la renta (v2.3): Tesseract y sus idiomas, si se prepararon
# con scripts\preparar_ocr.ps1 (lo corre construir.bat).
for carpeta in ("tesseract", "tessdata"):
    if (RAIZ / "datos_app" / carpeta).exists():
        datos.append((str(RAIZ / "datos_app" / carpeta), f"ocr/{carpeta}"))

# Los archivos reales de clientes (privado/) NUNCA van dentro del ejecutable:
# el .exe se puede copiar a otro computador (sección 4.3).

analisis = Analysis(
    [str(RAIZ / "empaquetar" / "lanzador.py")],
    pathex=[str(RAIZ / "backend")],
    binaries=[],
    datas=datos,
    hiddenimports=[
        # Uvicorn y SQLAlchemy cargan partes por nombre, así que PyInstaller
        # no las detecta solo y hay que nombrarlas.
        "uvicorn.logging",
        "uvicorn.loops.auto",
        "uvicorn.loops.asyncio",
        "uvicorn.protocols.http.auto",
        "uvicorn.protocols.http.h11_impl",
        "uvicorn.protocols.websockets.auto",
        "uvicorn.lifespan.on",
        "sqlalchemy.dialects.sqlite",
        "sqlalchemy.dialects.postgresql",
        "sqlalchemy.dialects.postgresql.psycopg",
        "psycopg",
        "openpyxl",
        # Lectores de Word y PDF (v2.2): se importan por nombre dentro de los
        # importadores, así que PyInstaller tampoco los ve solo.
        "docx",
        "pdfplumber",
        "pypdf",
        "xlrd",
        "reportlab.graphics.barcode",
        # Inicio de sesión (A2): el hash de la contraseña y el asistente que la crea.
        "bcrypt",
        # Declaración de renta (v2.3): lectura de fotos.
        "pytesseract",
        "cv2",
        "numpy",
        "rapidfuzz",
        "crear_usuario",
        "app",
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=["tkinter", "matplotlib", "pytest", "playwright", "IPython"],
    noarchive=False,
)

pyz = PYZ(analisis.pure)

exe = EXE(
    pyz,
    analisis.scripts,
    [],
    exclude_binaries=True,
    name="CarlosCruz",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,          # la consola muestra la dirección y los mensajes
    icon=str(RAIZ / "empaquetar" / "carloscruz.ico")
        if (RAIZ / "empaquetar" / "carloscruz.ico").exists() else None,
)

coleccion = COLLECT(
    exe,
    analisis.binaries,
    analisis.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="CarlosCruz",
)
