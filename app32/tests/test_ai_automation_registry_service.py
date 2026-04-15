import os
import sys
from datetime import datetime
from types import SimpleNamespace

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.ai_automation_registry_service import AIAutomationRegistryService


def test_automation_registry_aggregates_runtime_and_financial(monkeypatch):
    fake_job = SimpleNamespace(id="process_daily_routines", next_run_time=datetime(2026, 4, 15, 8, 0, 0))
    monkeypatch.setattr(
        "services.ai_automation_registry_service.get_scheduler",
        lambda: SimpleNamespace(scheduler=SimpleNamespace(get_jobs=lambda: [fake_job])),
    )

    class _FakeQuery:
        def __init__(self, count_value):
            self.count_value = count_value

        def filter(self, *args, **kwargs):
            return self

        def count(self):
            return self.count_value

    monkeypatch.setattr("services.ai_automation_registry_service.ProcessRoutine", SimpleNamespace(query=_FakeQuery(3), is_active=SimpleNamespace(is_=lambda value: value), company_id=31))
    monkeypatch.setattr("services.ai_automation_registry_service.FinancialAutomationRule", SimpleNamespace(query=_FakeQuery(2), deleted_at=SimpleNamespace(is_=lambda value: value), is_active=SimpleNamespace(is_=lambda value: value), company_id=31))
    monkeypatch.setattr("services.ai_automation_registry_service.FinancialAutomationExecution", SimpleNamespace(query=_FakeQuery(5), company_id=31, executed_at=SimpleNamespace(__ge__=lambda self, other: True)))

    payload = AIAutomationRegistryService.build_registry(SimpleNamespace(id=31))

    assert payload["summary"]["automations"] >= 5
    assert payload["summary"]["scheduled_jobs"] >= 1
    assert payload["summary"]["active_routines"] == 3
