#!/usr/bin/env bash
# Copia aislada para probar sin tocar la base real: puerto 8001 (o $PUERTO) y SQLite desechable.
#   scripts/copia_aislada.sh [carpeta-de-la-base]
# Las pruebas que escriben datos (subir, calcular, cerrar) van SIEMPRE aquí.
set -euo pipefail
RAIZ="$(cd "$(dirname "$0")/.." && pwd)"
BASE="${1:-$(mktemp -d)}"
mkdir -p "$BASE"
export ALMACENAMIENTO=local
export CC_SQLITE="$BASE/aislada.db"
export CC_TMP_SUBIDAS="$BASE/subidas"
unset DATABASE_URL || true
# Usuario de prueba (A2), en un archivo de configuración propio de la copia:
# nunca se tocan las credenciales reales de backend/.env.
export CC_ENV="$BASE/copia.env"
if ! grep -q '^CC_USUARIO=' "$CC_ENV" 2>/dev/null; then
  "$RAIZ/.venv/Scripts/python" "$RAIZ/backend/crear_usuario.py" --usuario prueba --clave prueba-aislada-2026 --archivo "$CC_ENV" >/dev/null
fi
echo "Copia aislada · base: $CC_SQLITE · usuario: prueba / prueba-aislada-2026"
exec "$RAIZ/.venv/Scripts/python" -m uvicorn app.main:app --app-dir "$RAIZ/backend" --host 127.0.0.1 --port "${PUERTO:-8001}"
