@echo off
chcp 65001 >nul
title Carlos Cruz - construir el instalador
cd /d "%~dp0.."
echo ==========================================================
echo   CARLOS CRUZ - construir el programa para el cliente
echo ==========================================================
echo.
echo Esto genera una carpeta que se puede copiar al computador
echo del cliente. Alli NO hay que instalar Python ni Node.
echo.

if not exist ".venv\Scripts\python.exe" (
  echo [ERROR] Falta el entorno. Ejecute primero iniciar.bat
  pause
  exit /b 1
)

echo [1/4] Instalando el empaquetador...
".venv\Scripts\python.exe" -m pip install -q --disable-pip-version-check pyinstaller
if errorlevel 1 (
  echo [ERROR] No se pudo instalar PyInstaller. Revise su conexion.
  pause
  exit /b 1
)

echo [2/4] Compilando la interfaz...
where npm >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Node.js no esta instalado. Se necesita solo AQUI, para compilar.
  echo         Descarguelo de https://nodejs.org
  pause
  exit /b 1
)
pushd frontend
call npm install --no-audit --no-fund
call npm run build
popd
if not exist "frontend\dist\index.html" (
  echo [ERROR] La interfaz no se compilo.
  pause
  exit /b 1
)

echo [3/4] Empaquetando...
".venv\Scripts\python.exe" -m PyInstaller --noconfirm --clean ^
  --distpath "empaquetar\salida" --workpath "empaquetar\temporal" ^
  "empaquetar\carloscruz.spec"
if errorlevel 1 (
  echo [ERROR] Fallo el empaquetado. Revise los mensajes de arriba.
  pause
  exit /b 1
)

echo [4/4] Agregando el instructivo...
copy /y "empaquetar\LEAME.txt" "empaquetar\salida\CarlosCruz\LEAME.txt" >nul 2>nul

echo.
echo ==========================================================
echo   LISTO
echo ==========================================================
echo.
echo   Carpeta generada:
echo     empaquetar\salida\CarlosCruz
echo.
echo   Copie ESA CARPETA COMPLETA al computador del cliente
echo   (en una USB, por Drive, por donde sea) y alli haga
echo   doble clic en CarlosCruz.exe
echo.
echo   Los datos del cliente quedan en:
echo     Documentos\Carlos Cruz
echo.
pause
