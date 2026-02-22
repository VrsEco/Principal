@echo off
echo ================================================================================
echo   TESTAR API DE PRODUTOS
echo ================================================================================
echo.
echo Este script vai testar diretamente a API de produtos
echo.
pause

echo.
echo [1] Testando GET /api/implantacao/6/products
echo.
curl -s http://127.0.0.1:5003/pev/api/implantacao/6/products

echo.
echo.
echo ================================================================================
echo.
echo [2] Testando GET /api/implantacao/6/products/totals
echo.
curl -s http://127.0.0.1:5003/pev/api/implantacao/6/products/totals

echo.
echo.
echo ================================================================================
echo.
echo [3] Testando GET /api/implantacao/6/structures/fixed-costs-summary
echo.
curl -s http://127.0.0.1:5003/pev/api/implantacao/6/structures/fixed-costs-summary

echo.
echo.
echo ================================================================================
echo   FIM DO TESTE
echo ================================================================================
echo.
pause

