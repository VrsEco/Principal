@echo off
echo ========================================
echo CORRECAO - Erro ao Salvar Investimento
echo ========================================
echo.
echo Este script vai:
echo 1. Criar as tabelas de investimento no banco
echo 2. Popular os itens de investimento padrao
echo 3. Reiniciar o servidor
echo.
pause

echo.
echo [1/3] Criando tabelas de investimento...
python -c "from config_database import get_db; db = get_db(); db.init_database(); print('Tabelas criadas com sucesso!')"

echo.
echo [2/3] Populando itens de investimento...
python scripts\seed_investment_items.py

echo.
echo [3/3] As correcoes foram aplicadas!
echo.
echo Agora reinicie o servidor com: python app_pev.py
echo.
echo Teste em: http://127.0.0.1:5003/pev/implantacao/modelo/modelagem-financeira?plan_id=8
echo.
pause

