"""Nombre del cliente sacado del nombre del archivo, aunque venga mal escrito (A1).

El nombre del archivo es el último recurso para identificar al cliente. La gente
escribe rápido: «CANTABILIDAD», «BALNCE», «ESTDOS FINANSIEROS». Esas palabras
dicen QUÉ es el archivo, no DE QUIÉN es, y hay que quitarlas igual que si
estuvieran bien escritas. Lo que no se puede es comerse el nombre del negocio.
"""
from __future__ import annotations

import pytest

from app.importadores.identidad import nombre_desde_archivo


@pytest.mark.parametrize("archivo, esperado", [
    ("CANTABILIDAD PYME PEDRO GOMEZ.xlsx", "PEDRO GOMEZ"),
    ("contavilidad_mipyme_LUISA_TORO_2026.xlsx", "LUISA TORO"),
    ("BALNCE DE PRUEBA HERNAN DIAZ.xls", "HERNAN DIAZ"),
    ("ESTDOS FINANSIEROS DROGUERIA SAN JOSE 2025.pdf", "DROGUERIA SAN JOSE"),
    ("Contabilidaad Microempresa Rosa Lopez.xlsx", "ROSA LOPEZ"),
    ("REGISTROS AUXILIARES - VENTAZ Y CONPRAS - CARLOS RUIZ.xlsx", "CARLOS RUIZ"),
    ("negocio_EMPRESA_juan_perez_setiembre.xlsx", "JUAN PEREZ"),
    ("INVENTARO FEBERO 2026 TIENDA LA ESQUINA.xlsx", "TIENDA LA ESQUINA"),
    ("CONTABILIDAD-PYMES-final-v2 (copia) ANA MORA.xlsx", "ANA MORA"),
])
def test_quita_las_palabras_de_ruido_aunque_esten_mal_escritas(archivo, esperado):
    assert nombre_desde_archivo(archivo) == esperado


@pytest.mark.parametrize("archivo, esperado", [
    # «COMERCIAL» se parece a «COMERCIO» pero es parte del nombre del negocio.
    ("COMERCIAL EL TRIUNFO.xlsx", "COMERCIAL EL TRIUNFO"),
    # «FINCA» se parece a «FINAL», y es el negocio.
    ("FINCA LA ESPERANZA contabilidad.xlsx", "FINCA LA ESPERANZA"),
    # Palabras cortas no se comparan por parecido: «MARIA» no es «MAYO».
    ("MARIA ELENA ROJAS ventas.xlsx", "MARIA ELENA ROJAS"),
])
def test_no_se_come_el_nombre_del_negocio(archivo, esperado):
    assert nombre_desde_archivo(archivo) == esperado
