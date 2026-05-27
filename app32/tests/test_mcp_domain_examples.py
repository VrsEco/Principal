from pathlib import Path

import pytest
from pydantic import ValidationError

from src.core.mcp_domain_example_tools import register_domain_example_tools
from src.intelligence.mcp_contracts import (
    APP32_DOMAIN_EXAMPLES_MANIFEST,
    MCPDomainExampleFlow,
    MCPDomainExampleStep,
    MCPDomainExamplesManifest,
)


DOC = Path(__file__).resolve().parents[1] / "docs" / "governance" / "ai_mcp_domain_examples.md"


class _FakeMCP:
    def __init__(self):
        self.registered = {}

    def tool(self, *args, **kwargs):
        def decorator(func):
            self.registered[kwargs.get("name") or func.__name__] = func
            return func

        if args and callable(args[0]):
            return decorator(args[0])
        return decorator


def test_domain_examples_manifest_covers_routine_strategy_finance():
    manifest = APP32_DOMAIN_EXAMPLES_MANIFEST
    domains = {example.domain for example in manifest.examples}

    assert manifest.version == "app32.ai-mcp.domain-examples.v1"
    assert domains == {"routine", "strategy", "finance"}
    assert len(manifest.examples) == 6
    assert len(manifest.get_domain_examples("routine")) == 2
    assert len(manifest.get_domain_examples("strategy")) == 2
    assert len(manifest.get_domain_examples("finance")) == 2


def test_domain_examples_security_boundaries_are_enforced_in_manifest():
    routine_examples = APP32_DOMAIN_EXAMPLES_MANIFEST.get_domain_examples("routine")
    strategy_examples = APP32_DOMAIN_EXAMPLES_MANIFEST.get_domain_examples("strategy")
    finance_examples = APP32_DOMAIN_EXAMPLES_MANIFEST.get_domain_examples("finance")

    assert all(example.surface != "analytics" for example in routine_examples)
    assert all("strategy_plan_diagnostics" in example.related_analysis_ids for example in strategy_examples)
    redirect = next(example for example in strategy_examples if example.example_id == "strategy_analysis_to_mutation_redirect")
    assert any(step.tool_name == "update_plan_section" for step in redirect.steps if step.kind == "execute")
    assert all(example.surface in {"admin", "analytics"} for example in finance_examples)
    assert all(example.company_scope == "explicit_company_id" for example in finance_examples)
    assert all(set(example.allowed_profiles) <= {"administrador", "admin_tecnico"} for example in finance_examples)
    assert any(example.mode == "mutate" and example.human_gate_required for example in finance_examples)


def test_domain_examples_tool_returns_manifest_domain_and_specific_example():
    mcp = _FakeMCP()
    register_domain_example_tools(mcp)
    tool = mcp.registered["describe_app32_domain_examples_tool"]

    manifest_payload = tool()
    assert manifest_payload["success"] is True
    assert manifest_payload["data"]["version"] == "app32.ai-mcp.domain-examples.v1"

    domain_payload = tool(domain="finance")
    assert domain_payload["success"] is True
    assert len(domain_payload["data"]) == 2
    assert all(item["domain"] == "finance" for item in domain_payload["data"])

    example_payload = tool(example_id="strategy_plan_diagnostics_analysis")
    assert example_payload["success"] is True
    assert example_payload["data"]["domain"] == "strategy"
    assert example_payload["data"]["example_id"] == "strategy_plan_diagnostics_analysis"

    missing_domain = tool(domain="unknown")
    assert missing_domain["success"] is False
    assert missing_domain["error"]["code"] == "domain_examples_not_found"

    missing_example = tool(example_id="missing")
    assert missing_example["success"] is False
    assert missing_example["error"]["code"] == "domain_example_not_found"


def test_domain_examples_doc_contains_manifest_tool_and_smoke():
    text = DOC.read_text(encoding="utf-8")

    assert "Exemplos Oficiais de Fluxos IA/MCP por Domínio" in text
    assert "APP32_DOMAIN_EXAMPLES_MANIFEST" in text
    assert "describe_app32_domain_examples_tool" in text
    assert "AI_MCP_DOMAIN_EXAMPLES_OK 6 3" in text
    assert "Não usar surface `user` para finanças" in text


def test_domain_examples_contract_rejects_unsafe_finance_and_incomplete_manifest():
    with pytest.raises(ValidationError):
        MCPDomainExampleFlow(
            example_id="finance_user_flow",
            domain="finance",
            title="Fluxo financeiro inseguro",
            intent="Tentativa inválida de usar finanças em surface user.",
            surface="user",
            allowed_profiles=["administrador"],
            mode="read",
            risk="medium",
            company_scope="active_company",
            preconditions=["Pré-condição válida."],
            steps=[
                MCPDomainExampleStep(
                    order=1,
                    kind="discover",
                    tool_name="list_app32_capabilities",
                    purpose="Descobrir surface.",
                    required_inputs=["company_id"],
                    expected_outcome="Capabilities lidas.",
                ),
                MCPDomainExampleStep(
                    order=2,
                    kind="respond",
                    purpose="Responder.",
                    required_inputs=["result"],
                    expected_outcome="Resposta pronta.",
                ),
            ],
            expected_response_shape=["ok", "result"],
            blocked_by=["Bloqueio de teste."],
            related_contracts=[
                "src.intelligence.mcp_contracts.domain_playbooks",
                "src.intelligence.mcp_contracts.crud_domains",
            ],
            related_analysis_ids=["finance_cash_commitments"],
            notes=["Inseguro."],
        )

    safe_step = MCPDomainExampleStep(
        order=1,
        kind="discover",
        tool_name="list_app32_capabilities",
        purpose="Descobrir capabilities do tenant.",
        required_inputs=["company_id"],
        expected_outcome="Capabilities confirmadas.",
    )
    safe_example = MCPDomainExampleFlow(
        example_id="routine_safe_example",
        domain="routine",
        title="Fluxo seguro de rotina",
        intent="Fluxo mínimo seguro para rotina.",
        surface="user",
        allowed_profiles=["colaborador"],
        mode="read",
        risk="low",
        company_scope="active_company",
        preconditions=["Tenant ativo."],
        steps=[
            safe_step,
            MCPDomainExampleStep(
                order=2,
                kind="respond",
                purpose="Responder com resultado.",
                required_inputs=["result"],
                expected_outcome="Resposta emitida.",
            ),
        ],
        expected_response_shape=["row_count", "items"],
        blocked_by=["Sem company_id."],
        related_contracts=[
            "src.intelligence.mcp_contracts.domain_playbooks",
            "src.intelligence.mcp_contracts.crud_domains",
        ],
        related_analysis_ids=[],
        notes=["Fluxo seguro."],
    )

    with pytest.raises(ValidationError):
        MCPDomainExamplesManifest(examples=[safe_example])
