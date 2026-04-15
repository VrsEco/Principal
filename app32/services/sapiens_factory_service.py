from __future__ import annotations

import re
import unicodedata
from typing import Any

from services.ai_capability_blueprint_service import AICapabilityBlueprintService
from services.sapiens_factory_registry_service import SapiensFactoryRegistryService
from services.sapiens_factory_schema import FactoryActorContext, FactoryChangeType, FactoryTargetLayer, SapiensFactoryChangeRequest


class SapiensFactoryService:
    """Camada determinística da Sapiens Factory para diagnóstico, classificação e plano inicial."""

    _CHANGE_TYPE_HINTS: tuple[tuple[str, FactoryChangeType], ...] = (
        ("criar", "create"),
        ("nova func", "create"),
        ("nova capacidade", "create"),
        ("alter", "alter"),
        ("ativar", "activate"),
        ("desativ", "deactivate"),
        ("manuten", "fix"),
        ("erro", "fix"),
        ("corrig", "fix"),
        ("refator", "refactor"),
        ("cogni", "refactor"),
        ("diagnos", "diagnose"),
    )

    _LAYER_HINTS: tuple[tuple[str, FactoryTargetLayer], ...] = (
        ("service", "service"),
        ("tool", "tool_contract"),
        ("contrato", "tool_contract"),
        ("mcp", "rest_mcp"),
        ("api", "rest_mcp"),
        ("workflow", "workflow"),
        ("fluxo", "workflow"),
        ("sapiens", "ui_sapiens"),
        ("ui", "ui_sapiens"),
        ("tela", "ui_sapiens"),
    )

    @staticmethod
    def _normalize_text(value: str) -> str:
        text = unicodedata.normalize("NFKD", str(value or "").strip().lower())
        text = "".join(ch for ch in text if not unicodedata.combining(ch))
        return re.sub(r"\s+", " ", text)

    @classmethod
    def _infer_change_type(cls, payload: SapiensFactoryChangeRequest) -> FactoryChangeType:
        if payload.change_type:
            return payload.change_type
        normalized = cls._normalize_text(payload.request_text)
        for hint, change_type in cls._CHANGE_TYPE_HINTS:
            if hint in normalized:
                return change_type
        return "diagnose"

    @classmethod
    def _infer_target_layers(cls, payload: SapiensFactoryChangeRequest) -> list[FactoryTargetLayer]:
        if payload.target_layers:
            return list(dict.fromkeys(payload.target_layers))
        normalized = cls._normalize_text(payload.request_text)
        layers: list[FactoryTargetLayer] = []
        for hint, layer in cls._LAYER_HINTS:
            if hint in normalized and layer not in layers:
                layers.append(layer)
        return layers or ["workflow", "service", "tool_contract"]

    @classmethod
    def _infer_domain(cls, payload: SapiensFactoryChangeRequest) -> str:
        if payload.domain:
            return payload.domain
        normalized = cls._normalize_text(payload.request_text)
        if "finance" in normalized or "resultado financeiro" in normalized or "resultados financeiros" in normalized:
            return "finance"
        if "planej" in normalized or "estrateg" in normalized:
            return "strategy"
        if "rotina" in normalized or "trabalho" in normalized:
            return "routine"
        if "process" in normalized:
            return "processes"
        if "sapiens" in normalized or "llm" in normalized or "mcp" in normalized:
            return "engineering"
        return "engineering"

    @classmethod
    def _infer_target_object(cls, payload: SapiensFactoryChangeRequest) -> str | None:
        if payload.target_object:
            return payload.target_object
        text = payload.request_text
        match = re.search(r"(workflow|tool|service|api|mcp)\s+([A-Za-z0-9_\-\.]+)", text, flags=re.IGNORECASE)
        if match:
            return f"{match.group(1).lower()}:{match.group(2)}"
        normalized = cls._normalize_text(text)
        if "resultado financeiro" in normalized or "resultados financeiros" in normalized:
            return "capability:financial_results_query"
        return None

    @classmethod
    def _calculate_risk(cls, change_type: FactoryChangeType, domain: str, layers: list[FactoryTargetLayer]) -> str:
        if domain == "finance":
            return "high"
        if change_type in {"activate", "deactivate"}:
            return "high"
        if "rest_mcp" in layers and "service" in layers:
            return "high"
        if change_type == "fix" and "tool_contract" in layers:
            return "medium"
        if change_type in {"fix", "refactor", "create"} and "workflow" in layers:
            return "medium"
        return "low"

    @classmethod
    def _requires_human_gate(cls, change_type: FactoryChangeType, risk: str, layers: list[FactoryTargetLayer]) -> bool:
        if change_type in {"activate", "deactivate"}:
            return True
        if risk in {"high", "critical"}:
            return True
        return "rest_mcp" in layers and "workflow" in layers

    @classmethod
    def _recommend_artifacts(cls, layers: list[FactoryTargetLayer]) -> list[str]:
        mapping = {
            "service": "service_spec",
            "tool_contract": "tool_contract",
            "rest_mcp": "rest_mcp_contract",
            "workflow": "workflow_definition",
            "ui_sapiens": "ui_wizard_entrypoint",
        }
        return [mapping[layer] for layer in layers if layer in mapping]

    @classmethod
    def _build_next_steps(cls, *, change_type: FactoryChangeType, layers: list[FactoryTargetLayer], risk: str, target_object: str | None) -> list[str]:
        steps = [
            "Entender intenção e normalizar o pedido técnico em formulário canônico.",
            "Mapear impacto nas camadas afetadas e dependências da capability.",
        ]
        if target_object:
            steps.append(f"Traçar dependências do alvo identificado: {target_object}.")
        if "service" in layers:
            steps.append("Revisar ou criar a regra de negócio canônica no Service.")
        if "tool_contract" in layers:
            steps.append("Revisar ou publicar Tool + contrato com validação rigorosa.")
        if "rest_mcp" in layers:
            steps.append("Expor a capability em REST/MCP com tenant-scope, RBAC e auditoria.")
        if "workflow" in layers:
            steps.append("Orquestrar o workflow assistido com confirmação explícita quando necessário.")
        if "ui_sapiens" in layers:
            steps.append("Conectar a capability no Sapiens/UI com wizard e trilha de operação.")
        if change_type in {"activate", "deactivate"}:
            steps.append("Executar ativação/desativação somente com confirmação humana e rollback previsto.")
        if risk in {"high", "critical"}:
            steps.append("Validar governança, human gate e readiness antes da execução controlada.")
        return steps

    @classmethod
    def build_runtime_context(cls, actor: FactoryActorContext) -> dict[str, Any]:
        registry = SapiensFactoryRegistryService.build_registry_snapshot()
        return {
            "actor": actor.model_dump(mode="json"),
            "registry_summary": registry["summary"],
            "allowed_execution_modes": ["diagnose", "plan", "prepare", "execute_controlled"],
            "guardrails": [
                "Toda mudança sensível exige tenant-scope, RBAC e trilha de auditoria.",
                "A LLM interpreta; a execução real continua determinística e governada no APP32.",
                "Ativar/desativar requer human gate explícito.",
            ],
        }

    @classmethod
    def assess_change_request(cls, raw_payload: dict[str, Any], *, actor_context: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = SapiensFactoryChangeRequest.model_validate(raw_payload)
        actor = FactoryActorContext.model_validate(actor_context or {})
        change_type = cls._infer_change_type(payload)
        layers = cls._infer_target_layers(payload)
        domain = cls._infer_domain(payload)
        target_object = cls._infer_target_object(payload)
        risk = cls._calculate_risk(change_type, domain, layers)
        human_gate = cls._requires_human_gate(change_type, risk, layers)
        capability_trace = None
        related_capabilities: list[str] = []
        if target_object and ":" in target_object:
            _, capability_key = target_object.split(":", 1)
            capability_trace = SapiensFactoryRegistryService.trace_capability_dependencies(capability_key)
            if capability_trace and capability_trace.get("found"):
                related_capabilities = [capability_trace["capability"]["key"]]
                related_capabilities.extend(item["key"] for item in capability_trace.get("dependencies", []))

        normalized_request = payload.model_copy(update={
            "change_type": change_type,
            "target_layers": layers,
            "target_object": target_object,
            "domain": domain,
            "company_id": payload.company_id or actor.company_id,
        }).model_dump(mode="json")
        artifacts = cls._recommend_artifacts(layers)
        next_steps = cls._build_next_steps(change_type=change_type, layers=layers, risk=risk, target_object=target_object)
        blueprint = AICapabilityBlueprintService.build_blueprint(
            title=payload.desired_outcome or payload.request_text[:80],
            domain=domain,
            target_layers=layers,
            risk=risk,
            human_gate_required=human_gate,
            target_object=target_object,
            execution_mode=payload.execution_mode,
        )
        return {
            "summary": {
                "change_type": change_type,
                "domain": domain,
                "risk": risk,
                "human_gate_required": human_gate,
                "execution_mode": payload.execution_mode,
            },
            "target": {"object": target_object, "layers": layers},
            "artifacts": artifacts,
            "recommended_artifacts": artifacts,
            "next_steps": next_steps,
            "actor_context": actor.model_dump(mode="json"),
            "runtime_context": cls.build_runtime_context(actor),
            "capability_trace": capability_trace,
            "related_capabilities": related_capabilities,
            "risk_level": risk,
            "human_gate_required": human_gate,
            "request": normalized_request,
            "blueprint": blueprint,
            "backlog_plan": blueprint.get("backlog_plan") or [],
        }
