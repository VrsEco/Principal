"""
Script: add_tasks_incentive_sprint.py

Adiciona as atividades do Sprint Plan do Módulo de Incentivos (Refatoração)
ao projeto AA.J.31 - Agentes de Work V3 na produção via SSH.

Execução: python scripts/add_tasks_incentive_sprint.py
"""

import sys
import os
from pathlib import Path
from datetime import date, timedelta

sys.path.append(str(Path(__file__).resolve().parents[1]))
from scripts.deploy.configr_remote_helper import connect_ssh, APP_DIR

# ── DEFINIÇÃO DAS ATIVIDADES ────────────────────────────────────────────────
# Sprints do Módulo de Incentivos — Refatoração Arquitetural

TODAY = date.today()

def weeks(n): return (TODAY + timedelta(weeks=n)).isoformat()


TASKS = [
    # ── S1: CRUD de Indicadores ──────────────────────────────────────────────
    {
        "what": "[S1] Refatorar model IncentiveIndicator — adicionar campo collection_mode (auto_interno | manual | api | mcp) e source_detail (JSON)",
        "how": "Alterar models/incentive.py. Criar migration Alembic. Garantir multi-tenancy por company_id.",
        "stage": "inbox", "priority": "high",
        "due": weeks(1)
    },
    {
        "what": "[S1] Criar CRUD de Indicadores com UI própria — /incentives/indicators",
        "how": "Nova rota, template indicator_list.html e indicator_form.html. Campos: código, nome, tipo, fonte (processo/projeto/OKR/manual/API), modo de coleta, indicador ativo.",
        "stage": "inbox", "priority": "high",
        "due": weeks(1)
    },
    {
        "what": "[S1] Implementar coleta nativa do sistema de pontuação de Processos e Projetos como IncentiveIndicator",
        "how": "Criar classe ScoreHarvester em services/incentive_service.py que lê pontos obtidos/possíveis + atrasos + ocorrências do período e grava IncentiveFact automaticamente.",
        "stage": "inbox", "priority": "high",
        "due": weeks(2)
    },
    {
        "what": "[S1] Criar endpoint MCP Tool: get_incentive_indicators — expor catálogo de indicadores via MCP Server",
        "how": "Seguir padrão Espelhamento (Regra #3 do Squad). Registrar em src/core/mcp_server.py.",
        "stage": "inbox", "priority": "normal",
        "due": weeks(2)
    },

    # ── S2: Reformulação do Plano (Etapas) ───────────────────────────────────
    {
        "what": "[S2] Redesenhar fluxo de criação do Plano em 4 etapas: Info → Participantes → Vetores de Premiação → Revisão",
        "how": "Transformar rules_manage.html em wizard multi-step. Cada etapa salva parcialmente via AJAX. UX: barra de progresso no topo.",
        "stage": "inbox", "priority": "high",
        "due": weeks(2)
    },
    {
        "what": "[S2] Criar model IncentiveParticipant — colaborador com valor_base, data_entrada, elegivel por plano",
        "how": "Nova tabela incentive_participants (company_id, rule_set_id, employee_id, valor_base, elegivel, data_entrada). Migration Alembic. CRUD na etapa 2 do wizard.",
        "stage": "inbox", "priority": "high",
        "due": weeks(2)
    },
    {
        "what": "[S2] Refatorar IncentiveRule → IncentiveVetor — renomear conceito de Regra para Vetor de Premiação na UI",
        "how": "Sem quebrar o model (manter tabela). Apenas atualizar: labels na UI, títulos de telas, comentários no código e documentação interna.",
        "stage": "inbox", "priority": "normal",
        "due": weeks(3)
    },
    {
        "what": "[S2] Implementar Vetores de Premiação com tipo: bonus | redutor | bloqueador — campos peso, meta, piso, teto, incidência",
        "how": "Atualizar IncentiveRule model: adicionar colunas vetor_type, piso (min_activation), incidencia (individual/coletivo). Migration Alembic. Atualizar UI da etapa 3.",
        "stage": "inbox", "priority": "high",
        "due": weeks(3)
    },

    # ── S3: Engine de Coleta Automática ──────────────────────────────────────
    {
        "what": "[S3] Refatorar harvest_all_modules — integrar pontuação de Processos/Projetos como fonte nativa",
        "how": "Expandir services/incentive_service.py para ler score_obtained/score_possible de instâncias de processos e atividades de projetos. Gravar IncentiveFact com evidence_payload detalhado.",
        "stage": "inbox", "priority": "high",
        "due": weeks(3)
    },
    {
        "what": "[S3] Implementar harvester para source_mode=api_externa — receber dados via Webhook/API REST",
        "how": "Criar endpoint POST /api/incentives/fact/webhook/<token> que recebe payload externo e grava IncentiveFact com status=draft. Token por company_id para segurança.",
        "stage": "inbox", "priority": "normal",
        "due": weeks(4)
    },
    {
        "what": "[S3] Implementar harvester para source_mode=mcp_tool — agente MCP coleta via ferramenta",
        "how": "Criar MCP Tool: harvest_incentive_facts(company_id, indicator_id, period_start, period_end). Registrar em mcp_server.py. Agente Sapiens pode disparar a coleta.",
        "stage": "inbox", "priority": "normal",
        "due": weeks(4)
    },

    # ── S4: Painel de Validação ───────────────────────────────────────────────
    {
        "what": "[S4] Criar Painel de Validação de Fatos — tela para revisar/ajustar valores antes do fechamento",
        "how": "Nova tela /incentives/validation/<calc_id>. Lista todos os IncentiveFacts do período com campo de override manual. Status: draft → verified → frozen.",
        "stage": "inbox", "priority": "high",
        "due": weeks(4)
    },
    {
        "what": "[S4] Implementar modo manual no painel — gestor insere valor direto para indicadores collection_mode=manual",
        "how": "Formulário inline por colaborador/indicador. Salva IncentiveFact com status=draft e requer aprovação do gestor (→ verified) antes de fechar.",
        "stage": "inbox", "priority": "normal",
        "due": weeks(5)
    },

    # ── S5: Integração e Qualidade ────────────────────────────────────────────
    {
        "what": "[S5] QA: Criar script de seed completo do módulo de incentivos para testes E2E",
        "how": "Script scripts/seed_incentive_full.py: cria plano, participantes, indicadores de cada fonte, roda coleta, executa cálculo preview e valida resultado.",
        "stage": "inbox", "priority": "normal",
        "due": weeks(5)
    },
    {
        "what": "[S5] Documentar arquitetura final do Módulo de Incentivos em docs/INCENTIVE_MODULE.md",
        "how": "Diagrama do fluxo: Indicador → Coleta (4 modos) → Fato → Vetor → Cálculo → Fechamento. Glossário: Vetor de Premiação, Fato, Participante, Coleta.",
        "stage": "inbox", "priority": "low",
        "due": weeks(6)
    },
]

# ── EXECUÇÃO VIA SSH ─────────────────────────────────────────────────────────

def run():
    ssh = connect_ssh()
    try:
        # Pega DATABASE_URL do .env de produção
        cmd = f"cd {APP_DIR} && grep DATABASE_URL .env | cut -d= -f2-"
        _, stdout, _ = ssh.exec_command(cmd)
        db_url = stdout.read().decode().strip()
        if not db_url:
            print("❌ DATABASE_URL não encontrada no .env de produção")
            return

        # Busca o projeto id=31 (AA.J.31) e confirma company_id
        sql_find = "SELECT id, title, company_id FROM projects WHERE id = 31;"
        _, stdout, _ = ssh.exec_command(f'psql "{db_url}" -c "{sql_find}"')
        result = stdout.read().decode()
        print(f"Projeto encontrado:\n{result}")

        if "31" not in result:
            print("❌ Projeto id=31 não encontrado na produção.")
            return

        # Insere cada atividade
        inserted = 0
        for task in TASKS:
            what_escaped = task["what"].replace("'", "''")
            how_escaped = task["how"].replace("'", "''")
            sql_insert = (
                f"INSERT INTO project_tasks "
                f"(project_id, what, how, stage, priority, due_date, status, score_weight, estimated_hours, worked_hours, created_at, updated_at) "
                f"VALUES "
                f"(31, '{what_escaped}', '{how_escaped}', '{task['stage']}', '{task['priority']}', "
                f"'{task['due']}', 'planned', 1.0, 0, 0, NOW(), NOW());"
            )
            _, stdout, stderr = ssh.exec_command(f'psql "{db_url}" -c "{sql_insert}"')
            out = stdout.read().decode()
            err = stderr.read().decode()
            if "INSERT" in out:
                inserted += 1
                print(f"  ✅ Inserida: {task['what'][:80]}...")
            else:
                print(f"  ❌ Erro: {err.strip()} | SQL saída: {out.strip()}")

        print(f"\n🎯 Total inserido: {inserted}/{len(TASKS)} atividades no projeto AA.J.31")

    finally:
        ssh.close()

if __name__ == "__main__":
    run()
