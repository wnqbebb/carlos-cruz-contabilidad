"""Fotos y reportes de exógena FICTICIOS para los recorridos de renta (J7, J8, J9). Rescate.

Nada es real: contribuyentes inventados, cédulas ficticias, entidades genéricas.
  · J7 · `contribuyente_a_foto.jpg`: la exógena de la «Contribuyente A» (tabla anonimizada de
    PROMPT_V23.md §5.10, en backend/tests/renta/caso_a.json), fotografiada con el celular: algo
    girada y con sombra, pero legible. Dos filas se imprimieron dos veces (hay que confirmarlas).
  · J8 · `contribuyente_f_pagina_{1,2,3}.jpg`: tres fotos difíciles de otro contribuyente ficticio
    (giradas 90°, poco contraste, texto encimado, nota a mano con aspecto de contraseña).
  · J9 · `exogena_persona_nueva.xlsx`: una exógena en Excel de alguien que no es cliente contable.

    python -m demo.fotos_ficticias          # escribe todo en docs/demo/renta/
"""
from __future__ import annotations

import io
import json
import random
from pathlib import Path

import numpy as np
from openpyxl import Workbook
from PIL import Image, ImageFilter

from tests.renta.fotos_sinteticas import CONTRIBUYENTE_F, _perspectiva, fotografiar, hoja

RAIZ = Path(__file__).resolve().parents[2]
SALIDA = RAIZ / "docs" / "demo" / "renta"
CASO_A = json.loads((RAIZ / "backend" / "tests" / "renta" / "caso_a.json").read_text(encoding="utf-8"))


def caso_a_para_foto() -> dict:
    return {
        "documento": CASO_A["documento"],
        "topes": CASO_A["topes"],
        "lineas": [(l["entidad"], l["titular"], l["detalle"], l["valor"], l["uso"]) for l in CASO_A["lineas"]],
        "resaltadas": [2, 3, 6],
        "encimadas": [9, 15],          # dos filas impresas dos veces: la app pide confirmarlas
        "credencial": "",
        "saldo_a_favor": "",
    }


def foto_legible(im: Image.Image, semilla: int = 3) -> bytes:
    """Como una foto buena de celular: un poco inclinada, con sombra suave, buen contraste."""
    rnd = random.Random(semilla)
    im = im.rotate(rnd.uniform(1.0, 1.8), expand=True, fillcolor=(80, 70, 62), resample=Image.BICUBIC)
    w, h = im.size
    m = int(min(w, h) * 0.02)
    coef = _perspectiva([(m, 0), (w, int(m * 0.5)), (w - m, h), (0, h - int(m * 0.3))], [(0, 0), (w, 0), (w, h), (0, h)])
    im = im.transform((w, h), Image.PERSPECTIVE, coef, Image.BICUBIC, fillcolor=(80, 70, 62))
    a = np.asarray(im).astype(np.float32)
    gy, gx = np.mgrid[0:h, 0:w]
    a = a * (0.86 + 0.14 * (gx / w))[..., None]
    a += np.random.default_rng(semilla).normal(0, 2.5, a.shape)
    im = Image.fromarray(a.clip(0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.4))
    buf = io.BytesIO()
    im.save(buf, format="JPEG", quality=88)
    return buf.getvalue()


def paginas_f() -> list[bytes]:
    """Las 3 fotos del contribuyente F: la hoja partida en tres, cada página peor que la anterior."""
    lineas = list(CONTRIBUYENTE_F["lineas"])
    trozos = [lineas[:5], lineas[5:9], lineas[9:]]
    fotos = []
    for i, trozo in enumerate(trozos):
        caso = {**CONTRIBUYENTE_F, "lineas": trozo,
                "resaltadas": [k for k in range(len(trozo)) if (k + i) % 3 == 0],
                "encimadas": [1] if i else [],
                "credencial": CONTRIBUYENTE_F["credencial"] if i == 0 else "",
                "saldo_a_favor": CONTRIBUYENTE_F["saldo_a_favor"] if i == 2 else ""}
        fotos.append(fotografiar(hoja(caso), semilla=7 + i))
    return fotos


def exogena_persona_nueva() -> bytes:
    """Exógena en Excel de una persona que solo viene por la renta (J9)."""
    wb = Workbook()
    ws = wb.active
    ws.title = "Reporte"
    ws.append(["Tipo de documento: C.C.", "", "", "", ""])
    ws.append(["Identificación: 10000009", "", "", "", ""])
    ws.append(["Nombres / Razón social: PERSONA NUEVA FICTICIA", "", "", "", ""])
    ws.append([])
    ws.append(["Entidad", "Titular", "Detalle", "Valor", "Uso sugerido"])
    ws.append(["EMPRESA EJEMPLO S.A.S.", "PERSONA NUEVA FICTICIA", "Pagos por salarios", 75_000_000, "Tope 1: Ingresos brutos | R32"])
    ws.append(["EMPRESA EJEMPLO S.A.S.", "PERSONA NUEVA FICTICIA", "Aportes obligatorios a pensión y salud", 6_000_000, "R33"])
    ws.append(["EMPRESA EJEMPLO S.A.S.", "PERSONA NUEVA FICTICIA", "Retención en la fuente por salarios", 1_200_000, "R132 Retenciones"])
    ws.append(["BANCO DEMO", "PERSONA NUEVA FICTICIA", "Saldo cuentas bancarias (Titular Principal)", 15_000_000, "Tope 2: Patrimonio | R29"])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def archivos() -> dict[str, bytes]:
    out = {"contribuyente_a_foto.jpg": foto_legible(hoja(caso_a_para_foto()))}
    for i, foto in enumerate(paginas_f(), 1):
        out[f"contribuyente_f_pagina_{i}.jpg"] = foto
    out["exogena_persona_nueva.xlsx"] = exogena_persona_nueva()
    return out


def main() -> None:
    SALIDA.mkdir(parents=True, exist_ok=True)
    for nombre, datos in archivos().items():
        (SALIDA / nombre).write_bytes(datos)
        print("escrito", SALIDA / nombre, len(datos) // 1024, "KB")


if __name__ == "__main__":
    main()
