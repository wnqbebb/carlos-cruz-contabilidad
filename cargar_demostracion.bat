@echo off
chcp 65001 >nul
title Carlos Cruz - Cargar clientes de demostracion
cd /d "%~dp0"
echo ==========================================================
echo    Cargar clientes de DEMOSTRACION (todos ficticios)
echo ==========================================================
echo.
echo  La aplicacion debe estar abierta (iniciar.bat) en http://localhost:8000
echo  Se cargan 8 clientes contables (enero 2025 a septiembre 2026) y 8 de renta.
echo  Todos llevan la etiqueta "Demostracion" y se borran desde el menu de la
echo  cuenta  ^>  Sistema  ^>  Eliminar clientes de demostracion.
echo  Nunca tocan sus clientes reales.
echo.
set /p USUARIO=Su usuario:
set /p CLAVE=Su contrasena:
echo.
echo Cargando... (tarda unos 8 minutos)
set "CC_TESSERACT=%~dp0datos_app\tesseract\tesseract.exe"
pushd backend
"..\.venv\Scripts\python.exe" -m demo.generar_historicos --url http://localhost:8000 --usuario "%USUARIO%" --clave "%CLAVE%"
"..\.venv\Scripts\python.exe" -m demo.mas_demostracion --url http://localhost:8000 --usuario "%USUARIO%" --clave "%CLAVE%"
popd
set "CLAVE="
echo.
echo Listo. Recargue la pagina en el navegador.
pause
