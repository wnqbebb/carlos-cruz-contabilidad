"""Plantilla oficial: hojas con encabezados buscados por sinónimos (no por posición)."""
from __future__ import annotations

from decimal import Decimal

from ..contabilidad.puc import puc
from ..modelos import (ActivoFijo, Alerta, ConteoFisico, Empleado, MovInventario, Movimiento, Paquete, SaldoInicial)
from ..utils.numeros import CERO, D, mes_año_en_texto, normalizar, parse_fecha
from .base import Deteccion
from .lector import Hoja

HOJAS = ("EMPRESA", "SALDOS INICIALES", "MOVIMIENTOS", "AJUSTES", "INVENTARIO MOVS", "INVENTARIO FISICO", "ACTIVOS FIJOS", "NOMINA")

_CONTABLE = {
    "fecha": ["FECHA"], "comprobante": ["NO COMPROBANTE", "COMPROBANTE", "NUMERO COMPROBANTE"], "tipo": ["TIPO"],
    "codigo": ["CODIGO PUC", "CODIGO", "CUENTA PUC", "PUC"], "nombre": ["NOMBRE CUENTA", "NOMBRE DE LA CUENTA", "CUENTA"],
    "tercero_id": ["NIT TERCERO", "NIT CC TERCERO", "TERCERO NIT", "NIT", "IDENTIFICACION"],
    "tercero_nombre": ["NOMBRE TERCERO", "TERCERO"], "descripcion": ["DESCRIPCION", "DETALLE", "CONCEPTO"],
    "debito": ["DEBITO", "DEBE", "SALDO DEBITO"], "credito": ["CREDITO", "HABER", "SALDO CREDITO"],
    "base": ["BASE RETENCION", "BASE"],
}
ESQUEMAS = {
    "SALDOS INICIALES": {k: _CONTABLE[k] for k in ("codigo", "nombre", "debito", "credito")},
    "MOVIMIENTOS": _CONTABLE,
    "AJUSTES": _CONTABLE,
    "INVENTARIO MOVS": {
        "fecha": ["FECHA"], "documento": ["DOCUMENTO", "NO DOCUMENTO", "FACTURA"],
        "codigo": ["CODIGO PRODUCTO", "CODIGO", "REFERENCIA"], "descripcion": ["DESCRIPCION", "PRODUCTO", "NOMBRE"],
        "laboratorio": ["LABORATORIO", "MARCA"], "lote": ["LOTE"], "vencimiento": ["FECHA VENCIMIENTO", "VENCIMIENTO", "VENCE"],
        "tipo": ["TIPO", "TIPO MOVIMIENTO"], "cantidad": ["CANTIDAD", "UNIDADES"], "costo": ["COSTO UNITARIO", "COSTO"],
        "precio": ["PRECIO VENTA", "PRECIO"],
    },
    "INVENTARIO FISICO": {"codigo": ["CODIGO PRODUCTO", "CODIGO"], "cantidad": ["CANTIDAD CONTADA", "CANTIDAD", "CONTEO"],
                          "fecha": ["FECHA DE CONTEO", "FECHA CONTEO", "FECHA"]},
    "ACTIVOS FIJOS": {
        "descripcion": ["DESCRIPCION", "ACTIVO"], "cuenta": ["CUENTA PUC", "CODIGO PUC", "CUENTA", "CODIGO"],
        "fecha": ["FECHA COMPRA", "FECHA DE COMPRA", "FECHA"], "costo": ["COSTO", "VALOR"],
        "vida": ["VIDA UTIL MESES", "VIDA UTIL", "MESES"], "residual": ["VALOR RESIDUAL", "RESIDUAL"], "metodo": ["METODO"],
    },
    "NOMINA": {
        "mes": ["MES"], "nombre": ["NOMBRE", "EMPLEADO"], "cedula": ["CEDULA", "DOCUMENTO"], "cargo": ["CARGO"],
        "salario": ["SALARIO BASICO", "SALARIO", "BASICO"], "valor_hora": ["VALOR HORA"], "horas": ["HORAS TRABAJADAS", "HORAS"],
        "dias": ["DIAS TRABAJADOS", "DIAS"], "aux": ["AUX TRANSPORTE", "AUXILIO DE TRANSPORTE", "AUX"],
        "extras": ["HORAS EXTRA", "VALOR HORAS EXTRA", "EXTRAS"], "comisiones": ["COMISIONES"],
        "riesgo": ["CLASE RIESGO ARL", "CLASE DE RIESGO ARL", "CLASE RIESGO", "RIESGO ARL"],
    },
}
EMPRESA_CAMPOS = {
    "RAZON SOCIAL": "razon_social", "SIGLA": "sigla", "NIT": "nit", "DIRECCION": "direccion", "MUNICIPIO": "municipio",
    "PERIODO DESDE": "periodo_desde", "PERIODO HASTA": "periodo_hasta", "REPRESENTANTE LEGAL": "rep_legal",
    "CC REPRESENTANTE LEGAL": "rep_legal_cc", "CONTADOR": "contador", "CC CONTADOR": "contador_cc",
    "TARJETA PROFESIONAL CONTADOR": "contador_tp", "TARJETA PROFESIONAL": "contador_tp", "GRUPO NIIF": "grupo_niif",
    "RESPONSABLE DE IVA": "responsable_iva", "TARIFA RENTA": "tarifa_renta", "CAPITAL SUSCRITO": "capital_suscrito",
    "DEMO": "demo",
}
TIPOS_INV = {
    "INVENTARIO INICIAL": "inventario_inicial", "INICIAL": "inventario_inicial", "SALDO INICIAL": "inventario_inicial",
    "COMPRA": "compra", "ENTRADA": "compra", "VENTA": "venta", "SALIDA": "venta",
    "DEVOLUCION COMPRA": "devolucion_compra", "DEVOLUCION EN COMPRA": "devolucion_compra",
    "DEVOLUCION VENTA": "devolucion_venta", "DEVOLUCION EN VENTA": "devolucion_venta", "AJUSTE": "ajuste",
}


def nombre_hoja(h: Hoja) -> str | None:
    n = normalizar(h.nombre.replace("_", " "))
    return n if n in HOJAS else None


def _mapear_encabezados(textos: list[tuple[int, str]], esquema: dict) -> dict[str, int]:
    asignados: dict[str, tuple[int, int]] = {}
    for c, t in textos:
        mejor, puntaje = None, 0
        for campo, sinonimos in esquema.items():
            for s in sinonimos:
                p = 1000 + len(s) if t == s else (len(s) if s in t else 0)
                if p > puntaje:
                    mejor, puntaje = campo, p
        if mejor and (mejor not in asignados or asignados[mejor][1] < puntaje):
            asignados[mejor] = (c, puntaje)
    return {k: v[0] for k, v in asignados.items()}


def _encabezado(h: Hoja, esquema: dict) -> tuple[int, dict[str, int]] | None:
    for r in range(min(h.nfilas, 8)):
        cols = _mapear_encabezados(h.fila_textos(r), esquema)
        if len(cols) >= 2:
            return r, cols
    return None


def _codigo(valor) -> str:
    if valor is None:
        return ""
    if isinstance(valor, float) and valor.is_integer():
        return str(int(valor))
    return str(valor).strip().split(".")[0].replace(" ", "") if str(valor).strip().replace(".", "").isdigit() else str(valor).strip()


def importar(h: Hoja, id_: str) -> Deteccion:
    tipo = nombre_hoja(h)
    paquete = Paquete()
    if tipo == "EMPRESA":
        datos = {}
        for r in range(h.nfilas):
            etiqueta = h.norm(r, 0)
            if etiqueta in EMPRESA_CAMPOS and h.v(r, 1) is not None:
                datos[EMPRESA_CAMPOS[etiqueta]] = h.v(r, 1)
        paquete.empresa = datos
        return Deteccion(id_, h.archivo, h.nombre, "plantilla", True, "Datos de la empresa y del periodo", {"hoja": tipo, "campos": len(datos)}, paquete)

    enc = _encabezado(h, ESQUEMAS[tipo])
    if not enc:
        return Deteccion(id_, h.archivo, h.nombre, "plantilla", False, "No se encontraron los encabezados esperados", {"hoja": tipo}, paquete)
    r_h, cols = enc

    def v(r, campo):
        return h.v(r, cols[campo]) if campo in cols else None

    p = puc()
    filas = 0
    for r in range(r_h + 1, h.nfilas):
        if all(h.v(r, c) is None for c in cols.values()):
            continue
        filas += 1
        origen = h.origen(r)
        if tipo in ("SALDOS INICIALES", "MOVIMIENTOS", "AJUSTES"):
            deb, cre = D(v(r, "debito")), D(v(r, "credito"))
            if not deb and not cre:
                paquete.filas_ignoradas.append({"origen": origen, "motivo": "Fila sin débito ni crédito"})
                continue
            codigo = _codigo(v(r, "codigo"))
            nombre = str(v(r, "nombre") or "").strip()
            cuenta = codigo if codigo and p.valido(codigo) else ""
            if codigo and not cuenta:
                paquete.alertas.append(Alerta("PUC", "advertencia", f"Código «{codigo}» no existe en el PUC; se mapeará por nombre.", origen=origen))
                nombre = nombre or codigo
            if tipo == "SALDOS INICIALES":
                paquete.saldos_iniciales.append(SaldoInicial(cuenta, deb, cre, nombre, origen))
            else:
                m = Movimiento(cuenta, deb, cre, parse_fecha(v(r, "fecha")), str(v(r, "comprobante") or "").strip(),
                               normalizar(v(r, "tipo")).lower(), nombre, _codigo(v(r, "tercero_id")), str(v(r, "tercero_nombre") or ""),
                               str(v(r, "descripcion") or ""), origen, D(v(r, "base")) if v(r, "base") is not None else None)
                (paquete.ajustes_manuales if tipo == "AJUSTES" else paquete.movimientos).append(m)
        elif tipo == "INVENTARIO MOVS":
            t = TIPOS_INV.get(normalizar(v(r, "tipo")))
            cant = D(v(r, "cantidad"))
            if not t or not cant:
                paquete.filas_ignoradas.append({"origen": origen, "motivo": f"Tipo de movimiento «{v(r, 'tipo')}» no reconocido o cantidad vacía"})
                continue
            costo = v(r, "costo")
            precio = v(r, "precio")
            paquete.inventario_movs.append(MovInventario(
                _codigo(v(r, "codigo")), t, cant, parse_fecha(v(r, "fecha")), str(v(r, "documento") or ""),
                str(v(r, "descripcion") or ""), str(v(r, "laboratorio") or ""), str(v(r, "lote") or ""),
                parse_fecha(v(r, "vencimiento")), D(costo) if costo not in (None, "") else None,
                D(precio) if precio not in (None, "") else None, origen))
        elif tipo == "INVENTARIO FISICO":
            paquete.inventario_fisico.append(ConteoFisico(_codigo(v(r, "codigo")), D(v(r, "cantidad")), parse_fecha(v(r, "fecha")), origen))
        elif tipo == "ACTIVOS FIJOS":
            paquete.activos_fijos.append(ActivoFijo(
                str(v(r, "descripcion") or ""), _codigo(v(r, "cuenta")), parse_fecha(v(r, "fecha")), D(v(r, "costo")),
                int(D(v(r, "vida"))), D(v(r, "residual")), str(v(r, "metodo") or "linea_recta"), origen))
        elif tipo == "NOMINA":
            salario, vh = D(v(r, "salario")), D(v(r, "valor_hora"))
            aux = normalizar(v(r, "aux"))
            mes, año = mes_año_en_texto(str(v(r, "mes") or ""))
            mes_val = v(r, "mes")
            if isinstance(mes_val, (int, float)) and 1 <= int(mes_val) <= 12:
                mes = int(mes_val)
            fecha_mes = parse_fecha(mes_val)
            if fecha_mes:
                mes, año = fecha_mes.month, fecha_mes.year
            e = Empleado(
                nombre=str(v(r, "nombre") or "").strip(), cargo=str(v(r, "cargo") or ""), cedula=_codigo(v(r, "cedula")),
                mes=mes, año=año, salario_basico=salario or None, valor_hora=vh or None, horas=D(v(r, "horas")) or None,
                dias=D(v(r, "dias")) or Decimal("30"), aux_transporte="si" if aux in ("SI", "S") else ("no" if aux in ("NO", "N") else "auto"),
                horas_extra=D(v(r, "extras")), comisiones=D(v(r, "comisiones")), clase_riesgo=int(D(v(r, "riesgo")) or 1), origen=origen)
            if not e.nombre or not (e.salario_basico or (e.valor_hora and e.horas)):
                paquete.filas_ignoradas.append({"origen": origen, "motivo": "Empleado sin nombre o sin salario/horas"})
                continue
            paquete.empleados.append(e)
    resumen = {"hoja": tipo, "filas": filas, "movimientos": len(paquete.movimientos) + len(paquete.ajustes_manuales),
               "saldos_iniciales": len(paquete.saldos_iniciales), "productos_movs": len(paquete.inventario_movs),
               "empleados": len(paquete.empleados), "activos_fijos": len(paquete.activos_fijos)}
    return Deteccion(id_, h.archivo, h.nombre, "plantilla", True, "", resumen, paquete)


def cero() -> Decimal:
    return CERO
