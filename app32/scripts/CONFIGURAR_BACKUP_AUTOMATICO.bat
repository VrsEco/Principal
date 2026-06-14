@echo off
setlocal
title Configurar Backup Automatico de Producao
cd /d "%~dp0.."
echo ==================================================
echo   CONFIGURACAO DE BACKUP DE PRODUCAO
echo ==================================================
echo.
echo Este script registra a tarefa GestaoVersus_Postgres_Backup
echo para sincronizar o backup de PRODUCAO no Configr.
echo.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "scripts\backup\register_postgres_backup_tasks.ps1"
exit /b %ERRORLEVEL%
