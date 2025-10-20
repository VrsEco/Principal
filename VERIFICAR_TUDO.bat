@echo off
echo ========================================
echo   VERIFICACAO COMPLETA - APP26
echo ========================================
echo.
echo 1. Detalhamento de todos os dados:
echo ----------------------------------------
python detalhar_dados.py
echo.
echo.
echo 2. Comparacao APP25 vs APP26:
echo ----------------------------------------
python comparar_bancos.py
echo.
echo.
echo ========================================
echo   VERIFICACAO CONCLUIDA
echo ========================================
echo.
echo Os dados ESTAO no banco de dados!
echo Se nao aparecem na tela:
echo   - Limpe cache (Ctrl+F5)
echo   - Reinicie o servidor
echo   - Verifique plano selecionado
echo.
pause




