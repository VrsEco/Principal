# 📊 Análise de Arquivos Python na Raiz

## ✅ **ARQUIVOS ESSENCIAIS** (NÃO MOVER)

Estes arquivos são **necessários** para o sistema funcionar:

1. **`app_pev.py`** - Aplicação principal Flask (usado pelo Dockerfile)
2. **`config.py`** - Configuração do Flask (importado por app_pev.py)
3. **`config_database.py`** - Configuração do banco (importado por app_pev.py)
4. **`config_dev.py`** - Configuração de desenvolvimento (opcional mas útil)
5. **`config_prod.py`** - Configuração de produção (opcional mas útil)

---

## ⚠️ **ARQUIVOS ÚTEIS** (MANTER mas podem ser organizados)

Scripts que podem ser úteis ocasionalmente:

### Relatórios/Servidores
- **`relatorios_server.py`** - Servidor de relatórios (pode ser usado)
- **`routine_scheduler.py`** - Agendador de rotinas (pode ser usado)

### Status/Verificação
- **`status_sistema.py`** - Verifica status do sistema (útil para debug)

---

## 🗑️ **ARQUIVOS ANTIGOS/PERDIDOS** (PODE MOVER para docs/diversos)

### Scripts de Migração (já executados)
- `apply_modefin_migration.py`
- `apply_my_work_migration.py`
- `apply_ui_catalog_migration.py`
- `apply_urgent_fixes.py`
- `apply_user_employee_link_migration.py`
- `migracao_segura.py`
- `migration_simples.py`
- `migrar_dados_grv.py`
- `atualizar_plan_mode_manual.py`

### Scripts de Debug/Teste (temporários)
- `debug_class_structure.py`
- `debug_portfolio_delete.py`
- `debug_retrieve.py`
- `debug_save.py`
- `debug_specific_portfolio.py`
- `test_api_meeting_response.py`
- `test_api_response.py`
- `test_dict_conversion.py`
- `test_final_complete.py`
- `test_indicator_group_create.py`
- `test_indicators_api.py`
- `test_investment_api.py`
- `test_meeting_json_fields.py`
- `test_meetings_page.py`
- `test_meetings_route.py`
- `test_placeholder_conversion.py`
- `testar_api_estruturas.py`
- `testar_conexao.py`
- `testar_criacao_plano.py`
- `testar_plano_6.py`
- `testar_rota_nova.py`
- `testar_sistema_logs.py`
- `testar_todos_planos.py`
- `teste_conexao_rapido.py`
- `teste_final_completo.py`
- `teste_gerador_relatorio.py`
- `teste_plano.py`
- `teste_relatorio_novo.py`
- `teste_relatorio_profissional.py`
- `testpy.py`

### Scripts de Verificação (check/debug)
- `check_class_closure.py`
- `check_drivers_table.py`
- `check_indicators.py`
- `check_meeting_tables.py`
- `check_meetings_data.py`
- `check_okr_data.py`
- `check_project_portfolio_relation.py`
- `check_remaining_portfolios.py`
- `check_specific_meeting.py`
- `check_user_employee_link.py`
- `verificar_conexao_postgresql.py`
- `verificar_config.py`
- `verificar_favicon.py`
- `verificar_meus_dados.py`
- `verificar_novas_rotas.py`
- `verificar_projeto_49.py`
- `verificar_rotas_estruturas.py`
- `verificar_rotinas_db.py`
- `verificar_servidor.py`
- `verify_method.py`
- `verify_postgresql_migration.py`

### Scripts Temporários (temp/tmp)
- `temp_check_db.py`
- `temp_insert_product.py`
- `temp_orig.py`
- `temp_print_nav.py`
- `temp_query_plans.py`
- `temp_search.py`
- `tmp_apply_patch.py`
- `tmp_check.py`
- `tmp_inst_schema.py`
- `tmp_probe.py`

### Scripts de Comparação (já usados)
- `compare_all_tables.py`
- `compare_meeting_tables.py`

### Scripts de Busca/Debug
- `buscar_planejamentos.py`
- `buscar_planejamentos_rapido.py`

### Scripts de Setup/Configuração Inicial (já executados)
- `configure_integrations.py` - Configuração inicial (já feito)
- `configure_openai.py` - Configuração inicial (já feito)
- `setup.py` - Setup inicial (já feito)
- `setup_company_agent.py` - Setup inicial (já feito)
- `setup_dependencies.py` - Setup inicial (já feito)
- `setup_report_system.py` - Setup inicial (já feito)
- `setup_user_logs_system.py` - Setup inicial (já feito)
- `integrate_logs_system.py` - Integração inicial (já feito)

### Scripts de Correção/Manutenção Antiga
- `adicionar_rodape_model7.py`
- `limpar_rodape_model7.py`
- `corrigir_encoding_completo.py`
- `fix_class_structure.py`
- `fix_meeting_agenda_items.py`
- `link_users_to_employees.py`
- `print_pop_block.py`
- `update_build_sections.py`
- `update_company_coverage.py`
- `update_db.py`
- `update_placeholder_scheduler.py`

### Scripts de Criação de Tabelas (já executados)
- `create_ai_agents_table.py`
- `create_company_projects_table.py`
- `create_drivers_table.py`
- `create_missing_tables.py`
- `create_portfolios_table.py`
- `create_test_portfolio_with_projects.py`
- `criar_tabela_capital_giro.py`

### Scripts de Backup/Relatório Antigos
- `backup_automatico.py` - Backup (pode manter se ainda usa)
- `backup_to_s3.py` - Backup S3 (pode manter se ainda usa)
- `criar_backup.py` - Backup simples
- `exemplo_relatorio_reunioes.py` - Exemplo antigo
- `final_report.py` - Relatório antigo
- `gerar_relatorio_agora.py` - Relatório antigo
- `gerar_relatorio_save_water.py` - Relatório antigo

### Scripts Utilitários Diversos
- `install_dependencies.py` - Instalação (já feito)
- `snippet.py` - Snippet temporário
- `SCRIPT_ADICIONAR_EMPRESA.py` - Script antigo

---

## 📝 **RECOMENDAÇÃO**

### Manter na Raiz:
```
✅ app_pev.py
✅ config.py
✅ config_database.py
✅ config_dev.py (opcional)
✅ config_prod.py (opcional)
⚠️ status_sistema.py (útil para debug)
⚠️ relatorios_server.py (se ainda usa)
⚠️ routine_scheduler.py (se ainda usa)
```

### Mover para `docs/diversos/scripts_antigos/`:
- Todos os scripts de migração já executados
- Todos os scripts de debug/teste
- Todos os scripts temporários (temp/tmp)
- Todos os scripts de verificação (check/verify)
- Scripts de setup já executados
- Scripts de correção/manutenção antiga
- Scripts de criação de tabelas já executados

---

**Total de arquivos .py na raiz:** ~110  
**Arquivos essenciais:** ~5-8  
**Arquivos para mover:** ~100+







