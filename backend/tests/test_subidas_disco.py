"""Archivos subidos en disco temporal, no en memoria (adición A5)."""
from __future__ import annotations

import gc
import io
import os
import time
import tracemalloc
import zipfile
from pathlib import Path

from app.repositorio import sesiones
from app.repositorio import subidas
from tests.test_ficha import _docx

ACTA = _docx(["ACTA DE CONSTITUCIÓN", "Se constituye la sociedad denominada PRUEBA DISCO S.A.S.", "NIT 900.555.444-1"])


def _docx_de(megas: int) -> bytes:
    """Un Word válido de ~`megas` MB: el acta más un anexo binario que no se puede comprimir."""
    buf = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(ACTA)) as origen, zipfile.ZipFile(buf, "w") as destino:
        for item in origen.infolist():
            destino.writestr(item, origen.read(item.filename))
        destino.writestr(zipfile.ZipInfo("word/media/anexo.bin"), os.urandom(megas * 1024 * 1024),
                         compress_type=zipfile.ZIP_STORED)
    return buf.getvalue()


def test_la_subida_queda_en_disco_y_la_sesion_solo_guarda_la_ruta(cliente_api):
    r = cliente_api.post("/api/subir", files=[("archivos", ("acta.docx", ACTA))]).json()
    s = sesiones.obtener(r["subida_id"])
    [ref] = s["archivos"]
    assert set(ref) == {"nombre", "ruta", "bytes"} and ref["bytes"] == len(ACTA)
    # v2.3 · C25: en disco va cifrado y con nombre aleatorio; se descifra igual al original.
    en_disco = Path(ref["ruta"]).read_bytes()
    assert en_disco != ACTA and en_disco.startswith(b"CC1") and b"PK" not in en_disco[:40]
    assert "acta" not in Path(ref["ruta"]).name
    assert subidas.leer([ref]) == [("acta.docx", ACTA)]
    assert Path(ref["ruta"]).parent == subidas.carpeta() / r["subida_id"]
    # Al confirmar se usa el archivo del disco y la carpeta se borra.
    cliente_api.post(f"/api/subir/{r['subida_id']}/confirmar", json={
        "clase": "contabilidad", "crear": {"nit": "900555444", "razon_social": "PRUEBA DISCO S.A.S."}})
    assert not (subidas.carpeta() / r["subida_id"]).exists()


def test_las_subidas_vencidas_se_borran_solas():
    vieja = subidas.guardar("vieja", [("a.csv", b"x;y")])
    nueva = subidas.guardar("nueva", [("b.csv", b"x;y")])
    hace_nueve_horas = time.time() - 9 * 3600
    os.utime(Path(vieja[0]["ruta"]).parent, (hace_nueve_horas, hace_nueve_horas))
    assert subidas.limpiar() >= 1
    assert not Path(vieja[0]["ruta"]).exists() and Path(nueva[0]["ruta"]).exists()
    assert subidas.leer(vieja) == []          # una subida limpiada no revienta: no devuelve nada
    subidas.borrar("nueva")


def test_nombres_peligrosos_no_salen_de_la_carpeta():
    [ref] = subidas.guardar("rara", [("..\\..\\otro/lado:raro?.xlsx", b"1")])
    assert Path(ref["ruta"]).parent == subidas.carpeta() / "rara"
    subidas.borrar("rara")


def test_diez_subidas_de_20_mb_no_llenan_la_memoria(cliente_api):
    """Antes cada subida retenía sus bytes 8 horas: 10 × 20 MB = 200 MB en memoria."""
    grande = _docx_de(20)
    assert len(grande) > 20 * 1024 * 1024
    gc.collect()
    tracemalloc.start()
    try:
        r = cliente_api.post("/api/subir", files=[("archivos", ("acta grande.docx", grande))])
        assert r.status_code == 200, r.text
        gc.collect()
        base = tracemalloc.get_traced_memory()[0]
        for i in range(10):
            r = cliente_api.post("/api/subir", files=[("archivos", (f"acta grande {i}.docx", grande))])
            assert r.status_code == 200, r.text
        gc.collect()
        retenido = tracemalloc.get_traced_memory()[0] - base
    finally:
        tracemalloc.stop()
    assert retenido < 15 * 1024 * 1024, f"Se retuvieron {retenido / 1024 / 1024:.1f} MB tras 10 subidas"
