from __future__ import annotations

import re
from typing import Any


class AICapabilityBlueprintService:
    """Contrato canônico de capability para IA/automação no APP32."""

    @staticmethod
    def _slugify(value: str) -> str:
        normalized = re.sub(r"[^a-zA-Z0-9]+", "_", str(value or "").strip().lower()).strip("_")
        return normalized or "capability"

    @classmethod
    def build_blueprint(
        cls,
        *,
        title: str,
        domain: str,
        target_layers: list[str] | None = None,
        risk: str = "medium",
        human_gate_required: bool = False,
        target_object: str | None = None,
        execution_mode: str = "diagnose",
    ) -> dict[str, Any]:
        layers = list(dict.fromkeys(target_layers or ["service", "tool_contract", "rest_mcp", "workflow"]))
        capability_key = target_object or f"capability:{cls._slugify(domain)}_{cls._slugify(title)}"
        normalized_key = capability_key.split(":", 1)[-1]
        action_key = normalized_key.replace("__", "_").replace("-", "_")

        surfaces = {
            "service": "service" in layers,
            "tool_contract": "tool_contract" in layers,
            "rest_mcp": "rest_mcp" in layers,
            "workflow": "workflow" in layers,
            "ui_sapiens": "ui_sapiens" in layers,
        }
        artifacts = [
            {"name": "service", "status": "required" if surfaces["service"] else "optional", "path_hint": "services/<domain>_service.py"},
            {"name": "schema", "status": "required", "path_hint": "schemas/<domain>.py"},
            {"name": "tool_contract", "status": "required" if surfaces["tool_contract"] else "optional", "path_hint": "src/core/mcp_<capability>.py"},
            {"name": "rest_mcp", "status": "required" if surfaces["rest_mcp"] else "optional", "path_hint": "api/routes/<domain>.py"},
            {"name": "workflow", "status": "required" if surfaces["workflow"] else "optional", "path_hint": "src/intelligence/workflows/<module>.py"},
            {"name": "ui_entrypoint", "status": "required" if surfaces["ui_sapiens"] else "optional", "path_hint": "templates/modules/operations/<capability>.html"},
            {"name": "tests", "status": "required", "path_hint": "tests/test_<capability>.py"},
            {"name": "documentation", "status": "required", "path_hint": "docs/specifications/<capability>.md"},
        ]
        backlog_plan = [
            {
                "step": 1,
                "title": "Formalizar capability",
                "description": "Definir escopo, domínio, company_id, risco, human gate e surfaces obrigatórias.",
            },
            {
                "step": 2,
                "title": "Implementar contrato determinístico",
                "description": "Publicar schema, service e tool/REST/MCP conforme blueprint canônico.",
            },
            {
                "step": 3,
                "title": "Conectar workflow/UI",
                "description": "Integrar workflow, Sapiens e/ou UI operacional mantendo rastreabilidade.",
            },
            {
                "step": 4,
                "title": "Validar readiness",
                "description": "Executar testes, auditoria, observabilidade e checklist de rollout.",
            },
        ]
        return {
            "capability_key": normalized_key,
            "title": title,
            "domain": domain,
            "action_key": action_key,
            "risk": risk,
            "execution_mode": execution_mode,
            "human_gate_required": human_gate_required,
            "target_layers": layers,
            "surfaces": surfaces,
            "governance": {
                "tenant_scope": "required",
                "rbac": "required",
                "audit_trail": "required",
                "human_gate": "required" if human_gate_required else "conditional",
            },
            "contracts": {
                "service": f"{domain}_service.{action_key}",
                "tool_contract": f"{action_key}" if surfaces["tool_contract"] else None,
                "rest_endpoint": f"/api/{domain}/{action_key.replace('_', '-')}" if surfaces["rest_mcp"] else None,
                "mcp_tool": action_key if surfaces["rest_mcp"] else None,
                "workflow_code": action_key if surfaces["workflow"] else None,
            },
            "artifacts": artifacts,
            "backlog_plan": backlog_plan,
        }
