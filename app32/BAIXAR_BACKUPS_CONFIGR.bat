@echo off
title Baixar Backups do Servidor Configr
echo ==================================================
echo   GESTAOVERSUS - SINCRONIZACAO DE BACKUPS
echo ==================================================
echo.
cd /d "%~dp0"
python scripts\download_backups.py
set EXIT_CODE=%ERRORLEVEL%
echo.
echo ==================================================
if %EXIT_CODE% EQU 0 (
    echo   Operacao finalizada com sucesso.
) else (
    echo   Operacao finalizada com erro ^(codigo %EXIT_CODE%^).
)
echo ==================================================
exit /b %EXIT_CODE%
