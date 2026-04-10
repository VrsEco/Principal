from __future__ import annotations

from src.intelligence.tools_support import sanitize_output
from services.analytics_read_model_service import AnalyticsReadModelService


def get_plan_diagnostics_read_model(company_id: int, plan_id: int):
    """Retorna read model estruturado para diagnóstico de plano estratégico."""
    try:
        return AnalyticsReadModelService.get_plan_diagnostics_read_model(
            company_id=company_id,
            plan_id=plan_id,
        )
    except Exception as exc:  # pragma: no cover - proteção defensiva compatível
        return sanitize_output(f"Erro ao montar read model do plano: {exc}")


def get_team_workload_read_model(company_id: int, department: str | None = None, employee_id: int | None = None):
    """Retorna read model whitelisted de workload por empresa/departamento/colaborador."""
    try:
        return AnalyticsReadModelService.get_team_workload_read_model(
            company_id=company_id,
            department=department,
            employee_id=employee_id,
        )
    except Exception as exc:  # pragma: no cover - proteção defensiva compatível
        return sanitize_output(f"Erro ao montar read model de workload: {exc}")


def get_projects_execution_risk_read_model(
    company_id: int,
    project_id: int | None = None,
    employee_id: int | None = None,
    status: str | None = None,
    limit: int = 50,
):
    """Retorna read model whitelisted de risco de execução de projetos."""
    try:
        return AnalyticsReadModelService.get_projects_execution_risk_read_model(
            company_id=company_id,
            project_id=project_id,
            employee_id=employee_id,
            status=status,
            limit=limit,
        )
    except Exception as exc:  # pragma: no cover - proteção defensiva compatível
        return sanitize_output(f"Erro ao montar read model de risco de execução: {exc}")


__all__ = [
    "get_plan_diagnostics_read_model",
    "get_team_workload_read_model",
    "get_projects_execution_risk_read_model",
]
