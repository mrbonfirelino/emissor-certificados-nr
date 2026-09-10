@echo off
setlocal EnableExtensions
title NormaTech Portal - Atualizacao
cd /d "%~dp0"

echo ============================================
echo  NORMATECH PORTAL - ATUALIZACAO
echo ============================================
echo Coloque a versao nova dentro de uma pasta
echo "Atualizacao" (src\, run_web.py, requirements-web.txt)
echo ao lado deste script. Downtime estimado: ~1 min.
echo.

net session >nul 2>&1
if errorlevel 1 (
    echo [AVISO] Rode como Administrador para parar/iniciar o servico.
)

REM 0) Localiza pasta de atualizacao
set "SRC="
for /d %%D in ("Atuali*") do set "SRC=%%D"
if "%SRC%"=="" (
    echo [ERRO] Nenhuma pasta "Atualizacao" encontrada ao lado deste script.
    pause
    exit /b 1
)
echo Pasta de atualizacao: %SRC%

REM 1) Para o servico (se existir NSSM)
set "NSSM=tools\nssm.exe"
set "TEM_SERVICO=0"
if exist "%NSSM%" (
    "%NSSM%" stop NormaTechPortal >nul 2>&1
    set "TEM_SERVICO=1"
)

REM 2) Backup do data\
for /f %%T in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd_HHmmss"') do set "TS=%%T"
if not exist "backups" mkdir "backups"
echo [1/5] Backup data\ -^> backups\pre_atualizacao_portal_%TS%.zip ...
powershell -NoProfile -Command "Compress-Archive -Path 'data\*' -DestinationPath 'backups\pre_atualizacao_portal_%TS%.zip' -Force"
if errorlevel 1 ( echo [ERRO] Falha no backup - abortado. & pause & exit /b 1 )

REM 3) Copia dos arquivos novos (data\ e .venv intocados)
echo [2/5] Copiando arquivos novos ...
if exist "%SRC%\src"  robocopy "%SRC%\src"  "src"  /MIR /XD __pycache__ /NFL /NDL /NJH /NJS /NP
if exist "%SRC%\src"  if errorlevel 8 ( echo [ERRO] robocopy src falhou & pause & exit /b 1 )
if exist "%SRC%\run_web.py"           copy /Y "%SRC%\run_web.py"           . >nul
if exist "%SRC%\requirements-web.txt" copy /Y "%SRC%\requirements-web.txt" . >nul

REM 4) Dependencias
echo [3/5] Sincronizando dependencias ...
".venv\Scripts\python.exe" -m pip install -r requirements-web.txt -q

REM 5) Inicia novamente
echo [4/5] Reativando o portal ...
if "%TEM_SERVICO%"=="1" (
    "%NSSM%" start NormaTechPortal
) else (
    echo        Servico nao instalado - inicie manualmente:
    echo        .venv\Scripts\python run_web.py --host 0.0.0.0 --port 8000
)

echo [5/5] Limpando pasta de atualizacao ...
del /q /f "%SRC%\*.*" >nul 2>&1
for /d %%S in ("%SRC%\*") do rd /s /q "%%S" >nul 2>&1
rd /q "%SRC%" >nul 2>&1

echo.
echo CONCLUIDO. Backup salvo em backups\pre_atualizacao_portal_%TS%.zip
pause
