@echo off
echo ================================================================================
echo   TESTE FINAL - Verificar se dados aparecem
echo ================================================================================
echo.
echo Por favor, siga estes passos:
echo.
echo 1. Abra o navegador em:
echo    http://127.0.0.1:5003/pev/implantacao/modelo/modelagem-financeira?plan_id=6
echo.
echo 2. Abra o Console (F12)
echo.
echo 3. Cole este codigo e pressione Enter:
echo.
echo    fetch('/pev/api/implantacao/6/products/totals').then(r =^> r.json()).then(data =^> { console.log('=== TESTE ==='); console.log('Totals:', data.totals); console.log('Tem faturamento?', 'faturamento' in (data.totals ^|^| {})); console.log('Faturamento:', data.totals?.faturamento); });
echo.
echo 4. Verifique o resultado:
echo.
echo    SE APARECER:
echo      Tem faturamento? true
echo      Faturamento: {valor: 1200000, percentual: 100}
echo    ==^> FUNCIONOU! Os dados devem aparecer na tela agora!
echo.
echo    SE APARECER:
echo      Tem faturamento? false
echo      Faturamento: undefined
echo    ==^> Ainda nao funcionou. Me avise!
echo.
echo ================================================================================
pause

