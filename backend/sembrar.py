"""Siembra el primer cliente (FANANT) a partir de `data/empresa_fanant.json`.

Uso:
    .venv/Scripts/python backend/sembrar.py

Es idempotente: si el cliente ya existe, actualiza su ficha en vez de duplicarla.
Sirve para dejar la base lista tanto en local como en Supabase.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.config import DATA, MARCA, estado_almacenamiento  # noqa: E402
from app.db import diagnostico  # noqa: E402
from app.repositorio import clientes as repo  # noqa: E402
from app.repositorio import parametros as repo_parametros  # noqa: E402


def ficha_fanant() -> dict:
    datos = json.loads((DATA / "empresa_fanant.json").read_text(encoding="utf-8"))
    return {
        "nit": datos["nit"],
        "razon_social": datos["razon_social"],
        "sigla": datos.get("sigla", ""),
        "tipo_persona": "juridica",
        "regimen": "responsable_iva",
        "grupo_niif": datos.get("grupo_niif", 3),
        "responsable_iva": datos.get("responsable_iva", True),
        "tarifa_renta": datos.get("tarifa_renta", "0.35"),
        "ciiu": datos.get("ciiu", ""),
        "direccion": datos.get("direccion", ""),
        "municipio": datos.get("municipio", ""),
        "departamento": "Valle del Cauca",
        "email": "fanant2024@gmail.com",
        "rep_legal": datos.get("rep_legal", ""),
        "rep_legal_cc": datos.get("rep_legal_cc", ""),
        "rep_legal_suplente": datos.get("rep_legal_suplente", ""),
        "contador": datos.get("contador", ""),
        "contador_cc": datos.get("contador_cc", ""),
        "contador_tp": datos.get("contador_tp", ""),
        "fecha_constitucion": datos.get("constitucion") or None,
        "capital_suscrito": datos.get("capital_suscrito", "0"),
        "valor_nominal_accion": datos.get("valor_nominal_accion", "0"),
        "honorarios_mes": "300000",
        "periodicidad": "mensual",
        "estado": "activo",
        "etiquetas": ["Farmacia", "Guacarí"],
        "socios": [
            {
                "nombre": a.get("nombre", ""),
                "cedula": a.get("cedula", ""),
                "comprometido": a.get("comprometido", "0"),
                "pagado": a.get("pagado", "0"),
            }
            for a in datos.get("accionistas", [])
        ],
    }


def main() -> int:
    estado = diagnostico()
    almacen = estado_almacenamiento()
    print(f"{MARCA} · sembrando datos iniciales")
    print(f"  base: {almacen['modo']} ({estado['motor']})")
    if not estado["conectado"]:
        print(f"  ERROR: {estado['error']}")
        return 1

    anios = repo_parametros.sembrar_si_vacio()
    print(f"  parámetros legales: {anios} año(s) sembrados" if anios
          else "  parámetros legales: ya estaban cargados")

    ficha = ficha_fanant()
    socios = ficha.pop("socios")
    existente = repo.por_nit(ficha["nit"])
    if existente:
        cliente = repo.actualizar(existente["id"], ficha)
        print(f"  cliente actualizado: {cliente['razon_social']} ({cliente['nit_formateado']})")
    else:
        cliente = repo.crear(ficha)
        print(f"  cliente creado: {cliente['razon_social']} ({cliente['nit_formateado']})")

    cuantos = repo.guardar_socios(cliente["id"], socios)
    print(f"  socios registrados: {cuantos}")
    print(f"  total de clientes en la base: {repo.contar()['total']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
