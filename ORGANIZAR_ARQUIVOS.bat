@echo off
REM ============================================
REM Script: ORGANIZAR_ARQUIVOS.bat
REM Descrição: Move arquivos antigos/perdidos para docs/diversos
REM ============================================

echo ============================================
echo ORGANIZAR ARQUIVOS - App31
echo ============================================
echo.
echo Este script ira:
echo   1. Criar estrutura docs/diversos/
echo   2. Mover arquivos .py antigos/perdidos
echo   3. Mover arquivos .md de documentacao antiga
echo   4. Mover arquivos .bat de scripts antigos
echo   5. Preservar arquivos essenciais
echo.
echo Deseja continuar? (S/N)
set /p confirmacao=

if /i not "%confirmacao%"=="S" (
    echo Cancelado.
    exit /b
)

echo.
echo Criando estrutura de diretorios...
if not exist "docs\diversos" mkdir "docs\diversos"
if not exist "docs\diversos\scripts_antigos" mkdir "docs\diversos\scripts_antigos"
if not exist "docs\diversos\scripts_antigos\migracoes" mkdir "docs\diversos\scripts_antigos\migracoes"
if not exist "docs\diversos\scripts_antigos\debug_testes" mkdir "docs\diversos\scripts_antigos\debug_testes"
if not exist "docs\diversos\scripts_antigos\setup_config" mkdir "docs\diversos\scripts_antigos\setup_config"
if not exist "docs\diversos\scripts_antigos\verificacao" mkdir "docs\diversos\scripts_antigos\verificacao"
if not exist "docs\diversos\scripts_antigos\temporarios" mkdir "docs\diversos\scripts_antigos\temporarios"
if not exist "docs\diversos\scripts_antigos\manutencao" mkdir "docs\diversos\scripts_antigos\manutencao"
if not exist "docs\diversos\scripts_antigos\criacao_tabelas" mkdir "docs\diversos\scripts_antigos\criacao_tabelas"
if not exist "docs\diversos\scripts_antigos\relatorios_backup" mkdir "docs\diversos\scripts_antigos\relatorios_backup"
if not exist "docs\diversos\documentacao_antiga" mkdir "docs\diversos\documentacao_antiga"
if not exist "docs\diversos\scripts_bat_antigos" mkdir "docs\diversos\scripts_bat_antigos"

echo Estrutura criada!
echo.

echo Movendo scripts de migracao...
move /Y apply_modefin_migration.py "docs\diversos\scripts_antigos\migracoes\" 2>nul
move /Y apply_my_work_migration.py "docs\diversos\scripts_antigos\migracoes\" 2>nul
move /Y apply_ui_catalog_migration.py "docs\diversos\scripts_antigos\migracoes\" 2>nul
move /Y apply_urgent_fixes.py "docs\diversos\scripts_antigos\migracoes\" 2>nul
move /Y apply_user_employee_link_migration.py "docs\diversos\scripts_antigos\migracoes\" 2>nul
move /Y migracao_segura.py "docs\diversos\scripts_antigos\migracoes\" 2>nul
move /Y migration_simples.py "docs\diversos\scripts_antigos\migracoes\" 2>nul
move /Y migrar_dados_grv.py "docs\diversos\scripts_antigos\migracoes\" 2>nul
move /Y atualizar_plan_mode_manual.py "docs\diversos\scripts_antigos\migracoes\" 2>nul

echo Movendo scripts de debug/teste...
move /Y debug_*.py "docs\diversos\scripts_antigos\debug_testes\" 2>nul
move /Y test_*.py "docs\diversos\scripts_antigos\debug_testes\" 2>nul
move /Y testar_*.py "docs\diversos\scripts_antigos\debug_testes\" 2>nul
move /Y teste_*.py "docs\diversos\scripts_antigos\debug_testes\" 2>nul
move /Y testpy.py "docs\diversos\scripts_antigos\debug_testes\" 2>nul

echo Movendo scripts de verificacao...
move /Y check_*.py "docs\diversos\scripts_antigos\verificacao\" 2>nul
move /Y verificar_*.py "docs\diversos\scripts_antigos\verificacao\" 2>nul
move /Y verify_*.py "docs\diversos\scripts_antigos\verificacao\" 2>nul

echo Movendo scripts temporarios...
move /Y temp_*.py "docs\diversos\scripts_antigos\temporarios\" 2>nul
move /Y tmp_*.py "docs\diversos\scripts_antigos\temporarios\" 2>nul

echo Movendo scripts de setup/configuracao...
move /Y setup_*.py "docs\diversos\scripts_antigos\setup_config\" 2>nul
move /Y setup.py "docs\diversos\scripts_antigos\setup_config\" 2>nul
move /Y configure_*.py "docs\diversos\scripts_antigos\setup_config\" 2>nul
move /Y integrate_logs_system.py "docs\diversos\scripts_antigos\setup_config\" 2>nul
move /Y install_dependencies.py "docs\diversos\scripts_antigos\setup_config\" 2>nul

echo Movendo scripts de manutencao...
move /Y fix_*.py "docs\diversos\scripts_antigos\manutencao\" 2>nul
move /Y corrigir_*.py "docs\diversos\scripts_antigos\manutencao\" 2>nul
move /Y update_*.py "docs\diversos\scripts_antigos\manutencao\" 2>nul
move /Y adicionar_*.py "docs\diversos\scripts_antigos\manutencao\" 2>nul
move /Y limpar_*.py "docs\diversos\scripts_antigos\manutencao\" 2>nul
move /Y link_*.py "docs\diversos\scripts_antigos\manutencao\" 2>nul
move /Y print_*.py "docs\diversos\scripts_antigos\manutencao\" 2>nul

echo Movendo scripts de criacao de tabelas...
move /Y create_*.py "docs\diversos\scripts_antigos\criacao_tabelas\" 2>nul
move /Y criar_*.py "docs\diversos\scripts_antigos\criacao_tabelas\" 2>nul

echo Movendo scripts de relatorios/backup...
move /Y exemplo_relatorio_*.py "docs\diversos\scripts_antigos\relatorios_backup\" 2>nul
move /Y final_report.py "docs\diversos\scripts_antigos\relatorios_backup\" 2>nul
move /Y gerar_relatorio_*.py "docs\diversos\scripts_antigos\relatorios_backup\" 2>nul
move /Y criar_backup.py "docs\diversos\scripts_antigos\relatorios_backup\" 2>nul
REM Manter backup_automatico.py e backup_to_s3.py se ainda usa

echo Movendo outros scripts...
move /Y buscar_*.py "docs\diversos\scripts_antigos\" 2>nul
move /Y compare_*.py "docs\diversos\scripts_antigos\" 2>nul
move /Y snippet.py "docs\diversos\scripts_antigos\" 2>nul
move /Y SCRIPT_*.py "docs\diversos\scripts_antigos\" 2>nul

echo.
echo Movendo documentacao antiga...
REM Arquivos que comecam com _
for %%f in (_*.md) do move /Y "%%f" "docs\diversos\documentacao_antiga\" 2>nul
REM Arquivos de correcao/implementacao antiga
move /Y *_CORRECAO_*.md "docs\diversos\documentacao_antiga\" 2>nul
move /Y *_IMPLEMENTACAO_*.md "docs\diversos\documentacao_antiga\" 2>nul
move /Y *_RESUMO_*.md "docs\diversos\documentacao_antiga\" 2>nul
move /Y *_ATUALIZACAO_*.md "docs\diversos\documentacao_antiga\" 2>nul
move /Y *_MIGRACAO_*.md "docs\diversos\documentacao_antiga\" 2>nul
move /Y *_TESTE_*.md "docs\diversos\documentacao_antiga\" 2>nul
move /Y *_GUIA_*.md "docs\diversos\documentacao_antiga\" 2>nul
move /Y *_COMO_*.md "docs\diversos\documentacao_antiga\" 2>nul

echo Movendo scripts .bat antigos...
for %%f in (*.bat) do (
    if not "%%f"=="ORGANIZAR_ARQUIVOS.bat" (
        if not "%%f"=="PROMOVER_DEV_PARA_PROD.bat" (
            if not "%%f"=="CRIAR_APP32.bat" (
                move /Y "%%f" "docs\diversos\scripts_bat_antigos\" 2>nul
            )
        )
    )
)

echo.
echo ============================================
echo ORGANIZACAO CONCLUIDA!
echo ============================================
echo.
echo Arquivos movidos para:
echo   docs\diversos\scripts_antigos\
echo   docs\diversos\documentacao_antiga\
echo   docs\diversos\scripts_bat_antigos\
echo.
echo Arquivos mantidos na raiz:
echo   - app_pev.py
echo   - config.py
echo   - config_database.py
echo   - config_dev.py
echo   - config_prod.py
echo   - status_sistema.py
echo   - relatorios_server.py
echo   - routine_scheduler.py
echo   - backup_automatico.py
echo   - backup_to_s3.py
echo.
pause





