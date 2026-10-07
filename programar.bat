@echo off
chcp 65001 >nul
title Carlos Cruz - programar mantenimiento
cd /d "%~dp0"
echo ==========================================================
echo   Programar el mantenimiento automatico de la base
echo ==========================================================
echo.
echo Esto crea una tarea de Windows que cada 3 dias hace una
echo consulta a la base, para que Supabase no pause el proyecto
echo por inactividad.
echo.
echo Si la aplicacion usa base local (SQLite), no hace falta:
echo una base local nunca se pausa.
echo.
set /p RESP="Desea programarla ahora? (S/N): "
if /i not "%RESP%"=="S" goto :fin

schtasks /create /tn "Carlos Cruz - mantener base viva" /tr "\"%~dp0.venv\Scripts\python.exe\" \"%~dp0backend\mantener_vivo.py\"" /sc daily /mo 3 /st 04:00 /f
if errorlevel 1 (
  echo.
  echo [ERROR] No se pudo crear la tarea.
  echo         Ejecute este archivo como Administrador y reintente.
) else (
  echo.
  echo Listo. La tarea quedo programada: cada 3 dias a las 4:00 a.m.
  echo Para quitarla:  schtasks /delete /tn "Carlos Cruz - mantener base viva" /f
)

:fin
echo.
pause
