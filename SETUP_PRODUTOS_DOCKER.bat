@echo off
echo ========================================
echo SETUP COMPLETO - Cadastro de Produtos
echo Ambiente Docker
echo ========================================
echo.

echo [1/3] Copiando migration para o container...
docker cp migrations\create_plan_products_table.sql gestaoversus_db_dev:/tmp/

IF %ERRORLEVEL% NEQ 0 (
    echo ❌ Erro ao copiar arquivo
    pause
    exit /b 1
)

echo ✅ Arquivo copiado
echo.

echo [2/3] Aplicando migration no banco de dados...
docker exec gestaoversus_db_dev psql -U postgres -d bd_app_versus_dev -f /tmp/create_plan_products_table.sql

IF %ERRORLEVEL% NEQ 0 (
    echo ❌ Erro ao aplicar migration
    pause
    exit /b 1
)

echo ✅ Migration aplicada
echo.

echo [3/3] Verificando tabela criada...
docker exec gestaoversus_db_dev psql -U postgres -d bd_app_versus_dev -c "\d plan_products"

echo.
echo ========================================
echo ✅ SETUP CONCLUÍDO COM SUCESSO!
echo ========================================
echo.
echo Próximos passos:
echo 1. Container já está rodando ✅
echo 2. Tabela criada ✅
echo 3. Acesse: http://localhost:5003/pev/dashboard
echo 4. Selecione um planejamento
echo 5. Clique em "📦 Cadastro de Produtos"
echo.
echo ========================================

pause

