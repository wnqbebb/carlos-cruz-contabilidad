"""Más clientes de demostración (rescate §6.1). Todo es FICTICIO y se carga POR LA API, como un usuario.

Contabilidad (cada uno con un formato de entrada distinto y una situación distinta):
  6  RESTAURANTE SAZÓN DEL PACÍFICO S.A.S. (Buenaventura)  Excel de facturas electrónicas de la DIAN
                                                            (ventas con impuesto al consumo, compras con
                                                            IVA). Al día: enero 2025 a septiembre 2026.
  7  DROGUERÍA SAN ROQUE S.A.S. (Cartago)                  Plantilla oficial con kardex de inventario.
                                                            Atrasada: llega hasta mayo de 2026.
  8  TALLER DE MOTOS EL PISTÓN (persona natural, Jamundí) Libro diario en CSV. Agosto de 2026 con un
                                                            descuadre de $ 30.000; septiembre sin cerrar.
Renta (año gravable 2025):
  · Los 6 contribuyentes del caso D (asalariado, independiente, pensionado, rentista, no obligado y
    vencido sin impuesto), con su exógena en Excel y los datos que solo el contador sabe.
  · 2 con fotos sintéticas de la exógena: la Contribuyente A (legible) y el contribuyente F (difícil).

Uso, desde backend/:
    python -m demo.mas_demostracion --url http://localhost:8000 --usuario carlos --clave '…'
Se borran con «Eliminar clientes de demostración» (menú de la cuenta › Sistema).
"""
from __future__ import annotations

import argparse
import csv
import io
import random
import sys
from datetime import date

from openpyxl import Workbook

from app.exportar import plantilla
from demo import dian_ficticio as F
from demo.generar_historicos import ETIQUETA, NOTA, Api, cargar, ficha_base, meses, ultimo_dia

RND = random.Random(2026)




# ── 6 · restaurante: facturas electrónicas de la DIAN ──────────────────────
RESTAURANTE = {"nit": "901411222", "razon": "RESTAURANTE SAZÓN DEL PACÍFICO S.A.S."}


def _facturas_restaurante(a: int, m: int) -> bytes:
    yo = (RESTAURANTE["nit"], RESTAURANTE["razon"])
    filas = []
    fin = ultimo_dia(a, m).day
    temporada = 1.35 if m in (6, 7, 12) else 1.0
    for i in range(1, 26):                      # ventas del mes: consumidor final y empresas
        base = round(RND.randint(380, 980) * 1000 * temporada, -3)
        inc = round(base * 0.08)                # impuesto nacional al consumo de restaurantes (8 %)
        cliente = ("222222222222", "CONSUMIDOR FINAL") if i % 4 else ("900555111", "HOTEL BAHÍA S.A.S.")
        fila = F._fila("Factura electrónica", "RSP", a * 10000 + m * 100 + i, f"{min(i, fin):02d}-{m:02d}-{a}",
                       yo, cliente, total=base + inc, forma="Contado" if i % 4 else "Crédito")
        fila[F.ENCABEZADOS.index("INC")] = inc
        filas.append(fila)
    for i, (prov, iva_tarifa) in enumerate([(("800777123", "PESCADOS DEL PUERTO S.A.S."), 0.0),
                                            (("890444333", "DISTRIBUIDORA DE ABARROTES S.A."), 0.05),
                                            (("860001022", "GAS NATURAL DEL VALLE S.A. E.S.P."), 0.19)]):
        for k in range(1, 4):
            base = RND.randint(900, 2600) * 1000
            iva = round(base * iva_tarifa)
            filas.append(F._fila("Factura electrónica", "C", a * 1000 + m * 10 + k + i * 3, f"{k * 8:02d}-{m:02d}-{a}",
                                 prov, yo, iva=iva, total=base + iva, forma="Crédito", grupo="Recibido"))
    return F.libro(filas)


def restaurante(api: Api) -> str:
    print(RESTAURANTE["razon"])
    cliente_id = None
    for a, m in meses():
        nombre = f"facturas_dian_{a}_{m:02d}.xlsx"
        archivos = [(nombre, _facturas_restaurante(a, m))]
        crear = None if cliente_id else ficha_base(RESTAURANTE["nit"], RESTAURANTE["razon"], municipio="Buenaventura",
                                                   departamento="Valle del Cauca", ciiu="5611", honorarios_mes="900000")
        cliente_id, res = cargar(api, archivos, cliente_id=cliente_id, crear=crear,
                                 periodo=(date(a, m, 1), ultimo_dia(a, m)))
        print(f"  {a}-{m:02d}  ingresos {res['resumen']['ingresos']}")
    return cliente_id


# ── 7 · droguería: plantilla oficial con inventario ───────────────────────
DROGUERIA = {"nit": "901422333", "razon": "DROGUERÍA SAN ROQUE S.A.S."}
PRODUCTOS = [("A01", "Acetaminofén 500 mg x100", 9800, 18500), ("A02", "Ibuprofeno 400 mg x50", 7600, 14900),
             ("A03", "Suero oral x6", 6200, 11800), ("A04", "Vitamina C x30", 12500, 23900)]


def _plantilla_drogueria(a: int, m: int, primero: bool, stock: dict[str, int]) -> bytes:
    hojas = {k: [] for k in ("SALDOS_INICIALES", "MOVIMIENTOS", "INVENTARIO_MOVS", "INVENTARIO_FISICO",
                             "ACTIVOS_FIJOS", "NOMINA", "AJUSTES")}
    fin = ultimo_dia(a, m)
    if primero:
        hojas["SALDOS_INICIALES"] = [["110505", "Caja general", 3000000, None], ["111005", "Bancos", 25000000, None],
                                     ["1435", "Mercancías", 12000000, None], ["3105", "Capital suscrito y pagado", None, 40000000]]
        for cod, desc, costo, _ in PRODUCTOS:
            hojas["INVENTARIO_MOVS"].append([f"{a}-{m:02d}-01", "SI", cod, desc, "LAB DEMO", "L1", "2027-12-31",
                                             "Inventario inicial", 300, costo, None])
            stock[cod] = 300
    compras = 0
    for cod, desc, costo, _ in PRODUCTOS:
        q = RND.randint(120, 220)
        compras += q * costo
        stock[cod] += q
        hojas["INVENTARIO_MOVS"].append([f"{a}-{m:02d}-05", f"FC-{m:02d}", cod, desc, "LAB DEMO", f"L{m}", "2027-12-31",
                                         "Compra", q, costo, None])
    iva_c = round(compras * 0.19)
    hojas["MOVIMIENTOS"] += [
        [f"{a}-{m:02d}-05", f"FC-{m:02d}", "Compra", "1435", "Mercancías", "830100200", "LABORATORIO DEMO S.A.", "Compra del mes", compras, None, None],
        [f"{a}-{m:02d}-05", f"FC-{m:02d}", "Compra", "240810", "IVA descontable", "830100200", "LABORATORIO DEMO S.A.", "IVA compra", iva_c, None, None],
        [f"{a}-{m:02d}-05", f"FC-{m:02d}", "Compra", "220505", "Proveedores", "830100200", "LABORATORIO DEMO S.A.", "A 30 días", None, compras + iva_c, None],
    ]
    ventas = 0
    for cod, desc, _, precio in PRODUCTOS:
        q = min(stock[cod] - 20, RND.randint(130, 230))
        ventas += q * precio
        stock[cod] -= q
        hojas["INVENTARIO_MOVS"].append([f"{a}-{m:02d}-{fin.day}", f"RC-{m:02d}", cod, desc, "", "", None, "Venta", q, None, precio])
    hojas["MOVIMIENTOS"] += [
        [fin.isoformat(), f"RC-{m:02d}", "Venta", "110505", "Caja general", "", "Clientes varios", "Ventas del mes", ventas, None, None],
        [fin.isoformat(), f"RC-{m:02d}", "Venta", "4135", "Comercio", "", "Clientes varios", "Ventas del mes", None, ventas, None],
        [fin.isoformat(), f"CE-{m:02d}", "Egreso", "512010", "Arrendamientos", "", "Arrendador demo", "Arriendo local", 1800000, None, None],
        [fin.isoformat(), f"CE-{m:02d}", "Egreso", "110505", "Caja general", "", "Arrendador demo", "Arriendo local", None, 1800000, None],
    ]
    hojas["INVENTARIO_FISICO"] = [[cod, stock[cod], fin.isoformat()] for cod, *_ in PRODUCTOS]
    datos = {**hojas, "_meta": {"periodo": (date(a, m, 1).isoformat(), fin.isoformat()), "empresa": DROGUERIA["razon"],
                                "nit": DROGUERIA["nit"], "nombre": "", "descripcion": "", "editar": True,
                                "empresa_dict": {"razon_social": DROGUERIA["razon"], "nit": DROGUERIA["nit"],
                                                 "periodo_desde": date(a, m, 1).isoformat(), "periodo_hasta": fin.isoformat()}}}
    return plantilla.construir(datos=datos)


def drogueria(api: Api) -> str:
    print(DROGUERIA["razon"])
    cliente_id, stock = None, {}
    for a, m in meses(hasta=(2026, 5)):                    # atrasada: junio a septiembre sin contabilizar
        archivos = [(f"drogueria_{a}_{m:02d}.xlsx", _plantilla_drogueria(a, m, cliente_id is None, stock))]
        crear = None if cliente_id else ficha_base(DROGUERIA["nit"], DROGUERIA["razon"], municipio="Cartago",
                                                   departamento="Valle del Cauca", ciiu="4773", honorarios_mes="650000")
        cliente_id, res = cargar(api, archivos, cliente_id=cliente_id, crear=crear)
        print(f"  {a}-{m:02d}  utilidad {res['resumen']['utilidad_neta']}")
    return cliente_id


# ── 8 · taller: libro diario en CSV ─────────────────────────────────────
TALLER = {"nit": "1113444555", "razon": "JHON JAIRO RÍOS — TALLER DE MOTOS EL PISTÓN"}


def _diario_taller(a: int, m: int) -> bytes:
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=";")
    w.writerow(["Fecha", "Comprobante", "Cuenta", "Nombre cuenta", "Tercero", "Descripción", "Débito", "Crédito"])
    fin = ultimo_dia(a, m)
    servicios = RND.randint(55, 85) * 100000
    repuestos = RND.randint(20, 40) * 100000
    lineas = [
        (f"{a}-{m:02d}-15", f"RC{m:02d}1", "110505", "Caja", "Clientes varios", "Servicios de mantenimiento", servicios, 0),
        (f"{a}-{m:02d}-15", f"RC{m:02d}1", "4155", "Servicios", "Clientes varios", "Servicios de mantenimiento", 0, servicios),
        (f"{a}-{m:02d}-10", f"CE{m:02d}1", "6135", "Costo repuestos", "Repuestos Moto Sur", "Repuestos usados", repuestos, 0),
        (f"{a}-{m:02d}-10", f"CE{m:02d}1", "110505", "Caja", "Repuestos Moto Sur", "Pago repuestos", 0, repuestos),
        (fin.isoformat(), f"CE{m:02d}2", "512010", "Arriendo", "Arrendador demo", "Arriendo del taller", 950000, 0),
        (fin.isoformat(), f"CE{m:02d}2", "110505", "Caja", "Arrendador demo", "Pago arriendo", 0, 950000),
        (fin.isoformat(), f"CE{m:02d}3", "510506", "Sueldos", "Ayudante del taller", "Sueldo del ayudante", 1423500, 0),
        (fin.isoformat(), f"CE{m:02d}3", "110505", "Caja", "Ayudante del taller", "Pago sueldo", 0, 1423500),
    ]
    if (a, m) == (2026, 8):          # descuadre a propósito: el contador lo ve en la ficha
        lineas.append((fin.isoformat(), f"CE{m:02d}4", "513530", "Energía", "Empresa de energía", "Recibo de luz", 180000, 0))
        lineas.append((fin.isoformat(), f"CE{m:02d}4", "110505", "Caja", "Empresa de energía", "Pago luz", 0, 150000))
    for l in lineas:
        w.writerow(l)
    return buf.getvalue().encode("utf-8-sig")


def taller(api: Api) -> str:
    print(TALLER["razon"])
    cliente_id = None
    for a, m in meses():
        archivos = [(f"taller_diario_{a}_{m:02d}.csv", _diario_taller(a, m))]
        crear = None if cliente_id else ficha_base(TALLER["nit"], TALLER["razon"], tipo_persona="natural",
                                                   municipio="Jamundí", departamento="Valle del Cauca", ciiu="4542",
                                                   honorarios_mes="350000")
        cliente_id, res = cargar(api, archivos, cliente_id=cliente_id, crear=crear,
                                 periodo=(date(a, m, 1), ultimo_dia(a, m)), cerrar=(a, m) < (2026, 8))
        p = res.get("periodo") or {}
        print(f"  {a}-{m:02d}  {'cuadra' if p.get('cuadra') else 'NO CUADRA'}")
    return cliente_id


# ── renta: caso D y fotos sintéticas ───────────────────────────────────────
def _exogena(numero: str, nombre: str, lineas: list[tuple[str, str, int, str]]) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.append([f"Tipo de documento: C.C."])
    ws.append([f"Identificación: {numero}"])
    ws.append([f"Nombres / Razón social: {nombre}"])
    ws.append([])
    ws.append(["Entidad", "Titular", "Detalle", "Valor", "Uso sugerido"])
    for entidad, detalle, valor, uso in lineas:
        ws.append([entidad, nombre, detalle, valor, uso])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


CASO_D = [
    ("10000011", "D1 ASALARIADO CON DEPENDIENTES", [
        ("EMPRESA DEMO S.A.S.", "Pagos por salarios", 120_000_000, "Tope 1: Ingresos brutos | R32"),
        ("EMPRESA DEMO S.A.S.", "Aportes obligatorios a pensión y salud", 10_800_000, "R33"),
        ("EMPRESA DEMO S.A.S.", "Retención en la fuente por salarios", 4_000_000, "R132 Retenciones"),
        ("BANCO DEMO", "Saldo cuentas bancarias (Titular Principal)", 300_000_000, "Tope 2: Patrimonio | R29"),
        ("BANCO DEMO", "Saldo crédito hipotecario", 100_000_000, "R30 Deudas")],
     [{"tipo": "beneficio", "id": "dependientes", "valor": "2"},
      {"tipo": "beneficio", "id": "intereses_vivienda", "valor": "12000000"},
      {"tipo": "beneficio", "id": "medicina_prepagada", "valor": "3000000"}]),
    ("10000012", "D2 INDEPENDIENTE CON HONORARIOS", [
        ("CLIENTE DEMO S.A.S.", "Pagos por honorarios", 150_000_000, "Tope 1: Ingresos brutos | R43"),
        ("CLIENTE DEMO S.A.S.", "Retención en la fuente por honorarios", 16_500_000, "R132 Retenciones"),
        ("BANCO DEMO", "Saldo cuentas bancarias (Titular Principal)", 80_000_000, "Tope 2: Patrimonio | R29")],
     [{"tipo": "agregar", "categoria": "costo_honorarios", "valor": "30000000", "descripcion": "Costos con soporte"},
      {"tipo": "ajuste_casilla", "casilla": 44, "valor": "17100000",
       "nota": "Aportes a pensión y salud como independiente (planillas PILA del año)"},
      {"tipo": "beneficio", "id": "gmf_pagado", "valor": "600000"},
      {"tipo": "beneficio", "id": "dependientes", "valor": "1"}]),
    ("10000013", "D3 PENSIONADO", [
        ("FONDO DE PENSIONES DEMO", "Mesadas pensionales", 60_000_000, "Tope 1: Ingresos brutos | R99"),
        ("BANCO DEMO", "Rendimientos financieros CDT", 5_000_000, "Tope 1: Ingresos brutos | R58"),
        ("BANCO DEMO", "Retención practicada rendimientos", 350_000, "R132 Retenciones")], []),
    ("10000014", "D4 RENTISTA CON DIVIDENDOS", [
        ("INMOBILIARIA DEMO", "Pagos por arrendamientos", 96_000_000, "Tope 1: Ingresos brutos"),
        ("SOCIEDAD DEMO S.A.", "Dividendos y participaciones 2017 y siguientes", 80_000_000, "R107"),
        ("INMOBILIARIA DEMO", "Retención en la fuente por arrendamientos", 7_000_000, "R132 Retenciones"),
        ("CATASTRO", "Avalúo catastral inmueble", 1_200_000_000, "Tope 2: Patrimonio | R29")],
     [{"tipo": "agregar", "categoria": "costo_capital", "valor": "14000000", "descripcion": "Mantenimiento y predial"},
      {"tipo": "beneficio", "id": "gmf_pagado", "valor": "1000000"}]),
    ("10000015", "D5 NO OBLIGADO", [
        ("EMPRESA DEMO S.A.S.", "Pagos por salarios", 40_000_000, "Tope 1: Ingresos brutos | R32"),
        ("BANCO DEMO", "Saldo cuentas bancarias (Titular Principal)", 50_000_000, "Tope 2: Patrimonio | R29")], []),
    ("10000016", "D6 VENCIDO SIN IMPUESTO", [
        ("EMPRESA DEMO S.A.S.", "Pagos por salarios", 75_000_000, "Tope 1: Ingresos brutos | R32"),
        ("EMPRESA DEMO S.A.S.", "Aportes obligatorios a pensión y salud", 6_750_000, "R33")], []),
]


def _contribuyente(api: Api, numero: str, nombre: str) -> str:
    c = api.post("/api/clientes", {"nit": numero, "razon_social": nombre, "tipo_persona": "natural", "demo": True,
                                   "regimen": "no_responsable_iva", "etiquetas": [ETIQUETA, "renta", "solo_renta"],
                                   "notas": NOTA})
    return c["id"]


def _subir_renta(api: Api, cid: str, archivos: list[tuple[str, bytes]]) -> dict:
    files = [("archivos", (n, b)) for n, b in archivos]
    return api._ok(api.c.post(f"/api/renta/{cid}/2025/documentos", files=files))


def renta(api: Api) -> None:
    print("Renta 2025 · caso D")
    for numero, nombre, lineas, cambios in CASO_D:
        cid = _contribuyente(api, numero, nombre)
        _subir_renta(api, cid, [(f"exogena_{numero}.xlsx", _exogena(numero, nombre, lineas))])
        for c in cambios:
            api.post(f"/api/renta/{cid}/2025/cambio", c)
        print(f"  {nombre}")
    print("Renta 2025 · fotos sintéticas")
    from demo import fotos_ficticias as FF

    fotos = FF.archivos()
    cid = _contribuyente(api, "10000001", "CONTRIBUYENTE A")
    _subir_renta(api, cid, [("contribuyente_a_foto.jpg", fotos["contribuyente_a_foto.jpg"])])
    cid = _contribuyente(api, "10000006", "CONTRIBUYENTE F FICTICIO")
    _subir_renta(api, cid, [(n, fotos[n]) for n in ("contribuyente_f_pagina_1.jpg", "contribuyente_f_pagina_2.jpg",
                                                     "contribuyente_f_pagina_3.jpg")])
    print("  CONTRIBUYENTE A y CONTRIBUYENTE F")


PARTES = {"6": restaurante, "7": drogueria, "8": taller, "renta": renta}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Carga más clientes de demostración (ficticios) por la API.")
    ap.add_argument("--url", required=True)
    ap.add_argument("--usuario", default="")
    ap.add_argument("--clave", default="")
    ap.add_argument("--solo", default="6,7,8,renta")
    args = ap.parse_args(argv)
    api = Api(args.url, args.usuario, args.clave)
    for clave in [x.strip() for x in args.solo.split(",") if x.strip()]:
        PARTES[clave](api)
    return 0


if __name__ == "__main__":
    sys.exit(main())
