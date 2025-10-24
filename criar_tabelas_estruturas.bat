@echo off
echo ============================================
echo   CRIANDO TABELAS DE ESTRUTURAS
echo ============================================
echo.

echo Executando script SQL no PostgreSQL...
docker exec -i gestaoversus_db_dev psql -U postgres -d bd_app_versus_dev < criar_tabelas_estruturas.sql

echo.
echo ============================================
echo   VERIFICANDO TABELAS CRIADAS
echo ============================================
echo.

docker exec -i gestaoversus_db_dev psql -U postgres -d bd_app_versus_dev -c "\dt plan_structures"
docker exec -i gestaoversus_db_dev psql -U postgres -d bd_app_versus_dev -c "\dt plan_structure_installments"

echo.
echo ============================================
echo   PRONTO!
echo ============================================
echo.
echo As tabelas foram criadas com sucesso.
echo Agora voce pode testar novamente a criacao de estruturas.
echo.
pause

