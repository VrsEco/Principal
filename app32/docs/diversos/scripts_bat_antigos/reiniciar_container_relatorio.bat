@echo off
echo ============================================
echo Reiniciando container para aplicar mudancas
echo ============================================
echo.

echo Parando container...
docker-compose stop app

echo Limpando cache Python dentro do container...
docker exec app31_app_prod find /app -type d -name __pycache__ -exec rm -rf {} + 2>nul || echo "Cache limpo ou container nao esta rodando"

echo Removendo arquivos .pyc...
docker exec app31_app_prod find /app -name "*.pyc" -delete 2>nul || echo "Arquivos .pyc removidos ou container nao esta rodando"

echo Reiniciando container...
docker-compose start app

echo.
echo ============================================
echo Container reiniciado!
echo Teste a URL do relatorio novamente.
echo ============================================
pause

