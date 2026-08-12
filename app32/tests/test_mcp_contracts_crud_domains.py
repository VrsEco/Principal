import pytest
from pydantic import ValidationError

from src.intelligence.mcp_contracts import (
    APP32_CRUD_CONTRACTS_MANIFEST,
    CRUDDomainContract,
    CRUDOperationContract,
)


def test_app32_crud_contracts_cover_required_domains_and_crud_guidance():
    domains = {contract.domain for contract in APP32_CRUD_CONTRACTS_MANIFEST.domains}

    assert domains == {
        "routine",
        "projects",
        "processes",
        "meetings",
        "real_estate_auctions",
        "finance",
        "strategy",
        "governance",
    }

    for contract in APP32_CRUD_CONTRACTS_MANIFEST.domains:
        assert contract.operations
        assert all(operation.tenant_scope_required for operation in contract.operations)
        assert any(operation.action in {"read", "list", "analyze"} for operation in contract.operations)
        assert any(operation.action in {"create", "update", "execute"} for operation in contract.operations)


def test_finance_contract_is_permission_aware_for_create_update_and_keeps_delete_gated():
    finance = APP32_CRUD_CONTRACTS_MANIFEST.get_domain("finance")

    assert finance is not None
    create_update = [op for op in finance.operations if op.action in {"create", "update"}]
    delete_ops = [op for op in finance.operations if op.action == "delete"]

    assert create_update
    assert delete_ops
    assert all(operation.human_gate_required is False for operation in create_update)
    assert all(operation.risk == "medium" for operation in create_update)
    assert all("colaborador" in operation.allowed_roles for operation in create_update)
    assert all(operation.human_gate_required is True for operation in delete_ops)
    assert all(operation.risk == "critical" for operation in delete_ops)

    with pytest.raises(ValidationError):
        CRUDOperationContract(
            domain="finance",
            action="create",
            operation="finance.entry.create",
            entity="financial_entry",
            description="Tentativa insegura de mutação financeira.",
            allowed_roles=["cliente"],
            required_permissions=["finance.entry.create"],
            human_gate_required=False,
            risk="low",
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
