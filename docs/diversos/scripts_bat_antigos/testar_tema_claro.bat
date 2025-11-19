@echo off
chcp 65001 > nul
title Testar Tema Claro - Dashboard PEV

echo.
echo ════════════════════════════════════════════════════════════
echo  🎨 TESTANDO TEMA CLARO DO DASHBOARD PEV
echo ════════════════════════════════════════════════════════════
echo.
echo  ✓ Tema claro aplicado com sucesso!
echo.
echo  CORES DO TEMA CLARO:
echo  • Azul (#3b82f6) - Botões e destaques
echo  • Amarelo (#d97706) - Estatísticas
echo  • Branco (#ffffff) - Fundo principal
echo  • Azul claro (#dbeafe) - Cards e headers
echo.
echo ════════════════════════════════════════════════════════════
echo  COMO TESTAR:
echo ════════════════════════════════════════════════════════════
echo.
echo  1. O navegador abrirá o dashboard
echo  2. No header, localize o seletor de tema (canto superior direito)
echo  3. Selecione: "Tema Azul/Branco/Amarelo"
echo  4. Veja a transformação instantânea!
echo.
echo  COMPONENTES PARA VERIFICAR:
echo  ✓ Fundo geral branco/claro
echo  ✓ Header com azul claro
echo  ✓ Cards do manifesto em azul
echo  ✓ Resumo com fundo amarelo
echo  ✓ Botões azuis
echo  ✓ Modais com fundo claro
echo.
echo ════════════════════════════════════════════════════════════
echo  ABRINDO NAVEGADOR...
echo ════════════════════════════════════════════════════════════
echo.
timeout /t 2 /nobreak > nul

start http://127.0.0.1:5003/pev/dashboard

echo.
echo  ✓ Navegador aberto!
echo  ✓ Aguarde o carregamento...
echo  ✓ Não esqueça de selecionar o tema no header!
echo.
echo  📖 Documentação completa: TEMA_CLARO_DASHBOARD_APLICADO.md
echo.
echo  Pressione qualquer tecla para fechar...
pause > nul

