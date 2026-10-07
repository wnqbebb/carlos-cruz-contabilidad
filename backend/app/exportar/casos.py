"""Tres casos de ejemplo para probar la aplicación sin datos reales.

La idea es que el contador vea, sin arriesgar nada, qué pasa con un cliente
ordenado, con uno desordenado y con uno pequeño:

  · `completo`  — una tienda con TODO: inventario valorizado con lotes y
                  vencimientos, activos fijos, nómina, retenciones e IVA.
                  Sirve para ver la aplicación entera funcionando.

  · `mediocre`  — el caso real de todos los días: cuentas escritas a mano sin
                  código PUC, un comprobante descuadrado, saldos iniciales
                  incompletos y una nómina mal liquidada. Sirve para ver QUÉ
                  detecta el sistema y cómo lo explica.

  · `basico`    — un profesional independiente: ocho movimientos, sin
                  inventario ni nómina. Sirve para entender el flujo en un
                  minuto.

Todos los datos son ficticios. El motor los procesa igual que los reales.
"""
from __future__ import annotations

_PROV = ("900111222-3", "Distribuidora Naturista Demo S.A.S.")

# ════════════════════════════════════════════════════════════════════════════
#  1. COMPLETO — tienda naturista con todos los módulos
# ════════════════════════════════════════════════════════════════════════════
COMPLETO = {
    "_meta": {
        "nombre": "Tienda completa",
        "descripcion": "Comercio con inventario valorizado, activos fijos, nómina, IVA y retenciones. "
                       "Todo cuadra: sirve para ver la aplicación entera.",
        "periodo": ("2025-01-01", "2025-01-31"),
        "empresa": "COMERCIALIZADORA EJEMPLO COMPLETO S.A.S.",
        "nit": "901234567",
    },
    "SALDOS_INICIALES": [
        ("110505", "Caja general", 1500000, None),
        ("111005", "Bancos", 20000000, None),
        ("1435", "Mercancías no fabricadas por la empresa", 6500000, None),
        ("152405", "Muebles y enseres", 2000000, None),
        ("3105", "Capital suscrito y pagado", None, 30000000),
    ],
    "MOVIMIENTOS": [
        ("2025-01-05", "CE-001", "Egreso", "5120", "Arrendamientos", "", "Arrendador local", "Arriendo local enero", 1200000, None, None),
        ("2025-01-05", "CE-001", "Egreso", "111005", "Bancos", "", "", "Pago arriendo enero", None, 1200000, None),
        ("2025-01-08", "FC-001", "Compra", "1435", "Mercancías", *_PROV, "Compra mercancía P001 y P005", 1600000, None, None),
        ("2025-01-08", "FC-001", "Compra", "240810", "IVA descontable", *_PROV, "IVA 19 % compra", 304000, None, None),
        ("2025-01-08", "FC-001", "Compra", "2205", "Proveedores nacionales", *_PROV, "Factura a crédito", None, 1904000, None),
        ("2025-01-10", "CE-002", "Egreso", "5135", "Servicios", "", "Empresa de servicios públicos", "Energía y agua", 180000, None, None),
        ("2025-01-10", "CE-002", "Egreso", "110505", "Caja general", "", "", "Pago servicios", None, 180000, None),
        ("2025-01-15", "RC-001", "Venta", "110505", "Caja general", "", "Clientes varios", "Ventas de contado 1 al 15", 6188000, None, None),
        ("2025-01-15", "RC-001", "Venta", "4135", "Comercio al por mayor y al por menor", "", "Clientes varios", "Ventas 1 al 15", None, 5200000, None),
        ("2025-01-15", "RC-001", "Venta", "240805", "IVA generado", "", "Clientes varios", "IVA 19 % ventas", None, 988000, None),
        ("2025-01-20", "FC-002", "Compra", "1435", "Mercancías", *_PROV, "Compra mercancía P002", 960000, None, None),
        ("2025-01-20", "FC-002", "Compra", "240810", "IVA descontable", *_PROV, "IVA 19 % compra", 182400, None, None),
        ("2025-01-20", "FC-002", "Compra", "111005", "Bancos", *_PROV, "Pago de contado", None, 1142400, None),
        ("2025-01-25", "CE-003", "Egreso", "519530", "Útiles, papelería y fotocopias", "", "Papelería", "Papelería", 85000, None, None),
        ("2025-01-25", "CE-003", "Egreso", "110505", "Caja general", "", "", "Pago papelería", None, 85000, None),
        ("2025-01-31", "RC-002", "Venta", "110505", "Caja general", "", "Clientes varios", "Ventas de contado 16 al 31", 6902000, None, None),
        ("2025-01-31", "RC-002", "Venta", "4135", "Comercio al por mayor y al por menor", "", "Clientes varios", "Ventas 16 al 31", None, 5800000, None),
        ("2025-01-31", "RC-002", "Venta", "240805", "IVA generado", "", "Clientes varios", "IVA 19 % ventas", None, 1102000, None),
        ("2025-01-31", "CE-004", "Egreso", "5110", "Honorarios", "[CEDULA]-1", "CARLOS ARTURO CRUZ CAICEDO", "Asesoría contable enero", 300000, None, 300000),
        ("2025-01-31", "CE-004", "Egreso", "236515", "Retención honorarios", "[CEDULA]-1", "CARLOS ARTURO CRUZ CAICEDO", "Retención en la fuente 10 %", None, 30000, 300000),
        ("2025-01-31", "CE-004", "Egreso", "111005", "Bancos", "[CEDULA]-1", "CARLOS ARTURO CRUZ CAICEDO", "Pago honorarios", None, 270000, None),
        ("2025-01-31", "NC-001", "Nota", "111005", "Bancos", "", "", "Consignación del efectivo", 5000000, None, None),
        ("2025-01-31", "NC-001", "Nota", "110505", "Caja general", "", "", "Consignación del efectivo", None, 5000000, None),
        ("2025-01-31", "NC-002", "Nota", "530505", "Gastos bancarios", "", "Banco", "Comisiones bancarias", 15000, None, None),
        ("2025-01-31", "NC-002", "Nota", "111005", "Bancos", "", "Banco", "Comisiones bancarias", None, 15000, None),
    ],
    "INVENTARIO_MOVS": [
        ("2024-12-31", "SI", "P001", "Moringa cápsulas x60", "Laboratorio Ejemplo", "M-2401", "2026-06-30", "Inventario inicial", 100, 18000, None),
        ("2024-12-31", "SI", "P002", "Omega 3 x100 cápsulas", "Laboratorio Ejemplo", "O-2402", "2025-03-15", "Inventario inicial", 80, 25000, None),
        ("2024-12-31", "SI", "P003", "Aceite de coco 500 ml", "Laboratorio Ejemplo", "C-2310", "2025-01-20", "Inventario inicial", 20, 15000, None),
        ("2024-12-31", "SI", "P003", "Aceite de coco 500 ml", "Laboratorio Ejemplo", "C-2412", "2026-01-31", "Inventario inicial", 40, 15000, None),
        ("2024-12-31", "SI", "P004", "Gel de sábila 250 g", "Laboratorio Ejemplo", "S-2404", "2025-04-10", "Inventario inicial", 90, 10000, None),
        ("2024-12-31", "SI", "P005", "Té verde x20 sobres", "Laboratorio Ejemplo", "T-2411", "2027-02-28", "Inventario inicial", 150, 6000, None),
        ("2025-01-08", "FC-001", "P001", "Moringa cápsulas x60", "Laboratorio Ejemplo", "M-2501", "2027-01-31", "Compra", 50, 19000, None),
        ("2025-01-08", "FC-001", "P005", "Té verde x20 sobres", "Laboratorio Ejemplo", "T-2501", "2027-06-30", "Compra", 100, 6500, None),
        ("2025-01-15", "RC-001", "P001", "Moringa cápsulas x60", "", "", None, "Venta", 40, None, 45000),
        ("2025-01-15", "RC-001", "P002", "Omega 3 x100 cápsulas", "", "", None, "Venta", 30, None, 60000),
        ("2025-01-15", "RC-001", "P004", "Gel de sábila 250 g", "", "", None, "Venta", 20, None, 28000),
        ("2025-01-15", "RC-001", "P005", "Té verde x20 sobres", "", "", None, "Venta", 60, None, 14000),
        ("2025-01-20", "FC-002", "P002", "Omega 3 x100 cápsulas", "Laboratorio Ejemplo", "O-2501", "2026-12-31", "Compra", 40, 24000, None),
        ("2025-01-31", "RC-002", "P001", "Moringa cápsulas x60", "", "", None, "Venta", 30, None, 45000),
        ("2025-01-31", "RC-002", "P002", "Omega 3 x100 cápsulas", "", "", None, "Venta", 30, None, 60000),
        ("2025-01-31", "RC-002", "P003", "Aceite de coco 500 ml", "", "C-2412", None, "Venta", 25, None, 38000),
        ("2025-01-31", "RC-002", "P004", "Gel de sábila 250 g", "", "", None, "Venta", 20, None, 28000),
        ("2025-01-31", "RC-002", "P005", "Té verde x20 sobres", "", "", None, "Venta", 60, None, 14000),
    ],
    "INVENTARIO_FISICO": [
        ("P001", 80, "2025-01-31"), ("P002", 58, "2025-01-31"), ("P003", 35, "2025-01-31"),
        ("P004", 50, "2025-01-31"), ("P005", 131, "2025-01-31"),
    ],
    "ACTIVOS_FIJOS": [
        ("Muebles y estantería de exhibición", "152405", "2024-12-20", 2000000, 120, 0, "Línea recta"),
    ],
    "NOMINA": [
        ("2025-01-01", "ADRIANA DURAN JARAMILLO", "[CEDULA]", "Administradora", 1423500, None, None, 30, "SI", 0, 0, 1),
    ],
}

# ════════════════════════════════════════════════════════════════════════════
#  2. MEDIOCRE — el archivo que llega en la vida real
# ════════════════════════════════════════════════════════════════════════════
# A propósito trae los errores que el sistema tiene que cazar:
#   · cuentas escritas a mano SIN código PUC → hay que mapearlas
#   · el comprobante CE-010 está descuadrado por $ 50.000
#   · faltan saldos iniciales de varias cuentas
#   · la nómina usa un salario por debajo del mínimo legal
MEDIOCRE = {
    "_meta": {
        "nombre": "Caso desordenado",
        "descripcion": "Como llegan los archivos de verdad: cuentas sin código PUC, un comprobante "
                       "descuadrado y una nómina mal liquidada. Sirve para ver QUÉ detecta el sistema.",
        "periodo": ("2025-01-01", "2025-01-31"),
        "empresa": "DISTRIBUIDORA EJEMPLO DESORDEN S.A.S.",
        "nit": "900987654",
    },
    "SALDOS_INICIALES": [
        ("110505", "Caja general", 800000, None),
        ("3105", "Capital suscrito y pagado", None, 800000),
    ],
    "MOVIMIENTOS": [
        # Cuentas sin código: el contador solo escribió el nombre.
        ("2025-01-03", "CE-010", "Egreso", "", "ARRIENDO LOCAL", "", "Arrendador", "Arriendo del mes", 900000, None, None),
        ("2025-01-03", "CE-010", "Egreso", "", "BANCO", "", "", "Pago arriendo", None, 850000, None),  # ← faltan $50.000
        ("2025-01-07", "FC-020", "Compra", "", "MERCANCIA", "900333444-5", "Proveedor Ejemplo", "Compra de mercancía", 2500000, None, None),
        ("2025-01-07", "FC-020", "Compra", "", "IVA DESCONTABLE", "900333444-5", "Proveedor Ejemplo", "IVA 19 %", 475000, None, None),
        ("2025-01-07", "FC-020", "Compra", "", "PROVEEDORES", "900333444-5", "Proveedor Ejemplo", "Queda a crédito", None, 2975000, None),
        ("2025-01-12", "RC-010", "Venta", "", "CAJA", "", "Clientes mostrador", "Ventas primera quincena", 4165000, None, None),
        ("2025-01-12", "RC-010", "Venta", "", "VENTAS", "", "Clientes mostrador", "Ventas primera quincena", None, 3500000, None),
        ("2025-01-12", "RC-010", "Venta", "", "IVA GENERADO", "", "Clientes mostrador", "IVA 19 %", None, 665000, None),
        ("2025-01-18", "CE-011", "Egreso", "", "SERVICIOS PUBLICOS", "", "Empresa de servicios", "Luz y agua", 240000, None, None),
        ("2025-01-18", "CE-011", "Egreso", "", "CAJA", "", "", "Pago servicios", None, 240000, None),
        ("2025-01-28", "RC-011", "Venta", "", "CAJA", "", "Clientes mostrador", "Ventas segunda quincena", 2975000, None, None),
        ("2025-01-28", "RC-011", "Venta", "", "VENTAS", "", "Clientes mostrador", "Ventas segunda quincena", None, 2500000, None),
        ("2025-01-28", "RC-011", "Venta", "", "IVA GENERADO", "", "Clientes mostrador", "IVA 19 %", None, 475000, None),
        ("2025-01-31", "CE-012", "Egreso", "", "GASTOS VARIOS", "", "Varios", "Gastos sin soporte detallado", 320000, None, None),
        ("2025-01-31", "CE-012", "Egreso", "", "CAJA", "", "", "Pago gastos varios", None, 320000, None),
    ],
    "NOMINA": [
        # Salario por debajo del mínimo legal: el motor lo detecta y lo explica.
        ("2025-01-01", "EMPLEADO DE EJEMPLO UNO", "1012345678", "Vendedor", 1000000, None, None, 30, "SI", 0, 0, 2),
    ],
}

# ════════════════════════════════════════════════════════════════════════════
#  3. BÁSICO — profesional independiente, lo mínimo para entender el flujo
# ════════════════════════════════════════════════════════════════════════════
BASICO = {
    "_meta": {
        "nombre": "Caso sencillo",
        "descripcion": "Un profesional independiente: ocho movimientos, sin inventario ni nómina. "
                       "Para entender el flujo completo en un minuto.",
        "periodo": ("2025-01-01", "2025-01-31"),
        "empresa": "SERVICIOS PROFESIONALES EJEMPLO",
        "nit": "19876543",
    },
    "SALDOS_INICIALES": [
        ("111005", "Bancos", 5000000, None),
        ("3105", "Capital suscrito y pagado", None, 5000000),
    ],
    "MOVIMIENTOS": [
        ("2025-01-10", "FV-001", "Venta", "130505", "Clientes nacionales", "900555666-7", "Cliente Ejemplo S.A.S.", "Factura de servicios enero", 4000000, None, None),
        ("2025-01-10", "FV-001", "Venta", "4155", "Actividades empresariales y de alquiler", "900555666-7", "Cliente Ejemplo S.A.S.", "Ingreso por servicios profesionales", None, 4000000, None),
        ("2025-01-20", "RC-001", "Nota", "111005", "Bancos", "900555666-7", "Cliente Ejemplo S.A.S.", "Pago de la factura", 3600000, None, None),
        ("2025-01-20", "RC-001", "Nota", "135515", "Retención en la fuente", "900555666-7", "Cliente Ejemplo S.A.S.", "Retención 10 % que le practicaron", 400000, None, 4000000),
        ("2025-01-20", "RC-001", "Nota", "130505", "Clientes nacionales", "900555666-7", "Cliente Ejemplo S.A.S.", "Cancela la factura", None, 4000000, None),
        ("2025-01-25", "CE-001", "Egreso", "5135", "Servicios", "", "Operador de internet", "Internet y telefonía", 150000, None, None),
        ("2025-01-25", "CE-001", "Egreso", "111005", "Bancos", "", "Operador de internet", "Pago internet", None, 150000, None),
        ("2025-01-31", "CE-002", "Egreso", "519530", "Útiles y papelería", "", "Papelería", "Papelería del mes", 90000, None, None),
        ("2025-01-31", "CE-002", "Egreso", "111005", "Bancos", "", "Papelería", "Pago papelería", None, 90000, None),
    ],
}

CASOS: dict[str, dict] = {
    "completo": COMPLETO,
    "mediocre": MEDIOCRE,
    "basico": BASICO,
}


def listar() -> list[dict]:
    """Catálogo de casos para que la interfaz los muestre."""
    return [
        {
            "id": clave,
            "nombre": datos["_meta"]["nombre"],
            "descripcion": datos["_meta"]["descripcion"],
            "empresa": datos["_meta"]["empresa"],
            "nit": datos["_meta"]["nit"],
            "movimientos": len(datos.get("MOVIMIENTOS", [])),
            "con_inventario": bool(datos.get("INVENTARIO_MOVS")),
            "con_nomina": bool(datos.get("NOMINA")),
            "con_activos": bool(datos.get("ACTIVOS_FIJOS")),
        }
        for clave, datos in CASOS.items()
    ]


def obtener(caso: str) -> dict:
    """Datos de un caso. Si el nombre no existe, devuelve el completo."""
    return CASOS.get((caso or "").strip().lower(), COMPLETO)
