@echo off
setlocal EnableExtensions
title NormaTech - Desativar Modo Protegido do Office
cd /d "%~dp0"

echo =========================================================
echo  NORMATECH - DESATIVA MODO PROTEGIDO DO OFFICE
echo ---------------------------------------------------------
echo O Modo Protegido faz o Excel/PowerPoint recusar a
echo exportacao para PDF via COM (erro -2147352567).
echo Este script desativa o Modo Protegido para o usuario
echo atual e remove o bloqueio de internet dos arquivos.
echo =========================================================
echo.

for %%A in (Excel PowerPoint Word) do (
    for %%V in (DisableInternetFilesInPV DisableUnsafeLocationsInPV DisableAttachInPV) do (
        reg add "HKCU\Software\Microsoft\Office\16.0\%%A\Security\ProtectedView" /v %%V /t REG_DWORD /d 1 /f >nul 2>&1
        reg add "HKCU\Software\Microsoft\Office\15.0\%%A\Security\ProtectedView" /v %%V /t REG_DWORD /d 1 /f >nul 2>&1
    )
)
echo [OK] Modo Protegido desativado (Excel/PowerPoint/Word, Office 15 e 16).

echo Removendo bloqueio de internet dos arquivos do projeto ...
powershell -NoProfile -Command "Get-ChildItem -Recurse -Path . -File -ErrorAction SilentlyContinue | Unblock-File"
echo [OK] Arquivos desbloqueados.

echo.
echo CONCLUIDO. Rode novamente apenas apos atualizar o sistema.
pause
