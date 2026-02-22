@echo off
echo ============================================
echo   VERIFICANDO SE PROJETO 49 FOI CRIADO
echo ============================================
echo.

docker cp verificar_projeto_49.py gestaoversus_app_dev:/app/verificar.py
docker exec -it gestaoversus_app_dev python verificar.py

echo.
pause

