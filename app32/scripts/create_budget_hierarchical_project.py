from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path
from typing import Iterable

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

from app import create_app
from models import db
from models.project import Project, ProjectTask


DEFAULT_COMPANY_ID = 9
DEFAULT_PORTFOLIO_ID = 30
DEFAULT_OWNER = "Fabiano Diretor"
DEFAULT_DEADLINE = date(2026, 5, 29)
DEFAULT_SOURCE_PROJECT_ID = 31
DEFAULT_TITLE = "Orçamento Hierárquico 2026 — Ciclos CAPEX/OPEX e Enquadramento Financeiro"


PROJECT_NOTES = """
Projeto criado para implantar o módulo de orçamento hierárquico com:
- Ciclo Orçamentário como camada superior de consolidação.
- Orçamentos independentes por categoria (CAPEX, OPEX, CAPEX Extra).
- Estrutura Orçamento > Verba > Contrato > Documento > Agendamento > Lançamento.
- Código hierárquico estruturado com consolidação por ciclo e por orçamento.
- Enquadramento orçamentário no financeiro operacional do dia a dia.

Observação operacional:
- Na base local consultada em 2026-03-27 não foi encontrada entidade com código AA.P.31.
- Por inferência operacional, as atividades foram importadas do projeto id=31 (AA.J.31 / "Agentes de Wokr V3"),
  que é a referência existente no contexto da empresa 9.
""".strip()


BOOTSTRAP_TASKS = [
    {
        "what": "[ARQUITETO] Definir a arquitetura do Ciclo Orçamentário e a hierarquia consolidada CAPEX/OPEX/Extra",
        "how": "Fechar modelo-alvo com FinancialBudgetCycle, categorias de orçamento, filtros consolidados, regras de multi-tenancy e breadcrumbs do workspace.",
        "priority": "high",
    },
    {
        "what": "[DBA] Criar migrations e backfill para códigos hierárquicos e ciclo orçamentário",
        "how": "Adicionar budget_cycle_id, budget_category, budget_seq, line_seq, contract_seq, document_seq, full_code e company_code_snapshot com índices e constraints.",
        "priority": "high",
    },
    {
        "what": "[BACKEND_SERVICE] Implementar geração de códigos e consolidação por ciclo/orçamento",
        "how": "Criar regra determinística para geração do código estrutural e consolidação separado/consolidado de CAPEX, OPEX e Extra dentro do exercício.",
        "priority": "high",
    },
    {
        "what": "[BACKEND_API] Expor workspace de orçamento com filtros por ciclo, categoria e consolidação",
        "how": "Adaptar recursos REST para suportar visão por ciclo, orçamento individual, agrupamentos e drill-down hierárquico completo.",
        "priority": "high",
    },
    {
        "what": "[BACKEND_SERVICE] Integrar enquadramento orçamentário no agendamento e lançamento diário do financeiro",
        "how": "Permitir vínculo previsto, extra-orçamentário e não planejado nos fluxos operacionais genéricos, com herança automática quando vier do orçamento.",
        "priority": "high",
    },
    {
        "what": "[FRONTEND] Criar tela raiz de Ciclos/Orçamentos com visão consolidada",
        "how": "Basear a shell visual no padrão process_instances, exibindo cards, filtros e acesso ao workspace hierárquico.",
        "priority": "normal",
    },
    {
        "what": "[FRONTEND] Implementar workspace hierárquico Orçamento > Verba > Contrato > Documento > Agendamentos",
        "how": "Usar o padrão operacional de financial/schedules para drill-down com breadcrumbs, KPIs por nível e seleção progressiva.",
        "priority": "high",
    },
    {
        "what": "[FRONTEND] Expor enquadramento orçamentário na tela operacional do financeiro",
        "how": "Adicionar seleção guiada de ciclo, orçamento, verba, contrato e documento nas telas genéricas de agendamento e lançamento.",
        "priority": "normal",
    },
    {
        "what": "[AI_ENGINEER] Planejar espelhamento MCP First do módulo de orçamento",
        "how": "Mapear ferramentas MCP equivalentes para listar ciclos, criar verbas, contratos, documentos, agendamentos e consultar execução consolidada.",
        "priority": "normal",
    },
    {
        "what": "[QA_AUTOMATION] Cobrir testes de integridade, consolidação e regressão do módulo de orçamento",
        "how": "Criar testes multi-tenant, geração de códigos, consolidação CAPEX/OPEX/Extra e herança de vínculo orçamentário até o lançamento.",
        "priority": "high",
    },
]


def _ensure_project(
    *,
    company_id: int,
    title: str,
    owner: str,
    deadline: date,
    portfolio_id: int | None,
) -> tuple[Project, bool]:
    project = Project.query.filter_by(company_id=company_id, name=title).first()
    if project:
        return project, False

    project = Project(
        company_id=company_id,
        name=title,
        owner=owner,
        status="in_progress",
        priority="high",
        deadline=deadline,
        portfolio_id=portfolio_id,
        notes=PROJECT_NOTES,
    )
    db.session.add(project)
    db.session.flush()
    return project, True


def _task_exists(project_id: int, what: str, marker: str | None = None) -> bool:
    query = ProjectTask.query.filter_by(project_id=project_id, what=what)
    if marker:
        query = query.filter(ProjectTask.notes.ilike(f"%{marker}%"))
    return db.session.query(query.exists()).scalar()


def _insert_bootstrap_tasks(project_id: int) -> int:
    inserted = 0
    for task in BOOTSTRAP_TASKS:
        marker = "[budget-hierarchical-bootstrap]"
        if _task_exists(project_id, task["what"], marker):
            continue

        db.session.add(
            ProjectTask(
                project_id=project_id,
                what=task["what"],
                how=task["how"],
                stage="inbox",
                status="planned",
                priority=task["priority"],
                notes=marker,
            )
        )
        inserted += 1
    return inserted


def _iter_source_tasks(source_project_id: int) -> Iterable[ProjectTask]:
    return (
        ProjectTask.query.filter_by(project_id=source_project_id)
        .order_by(ProjectTask.id.asc())
        .all()
    )


def _clone_source_tasks(*, project_id: int, source_project_id: int) -> int:
    inserted = 0
    for source_task in _iter_source_tasks(source_project_id):
        marker = f"[origem:project#{source_project_id}:task#{source_task.id}]"
        if _task_exists(project_id, source_task.what, marker):
            continue

        notes_parts = [source_task.notes.strip()] if source_task.notes else []
        notes_parts.append(marker)

        db.session.add(
            ProjectTask(
                project_id=project_id,
                what=source_task.what,
                who=source_task.who,
                employee_id=source_task.employee_id,
                due_date=source_task.due_date,
                how=source_task.how,
                amount=source_task.amount,
                status=source_task.status or "planned",
                stage=source_task.stage or "inbox",
                priority=source_task.priority or "normal",
                notes="\n".join(notes_parts),
                score_weight=source_task.score_weight,
                estimated_hours=source_task.estimated_hours,
                worked_hours=source_task.worked_hours,
                logs=source_task.logs,
            )
        )
        inserted += 1
    return inserted


def run(
    *,
    company_id: int,
    title: str,
    owner: str,
    deadline: date,
    portfolio_id: int | None,
    source_project_id: int,
) -> None:
    app = create_app("development")
    with app.app_context():
        source_project = Project.query.filter_by(id=source_project_id, company_id=company_id).first()
        if not source_project:
            raise RuntimeError(
                f"Projeto fonte id={source_project_id} não encontrado para company_id={company_id}."
            )

        project, created = _ensure_project(
            company_id=company_id,
            title=title,
            owner=owner,
            deadline=deadline,
            portfolio_id=portfolio_id,
        )

        inserted_bootstrap = _insert_bootstrap_tasks(project.id)
        inserted_clone = _clone_source_tasks(
            project_id=project.id,
            source_project_id=source_project_id,
        )

        project.update_progress()
        db.session.commit()

        print(
            {
                "project_id": project.id,
                "project_code": project.code,
                "project_name": project.name,
                "created": created,
                "bootstrap_tasks_inserted": inserted_bootstrap,
                "source_tasks_cloned": inserted_clone,
                "total_tasks": ProjectTask.query.filter_by(project_id=project.id).count(),
                "source_project_id": source_project_id,
                "source_project_code": source_project.code,
            }
        )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Cria o projeto do orçamento hierárquico e importa tarefas de referência."
    )
    parser.add_argument("--company-id", type=int, default=DEFAULT_COMPANY_ID)
    parser.add_argument("--title", default=DEFAULT_TITLE)
    parser.add_argument("--owner", default=DEFAULT_OWNER)
    parser.add_argument("--deadline", default=DEFAULT_DEADLINE.isoformat())
    parser.add_argument("--portfolio-id", type=int, default=DEFAULT_PORTFOLIO_ID)
    parser.add_argument("--source-project-id", type=int, default=DEFAULT_SOURCE_PROJECT_ID)
    args = parser.parse_args()

    run(
        company_id=args.company_id,
        title=args.title,
        owner=args.owner,
        deadline=date.fromisoformat(args.deadline),
        portfolio_id=args.portfolio_id,
        source_project_id=args.source_project_id,
    )


if __name__ == "__main__":
    main()
