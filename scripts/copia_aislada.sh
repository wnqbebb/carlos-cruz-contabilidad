#!/usr/bin/env bash
# Copia aislada para probar sin tocar la base real: puerto 8001 y SQLite desechable.
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
echo "Copia aislada · base: $CC_SQLITE"
exec "$RAIZ/.venv/Scripts/python" -m uvicorn app.main:app --app-dir "$RAIZ/backend" --host 127.0.0.1 --port 8001
