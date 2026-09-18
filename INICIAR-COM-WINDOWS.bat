@echo off
setlocal EnableExtensions
title NormaTech Portal - Iniciar com o Windows
cd /d "%~dp0"

REM Rodar UMA VEZ: cria atalho na Inicializacao do Windows para o portal
REM abrir sozinho quando o computador ligar. Desfazer = apagar o atalho
REM em shell:startup (Windows+R -> shell:startup).

set ATALHO=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\NormaTech Portal.lnk

powershell -NoProfile -Command "$s=(New-Object -ComObject WScript.Shell).CreateShortcut('%ATALHO%'); $s.TargetPath='%~dp0INICIAR-PORTAL.bat'; $s.WorkingDirectory='%~dp0'; $s.WindowStyle=7; $s.Description='NormaTech Portal (inicia com o Windows)'; $s.Save()"
if errorlevel 1 (
    echo [ERRO] Nao consegui criar o atalho em:
    echo   %ATALHO%
    pause
    exit /b 1
)
echo [1/2] Atalho criado: o portal inicia sozinho quando o Windows ligar.

REM Firewall (so funciona se este script foi executado como Administrador)
net session >nul 2>&1
if errorlevel 1 (
    echo [2/2] AVISO: firewall nao liberado. Rode este script como Administrador
    echo       uma vez, ou libere a porta manualmente:
    echo       netsh advfirewall firewall add rule name="NormaTech Web" dir=in action=allow protocol=TCP localport=8000
) else (
    netsh advfirewall firewall delete rule name="NormaTech Web" >nul 2>&1
    netsh advfirewall firewall add rule name="NormaTech Web" dir=in action=allow protocol=TCP localport=8000 >nul
    echo [2/2] Firewall liberado na porta 8000.
)

echo.
echo PRONTO. Para desfazer, apague o atalho "NormaTech Portal" em shell:startup
pause
