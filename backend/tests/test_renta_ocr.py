"""Lectura de fotos de reportes de exógena (v2.3 · Fase 5, 5.3 y 5.10).

- Contribuyente F: foto sintética difícil, generada al correr (girada, en perspectiva,
  poco contraste, sombra, texto encimado, resaltados, nota a mano con aspecto de
  contraseña, «SF: …» y un recetario en el margen).
- Caso B: las tres fotos reales del contador, solo si existe `privado/` (no va a git).
"""
import json
import re
from decimal import Decimal as D
from pathlib import Path

import pytest

from app.config import PRIVADO
from app.renta import clasificacion as C
from app.renta import documentos, ocr
from app.renta.lectura import unir_paginas, validar_sumas

from .renta.fotos_sinteticas import CONTRIBUYENTE_F, fotografiar, hoja

pytestmark = pytest.mark.skipif(not ocr.disponible(), reason="Tesseract no está instalado en este equipo")

IMAGENES_B = PRIVADO / "renta" / "imagenes"


@pytest.fixture(scope="module")
def foto_f() -> bytes:
    return fotografiar(hoja())


@pytest.fixture(scope="module")
def leido_f(foto_f):
    return documentos.leer_archivo("contribuyente_f.jpg", foto_f)


def test_foto_dificil_topes_y_lineas(leido_f):
    rep = leido_f.reporte
    assert rep.numero_doc == CONTRIBUYENTE_F["documento"]["numero"]        # se enderezó (venía girada 90°)
    assert rep.topes == {int(k): v for k, v in CONTRIBUYENTE_F["topes"].items()}
    esperados = sorted(v for *_, v, _ in CONTRIBUYENTE_F["lineas"])
    leidos = sorted(l.valor for l in rep.lineas)
    aciertos = sum(1 for v in esperados if v in leidos)
    assert aciertos >= len(esperados) - 1, (esperados, leidos)
    validacion = {v["tope"]: v["estado"] for v in validar_sumas(rep)}
    assert all(e in ("cuadra", "corregida", "redondeo") for e in validacion.values()), validacion


def test_foto_dificil_resaltados_y_notas_a_mano(leido_f):
    rep = leido_f.reporte
    assert sum(1 for l in rep.lineas if l.resaltada) >= 2
    # La nota con aspecto de contraseña se detecta y NO se guarda en ningún lado.
    assert rep.anotaciones_a_mano or rep.credenciales_descartadas
    todo = json.dumps([l.a_dict() for l in rep.lineas] + [rep.nombre, rep.sugerencias_a_mano], ensure_ascii=False)
    assert "1977" not in todo and "@" not in todo
    # La cifra útil escrita a mano se ofrece como sugerencia, no como dato.
    assert any(re.sub(r"\D", "", s) == "6275000" for s in rep.sugerencias_a_mano)
    # Solo se guardan recortes de filas de la tabla, nunca la foto completa.
    assert leido_f.recortes and all(len(png) < 200_000 for png in leido_f.recortes.values())


def test_foto_dificil_pagos_de_una_empresa_son_una_pregunta(leido_f):
    clas = C.clasificar_todas(leido_f.reporte.lineas)
    qs = C.preguntas(clas, leido_f.reporte.sugerencias_a_mano)
    pagadores = [q for q in qs if q.id.startswith("pagador:")]
    assert len(pagadores) == 1 and "2 documentos" in pagadores[0].texto
    assert any(q.id == "saldo_favor" and q.defecto == "no" for q in qs)   # escrito a mano: se confirma


def test_foto_dificil_por_la_api(cliente_api, foto_f):
    cid = cliente_api.post("/api/clientes", json={"nit": "10000006", "razon_social": "CONTRIBUYENTE F",
                                                 "tipo_persona": "natural"}).json()["id"]
    r = cliente_api.post(f"/api/renta/{cid}/2025/documentos",
                         files=[("archivos", ("foto.jpg", foto_f, "image/jpeg"))])
    assert r.status_code == 200, r.text
    res = r.json()["resultado"]
    motivos = {m["tope"] for m in res["obligacion"]["motivos"] if m["supera"]}
    assert {"ingresos", "patrimonio", "consignaciones"} <= motivos
    assert res["anotaciones_a_mano"]
    assert any("avalúo" in m["texto"] for m in res["marcas"])
    linea = next(l for l in res["lineas"] if l["recorte"])
    png = cliente_api.get(f"/api/renta/{cid}/2025/recorte/{linea['recorte']}")
    assert png.status_code == 200 and png.content[:4] == b"\x89PNG"


@pytest.mark.skipif(not IMAGENES_B.exists(), reason="Caso B: sin la carpeta privado/renta/imagenes (fotos reales fuera de git)")
def test_caso_b_fotos_reales_en_desorden(capsys):
    archivos = [IMAGENES_B / n for n in ("3.png", "1.png", "2.png")]          # en desorden
    leidos = [documentos.leer_archivo(p.name, p.read_bytes()) for p in archivos]
    grupos = documentos.agrupar_por_contribuyente(leidos)
    assert not grupos["otros"]                                               # las tres son del mismo contribuyente
    rep, _ = unir_paginas([l.reporte for l in grupos["leidos"]])
    assert rep.topes == {1: "82535904", 2: "226543936", 3: "19977892", 4: "125053184", 5: "12910068"}
    assert rep.responsable_iva                                               # Tope 6
    from app.renta import obligacion
    o = obligacion.evaluar({"ingresos": rep.topes[1], "patrimonio": rep.topes[2], "consumos_tc": rep.topes[3],
                            "consignaciones": rep.topes[4], "compras": rep.topes[5],
                            "responsable_iva": rep.responsable_iva}, 2025)
    assert {m["tope"] for m in o["motivos"] if m["supera"]} >= {"ingresos", "patrimonio", "consignaciones",
                                                                "responsable_iva"}
    clas = C.clasificar_todas(rep.lineas)
    saldo = [c for c in clas if c.categoria == "anterior_saldo_favor"]
    assert saldo and saldo[0].linea.importe() == D("6275000")
    qs = C.preguntas(clas, rep.sugerencias_a_mano)
    # Los ≈ 12 pagos de una misma empresa por documentos soporte: UNA sola pregunta.
    pagadores = [q for q in qs if q.id.startswith("pagador:")]
    docs = max(int(re.search(r"en (\d+) documentos?", q.texto).group(1)) for q in pagadores)
    assert docs >= 8
    assert any(q.id == "saldo_favor" for q in qs)
    # La nota a mano del encabezado no se guarda; se avisa.
    assert rep.anotaciones_a_mano
    todo = json.dumps([l.a_dict() for l in rep.lineas], ensure_ascii=False)
    assert "@" not in todo
    # El patrimonio del año anterior está en la página 3 con el detalle encimado: el valor se lee y la
    # fila queda en ámbar para que el contador la clasifique con un clic.
    anterior = [l for l in rep.lineas if l.valor == "181910000"]
    assert anterior and anterior[0].encimada
    alta = sum(1 for l in rep.lineas if l.confianza >= 0.6) / len(rep.lineas)
    with capsys.disabled():
        print(f"\n  Caso B: {len(rep.lineas)} filas leídas · {alta:.0%} con confianza alta en el valor")


@pytest.mark.skipif(not (IMAGENES_B / "4.png").exists(), reason="Caso A (foto real): sin privado/renta/imagenes/4.png")
def test_caso_a_foto_real_lee_las_23_filas():
    """La foto real del caso A da exactamente los valores de la transcripción anonimizada."""
    caso = json.loads((Path(__file__).parent / "renta" / "caso_a.json").read_text(encoding="utf-8"))
    leido = documentos.leer_archivo("4.png", (IMAGENES_B / "4.png").read_bytes())
    rep = leido.reporte
    estados = {v["tope"]: v["estado"] for v in validar_sumas(rep)}
    assert rep.topes == {int(k): v for k, v in caso["topes"].items()}
    assert sorted(l.valor for l in rep.lineas) == sorted(l["valor"] for l in caso["lineas"])
    assert estados[4] == "redondeo" and all(e in ("cuadra", "corregida", "redondeo") for e in estados.values())
    assert sum(1 for l in rep.lineas if l.no_titular) == 2
    assert rep.anotaciones_a_mano                                     # la nota junto al nombre: no se guarda
