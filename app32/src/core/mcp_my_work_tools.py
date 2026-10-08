"""Leitura MCP tenant-safe de "Meu trabalho" (atividades do usuário em uma empresa).

Substitui, para o mcp-versus, o uso de ``get_my_work``/``get_tasks_today``: aquelas
ferramentas calculam as empresas por conta própria (todas as empresas ativas para o
papel ``admin``), aceitam ``scope=team|company`` e devolvem texto formatado. Esta
exige ``company_id`` explícito (grant validado pelo wrapper do MCP), devolve somente
atividades **atribuídas diretamente ao usuário** e dados estruturados com limite.
"""

from __future__ import annotations

from datetime import date
from typing import Any

_MAX_LIMIT = 100
_DUE_MODES = ("today", "open")


def _validated_limit(limit: int) -> int:
    if isinstance(limit, bool) or not isinstance(limit, int):
        raise ValueError("limit deve ser um inteiro.")
    if limit < 1 or limit > _MAX_LIMIT:
        raise ValueError(f"limit deve estar entre 1 e {_MAX_LIMIT}.")
    return limit


def _validated_due(due: str) -> str:
    normalized = str(due or "").strip().lower()
    if normalized not in _DUE_MODES:
        raise ValueError(f"due deve ser um de: {', '.join(_DUE_MODES)}.")
    return normalized


def _as_text(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)[:10] if hasattr(value, "isoformat") else str(value)


def _item(activity: dict[str, Any]) -> dict[str, Any]:
    kind = "project_task" if activity.get("type") == "project" else "process_instance"
    return {
        "type": kind,
        "id": activity.get("id"),
        "title": activity.get("title") or "Item sem título",
        "due_date": _as_text(activity.get("deadline_date") or activity.get("deadline")),
        "status": activity.get("status"),
        "is_overdue": bool(activity.get("is_overdue")),
        "container": (
            activity.get("project_title")
            if kind == "project_task"
            else activity.get("process_title") or activity.get("process_name")
        ),
    }


def build_my_work(*, user_id: int, company_id: int, due: str, limit: int, today: date | None = None) -> dict[str, Any]:
    """Monta a resposta; separado do registro para ser testável sem o servidor MCP."""
    from services.my_work.discovery_service import get_user_activities_v2

    today = today or date.today()
    filters: dict[str, Any] = {"delivery_tags": ["open"]}
    if due == "today":
        filters["due_date_end"] = today.isoformat()

    result = get_user_activities_v2(
        user_id=user_id,
        scope="me",
        filters=filters,
        company_ids=[company_id],
        active_company_id=company_id,
    )
    activities = result[0] if isinstance(result, tuple) else result

    # O serviço aplica regras por papel (ex.: cliente enxerga a empresa). Aqui só
    # entram itens da empresa pedida e atribuídos diretamente ao usuário.
    mine = [
        activity
        for activity in (activities or [])
        if activity.get("company_id") == company_id and activity.get("viewer_is_directly_assigned") is True
    ]
    items = [_item(activity) for activity in mine]
    items.sort(key=lambda item: (str(item.get("due_date") or "9999"), str(item.get("type")), int(item.get("id") or 0)))

    return {
        "company_id": company_id,
        "as_of": today.isoformat(),
        "due": due,
        "summary": {
            "total": len(items),
            "overdue": sum(1 for item in items if item["is_overdue"]),
            "project_tasks": sum(1 for item in items if item["type"] == "project_task"),
            "process_instances": sum(1 for item in items if item["type"] == "process_instance"),
        },
        "limit": limit,
        "returned": min(len(items), limit),
        "items": items[:limit],
    }


def register_my_work_mcp_tools(mcp: Any) -> None:
    """Registra somente a leitura das atividades do próprio usuário."""

    @mcp.tool()
    def list_my_work_secure(company_id: int, due: str = "today", limit: int = 50) -> dict[str, Any]:
        """Lista MINHAS atividades abertas (projetos e processos) em uma empresa.

        due='today' traz as que vencem até hoje (inclui atrasadas); due='open' traz todas as abertas.
        Só devolve itens atribuídos diretamente ao usuário autenticado; não cria nem altera nada.
        """

        from src.intelligence.tools_support import get_active_user_id

        bounded_limit = _validated_limit(limit)
        mode = _validated_due(due)
        user_id = get_active_user_id()
        if not isinstance(user_id, int) or user_id <= 0:
            raise PermissionError("Usuário autenticado não identificado.")
        return build_my_work(user_id=user_id, company_id=company_id, due=mode, limit=bounded_limit)
