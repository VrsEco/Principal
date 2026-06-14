@echo off
setlocal
cd /d "%~dp0app32"
python scripts\download_backups.py
exit /b %ERRORLEVEL%
