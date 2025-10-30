@echo off
chcp 65001 > nul
echo ========================================
echo TESTAR MODAL DE CAPITAL DE GIRO
echo ========================================
echo.

echo [1/3] Reiniciando Docker...
docker-compose restart app

echo.
echo [2/3] Aguardando 10 segundos para garantir que reiniciou...
timeout /t 10 /nobreak > nul

echo.
echo [3/3] Abrindo navegador e página de debug...
echo.

echo ========================================
echo INSTRUÇÕES:
echo ========================================
echo.
echo 1. Pressione F12 para abrir o Console
echo 2. Verifique se aparecem os logs:
echo    [ModeFin] Iniciando...
echo    [ModeFin] Renderização completa!
echo    [ModeFin] Funções expostas no window: ...
echo.
echo 3. Verifique se todas as funções aparecem como "function"
echo.
echo 4. Clique no botão: + Capital de Giro
echo.
echo 5. Verifique se aparecem logs:
echo    [Modal] Abrindo modal...
echo    [Modal] Modal aberto com sucesso!
echo.
echo 6. Se o modal abrir, preencha os campos:
echo    - Tipo: Caixa
echo    - Data: 01/05/2026
echo    - Valor: 100000
echo    - Descrição: Teste inicial
echo.
echo 7. Clique em SALVAR
echo.
echo ========================================
echo.
echo Abrindo navegador em 3 segundos...
timeout /t 3 /nobreak > nul

start http://localhost:5000/pev/implantacao/modelo/modefin?plan_id=1

echo.
echo ========================================
echo NAVEGADOR ABERTO!
echo ========================================
echo.
echo Se o modal não abrir, veja: CORRIGIR_BOTAO_CAPITAL_GIRO.md
echo.
pause

