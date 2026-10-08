"""Balance de prueba o listado de saldos por cuenta: en Excel, en una tabla de Word o en un PDF (H04).

POR QUÉ EXISTE
Muchos contadores reciben el balance de prueba que imprime el programa contable,
en PDF. Hasta la v2.1 ese PDF se leía pero no entraba a la contabilidad. Ahora
una tabla con códigos PUC y valores se reconoce venga de donde venga.

LO DIFÍCIL, Y CÓMO SE RESUELVE
  · Un balance trae la clase, el grupo, la cuenta y la subcuenta, cada una con
    su total. Sumarlas todas cuenta cuatro veces lo mismo: solo se toman las
    cuentas que no tienen hijas en la lista (las «hojas» del árbol).
  · En un PDF las columnas vacías desaparecen: «1105 Caja 37.144.505» no dice
    si el valor es débito o crédito. Si hay encabezados, mandan ellos; si no,
    un valor solo se toma como saldo final del lado de la naturaleza de la
    cuenta, y con cuatro valores se exige que cuadre la aritmética
    (anterior + débitos − créditos = final). Lo que se interpreta se avisa.
"""
from __future__ import annotations

from decimal import Decimal

from ..contabilidad.puc import puc
from ..modelos import Alerta, Movimiento, Paquete, SaldoInicial
from ..utils.numeros import CERO, D, es_numero, mes_año_en_texto, normalizar, pesos
from .base import Deteccion
from .lector import Hoja

FORMATO = "balance"


def _codigo(v) -> str:
    if v is None:
        return ""
    if isinstance(v, float) and v.is_integer():
        v = int(v)
    t = str(v).strip().replace(" ", "")
    return t if t.isdigit() and 1 <= len(t) <= 10 else ""


def _es_cuenta(v) -> bool:
    """Código PUC de 4 a 8 dígitos cuya cuenta de 4 dígitos existe.

    Un teléfono (3168318444) o una cédula empiezan por un dígito de clase y
    pasarían por un código si solo se mirara el primer dígito.
    """
    t = _codigo(v)
    return 4 <= len(t) <= 8 and t[:4] in puc().cuentas


def _columna_codigos(h: Hoja) -> tuple[int, int] | None:
    """(columna de códigos, primera fila con código) si la hoja es un listado de cuentas."""
    alto = min(h.nfilas, 400)
    for c in range(min(h.ncols, 4)):
        filas = [r for r in range(alto) if h.v(r, c) is not None]
        codigos = [r for r in filas if _es_cuenta(h.v(r, c))]
        if len(codigos) >= 3 and len(codigos) >= len(filas) * 0.5:
            return c, codigos[0]
    return None


def detectar(h: Hoja) -> dict | None:
    pos = _columna_codigos(h)
    if not pos:
        return None
    c_cod, r_ini = pos
    # Columnas numéricas a la derecha del código.
    numericas = []
    for c in range(c_cod + 1, h.ncols):
        vals = [h.v(r, c) for r in range(r_ini, min(h.nfilas, r_ini + 200)) if _codigo(h.v(r, c_cod))]
        if sum(1 for v in vals if v is not None and es_numero(v)) >= 2:
            numericas.append(c)
    if not numericas:
        return None
    c_nombre = next((c for c in range(c_cod + 1, h.ncols) if c not in numericas and any(
        isinstance(h.v(r, c), str) and not es_numero(h.v(r, c)) for r in range(r_ini, min(h.nfilas, r_ini + 30)))), None)
    if c_nombre is None:
        return None          # sin el nombre de la cuenta, no es un balance sino una lista de números
    # Encabezados: hasta dos filas encima de la primera cuenta («SALDO ANTERIOR» / «DÉBITO»).
    rotulos = {}
    for c in numericas:
        partes = [normalizar(h.v(r, c)) for r in range(max(0, r_ini - 3), r_ini) if isinstance(h.v(r, c), str)]
        rotulos[c] = " ".join(p for p in partes if p)
    return {"codigo": c_cod, "nombre": c_nombre, "inicio": r_ini, "numericas": numericas, "rotulos": rotulos,
            "sin_encabezado": bool(getattr(h, "sin_encabezado", False)) or not any(rotulos.values())}


def _rol(rotulo: str) -> str:
    t = f" {rotulo} "
    lado = "d" if any(x in t for x in (" DEBITO", " DEBE ", " DB ", " DEUDOR")) else \
        ("c" if any(x in t for x in (" CREDITO", " HABER ", " CR ", " ACREEDOR")) else "")
    if any(x in t for x in ("ANTERIOR", "INICIAL", "APERTURA")):
        return f"ini_{lado}" if lado else "ini"
    if any(x in t for x in ("FINAL", "NUEVO SALDO", "ACTUAL", "SALDO A ")):
        return f"fin_{lado}" if lado else "fin"
    if "SALDO" in t:
        return f"fin_{lado}" if lado else "fin"
    if any(x in t for x in ("MOVIMIENTO", "MOVIMIENTOS")) and lado:
        return f"mov_{lado}"
    if lado:
        return f"mov_{lado}"
    return ""


def importar(h: Hoja, pos: dict, id_: str) -> Deteccion:
    p = puc()
    paquete = Paquete()
    filas = []
    for r in range(pos["inicio"], h.nfilas):
        codigo = _codigo(h.v(r, pos["codigo"]))
        if not _es_cuenta(codigo) or not p.valido(codigo):
            continue
        nombre = str(h.v(r, pos["nombre"]) or "").strip() if pos["nombre"] is not None else ""
        valores = {c: h.v(r, c) for c in pos["numericas"] if h.v(r, c) is not None and es_numero(h.v(r, c))}
        filas.append((r, codigo, nombre, valores))

    # Solo las cuentas sin hijas: las demás son subtotales del propio balance.
    codigos = {f[1] for f in filas}
    padres = {c for c in codigos if any(o != c and o.startswith(c) for o in codigos)}
    hojas = [f for f in filas if f[1] not in padres]

    roles = {c: _rol(pos["rotulos"].get(c, "")) for c in pos["numericas"]}
    usar_rotulos = not pos["sin_encabezado"] and any(roles.values())
    interpretadas = 0
    for r, codigo, nombre, valores in hojas:
        nat = p.naturaleza(codigo)
        origen = h.origen(r)
        ini = mov_d = mov_c = fin = None
        if usar_rotulos:
            acum: dict[str, Decimal] = {}
            for c, v in valores.items():
                rol = roles.get(c) or ""
                if rol:
                    acum[rol] = acum.get(rol, CERO) + D(v)
            if "ini_d" in acum or "ini_c" in acum:
                ini = acum.get("ini_d", CERO) - acum.get("ini_c", CERO)
            elif "ini" in acum:
                ini = acum["ini"] if nat == "D" else -acum["ini"]
            mov_d, mov_c = acum.get("mov_d"), acum.get("mov_c")
            if "fin_d" in acum or "fin_c" in acum:
                fin = acum.get("fin_d", CERO) - acum.get("fin_c", CERO)
            elif "fin" in acum:
                fin = acum["fin"] if nat == "D" else -acum["fin"]
        else:
            nums = [D(v) for _, v in sorted(valores.items())]
            signo = 1 if nat == "D" else -1
            # Cuatro valores: anterior, débitos, créditos y final, en positivo del
            # lado de la naturaleza. Solo se acepta si la aritmética cuadra.
            if len(nums) == 4 and nums[0] + signo * (nums[1] - nums[2]) == nums[3]:
                ini = nums[0] * signo
                mov_d, mov_c = nums[1], nums[2]
                fin = ini + mov_d - mov_c
            elif nums:
                fin = nums[-1] * signo
                if len(nums) > 1:
                    interpretadas += 1
        if ini is not None and (mov_d is not None or mov_c is not None):
            if ini:
                paquete.saldos_iniciales.append(SaldoInicial(codigo, ini if ini > 0 else CERO, -ini if ini < 0 else CERO,
                                                             nombre, origen))
            if mov_d or mov_c:
                paquete.movimientos.append(Movimiento(codigo, mov_d or CERO, mov_c or CERO, None, f"BAL {h.nombre}", "balance",
                                                      nombre, descripcion="Movimiento del periodo según balance",
                                                      origen=origen))
        elif fin is not None or ini is not None:
            neto = fin if fin is not None else ini
            if neto:
                paquete.movimientos.append(Movimiento(codigo, neto if neto > 0 else CERO, -neto if neto < 0 else CERO, None,
                                                      f"BAL {h.nombre}", "balance", nombre,
                                                      descripcion="Saldo según el balance recibido", origen=origen))

    td = sum((m.debito for m in paquete.movimientos), CERO) + sum((s.debito for s in paquete.saldos_iniciales), CERO)
    tc = sum((m.credito for m in paquete.movimientos), CERO) + sum((s.credito for s in paquete.saldos_iniciales), CERO)
    if padres:
        paquete.filas_ignoradas.append({"origen": f"{h.archivo} › {h.nombre}",
                                        "motivo": f"{len(padres)} cuenta(s) de nivel superior (clase, grupo o cuenta con "
                                                  "subcuentas) se tomaron como subtotales y no se sumaron."})
    if interpretadas:
        paquete.alertas.append(Alerta(
            "BAL-COLUMNAS", "advertencia",
            f"«{h.nombre}»: {interpretadas} fila(s) traen varios valores sin encabezado que diga cuál es cuál; se tomó el "
            "último como saldo final, del lado de la naturaleza de la cuenta. Revise el balance de prueba."))
    if td != tc:
        paquete.alertas.append(Alerta("SUMAS-IGUALES", "error",
                                      f"El balance «{h.nombre}» no cuadra: débitos {pesos(td)} ≠ créditos {pesos(tc)}."))
    # Fecha de corte: «BALANCE DE PRUEBA A 31 DE MARZO DE 2026» encima de la tabla o en el texto del PDF.
    titulo = " ".join(h.texto(r, c) for r in range(pos["inicio"]) for c, _ in h.fila_textos(r))
    mes, anio = mes_año_en_texto(f"{titulo} {getattr(h, 'contexto', '')}")
    if titulo:
        paquete.titulos.append(titulo)
    resumen = {"titulo": titulo, "mes": mes, "año": anio,
               "movimientos": len(paquete.movimientos), "saldos_iniciales": len(paquete.saldos_iniciales),
               "cuentas": len(hojas), "total_debito": td, "total_credito": tc, "subtotales_omitidos": len(padres)}
    return Deteccion(id_, h.archivo, h.nombre, FORMATO, bool(paquete.movimientos or paquete.saldos_iniciales),
                     "" if hojas else "Sin cuentas con valores", resumen, paquete)
