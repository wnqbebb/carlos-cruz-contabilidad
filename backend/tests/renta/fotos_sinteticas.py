"""Fotos sintéticas difíciles de un reporte de exógena (contribuyente ficticio F).

Se generan al correr la prueba (no hay imágenes en git). Reproducen lo que traen las
fotos reales del contador: hoja girada y en perspectiva, poco contraste y sombra,
filas impresas dos veces (texto encimado), filas resaltadas en rosa, una nota a mano
con aspecto de contraseña arriba, «SF: …» abajo y texto ajeno en el margen.
"""
from __future__ import annotations

import io
import random
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

CONTRIBUYENTE_F = {
    "documento": {"tipo": "C.C.", "numero": "10000006", "nombre": "CONTRIBUYENTE F FICTICIO"},
    "topes": {"1": "82535904", "2": "226543936", "3": "19977892", "4": "125053184", "5": "12910068"},
    "lineas": [
        ("BANCO A S.A.", "CONTRIBUYENTE F", "Saldo cuentas bancarias (Titular Principal)", "3543936", "Tope 2: Patrimonio | R29"),
        ("CATASTRO", "CONTRIBUYENTE F", "Avalúo catastral inmueble", "108152000", "Tope 2: Patrimonio | R29"),
        ("CATASTRO", "CONTRIBUYENTE F", "Avalúo catastral inmueble", "98448000", "Tope 2: Patrimonio | R29"),
        ("TRANSITO", "CONTRIBUYENTE F", "Vehículo avalúo comercial", "16400000", "Tope 2: Patrimonio | R29"),
        ("TRANSPORTES X S.A.S.", "CONTRIBUYENTE F", "Ingresos documentos soporte", "40000000", "Tope 1: Ingresos brutos"),
        ("TRANSPORTES X S.A.S.", "CONTRIBUYENTE F", "Ingresos documentos soporte", "32535904", "Tope 1: Ingresos brutos"),
        ("BANCO B", "CONTRIBUYENTE F", "Rendimientos financieros", "10000000", "Tope 1: Ingresos brutos | R58"),
        ("BANCO A S.A.", "CONTRIBUYENTE F", "Total consumos o gastos con tarjeta Crédito", "19977892", "Tope 3: Consumos TC"),
        ("BANCO A S.A.", "CONTRIBUYENTE F", "Valor total de los movimientos en cuentas", "125053184", "Tope 4: Consignaciones"),
        ("DIAN", "CONTRIBUYENTE F", "Suma valor total facturas tras ajustes por notas", "12910068", "Tope 5: Compras"),
        ("BANCO A S.A.", "CONTRIBUYENTE F", "Cuentas por pagar de clientes (Concepto: 1315)", "25000000", "R30 Deudas"),
        ("BANCO B", "CONTRIBUYENTE F", "Retención practicada rendimientos", "700000", "R132 Retenciones"),
    ],
    "resaltadas": [4, 5, 8],
    "encimadas": [7],
    "credencial": "carlos1977@.",
    "saldo_a_favor": "SF: 6.275.000",
}


def _fuente(tamano: int):
    for nombre in ("arial.ttf", "Arial.ttf", "DejaVuSans.ttf", "LiberationSans-Regular.ttf"):
        for base in ("", "C:/Windows/Fonts/", "/usr/share/fonts/truetype/dejavu/", "/Library/Fonts/"):
            try:
                return ImageFont.truetype(base + nombre, tamano)
            except OSError:
                continue
    return ImageFont.load_default(size=tamano)


def _a_mano(tamano: int):
    for nombre in ("segoesc.ttf", "Inkfree.ttf", "comic.ttf"):
        try:
            return ImageFont.truetype("C:/Windows/Fonts/" + nombre, tamano)
        except OSError:
            continue
    return _fuente(tamano)


def _pesos(v: str) -> str:
    return f"$ {int(v):,}.00"


def hoja(caso=CONTRIBUYENTE_F) -> Image.Image:
    """La hoja impresa, limpia y derecha (antes de fotografiarla)."""
    ancho, alto = 2200, 1700
    im = Image.new("RGB", (ancho, alto), (250, 249, 245))
    d = ImageDraw.Draw(im)
    f = _fuente(26)
    x0, y0 = 160, 170
    cols = [x0, 520, 860, 1560, 1820, 2140]
    alto_fila = 44
    d.text((x0, y0 - 130), "Tipo de documento:   C.C.", font=f, fill=(20, 20, 20))
    d.text((x0, y0 - 90), f"Identificación:        {caso['documento']['numero']}", font=f, fill=(20, 20, 20))
    d.text((x0, y0 - 50), f"Nombres / Razón social:   {caso['documento']['nombre']}", font=f, fill=(20, 20, 20))
    filas = [("", "", f"Tope {n} - {t}", v, "") for (n, v), t in
             zip(caso["topes"].items(), ("Ingresos", "Patrimonio", "Consumo TC", "Movimiento", "Compras"))]
    filas += list(caso["lineas"])
    for i, fila in enumerate(filas):
        y = y0 + i * alto_fila
        k = i - 5
        if k in caso["resaltadas"]:
            d.rectangle([cols[0], y + 2, cols[-1], y + alto_fila - 2], fill=(255, 170, 205))
        textos = [fila[0], fila[1], fila[2], _pesos(fila[3]), fila[4]]
        for j, t in enumerate(textos):
            d.text((cols[j] + 8, y + 8), t, font=f, fill=(25, 25, 25))
            if k in caso["encimadas"]:  # la hoja pasó dos veces por la impresora
                d.text((cols[j] + 11, y + 10), t, font=f, fill=(90, 90, 90))
        d.line([cols[0], y, cols[-1], y], fill=(30, 30, 30), width=2)
    yfin = y0 + len(filas) * alto_fila
    d.line([cols[0], yfin, cols[-1], yfin], fill=(30, 30, 30), width=2)
    for x in cols:
        d.line([x, y0, x, yfin], fill=(30, 30, 30), width=2)
    # Notas a mano: arriba una cadena con aspecto de contraseña; abajo el saldo a favor.
    m = _a_mano(40)
    d.text((1300, 40), caso["credencial"], font=m, fill=(25, 45, 140))
    d.text((300, yfin + 60), caso["saldo_a_favor"], font=m, fill=(25, 45, 140))
    # Texto ajeno en el margen izquierdo (un recetario).
    margen = Image.new("RGBA", (900, 60), (0, 0, 0, 0))
    ImageDraw.Draw(margen).text((0, 0), "Dra. Ejemplo · Rx · Tomar 1 cada 8 h", font=_fuente(30), fill=(60, 60, 140, 255))
    im.paste(margen.rotate(90, expand=True), (40, 500), margen.rotate(90, expand=True))
    return im


def fotografiar(im: Image.Image, semilla: int = 7) -> bytes:
    """Como la tomaría un celular: girada 90°, inclinada, en perspectiva, con sombra y poco contraste."""
    rnd = random.Random(semilla)
    im = im.rotate(-90, expand=True)                              # hoja de lado
    im = im.rotate(rnd.uniform(2.5, 4.0), expand=True, fillcolor=(70, 60, 55), resample=Image.BICUBIC)
    w, h = im.size
    m = int(min(w, h) * 0.05)
    origen = [(0, 0), (w, 0), (w, h), (0, h)]
    destino = [(m, int(m * 0.4)), (w - int(m * 0.3), 0), (w, h), (int(m * 0.6), h - m)]
    coef = _perspectiva(destino, origen)
    im = im.transform((w, h), Image.PERSPECTIVE, coef, Image.BICUBIC, fillcolor=(70, 60, 55))
    a = np.asarray(im).astype(np.float32)
    # Poco contraste y una sombra diagonal.
    a = 95 + a * 0.55
    gy, gx = np.mgrid[0:h, 0:w]
    sombra = 0.62 + 0.38 * (gx / w * 0.6 + gy / h * 0.4)
    a = a * sombra[..., None]
    a += np.random.default_rng(semilla).normal(0, 4, a.shape)
    im = Image.fromarray(a.clip(0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.8))
    im = im.resize((int(w * 0.75), int(h * 0.75)))
    buf = io.BytesIO()
    im.save(buf, format="JPEG", quality=80)
    return buf.getvalue()


def _perspectiva(pa, pb):
    matriz = []
    for p1, p2 in zip(pa, pb):
        matriz.append([p1[0], p1[1], 1, 0, 0, 0, -p2[0] * p1[0], -p2[0] * p1[1]])
        matriz.append([0, 0, 0, p1[0], p1[1], 1, -p2[1] * p1[0], -p2[1] * p1[1]])
    A = np.array(matriz, dtype=np.float64)
    B = np.array(pb, dtype=np.float64).reshape(8)
    return np.linalg.solve(A, B).tolist()


def guardar(carpeta: Path) -> Path:
    carpeta.mkdir(parents=True, exist_ok=True)
    ruta = carpeta / "contribuyente_f.jpg"
    ruta.write_bytes(fotografiar(hoja()))
    return ruta


if __name__ == "__main__":  # python backend/tests/renta/fotos_sinteticas.py <carpeta>
    import sys

    print(guardar(Path(sys.argv[1] if len(sys.argv) > 1 else ".")))
