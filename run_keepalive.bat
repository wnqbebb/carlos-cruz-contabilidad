@echo off
cd /d "%~dp0"
call .venv\Scripts\python backend\mantener_vivo.py >> datos_app\mantener_vivo.log 2>&1
