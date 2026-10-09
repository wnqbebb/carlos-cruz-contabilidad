@echo off
chcp 65001 >nul
title Restablecer acceso · Carlos Cruz Contabilidad

echo ============================================================
echo   CARLOS CRUZ · Restablecer acceso local
echo ============================================================
echo.
echo Este comando restablece el acceso local de la aplicacion
echo para que pueda crear un nuevo usuario y contrasena.
echo.
set /p CONFIRMAR="Desea continuar? (S/N): "
if /i not "%CONFIRMAR%"=="S" (
    echo Operacion cancelada.
    pause
    exit /b 0
)

echo.
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" backend\scripts\restablecer_acceso.py
) else (
    python backend\scripts\restablecer_acceso.py
)

echo.
pause
