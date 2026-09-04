@echo off
rem ============================================================
rem  NormaTech - ATUALIZAR.bat
rem  Como usar:
rem    1. Este arquivo deve ficar AO LADO da pasta CertificadosNR
rem    2. Crie uma pasta chamada "Atualizacao" (ao lado tambem)
rem    3. Copie para dentro dela o conteudo da nova versao
rem       (os arquivos da pasta CertificadosNR, ou a propria pasta)
rem    4. De dois cliques neste arquivo
rem  O programa e atualizado e a pasta Atualizacao e esvaziada.
rem  Seus dados (pasta data) NUNCA sao tocados e recebem backup.
rem ============================================================
setlocal
title NormaTech - Atualizador
cd /d "%~dp0"

set "APP=CertificadosNR"
if not exist "%APP%\CertificadosNR.exe" (
    echo [ERRO] Nao encontrei %APP%\CertificadosNR.exe
    echo Este arquivo deve ficar AO LADO da pasta CertificadosNR.
    pause
    exit /b 1
)

set "UPD="
for /d %%D in ("Atuali*") do set "UPD=%%~nxD"
if "%UPD%"=="" (
    echo [ERRO] Crie a pasta "Atualizacao" e coloque nela a nova versao.
    pause
    exit /b 1
)

set "SRC=%UPD%"
if exist "%UPD%\CertificadosNR\CertificadosNR.exe" set "SRC=%UPD%\CertificadosNR"
if not exist "%SRC%\CertificadosNR.exe" (
    echo [ERRO] A pasta "%UPD%" nao parece conter a nova versao.
    echo Coloque nela o CONTEUDO da pasta CertificadosNR da nova versao
    echo ou a propria pasta CertificadosNR.
    pause
    exit /b 1
)

echo (1/5) Fechando o programa se estiver aberto...
taskkill /F /IM CertificadosNR.exe >nul 2>&1
timeout /t 2 /nobreak >nul

echo (2/5) Backup de seguranca dos dados...
set "TS=%date:~-4%%date:~3,2%%date:~0,2%_%time:~0,2%%time:~3,2%%time:~6,2%"
set "TS=%TS: =0%"
robocopy "%APP%\data" "backup_pre_atualizacao_%TS%\data" /E >nul

echo (3/5) Atualizando arquivos do programa (a pasta data NAO e tocada)...
robocopy "%SRC%" "%APP%" /MIR /XD data /NFL /NDL /NJH /NJS /NP >nul
if errorlevel 8 (
    echo [ERRO] Falha ao copiar os arquivos. Tente novamente.
    echo Seus dados estao salvos em backup_pre_atualizacao_%TS%
    pause
    exit /b 1
)

echo (4/5) Limpando a pasta de atualizacao...
del /q "%UPD%"\* >nul 2>&1
for /d %%D in ("%UPD%\*") do rd /s /q "%%D" >nul 2>&1

echo (5/5) Atualizacao concluida com sucesso!
echo.
choice /c SN /m "Abrir o programa agora (S/N)"
if errorlevel 2 goto fim
start "" "%APP%\CertificadosNR.exe"
:fim
echo.
echo Dica: guarde a pasta backup_pre_atualizacao_%TS% por alguns dias.
pause
