@echo off
echo ================================================================================
echo   VER LOGS DO DOCKER - App GestaoVersus
echo ================================================================================
echo.
echo Escolha uma opcao:
echo.
echo [1] Ver logs em TEMPO REAL (acompanhar conforme acontecem)
echo [2] Ver ultimas 100 linhas dos logs
echo [3] Ver ultimas 50 linhas dos logs
echo [4] Ver todos os logs (pode ser muito!)
echo.
set /p opcao="Digite o numero da opcao: "

if "%opcao%"=="1" (
    echo.
    echo Mostrando logs em TEMPO REAL...
    echo Pressione Ctrl+C para sair
    echo.
    docker-compose -f docker-compose.dev.yml logs -f app_dev
)

if "%opcao%"=="2" (
    echo.
    echo Mostrando ultimas 100 linhas...
    echo.
    docker-compose -f docker-compose.dev.yml logs --tail=100 app_dev
    echo.
    echo Pressione qualquer tecla para fechar...
    pause >nul
)

if "%opcao%"=="3" (
    echo.
    echo Mostrando ultimas 50 linhas...
    echo.
    docker-compose -f docker-compose.dev.yml logs --tail=50 app_dev
    echo.
    echo Pressione qualquer tecla para fechar...
    pause >nul
)

if "%opcao%"=="4" (
    echo.
    echo Mostrando TODOS os logs...
    echo.
    docker-compose -f docker-compose.dev.yml logs app_dev
    echo.
    echo Pressione qualquer tecla para fechar...
    pause >nul
)

echo.
echo Fim!
