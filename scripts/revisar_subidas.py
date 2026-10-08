"""Sube cada archivo de prueba por la API y revisa que se reconozca y se calcule (sección 4.1).

    .venv/Scripts/python scripts/revisar_subidas.py http://127.0.0.1:8001 [--usuario prueba --clave prueba-aislada-2026]

1. El banco de archivos variados (backend/tests/archivos_variados): cada uno por
   la puerta única, creando un cliente con NIT ficticio, respondiendo las
   preguntas con la opción por defecto y calculando.
2. Los archivos reales de FANANT (privado/fuentes), si están en este equipo:
   cada uno solo, y la contabilidad completa de enero 2025 en el cliente FANANT
   de la copia, comparando con las cifras de control de docs/v22/fase-2.md.

Solo contra la copia aislada: escribe clientes y periodos.
"""
from __future__ import annotations

import argparse
import json
import sys
from decimal import Decimal
from pathlib import Path

import httpx

RAIZ = Path(__file__).resolve().parents[1]
BANCO = RAIZ / "backend" / "tests" / "archivos_variados"
PRIVADO = RAIZ / "privado"

# docs/v22/fase-2.md: cierre de FANANT enero 2025 (causación de nómina aceptada, IVA sin reclasificar).
CIERRE_FANANT = {
    "110505": ("37144505", "0"), "237005": ("0", "56940"), "237006": ("0", "7430.67"), "237010": ("0", "56940"),
    "238030": ("0", "227760"), "240805": ("2280", "0"), "2505": ("0", "1509620"), "2510": ("0", "135237.55"),
    "2515": ("0", "16235"), "2520": ("0", "135237.55"), "2525": ("0", "59359.95"), "3105": ("0", "37800000"),
    "3610": ("2857975.72", "0"),
}
RESUMEN_FANANT = {"total_activo": "37144505", "total_pasivo": "2202480.72", "total_patrimonio": "34942024.28",
                  "utilidad_neta": "-2857975.72", "ingresos": "22641"}


def ok(r: httpx.Response) -> dict:
    if r.status_code >= 400:
        raise RuntimeError(f"{r.request.method} {r.request.url.path} → {r.status_code}: {r.text[:400]}")
    return r.json()


def calcular(c: httpx.Client, imp: dict, decisiones: dict | None = None, periodizacion: str | None = None) -> dict:
    pet = {"sesion_id": imp["sesion_id"], "cliente_id": imp.get("cliente_id"), "incluir": {},
           "mapeo": {m["normalizado"]: m["codigo"] for m in imp["mapeo"] if m.get("codigo")},
           "empresa": {}, "config": {}, "decisiones": decisiones or {}, "recordar_alias": False,
           "respuestas": {p["id"]: p["defecto"] for p in imp.get("preguntas") or []}}
    if periodizacion:
        pet["periodizacion"] = periodizacion
    return ok(c.post("/api/calcular", json=pet))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("url")
    ap.add_argument("--usuario", default="prueba")
    ap.add_argument("--clave", default="prueba-aislada-2026")
    a = ap.parse_args()
    if ":8000" in a.url:
        print("Se niega a correr contra :8000 (la base real).")
        return 1
    c = httpx.Client(base_url=a.url, timeout=600)
    ok(c.post("/api/sesion", json={"usuario": a.usuario, "clave": a.clave}))
    fallos = []

    print("1 · banco de archivos variados")
    for i, archivo in enumerate(sorted(p for p in BANCO.iterdir() if p.suffix in (".xlsx", ".csv", ".pdf", ".docx"))):
        nit = str(900700100 + i)
        try:
            r = c.post("/api/subir", files=[("archivos", (archivo.name, archivo.read_bytes()))])
            if r.status_code == 400:   # p. ej. el PDF escaneado: se rechaza con un mensaje claro
                print(f"   {archivo.name:<42} rechazado con mensaje: {r.json()['detail']['mensaje'][:70]}")
                continue
            sub = ok(r)
            imp = ok(c.post(f"/api/subir/{sub['subida_id']}/confirmar",
                            json={"clase": "contabilidad", "crear": {"nit": nit, "razon_social": f"PRUEBA {archivo.stem.upper()} S.A.S."}}))
            per = imp.get("periodizacion") or {}
            res = calcular(c, imp, periodizacion="por_periodo" if per.get("posible") else None)
            p = res.get("periodo") or {}
            print(f"   {archivo.name:<42} {sub['clase']:<12} preguntas {len(imp.get('preguntas') or []):>2} · "
                  f"{'cuadra' if p.get('cuadra') else 'NO CUADRA'} · periodos {len(res.get('periodos_procesados') or [1])}")
            if not p.get("cuadra"):
                fallos.append(f"{archivo.name}: no cuadra")
        except Exception as ex:  # se informa y se sigue con el siguiente
            fallos.append(f"{archivo.name}: {ex}")
            print(f"   {archivo.name:<42} ERROR {ex}")

    fuentes = PRIVADO / "fuentes"
    if not fuentes.exists():
        print("2 · privado/fuentes no está en este equipo: se omite")
    else:
        print("2 · archivos reales de FANANT, uno por uno")
        for archivo in sorted(fuentes.iterdir()):
            r = c.post("/api/subir", files=[("archivos", (archivo.name, archivo.read_bytes()))])
            d = r.json()
            print(f"   {archivo.name:<42} {r.status_code} · {d.get('clase', d.get('detail'))}")
            if r.status_code >= 500:
                fallos.append(f"{archivo.name}: {r.status_code}")
        ficha = json.loads((PRIVADO / "empresa_fanant.json").read_text(encoding="utf-8"))
        nit = ficha["nit"].split("-")[0]
        fanant = next((x for x in ok(c.get("/api/clientes", params={"q": nit, "estado": ""}))["clientes"]), None)
        if not fanant:
            print("   FANANT no está en la copia: se omite el control de cifras")
        else:
            archivos = [(n, (fuentes / n).read_bytes()) for n in ("CONTABILIDAD.xls", "NOMINA__enero__2025.xlsx")]
            sub = ok(c.post("/api/subir", params={"cliente_id": fanant["id"]}, files=[("archivos", x) for x in archivos]))
            imp = ok(c.post(f"/api/subir/{sub['subida_id']}/confirmar", json={"cliente_id": fanant["id"]}))
            res = calcular(c, imp, {"nomina_causacion": True, "recl_iva": False})
            saldos = {s["codigo"]: (Decimal(str(s["debito"])), Decimal(str(s["credito"]))) for s in res["saldos_siguiente"]}
            esperado = {k: (Decimal(a), Decimal(b)) for k, (a, b) in CIERRE_FANANT.items()}
            iguales = saldos == esperado and all(Decimal(str(res["resumen"][k])) == Decimal(v) for k, v in RESUMEN_FANANT.items())
            print(f"   control FANANT enero 2025: {'13 saldos y totales IDÉNTICOS' if iguales else 'DIFERENTES'}")
            if not iguales:
                fallos.append("cifras de control de FANANT diferentes")

    if fallos:
        print("FALLOS:")
        for f in fallos:
            print("  ·", f)
        return 1
    print("Sin fallos.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
