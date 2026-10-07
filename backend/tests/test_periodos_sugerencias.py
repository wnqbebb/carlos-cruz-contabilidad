"""Periodos, cierres encadenados y sugerencias.

Las sugerencias son la parte del sistema que «opina», así que cada una se prueba
contra datos armados a propósito: si una se dispara sin dato que la sustente, o
deja de dispararse cuando debería, aquí se ve.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from app.inteligencia import sugerencias as sug
from app.repositorio import clientes as repo_clientes
from app.repositorio import periodos as repo

D = Decimal


# ── utilidades de montaje ───────────────────────────────────────────────────
def _cliente(**extra) -> dict:
    return repo_clientes.crear({"nit": "[NIT]", "razon_social": "ANTARES SAS", **extra})


def _resultado(desde: str, hasta: str, *, activo="0", pasivo="0", patrimonio="0",
               ingresos="0", gastos="0", utilidad="0", descuadre="0", cuentas=10,
               movimientos=5) -> dict:
    """Payload con la forma que produce el motor, ya serializado a cadenas.

    `cuentas` y `movimientos` van por encima de cero porque desde la v2.2 un
    resultado sin ninguna de las dos cosas se rechaza (H19): guardarlo borraría
    el trabajo anterior del periodo.
    """
    return {
        "empresa": {"periodo_desde": desde, "periodo_hasta": hasta},
        "resumen": {
            "total_activo": activo, "total_pasivo": pasivo, "total_patrimonio": patrimonio,
            "ingresos": ingresos, "total_gastos": gastos, "utilidad_neta": utilidad,
            "descuadre_esf": descuadre, "cuentas": cuentas, "movimientos": movimientos,
        },
    }


def _codigos(informe: dict) -> set[str]:
    return {s["codigo"] for s in informe["sugerencias"]}


def _buscar(informe: dict, codigo: str) -> dict:
    for s in informe["sugerencias"]:
        if s["codigo"] == codigo:
            return s
    pytest.fail(f"No se emitió la sugerencia {codigo}. Emitidas: {sorted(_codigos(informe))}")


# ── periodos ────────────────────────────────────────────────────────────────
def test_asegurar_es_idempotente(base_limpia):
    c = _cliente()
    p1 = repo.asegurar(c["id"], date(2025, 1, 1), date(2025, 1, 31))
    p2 = repo.asegurar(c["id"], date(2025, 1, 1), date(2025, 1, 31))
    assert p1["id"] == p2["id"]
    assert len(repo.listar(c["id"])) == 1


def test_periodo_invertido_se_rechaza(base_limpia):
    c = _cliente()
    with pytest.raises(repo.ErrorPeriodo):
        repo.asegurar(c["id"], date(2025, 1, 31), date(2025, 1, 1))


def test_guardar_resultado_extrae_los_indicadores(base_limpia):
    c = _cliente()
    p = repo.guardar_resultado(
        c["id"],
        _resultado("2025-01-01", "2025-01-31", activo="37144505", utilidad="-1234475.72", cuentas=20),
    )
    assert p["estado"] == "calculado"
    assert p["total_activo"] == "37144505.00"
    assert p["utilidad"] == "-1234475.72"
    assert p["cuentas"] == 20


def test_recalcular_reemplaza_y_no_duplica(base_limpia):
    c = _cliente()
    repo.guardar_resultado(c["id"], _resultado("2025-01-01", "2025-01-31", utilidad="100"))
    repo.guardar_resultado(c["id"], _resultado("2025-01-01", "2025-01-31", utilidad="200"))
    periodos = repo.listar(c["id"])
    assert len(periodos) == 1
    assert periodos[0]["utilidad"] == "200.00"


def test_resultado_completo_se_recupera_tal_cual(base_limpia):
    c = _cliente()
    payload = _resultado("2025-01-01", "2025-01-31", utilidad="-1234475.72")
    payload["reportes"] = {"balance": {"filas": [{"valor": "1423500.10"}]}}
    p = repo.guardar_resultado(c["id"], payload, {"config": {"calcular_renta": False}})
    guardado = repo.resultado(p["id"])
    assert guardado["resultado"]["reportes"]["balance"]["filas"][0]["valor"] == "1423500.10"
    assert guardado["peticion"]["config"]["calcular_renta"] is False


def test_movimientos_guardados_cuadran(base_limpia):
    c = _cliente()
    p = repo.guardar_resultado(c["id"], _resultado("2025-01-01", "2025-01-31"))
    movs = [
        {"cuenta": "110505", "debito": "1423500.10", "credito": "0", "fecha": "2025-01-15"},
        {"cuenta": "510506", "debito": "0", "credito": "1423500.10", "fecha": "2025-01-15"},
    ]
    assert repo.guardar_movimientos(c["id"], p["id"], movs) == 2
    pagina = repo.movimientos(c["id"])
    assert pagina["total"] == 2
    assert pagina["suma_debito"] == pagina["suma_credito"] == "1423500.10"


def test_movimientos_se_reemplazan_al_recalcular(base_limpia):
    c = _cliente()
    p = repo.guardar_resultado(c["id"], _resultado("2025-01-01", "2025-01-31"))
    repo.guardar_movimientos(c["id"], p["id"], [{"cuenta": "1105", "debito": "100"}])
    repo.guardar_movimientos(c["id"], p["id"], [{"cuenta": "1105", "debito": "200"}])
    pagina = repo.movimientos(c["id"])
    assert pagina["total"] == 1 and pagina["suma_debito"] == "200.00"


def test_filtro_por_prefijo_de_cuenta(base_limpia):
    c = _cliente()
    p = repo.guardar_resultado(c["id"], _resultado("2025-01-01", "2025-01-31"))
    repo.guardar_movimientos(c["id"], p["id"], [
        {"cuenta": "110505", "debito": "100"},
        {"cuenta": "110510", "debito": "200"},
        {"cuenta": "510506", "debito": "300"},
    ])
    assert repo.movimientos(c["id"], cuenta="11")["total"] == 2
    assert repo.movimientos(c["id"], cuenta="1105")["total"] == 2
    assert repo.movimientos(c["id"], cuenta="51")["total"] == 1


# ── cierres encadenados ─────────────────────────────────────────────────────
def test_el_cierre_abre_el_periodo_siguiente(base_limpia):
    c = _cliente()
    p = repo.guardar_resultado(c["id"], _resultado("2025-01-01", "2025-01-31"))
    saldos = [
        {"codigo": "110505", "nombre": "Caja general", "debito": "37144505.00", "credito": "0"},
        {"codigo": "3105", "nombre": "Capital", "debito": "0", "credito": "37800000.00"},
    ]
    cierre = repo.cerrar(c["id"], p["id"], saldos)
    assert cierre["cuentas"] == 2
    assert repo.obtener(p["id"])["estado"] == "cerrado"

    previos = repo.saldos_previos(c["id"], date(2025, 2, 1))
    assert previos is not None
    corte, lista = previos
    assert corte == date(2025, 1, 31)
    assert len(lista) == 2
    caja = next(s for s in lista if s.cuenta == "110505")
    assert caja.debito == D("37144505.00")  # exacto, sin pasar por float
    assert "Cierre guardado" in caja.origen


def test_no_se_toman_saldos_de_un_cierre_posterior(base_limpia):
    c = _cliente()
    p = repo.guardar_resultado(c["id"], _resultado("2025-03-01", "2025-03-31"))
    repo.cerrar(c["id"], p["id"], [{"codigo": "1105", "debito": "1", "credito": "0"}])
    # Para enero no puede existir un saldo inicial que venga de marzo.
    assert repo.saldos_previos(c["id"], date(2025, 1, 1)) is None


def test_un_periodo_cerrado_no_se_elimina_por_accidente(base_limpia):
    c = _cliente()
    p = repo.guardar_resultado(c["id"], _resultado("2025-01-01", "2025-01-31"))
    repo.cerrar(c["id"], p["id"], [{"codigo": "1105", "debito": "1", "credito": "0"}])
    with pytest.raises(repo.ErrorPeriodo) as ex:
        repo.eliminar(p["id"])
    assert "cerrado" in str(ex.value).lower()
    # Reabrirlo sí lo permite, y borra el cierre para no dejar saldos huérfanos.
    repo.reabrir(p["id"])
    assert repo.listar_cierres(c["id"]) == []
    repo.eliminar(p["id"])
    assert repo.listar(c["id"]) == []


def test_eliminar_el_cliente_arrastra_su_contabilidad(base_limpia):
    c = _cliente()
    p = repo.guardar_resultado(c["id"], _resultado("2025-01-01", "2025-01-31"))
    repo.guardar_movimientos(c["id"], p["id"], [{"cuenta": "1105", "debito": "100"}])
    informe = repo_clientes.eliminar(c["id"])
    assert informe["periodos_borrados"] == 1
    assert repo.listar(c["id"]) == []


# ── sugerencias ─────────────────────────────────────────────────────────────
def test_cliente_sin_periodos(base_limpia):
    c = _cliente()
    informe = sug.de_cliente(c["id"])
    assert "SIN_PERIODOS" in _codigos(informe)


def test_descuadre_es_critico_y_dice_cuanto(base_limpia):
    c = _cliente()
    repo.guardar_resultado(
        c["id"], _resultado("2025-01-01", "2025-01-31", activo="1000", descuadre="598"))
    s = _buscar(sug.de_cliente(c["id"], date(2025, 2, 1)), "DESCUADRE")
    assert s["severidad"] == "critica"
    assert "598" in s["detalle"]


def test_sin_descuadre_no_hay_sugerencia(base_limpia):
    c = _cliente()
    repo.guardar_resultado(c["id"], _resultado("2025-01-01", "2025-01-31", descuadre="0"))
    assert "DESCUADRE" not in _codigos(sug.de_cliente(c["id"], date(2025, 2, 1)))


def test_periodo_calculado_sin_cerrar(base_limpia):
    c = _cliente()
    repo.guardar_resultado(c["id"], _resultado("2025-01-01", "2025-01-31"))
    assert "SIN_CERRAR" in _codigos(sug.de_cliente(c["id"], date(2025, 2, 1)))


def test_hueco_entre_periodos(base_limpia):
    c = _cliente()
    repo.guardar_resultado(c["id"], _resultado("2025-01-01", "2025-01-31"))
    repo.guardar_resultado(c["id"], _resultado("2025-03-01", "2025-03-31"))
    s = _buscar(sug.de_cliente(c["id"], date(2025, 4, 1)), "HUECOS")
    assert "28" in s["detalle"]  # los 28 días de febrero de 2025


def test_periodos_consecutivos_no_generan_hueco(base_limpia):
    c = _cliente()
    repo.guardar_resultado(c["id"], _resultado("2025-01-01", "2025-01-31"))
    repo.guardar_resultado(c["id"], _resultado("2025-02-01", "2025-02-28"))
    assert "HUECOS" not in _codigos(sug.de_cliente(c["id"], date(2025, 3, 1)))


def test_atraso_respeta_la_periodicidad_pactada(base_limpia):
    c = _cliente(periodicidad="anual")
    repo.guardar_resultado(c["id"], _resultado("2024-01-01", "2024-12-31"))
    # Seis meses después: un cliente anual todavía no está atrasado…
    assert "ATRASADO" not in _codigos(sug.de_cliente(c["id"], date(2025, 6, 1)))
    # …pero uno mensual sí lo estaría.
    repo_clientes.actualizar(c["id"], {"periodicidad": "mensual"})
    assert "ATRASADO" in _codigos(sug.de_cliente(c["id"], date(2025, 6, 1)))


def test_variacion_fuerte_se_avisa_con_los_dos_valores(base_limpia):
    c = _cliente()
    repo.guardar_resultado(c["id"], _resultado("2025-01-01", "2025-01-31", ingresos="1000000"))
    repo.guardar_resultado(c["id"], _resultado("2025-02-01", "2025-02-28", ingresos="3000000"))
    s = _buscar(sug.de_cliente(c["id"], date(2025, 3, 1)), "VARIACION_TOTAL_INGRESOS")
    assert "200" in s["titulo"]            # subieron 200 %
    assert "1.000.000" in s["detalle"] and "3.000.000" in s["detalle"]


def test_variacion_pequena_no_molesta(base_limpia):
    c = _cliente()
    repo.guardar_resultado(c["id"], _resultado("2025-01-01", "2025-01-31", ingresos="1000000"))
    repo.guardar_resultado(c["id"], _resultado("2025-02-01", "2025-02-28", ingresos="1100000"))
    assert "VARIACION_TOTAL_INGRESOS" not in _codigos(sug.de_cliente(c["id"], date(2025, 3, 1)))


def test_racha_de_perdidas(base_limpia):
    c = _cliente()
    for mes, fin in ((1, 31), (2, 28), (3, 31)):
        repo.guardar_resultado(
            c["id"], _resultado(f"2025-{mes:02d}-01", f"2025-{mes:02d}-{fin}", utilidad="-500000"))
    s = _buscar(sug.de_cliente(c["id"], date(2025, 4, 1)), "PERDIDAS_SEGUIDAS")
    assert "1.500.000" in s["detalle"]  # suma exacta de las tres pérdidas


def test_dos_perdidas_no_bastan(base_limpia):
    c = _cliente()
    for mes, fin in ((1, 31), (2, 28)):
        repo.guardar_resultado(
            c["id"], _resultado(f"2025-{mes:02d}-01", f"2025-{mes:02d}-{fin}", utilidad="-500000"))
    assert "PERDIDAS_SEGUIDAS" not in _codigos(sug.de_cliente(c["id"], date(2025, 3, 1)))


def test_causal_de_disolucion_solo_con_capital_registrado(base_limpia):
    # Sin capital en la ficha no se puede evaluar, así que no se opina.
    c = _cliente()
    repo.guardar_resultado(
        c["id"], _resultado("2025-01-01", "2025-01-31", patrimonio="-2204760.72"))
    assert "CAUSAL_DISOLUCION" not in _codigos(sug.de_cliente(c["id"], date(2025, 2, 1)))

    repo_clientes.actualizar(c["id"], {"capital_suscrito": "30000000"})
    s = _buscar(sug.de_cliente(c["id"], date(2025, 2, 1)), "CAUSAL_DISOLUCION")
    assert s["severidad"] == "critica"
    assert "15.000.000" in s["detalle"]  # la mitad del capital


def test_patrimonio_sano_no_dispara_disolucion(base_limpia):
    c = _cliente(capital_suscrito="30000000")
    repo.guardar_resultado(c["id"], _resultado("2025-01-01", "2025-01-31", patrimonio="25000000"))
    assert "CAUSAL_DISOLUCION" not in _codigos(sug.de_cliente(c["id"], date(2025, 2, 1)))


def test_endeudamiento_alto(base_limpia):
    c = _cliente()
    repo.guardar_resultado(
        c["id"], _resultado("2025-01-01", "2025-01-31", activo="1000000", pasivo="900000"))
    s = _buscar(sug.de_cliente(c["id"], date(2025, 2, 1)), "ENDEUDAMIENTO")
    assert "90" in s["titulo"]


def test_capital_de_socios_por_pagar(base_limpia):
    c = _cliente()
    repo_clientes.guardar_socios(c["id"], [
        {"nombre": "ADRIANA DURAN", "comprometido": "7500000", "pagado": "7500000"},
        {"nombre": "JULIO MONTOYA", "comprometido": "7500000", "pagado": "0"},
    ])
    s = _buscar(sug.de_cliente(c["id"]), "CAPITAL_POR_PAGAR")
    assert "7.500.000" in s["detalle"]
    assert len(s["dato"]["socios"]) == 1


def test_ficha_incompleta_enumera_lo_que_falta(base_limpia):
    c = _cliente()
    s = _buscar(sug.de_cliente(c["id"]), "FICHA_INCOMPLETA")
    assert "municipio" in s["detalle"]
    repo_clientes.actualizar(c["id"], {
        "direccion": "Calle 8 No 9-86", "municipio": "Guacarí", "ciiu": "4773",
        "rep_legal": "ADRIANA DURAN", "email": "fanant2024@gmail.com",
    })
    assert "FICHA_INCOMPLETA" not in _codigos(sug.de_cliente(c["id"]))


def test_turno_dian_es_informativo_no_una_fecha_inventada(base_limpia):
    c = _cliente()
    s = _buscar(sug.de_cliente(c["id"]), "TURNO_DIAN")
    assert s["severidad"] == "informativa"
    assert s["dato"]["turno"] == 8
    # No debe afirmar una fecha de vencimiento: las fija un decreto cada año.
    assert "decreto" in s["detalle"].lower()


def test_sugerencias_ordenadas_por_gravedad(base_limpia):
    c = _cliente(capital_suscrito="30000000")
    repo.guardar_resultado(
        c["id"], _resultado("2025-01-01", "2025-01-31", patrimonio="-100", descuadre="598"))
    informe = sug.de_cliente(c["id"], date(2025, 2, 1))
    orden = [sug.ORDEN_SEVERIDAD[s["severidad"]] for s in informe["sugerencias"]]
    assert orden == sorted(orden)
    assert informe["sugerencias"][0]["severidad"] == "critica"


def test_cartera_pone_primero_lo_critico(base_limpia):
    tranquilo = repo_clientes.crear({
        "nit": "800197268", "razon_social": "AL DIA SAS", "direccion": "x", "municipio": "Buga",
        "ciiu": "4773", "rep_legal": "y", "email": "z@z.co",
    })
    repo.guardar_resultado(tranquilo["id"], _resultado("2026-09-01", "2026-09-30"))
    repo.cerrar(tranquilo["id"], repo.listar(tranquilo["id"])[0]["id"],
                [{"codigo": "1105", "debito": "1", "credito": "0"}])

    problematico = _cliente(capital_suscrito="30000000")
    repo.guardar_resultado(
        problematico["id"],
        _resultado("2025-01-01", "2025-01-31", patrimonio="-2204760.72", descuadre="598"))

    cartera = sug.de_cartera(date(2026, 10, 6))
    assert cartera["clientes"][0]["cliente_id"] == problematico["id"]
    assert cartera["criticas"] >= 1


# ── regresión: el dinero no se compara dentro del SQL ───────────────────────
def test_el_conteo_de_descuadrados_no_se_confunde_con_el_formato(base_limpia):
    """Regresión de un bug real.

    `resumen_global` contaba los periodos descuadrados con un
    `where descuadre != 0`. En SQLite los importes son TEXTO, así que esa
    comparación es lexicográfica: un periodo con descuadre "0.00" se contaba
    como descuadrado porque el texto no coincidía con "0". Ahora se consulta la
    columna booleana `cuadra`, que se escribe explícitamente.
    """
    c = _cliente()
    repo.guardar_resultado(c["id"], _resultado("2025-01-01", "2025-01-31", descuadre="0"))
    repo.guardar_resultado(c["id"], _resultado("2025-02-01", "2025-02-28", descuadre="0.00"))
    repo.guardar_resultado(c["id"], _resultado("2025-03-01", "2025-03-31", descuadre="0.000"))

    assert repo.resumen_global()["descuadrados"] == 0, "cuadrados contados como descuadrados"
    for p in repo.listar(c["id"]):
        assert p["cuadra"] is True

    # Y uno de verdad descuadrado sí se cuenta.
    repo.guardar_resultado(c["id"], _resultado("2025-04-01", "2025-04-30", descuadre="598"))
    assert repo.resumen_global()["descuadrados"] == 1
    abril = next(p for p in repo.listar(c["id"]) if p["desde"] == "2025-04-01")
    assert abril["cuadra"] is False


def test_un_descuadre_negativo_tambien_se_detecta(base_limpia):
    """Lexicográficamente "-598" < "0", así que un descuadre negativo era otro
    caso donde la comparación en SQL podía fallar."""
    c = _cliente()
    repo.guardar_resultado(c["id"], _resultado("2025-01-01", "2025-01-31", descuadre="-598"))
    assert repo.resumen_global()["descuadrados"] == 1
    assert repo.listar(c["id"])[0]["cuadra"] is False


def test_un_centavo_de_descuadre_ya_cuenta(base_limpia):
    """En contabilidad un centavo de diferencia es un error, no un redondeo."""
    c = _cliente()
    repo.guardar_resultado(c["id"], _resultado("2025-01-01", "2025-01-31", descuadre="0.01"))
    assert repo.resumen_global()["descuadrados"] == 1
