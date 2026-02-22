@echo off
echo ================================================================================
echo   TESTAR PAGINA AGORA
echo ================================================================================
echo.
echo As mudancas ja foram aplicadas (modo desenvolvimento com volumes).
echo.
echo Siga estes passos:
echo.
echo 1. Recarregue a pagina no navegador (F5 ou Ctrl+R)
echo    http://127.0.0.1:5003/pev/implantacao/modelo/modelagem-financeira?plan_id=6
echo.
echo 2. Verifique se a pagina carrega SEM erro "Internal Server Error"
echo.
echo 3. Verifique se os valores aparecem nos cards:
echo.
echo    Margem de Contribuicao:
echo      - Faturamento: R$ 1.200.000,00
echo      - Custos Variaveis: R$ 384.000,00
echo      - Margem: R$ 816.000,00
echo.
echo    Custos e Despesas Fixas:
echo      - Custos Fixos: R$ 65.400,00
echo      - Despesas Fixas: R$ 8.800,00
echo      - Resultado Operacional: R$ 741.800,00
echo.
echo 4. Se ainda der erro, execute: docker-compose restart app
echo.
echo ================================================================================
pause

