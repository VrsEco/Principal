import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services import scheduler_service as scheduler_module


def test_setup_knowledge_jobs_registers_immediate_idempotent_interval(monkeypatch):
    captured = []

    def fake_add_job(**kwargs):
        captured.append(kwargs)

    monkeypatch.setattr(scheduler_module.scheduler_service, "add_job", fake_add_job)
    app = SimpleNamespace(
        config={
            "KNOWLEDGE_PRODUCT_HELP_SYNC_MINUTES": 7,
            "KNOWLEDGE_TENANT_SYNC_MINUTES": 11,
        }
    )

    scheduler_module.setup_knowledge_jobs(app)

    by_id = {item["job_id"]: item for item in captured}
    assert by_id["knowledge_product_help_sync"]["trigger"] == "interval"
    assert by_id["knowledge_product_help_sync"]["minutes"] == 7
    assert by_id["knowledge_product_help_sync"]["next_run_time"] is not None
    assert by_id["knowledge_tenant_sources_sync"]["trigger"] == "interval"
    assert by_id["knowledge_tenant_sources_sync"]["minutes"] == 11
    assert by_id["knowledge_tenant_sources_sync"]["next_run_time"] is not None


def test_automation_registry_exposes_knowledge_sync():
    specs = {
        item["key"]: item
        for item in __import__(
            "services.ai_automation_registry_service",
            fromlist=["AIAutomationRegistryService"],
        ).AIAutomationRegistryService.DEFAULT_JOB_SPECS
    }

    assert specs["knowledge_product_help_sync"]["kind"] == "knowledge_sync"
    assert "idempotente" in " ".join(specs["knowledge_product_help_sync"]["governance"])
    assert specs["knowledge_tenant_sources_sync"]["kind"] == "knowledge_sync"
    assert "company_id" in " ".join(
        specs["knowledge_tenant_sources_sync"]["governance"]
    ).lower()
