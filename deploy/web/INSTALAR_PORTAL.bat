@echo off
setlocal EnableExtensions
title NormaTech Portal - Instalacao
cd /d "%~dp0"

echo ============================================
echo  NORMATECH PORTAL - INSTALACAO (Fase 1)
echo ============================================
echo Pasta: %CD%
echo.

REM 0) Admin (necessario para servico e firewall)
net session >nul 2>&1
if errorlevel 1 (
    echo [AVISO] Execute como Administrador para instalar o servico e liberar a porta 8000.
    echo.
)

REM 1) Python
set PY=python
%PY% --version >nul 2>&1
if errorlevel 1 (
    echo [ERRO] Python nao encontrado no PATH. Instale o Python 3.11+ e rode novamente.
    pause
    exit /b 1
)

REM 2) Ambiente virtual
if not exist ".venv\Scripts\python.exe" (
    echo [2/6] Criando ambiente virtual .venv ...
    %PY% -m venv .venv
    if errorlevel 1 ( echo [ERRO] Falha ao criar .venv & pause & exit /b 1 )
) else (
    echo [2/6] .venv ja existe.
)

REM 3) Dependencias
echo [3/6] Instalando dependencias (requirements-web.txt) ...
".venv\Scripts\python.exe" -m pip install --upgrade pip >nul
".venv\Scripts\python.exe" -m pip install -r requirements-web.txt
if errorlevel 1 ( echo [ERRO] Falha no pip install & pause & exit /b 1 )

REM 4) Teste de importacao
echo [4/6] Testando importacoes ...
".venv\Scripts\python.exe" -c "import fastapi, waitress, jinja2, itsdangerous, multipart; print('imports OK')"
if errorlevel 1 ( echo [ERRO] Falha ao importar dependencias & pause & exit /b 1 )

REM 5) Servico Windows (NSSM opcional)
set NSSM=tools\nssm.exe
if exist "%NSSM%" (
    echo [5/6] Instalando servico NormaTechPortal via NSSM ...
    "%NSSM%" install NormaTechPortal "%CD%\.venv\Scripts\python.exe" run_web.py --host 0.0.0.0 --port 8000
    "%NSSM%" set NormaTechPortal AppDirectory "%CD%"
    "%NSSM%" set NormaTechPortal AppStdout "%CD%\logs\portal_out.log"
    "%NSSM%" set NormaTechPortal AppStderr "%CD%\logs\portal_err.log"
    if not exist "logs" mkdir "logs"
    "%NSSM%" start NormaTechPortal
    echo        Servico NormaTechPortal instalado e iniciado.
) else (
    echo [5/6] tools\nssm.exe nao encontrado - servico NAO instalado.
    echo        Para testar manualmente:  .venv\Scripts\python run_web.py --host 0.0.0.0 --port 8000
    echo        (coloque nssm.exe em tools\ e rode este script de novo p/ virar servico)
)

REM 6) Firewall
echo [6/6] Liberando porta 8000 no firewall ...
netsh advfirewall firewall delete rule name="NormaTech Portal" >nul 2>&1
netsh advfirewall firewall add rule name="NormaTech Portal" dir=in action=allow protocol=TCP localport=8000 >nul
if errorlevel 1 ( echo [AVISO] Nao consegui liberar o firewall - rode como Administrador. ) else ( echo        Firewall OK. )

echo.
echo ============================================
echo  CONCLUIDO. Acesso na rede:
echo    http://NOME-DO-SERVIDOR:8000
echo    http://IP-DO-SERVIDOR:8000
echo  1o acesso: senha do admin aparece no
echo  console do servico (logs\portal_out.log)
echo  e em data\web_admin_provisorio.txt
echo ============================================
pause
