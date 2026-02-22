@echo off
echo ============================================
echo   MIGRATION: Modelagem Financeira
echo   Criando tabelas de modelagem financeira
echo ============================================
echo.

echo Aplicando migration 1/2: Criar tabelas...
docker exec -i gestaoversus_db_dev psql -U postgres -d bd_app_versus_dev < migrations/create_finance_tables.sql

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ❌ ERRO ao criar tabelas!
    echo.
    goto erro
)

echo.
echo Aplicando migration 2/2: Adicionar campo notes...
docker exec -i gestaoversus_db_dev psql -U postgres -d bd_app_versus_dev < migrations/add_notes_to_finance_metrics.sql

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ⚠️ Aviso: Erro ao adicionar campo notes (pode já existir)
    echo.
)

echo.
echo ============================================
echo ✅ MIGRATIONS APLICADAS COM SUCESSO!
echo ============================================
echo.
echo Tabelas criadas:
echo   - plan_finance_premises
echo   - plan_finance_investments
echo   - plan_finance_sources
echo   - plan_finance_business_periods
echo   - plan_finance_business_distribution
echo   - plan_finance_variable_costs
echo   - plan_finance_result_rules
echo   - plan_finance_investor_periods
echo   - plan_finance_metrics
echo.
echo Agora você pode testar a página:
echo   http://127.0.0.1:5003/pev/implantacao/modelo/modelagem-financeira?plan_id=45
echo.
echo (Substitua plan_id=45 por um ID válido!)
echo.
goto fim

:erro
echo Verifique se o container está rodando:
echo   docker ps
echo.
echo Se necessário, inicie os containers:
echo   docker-compose up -d
echo.

:fim
pause

