"""Lectura de fotos de reportes (OCR) para la declaración de renta (spec v2.3 · 5.3).

Tubería, en orden:
1. Quitar sombras (dividir por el fondo difuminado) y orientar la hoja (OSD de
   Tesseract y, si duda, probar los cuatro giros).
2. Encontrar la **tabla** por sus líneas y aplanarla (perspectiva) a un rectángulo.
   Lo que queda fuera (márgenes, recetarios, papeles ajenos, dedos) no se lee como dato.
3. Rejilla: filas y columnas por las líneas detectadas; cada celda se lee sola.
4. Por fila: ¿resaltada a mano (color)? ¿texto encimado (confianza baja o valor
   que no tiene forma de dinero)?
5. Fuera de la tabla solo se buscan **notas a mano**: si parecen credenciales se
   descartan y se avisa; si son cifras («SF: 6.275.000») se ofrecen como sugerencia.

Nada de lo leído entra solo: todo pasa por la pantalla de verificación.
"""
from __future__ import annotations

import os
import re
import shutil
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from ..config import RAIZ

try:  # opcionales: sin ellos la app sigue funcionando con PDF y Excel
    import cv2
    import pytesseract
except Exception:  # pragma: no cover
    cv2 = None
    pytesseract = None

# Dónde está el lector: `datos_app` en el equipo de desarrollo; dentro del .exe, sus recursos (CC_OCR).
CARPETA_OCR = Path(os.environ.get("CC_OCR") or (RAIZ / "datos_app"))
TESSDATA = CARPETA_OCR / "tessdata"
RUTAS_TESSERACT = [
    Path(os.environ.get("CC_TESSERACT", "")),
    CARPETA_OCR / "tesseract" / "tesseract.exe",
    Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe"),
    Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Tesseract-OCR" / "tesseract.exe",
]

DINERO = re.compile(r"\$?\s*-?\d{1,3}(?:[.,]\d{3})+(?:[.,]\d{2})?|\$\s*\d+(?:[.,]\d{2})?")


class OcrNoDisponible(Exception):
    pass


def disponible() -> bool:
    try:
        _configurar()
        return True
    except OcrNoDisponible:
        return False


def _configurar() -> None:
    if cv2 is None or pytesseract is None:
        raise OcrNoDisponible("Falta el lector de imágenes en este equipo.")
    if getattr(_configurar, "_listo", False):
        return
    exe = next((str(p) for p in RUTAS_TESSERACT if str(p) not in ("", ".") and p.exists()), None) or shutil.which("tesseract")
    if not exe:
        raise OcrNoDisponible("Falta el lector de imágenes (Tesseract) en este equipo.")
    pytesseract.pytesseract.tesseract_cmd = exe
    if (TESSDATA / "spa.traineddata").exists():
        os.environ["TESSDATA_PREFIX"] = str(TESSDATA)
    _configurar._listo = True  # type: ignore[attr-defined]


@dataclass
class Celda:
    texto: str
    confianza: float
    caja: tuple[int, int, int, int]  # x, y, ancho, alto en la tabla aplanada


@dataclass
class Fila:
    celdas: list[Celda]
    resaltada: bool = False
    caja: tuple[int, int, int, int] = (0, 0, 0, 0)

    @property
    def confianza(self) -> float:
        con_texto = [c.confianza for c in self.celdas if c.texto.strip()]
        return min(con_texto) if con_texto else 0.0


@dataclass
class LecturaImagen:
    filas: list[Fila] = field(default_factory=list)
    texto_cabecera: str = ""
    giro: int = 0
    tabla_encontrada: bool = False
    notas_a_mano: list[str] = field(default_factory=list)     # solo cifras útiles, nunca credenciales
    texto_arriba: str = ""                                     # encabezado impreso fuera de la tabla (no se guarda)
    anotaciones: bool = False                                  # hay escritura a mano fuera de la tabla
    credenciales_descartadas: int = 0
    encimada: bool = False
    tabla: "np.ndarray | None" = None                          # imagen aplanada (para recortes de verificación)


# ── preprocesado ──────────────────────────────────────────────────────────
def cargar(ruta_o_bytes) -> "np.ndarray":
    _configurar()
    if isinstance(ruta_o_bytes, (bytes, bytearray)):
        im = cv2.imdecode(np.frombuffer(ruta_o_bytes, np.uint8), cv2.IMREAD_COLOR)
    else:
        im = cv2.imread(str(ruta_o_bytes), cv2.IMREAD_COLOR)
    if im is None:
        raise ValueError("No se pudo abrir la imagen.")
    # Las fotos de celular llegan muy grandes: se trabaja a un tamaño útil para el OCR.
    alto, ancho = im.shape[:2]
    lado = max(alto, ancho)
    if lado > 3200:
        f = 3200 / lado
        im = cv2.resize(im, (int(ancho * f), int(alto * f)), interpolation=cv2.INTER_AREA)
    elif lado < 1400:
        f = 1400 / lado
        im = cv2.resize(im, (int(ancho * f), int(alto * f)), interpolation=cv2.INTER_CUBIC)
    return im


def sin_sombras(gris: "np.ndarray") -> "np.ndarray":
    fondo = cv2.medianBlur(cv2.dilate(gris, np.ones((7, 7), np.uint8)), 41)
    plano = cv2.divide(gris, fondo, scale=255)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    return clahe.apply(plano)


def binaria(gris: "np.ndarray") -> "np.ndarray":
    return cv2.adaptiveThreshold(gris, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY_INV, 25, 15)


def _girar(im, grados: int):
    if grados % 360 == 0:
        return im
    codigo = {90: cv2.ROTATE_90_CLOCKWISE, 180: cv2.ROTATE_180, 270: cv2.ROTATE_90_COUNTERCLOCKWISE}[grados % 360]
    return cv2.rotate(im, codigo)


def _puntaje_orientacion(gris) -> float:
    """Cuánto texto legible sale con este giro: suma de la confianza de las palabras seguras."""
    h, w = gris.shape
    f = 1300 / max(h, w)
    peq = cv2.resize(gris, None, fx=f, fy=f, interpolation=cv2.INTER_AREA) if f < 1 else gris
    d = pytesseract.image_to_data(peq, lang="spa", config="--psm 6", output_type=pytesseract.Output.DICT)
    return sum(float(c) for t, c in zip(d["text"], d["conf"])
               if len(t.strip()) >= 3 and float(c) >= 60 and re.search(r"[A-Za-z0-9]", t))


def orientar(im) -> tuple["np.ndarray", int]:
    """Endereza la hoja (0, 90, 180 o 270°). Si el OSD de Tesseract no está seguro, se prueban los giros."""
    gris = sin_sombras(cv2.cvtColor(im, cv2.COLOR_BGR2GRAY))
    candidatos = [0, 90, 180, 270]
    try:
        osd = pytesseract.image_to_osd(gris, config="--psm 0")
        giro = int(re.search(r"Rotate: (\d+)", osd).group(1))
        conf = float(re.search(r"Orientation confidence: ([\d.]+)", osd).group(1))
        if conf >= 3:
            return _girar(im, giro), giro
        # Con poca confianza el OSD suele acertar el eje: se compara con su giro opuesto.
        candidatos = [giro, (giro + 180) % 360]
    except Exception:
        pass
    mejor = max(candidatos, key=lambda g: _puntaje_orientacion(_girar(gris, g)))
    return _girar(im, mejor), mejor


# ── tabla ─────────────────────────────────────────────────────────────────
def _lineas(bw):
    h, w = bw.shape
    hor = cv2.morphologyEx(bw, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (max(w // 25, 20), 1)))
    ver = cv2.morphologyEx(bw, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (1, max(h // 40, 15))))
    return hor, ver


def _picos_simples(proyeccion, minimo: float) -> list[int]:
    idx = np.where(proyeccion > minimo)[0]
    if not len(idx):
        return []
    grupos = [[idx[0]]]
    for i in idx[1:]:
        (grupos[-1].append(i) if i - grupos[-1][-1] <= 3 else grupos.append([i]))
    return [int(np.mean(g)) for g in grupos]


def _ordenar_esquinas(pts):
    pts = pts.reshape(4, 2).astype("float32")
    s = pts.sum(axis=1)
    d = np.diff(pts, axis=1).ravel()
    return np.array([pts[np.argmin(s)], pts[np.argmin(d)], pts[np.argmax(s)], pts[np.argmax(d)]], dtype="float32")


def enderezar(im) -> "np.ndarray":
    """Corrige la inclinación fina (pocos grados) con el ángulo mediano de las líneas largas."""
    gris = sin_sombras(cv2.cvtColor(im, cv2.COLOR_BGR2GRAY))
    bordes = cv2.Canny(gris, 50, 150)
    h, w = gris.shape
    segs = cv2.HoughLinesP(bordes, 1, np.pi / 720, threshold=120, minLineLength=w // 6, maxLineGap=10)
    if segs is None:
        return im
    angulos = []
    for x1, y1, x2, y2 in np.asarray(segs).reshape(-1, 4):
        a = np.degrees(np.arctan2(y2 - y1, x2 - x1))
        if abs(a) <= 20:
            angulos.append(a)
    if len(angulos) < 3:
        return im
    angulo = float(np.median(angulos))
    if abs(angulo) < 0.3:
        return im
    M = cv2.getRotationMatrix2D((w / 2, h / 2), angulo, 1.0)
    return cv2.warpAffine(im, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)


def _mascara_papel(gris) -> "np.ndarray | None":
    """La hoja (clara) frente al fondo (mesa, mano). Se encoge un poco para dejar fuera su borde."""
    suave = cv2.GaussianBlur(gris, (9, 9), 0)
    _, claro = cv2.threshold(suave, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    contornos, _ = cv2.findContours(claro, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contornos:
        return None
    c = max(contornos, key=cv2.contourArea)
    h, w = gris.shape
    if cv2.contourArea(c) < 0.3 * h * w or cv2.contourArea(c) > 0.98 * h * w:
        return None
    mascara = np.zeros_like(gris)
    cv2.drawContours(mascara, [c], -1, 255, thickness=-1)
    k = max(9, int(min(h, w) * 0.015))
    return cv2.erode(mascara, np.ones((k, k), np.uint8))


def aplanar_tabla(im) -> tuple["np.ndarray", bool, tuple[int, int, int, int]]:
    """Recorta y endereza la tabla. Devuelve (imagen, se_encontró, caja en la imagen original)."""
    gris_crudo = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY)
    gris = sin_sombras(gris_crudo)
    bw = binaria(gris)
    hor, ver = _lineas(bw)
    lineas = cv2.add(hor, ver)
    papel = _mascara_papel(gris_crudo)
    if papel is not None:
        lineas = cv2.bitwise_and(lineas, papel)   # el borde del papel no es la tabla
    rejilla = cv2.dilate(lineas, np.ones((5, 5), np.uint8), iterations=2)
    contornos, _ = cv2.findContours(rejilla, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    h, w = gris.shape
    if not contornos:
        return im, False, (0, 0, w, h)
    c = max(contornos, key=cv2.contourArea)
    if cv2.contourArea(c) < 0.03 * h * w:
        return im, False, (0, 0, w, h)
    bx, by, bw_, bh_ = cv2.boundingRect(c)
    dentro = hor[by:by + bh_, bx:bx + bw_]
    if cv2.contourArea(c) < 0.15 * h * w and len(_picos_simples(dentro.sum(axis=1) / 255, bw_ * 0.5)) < 3:
        return im, False, (0, 0, w, h)
    x, y, cw, ch = cv2.boundingRect(c)
    # Las cuatro esquinas: los puntos del contorno más cercanos a las esquinas de su caja.
    pts = c.reshape(-1, 2).astype("float32")
    esquinas_caja = np.array([[x, y], [x + cw, y], [x + cw, y + ch], [x, y + ch]], dtype="float32")
    esquinas = np.array([pts[np.argmin(((pts - e) ** 2).sum(axis=1))] for e in esquinas_caja], dtype="float32")
    esquinas = _ordenar_esquinas(esquinas)
    # Un margen hacia afuera: el borde de una hoja curva corta las primeras letras.
    centro = esquinas.mean(axis=0)
    esquinas = centro + (esquinas - centro) * np.array([1.025, 1.0], dtype="float32")
    esquinas[:, 0] = esquinas[:, 0].clip(0, w - 1)
    esquinas[:, 1] = esquinas[:, 1].clip(0, h - 1)
    ancho = int(max(np.linalg.norm(esquinas[0] - esquinas[1]), np.linalg.norm(esquinas[3] - esquinas[2])))
    alto = int(max(np.linalg.norm(esquinas[0] - esquinas[3]), np.linalg.norm(esquinas[1] - esquinas[2])))
    if ancho < 200 or alto < 100:
        return im, False, (0, 0, w, h)
    destino = np.array([[0, 0], [ancho - 1, 0], [ancho - 1, alto - 1], [0, alto - 1]], dtype="float32")
    M = cv2.getPerspectiveTransform(esquinas, destino)
    plana = cv2.warpPerspective(im, M, (ancho, alto), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    return plana, True, (x, y, cw, ch)


def _rectas(mascara, vertical: bool, largo_min: int) -> list[tuple[float, float]]:
    """Rectas de la rejilla como (pendiente, intercepto): x = m·y + b (verticales) o y = m·x + b (horizontales).

    Las fotos de hojas curvas dejan líneas un poco inclinadas aun después de aplanar
    la tabla; por eso cada línea se modela como recta y se evalúa donde haga falta.
    """
    segs = cv2.HoughLinesP(mascara, 1, np.pi / 360, threshold=60, minLineLength=largo_min, maxLineGap=25)
    if segs is None:
        return []
    candidatas = []
    for x1, y1, x2, y2 in np.asarray(segs).reshape(-1, 4):
        if vertical:
            if abs(x2 - x1) > abs(y2 - y1) * 0.15:
                continue
            m = (x2 - x1) / (y2 - y1) if y2 != y1 else 0.0
            candidatas.append((m, x1 - m * y1, abs(y2 - y1)))
        else:
            if abs(y2 - y1) > abs(x2 - x1) * 0.15:
                continue
            m = (y2 - y1) / (x2 - x1) if x2 != x1 else 0.0
            candidatas.append((m, y1 - m * x1, abs(x2 - x1)))
    if not candidatas:
        return []
    # Agrupa los segmentos de una misma línea por su posición en el centro de la imagen.
    centro = (mascara.shape[0] if vertical else mascara.shape[1]) / 2
    candidatas.sort(key=lambda c: c[0] * centro + c[1])
    grupos: list[list] = [[candidatas[0]]]
    for c in candidatas[1:]:
        ultimo = grupos[-1][-1]
        if abs((c[0] * centro + c[1]) - (ultimo[0] * centro + ultimo[1])) <= 10:
            grupos[-1].append(c)
        else:
            grupos.append([c])
    rectas = []
    for g in grupos:
        peso = sum(c[2] for c in g)
        if peso < largo_min:
            continue
        m = sum(c[0] * c[2] for c in g) / peso
        b = sum(c[1] * c[2] for c in g) / peso
        if _cobertura(mascara, m, b, vertical) >= 0.6:
            rectas.append((m, b))
    return rectas


def _cobertura(mascara, m: float, b: float, vertical: bool) -> float:
    """Qué parte de la recta está realmente pintada en la máscara.

    Los trazos de letras alineadas (la «C» de una columna de nombres) forman
    segmentos que Hough une; una línea de la rejilla, en cambio, se ve casi entera.
    """
    alto, ancho = mascara.shape
    largo = alto if vertical else ancho
    pasos = np.arange(0, largo, 3)
    if vertical:
        xs = np.clip((m * pasos + b).astype(int), 0, ancho - 1)
        tramo = np.stack([mascara[pasos, np.clip(xs + d, 0, ancho - 1)] for d in (-2, -1, 0, 1, 2)]).max(axis=0)
    else:
        ys = np.clip((m * pasos + b).astype(int), 0, alto - 1)
        tramo = np.stack([mascara[np.clip(ys + d, 0, alto - 1), pasos] for d in (-2, -1, 0, 1, 2)]).max(axis=0)
    pintado = tramo > 0
    if not pintado.any():
        return 0.0
    # Solo cuenta entre el primer y el último punto pintado (una columna puede no llegar al borde).
    idx = np.where(pintado)[0]
    return float(pintado[idx[0]: idx[-1] + 1].mean())


def altura_letra(bw) -> int:
    """Altura típica de la letra: mediana de los componentes del tamaño de un carácter."""
    n, _, stats, _ = cv2.connectedComponentsWithStats(bw, connectivity=8)
    alturas = [s[cv2.CC_STAT_HEIGHT] for s in stats[1:] if 6 <= s[cv2.CC_STAT_HEIGHT] <= 80
               and s[cv2.CC_STAT_WIDTH] <= 80]
    return int(np.median(alturas)) if alturas else 15


def mascaras_rejilla(gris):
    """Máscaras de las líneas horizontales y verticales de la tabla."""
    bw = binaria(gris)
    h, w = bw.shape
    letra = altura_letra(bw)
    largo_v = max(int(letra * 2.2), h // 60, 12)
    gruesa_v = cv2.dilate(bw, np.ones((1, 3), np.uint8))
    gruesa_h = cv2.dilate(bw, np.ones((3, 1), np.uint8))
    hor = cv2.morphologyEx(gruesa_h, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (max(w // 30, 20), 1)))
    ver = cv2.morphologyEx(gruesa_v, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (1, largo_v)))
    return hor, ver


def sin_rejilla(gris) -> "np.ndarray":
    """La tabla sin sus líneas: Tesseract las confunde con letras y desordena filas casi vacías."""
    hor, ver = mascaras_rejilla(gris)
    lineas = cv2.dilate(cv2.add(hor, ver), np.ones((3, 3), np.uint8))
    limpio = gris.copy()
    limpio[lineas > 0] = 255
    return limpio


def rejilla(plana) -> tuple[list[tuple[float, float]], list[tuple[float, float]]]:
    """(horizontales, verticales) como rectas, ordenadas.

    Un trazo cuenta como línea de la rejilla si mide más de 2,2 veces la altura de la
    letra: así los palos de las letras (que se repiten alineados fila tras fila) no se
    confunden con columnas. Antes se engruesa 3 px para tolerar líneas inclinadas.
    """
    hor, ver = mascaras_rejilla(sin_sombras(cv2.cvtColor(plana, cv2.COLOR_BGR2GRAY)))
    h, w = hor.shape
    horizontales = _rectas(hor, False, int(w * 0.3))
    verticales = _rectas(ver, True, int(h * 0.25))
    return horizontales, verticales


# ── lectura ───────────────────────────────────────────────────────────────
@dataclass
class Palabra:
    texto: str
    confianza: float
    x: int
    y: int
    w: int
    h: int
    linea: tuple[int, int, int]  # bloque, párrafo, línea de Tesseract


def palabras(gris, psm: int = 4) -> list[Palabra]:
    d = pytesseract.image_to_data(gris, lang="spa", config=f"--psm {psm}", output_type=pytesseract.Output.DICT)
    out = []
    for i, t in enumerate(d["text"]):
        if t.strip() and float(d["conf"][i]) >= 0:
            out.append(Palabra(t.strip(), float(d["conf"][i]) / 100, d["left"][i], d["top"][i], d["width"][i],
                               d["height"][i], (d["block_num"][i], d["par_num"][i], d["line_num"][i])))
    return out


BASURA_BORDE = re.compile(r"^[\[\]|¡!{}_—–-]+|[\[\]|¡!{}_—–-]+$")


def _limpiar(texto: str) -> str:
    """Quita restos de las líneas de la rejilla que el OCR toma por letras ([ | ¡ …)."""
    return BASURA_BORDE.sub("", texto).strip()


def resaltado(color_fila) -> bool:
    """Fila marcada con resaltador: una fracción grande de píxeles claros y muy saturados."""
    if color_fila.size == 0:
        return False
    hsv = cv2.cvtColor(color_fila, cv2.COLOR_BGR2HSV)
    marcados = (hsv[:, :, 1] > 60) & (hsv[:, :, 2] > 120)
    return float(marcados.mean()) > 0.35


def _franjas(horizontales, ancho: int, alto: int) -> list[tuple[int, int, tuple, tuple]]:
    """Franjas de fila entre líneas horizontales consecutivas (con la inclinación de cada línea).

    Devuelve (y0, y1, recta_de_arriba, recta_de_abajo): la franja cubre las dos rectas
    completas; después se descartan las palabras cuyo centro cae fuera de ellas.
    """
    rectas = [(0.0, 0.0)] + list(horizontales) + [(0.0, float(alto))]
    franjas = []
    for (ma, ba), (mb, bb) in zip(rectas[:-1], rectas[1:]):
        a_min, a_max = min(ba, ma * ancho + ba), max(ba, ma * ancho + ba)
        b_min, b_max = min(bb, mb * ancho + bb), max(bb, mb * ancho + bb)
        if b_min - a_max >= 10:
            franjas.append((max(0, int(a_min)), min(alto, int(b_max) + 1), (ma, ba), (mb, bb)))
    return franjas


def _leer_recorte(gris, numerica: bool) -> tuple[str, float]:
    if gris.size == 0 or gris.shape[0] < 6 or gris.shape[1] < 6:
        return "", 0.0
    f = max(1.0, min(4.0, 56 / gris.shape[0]))
    g = cv2.resize(gris, None, fx=f, fy=f, interpolation=cv2.INTER_CUBIC)
    g = cv2.copyMakeBorder(g, 12, 12, 12, 12, cv2.BORDER_CONSTANT, value=255)
    cfg = "--psm 7" + (" -c tessedit_char_whitelist=$0123456789.," if numerica else "")
    d = pytesseract.image_to_data(g, lang="spa", config=cfg, output_type=pytesseract.Output.DICT)
    ps = [(t, float(c)) for t, c in zip(d["text"], d["conf"]) if t.strip() and float(c) >= 0]
    if not ps:
        return "", 0.0
    return " ".join(t for t, _ in ps), sum(c for _, c in ps) / len(ps) / 100


def _releer_celdas(lectura: LecturaImagen, limpio, horizontales, verticales) -> None:
    """Relee celda por celda lo que la lectura por fila dejó dudoso.

    En una fila con texto encimado Tesseract puede descartar la línea entera, valor
    incluido, aunque el valor esté limpio. Por eso el valor de cada fila se relee
    solo (con dígitos únicamente), y las celdas de texto de baja confianza también.
    """
    if not lectura.filas or not verticales:
        return
    alto, ancho = limpio.shape
    ncol = len(verticales) + 1
    # Columna de los valores: la que más importes trae.
    cuenta = [sum(1 for f in lectura.filas if j < len(f.celdas) and DINERO.search(f.celdas[j].texto)) for j in range(ncol)]
    col_valor = int(np.argmax(cuenta)) if max(cuenta) else None
    if col_valor is None:
        return

    def limites_columna(j: int, y: float) -> tuple[int, int]:
        bordes = [0.0] + [m * y + b for m, b in verticales] + [float(ancho)]
        return int(max(0, bordes[j])), int(min(ancho, bordes[j + 1]))

    trabajos = []
    for i, f in enumerate(lectura.filas):
        y0, y1 = f.caja[1], f.caja[1] + f.caja[3]
        ym = (y0 + y1) / 2
        for j in range(ncol):
            c = f.celdas[j] if j < len(f.celdas) else None
            if j == col_valor or (c is not None and c.texto and c.confianza < 0.5):
                x0, x1 = limites_columna(j, ym)
                trabajos.append((i, j, limpio[max(0, y0 - 3):min(alto, y1 + 3), x0 + 3:max(x0 + 4, x1 - 3)], j == col_valor))
    with ThreadPoolExecutor(max_workers=min(6, (os.cpu_count() or 2))) as hilos:
        resultados = list(hilos.map(lambda t: _leer_recorte(t[2], t[3]), trabajos))
    for (i, j, _, numerica), (texto, conf) in zip(trabajos, resultados):
        f = lectura.filas[i]
        while len(f.celdas) <= j:
            f.celdas.append(Celda(texto="", confianza=0.0, caja=(0, 0, 0, 0)))
        actual = f.celdas[j]
        if numerica:
            if DINERO.search(texto) and (not DINERO.search(actual.texto) or conf >= actual.confianza):
                nuevo, viejo = re.sub(r"\D", "", texto), re.sub(r"\D", "", actual.texto)
                if DINERO.search(actual.texto) and nuevo[1:] == viejo and nuevo[:1] in "51":
                    continue  # la relectura tomó el «$» por un dígito: se queda la primera
                f.celdas[j] = Celda(texto=texto, confianza=conf, caja=actual.caja)
        elif texto and conf > actual.confianza + 0.1:
            f.celdas[j] = Celda(texto=_limpiar(texto), confianza=conf, caja=actual.caja)


def _marcar_resaltadas(lectura: LecturaImagen, plana) -> None:
    """Resaltador: la fila tiene bastante más color que las demás de la misma hoja.

    Se compara contra la propia hoja porque con poca luz o poco contraste el rosa del
    resaltador pierde saturación y un umbral fijo no lo ve.
    """
    if len(lectura.filas) < 3:
        return
    sat = cv2.cvtColor(plana, cv2.COLOR_BGR2HSV)[:, :, 1].astype(np.float32)
    medias = []
    for f in lectura.filas:
        y0, y1 = f.caja[1], f.caja[1] + max(f.caja[3], 1)
        medias.append(float(sat[y0:y1, :].mean()) if y1 > y0 else 0.0)
    base = float(np.median(medias))
    for f, m in zip(lectura.filas, medias):
        f.resaltada = f.resaltada or (m > base + 10 and m > base * 1.6)


def _subfilas(ps: list[Palabra], escala: float) -> list[list[Palabra]]:
    """Una franja puede abarcar varias filas (faltó una línea de la rejilla en la foto).

    Si Tesseract encontró en ella varias líneas de texto con importe, cada una es una
    fila. Si dos traen el MISMO importe, es la hoja impresa dos veces: queda la más segura.
    """
    lineas: dict[tuple, list[Palabra]] = {}
    for p in ps:
        lineas.setdefault(p.linea, []).append(p)
    con_importe = [l for l in lineas.values() if any(DINERO.search(p.texto) for p in l)]
    if len(con_importe) <= 1:
        return [ps]
    # Las líneas sin importe (restos, segundas líneas de un detalle) se pegan a la línea con importe más cercana.
    centro = lambda l: sum(p.y + p.h / 2 for p in l) / len(l)
    filas = {id(l): list(l) for l in con_importe}
    for l in lineas.values():
        if l in con_importe:
            continue
        cercana = min(con_importe, key=lambda c: abs(centro(c) - centro(l)))
        filas[id(cercana)].extend(l)
    resultado: list[list[Palabra]] = []
    vistos: dict[str, int] = {}
    for l in sorted(con_importe, key=centro):
        fila = filas[id(l)]
        importe = re.sub(r"\D", "", next(p.texto for p in l if DINERO.search(p.texto)))
        conf = sum(p.confianza for p in fila) / len(fila)
        if importe in vistos:
            k = vistos[importe]
            if conf > sum(p.confianza for p in resultado[k]) / len(resultado[k]):
                resultado[k] = fila
            continue
        vistos[importe] = len(resultado)
        resultado.append(fila)
    return resultado


def _celdas_de(ps: list[Palabra], verticales, ncol: int, dy: int, escala: float,
               arriba=None, abajo=None) -> list[Celda]:
    grupos: list[list[Palabra]] = [[] for _ in range(ncol)]
    for p in ps:
        cx = (p.x + p.w / 2) / escala
        cy = (p.y + p.h / 2) / escala + dy
        if arriba is not None and (cy < arriba[0] * cx + arriba[1] - 2 or cy > abajo[0] * cx + abajo[1] + 2):
            continue  # pertenece a la fila vecina
        col = sum(1 for m, b in verticales if m * cy + b < cx)
        grupos[min(col, ncol - 1)].append(p)
    celdas = []
    for lista in grupos:
        if lista:
            texto = _limpiar(" ".join(p.texto for p in lista))
            conf = sum(p.confianza for p in lista) / len(lista)
            x0 = int(min(p.x for p in lista) / escala); y0 = int(min(p.y for p in lista) / escala) + dy
            x1 = int(max(p.x + p.w for p in lista) / escala); y1 = int(max(p.y + p.h for p in lista) / escala) + dy
            celdas.append(Celda(texto=texto, confianza=conf, caja=(x0, y0, x1 - x0, y1 - y0)))
        else:
            celdas.append(Celda(texto="", confianza=0.0, caja=(0, 0, 0, 0)))
    return celdas


def leer_imagen(ruta_o_bytes) -> LecturaImagen:
    im = cargar(ruta_o_bytes)
    im, giro = orientar(im)
    im = enderezar(im)
    plana, encontrada, caja = aplanar_tabla(im)
    lectura = LecturaImagen(giro=giro, tabla_encontrada=encontrada, tabla=plana)
    gris = sin_sombras(cv2.cvtColor(plana, cv2.COLOR_BGR2GRAY))
    alto, ancho = gris.shape
    horizontales, verticales = rejilla(plana) if encontrada else ([], [])
    ncol = len(verticales) + 1
    bajas = 0

    if len(horizontales) >= 3:
        # Una lectura por fila: ampliada para que la letra quede de ~30 px de alto.
        franjas = _franjas(horizontales, ancho, alto)
        limpio = sin_rejilla(gris)

        def leer_franja(fr):
            y0, y1 = fr[0], fr[1]
            tira = limpio[y0:y1, :]
            escala = max(1.0, min(3.0, 64 / max(tira.shape[0], 1)))
            grande = cv2.resize(tira, None, fx=escala, fy=escala, interpolation=cv2.INTER_CUBIC)
            return palabras(grande, 6), escala

        with ThreadPoolExecutor(max_workers=min(6, (os.cpu_count() or 2))) as hilos:
            leidas = list(hilos.map(leer_franja, franjas))
        for (y0, y1, arriba, abajo), (ps, escala) in zip(franjas, leidas):
            if not ps:
                continue
            for sub in _subfilas(ps, escala):
                sy0 = y0 + int(min(p.y for p in sub) / escala)
                sy1 = y0 + int(max(p.y + p.h for p in sub) / escala)
                celdas = _celdas_de(sub, verticales, ncol, y0, escala, arriba, abajo)
                fila = Fila(celdas=celdas, resaltada=resaltado(plana[sy0:sy1, :]), caja=(0, sy0, ancho, max(1, sy1 - sy0)))
                if any(c.texto for c in celdas):
                    lectura.filas.append(fila)
        _releer_celdas(lectura, limpio, horizontales, verticales)
        _marcar_resaltadas(lectura, plana)
    else:
        # Sin rejilla: las líneas que Tesseract agrupa.
        grupos: dict[tuple, list[Palabra]] = {}
        for p in palabras(gris, 4):
            grupos.setdefault(p.linea, []).append(p)
        for clave in sorted(grupos, key=lambda k: min(p.y for p in grupos[k])):
            ps = grupos[clave]
            y0 = min(p.y for p in ps); y1 = max(p.y + p.h for p in ps)
            celdas = _celdas_de(ps, verticales, ncol, 0, 1.0)
            lectura.filas.append(Fila(celdas=celdas, resaltada=resaltado(plana[y0:y1, :]), caja=(0, y0, ancho, y1 - y0)))
    for f in lectura.filas:
        if f.confianza < 0.6:
            bajas += 1
    lectura.texto_cabecera = "\n".join(" ".join(c.texto for c in f.celdas if c.texto) for f in lectura.filas[:4])
    lectura.encimada = bool(lectura.filas) and bajas / len(lectura.filas) > 0.5
    _notas_fuera_de_tabla(im, caja, encontrada, lectura)
    return lectura


# ── notas a mano y credenciales ──────────────────────────────────────────
CREDENCIAL = re.compile(
    r"(?=.*[A-Za-zÁÉÍÓÚÑáéíóúñ])(?=.*\d)(?=.*[@*#$%&!?._\-/])\S{5,}"   # letras + cifras + símbolo
    r"|\S+@\S*"                                                          # correo o usuario con @
    r"|(?i:clave|contrase[ñn]a|usuario|password|pass|user)\b")
CIFRA_NOTA = re.compile(r"\b(SF|S\.F\.|SALDO\s*A?\s*FAVOR|ANT|ANTICIPO)\s*[:=]?\s*\$?\s*(\d[\d.,]{4,}\d)", re.I)


def parece_credencial(texto: str) -> bool:
    return any(CREDENCIAL.fullmatch(t) or CREDENCIAL.match(t) for t in texto.split())


def _notas_fuera_de_tabla(im, caja, encontrada: bool, lectura: LecturaImagen) -> None:
    """Lee SOLO para detectar notas a mano fuera de la tabla. El texto nunca se guarda."""
    h, w = im.shape[:2]
    x, y, cw, ch = caja
    zonas = [("arriba", im[0:y, :]), ("abajo", im[y + ch:h, :])] if encontrada else []
    for donde, zona in zonas:
        if zona.size == 0 or zona.shape[0] < 20:
            continue
        g = sin_sombras(cv2.cvtColor(zona, cv2.COLOR_BGR2GRAY))
        d = pytesseract.image_to_data(g, lang="spa", config="--psm 11", output_type=pytesseract.Output.DICT)
        texto = " ".join(t for t in d["text"] if t.strip())
        _revisar_texto_libre(texto, lectura)
        seguras = sum(1 for t, c in zip(d["text"], d["conf"]) if len(t.strip()) >= 3 and float(c) >= 70)
        if _hay_tinta(g) and seguras < 4:
            lectura.anotaciones = True
        if donde == "arriba":
            lectura.texto_arriba = pytesseract.image_to_string(g, lang="spa", config="--psm 6")


def _hay_tinta(gris) -> bool:
    """Trazos oscuros de tamaño de letra o mayores (escritura) en una zona sin texto impreso legible."""
    bw = cv2.adaptiveThreshold(gris, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY_INV, 31, 25)
    n, _, stats, _ = cv2.connectedComponentsWithStats(bw, connectivity=8)
    trazos = [s for s in stats[1:] if s[cv2.CC_STAT_HEIGHT] >= 14 and s[cv2.CC_STAT_AREA] >= 60
              and s[cv2.CC_STAT_WIDTH] < gris.shape[1] * 0.5]
    return len(trazos) >= 4


def _revisar_texto_libre(texto: str, lectura: LecturaImagen) -> None:
    for m in CIFRA_NOTA.finditer(texto):
        lectura.notas_a_mano.append(f"{m.group(1).upper()}: {m.group(2)}")
    for palabra in texto.split():
        if CREDENCIAL.fullmatch(palabra) and not DINERO.fullmatch(palabra):
            lectura.credenciales_descartadas += 1


def recorte_png(lectura: LecturaImagen, caja: tuple[int, int, int, int], margen: int = 4) -> bytes:
    """Recorte de la tabla aplanada (para la pantalla de verificación). Nunca la foto completa."""
    if lectura.tabla is None:
        return b""
    x, y, w, h = caja
    alto, ancho = lectura.tabla.shape[:2]
    trozo = lectura.tabla[max(0, y - margen):min(alto, y + h + margen), max(0, x - margen):min(ancho, x + w + margen)]
    ok, buf = cv2.imencode(".png", trozo)
    return buf.tobytes() if ok else b""


def texto_de(lectura: LecturaImagen, caja: tuple[int, int, int, int]) -> str:
    """Texto corrido de una zona de la tabla aplanada (para el encabezado, que tiene varias líneas)."""
    if lectura.tabla is None:
        return ""
    x, y, w, h = caja
    zona = lectura.tabla[max(0, y - 2):y + h + 2, x:x + w]
    if zona.size == 0:
        return ""
    gris = sin_sombras(cv2.cvtColor(zona, cv2.COLOR_BGR2GRAY))
    escala = max(1.0, min(3.0, 90 / max(zona.shape[0], 1)))
    gris = cv2.resize(gris, None, fx=escala, fy=escala, interpolation=cv2.INTER_CUBIC)
    return pytesseract.image_to_string(gris, lang="spa", config="--psm 6")
