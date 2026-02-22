@echo off
echo ================================================================================
echo   VERIFICAR SE O DOCKER REINICIOU CORRETAMENTE
echo ================================================================================
echo.
echo Checando status dos containers...
echo.

docker-compose -f docker-compose.dev.yml ps

echo.
echo ================================================================================
echo.
echo Se o container app_dev estiver "Up", significa que esta rodando.
echo.
echo Para ver os logs e confirmar que o codigo novo foi carregado:
echo.
pause

echo.
echo Mostrando ultimas 30 linhas dos logs...
echo Procure por linhas com DEBUG, emojis ou timestamps recentes
echo.
echo ================================================================================
echo.

docker-compose -f docker-compose.dev.yml logs --tail=30 app_dev

echo.
echo ================================================================================
echo   FIM
echo ================================================================================
echo.
echo Se voce viu linhas recentes nos logs, o Docker foi reiniciado!
echo.
pause

