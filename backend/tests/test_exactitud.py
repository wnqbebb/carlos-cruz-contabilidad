"""Pruebas de EXACTITUD: ningún importe debe pasar nunca por un float.

Esta es la promesa central del sistema. Si alguna de estas pruebas falla,
alguien reintrodujo un `float` en el camino del dinero y hay que revertirlo
antes de desplegar.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

import pytest

from app.exactitud import a_json, cuadra, dec_a_texto, suma
from app.utils import nit as unit

D = Decimal


# ── el serializador ─────────────────────────────────────────────────────────
def test_decimal_sale_como_texto_no_como_float():
    assert a_json(D("1423500.10")) == "1423500.10"
    assert isinstance(a_json(D("1423500.10")), str)


def test_decimal_sin_notacion_cientifica():
    """Decimal('1E+7') no puede salir como '1E+7': el frontend no lo entendería."""
    assert dec_a_texto(D("1E+7")) == "10000000"
    assert dec_a_texto(D("0.00")) == "0"
    assert dec_a_texto(D("-0.50")) == "-0.50"


def test_ningun_float_en_la_salida():
    @dataclass
    class Linea:
        cuenta: str
        debito: Decimal
        credito: Decimal

    datos = {
        "lineas": [Linea("1105", D("0.1"), D("0.2"))],
        "fecha": date(2025, 1, 31),
        "cuadra": True,
        "cuentas": 20,
        "anidado": {"total": D("30000000")},
    }
    salida = a_json(datos)
    crudo = json.dumps(salida)

    def buscar_floats(obj, ruta="raíz"):
        if isinstance(obj, float):
            pytest.fail(f"Se encontró un float en {ruta}: {obj!r}")
        if isinstance(obj, dict):
            for k, v in obj.items():
                buscar_floats(v, f"{ruta}.{k}")
        if isinstance(obj, list):
            for i, v in enumerate(obj):
                buscar_floats(v, f"{ruta}[{i}]")

    buscar_floats(json.loads(crudo))
    assert salida["lineas"][0]["debito"] == "0.1"
    assert salida["cuadra"] is True          # los booleanos siguen siendo booleanos
    assert salida["cuentas"] == 20           # los conteos siguen siendo enteros
    assert salida["fecha"] == "2025-01-31"


def test_suma_exacta_donde_el_float_falla():
    # Con floats, 0.1 + 0.2 da 0.30000000000000004.
    assert suma([D("0.1"), D("0.2")]) == D("0.3")
    # Mil centavos deben dar exactamente diez pesos.
    assert suma([D("0.01")] * 1000) == D("10")
    assert float(D("0.1") + D("0.2")) != 0.1 + 0.2 or True  # documenta el contraste


def test_cuadra_no_tolera_un_peso():
    """En contabilidad un peso de diferencia es un error, no un redondeo."""
    assert cuadra(D("100"), D("100"))
    assert not cuadra(D("100"), D("101"))
    assert not cuadra(D("100"), D("100.01"))


# ── el NIT y su dígito de verificación ──────────────────────────────────────
@pytest.mark.parametrize(
    "base,dv_esperado",
    [
        ("[NIT]", "9"),   # FANANT (NIT real del cliente)
        ("800197268", "4"),
        ("860002964", "4"),
        ("899999061", "9"),
    ],
)
def test_digito_verificacion_contra_nits_reales(base, dv_esperado):
    assert unit.digito_verificacion(base) == dv_esperado


def test_nit_se_limpia_de_puntos_y_guiones():
    for entrada in ("[NIT]-9", "[NIT]-9", " [NIT] ", "[NIT]"):
        assert unit.limpiar(entrada) == "[NIT]"


def test_nit_formateado():
    assert unit.formatear("[NIT]") == "[NIT]-9"
    assert unit.formatear("[NIT]", "9") == "[NIT]-9"


def test_nit_invalido_se_rechaza():
    assert not unit.valido("123")             # demasiado corto
    assert not unit.valido("[NIT]", "3")  # el DV no corresponde
    assert unit.valido("[NIT]", "9")


def test_turno_dian_por_ultimo_digito():
    assert unit.turno_dian("[NIT]") == 8
    assert unit.turno_dian("901897820") == 10  # el 0 es el último turno
    assert unit.turno_dian("901897821") == 1


# ── la API completa ─────────────────────────────────────────────────────────
def _recorrer(obj, ruta="raíz"):
    """Devuelve las rutas donde aparece un float en la respuesta JSON."""
    if isinstance(obj, float):
        return [f"{ruta} = {obj!r}"]
    hallados = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            hallados += _recorrer(v, f"{ruta}.{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            hallados += _recorrer(v, f"{ruta}[{i}]")
    return hallados


def test_la_respuesta_del_calculo_no_contiene_ni_un_float(cliente_api):
    """Prueba de extremo a extremo con los archivos reales del cliente.

    Es la red de seguridad más importante del proyecto: recorre TODA la
    respuesta del cálculo (balance, estados, mayor, nómina, inventario) y falla
    si encuentra un solo float. Si falla, alguien reintrodujo un float en el
    camino del dinero.
    """
    cliente = cliente_api.post("/api/clientes", json={
        "nit": "[NIT]", "razon_social": "FARMACIA NATURISTA ANTARES SAS",
    }).json()

    importacion = cliente_api.post(f"/api/importar/ejemplo?cliente_id={cliente['id']}").json()
    assert importacion["sesion_id"]

    mapeo = {m["normalizado"]: m["codigo"] for m in importacion["mapeo"] if m["codigo"]}
    respuesta = cliente_api.post("/api/calcular", json={
        "sesion_id": importacion["sesion_id"], "cliente_id": cliente["id"],
        "empresa": {}, "mapeo": mapeo, "incluir": {}, "decisiones": {}, "config": {},
    })
    assert respuesta.status_code == 200, respuesta.text
    datos = respuesta.json()

    floats = _recorrer(datos)
    assert not floats, "La API devolvió floats en:\n" + "\n".join(floats[:20])

    # Y los importes siguen siendo legibles y exactos.
    resumen = datos["resumen"]
    assert isinstance(resumen["total_activo"], str)
    D(resumen["total_activo"])          # parsea como decimal sin perder nada
    D(resumen["utilidad_neta"])
    assert resumen["esf_cuadra"] is True
    assert datos["guardado"] is True


def test_el_periodo_guardado_se_relee_identico(cliente_api):
    """Lo que se guarda en la base y se vuelve a leer debe ser idéntico al peso."""
    cliente = cliente_api.post("/api/clientes", json={
        "nit": "[NIT]", "razon_social": "FARMACIA NATURISTA ANTARES SAS",
    }).json()
    imp = cliente_api.post(f"/api/importar/ejemplo?cliente_id={cliente['id']}").json()
    mapeo = {m["normalizado"]: m["codigo"] for m in imp["mapeo"] if m["codigo"]}
    calculado = cliente_api.post("/api/calcular", json={
        "sesion_id": imp["sesion_id"], "cliente_id": cliente["id"],
        "empresa": {}, "mapeo": mapeo, "incluir": {}, "decisiones": {}, "config": {},
    }).json()

    periodo_id = calculado["periodo"]["id"]
    releido = cliente_api.get(f"/api/periodos/{periodo_id}/resultado").json()["resultado"]

    assert releido["resumen"]["total_activo"] == calculado["resumen"]["total_activo"]
    assert releido["resumen"]["utilidad_neta"] == calculado["resumen"]["utilidad_neta"]
    assert not _recorrer(releido), "el resultado releído trae floats"

    # Los movimientos guardados cuadran débitos con créditos, al peso.
    movs = cliente_api.get(f"/api/clientes/{cliente['id']}/movimientos").json()
    assert movs["total"] > 0
    assert D(movs["suma_debito"]) == D(movs["suma_credito"])
