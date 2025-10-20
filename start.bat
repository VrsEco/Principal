@echo off
REM Script de Início Rápido - GestaoVersus (APP30) - Windows
REM Facilita o deploy em diferentes ambientes

title GestaoVersus - Deploy Manager

echo.
echo ========================================================
echo     GestaoVersus (APP30) - Deploy Manager
echo ========================================================
echo.

:menu
echo.
echo Escolha o ambiente:
echo.
echo 1. Desenvolvimento (Local)
echo 2. Producao (Docker Compose)
echo 3. Backup Database
echo 4. Restaurar Backup
echo 5. Health Check
echo 0. Sair
echo.

set /p choice="Opcao: "

if "%choice%"=="1" goto dev
if "%choice%"=="2" goto prod
if "%choice%"=="3" goto backup
if "%choice%"=="4" goto restore
if "%choice%"=="5" goto health
if "%choice%"=="0" goto exit
goto invalid

:dev
echo.
echo Iniciando ambiente de desenvolvimento...
echo.

REM Verificar se .env.development existe
if not exist .env.development (
    echo Arquivo .env.development nao encontrado. Criando...
    copy .env.example .env.development
    echo Configure .env.development antes de continuar!
    pause
    goto menu
)

REM Iniciar containers
docker-compose -f docker-compose.dev.yml up -d

echo.
echo Ambiente de desenvolvimento iniciado!
echo Acesse: http://localhost:5002
echo Adminer: http://localhost:8080
echo.
echo Para ver logs: docker-compose -f docker-compose.dev.yml logs -f
echo.
pause
goto menu

:prod
echo.
echo Iniciando ambiente de producao...
echo.

REM Verificar se .env.production existe
if not exist .env.production (
    echo Arquivo .env.production nao encontrado!
    echo Execute: copy .env.example .env.production
    echo E configure todas as variaveis!
    pause
    goto menu
)

REM Confirmar
set /p confirm="Isso vai iniciar a aplicacao em modo PRODUCAO. Continuar? (S/N): "
if /i not "%confirm%"=="S" (
    echo Cancelado.
    pause
    goto menu
)

REM Build e start
docker-compose up -d --build

echo.
echo Ambiente de producao iniciado!
echo Acesse: https://congigr.com
echo.
echo Para ver logs: docker-compose logs -f
echo.
pause
goto menu

:backup
echo.
echo Fazendo backup do database...
echo.

if exist scripts\backup_database.py (
    python scripts\backup_database.py
) else (
    echo Script de backup nao encontrado!
)

pause
goto menu

:restore
echo.
echo Restaurando backup...
echo.

if exist scripts\restore_database.py (
    python scripts\restore_database.py
) else (
    echo Script de restauracao nao encontrado!
)

pause
goto menu

:health
echo.
set /p url="URL da aplicacao (padrao: http://localhost:5002): "
if "%url%"=="" set url=http://localhost:5002

echo.
echo Verificando saude da aplicacao...
echo.

if exist scripts\health_check.py (
    python scripts\health_check.py --url %url%
) else (
    echo Script de health check nao encontrado!
)

pause
goto menu

:invalid
echo.
echo Opcao invalida!
pause
goto menu

:exit
echo.
echo Ate logo!
timeout /t 2
exit


