@echo off
REM ============================================================================
REM SCRIPT: Teste de Totalizados de Produtos
REM DATA: 27/10/2025
REM DESCRIÇÃO: Testa se o endpoint está retornando os totalizados corretamente
REM ============================================================================

echo.
echo ========================================
echo   TESTE: TOTALIZADOS DE PRODUTOS
echo ========================================
echo.
echo Este script testa o endpoint de totalizados
echo.

echo [INFO] Endpoint: GET /pev/api/implantacao/8/products/totals
echo.

echo [TESTE] Fazendo requisicao...
echo.

curl -X GET "http://127.0.0.1:5003/pev/api/implantacao/8/products/totals" ^
  -H "Content-Type: application/json" ^
  --cookie-jar cookies.txt ^
  --cookie cookies.txt

echo.
echo.
echo ========================================
echo   VALORES ESPERADOS (FALLBACK_PRODUCTS)
echo ========================================
echo.
echo Produto: Projetos Marceneiros
echo - Preco: R$ 10.000,00
echo - Custos Variaveis: 32%% (R$ 3.200,00)
echo - Despesas Variaveis: 0%% (R$ 0,00)
echo - Meta Market Share: 120 unidades/mes (20%%)
echo.
echo TOTALIZADOS ESPERADOS:
echo - Faturamento: R$ 1.200.000,00 (100%%)
echo   (10.000 x 120 = 1.200.000)
echo.
echo - Custos Variaveis: R$ 384.000,00 (32%%)
echo   (3.200 x 120 = 384.000)
echo.
echo - Despesas Variaveis: R$ 0,00 (0%%)
echo   (0 x 120 = 0)
echo.
echo - Margem de Contribuicao: R$ 816.000,00 (68%%)
echo   (6.800 x 120 = 816.000)
echo.
echo ========================================
echo.

pause

