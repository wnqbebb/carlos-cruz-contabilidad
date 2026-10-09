@echo off
chcp 65001 >nul
rem ════════════════════════════════════════════════════════════════════════
rem  Carlos Cruz · revisión de seguridad (v2.3 · Fase 6, control C35)
rem  Corre lo mismo que GitHub Actions en cada push:
rem    1. pip-audit   dependencias de Python con vulnerabilidades conocidas
rem    2. npm audit   dependencias de la interfaz (falla con altas o críticas)
rem    3. bandit      análisis estático del backend
rem    4. semgrep     reglas de seguridad (si está disponible en este equipo)
rem    5. gitleaks    secretos y datos personales: el árbol actual y TODO el historial
rem    6. pruebas     las de seguridad
rem  Termina en 0 solo si todo pasa.
rem ════════════════════════════════════════════════════════════════════════
cd /d "%~dp0.."
set "FALLA=0"
set "PY=.venv\Scripts\python.exe"

echo [1/6] pip-audit...
"%PY%" -m pip install -q pip-audit bandit >nul 2>nul
"%PY%" -m pip_audit -r backend\requirements.lock --require-hashes --progress-spinner off || set "FALLA=1"

echo [2/6] npm audit...
pushd frontend
call npm audit --audit-level=high || set "FALLA=1"
popd

echo [3/6] bandit...
"%PY%" -m bandit -q -r backend\app -c backend\bandit.yaml || set "FALLA=1"

echo [4/6] semgrep...
rem semgrep se instala en el entorno con: .venv\Scripts\python -m pip install semgrep
if exist ".venv\Scripts\semgrep.exe" (
  set "PYTHONUTF8=1"
  ".venv\Scripts\semgrep.exe" scan --config p/python --config p/secrets --metrics=off --error --quiet backend\app || set "FALLA=1"
) else (
  echo   semgrep no está instalado en este equipo: lo corre GitHub Actions en cada push.
)

echo [5/6] gitleaks...
if not exist "herramientas\gitleaks\gitleaks.exe" (
  powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "$u=(Invoke-RestMethod https://api.github.com/repos/gitleaks/gitleaks/releases/latest).assets ^| ?{$_.name -like '*windows_x64.zip'} ^| select -First 1 -Expand browser_download_url; New-Item -ItemType Directory -Force herramientas\gitleaks ^| Out-Null; Invoke-WebRequest $u -OutFile herramientas\gitleaks\g.zip; Expand-Archive -Force herramientas\gitleaks\g.zip herramientas\gitleaks; Remove-Item herramientas\gitleaks\g.zip"
)
herramientas\gitleaks\gitleaks.exe git . --config .gitleaks.toml --redact --no-banner || set "FALLA=1"

echo [6/6] pruebas de seguridad...
pushd backend
"..\%PY%" -m pytest tests\test_seguridad.py tests\test_sesion.py -q -p no:cacheprovider || set "FALLA=1"
popd

echo.
if "%FALLA%"=="0" (
  echo   REVISION DE SEGURIDAD: TODO EN VERDE
  exit /b 0
)
echo   REVISION DE SEGURIDAD: HAY HALLAZGOS (ver arriba)
exit /b 1
