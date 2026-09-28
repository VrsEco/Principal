# Guia da Feature: Gestão Estratégica — Calendário e Jornadas

## Metadados
- `feature_id`: `calendario_e_jornadas`
- `dominio`: `workload`
- `ramo_menu`: `Gestão Estratégica`
- `caminho_menu`: `Gestão Estratégica > Execução > Calendário e Jornadas`
- `rotas_app`: `/work-journey`, `/calendar`, `/process-routines/analysis`, `/efficiency-analysis`
- `surfaces_permitidas`: `user`, `admin`, `analytics`
- `sensibilidade`: `media`
- `company_id_obrigatorio`: `sim`

## Objetivo
Organizar a jornada de trabalho de cada colaborador (blocos fixos de agenda, regras, eventos de calendário, transferências de bloco e ausências), gerar a agenda diária automaticamente, e analisar capacidade e eficiência da equipe frente aos compromissos reais de rotina, processos, projetos e reuniões.

## Quando usar
- explicar como montar ou consultar o calendário/jornada de um colaborador
- explicar como funciona a geração automática de agenda diária a partir dos blocos e regras
- explicar como solicitar ou aprovar uma transferência de bloco de agenda ou uma ausência
- explicar a análise de capacidade (Análise das Jornadas): quanto da capacidade semanal de um colaborador está comprometida com rotina, projetos, processos e reuniões
- explicar a análise de eficiência da equipe

## Quando não usar
- para gerenciar o conteúdo de processos, projetos ou reuniões em si — features próprias: `gestao_processos_estrutura`/`gestao_processos_execucao`, `gestao_projetos`, `gestao_reunioes`
- fora da surface autorizada

## Entradas esperadas
### Obrigatórias
- `company_id`: escopo do tenant

### Opcionais
- `employee_id`: colaborador específico (gestor pode consultar de outros; colaborador comum só vê a própria jornada/análise)
- `department`: filtro por departamento (ignorado quando o usuário não tem acesso total à empresa)
- `period`: período de referência para relatórios de horas e análises

## Saídas esperadas
- `calendario_e_blocos`: blocos fixos, regras e eventos de calendário do colaborador
- `agenda_diaria`: agenda gerada automaticamente para o dia, com opção de bloqueio/edição
- `analise_de_capacidade`: capacidade semanal vs. compromissos (rotina, projetos, processos, reuniões) e percentual de utilização por colaborador
- `analise_de_eficiencia`: indicadores de eficiência da equipe ou do próprio colaborador

## Como orientar o usuário
1. Acessar **Gestão Estratégica > Execução > Calendário e Jornadas** no menu.
2. Em **Calendário**, consultar ou montar os blocos fixos e regras da jornada; a agenda diária pode ser gerada automaticamente a partir deles.
3. Solicitar transferência de um bloco de agenda ou registrar uma ausência — ambas passam por aprovação.
4. Em **Análise das Jornadas**, consultar quanto da capacidade semanal de cada colaborador está comprometida — útil para identificar sobrecarga.
5. Em **Análise da Eficiência**, consultar indicadores de eficiência da equipe.

## Uso por IA / MCP
**Correção em relação a uma versão anterior deste guia:** existem, sim, tools MCP reais e completas para este domínio — só não estão publicadas no allowlist do `mcp-versus` (piloto OAuth). Elas já rodam nas surfaces internas `user`/`admin`/`analytics` completas (`src/core/mcp_work_journey_tools.py` e `src/core/mcp_work_journey_analytics_tools.py`, registradas em `src/intelligence/tool_catalog.py`), mas o `mcp_surface_registry.py` do piloto não as inclui em nenhum cohort — é o mesmo padrão de gap já identificado e corrigido em `processes`/`meetings`.

Tools já implementadas no domínio `routine` (28 no total; nenhuma exposta em `mcp-versus`):
- **Board e blocos**: `get_work_journey_board_tool`, `list_work_journey_blocks_tool`, `save_work_journey_block_tool`, `delete_work_journey_block_tool`
- **Regras**: `list_work_journey_rules_tool`, `save_work_journey_rule_tool`, `delete_work_journey_rule_tool`
- **Itens e tarefas manuais**: `update_work_journey_item_tool`, `list_work_journey_manual_tasks_tool`, `create_work_journey_manual_task_tool`, `delete_work_journey_manual_task_tool`
- **Transferências e ausências**: `create_work_journey_transfer_request_tool`, `approve_work_journey_transfer_request_tool`, `list_work_journey_transfers_tool`, `create_work_journey_absence_request_tool`, `approve_work_journey_absence_request_tool`, `list_work_journey_absences_tool`
- **Agenda**: `get_work_journey_agenda_tool`, `generate_work_journey_agenda_tool`, `lock_work_journey_agenda_tool`, `unlock_work_journey_agenda_tool`, `move_work_journey_agenda_item_tool`
- **Vínculo rotina↔jornada**: `list_routine_journey_bindings_tool`, `save_routine_journey_binding_tool`, `list_employee_process_routines_for_journey_tool`
- **Calendário de eventos**: `list_work_calendar_events_tool`, `create_work_calendar_event_tool`, `update_work_calendar_event_tool`, `delete_work_calendar_event_tool`
- **Analytics**: `list_work_journey_task_inventory_tool`, `get_work_journey_capacity_report_tool` (mesmo cálculo de capacidade da tela Análise das Jornadas), `get_process_routines_analysis_tool`, `get_efficiency_collaborators_analysis_tool`

Todas já resolvem escopo por colaborador (`resolve_actor_scope`/`ensure_employee_mutation_allowed`) do mesmo jeito que a UI — colaborador comum só opera a própria jornada, gestor/acesso total pode operar de outros. Se e quando a exposição via `mcp-versus` for aprovada, o padrão recomendado é o mesmo já usado para `processes`/`meetings`: cohort de leitura sempre exposto (board, agenda, analytics), cohort de mutação simples (blocos, regras, tarefas manuais, eventos de calendário) e cohort de mutação sensível com `human_gate` para aprovação de transferência/ausência e geração/trava de agenda.

**Achado importante:** o cálculo de capacidade (Análise das Jornadas / `get_work_journey_capacity_report_tool`) usa estimativas fixas por tipo de compromisso quando não há dado real mais preciso (ex.: 1h por atividade de projeto, 2h por instância de processo, 1h por reunião, capacidade semanal padrão de 40h) — é uma aproximação, não uma medição exata de tempo gasto. Isso é importante para não prometer precisão que a funcionalidade não tem.

## Validações e restrições
- `company_id` obrigatório; jornada/calendário de outra empresa nunca é retornado
- colaborador comum só vê e gerencia a própria jornada; gestor/usuário com acesso total à empresa pode consultar e gerenciar a de outros colaboradores
- na Análise das Jornadas, usuário sem acesso total à empresa tem `employee_id` forçado para si mesmo e o filtro de departamento é ignorado
- na Análise da Eficiência, usuário sem acesso total só vê os colaboradores vinculados ao seu próprio usuário, não a equipe toda
- transferências de bloco e ausências são fluxos de aprovação, não edição direta

## O que nunca expor
- estrutura de tabelas internas ou nomes de services (`work_journey_*`, `routine_analysis_service`, `efficiency_collaborators_service`)
- jornada, calendário ou análise de capacidade/eficiência de colaboradores fora da visibilidade do usuário
- dados de outra empresa/tenant
