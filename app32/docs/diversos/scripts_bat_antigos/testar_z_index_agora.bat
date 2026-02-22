@echo off
chcp 65001 > nul
cls
echo ========================================
echo CORRECAO Z-INDEX - MODAL CAPITAL DE GIRO
echo ========================================
echo.

echo Problema identificado: Modal estava escondido atras de outros elementos
echo Solucao aplicada: Z-index aumentado para 999999 !important
echo.
echo ========================================
echo EXECUTANDO TESTE
echo ========================================
echo.

echo [1/2] Aguardando 2 segundos...
timeout /t 2 /nobreak > nul

echo.
echo [2/2] Abrindo navegador...
echo.

start http://localhost:5003/pev/implantacao/modelo/modefin?plan_id=6

echo.
echo ========================================
echo INSTRUCOES DE TESTE
echo ========================================
echo.
echo 1. Quando a pagina abrir, pressione: Ctrl + F5
echo    (Isso forca o reload e limpa o cache CSS)
echo.
echo 2. Pressione F12 para abrir o Console
echo.
echo 3. Clique no botao: + Capital de Giro
echo.
echo 4. Verifique se o modal APARECE na tela:
echo    - Fundo escuro cobrindo a pagina
echo    - Card branco centralizado
echo    - Formulario visivel
echo.
echo 5. No Console, deve aparecer:
echo    [Modal] Z-index aplicado: 999999
echo    [Modal] Display: flex
echo    [Modal] Position: fixed
echo.
echo ========================================
echo TESTES COMPLETOS
echo ========================================
echo.
echo Se o modal aparecer:
echo   [X] Preencha os campos
echo   [X] Clique em Salvar
echo   [X] Verifique se aparece na tabela
echo.
echo ========================================
echo.
echo Navegador aberto! Execute os testes acima.
echo.
echo Se o modal NAO aparecer, veja: CORRECAO_Z_INDEX_MODAL.md
echo.
pause

