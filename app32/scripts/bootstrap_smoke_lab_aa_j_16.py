from __future__ import annotations

import argparse
import json
from datetime import date, time

from app import create_app
from models import db
from models.company import Company
from models.employee import Employee
from models.financial_budget import FinancialBudgetVersion
from models.plan import Plan
from models.process import MacroProcess, Process, ProcessArea
from models.project import Project, ProjectTask
from models.user import User
from models.work_journey import WorkJourneyBlock, WorkJourneyRule
from services.financial_budget_service import FinancialBudgetService
from services.financial_budget_workspace_service import FinancialBudgetWorkspaceService
from services.plan_service import PlanService


PLAN_TITLE = "[LAB M1] Plano Estratégico Smoke"
BUDGET_NAME = "[LAB M1] Orçamento Matricial Smoke 2026"
LINE_NAME = "[LAB M1] Verba Comercial Base"
AREA_NAME = "[LAB M1] Area Comercial"
MACRO_NAME = "[LAB M1] Macroprocesso Vendas"
PROCESS_NAME = "[LAB M1] Processo Operacional Comercial"
BLOCK_NAME = "[LAB M1] Bloco Operacional Manhã"
RULE_TITLE = "[LAB M1] Revisão operacional diária"
MY_TASK_TITLE = "[LAB M1][Smoke] Tarefa minha do dia"
COMPANY_TASK_TITLE = "[LAB M1][Smoke] Tarefa empresa do dia"


def ensure_employee(company_id: int, user_id: int) -> Employee:
    user = User.query.get(user_id)
    if not user:
        raise ValueError(f"Usuário {user_id} não encontrado.")

    employee = Employee.query.filter_by(company_id=company_id, user_id=user_id).first()
    if employee:
        return employee

    employee = Employee(
        company_id=company_id,
        user_id=user_id,
        name=(getattr(user, "name", None) or getattr(user, "email", None) or f"User {user_id}").strip(),
        email=getattr(user, "email", None),
        department="Laboratório AA.J.16",
        status="active",
        weekly_hours=44,
        notes="Bootstrap smoke AA.J.16",
    )
    db.session.add(employee)
    db.session.commit()
    return employee


def ensure_work_journey_assets(company_id: int, employee: Employee) -> dict[str, int | None]:
    block = WorkJourneyBlock.query.filter_by(
        company_id=company_id,
        employee_id=employee.id,
        name=BLOCK_NAME,
    ).first()
    if not block:
        block = WorkJourneyBlock(
            company_id=company_id,
            employee_id=employee.id,
            name=BLOCK_NAME,
            description="Bloco base para smoke da jornada operacional.",
            start_time=time(8, 0),
            end_time=time(12, 0),
            block_mode="operational",
            weekdays_json=[0, 1, 2, 3, 4],
            accepted_item_types=["manual", "project_task", "process_instance", "meeting"],
            order_index=10,
            is_active=True,
        )
        db.session.add(block)
        db.session.commit()

    rule = WorkJourneyRule.query.filter_by(
        company_id=company_id,
        employee_id=employee.id,
        title=RULE_TITLE,
    ).first()
    if not rule:
        rule = WorkJourneyRule(
            company_id=company_id,
            employee_id=employee.id,
            preferred_block_id=block.id,
            title=RULE_TITLE,
            description="Obrigação recorrente criada para smoke do módulo Rotina.",
            item_type="manual",
            recurrence_type="daily",
            recurrence_config={"weekdays": [0, 1, 2, 3, 4]},
            estimated_minutes=30,
            priority="normal",
            start_date=date.today(),
            is_active=True,
        )
        db.session.add(rule)
        db.session.commit()

    assigned_task = (
        db.session.query(ProjectTask)
        .join(Project, Project.id == ProjectTask.project_id)
        .filter(Project.company_id == company_id)
        .filter(ProjectTask.status.notin_(["completed", "cancelled"]))
        .order_by(ProjectTask.id.asc())
        .first()
    )
    if assigned_task and assigned_task.employee_id != employee.id:
        assigned_task.employee_id = employee.id
        assigned_task.who = employee.name
        db.session.add(assigned_task)
        db.session.commit()

    return {
        "employee_id": employee.id,
        "block_id": block.id if block else None,
        "rule_id": rule.id if rule else None,
        "assigned_project_task_id": assigned_task.id if assigned_task else None,
    }


def ensure_scope_tasks(company_id: int, employee: Employee) -> dict[str, int | None]:
    project = Project.query.filter_by(company_id=company_id).order_by(Project.id.asc()).first()
    if not project:
        return {"my_scope_task_id": None, "company_scope_task_id": None}

    my_task = (
        ProjectTask.query.filter_by(project_id=project.id, what=MY_TASK_TITLE)
        .order_by(ProjectTask.id.asc())
        .first()
    )
    if not my_task:
        my_task = ProjectTask(
            project_id=project.id,
            what=MY_TASK_TITLE,
            who=employee.name,
            employee_id=employee.id,
            due_date=date.today(),
            status="planned",
            stage="inbox",
            priority="high",
            notes="Criada automaticamente para validar scope=me no smoke AA.J.16.",
        )
        db.session.add(my_task)

    company_task = (
        ProjectTask.query.filter_by(project_id=project.id, what=COMPANY_TASK_TITLE)
        .order_by(ProjectTask.id.asc())
        .first()
    )
    if not company_task:
        company_task = ProjectTask(
            project_id=project.id,
            what=COMPANY_TASK_TITLE,
            who="Empresa",
            employee_id=None,
            due_date=date.today(),
            status="planned",
            stage="inbox",
            priority="normal",
            notes="Criada automaticamente para validar scope=company no smoke AA.J.16.",
        )
        db.session.add(company_task)

    db.session.commit()
    return {
        "my_scope_task_id": my_task.id if my_task else None,
        "company_scope_task_id": company_task.id if company_task else None,
    }


def ensure_plan(company_id: int) -> Plan:
    plan = Plan.query.filter_by(company_id=company_id, title=PLAN_TITLE).first()
    if plan:
        return plan
    return PlanService.create_plan(
        company_id,
        {
            "title": PLAN_TITLE,
            "description": "Plano estratégico mínimo para smoke do laboratório AA.J.16.",
            "mode": "implantation",
            "status": "draft",
            "meta_data": {"source": "bootstrap_smoke_lab_aa_j_16"},
        },
    )


def ensure_budget_version(company_id: int, employee: Employee, user_id: int) -> dict[str, int | None]:
    version = FinancialBudgetVersion.query.filter_by(company_id=company_id, name=BUDGET_NAME).first()
    if not version:
        version_payload, error = FinancialBudgetService.create_version(
            payload={
                "company_id": company_id,
                "code": "AUTO",
                "name": BUDGET_NAME,
                "budget_category": "general",
                "scenario_type": "original",
                "status": "draft",
                "period_start": date(2026, 1, 1),
                "period_end": date(2026, 12, 31),
                "responsible_employee_id": employee.id,
                "created_by_user_id": user_id,
                "notes": "Versão bootstrap para smoke do laboratório.",
                "metadata_json": {"source": "bootstrap_smoke_lab_aa_j_16"},
            }
        )
        if error:
            raise ValueError(error)
        version = FinancialBudgetVersion.query.get(version_payload["id"])

    workspace, error = FinancialBudgetWorkspaceService.get_planning_workspace(company_id=company_id, version_id=version.id)
    if error:
        raise ValueError(error)
    existing_line = next((line for line in (workspace or {}).get("lines", []) if line.get("line_name") == LINE_NAME), None)
    if not existing_line:
        line_payload, error = FinancialBudgetWorkspaceService.create_line(
            payload={
                "company_id": company_id,
                "budget_version_id": version.id,
                "line_code": "AUTO",
                "line_name": LINE_NAME,
                "budget_view": "competence",
                "movement_nature": "debit",
                "planned_amount": 1200,
                "responsible_employee_id": employee.id,
                "notes": "Verba mínima para smoke do workspace orçamentário.",
                "metadata_json": {"source": "bootstrap_smoke_lab_aa_j_16"},
            }
        )
        if error:
            raise ValueError(error)
        line_id = line_payload["id"]
    else:
        line_id = existing_line.get("id")

    return {"budget_version_id": version.id, "budget_line_id": line_id}


def ensure_commercial_process(company_id: int, employee: Employee) -> dict[str, int]:
    area = ProcessArea.query.filter_by(company_id=company_id, name=AREA_NAME).first()
    if not area:
        area = ProcessArea(
            company_id=company_id,
            name=AREA_NAME,
            code="M1.C.AC",
            description="Área comercial bootstrap do laboratório.",
            order_index=10,
        )
        db.session.add(area)
        db.session.commit()

    macro = MacroProcess.query.filter_by(company_id=company_id, area_id=area.id, name=MACRO_NAME).first()
    if not macro:
        macro = MacroProcess(
            company_id=company_id,
            area_id=area.id,
            name=MACRO_NAME,
            code="M1.C.AC.1",
            owner=employee.name,
            description="Macroprocesso bootstrap do laboratório.",
            order_index=1,
        )
        db.session.add(macro)
        db.session.commit()

    process = Process.query.filter_by(company_id=company_id, macro_id=macro.id, name=PROCESS_NAME).first()
    if not process:
        process = Process(
            company_id=company_id,
            macro_id=macro.id,
            name=PROCESS_NAME,
            code="M1.C.AC.1.1",
            description="Processo operacional criado para smoke do comercial.",
            responsible=employee.name,
            responsible_id=employee.id,
            owner_employee_id=employee.id,
            order_index=1,
            is_active=True,
        )
        db.session.add(process)
        db.session.commit()

    return {"area_id": area.id, "macro_id": macro.id, "process_id": process.id}


def main() -> None:
    parser = argparse.ArgumentParser(description="Bootstrap idempotente do laboratório AA.J.16 para smoke dos 4 pilares.")
    parser.add_argument("--company-id", type=int, default=10)
    parser.add_argument("--user-id", type=int, default=3)
    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        company = Company.query.get(args.company_id)
        if not company:
            raise SystemExit(f"Empresa {args.company_id} não encontrada.")

        employee = ensure_employee(args.company_id, args.user_id)
        journey = ensure_work_journey_assets(args.company_id, employee)
        scope_tasks = ensure_scope_tasks(args.company_id, employee)
        plan = ensure_plan(args.company_id)
        budget = ensure_budget_version(args.company_id, employee, args.user_id)
        commercial = ensure_commercial_process(args.company_id, employee)

        payload = {
            "company_id": args.company_id,
            "company_name": company.name,
            "user_id": args.user_id,
            "employee_id": employee.id,
            "plan_id": plan.id,
            **journey,
            **scope_tasks,
            **budget,
            **commercial,
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
