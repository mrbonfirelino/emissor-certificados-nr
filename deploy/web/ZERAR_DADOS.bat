@echo off
setlocal EnableExtensions
title NormaTech - Zerar dados
cd /d "%~dp0"

echo ============================================
echo  NORMATECH - ZERAR TODOS OS DADOS
echo ============================================
echo  Isso APAGA funcionarios, certificados, ASOs,
echo  EPIs, crachas, cartoes, integracoes e usuarios
echo  do portal. Backups antigos e configuracoes
echo  (empresa, senha de restauracao, preferencias)
echo  sao MANTIDOS.
echo.
echo  Feche o NormaTech desktop E pare o portal
echo  antes de continuar.
echo.
choice /c SN /m "Deseja realmente ZERAR os dados"
if errorlevel 2 exit /b 0

REM 1o ZIP de seguranca
for /f %%T in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd_HHmmss"') do set "TS=%%T"
if not exist "backups" mkdir "backups"
echo Criando copia de seguranca: backups\zerar_%TS%.zip ...
powershell -NoProfile -Command "Compress-Archive -Path 'data\*' -DestinationPath 'backups\zerar_%TS%.zip' -Force"
if errorlevel 1 ( echo [ERRO] Falha no backup - abortado. & pause & exit /b 1 )

echo.
choice /c SN /m "ULTIMA CONFIRMACAO: apagar os dados agora"
if errorlevel 2 ( echo Abortado - nada foi apagado. & pause & exit /b 0 )

REM Para o portal se houver servico
if exist "tools\nssm.exe" tools\nssm.exe stop NormaTechPortal >nul 2>&1

REM Banco + pastas geradas (configs permanecem)
del /q /f "data\certificados.db"     >nul 2>&1
del /q /f "data\certificados.db-wal" >nul 2>&1
del /q /f "data\certificados.db-shm" >nul 2>&1
for %%P in (certificados asos epis crachas cartoes assinados _previews backups) do (
    if exist "data\%%P" rd /s /q "data\%%P"
)

echo.
echo Dados apagados. Copia em backups\zerar_%TS%.zip
echo Na proxima abertura (desktop ou portal) o banco
echo nasce vazio; o usuario admin do portal sera
echo recriado com senha provisoria no primeiro boot.
if exist "tools\nssm.exe" tools\nssm.exe start NormaTechPortal >nul 2>&1
pause
