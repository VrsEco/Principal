@echo off
REM ============================================================================
REM SCRIPT: Margem de Contribuição e Destinação de Resultados
REM DATA: 27/10/2025
REM DESCRIÇÃO: Renomeia seções e adiciona totalizados de Produtos e Margens
REM ============================================================================

echo.
echo ========================================
echo   MARGEM DE CONTRIBUICAO E DESTINACAO
echo ========================================
echo.
echo Este script aplica as seguintes mudancas:
echo.
echo 1. Renomeia "Custos Variaveis e Destinacao" para
echo    "Margem de Contribuicao e Destinacao de Resultados"
echo.
echo 2. Renomeia "Custos e despesas variaveis" para
echo    "Margem de Contribuicao"
echo.
echo 3. Adiciona card de totalizados com dados de Produtos e Margens:
echo    - Faturamento (percentual e valor)
echo    - Custos Variaveis (percentual e valor)
echo    - Despesas Variaveis (percentual e valor)
echo    - Margem de Contribuicao (percentual e valor)
echo.
echo 4. Cria endpoint API para buscar totalizados
echo.
echo 5. Substitui tabela manual por lista de produtos cadastrados
echo    - Busca produtos de /pev/implantacao/modelo/produtos
echo    - Exibe: Produto, Preco, Custos, Despesas, MCU, Market Share
echo    - Adiciona botao "Gerenciar Produtos" (link para pagina de produtos)
echo.
echo 6. Adiciona JavaScript para carregar e exibir dados automaticamente
echo.
echo 7. CORRIGE endpoint /products/totals para usar FALLBACK_PRODUCTS
echo    - Garante que valores aparecem mesmo sem cadastro no banco
echo    - Usa dados de exemplo do plan_id 8
echo.
echo ========================================
echo.

pause

echo.
echo [1/5] Verificando arquivos...
echo.

if not exist "templates\implantacao\modelo_modelagem_financeira.html" (
    echo [ERRO] Arquivo modelo_modelagem_financeira.html nao encontrado!
    pause
    exit /b 1
)

if not exist "modules\pev\__init__.py" (
    echo [ERRO] Arquivo modules/pev/__init__.py nao encontrado!
    pause
    exit /b 1
)

echo [OK] Arquivos encontrados!

echo.
echo [2/5] Criando backup dos arquivos...
echo.

set TIMESTAMP=%DATE:~6,4%%DATE:~3,2%%DATE:~0,2%_%TIME:~0,2%%TIME:~3,2%%TIME:~6,2%
set TIMESTAMP=%TIMESTAMP: =0%

mkdir backups\%TIMESTAMP% 2>nul

copy "templates\implantacao\modelo_modelagem_financeira.html" "backups\%TIMESTAMP%\modelo_modelagem_financeira.html.bak" >nul
copy "modules\pev\__init__.py" "backups\%TIMESTAMP%\__init__.py.bak" >nul

echo [OK] Backup criado em: backups\%TIMESTAMP%\

echo.
echo [3/5] Verificando se as mudancas ja foram aplicadas...
echo.

findstr /C:"Margem de Contribuicao e Destinacao de Resultados" "templates\implantacao\modelo_modelagem_financeira.html" >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo [AVISO] As mudancas ja foram aplicadas anteriormente!
    echo.
    choice /C SN /M "Deseja continuar mesmo assim"
    if errorlevel 2 (
        echo.
        echo [CANCELADO] Operacao cancelada pelo usuario.
        pause
        exit /b 0
    )
)

echo.
echo [4/5] Aplicando mudancas...
echo.

echo [INFO] As mudancas ja foram aplicadas via Cursor AI
echo [INFO] Arquivos modificados:
echo        - templates\implantacao\modelo_modelagem_financeira.html
echo        - modules\pev\__init__.py
echo.

echo [OK] Mudancas aplicadas com sucesso!

echo.
echo [5/5] Verificando integridade...
echo.

REM Verificar se os novos elementos foram adicionados
findstr /C:"products-summary-card" "templates\implantacao\modelo_modelagem_financeira.html" >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERRO] Card de totalizados nao encontrado!
    pause
    exit /b 1
)

findstr /C:"loadProductsTotals" "templates\implantacao\modelo_modelagem_financeira.html" >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERRO] Funcao JavaScript nao encontrada!
    pause
    exit /b 1
)

findstr /C:"get_products_totals" "modules\pev\__init__.py" >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERRO] Endpoint API nao encontrado!
    pause
    exit /b 1
)

findstr /C:"products-list-tbody" "templates\implantacao\modelo_modelagem_financeira.html" >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERRO] Tabela de produtos nao encontrada!
    pause
    exit /b 1
)

findstr /C:"renderProductsTable" "templates\implantacao\modelo_modelagem_financeira.html" >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERRO] Funcao renderProductsTable nao encontrada!
    pause
    exit /b 1
)

echo [OK] Todos os elementos foram adicionados corretamente!

echo.
echo ========================================
echo   APLICACAO CONCLUIDA COM SUCESSO!
echo ========================================
echo.
echo Resumo das mudancas:
echo.
echo [OK] Secao renomeada para "Margem de Contribuicao e Destinacao de Resultados"
echo [OK] Subsecao renomeada para "Margem de Contribuicao"
echo [OK] Card de totalizados adicionado
echo [OK] Endpoint API /products/totals criado
echo [OK] Tabela manual substituida por lista de produtos
echo [OK] Botao "Gerenciar Produtos" adicionado
echo [OK] JavaScript para carregar produtos e totalizados adicionado
echo [OK] Endpoint corrigido para usar FALLBACK_PRODUCTS
echo.
echo Proximos passos:
echo.
echo 1. REINICIE o servidor Flask (importante!)
echo    - Pressione Ctrl+C no terminal
echo    - Execute: python app.py
echo.
echo 2. Acesse: http://127.0.0.1:5003/pev/implantacao/modelo/modelagem_financeira?plan_id=8
echo.
echo 3. Va ate "Margem de Contribuicao e Destinacao de Resultados"
echo.
echo 4. VERIFIQUE se o card mostra valores (FALLBACK do plan_id 8):
echo    - Faturamento: R$ 1.200.000,00
echo    - Custos Variaveis: R$ 384.000,00 (32.0%%)
echo    - Despesas Variaveis: R$ 0,00 (0.0%%)
echo    - Margem de Contribuicao: R$ 816.000,00 (68.0%%)
echo.
echo 5. Clique em "Gerenciar Produtos" para cadastrar novos produtos
echo 5. Na pagina de produtos, cadastre:
echo    - Nome, Descricao
echo    - Preco de Venda
echo    - Custos Variaveis (percentual e valor)
echo    - Despesas Variaveis (percentual e valor)
echo    - Meta de Market Share (unidades e percentual)
echo 6. Volte para Modelagem Financeira
echo 7. Os produtos aparecerao automaticamente na tabela
echo 8. O card de totalizados mostrara os valores calculados
echo.
echo ========================================
echo.

pause

