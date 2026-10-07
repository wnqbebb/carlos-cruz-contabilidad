# -*- mode: python ; coding: utf-8 -*-
"""Receta de PyInstaller para dejar la aplicación como un solo .exe.

El ejecutable lleva dentro Python, el motor contable y la interfaz ya compilada.
En el computador del cliente no hay que instalar Python, ni Node, ni nada.

Se construye con  empaquetar\\construir.bat
"""
from pathlib import Path

RAIZ = Path(SPECPATH).parent

datos = [
    # Catálogo PUC, parámetros legales y ficha de empresa por defecto.
    (str(RAIZ / "data"), "data"),
    # Interfaz compilada: la sirve el propio backend.
    (str(RAIZ / "frontend" / "dist"), "frontend/dist"),
]

# Los archivos de ejemplo del cliente son opcionales: si están, se incluyen
# para que los botones de demostración funcionen sin internet.
fuentes = RAIZ / "docs" / "fuentes"
if fuentes.is_dir():
    datos.append((str(fuentes), "docs/fuentes"))

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
