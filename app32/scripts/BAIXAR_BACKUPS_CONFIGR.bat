@echo off
title Baixar Backups de Producao do Servidor Configr
echo ==================================================
echo   GESTAOVERSUS - BACKUP DE PRODUCAO ^(CONFIGR^)
echo ==================================================
echo.
cd /d "%~dp0.."
python scripts\download_backups.py
set EXIT_CODE=%ERRORLEVEL%
echo.
echo ==================================================
if %EXIT_CODE% EQU 0 (
    echo   Backup de producao sincronizado com sucesso.
) else (
    echo   ERRO na sincronizacao do backup de producao ^(codigo %EXIT_CODE%^).
)
echo ==================================================
exit /b %EXIT_CODE%
