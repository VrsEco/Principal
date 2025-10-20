@echo off
echo ============================================================
echo REINICIANDO SERVIDOR COM NOVO BLUEPRINT
echo ============================================================
echo.

echo [1] Parando processos Python antigos...
taskkill /F /IM python.exe 2>nul
timeout /t 2 /nobreak >nul

echo [2] Limpando cache Python...
if exist __pycache__ rmdir /s /q __pycache__ 2>nul
if exist middleware\__pycache__ rmdir /s /q middleware\__pycache__ 2>nul
if exist services\__pycache__ rmdir /s /q services\__pycache__ 2>nul
if exist api\__pycache__ rmdir /s /q api\__pycache__ 2>nul

echo [3] Iniciando servidor...
echo.
echo ============================================================
echo SERVIDOR INICIANDO - Aguarde as mensagens de sucesso
echo ============================================================
echo.

python app_pev.py

