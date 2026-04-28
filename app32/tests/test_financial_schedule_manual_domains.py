import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import services.financial_schedule_service as schedule_module
from services.financial_schedule_service import FinancialScheduleService


def test_list_enabled_domains_merges_routine_and_manual_sources(monkeypatch):
    monkeypatch.setattr(
        schedule_module.FinancialDomainEnablementService,
        "list_items",
        staticmethod(
            lambda **kwargs: (
                {
                    "items_by_type": {
                        "project": [
                            {
                                "domain_type": "project",
                                "source_id": 11,
                                "display_label": "AA.J.11 - Projeto Rotina",
                                "is_enabled": True,
                            }
                        ],
                        "process": [],
                    }
                },
                None,
            )
        ),
    )
    monkeypatch.setattr(
        schedule_module.FinancialManualDomainService,
        "list_enabled_items",
        staticmethod(
            lambda **kwargs: (
                [
                    {
                        "domain_type": "process",
                        "source_kind": "manual",
                        "source_id": 22,
                        "display_label": "PROC-MAN-22 - Processo Manual",
                    }
                ],
                None,
            )
        ),
    )

    result, error = FinancialScheduleService.list_enabled_domains(company_id=9, allowed_company_ids=[9])

    assert error is None
    assert [item["domain_value"] for item in result] == [
        "routine:project:11",
        "manual:process:22",
    ]


def test_build_domain_value_uses_source_kind_namespace():
    assert FinancialScheduleService._build_domain_value("project", 55, "manual") == "manual:project:55"
    assert FinancialScheduleService._build_domain_value("process", 19, None) == "routine:process:19"
