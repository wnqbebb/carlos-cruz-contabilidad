"""Formato "cuenta T": cuentas en horizontal, cada una con columnas Debe | Haber."""
from __future__ import annotations

from collections import defaultdict
from decimal import Decimal

from ..contabilidad.puc import Mapeador
from ..modelos import Alerta, Movimiento, Paquete
from ..utils.numeros import CERO, D, años_en_texto, es_numero, pesos
from .base import Deteccion
from .lector import Hoja

PALABRAS_FIN = ("BALANCE", "TOTAL", "SUMA", "SALDO")


def detectar(h: Hoja, mapeador: Mapeador) -> int | None:
    for r in range(min(h.nfilas, 15)):
        textos = h.fila_textos(r)
        if len(textos) < 4:
            continue
        cols = [c for c, _ in textos]
        separadas = sum(1 for a, b in zip(cols, cols[1:]) if b - a >= 2)
        conocidas = sum(1 for _, t in textos if mapeador.resolver(t)["estado"] == "exacto")
        if separadas >= len(cols) * 0.6 and conocidas >= max(3, len(textos) // 2):
            return r
    return None


def _titulo(h: Hoja, hasta: int) -> str:
    for r in range(hasta):
        textos = h.fila_textos(r)
        if textos:
            return h.texto(r, textos[0][0])
    return ""


def importar(h: Hoja, r_h: int, id_: str) -> Deteccion:
    inicios = {c: h.texto(r_h, c) for c, _ in h.fila_textos(r_h)}
    columna_cuenta: dict[int, tuple[str, str]] = {}
    for c, nombre in inicios.items():
        columna_cuenta[c] = (nombre, "D")
        if c + 1 not in inicios:
            columna_cuenta[c + 1] = (nombre, "C")
    paquete = Paquete()
    acumulado: dict[int, Decimal] = defaultdict(lambda: CERO)
    movs: list[Movimiento] = []
    fila_sumas = None
    ultima = h.nfilas
    for r in range(r_h + 1, h.nfilas):
        textos = h.fila_textos(r)
        if textos and any(p in t for _, t in textos for p in PALABRAS_FIN):
            ultima = r
            break
        numeros = {c: D(v) for c, v in enumerate(h.valores[r]) if es_numero(v) and D(v) != 0}
        if not numeros:
            continue
        con_saldo = {c for c, v in acumulado.items() if v != 0}
        if len(con_saldo) >= 2 and con_saldo <= set(numeros) and all(numeros[c] == acumulado[c] for c in numeros):
            fila_sumas = r
            ultima = r
            break
        for c, v in numeros.items():
            if c not in columna_cuenta:
                paquete.filas_ignoradas.append({"origen": h.origen(r, c), "motivo": f"Valor {pesos(v)} fuera de las columnas de cuentas"})
                continue
            acumulado[c] += v
            nombre, lado = columna_cuenta[c]
            movs.append(Movimiento(cuenta="", nombre_cuenta=nombre, debito=v if lado == "D" else CERO,
                                   credito=v if lado == "C" else CERO, comprobante=f"CT {h.nombre}",
                                   descripcion=f"Movimiento cuenta T ({nombre})", origen=h.origen(r, c)))
    if ultima < h.nfilas:
        paquete.filas_ignoradas.append({
            "origen": f"{h.archivo} › {h.nombre} › filas {ultima + 1} a {h.nfilas}",
            "motivo": "Sumas, saldos y balance de comprobación del propio archivo: la aplicación los recalcula (no se suman dos veces).",
        })
    paquete.movimientos = movs
    titulo = _titulo(h, r_h)
    if titulo:
        paquete.titulos.append(titulo)
    td = sum((m.debito for m in movs), CERO)
    tc = sum((m.credito for m in movs), CERO)
    if td != tc:
        paquete.alertas.append(Alerta("SUMAS-IGUALES", "error", f"La hoja «{h.nombre}» no cuadra: débitos {pesos(td)} ≠ créditos {pesos(tc)}."))
    resumen = {
        "titulo": titulo, "años_titulo": años_en_texto(titulo), "fila_titulos": r_h + 1, "cuentas": len(inicios),
        "movimientos": len(movs), "total_debito": td, "total_credito": tc,
        "fila_sumas_archivo": fila_sumas + 1 if fila_sumas is not None else None,
    }
    return Deteccion(id_, h.archivo, h.nombre, "cuenta_t", True, "", resumen, paquete)
