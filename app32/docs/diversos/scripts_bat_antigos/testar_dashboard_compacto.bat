@echo off
chcp 65001 > nul
title Testar Dashboard Compacto do PEV

echo.
echo ════════════════════════════════════════════════════════════
echo  TESTANDO DASHBOARD COMPACTO DO PEV
echo ════════════════════════════════════════════════════════════
echo.
echo  ✓ Novo layout criado em: templates/plan_selector_compact.html
echo  ✓ Rota atualizada em: modules/pev/__init__.py
echo.
echo  CARACTERÍSTICAS DO NOVO LAYOUT:
echo  • Layout em 2 colunas lado a lado
echo  • Manifesto de planejamento compactado
echo  • Hub de projetos otimizado
echo  • Sem necessidade de rolagem vertical
echo  • Design responsivo para mobile
echo.
echo ════════════════════════════════════════════════════════════
echo  PRÓXIMOS PASSOS:
echo ════════════════════════════════════════════════════════════
echo.
echo  1. Acesse: http://127.0.0.1:5003/pev/dashboard
echo  2. Verifique o novo layout compacto
echo  3. Teste a criação de empresas e planejamentos
echo  4. Teste em diferentes resoluções de tela
echo.
echo  ABRINDO NAVEGADOR...
echo.
timeout /t 2 /nobreak > nul

start http://127.0.0.1:5003/pev/dashboard

echo.
echo  ✓ Navegador aberto!
echo  ✓ Aguarde o carregamento da página...
echo.
echo  Pressione qualquer tecla para fechar esta janela...
pause > nul

