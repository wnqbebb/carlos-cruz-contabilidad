@echo off
chcp 65001 >nul
title Carlos Cruz - Contabilidad que cuadra
cd /d "%~dp0"
echo ==========================================================
echo    CARLOS CRUZ  -  Contabilidad que cuadra
echo ==========================================================
echo.

if not exist ".venv\Scripts\python.exe" (
  echo Creando el entorno de Python la primera vez...
  py -3.12 -m venv .venv 2>nul || py -3 -m venv .venv 2>nul || python -m venv .venv
  if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] No se encontro Python 3.10 o superior. Instalelo desde https://www.python.org
    pause
    exit /b 1
  )
)

echo Verificando dependencias...
rem v2.3 · C34: versiones fijas y verificadas con hash (backend\requirements.lock).
".venv\Scripts\python.exe" -m pip install -q --disable-pip-version-check --require-hashes -r backend\requirements.lock
if errorlevel 1 (
  echo [ERROR] No se pudieron instalar las dependencias. Revise la conexion a internet.
  pause
  exit /b 1
)

rem Revisión antes de cada commit (gitleaks y «nada de privado/»), si esto es una copia de git.
if exist ".git" git config core.hooksPath .githooks >nul 2>nul

if not exist "datos_app\tesseract\tesseract.exe" (
  echo Preparando el lector de fotos para la declaracion de renta...
  powershell -NoProfile -ExecutionPolicy Bypass -File "scripts\preparar_ocr.ps1"
)

if not exist "backend\.env" (
  echo Creando backend\.env a partir del ejemplo...
  copy /y "backend\.env.example" "backend\.env" >nul
  echo   Funciona con base local. Para usar Supabase, llene DATABASE_URL en ese archivo.
)

rem Recompila la interfaz si falta o si alguna pantalla cambio desde la ultima
rem compilacion. Sin esto, los cambios de diseno no aparecian (Fase 0).
set "COMPILAR=0"
if not exist "frontend\dist\index.html" set "COMPILAR=1"
where node >nul 2>nul
if not errorlevel 1 (
  node frontend\scripts\necesita-build.mjs
  if errorlevel 1 set "COMPILAR=1"
)
if "%COMPILAR%"=="1" (
  echo Compilando la interfaz...
  where npm >nul 2>nul
  if errorlevel 1 (
    if exist "frontend\dist\index.html" (
      echo [AVISO] Hay cambios sin compilar y Node.js no esta instalado: se usa la ultima compilacion.
    ) else (
      echo [ERROR] Falta la interfaz compilada y Node.js no esta instalado.
      echo         Instalelo desde https://nodejs.org y vuelva a ejecutar este archivo.
      pause
      exit /b 1
    )
  ) else (
    pushd frontend
    if not exist "node_modules" call npm ci --no-audit --no-fund
    call npm run build
    popd
  )
)

echo Preparando la base de datos y el primer cliente...
".venv\Scripts\python.exe" backend\sembrar.py

echo.
echo  La aplicacion queda disponible en:  http://localhost:8000
echo  Para detenerla, cierre esta ventana.
echo.
start "" cmd /c "timeout /t 3 >nul & start http://localhost:8000"
".venv\Scripts\python.exe" -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
pause
