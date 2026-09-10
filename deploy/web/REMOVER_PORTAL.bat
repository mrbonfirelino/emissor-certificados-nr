@echo off
setlocal EnableExtensions
title NormaTech Portal - Remocao
cd /d "%~dp0"

echo ============================================
echo  NORMATECH PORTAL - REMOCAO
echo ============================================
echo  Remove o servico Windows e a regra de firewall.
echo  Os arquivos (src\, data\, .venv\) permanecem.
echo.

net session >nul 2>&1
if errorlevel 1 (
    echo [AVISO] Rode como Administrador.
)

if exist "tools\nssm.exe" (
    tools\nssm.exe stop NormaTechPortal   >nul 2>&1
    tools\nssm.exe remove NormaTechPortal confirm >nul 2>&1
    echo [1/2] Servico NormaTechPortal removido (se existia).
) else (
    echo [1/2] NSSM nao encontrado - servico nao removido automaticamente.
)

netsh advfirewall firewall delete rule name="NormaTech Portal" >nul 2>&1
echo [2/2] Regra de firewall "NormaTech Portal" removida (se existia).

echo.
echo CONCLUIDO. Para apagar tudo tambem do disco, exclua
echo manualmente a pasta do portal (data\ contem os dados!).
pause
