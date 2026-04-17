import pytest
from pydantic import ValidationError

from src.intelligence.mcp_contracts import (
    APP32_CRUD_CONTRACTS_MANIFEST,
    CRUDDomainContract,
    CRUDOperationContract,
)


def test_app32_crud_contracts_cover_required_domains_and_crud_guidance():
    domains = {contract.domain for contract in APP32_CRUD_CONTRACTS_MANIFEST.domains}

    assert domains == {"routine", "projects", "processes", "meetings", "finance", "strategy"}

    for contract in APP32_CRUD_CONTRACTS_MANIFEST.domains:
        assert contract.operations
        assert all(operation.tenant_scope_required for operation in contract.operations)
        assert any(operation.action in {"read", "list", "analyze"} for operation in contract.operations)
        assert any(operation.action in {"create", "update", "execute"} for operation in contract.operations)


def test_finance_mutations_require_human_gate_and_high_risk():
    finance = APP32_CRUD_CONTRACTS_MANIFEST.get_domain("finance")

    assert finance is not None
    mutating = [op for op in finance.operations if op.action in {"create", "update", "delete", "execute"}]

    assert mutating
    assert all(operation.human_gate_required for operation in mutating)
    assert all(operation.risk in {"high", "critical"} for operation in mutating)

    with pytest.raises(ValidationError):
        CRUDOperationContract(
            domain="finance",
            action="create",
            operation="finance.entry.create",
            entity="financial_entry",
            description="Tentativa insegura de mutação financeira.",
            allowed_roles=["administrador"],
            required_permissions=["finance.entry.create"],
            human_gate_required=False,
            risk="medium",
        )


def test_crud_contracts_forbid_extra_fields_and_domain_mismatch():
    with pytest.raises(ValidationError):
        CRUDOperationContract(
            domain="projects",
            action="read",
            operation="projects.task.read",
            entity="project_task",
            description="Consulta atividade de projeto.",
            allowed_roles=["colaborador"],
            required_permissions=["project.task.read"],
            unexpected="blocked",  # type: ignore[arg-type]
        )

    with pytest.raises(ValidationError):
        CRUDDomainContract(
            domain="projects",
            title="Projetos",
            description="Manifesto inválido com operação de outro domínio.",
            operations=[
                CRUDOperationContract(
                    domain="meetings",
                    action="read",
                    operation="meetings.read",
                    entity="meeting",
                    description="Consulta reunião.",
                    allowed_roles=["colaborador"],
                    required_permissions=["meeting.read"],
                )
            ],
        )
