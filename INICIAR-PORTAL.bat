@echo off
setlocal EnableExtensions
title NormaTech Portal
cd /d "%~dp0"

REM Uso: INICIAR-PORTAL.bat [porta]   (padrao 8000; use 80 para http://nome sem :porta)
set PORT=%1
if "%PORT%"=="" set PORT=8000

if not exist ".venv\Scripts\python.exe" (
    echo [1/2] Primeira execucao: criando ambiente virtual e instalando dependencias ...
    python -m venv .venv
    ".venv\Scripts\python.exe" -m pip install --upgrade pip >nul
    ".venv\Scripts\python.exe" -m pip install -r requirements-web.txt
    if errorlevel 1 ( echo [ERRO] Falha ao instalar dependencias & pause & exit /b 1 )
)

REM Auto-cura: se faltar algum modulo (ex.: venv antigo), completa as dependencias
".venv\Scripts\python.exe" -c "from src.web.app import create_app; from src.utils.excel_importer import import_employees_from_excel; from src.utils.batch_importer import generate_batch_certificates; from src.utils.aso_importer import import_asos_from_excel; from src.utils.blocking_importer import import_blocking_list" >nul 2>&1
if errorlevel 1 (
    echo Completando dependencias que faltam ...
    ".venv\Scripts\python.exe" -m pip install -r requirements-web.txt
    if errorlevel 1 ( echo [ERRO] Falha ao instalar dependencias & pause & exit /b 1 )
)

echo [2/2] Subindo o portal em http://0.0.0.0:%PORT% ...
".venv\Scripts\python.exe" run_web.py --host 0.0.0.0 --port %PORT%
pause
