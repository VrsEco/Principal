from types import SimpleNamespace

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
