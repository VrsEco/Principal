from __future__ import annotations

from typing import Any

from models import Employee, Indicator, OKRArea, OKRGlobal, Plan, Portfolio, Project, db
from services.project_task_service import ProjectTaskService


class ProjectService:
    PLAN_PORTFOLIO_MARKER = "[APP32_PLAN_PORTFOLIO]"

    @staticmethod
    def _positive_int(value: Any) -> int | None:
        try:
            parsed = int(value)
        except (TypeError, ValueError):
            return None
        return parsed if parsed > 0 else None

    @staticmethod
    def _normalize_progress(value: Any) -> int:
        try:
            parsed = int(value or 0)
        except (TypeError, ValueError):
            parsed = 0
        return max(0, min(parsed, 100))

    @staticmethod
    def _normalize_okr_links(value: Any, company_id: int) -> tuple[list[int], str | None]:
        if value in (None, ""):
            return [], None
        if not isinstance(value, (list, tuple, set)):
            return [], "okr_links deve ser uma lista de IDs."

        normalized: list[int] = []
        try:
            normalized = [int(item) for item in value]
        except (TypeError, ValueError):
            return [], "okr_links deve conter apenas IDs inteiros."

        if not normalized:
            return [], None

        global_ids = {
            row[0]
            for row in (
                OKRGlobal.query.filter(
                    OKRGlobal.company_id == company_id,
                    OKRGlobal.id.in_(normalized),
                )
                .with_entities(OKRGlobal.id)
                .all()
            )
        }
        area_ids = {
            row[0]
            for row in (
                OKRArea.query.filter(
                    OKRArea.company_id == company_id,
                    OKRArea.id.in_(normalized),
                )
                .with_entities(OKRArea.id)
                .all()
            )
        }
        missing = sorted(set(normalized) - global_ids - area_ids)
        if missing:
            return [], (
                "OKRs não encontrados na empresa ativa: "
                + ", ".join(str(item) for item in missing)
            )
        return normalized, None

    @staticmethod
    def _resolve_plan(company_id: int, plan_id: Any) -> tuple[Plan | None, str | None]:
        normalized_id = ProjectService._positive_int(plan_id)
        if not normalized_id:
            return None, None
        plan = Plan.query.filter_by(id=normalized_id, company_id=company_id).first()
        if not plan:
            return None, "Planejamento não encontrado na empresa ativa."
        return plan, None

    @staticmethod
    def _plan_portfolio_code(plan_id: int) -> str:
        return f"PLAN-{int(plan_id)}"

    @staticmethod
    def _get_or_create_plan_portfolio(
        company_id: int,
        plan: Plan,
        owner_name: str | None,
    ) -> Portfolio:
        code = ProjectService._plan_portfolio_code(plan.id)
        portfolio = Portfolio.query.filter_by(company_id=company_id, code=code).first()
        if portfolio:
            return portfolio

        responsible = None
        if owner_name:
            responsible = Employee.query.filter_by(
                company_id=company_id,
                name=owner_name,
                status="active",
            ).first()

        portfolio = Portfolio(
            company_id=company_id,
            code=code,
            name=plan.title,
            responsible_id=responsible.id if responsible else None,
            notes=(
                f"{ProjectService.PLAN_PORTFOLIO_MARKER} "
                f"Portfólio criado automaticamente pelo Planejamento Estratégico #{plan.id}."
            ),
        )
        db.session.add(portfolio)
        db.session.flush()
        return portfolio

    @staticmethod
    def _resolve_portfolio(
        company_id: int,
        data: dict[str, Any],
        plan: Plan | None,
    ) -> tuple[Portfolio | None, str | None]:
        option = str(data.get("portfolio_option") or "").strip().lower()
        portfolio_id = ProjectService._positive_int(data.get("portfolio_id"))

        if option == "new":
            if not plan:
                return None, "Um planejamento válido é obrigatório para criar o portfólio."
            return (
                ProjectService._get_or_create_plan_portfolio(
                    company_id,
                    plan,
                    str(data.get("owner") or "").strip() or None,
                ),
                None,
            )

        if option == "existing" and not portfolio_id:
            return None, "Selecione um portfólio existente."

        if portfolio_id:
            portfolio = Portfolio.query.filter_by(
                id=portfolio_id,
                company_id=company_id,
            ).first()
            if not portfolio:
                return None, "Portfólio não encontrado na empresa ativa."
            return portfolio, None

        return None, None

    @staticmethod
    def create_project(
        company_id: int,
        payload: dict[str, Any],
    ) -> tuple[Project | None, str | None]:
        data = dict(payload or {})
        name = str(data.get("name") or "").strip()
        if not name:
            return None, "Informe o nome do projeto."

        plan, error = ProjectService._resolve_plan(company_id, data.get("plan_id"))
        if error:
            return None, error

        portfolio, error = ProjectService._resolve_portfolio(company_id, data, plan)
        if error:
            return None, error

        okr_links, error = ProjectService._normalize_okr_links(
            data.get("okr_links"),
            company_id,
        )
        if error:
            return None, error

        deadline, error = ProjectTaskService.parse_due_date(data.get("deadline"))
        if error:
            return None, error

        project = Project(
            company_id=company_id,
            name=name,
            description=str(data.get("description") or "").strip() or None,
            plan_id=plan.id if plan else None,
            okr_links=okr_links,
            owner=str(data.get("owner") or "").strip() or None,
            status=str(data.get("status") or "planned"),
            deadline=deadline,
            budget=data.get("budget"),
            notes=str(data.get("notes") or "").strip() or None,
            progress=ProjectService._normalize_progress(data.get("progress")),
            priority=str(data.get("priority") or "medium"),
            portfolio_id=portfolio.id if portfolio else None,
        )
        db.session.add(project)

        indicator_id = ProjectService._positive_int(data.get("indicator_id"))
        if indicator_id:
            indicator = Indicator.query.filter_by(
                id=indicator_id,
                company_id=company_id,
                is_active=True,
            ).first()
            if not indicator:
                db.session.rollback()
                return None, "Indicador inválido para a empresa ativa."
            indicator.project = project
            marker = f"APP32_INDICATOR_LINK: {indicator.id}"
            if marker not in (project.notes or ""):
                project.notes = ((project.notes + "\n\n") if project.notes else "") + (
                    f"{marker}\n"
                    "Projeto criado a partir do Painel de Gestão Estratégica. "
                    "Após criar o projeto, crie as atividades corretivas vinculadas ao indicador."
                )

        db.session.commit()
        return project, None
