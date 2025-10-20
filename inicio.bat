@echo off
echo ========================================
echo    APP29 - Sistema de Planejamento
echo ========================================
echo.
echo Iniciando servidor...
echo.

REM Verificar se o Python do Anaconda está disponível
if exist "C:\Users\mff20\anaconda3\python.exe" (
    echo Usando Python do Anaconda...
    C:\Users\mff20\anaconda3\python.exe app_pev.py
) else (
    echo Python do Anaconda não encontrado. Tentando python padrão...
    python app_pev.py
)

echo.
echo Servidor finalizado.
pause

