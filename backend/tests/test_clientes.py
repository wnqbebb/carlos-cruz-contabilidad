"""Directorio de clientes: validación, búsqueda, paginación e importación masiva."""
from __future__ import annotations

import csv
import io

import pytest

from app.importadores import clientes_excel
from app.repositorio import clientes as repo


def _nuevo(nit="900100158", razon="DROGUERIA EJEMPLO SAS", **extra) -> dict:
    return {"nit": nit, "razon_social": razon, **extra}


# ── validación de la ficha ──────────────────────────────────────────────────
def test_crear_calcula_el_digito_de_verificacion(base_limpia):
    c = repo.crear(_nuevo())
    assert c["nit"] == "900100158"
    assert c["dv"] == "9"
    assert c["nit_formateado"] == "900.100.158-9"


def test_nit_duplicado_se_rechaza_con_el_nombre_del_otro(base_limpia):
    repo.crear(_nuevo(razon="PRIMERO SAS"))
    with pytest.raises(repo.ErrorCliente) as ex:
        repo.crear(_nuevo(razon="SEGUNDO SAS"))
    assert "PRIMERO SAS" in str(ex.value)


def test_dv_que_no_corresponde_se_rechaza(base_limpia):
    with pytest.raises(repo.ErrorCliente) as ex:
        repo.crear(_nuevo(dv="3"))
    assert "9" in str(ex.value)


def test_nit_y_razon_social_son_obligatorios(base_limpia):
    with pytest.raises(repo.ErrorCliente):
        repo.crear({"razon_social": "SIN NIT SAS"})
    with pytest.raises(repo.ErrorCliente):
        repo.crear({"nit": "900100158"})


def test_importes_se_devuelven_como_texto_exacto(base_limpia):
    c = repo.crear(_nuevo(honorarios_mes="300000", capital_suscrito="30000000.50"))
    assert c["honorarios_mes"] == "300000.00"
    assert c["capital_suscrito"] == "30000000.50"
    assert isinstance(c["honorarios_mes"], str)


# ── búsqueda ────────────────────────────────────────────────────────────────
def test_busqueda_ignora_tildes_y_mayusculas(base_limpia):
    repo.crear(_nuevo(razon="FARMACIA ANTARES", municipio="Guacarí"))
    for texto in ("antares", "ANTARES", "guacari", "Guacarí", "farmacia antares"):
        assert repo.listar(q=texto)["total"] == 1, f"falló con «{texto}»"


def test_busqueda_por_nit_parcial(base_limpia):
    repo.crear(_nuevo())
    assert repo.listar(q="900100")["total"] == 1
    assert repo.listar(q="900.100.158")["total"] == 1


def test_busqueda_exige_todas_las_palabras(base_limpia):
    repo.crear(_nuevo(razon="FARMACIA ANTARES", municipio="Guacarí"))
    repo.crear(_nuevo(nit="800197268", razon="DROGUERIA ANTARES", municipio="Buga"))
    assert repo.listar(q="antares")["total"] == 2
    assert repo.listar(q="antares guacari")["total"] == 1


def test_paginacion(base_limpia):
    for i in range(120):
        repo.crear({"nit": f"9000000{i:03d}", "razon_social": f"CLIENTE {i:03d} SAS"})
    p1 = repo.listar(pagina=1, por_pagina=50)
    assert p1["total"] == 120 and p1["paginas"] == 3 and len(p1["clientes"]) == 50
    p3 = repo.listar(pagina=3, por_pagina=50)
    assert len(p3["clientes"]) == 20
    # Sin solapamiento entre páginas
    assert not {c["id"] for c in p1["clientes"]} & {c["id"] for c in p3["clientes"]}


def test_archivar_saca_de_la_lista_pero_conserva(base_limpia):
    c = repo.crear(_nuevo())
    repo.archivar(c["id"])
    assert repo.listar(estado="activo")["total"] == 0
    assert repo.listar(estado="archivado")["total"] == 1
    assert repo.listar(estado="")["total"] == 1
    repo.archivar(c["id"], archivado=False)
    assert repo.listar(estado="activo")["total"] == 1


def test_socios_se_reemplazan_no_se_acumulan(base_limpia):
    c = repo.crear(_nuevo())
    repo.guardar_socios(c["id"], [{"nombre": "A", "comprometido": "100"}, {"nombre": "B"}])
    assert len(repo.obtener(c["id"])["socios"]) == 2
    repo.guardar_socios(c["id"], [{"nombre": "C"}])
    socios = repo.obtener(c["id"])["socios"]
    assert len(socios) == 1 and socios[0]["nombre"] == "C"


# ── importación masiva ──────────────────────────────────────────────────────
def _csv(filas: list[list[str]]) -> bytes:
    salida = io.StringIO()
    csv.writer(salida, delimiter=";", lineterminator="\n").writerows(filas)
    return salida.getvalue().encode("utf-8")


def test_importa_reconociendo_encabezados_en_otro_orden(base_limpia):
    datos = _csv([
        ["MUNICIPIO", "NOMBRE", "NIT", "HONORARIOS"],
        ["Guacarí", "DROGUERIA EJEMPLO SAS", "900100158", "300000"],
        ["Buga", "DROGUERIA BUGA SAS", "800197268", "250000"],
    ])
    informe = clientes_excel.importar(datos, "clientes.csv")
    assert informe["insertados"] == 2
    assert informe["rechazados"] == 0
    assert repo.listar()["total"] == 2
    assert repo.por_nit("900100158")["municipio"] == "Guacarí"


def test_simulacro_no_escribe_nada(base_limpia):
    datos = _csv([["NIT", "RAZON SOCIAL"], ["900100158", "DROGUERIA EJEMPLO SAS"]])
    informe = clientes_excel.importar(datos, "c.csv", solo_revisar=True)
    assert informe["insertados"] == 1
    assert informe["solo_revisar"] is True
    assert repo.listar()["total"] == 0, "el simulacro no debe guardar"


def test_nit_repetido_dentro_del_archivo_se_rechaza_una_vez(base_limpia):
    datos = _csv([
        ["NIT", "RAZON SOCIAL"],
        ["900100158", "PRIMERA VEZ SAS"],
        ["900.100.158-9", "SEGUNDA VEZ SAS"],
    ])
    informe = clientes_excel.importar(datos, "c.csv")
    assert informe["insertados"] == 1
    assert informe["rechazados"] == 1
    assert "repetido" in informe["rechazos"][0]["motivo"].lower()
    assert informe["rechazos"][0]["fila"] == 3


def test_fila_invalida_no_tumba_el_resto(base_limpia):
    datos = _csv([
        ["NIT", "RAZON SOCIAL"],
        ["900100158", "BUENA SAS"],
        ["12", "NIT MUY CORTO SAS"],
        ["", "SIN NIT SAS"],
        ["800197268", "OTRA BUENA SAS"],
    ])
    informe = clientes_excel.importar(datos, "c.csv")
    assert informe["insertados"] == 2
    assert informe["rechazados"] == 2
    # El informe dice en qué fila del Excel está cada problema.
    assert sorted(r["fila"] for r in informe["rechazos"]) == [3, 4]


def test_actualiza_los_existentes_cuando_se_pide(base_limpia):
    repo.crear(_nuevo(razon="NOMBRE VIEJO SAS", municipio="Palmira"))
    datos = _csv([["NIT", "RAZON SOCIAL", "MUNICIPIO"], ["900100158", "NOMBRE NUEVO SAS", "Guacarí"]])
    informe = clientes_excel.importar(datos, "c.csv", actualizar_existentes=True)
    assert informe["actualizados"] == 1 and informe["insertados"] == 0
    c = repo.por_nit("900100158")
    assert c["razon_social"] == "NOMBRE NUEVO SAS" and c["municipio"] == "Guacarí"


def test_no_actualiza_si_no_se_pide(base_limpia):
    repo.crear(_nuevo(razon="NOMBRE VIEJO SAS"))
    datos = _csv([["NIT", "RAZON SOCIAL"], ["900100158", "NOMBRE NUEVO SAS"]])
    informe = clientes_excel.importar(datos, "c.csv", actualizar_existentes=False)
    assert informe["actualizados"] == 0 and informe["rechazados"] == 1
    assert repo.por_nit("900100158")["razon_social"] == "NOMBRE VIEJO SAS"


def test_sin_columnas_obligatorias_explica_que_falta(base_limpia):
    datos = _csv([["TELEFONO", "CIUDAD"], ["3001234567", "Cali"]])
    informe = clientes_excel.importar(datos, "c.csv")
    assert informe["insertados"] == 0
    assert "NIT" in informe["mensaje"] and "RAZÓN SOCIAL" in informe["mensaje"]


def test_traduce_valores_escritos_a_mano(base_limpia):
    datos = _csv([
        ["NIT", "RAZON SOCIAL", "TIPO PERSONA", "REGIMEN", "PERIODICIDAD", "ESTADO", "ETIQUETAS"],
        ["900100158", "EJEMPLO SAS", "Jurídica", "Responsable de IVA", "Mensual", "Activo", "Farmacia;Valle"],
        ["1000000004", "PERSONA EJEMPLO", "Natural", "No responsable", "Anual", "Inactivo", "Persona natural"],
    ])
    informe = clientes_excel.importar(datos, "c.csv")
    assert informe["insertados"] == 2
    a = repo.por_nit("900100158")
    assert a["tipo_persona"] == "juridica" and a["regimen"] == "responsable_iva"
    assert a["periodicidad"] == "mensual" and a["estado"] == "activo"
    assert set(a["etiquetas"]) == {"Farmacia", "Valle"}
    b = repo.por_nit("1000000004")
    assert b["tipo_persona"] == "natural" and b["estado"] == "inactivo"


def test_volumen_de_mil_filas(base_limpia):
    filas = [["NIT", "RAZON SOCIAL", "HONORARIOS"]]
    filas += [[f"9{i:08d}", f"CLIENTE {i} SAS", str(100000 + i)] for i in range(1000)]
    informe = clientes_excel.importar(_csv(filas), "grande.csv")
    assert informe["insertados"] == 1000
    assert informe["rechazados"] == 0
    assert repo.contar()["total"] == 1000
    # La respuesta no puede traer las mil filas: se recorta la muestra.
    assert len(informe["muestra_insertados"]) == 50


def test_plantilla_de_ejemplo_se_reimporta_sola(base_limpia):
    """La plantilla que se entrega al contador tiene que pasar su propio importador."""
    informe = clientes_excel.importar(clientes_excel.plantilla_csv(), "plantilla.csv")
    assert informe["rechazados"] == 0, informe["rechazos"]
    assert informe["insertados"] == 2
