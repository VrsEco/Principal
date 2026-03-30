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
