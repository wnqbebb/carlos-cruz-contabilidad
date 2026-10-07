"""Kardex por producto: promedio ponderado (defecto) o PEPS, con control de lotes y vencimientos."""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from ..modelos import Alerta, ConteoFisico, MovInventario
from ..utils.numeros import CERO, redondear

ENTRADAS = {"inventario_inicial", "compra", "devolucion_venta"}
SALIDAS = {"venta", "devolucion_compra"}

NOMBRE_TIPO = {
    "inventario_inicial": "Inventario inicial", "compra": "Compra", "venta": "Venta",
    "devolucion_compra": "Devolución en compra", "devolucion_venta": "Devolución en venta", "ajuste": "Ajuste",
}


@dataclass
class FilaKardex:
    fecha: date | None
    documento: str
    tipo: str
    lote: str
    ent_cant: Decimal | None = None
    ent_cu: Decimal | None = None
    ent_total: Decimal | None = None
    sal_cant: Decimal | None = None
    sal_cu: Decimal | None = None
    sal_total: Decimal | None = None
    saldo_cant: Decimal = CERO
    saldo_cu: Decimal = CERO
    saldo_total: Decimal = CERO


@dataclass
class ProductoKardex:
    codigo: str
    descripcion: str = ""
    laboratorio: str = ""
    filas: list[FilaKardex] = field(default_factory=list)
    saldo_cant: Decimal = CERO
    saldo_total: Decimal = CERO
    inventario_inicial: Decimal = CERO
    compras: Decimal = CERO
    devoluciones_compra: Decimal = CERO
    costo_ventas: Decimal = CERO
    unidades_vendidas: Decimal = CERO
    ventas_valor: Decimal = CERO
    lotes: dict[str, dict] = field(default_factory=dict)

    @property
    def costo_promedio(self) -> Decimal:
        return redondear(self.saldo_total / self.saldo_cant, 2) if self.saldo_cant else CERO


def _clasificar(m: MovInventario) -> str:
    if m.tipo == "ajuste":
        return "entrada" if m.cantidad >= 0 else "salida"
    return "entrada" if m.tipo in ENTRADAS else "salida"


def calcular(movs: list[MovInventario], metodo: str = "promedio") -> tuple[dict[str, ProductoKardex], list[Alerta]]:
    alertas: list[Alerta] = []
    por_producto: dict[str, list[tuple[int, MovInventario]]] = defaultdict(list)
    for i, m in enumerate(movs):
        por_producto[m.codigo].append((i, m))

    resultado: dict[str, ProductoKardex] = {}
    for codigo, lista in por_producto.items():
        lista.sort(key=lambda t: (t[1].fecha or date.min, t[0]))
        prod = ProductoKardex(codigo)
        capas: list[list[Decimal]] = []  # PEPS: [cantidad, costo unitario]
        ultimo_cu_salida = CERO
        for _, m in lista:
            prod.descripcion = prod.descripcion or m.descripcion
            prod.laboratorio = prod.laboratorio or m.laboratorio
            cant = abs(m.cantidad)
            f = FilaKardex(m.fecha, m.documento, m.tipo, m.lote)
            promedio = (prod.saldo_total / prod.saldo_cant) if prod.saldo_cant > 0 else CERO
            if _clasificar(m) == "entrada":
                cu = m.costo_unitario
                if cu is None:
                    cu = ultimo_cu_salida if m.tipo == "devolucion_venta" and ultimo_cu_salida else promedio
                    if not cu:
                        alertas.append(Alerta("INV", "advertencia", f"Entrada sin costo unitario ({codigo}, {m.documento})", origen=m.origen))
                total = redondear(cant * cu, 2)
                prod.saldo_cant += cant
                prod.saldo_total += total
                capas.append([cant, cu])
                f.ent_cant, f.ent_cu, f.ent_total = cant, cu, total
                if m.tipo == "inventario_inicial":
                    prod.inventario_inicial += total
                elif m.tipo == "compra":
                    prod.compras += total
                elif m.tipo == "devolucion_venta":
                    prod.costo_ventas -= total
                    prod.unidades_vendidas -= cant
                lote = prod.lotes.setdefault(m.lote, {"cantidad": CERO, "vencimiento": m.vencimiento})
                lote["cantidad"] += cant
                if m.vencimiento:
                    lote["vencimiento"] = m.vencimiento
            else:
                if cant > prod.saldo_cant:
                    alertas.append(Alerta(
                        "INV-NEG", "error",
                        f"Inventario negativo: {codigo} {prod.descripcion} — salida de {cant} con saldo {prod.saldo_cant}",
                        origen=m.origen))
                if metodo == "peps":
                    total, pendiente = CERO, cant
                    while pendiente > 0 and capas:
                        tomar = min(pendiente, capas[0][0])
                        total += tomar * capas[0][1]
                        capas[0][0] -= tomar
                        pendiente -= tomar
                        if capas[0][0] == 0:
                            capas.pop(0)
                    if pendiente > 0:
                        total += pendiente * (ultimo_cu_salida or promedio)
                    total = redondear(total, 2)
                    cu = total / cant if cant else CERO
                else:
                    cu = m.costo_unitario if (m.tipo == "devolucion_compra" and m.costo_unitario) else promedio
                    total = redondear(cant * cu, 2)
                prod.saldo_cant -= cant
                prod.saldo_total -= total
                if prod.saldo_cant == 0 and prod.saldo_total != 0:
                    total += prod.saldo_total
                    prod.saldo_total = CERO
                ultimo_cu_salida = cu
                f.sal_cant, f.sal_cu, f.sal_total = cant, redondear(cu, 2), total
                if m.tipo == "venta":
                    prod.costo_ventas += total
                    prod.unidades_vendidas += cant
                    if m.precio_venta:
                        prod.ventas_valor += cant * m.precio_venta
                elif m.tipo == "devolucion_compra":
                    prod.devoluciones_compra += total
                _descontar_lote(prod, m.lote, cant)
            f.saldo_cant, f.saldo_total = prod.saldo_cant, prod.saldo_total
            f.saldo_cu = prod.costo_promedio
            prod.filas.append(f)
        resultado[codigo] = prod
    return dict(sorted(resultado.items())), alertas


def _descontar_lote(prod: ProductoKardex, lote: str, cant: Decimal) -> None:
    if lote and lote in prod.lotes:
        prod.lotes[lote]["cantidad"] -= cant
        return
    pendiente = cant
    orden = sorted(prod.lotes.items(), key=lambda kv: (kv[1]["vencimiento"] or date.max))
    for _, datos in orden:
        if pendiente <= 0:
            break
        tomar = min(pendiente, max(datos["cantidad"], CERO))
        datos["cantidad"] -= tomar
        pendiente -= tomar


def vencimientos(productos: dict[str, ProductoKardex], corte: date, alertas_dias=(30, 60, 90)) -> list[dict]:
    filas = []
    for p in productos.values():
        for lote, datos in p.lotes.items():
            if datos["cantidad"] <= 0 or not datos["vencimiento"]:
                continue
            dias = (datos["vencimiento"] - corte).days
            if dias < 0:
                estado = "Vencido"
            else:
                limite = next((d for d in alertas_dias if dias <= d), None)
                estado = f"Vence en ≤ {limite} días" if limite else "Vigente"
            filas.append({
                "codigo": p.codigo, "descripcion": p.descripcion, "laboratorio": p.laboratorio, "lote": lote or "(sin lote)",
                "vencimiento": datos["vencimiento"], "dias": dias, "cantidad": datos["cantidad"],
                "valor": redondear(datos["cantidad"] * p.costo_promedio, 2), "estado": estado,
            })
    return sorted(filas, key=lambda f: f["dias"])


def comparar_fisico(productos: dict[str, ProductoKardex], conteos: list[ConteoFisico]) -> list[dict]:
    filas = []
    contados = defaultdict(lambda: CERO)
    for c in conteos:
        contados[c.codigo] += c.cantidad
    for codigo, cantidad in contados.items():
        p = productos.get(codigo)
        saldo = p.saldo_cant if p else CERO
        cp = p.costo_promedio if p else CERO
        dif = cantidad - saldo
        filas.append({
            "codigo": codigo, "descripcion": p.descripcion if p else "(no existe en kardex)", "kardex": saldo,
            "fisico": cantidad, "diferencia": dif, "costo_promedio": cp, "valor": redondear(dif * cp, 2),
            "estado": "Sobrante" if dif > 0 else ("Faltante" if dif < 0 else "OK"),
        })
    return filas
