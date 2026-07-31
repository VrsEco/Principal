import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.knowledge.auto_update_service import KnowledgeAutoUpdateService


class _Adapter:
    source_type = "product_help"
    knowledge_scope = "product"
    adapter_version = "v1"

    def __init__(self, *, error=None):
        self.error = error
        self.validated_company_id = "unset"

    def validate_scope(self, *, company_id):
        self.validated_company_id = company_id

    def discover_documents(self, *, company_id):
        if self.error:
            raise self.error
        return ("document",)


class _Registry:
    def __init__(self, adapter):
        self.adapter = adapter

    def get(self, source_type):
        assert source_type == "product_help"
        return self.adapter


class _Repository:
    def __init__(self):
        self.started = []
        self.synced = []
        self.completed = []
        self.rolled_back = False

    def start_run(self, **kwargs):
        self.started.append(kwargs)
        return SimpleNamespace(id=17)

    def sync_documents(self, **kwargs):
        self.synced.append(kwargs)
        return {
            "discovered": 1,
            "created": 1,
            "updated": 0,
            "unchanged": 0,
            "deactivated": 0,
        }

    def complete_run(self, run_id, **kwargs):
        self.completed.append((run_id, kwargs))
        return SimpleNamespace(to_dict=lambda: {"id": run_id, "status": kwargs["status"]})

    def rollback(self):
        self.rolled_back = True


def test_auto_update_syncs_product_help_without_artificial_company_id():
    adapter = _Adapter()
    repository = _Repository()
    service = KnowledgeAutoUpdateService(
        repository=repository,
        registry=_Registry(adapter),
    )

    result = service.sync_product_help(trigger_kind="scheduled")

    assert result["ok"] is True
    assert adapter.validated_company_id is None
    assert repository.started[0]["knowledge_scope"] == "product"
    assert repository.started[0]["company_id"] is None
    assert repository.synced[0]["documents"] == ("document",)
    assert repository.completed[-1][1]["status"] == "completed"


def test_auto_update_records_failure_and_rolls_back():
    adapter = _Adapter(error=ValueError("catálogo inválido"))
    repository = _Repository()
    service = KnowledgeAutoUpdateService(
        repository=repository,
        registry=_Registry(adapter),
    )

    result = service.sync_product_help(trigger_kind="manual")

    assert result["ok"] is False
    assert repository.rolled_back is True
    assert repository.completed[-1][1]["status"] == "failed"
    assert "catálogo inválido" in repository.completed[-1][1]["error_message"]


def test_auto_update_syncs_each_registered_tenant_source(monkeypatch):
    service = KnowledgeAutoUpdateService()
    calls = []

    def fake_sync_source(source_type, *, company_id, trigger_kind):
        calls.append((source_type, company_id, trigger_kind))
        return {"ok": True}

    monkeypatch.setattr(service, "sync_source", fake_sync_source)

    payload = service.sync_company_sources(9, trigger_kind="manual")

    assert payload["ok"] is True
    assert payload["company_id"] == 9
    assert calls == [
        ("process_publication", 9, "manual"),
        ("meeting", 9, "manual"),
    ]


def test_auto_update_syncs_all_global_product_sources(monkeypatch):
    service = KnowledgeAutoUpdateService()
    calls = []

    def fake_sync_source(source_type, *, company_id, trigger_kind):
        calls.append((source_type, company_id, trigger_kind))
        return {"ok": True}

    monkeypatch.setattr(service, "sync_source", fake_sync_source)
    monkeypatch.setattr(
        service,
        "audit_product_manual",
        lambda: {"ok": True, "coverage_percent": 100.0},
    )

    payload = service.sync_product_sources(trigger_kind="manual")

    assert payload["ok"] is True
    assert calls == [
        ("product_help", None, "manual"),
        ("system_documentation", None, "manual"),
    ]
    assert payload["manual_catalog_audit"]["coverage_percent"] == 100.0
