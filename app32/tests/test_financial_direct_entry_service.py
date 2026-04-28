import os
import sys
from datetime import date
from decimal import Decimal

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import services.financial_direct_entry_service as direct_entry_module
from schemas.financial import FinancialDirectEntryCreateInput
from services.financial_direct_entry_service import FinancialDirectEntryService


def test_create_direct_entry_passes_due_date_to_schedule_allocation_validation(monkeypatch):
    captured = {}

    monkeypatch.setattr(
        direct_entry_module.FinancialService,
        "_ensure_company_scope",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(
        direct_entry_module.FinancialDirectEntryService,
        "_apply_counterparty_defaults",
        lambda **kwargs: None,
    )
    monkeypatch.setattr(
        direct_entry_module.FinancialCatalogService,
        "validate_reference_ids",
        lambda **kwargs: None,
    )

    def _capture_validate_schedule_allocations(**kwargs):
        captured.update(kwargs)
        return "stop-after-capture"

    monkeypatch.setattr(
        direct_entry_module.FinancialScheduleService,
        "_validate_schedule_allocations",
        _capture_validate_schedule_allocations,
    )

    result, error = FinancialDirectEntryService.create_direct_entry(
        payload={
            "company_id": 9,
            "entry_type": "payable",
            "description": "Teste lançamento direto",
            "document_number": "55444",
            "counterparty_id": 1,
            "bank_account_id": 1,
            "competence_date": date(2026, 3, 29),
            "occurred_on": date(2026, 3, 29),
            "due_date": date(2026, 3, 29),
            "original_amount": Decimal("100000.00"),
            "allocations": [
                {
                    "chart_account_id": 7,
                    "cost_center_id": 6,
                    "domain_type": "project",
                    "domain_source_id": 25,
                    "domain_label": "AA.J.25 - Projeto de Teste",
                    "allocation_type": "amount",
                    "percentage": Decimal("100"),
                    "allocated_amount": Decimal("100000.00"),
                    "metadata_json": {},
                }
            ],
        },
        allowed_company_ids=[9],
    )

    assert result is None
    assert error == "stop-after-capture"
    assert captured["company_id"] == 9
    assert captured["template_amount"] == Decimal("100000.00")
    assert captured["due_date"] == date(2026, 3, 29)
    assert captured["metadata_json"]["allocations"][0]["chart_account_id"] == 7
    assert captured["metadata_json"]["allocations"][0]["domain_source_kind"] == "routine"


def test_build_schedule_payload_delegates_schedule_code_generation():
    payload = FinancialDirectEntryService._build_schedule_payload(
        FinancialDirectEntryCreateInput.model_validate(
            {
                "company_id": 9,
                "entry_type": "receivable",
                "description": "Teste sem código",
                "document_number": "DOC-1",
                "counterparty_id": 1,
                "bank_account_id": 2,
                "competence_date": date(2026, 3, 29),
                "occurred_on": date(2026, 3, 29),
                "due_date": date(2026, 3, 30),
                "original_amount": Decimal("2500.00"),
                "allocations": [
                    {
                        "chart_account_id": 7,
                        "cost_center_id": 6,
                        "allocation_type": "amount",
                        "allocated_amount": Decimal("2500.00"),
                        "metadata_json": {},
                    }
                ],
            }
        )
    )

    assert "schedule_code" not in payload


def test_build_schedule_payload_keeps_manual_domain_source_kind():
    payload = FinancialDirectEntryService._build_schedule_payload(
        FinancialDirectEntryCreateInput.model_validate(
            {
                "company_id": 9,
                "entry_type": "receivable",
                "description": "Teste manual",
                "document_number": "DOC-2",
                "counterparty_id": 1,
                "bank_account_id": 2,
                "competence_date": date(2026, 3, 29),
                "occurred_on": date(2026, 3, 29),
                "due_date": date(2026, 3, 30),
                "original_amount": Decimal("2500.00"),
                "allocations": [
                    {
                        "chart_account_id": 7,
                        "cost_center_id": 6,
                        "domain_source_kind": "manual",
                        "domain_type": "project",
                        "domain_source_id": 44,
                        "domain_label": "PRJ-MAN-44 - Projeto Manual",
                        "allocation_type": "amount",
                        "allocated_amount": Decimal("2500.00"),
                        "metadata_json": {},
                    }
                ],
            }
        )
    )

    allocation = payload["metadata_json"]["allocations"][0]
    assert allocation["domain_source_kind"] == "manual"
    assert allocation["domain_type"] == "project"
    assert allocation["domain_source_id"] == 44


def test_validate_enabled_domains_accepts_manual_records(monkeypatch):
    class _Column:
        def __eq__(self, other):
            return self

        def is_(self, other):
            return self

    class _RoutineRecord:
        def __init__(self, domain_type, source_id):
            self.domain_type = domain_type
            self.source_id = source_id

    class _RoutineQuery:
        def filter(self, *args, **kwargs):
            return self

        def all(self):
            return [_RoutineRecord("project", 10)]

    monkeypatch.setattr(
        direct_entry_module,
        "FinancialDomainEnablement",
        type(
            "RoutineEnablementStub",
            (),
            {
                "query": _RoutineQuery(),
                "company_id": _Column(),
                "deleted_at": _Column(),
                "is_enabled": _Column(),
            },
        ),
    )

    class _Allocation:
        domain_source_kind = "manual"
        domain_type = "process"
        domain_source_id = 33

    monkeypatch.setattr(
        direct_entry_module,
        "FinancialManualDomainService",
        type(
            "ManualSvcStub",
            (),
            {
                "list_enabled_items": staticmethod(
                    lambda **kwargs: ([{"domain_type": "process", "source_id": 33}], None)
                )
            },
        ),
        raising=False,
    )

    error = FinancialDirectEntryService._validate_enabled_domains(
        company_id=9,
        allocations=[_Allocation()],
    )

    assert error is None
