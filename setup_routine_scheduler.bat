@echo off
REM Script para configurar o agendador de rotinas no Windows
REM Este script cria uma tarefa agendada que roda diariamente às 00:01

echo ================================================
echo Configurando Agendador de Rotinas
echo ================================================
echo.

REM Obtém o diretório atual
set SCRIPT_DIR=%~dp0
set PYTHON_SCRIPT=%SCRIPT_DIR%routine_scheduler.py
set PYTHON_EXE=%SCRIPT_DIR%venv\Scripts\python.exe

echo Diretorio do script: %SCRIPT_DIR%
echo Script Python: %PYTHON_SCRIPT%
echo Python executavel: %PYTHON_EXE%
echo.

REM Verifica se o Python existe no venv
if not exist "%PYTHON_EXE%" (
    echo ERRO: Python nao encontrado no ambiente virtual!
    echo Por favor, certifique-se de que o venv esta configurado.
    pause
    exit /b 1
)

REM Verifica se o script Python existe
if not exist "%PYTHON_SCRIPT%" (
    echo ERRO: Script routine_scheduler.py nao encontrado!
    pause
    exit /b 1
)

echo Criando tarefa agendada no Windows...
echo.

REM Remove a tarefa se já existir
schtasks /Delete /TN "RoutineScheduler" /F >nul 2>&1

REM Cria a nova tarefa agendada
REM /SC DAILY = Executa diariamente
REM /ST 00:01 = Horário de execução (00:01)
REM /TN = Nome da tarefa
REM /TR = Comando a ser executado

schtasks /Create /SC DAILY /ST 00:01 /TN "RoutineScheduler" /TR "\"%PYTHON_EXE%\" \"%PYTHON_SCRIPT%\"" /F

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ================================================
    echo Tarefa agendada criada com sucesso!
    echo ================================================
    echo.
    echo A tarefa "RoutineScheduler" sera executada:
    echo   - Diariamente as 00:01
    echo   - Script: %PYTHON_SCRIPT%
    echo.
    echo Para verificar: Abra o "Agendador de Tarefas" do Windows
    echo Para testar manualmente: Execute routine_scheduler.py
    echo.
) else (
    echo.
    echo ERRO ao criar a tarefa agendada!
    echo Por favor, execute este script como Administrador.
    echo.
)

pause



