from __future__ import annotations

from src.intelligence.tools_support import get_active_company_id, sanitize_output


def list_plans(mode: str | None = None, company_id: int | None = None):
    """Lista planos estratégicos da empresa ativa ou da empresa explicitamente informada."""
    from services.plan_service import PlanService

    selected_company_id = int(company_id) if company_id is not None else get_active_company_id()
    if not selected_company_id:
        return "Erro: Contexto de empresa nao identificado."

    try:
        plans = PlanService.list_plans(selected_company_id, mode)
        if not plans:
            return "Nenhum plano encontrado."
        return "\n".join(
            f"ID: {plan.id} | Título: {plan.title} | Modo: {plan.mode} | Progresso: {plan.progress}%"
            for plan in plans
        )
    except Exception as exc:  # pragma: no cover - proteção defensiva compatível com tool legada
        return f"Erro ao listar planos: {exc}"


def get_plan_diagnostics(plan_id: int):
    """Retorna diagnóstico consolidado de plano no tenant ativo."""
    from services.plan_service import PlanService

    company_id = get_active_company_id()
    if not company_id:
        return "Erro: Contexto de empresa nao identificado."

    try:
        data = PlanService.get_plan_dashboard_data(plan_id, company_id)
        if not data:
            return f"Plano {plan_id} não encontrado ou sem acesso."

        output = [
            f"DIAGNÓSTICO DO PLANO: {data['plan']['title']} (ID: {plan_id}, Modo: {data['plan']['mode']})",
            f"Progresso Geral: {data['stats']['progress_pct']}%",
            "\nSTATUS DAS SEÇÕES:",
        ]

        for section in data["sections"]:
            status_emoji = "✅" if section["status"] == "completed" else "⏳" if section["status"] == "in_progress" else "❌"
            output.append(f"  {status_emoji} {section['title']}: {section['status']}")

        if "finance" in data:
            output.append("\nRESUMO FINANCEIRO (Implantação):")
            output.append(f"  Investimento Total: R$ {data['finance']['total_investment']:,.2f}")
            output.append(f"  Payback Estimado: {data['finance']['payback']} meses")

        return sanitize_output("\n".join(output))
    except Exception as exc:  # pragma: no cover - proteção defensiva compatível com tool legada
        return sanitize_output(f"Erro ao diagnosticar plano: {exc}")


def update_plan_section(
    plan_id: int,
    section_key: str,
    status: str = "completed",
    company_id: int | None = None,
):
    """Atualiza seção de plano após validar existência no tenant ativo ou explicitamente informado."""
    from services.plan_service import PlanService

    selected_company_id = int(company_id) if company_id is not None else get_active_company_id()
    if not selected_company_id:
        return "Erro: Contexto de empresa nao identificado."

    try:
        plan = PlanService.get_plan(plan_id, selected_company_id)
        if not plan:
            return f"Plano {plan_id} não encontrado."

        valid_section_keys = PlanService.get_valid_section_keys(plan.mode)
        if section_key not in valid_section_keys:
            valid_keys = ", ".join(valid_section_keys)
            return (
                f"Erro: section_key '{section_key}' inválida para plano no modo '{plan.mode}'. "
                f"Use uma das opções: {valid_keys}."
            )

        PlanService.update_section_status(plan_id, section_key, status)
        return f"Sucesso: Seção '{section_key}' do plano {plan_id} alterada para '{status}'."
    except Exception as exc:  # pragma: no cover - proteção defensiva compatível com tool legada
        return f"Erro ao atualizar seção: {exc}"


__all__ = ["list_plans", "get_plan_diagnostics", "update_plan_section"]
