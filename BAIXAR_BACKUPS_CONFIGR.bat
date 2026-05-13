@echo off
setlocal
cd /d "%~dp0app32"
call BAIXAR_BACKUPS_CONFIGR.bat
exit /b %ERRORLEVEL%
