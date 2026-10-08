#!/usr/bin/env bash
# Lighthouse (accesibilidad y buenas prácticas) en claro y oscuro (v2.2 · 8.4).
#   scripts/lighthouse-modos.sh http://127.0.0.1:8001 <carpeta-salida> /ruta1 /ruta2 …
# El modo oscuro se fuerza con la preferencia del sistema: la aplicación arranca
# en «Sistema» y la sigue.
set -uo pipefail
BASE="$1"; SALIDA="$2"; shift 2
mkdir -p "$SALIDA"
EDGE="/c/Program Files (x86)/Microsoft/Edge/Application/msedge.exe"
export CHROME_PATH="$EDGE"
for ruta in "$@"; do
  for modo in claro oscuro; do
    for forma in mobile desktop; do
      bandera="--headless=new --blink-settings=preferredColorScheme=1"
      [ "$modo" = oscuro ] && bandera="--headless=new --force-dark-mode --blink-settings=preferredColorScheme=0"
      nombre="$(echo "$ruta" | tr '/?=&' '____')-$modo-$forma"
      extra=""
      [ "$forma" = desktop ] && extra="--preset=desktop"
      npx -y lighthouse@12 "$BASE$ruta" $extra --only-categories=accessibility,best-practices \
        --chrome-flags="$bandera" --output=json --output-path="$SALIDA/$nombre.json" --quiet >/dev/null 2>&1
      node -e "const r=require(process.argv[1]);const c=r.categories;const malos=Object.values(r.audits).filter(a=>a.score!==null&&a.score<1&&r.categories.accessibility.auditRefs.some(x=>x.id===a.id)).map(a=>a.id);console.log(process.argv[2].padEnd(48),'a11y',Math.round(c.accessibility.score*100),'bp',Math.round(c['best-practices'].score*100),malos.join(' '))" "$SALIDA/$nombre.json" "$nombre"
    done
  done
done
