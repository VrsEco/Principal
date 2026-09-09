from pathlib import Path
from types import SimpleNamespace
import sys

import pytest
from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from schemas.contracts import CommercialOfferContractV1, ContractCatalogItemInput
from services.contracts_catalog_service import ContractsCatalogService
from services.contracts_service import ContractService
import services.contracts_catalog_service as contracts_catalog_service_module


def _commercial_contract(**overrides):
    payload = {
        "version": "1.0",
        "status": "active",
        "offer_role": "canonical_offer",
        "method_track": "urgent_need",
        "icp_summary": "PMEs com dor relevante e patrocinador com poder de decisão.",
        "buying_triggers": ["Risco ou perda relevante exige resposta objetiva."],
        "exclusion_criteria": ["Ausência de patrocinador."],
        "sponsor_required": "Sócio, diretor ou gestor autorizado",
        "required_participants": ["Responsável do projeto"],
        "problem_statement": "Dor empresarial específica com impacto relevante.",
        "promised_outcome": "Dor tratada com escopo, evidência e decisão rastreável.",
        "scope_in": ["Diagnóstico da causa", "Execução do projeto"],
        "scope_out": ["Atividades técnicas reguladas sem parceiro habilitado"],
        "deliverables": [
            {
                "key": "solution",
                "name": "Solução implantada",
                "description": "Intervenção acordada executada.",
                "acceptance_criterion": "Aceite registrado pelo responsável.",
                "evidence_type": "registro_app32",
                "responsible_role": "Responsável do projeto",
            }
        ],
        "client_dependencies": ["Disponibilizar dados e responsáveis"],
        "versus_capabilities": ["Consultor Versus e APP32"],
        "execution_model": "project",
        "process_links": [
            {
                "process_id": 10,
                "role": "delivery",
                "required": True,
                "owner_verified_at": "2026-09-09T12:00:00Z",
            }
        ],
        "indicator_contract": [
            {
                "indicator_key": "delivery_on_time",
                "name": "Entregas no prazo",
                "purpose": "Controlar previsibilidade da intervenção.",
                "frequency": "semanal",
                "responsible_role": "Responsável do projeto",
                "target_rule": "100% dos marcos críticos no prazo",
                "source": "APP32",
            }
        ],
        "business_review_policy": "Obrigatório antes do encerramento da Necessidade Urgente.",
        "closure_criteria": ["Entregáveis aceitos", "Business Review registrado"],
        "evidence_requirements": ["Aceite e resultado registrados"],
        "pricing_policy": "Preço aprovado por usuário autorizado conforme esforço e risco.",
        "approved_by_user_id": 3,
        "approved_at": "2026-09-09T12:00:00Z",
    }
    payload.update(overrides)
    return payload


def test_active_commercial_contract_requires_human_approval():
    payload = _commercial_contract(approved_by_user_id=None, approved_at=None)

    with pytest.raises(ValidationError, match="aprovação humana"):
        CommercialOfferContractV1.model_validate(payload)


def test_active_commercial_contract_requires_verified_process_owner():
    payload = _commercial_contract()
    payload["process_links"][0]["owner_verified_at"] = None

    with pytest.raises(ValidationError, match="dono verificado"):
        CommercialOfferContractV1.model_validate(payload)


def test_catalog_schema_and_service_preserve_structured_commercial_metadata():
    payload = {
        "company_id": 9,
        "parent_id": 20,
        "code_suffix": "001",
        "name": "Intervenção de Necessidade Urgente",
        "item_kind": "service",
        "description": "Resolve uma dor específica por projeto ou programa.",
        "unit_code": "projeto",
        "metadata_json": {
            "service_code": "17.01",
            "commercial_contract_enforced": True,
            "commercial_contract_v1": _commercial_contract(),
        },
    }

    parsed = ContractCatalogItemInput(**payload)
    _, _, _, metadata = ContractsCatalogService._normalize_item_payload(
        level_depth=2,
        item_kind=parsed.item_kind,
        description=parsed.description,
        unit_code=parsed.unit_code,
        metadata_json=parsed.metadata_json,
    )

    assert metadata["commercial_contract_enforced"] is True
    assert metadata["commercial_contract_v1"]["buying_triggers"] == [
        "Risco ou perda relevante exige resposta objetiva."
    ]
    assert metadata["commercial_contract_v1"]["deliverables"][0]["key"] == "solution"
    assert metadata["service_code"] == "17.01"


def test_contract_item_snapshot_preserves_sold_offer_version():
    catalog_item = SimpleNamespace(
        id=30,
        code="1.02.001",
        name="Intervenção de Necessidade Urgente",
        metadata_json={"commercial_contract_v1": _commercial_contract()},
    )
    contract = SimpleNamespace(updated_by_user_id=3, created_by_user_id=2)

    snapshot = ContractService._build_commercial_offer_snapshot(
        catalog_item=catalog_item,
        contract=contract,
    )

    assert snapshot["commercial_contract_version"] == "1.0"
    assert snapshot["method_track"] == "urgent_need"
    assert snapshot["catalog_item_code"] == "1.02.001"
    assert snapshot["materialized_by_user_id"] == 3
    assert snapshot["deliverables"][0]["acceptance_criterion"] == "Aceite registrado pelo responsável."


class _FakeProcessColumn:
    def __init__(self, key):
        self.key = key

    def __eq__(self, value):
        return ("eq", self.key, value)

    def in_(self, values):
        return ("in", self.key, set(values))


class _FakeProcessQuery:
    def __init__(self, rows):
        self.rows = list(rows)
        self.filters = []

    def filter(self, *conditions):
        self.filters.extend(conditions)
        return self

    def all(self):
        result = self.rows
        for operator, key, expected in self.filters:
            if operator == "eq":
                result = [row for row in result if getattr(row, key) == expected]
            if operator == "in":
                result = [row for row in result if getattr(row, key) in expected]
        return result


def _fake_process_model(rows):
    return type(
        "FakeProcess",
        (),
        {
            "id": _FakeProcessColumn("id"),
            "company_id": _FakeProcessColumn("company_id"),
            "query": _FakeProcessQuery(rows),
        },
    )


def test_commercial_contract_rejects_process_from_another_tenant(monkeypatch):
    foreign_process = SimpleNamespace(id=10, company_id=77, is_active=True)
    monkeypatch.setattr(
        contracts_catalog_service_module,
        "Process",
        _fake_process_model([foreign_process]),
    )

    reasons = ContractsCatalogService._get_commercial_process_link_reasons(
        company_id=9,
        contract=CommercialOfferContractV1.model_validate(_commercial_contract()),
    )

    assert reasons == ["Processos vinculados não existem nesta empresa: 10."]


def test_commercial_contract_rejects_inactive_linked_process(monkeypatch):
    inactive_process = SimpleNamespace(id=10, company_id=9, is_active=False)
    monkeypatch.setattr(
        contracts_catalog_service_module,
        "Process",
        _fake_process_model([inactive_process]),
    )

    reasons = ContractsCatalogService._get_commercial_process_link_reasons(
        company_id=9,
        contract=CommercialOfferContractV1.model_validate(_commercial_contract()),
    )

    assert reasons == ["Processos vinculados inativos: 10."]


def test_commercial_contract_rejects_approval_declared_by_another_actor():
    with pytest.raises(ValueError, match="próprio usuário autenticado"):
        ContractsCatalogService._validate_commercial_approval(
            metadata_json={"commercial_contract_v1": _commercial_contract()},
            actor_user_id=99,
        )


def test_commercial_contract_accepts_approval_of_authenticated_actor():
    ContractsCatalogService._validate_commercial_approval(
        metadata_json={"commercial_contract_v1": _commercial_contract()},
        actor_user_id=3,
    )
