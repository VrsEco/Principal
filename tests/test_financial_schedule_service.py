from types import SimpleNamespace
from decimal import Decimal

from app32.services.financial_schedule_service import FinancialScheduleService


class _FakeQuery:
    def __init__(self, results):
        self._results = list(results)

    def filter(self, *args, **kwargs):
        return self

    def first(self):
        return self._results.pop(0) if self._results else None


class _FakeColumn:
    def __eq__(self, other):
        return ("eq", other)

    def is_(self, other):
        return ("is", other)


class _FakeChartAccountModel:
    id = _FakeColumn()
    company_id = _FakeColumn()
    deleted_at = _FakeColumn()
    query = None


class _FakeCostCenterModel:
    id = _FakeColumn()
    company_id = _FakeColumn()
    deleted_at = _FakeColumn()
    parent_id = _FakeColumn()
    query = None


def test_validate_schedule_allocations_allows_unchanged_legacy_domain(monkeypatch):
    monkeypatch.setattr(
        FinancialScheduleService,
        "_calculate_schedule_adjustments",
        staticmethod(lambda **kwargs: {"template_amount": 100}),
    )

    from app32.services import financial_schedule_service as module

    _FakeChartAccountModel.query = _FakeQuery([SimpleNamespace(accepts_posting=True)])
    _FakeCostCenterModel.query = _FakeQuery([SimpleNamespace(id=10), None])
    monkeypatch.setattr(module, "FinancialChartAccount", _FakeChartAccountModel)
    monkeypatch.setattr(module, "FinancialCostCenter", _FakeCostCenterModel)
    monkeypatch.setattr(
        module.FinancialService,
        "_resolve_budget_links",
        staticmethod(lambda **kwargs: ({}, None)),
    )
    monkeypatch.setattr(
        module.FinancialDomainEnablementService,
        "_load_source",
        staticmethod(lambda *args, **kwargs: (None, "Projeto/Processo não encontrado para a empresa informada.")),
    )

    metadata_json = {
        "allocations": [
            {
                "chart_account_id": 1,
                "cost_center_id": 10,
                "allocation_type": "amount",
                "allocated_amount": 100,
                "percentage": 100,
                "domain_type": "project",
                "domain_source_id": 999,
                "domain_source_kind": "routine",
            }
        ]
    }
    allowance = FinancialScheduleService._build_legacy_domain_allowance(
        company_id=1,
        template_amount=100,
        due_date=None,
        metadata_json=metadata_json,
    )

    error = FinancialScheduleService._validate_schedule_allocations(
        company_id=1,
        template_amount=100,
        due_date=None,
        metadata_json=metadata_json,
        legacy_domain_allowance=allowance,
    )

    assert error is None


def test_validate_schedule_allocations_allows_unchanged_legacy_domain_from_existing_metadata(monkeypatch):
    monkeypatch.setattr(
        FinancialScheduleService,
        "_calculate_schedule_adjustments",
        staticmethod(lambda **kwargs: {"template_amount": 100}),
    )

    from app32.services import financial_schedule_service as module

    _FakeChartAccountModel.query = _FakeQuery([SimpleNamespace(accepts_posting=True)])
    _FakeCostCenterModel.query = _FakeQuery([SimpleNamespace(id=10), None])
    monkeypatch.setattr(module, "FinancialChartAccount", _FakeChartAccountModel)
    monkeypatch.setattr(module, "FinancialCostCenter", _FakeCostCenterModel)
    monkeypatch.setattr(
        module.FinancialService,
        "_resolve_budget_links",
        staticmethod(lambda **kwargs: ({}, None)),
    )
    monkeypatch.setattr(
        module.FinancialDomainEnablementService,
        "_load_source",
        staticmethod(lambda *args, **kwargs: (None, "Projeto/Processo não encontrado para a empresa informada.")),
    )

    metadata_json = {
        "allocations": [
            {
                "chart_account_id": 1,
                "cost_center_id": 10,
                "allocation_type": "amount",
                "allocated_amount": 100,
                "percentage": 100,
                "domain_type": "project",
                "domain_source_id": 999,
                "domain_source_kind": "routine",
            }
        ]
    }

    error = FinancialScheduleService._validate_schedule_allocations(
        company_id=1,
        template_amount=100,
        due_date=None,
        metadata_json=metadata_json,
        existing_metadata_json=metadata_json,
    )

    assert error is None


def test_validate_schedule_allocations_rejects_new_invalid_domain(monkeypatch):
    monkeypatch.setattr(
        FinancialScheduleService,
        "_calculate_schedule_adjustments",
        staticmethod(lambda **kwargs: {"template_amount": 100}),
    )

    from app32.services import financial_schedule_service as module

    _FakeChartAccountModel.query = _FakeQuery([SimpleNamespace(accepts_posting=True)])
    _FakeCostCenterModel.query = _FakeQuery([SimpleNamespace(id=10), None])
    monkeypatch.setattr(module, "FinancialChartAccount", _FakeChartAccountModel)
    monkeypatch.setattr(module, "FinancialCostCenter", _FakeCostCenterModel)
    monkeypatch.setattr(
        module.FinancialService,
        "_resolve_budget_links",
        staticmethod(lambda **kwargs: ({}, None)),
    )
    monkeypatch.setattr(
        module.FinancialDomainEnablementService,
        "_load_source",
        staticmethod(lambda *args, **kwargs: (None, "Projeto/Processo não encontrado para a empresa informada.")),
    )

    metadata_json = {
        "allocations": [
            {
                "chart_account_id": 1,
                "cost_center_id": 10,
                "allocation_type": "amount",
                "allocated_amount": 100,
                "percentage": 100,
                "domain_type": "project",
                "domain_source_id": 999,
                "domain_source_kind": "routine",
            }
        ]
    }

    error = FinancialScheduleService._validate_schedule_allocations(
        company_id=1,
        template_amount=100,
        due_date=None,
        metadata_json=metadata_json,
        legacy_domain_allowance=None,
    )

    assert error == "Linha 1 do rateio: Projeto/Processo não encontrado para a empresa informada."


def test_normalize_schedule_allocations_keeps_empty_domain_without_routine_default():
    result = FinancialScheduleService._normalize_schedule_allocations(
        company_id=1,
        template_amount=100,
        due_date=None,
        metadata_json={
            "allocations": [
                {
                    "chart_account_id": 1,
                    "cost_center_id": 10,
                    "allocation_type": "amount",
                    "allocated_amount": 100,
                    "percentage": 100,
                    "domain_type": None,
                    "domain_source_id": None,
                }
            ]
        },
    )

    assert result[0]["domain_type"] is None
    assert result[0]["domain_source_id"] is None
    assert result[0]["domain_source_kind"] is None
    assert result[0]["domain_value"] == ""


def test_sync_generated_entries_for_schedule_updates_materialized_entry(monkeypatch):
    schedule = SimpleNamespace(
        id=705,
        company_id=13,
        next_due_date=None,
        first_due_date=None,
    )
    entry = SimpleNamespace(
        id=11,
        entry_code="AG-000412-2025-11-07",
        due_date="2025-11-07",
        issue_date=None,
        competence_date=None,
        occurred_on=None,
        status="posted",
    )

    monkeypatch.setattr(
        FinancialScheduleService,
        "_list_generated_entries",
        staticmethod(lambda **kwargs: [entry]),
    )
    monkeypatch.setattr(
        FinancialScheduleService,
        "_build_entry_payload",
        staticmethod(
            lambda **kwargs: {
                "entry_type": "payable",
                "movement_nature": "debit",
                "origin_type": "manual",
                "status": "posted",
                "review_status": "approved",
                "description": "6/7 - análises laboratoriais 6/7",
                "memo": "memo novo",
                "document_number": "DOC-1",
                "external_reference": "financial_schedule:705",
                "origin_reference": "AG-000412",
                "financial_schedule_id": 705,
                "issue_date": "2025-11-07",
                "competence_date": "2025-11-07",
                "due_date": "2025-11-07",
                "occurred_on": "2025-11-07",
                "original_amount": Decimal("985.34"),
                "currency_code": "BRL",
                "bank_account_id": 9,
                "counterparty_id": 21,
                "chart_account_id": 31,
                "cost_center_id": 41,
                "budget_line_id": None,
                "budget_contract_id": None,
                "budget_document_id": None,
                "activity_id": None,
                "process_instance_id": None,
                "routine_id": None,
                "notes": "nota nova",
                "metadata_json": {"generated_from_schedule": True, "schedule_updated_amount": 985.34},
            }
        ),
    )

    captured_allocations = []

    monkeypatch.setattr(
        FinancialScheduleService,
        "_apply_schedule_allocations",
        staticmethod(
            lambda **kwargs: captured_allocations.append(kwargs["entry_id"]) or None
        ),
    )

    error = FinancialScheduleService._sync_generated_entries_for_schedule(schedule=schedule)

    assert error is None
    assert entry.original_amount == Decimal("985.34")
    assert entry.description == "6/7 - análises laboratoriais 6/7"
    assert entry.financial_schedule_id == 705
    assert entry.external_reference == "financial_schedule:705"
    assert entry.metadata_json["schedule_updated_amount"] == 985.34
    assert captured_allocations == [11]


def test_sync_generated_entries_for_schedule_preserves_entry_due_date_for_payload(monkeypatch):
    schedule = SimpleNamespace(
        id=705,
        company_id=13,
        next_due_date="2026-05-06",
        first_due_date="2025-11-07",
    )
    entry = SimpleNamespace(
        id=22,
        entry_code="AG-000412-2025-11-07",
        due_date="2025-11-07",
        issue_date=None,
        competence_date=None,
        occurred_on=None,
        status="scheduled",
    )

    monkeypatch.setattr(
        FinancialScheduleService,
        "_list_generated_entries",
        staticmethod(lambda **kwargs: [entry]),
    )

    captured = {}

    def _build_payload(**kwargs):
        captured["occurrence_date"] = kwargs["occurrence_date"]
        captured["force_posted"] = kwargs["force_posted"]
        return {
            "entry_type": "payable",
            "movement_nature": "debit",
            "origin_type": "manual",
            "status": "scheduled",
            "review_status": "pending_review",
            "description": "desc",
            "memo": None,
            "document_number": None,
            "external_reference": "financial_schedule:705",
            "origin_reference": "AG-000412",
            "financial_schedule_id": 705,
            "issue_date": "2025-11-07",
            "competence_date": "2025-11-07",
            "due_date": "2025-11-07",
            "occurred_on": None,
            "original_amount": Decimal("100.00"),
            "currency_code": "BRL",
            "bank_account_id": None,
            "counterparty_id": None,
            "chart_account_id": None,
            "cost_center_id": None,
            "budget_line_id": None,
            "budget_contract_id": None,
            "budget_document_id": None,
            "activity_id": None,
            "process_instance_id": None,
            "routine_id": None,
            "notes": None,
            "metadata_json": {},
        }

    monkeypatch.setattr(
        FinancialScheduleService,
        "_build_entry_payload",
        staticmethod(_build_payload),
    )
    monkeypatch.setattr(
        FinancialScheduleService,
        "_apply_schedule_allocations",
        staticmethod(lambda **kwargs: None),
    )

    error = FinancialScheduleService._sync_generated_entries_for_schedule(schedule=schedule)

    assert error is None
    assert captured["occurrence_date"] == "2025-11-07"
    assert captured["force_posted"] is False
