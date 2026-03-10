@echo off
title Baixar Backups do Servidor Configr
echo ==================================================
echo   GESTAOVERSUS - SINCRONIZACAO DE BACKUPS
echo ==================================================
echo.
cd /d "%~dp0"
python scripts\download_backups.py
echo.
echo ==================================================
echo   Operacao finalizada. Pressione qualquer tecla.
echo ==================================================
pause > nul
