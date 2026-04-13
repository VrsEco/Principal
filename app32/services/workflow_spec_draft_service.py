from __future__ import annotations

import re
import unicodedata
from typing import Any

from services.workflow_request_schema import WorkflowRequestPayload


class WorkflowSpecDraftService:
    VERB_ALIASES = {
        "cadastrar": "create",
        "criar": "create",
        "novo": "create",
        "nova": "create",
        "consultar": "read",
        "listar": "list",
        "obter": "get",
        "buscar": "get",
        "diagnosticar": "diagnose",
        "diagnostico": "diagnose",
        "resumir": "summarize",
        "resumo": "summarize",
        "concluir": "complete",
        "finalizar": "complete",
        "encerrar": "complete",
        "atualizar": "update",
        "alterar": "update",
        "aprovar": "approve",
        "rejeitar": "reject",
        "agendar": "schedule",
        "iniciar": "start",
        "acompanhar": "track",
    }

    @classmethod
    def _slugify(cls, value: str) -> str:
        normalized = unicodedata.normalize("NFKD", str(value or ""))
        ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
        cleaned = re.sub(r"[^a-zA-Z0-9]+", "_", ascii_text).strip("_").lower()
        return re.sub(r"_+", "_", cleaned)

    @classmethod
    def _split_csv(cls, value: str | None) -> list[str]:
        if not value:
            return []
        parts = re.split(r"[,\n;/]+", value)
        return [part.strip().lower() for part in parts if part and part.strip()]

    @classmethod
    def _suggest_action_key(cls, payload: WorkflowRequestPayload) -> str:
        title_slug = cls._slugify(payload.title)
        domain_key = cls._slugify(payload.business_domain) or "workflow"
        tokens = title_slug.split("_")
        verb = "run"
        if tokens:
            verb = cls.VERB_ALIASES.get(tokens[0], "")
        if not verb:
            verb = {"query": "read", "action": "execute", "hybrid": "orchestrate"}.get(payload.execution_profile, "run")
        object_tokens = [token for token in tokens[1:] if token not in {"de", "da", "do", "e", "para"}]
        object_slug = "_".join(object_tokens[:4]).strip("_")
        return f"{domain_key}.{verb}{'_' + object_slug if object_slug else ''}"

    @classmethod
    def _build_tools(cls, payload: WorkflowRequestPayload) -> list[dict[str, Any]]:
        tools = [
            {"name": "collect_workflow_inputs", "status": "proposed", "note": "Coleta progressiva dos dados informados pelo usuário."},
            {"name": "validate_workflow_payload", "status": "proposed", "note": "Validação técnica e de negócio antes da execução."},
        ]
        if payload.requires_human_confirmation != "no":
            tools.append({"name": "confirm_workflow_execution", "status": "proposed", "note": "Human gate / confirmação antes de executar."})

        systems = " ".join(cls._split_csv(payload.systems_involved))
        if "postgresql" in systems or "postgres" in systems or "banco" in systems:
            tools.append({"name": "query_database", "status": "candidate", "note": "Consulta segura e contextualizada por company_id."})
        if "erp" in systems:
            tools.append({"name": "erp_operation_bridge", "status": "candidate", "note": "Ponte de execução/consulta em ERP."})
        if "mcp" in systems:
            tools.append({"name": "open_mcp_console", "status": "candidate", "note": "Acesso a capacidades MCP relacionadas ao fluxo."})
        return tools

    @classmethod
    def _build_api_mcp_contracts(cls, payload: WorkflowRequestPayload, action_key: str) -> list[dict[str, Any]]:
        items = [
            {"name": action_key, "kind": "MCP", "status": "proposed", "note": "Ação canônica sugerida para o workflow."},
        ]
        systems = cls._split_csv(payload.systems_involved)
        if any("erp" in system for system in systems):
            items.append({"name": "ERP integration contract", "kind": "REST", "status": "candidate", "note": "Contrato REST/adapter para ERP a ser definido."})
        if any("finance" in system or "financeiro" in system for system in systems):
            items.append({"name": "financial_data_contract", "kind": "MCP", "status": "candidate", "note": "Capacidade financeira a ser vinculada ao fluxo."})
        return items

    @classmethod
    def _build_permissions(cls, payload: WorkflowRequestPayload) -> list[dict[str, Any]]:
        items = [
            {"name": "tenant_scope", "status": "required", "note": "Toda execução deve respeitar company_id."},
            {"name": "operator_role_review", "status": "proposed", "note": "Validar RBAC fino antes da publicação."},
        ]
        if payload.requires_human_confirmation != "no" or payload.sensitivity_level in {"high", "critical"}:
            items.append({"name": "human_gate", "status": "required", "note": "Fluxo deve confirmar com humano antes de executar ações sensíveis."})
        return items

    @classmethod
    def _build_configurations(cls, payload: WorkflowRequestPayload) -> list[dict[str, Any]]:
        configs = [
            {"name": "workflow_runtime_config", "status": "proposed", "note": "Configuração operacional específica do workflow."},
        ]
        for channel in cls._split_csv(payload.desired_channels):
            configs.append({"name": f"channel:{channel}", "status": "candidate", "note": f"Validar configuração do canal {channel}."})
        return configs

    @classmethod
    def _build_open_questions(cls, payload: WorkflowRequestPayload) -> list[str]:
        questions: list[str] = []
        if payload.requires_human_confirmation == "unknown":
            questions.append("Confirmar se o fluxo exige human gate antes da execução.")
        if not payload.systems_involved:
            questions.append("Identificar sistemas/API/MCP efetivamente envolvidos.")
        if not payload.dependencies:
            questions.append("Mapear dependências, credenciais e restrições operacionais.")
        if payload.execution_profile == "hybrid":
            questions.append("Separar claramente etapas de consulta e etapas de ação.")
        return questions or ["Validar naming final, RBAC e contrato operacional antes da publicação."]

    @classmethod
    def build_draft(cls, raw_payload: dict[str, Any]) -> dict[str, Any]:
        payload = WorkflowRequestPayload.model_validate(raw_payload)
        channels = cls._split_csv(payload.desired_channels)
        suggested_action_key = cls._suggest_action_key(payload)
        suggested_domain_key = cls._slugify(payload.business_domain) or "workflow"
        return {
            "draft_mode": "heuristic_ai_assisted",
            "workflow_title": payload.title,
            "suggested_domain_key": suggested_domain_key,
            "suggested_action_key": suggested_action_key,
            "execution_profile": payload.execution_profile,
            "sensitivity_level": payload.sensitivity_level,
            "requires_human_confirmation": payload.requires_human_confirmation,
            "channels": channels,
            "target_users": cls._split_csv(payload.target_users),
            "api_mcp_contracts": cls._build_api_mcp_contracts(payload, suggested_action_key),
            "tools": cls._build_tools(payload),
            "permissions": cls._build_permissions(payload),
            "configurations": cls._build_configurations(payload),
            "open_questions": cls._build_open_questions(payload),
        }
