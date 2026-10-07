"""NIT colombiano: limpieza, dígito de verificación y vencimientos DIAN.

El dígito de verificación (DV) se calcula con el algoritmo oficial de la DIAN:
se multiplica cada dígito del NIT —leído de derecha a izquierda— por un primo
de la tabla, se suman los productos y se toma el residuo módulo 11.
"""
from __future__ import annotations

import re

# Primos oficiales DIAN, de derecha a izquierda del NIT.
_PRIMOS = (3, 7, 13, 17, 19, 23, 29, 37, 41, 43, 47, 53, 59, 67, 71)


def limpiar(nit: str | int | None) -> str:
    """Deja solo los dígitos de la parte del NIT, sin DV, puntos ni guiones."""
    if nit is None:
        return ""
    texto = str(nit).strip()
    # Si viene como [NIT]-9 o [NIT]-9, el guion separa el DV.
    base = texto.split("-")[0] if "-" in texto else texto
    return re.sub(r"\D", "", base)


def digito_verificacion(nit: str | int | None) -> str:
    """DV del NIT. Devuelve '' si el NIT no es utilizable."""
    base = limpiar(nit)
    if not base or len(base) > len(_PRIMOS):
        return ""
    suma = sum(int(d) * p for d, p in zip(reversed(base), _PRIMOS))
    residuo = suma % 11
    return str(residuo if residuo < 2 else 11 - residuo)


def valido(nit: str | int | None, dv: str | int | None = None) -> bool:
    """¿El NIT es plausible? Si se da un DV, verifica que coincida."""
    base = limpiar(nit)
    if not (5 <= len(base) <= 15):
        return False
    if dv in (None, ""):
        return True
    return str(dv).strip() == digito_verificacion(base)


def formatear(nit: str | int | None, dv: str | int | None = None) -> str:
    """'[NIT]' → '[NIT]-9' (calcula el DV si no se entrega)."""
    base = limpiar(nit)
    if not base:
        return ""
    verificador = str(dv).strip() if dv not in (None, "") else digito_verificacion(base)
    miles = f"{int(base):,}".replace(",", ".")
    return f"{miles}-{verificador}" if verificador else miles


# ── Calendario tributario ───────────────────────────────────────────────────
# La DIAN asigna el día de vencimiento por el ÚLTIMO dígito del NIT (sin DV).
# El orden es: 1, 2, 3, ... 9, 0 → posiciones 1..10 dentro del grupo de plazos.
def turno_dian(nit: str | int | None) -> int:
    """Posición 1..10 del contribuyente en el calendario DIAN. 0 si no aplica."""
    base = limpiar(nit)
    if not base:
        return 0
    ultimo = int(base[-1])
    return 10 if ultimo == 0 else ultimo
