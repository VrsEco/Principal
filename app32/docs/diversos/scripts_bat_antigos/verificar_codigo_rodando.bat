@echo off
echo ================================================================================
echo   VERIFICAR CODIGO QUE ESTA RODANDO NO DOCKER
echo ================================================================================
echo.
echo Vamos entrar no container e verificar o arquivo products_service.py
echo.
pause

echo.
echo Executando comando dentro do container...
echo.
docker exec -it gestaoversus_app_dev_1 cat /app/modules/pev/products_service.py 2>nul | findstr /N "def calculate_totals" /C:"faturamento" /C:"custos_variaveis"

if errorlevel 1 (
    echo Tentando outro nome de container...
    docker exec -it app31-app_dev-1 cat /app/modules/pev/products_service.py 2>nul | findstr /N "def calculate_totals" /C:"faturamento" /C:"custos_variaveis"
)

if errorlevel 1 (
    echo Tentando outro nome...
    docker exec -it app31_app_dev_1 cat /app/modules/pev/products_service.py 2>nul | findstr /N "def calculate_totals" /C:"faturamento" /C:"custos_variaveis"
)

echo.
echo ================================================================================
echo.
echo Se aparecer linhas com "faturamento", "custos_variaveis", o codigo esta correto.
echo Se NAO aparecer nada, o Docker esta com codigo antigo!
echo.
pause

