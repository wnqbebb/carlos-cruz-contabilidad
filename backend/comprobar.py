"""Diagnóstico de la configuración. Dice en español qué falta y dónde arreglarlo.

Uso:
    .venv/Scripts/python backend/comprobar.py

No muestra ninguna clave completa: solo si está puesta y si funciona.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from app import config  # noqa: E402

# La consola de Windows usa cp1252 y no sabe imprimir ni los caracteres de caja
# ni el color ANSI. Se intenta pasar la salida a UTF-8; si no se puede, se cae a
# ASCII puro. Sin esto el diagnóstico se rompía justo en el equipo del usuario.
try:
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
    UNICODE = True
except Exception:  # pragma: no cover - depende de la consola
    UNICODE = False

# Windows Terminal entiende ANSI; la consola clásica (cmd.exe) no siempre.
COLOR = bool(os.getenv("WT_SESSION")) or (os.name != "nt" and sys.stdout.isatty())
VERDE, ROJO, AMBAR, FIN = ("\033[92m", "\033[91m", "\033[93m", "\033[0m") if COLOR else ("", "", "", "")

OK = f"{VERDE}[ OK ]{FIN}"
MAL = f"{ROJO}[FALLA]{FIN}"
AVISO = f"{AMBAR}[AVISO]{FIN}"
RAYA = "─" if UNICODE else "-"
VINETA = "·" if UNICODE else "*"
DOBLE = "=" * 62


def _tapar(valor: str) -> str:
    """Muestra que la clave está puesta sin revelarla."""
    if not valor:
        return "(vacio)"
    if len(valor) <= 12:
        return valor[:3] + "..."
    return f"{valor[:8]}...{valor[-4:]} ({len(valor)} caracteres)"


def _titulo(texto: str) -> None:
    print(f"\n{texto}")
    print(RAYA * len(texto))


def main() -> int:
    problemas: list[str] = []

    print(DOBLE)
    print(f"  {config.MARCA} - comprobacion de la configuracion")
    print(DOBLE)

    # ── 1. el archivo .env ──────────────────────────────────────────────────
    _titulo("1. Archivo de configuracion")
    env = config.RAIZ / "backend" / ".env"
    if env.exists():
        print(f"{OK} backend/.env existe")
    else:
        print(f"{MAL} No existe backend/.env")
        print("      Copie backend/.env.example como backend/.env y llenelo.")
        problemas.append("falta backend/.env")

    # ── 2. modo de almacenamiento ───────────────────────────────────────────
    _titulo("2. Donde se guardan los datos")
    url_bd = (os.getenv("DATABASE_URL") or "").strip()
    if config.ES_POSTGRES:
        print(f"{OK} Modo Supabase (Postgres)")
    else:
        print(f"{AVISO} Modo local (SQLite): los datos quedan solo en este computador")
        print(f"      Archivo: {config.SQLITE_ARCHIVO}")
        if not url_bd:
            print("      Para usar Supabase, llene DATABASE_URL en backend/.env")
        else:
            print("      DATABASE_URL esta puesta, pero ALMACENAMIENTO no es 'supabase'.")
            problemas.append("ALMACENAMIENTO no esta en 'supabase'")

    # ── 3. las claves ───────────────────────────────────────────────────────
    _titulo("3. Credenciales de Supabase")
    filas = [
        ("DATABASE_URL", url_bd, True),
        ("SUPABASE_URL", config.SUPABASE_URL, False),
        ("SUPABASE_ANON_KEY", config.SUPABASE_ANON_KEY, False),
        ("SUPABASE_SERVICE_KEY", config.SUPABASE_SERVICE_KEY, False),
    ]
    for nombre, valor, obligatoria in filas:
        marca = OK if valor else (MAL if obligatoria and config.ES_POSTGRES else AVISO)
        print(f"{marca} {nombre:22} {_tapar(valor)}")

    if url_bd:
        # Comprobaciones de forma que evitan los tres errores mas comunes.
        if ":6543" not in url_bd and ":5432" in url_bd:
            print(f"{AVISO} Esta usando el puerto 5432 (conexion directa).")
            print("      Supabase recomienda 6543 (pooler) para aplicaciones web.")
        if "sslmode" not in url_bd:
            print(f"{AVISO} A DATABASE_URL le falta  ?sslmode=require  al final.")
        if "[" in url_bd or "YOUR-PASSWORD" in url_bd.upper():
            print(f"{MAL} DATABASE_URL todavia tiene el texto de ejemplo de la contrasena.")
            print("      Reemplace [YOUR-PASSWORD] por la contrasena real de la base.")
            problemas.append("falta la contrasena en DATABASE_URL")

    # ── 4. la conexión ──────────────────────────────────────────────────────
    _titulo("4. Conexion a la base de datos")
    from app import db  # se importa aqui para que el diagnostico anterior salga primero

    estado = db.diagnostico()
    if estado["conectado"]:
        print(f"{OK} Conectado ({estado['motor']})")
    else:
        print(f"{MAL} No se pudo conectar")
        print(f"      {estado['error']}")
        problemas.append("sin conexion a la base")
        return _cierre(problemas)

    # ── 5. las tablas ───────────────────────────────────────────────────────
    _titulo("5. Tablas")
    from sqlalchemy import inspect

    from app.esquema import metadatos

    existentes = set(inspect(db.motor_db).get_table_names())
    esperadas = {t.name for t in metadatos.sorted_tables}
    faltan = sorted(esperadas - existentes)
    if faltan:
        print(f"{MAL} Faltan {len(faltan)} tabla(s): {', '.join(faltan)}")
        print("      Ejecute en Supabase -> SQL Editor, en este orden:")
        print("        supabase/migraciones/001_esquema.sql")
        print("        supabase/migraciones/002_seguridad.sql")
        problemas.append(f"faltan {len(faltan)} tablas")
    else:
        print(f"{OK} Las {len(esperadas)} tablas estan creadas")

    # ── 6. los datos ────────────────────────────────────────────────────────
    _titulo("6. Datos")
    try:
        from app.repositorio import clientes as repo
        from app.repositorio import parametros as repo_param
        from app.repositorio import periodos as repo_per

        conteo = repo.contar()
        trabajo = repo_per.resumen_global()
        anios = sorted(repo_param.todos().keys())
        print(f"{OK} Clientes: {conteo['total']} ({conteo['activos']} activos)")
        print(f"{OK} Periodos contabilizados: {trabajo['periodos']} "
              f"({trabajo['cerrados']} cerrados)")
        if trabajo["descuadrados"]:
            print(f"{AVISO} {trabajo['descuadrados']} periodo(s) con el balance descuadrado")
        if anios:
            print(f"{OK} Parametros legales cargados: {', '.join(anios)}")
        else:
            print(f"{AVISO} Sin parametros legales. Ejecute: python backend/sembrar.py")
        if conteo["total"] == 0:
            print(f"{AVISO} Sin clientes. Ejecute: python backend/sembrar.py")
    except Exception as ex:
        print(f"{MAL} No se pudieron leer los datos: {ex}")
        problemas.append("error leyendo datos")

    # ── 7. la interfaz ──────────────────────────────────────────────────────
    _titulo("7. Interfaz compilada")
    indice = config.FRONTEND_DIST / "index.html"
    if indice.exists():
        print(f"{OK} frontend/dist esta compilado")
    else:
        print(f"{AVISO} Falta compilar la interfaz")
        print("      Ejecute: cd frontend && npm install && npm run build")

    return _cierre(problemas)


def _cierre(problemas: list[str]) -> int:
    print()
    print(DOBLE)
    if problemas:
        print(f"  {ROJO}Hay {len(problemas)} cosa(s) por arreglar:{FIN}")
        for p in problemas:
            print(f"    {VINETA} {p}")
        print()
        print("  Guia completa: docs/DESPLIEGUE.md")
        print(DOBLE)
        return 1
    print(f"  {VERDE}Todo en orden. Ya puede abrir la aplicacion.{FIN}")
    print("  iniciar.bat   ->   http://localhost:8000")
    print(DOBLE)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
