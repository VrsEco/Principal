from __future__ import annotations

import os
from datetime import datetime

from models import db
from schemas.okr import okr_area_schema, okr_global_schema
from schemas.plan import PlanSectionStatusUpdate
from src.intelligence.security.mcp_mutation_guard import (
    evaluate_mutation_limit,
    record_mutation_success,
)
from src.intelligence.security.runtime_identity import resolve_runtime_identity
from src.intelligence.security.tool_policy import ToolPolicyRequest, evaluate_tool_policy
from src.intelligence.tooling.capabilities import TOOL_CONTEXT_COMPANY, TOOL_CONTEXT_USER
from src.intelligence.tools_support import get_active_company_id, sanitize_output


def _current_surface() -> str:
    return str(os.environ.get("APP32_MCP_SURFACE") or "user").strip().lower()


def _build_mcp_principal(company_id: int | None) -> dict[str, object]:
    from src.intelligence.tools_support import get_active_user_id

    user_id = get_active_user_id()
    runtime_identity = (
        resolve_runtime_identity(user_id=int(user_id), company_id=company_id)
        if user_id
        else {}
    )
    permissions = runtime_identity.get("permissions") or ()
    if isinstance(permissions, dict):
        permissions = tuple(str(key).strip().lower() for key in permissions.keys() if str(key).strip())
    elif isinstance(permissions, (list, tuple, set, frozenset)):
        permissions = tuple(str(item).strip().lower() for item in permissions if str(item).strip())
    elif permissions:
        permissions = (str(permissions).strip().lower(),)
    else:
        permissions = ()

    return {
        "user_id": user_id,
        "company_id": runtime_identity.get("company_id") or company_id,
        "employee_id": runtime_identity.get("employee_id"),
        "role": runtime_identity.get("role") or str(os.environ.get("APP32_MCP_FALLBACK_ROLE") or "colaborador").strip().lower(),
        "channel": str(os.environ.get("APP32_MCP_CHANNEL") or "claude_code").strip().lower(),
        "thread_id": os.environ.get("APP32_MCP_THREAD_ID"),
        "permissions": permissions,
        "accessible_company_ids": tuple(runtime_identity.get("accessible_company_ids") or ()),
    }


def _authorize_strategy_mcp(
    *,
    tool_name: str,
    action: str,
    company_id: int | None,
    risk: str,
    required_permissions: tuple[str, ...] = (),
):
    principal = _build_mcp_principal(company_id)
    decision = evaluate_tool_policy(
        principal,
        ToolPolicyRequest(
            tool_name=tool_name,
            surface=_current_surface(),
            domain="strategy",
            action=action,
            risk=risk,
            requested_company_id=company_id,
            accessible_company_ids=tuple(principal.get("accessible_company_ids") or ()),
            required_permissions=required_permissions,
            required_context=(TOOL_CONTEXT_USER, TOOL_CONTEXT_COMPANY),
        ),
    )
    return principal, decision


def _parse_optional_deadline(value: str | None):
    if value in (None, ""):
        return None
    raw = str(value).strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    raise ValueError("deadline deve estar em YYYY-MM-DD ou DD/MM/YYYY")


def _ensure_plan_belongs_to_company(plan_id: int | None, company_id: int) -> None:
    if not plan_id:
        return
    from services.plan_service import PlanService

    plan = PlanService.get_plan(int(plan_id), int(company_id))
    if not plan:
        raise ValueError(f"Plano {plan_id} não encontrado para a empresa {company_id}.")


def _normalize_linked_okr_ids(linked_okr_ids) -> list[int] | None:
    if linked_okr_ids in (None, ""):
        return None
    if not isinstance(linked_okr_ids, (list, tuple, set)):
        raise ValueError("linked_okr_ids deve ser uma lista de IDs de OKRs globais.")
    normalized: list[int] = []
    for item in linked_okr_ids:
        try:
            normalized.append(int(item))
        except Exception as exc:
            raise ValueError("linked_okr_ids deve conter apenas inteiros.") from exc
    return normalized


def _ensure_global_okrs_belong_to_company(okr_ids: list[int] | None, company_id: int) -> None:
    if not okr_ids:
        return
    from models import OKRGlobal

    found = (
        OKRGlobal.query.filter(
            OKRGlobal.company_id == int(company_id),
            OKRGlobal.id.in_(okr_ids),
        )
        .with_entities(OKRGlobal.id)
        .all()
    )
    found_ids = {row[0] for row in found}
    missing = [okr_id for okr_id in okr_ids if okr_id not in found_ids]
    if missing:
        raise ValueError(
            "Os seguintes OKRs globais não pertencem à empresa ativa ou não existem: "
            + ", ".join(str(item) for item in missing)
        )


def _ensure_global_okr_belongs_to_company(okr_global_id: int, company_id: int):
    from models import OKRGlobal

    okr = OKRGlobal.query.filter_by(id=int(okr_global_id), company_id=int(company_id)).first()
    if not okr:
        raise ValueError(f"OKR global {okr_global_id} não encontrado para a empresa {company_id}.")
    return okr


def _ensure_area_okr_belongs_to_company(okr_area_id: int, company_id: int):
    from models import OKRArea

    okr = OKRArea.query.filter_by(id=int(okr_area_id), company_id=int(company_id)).first()
    if not okr:
        raise ValueError(f"OKR de área {okr_area_id} não encontrado para a empresa {company_id}.")
    return okr


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


def get_plan_diagnostics(plan_id: int, company_id: int | None = None):
    """Retorna diagnóstico consolidado de plano no tenant ativo ou explicitamente informado."""
    from services.plan_service import PlanService

    selected_company_id = int(company_id) if company_id is not None else get_active_company_id()
    if not selected_company_id:
        return "Erro: Contexto de empresa nao identificado."

    try:
        data = PlanService.get_plan_dashboard_data(plan_id, selected_company_id)
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
        normalized_status = PlanSectionStatusUpdate(status=status).status
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

        PlanService.update_section_status(plan_id, section_key, normalized_status)
        return f"Sucesso: Seção '{section_key}' do plano {plan_id} alterada para '{normalized_status}'."
    except Exception as exc:  # pragma: no cover - proteção defensiva compatível com tool legada
        return f"Erro ao atualizar seção: {exc}"


def create_global_okr(
    objective: str,
    okr_type: str,
    company_id: int | None = None,
    plan_id: int | None = None,
    owner: str | None = None,
    deadline: str | None = None,
    observations: str | None = None,
    directionals: list[int] | None = None,
):
    """Cria um OKR global tenant-safe no domínio estratégico."""
    selected_company_id = int(company_id) if company_id is not None else get_active_company_id()
    if not selected_company_id:
        return {"success": False, "error": "Erro: Contexto de empresa nao identificado."}

    principal, decision = _authorize_strategy_mcp(
        tool_name="create_global_okr",
        action="create",
        company_id=selected_company_id,
        risk="medium",
        required_permissions=("okrs.global.create",),
    )
    if not decision.allowed:
        return {"success": False, "error": decision.reason, "policy": decision.to_audit_event()}

    limit_decision = evaluate_mutation_limit(
        action="create",
        company_id=decision.resolved_company_id,
        user_id=principal.get("user_id"),
    )
    if not limit_decision.allowed:
        return {"success": False, "error": limit_decision.reason, "limits": limit_decision.to_dict()}

    try:
        _ensure_plan_belongs_to_company(plan_id, int(decision.resolved_company_id))
        payload = {
            "company_id": int(decision.resolved_company_id),
            "plan_id": int(plan_id) if plan_id else None,
            "objective": str(objective or "").strip(),
            "type": str(okr_type or "").strip(),
            "owner": str(owner or "").strip() or None,
            "deadline": _parse_optional_deadline(deadline),
            "observations": str(observations or "").strip() or None,
            "directionals": directionals or None,
        }
        okr = okr_global_schema.load(payload)
        db.session.add(okr)
        db.session.commit()
        record_mutation_success(
            action="create",
            company_id=int(decision.resolved_company_id),
            user_id=int(principal["user_id"]),
            tool_name="create_global_okr",
            domain="strategy",
            metadata={"plan_id": plan_id, "okr_scope": "global", "okr_id": okr.id},
        )
        return {"success": True, "okr": okr_global_schema.dump(okr)}
    except Exception as exc:
        db.session.rollback()
        return {"success": False, "error": str(exc)}


def create_area_okr(
    objective: str,
    okr_type: str,
    company_id: int | None = None,
    plan_id: int | None = None,
    department: str | None = None,
    owner: str | None = None,
    deadline: str | None = None,
    observations: str | None = None,
    linked_okr_ids: list[int] | None = None,
):
    """Cria um OKR por área tenant-safe no domínio estratégico."""
    selected_company_id = int(company_id) if company_id is not None else get_active_company_id()
    if not selected_company_id:
        return {"success": False, "error": "Erro: Contexto de empresa nao identificado."}

    principal, decision = _authorize_strategy_mcp(
        tool_name="create_area_okr",
        action="create",
        company_id=selected_company_id,
        risk="medium",
        required_permissions=("okrs.area.create",),
    )
    if not decision.allowed:
        return {"success": False, "error": decision.reason, "policy": decision.to_audit_event()}

    limit_decision = evaluate_mutation_limit(
        action="create",
        company_id=decision.resolved_company_id,
        user_id=principal.get("user_id"),
    )
    if not limit_decision.allowed:
        return {"success": False, "error": limit_decision.reason, "limits": limit_decision.to_dict()}

    try:
        normalized_linked_ids = _normalize_linked_okr_ids(linked_okr_ids)
        _ensure_plan_belongs_to_company(plan_id, int(decision.resolved_company_id))
        _ensure_global_okrs_belong_to_company(normalized_linked_ids, int(decision.resolved_company_id))
        payload = {
            "company_id": int(decision.resolved_company_id),
            "plan_id": int(plan_id) if plan_id else None,
            "objective": str(objective or "").strip(),
            "linked_okr_ids": normalized_linked_ids,
            "type": str(okr_type or "").strip(),
            "department": str(department or "").strip() or None,
            "owner": str(owner or "").strip() or None,
            "deadline": _parse_optional_deadline(deadline),
            "observations": str(observations or "").strip() or None,
        }
        okr = okr_area_schema.load(payload)
        db.session.add(okr)
        db.session.commit()
        record_mutation_success(
            action="create",
            company_id=int(decision.resolved_company_id),
            user_id=int(principal["user_id"]),
            tool_name="create_area_okr",
            domain="strategy",
            metadata={"plan_id": plan_id, "okr_scope": "area", "okr_id": okr.id},
        )
        return {"success": True, "okr": okr_area_schema.dump(okr)}
    except Exception as exc:
        db.session.rollback()
        return {"success": False, "error": str(exc)}


def create_global_key_result(
    okr_global_id: int,
    label: str,
    company_id: int | None = None,
    metric: str | None = None,
    target: str | None = None,
    deadline: str | None = None,
    owner: str | None = None,
):
    """Cria um Key Result para um OKR global no tenant ativo."""
    from models import KeyResult
    from schemas.okr import key_result_schema

    selected_company_id = int(company_id) if company_id is not None else get_active_company_id()
    if not selected_company_id:
        return {"success": False, "error": "Erro: Contexto de empresa nao identificado."}

    principal, decision = _authorize_strategy_mcp(
        tool_name="create_global_key_result",
        action="create",
        company_id=selected_company_id,
        risk="medium",
        required_permissions=("okrs.key_results.create",),
    )
    if not decision.allowed:
        return {"success": False, "error": decision.reason, "policy": decision.to_audit_event()}

    limit_decision = evaluate_mutation_limit(
        action="create",
        company_id=decision.resolved_company_id,
        user_id=principal.get("user_id"),
    )
    if not limit_decision.allowed:
        return {"success": False, "error": limit_decision.reason, "limits": limit_decision.to_dict()}

    try:
        _ensure_global_okr_belongs_to_company(int(okr_global_id), int(decision.resolved_company_id))
        payload = {
            "okr_global_id": int(okr_global_id),
            "label": str(label or "").strip(),
            "metric": str(metric or "").strip() or None,
            "target": str(target or "").strip() or None,
            "deadline": _parse_optional_deadline(deadline),
            "owner": str(owner or "").strip() or None,
        }
        kr = key_result_schema.load(payload)
        db.session.add(kr)
        db.session.commit()
        record_mutation_success(
            action="create",
            company_id=int(decision.resolved_company_id),
            user_id=int(principal["user_id"]),
            tool_name="create_global_key_result",
            domain="strategy",
            metadata={"okr_scope": "global", "okr_id": int(okr_global_id), "key_result_id": kr.id},
        )
        return {"success": True, "key_result": key_result_schema.dump(kr)}
    except Exception as exc:
        db.session.rollback()
        return {"success": False, "error": str(exc)}


def create_area_key_result(
    okr_area_id: int,
    label: str,
    company_id: int | None = None,
    metric: str | None = None,
    target: str | None = None,
    deadline: str | None = None,
    owner: str | None = None,
):
    """Cria um Key Result para um OKR por área no tenant ativo."""
    from schemas.okr import key_result_area_schema

    selected_company_id = int(company_id) if company_id is not None else get_active_company_id()
    if not selected_company_id:
        return {"success": False, "error": "Erro: Contexto de empresa nao identificado."}

    principal, decision = _authorize_strategy_mcp(
        tool_name="create_area_key_result",
        action="create",
        company_id=selected_company_id,
        risk="medium",
        required_permissions=("okrs.key_results.create",),
    )
    if not decision.allowed:
        return {"success": False, "error": decision.reason, "policy": decision.to_audit_event()}

    limit_decision = evaluate_mutation_limit(
        action="create",
        company_id=decision.resolved_company_id,
        user_id=principal.get("user_id"),
    )
    if not limit_decision.allowed:
        return {"success": False, "error": limit_decision.reason, "limits": limit_decision.to_dict()}

    try:
        _ensure_area_okr_belongs_to_company(int(okr_area_id), int(decision.resolved_company_id))
        payload = {
            "okr_area_id": int(okr_area_id),
            "label": str(label or "").strip(),
            "metric": str(metric or "").strip() or None,
            "target": str(target or "").strip() or None,
            "deadline": _parse_optional_deadline(deadline),
            "owner": str(owner or "").strip() or None,
        }
        kr = key_result_area_schema.load(payload)
        db.session.add(kr)
        db.session.commit()
        record_mutation_success(
            action="create",
            company_id=int(decision.resolved_company_id),
            user_id=int(principal["user_id"]),
            tool_name="create_area_key_result",
            domain="strategy",
            metadata={"okr_scope": "area", "okr_id": int(okr_area_id), "key_result_id": kr.id},
        )
        return {"success": True, "key_result": key_result_area_schema.dump(kr)}
    except Exception as exc:
        db.session.rollback()
        return {"success": False, "error": str(exc)}


__all__ = [
    "list_plans",
    "get_plan_diagnostics",
    "update_plan_section",
    "create_global_okr",
    "create_area_okr",
    "create_global_key_result",
    "create_area_key_result",
]
