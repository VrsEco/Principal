import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import services.financial_catalog_service as catalog_module
from services.financial_catalog_service import FinancialCatalogService


class _Column:
    def __eq__(self, other):
        return ("eq", other)

    def is_(self, other):
        return ("is", other)


class _QueryStub:
    def __init__(self, result=None):
        self.result = result

    def filter(self, *args, **kwargs):
        return self

    def first(self):
        return self.result


def test_create_cost_center_preserves_default_suggestion(monkeypatch):
    captured = {}

    class _FakeCostCenter:
        company_id = _Column()
        code = _Column()
        deleted_at = _Column()
        query = _QueryStub(None)

        def __init__(self, **kwargs):
            self.id = 77
            self.__dict__.update(kwargs)

        def to_dict(self):
            return dict(self.__dict__)

    monkeypatch.setattr(catalog_module, "FinancialCostCenter", _FakeCostCenter)
    monkeypatch.setitem(FinancialCatalogService.CATALOGS, "cost_centers", {
        "model": _FakeCostCenter,
        "create_schema": catalog_module.FinancialCostCenterInput,
        "update_schema": catalog_module.FinancialCostCenterUpdateInput,
        "code_field": "code",
        "company_fk_fields": ["parent_id"],
    })
    monkeypatch.setattr(catalog_module.FinancialCatalogService, "_validate_scope", lambda **kwargs: None)
    monkeypatch.setattr(catalog_module.FinancialCatalogService, "_validate_related_scope", lambda **kwargs: None)
    monkeypatch.setattr(catalog_module.FinancialCatalogService, "_clear_default_cost_center_suggestions", lambda **kwargs: captured.setdefault("clear_kwargs", kwargs))
    monkeypatch.setattr(catalog_module.db.session, "add", lambda obj: captured.setdefault("added", obj))
    monkeypatch.setattr(catalog_module.db.session, "flush", lambda: captured.setdefault("flushed", True))
    monkeypatch.setattr(catalog_module.db.session, "commit", lambda: captured.setdefault("committed", True))
    monkeypatch.setattr(catalog_module.db.session, "rollback", lambda: captured.setdefault("rollback", True))

    result, error = FinancialCatalogService.create_item(
        catalog_type="cost_centers",
        payload={
            "company_id": 9,
            "code": "CC-001",
            "name": "Centro padrão",
            "is_default_suggestion": True,
        },
        allowed_company_ids=[9],
    )

    assert error is None
    assert result is not None
    assert result["is_default_suggestion"] is True
    assert captured["clear_kwargs"]["exclude_item_id"] == 77


def test_prepare_cost_center_payload_maps_account_level_type():
    payload = FinancialCatalogService._prepare_catalog_payload(
        catalog_type="cost_centers",
        company_id=9,
        data={
            "company_id": 9,
            "code": "1.01",
            "name": "Administrativo",
            "account_level_type": "synthetic",
            "metadata_json": {"external_code": "ERP-01"},
        },
    )

    assert payload["accepts_posting"] is False
    assert payload["metadata_json"]["account_level_type"] == "synthetic"
    assert payload["metadata_json"]["external_code"] == "ERP-01"


def test_validate_related_scope_rejects_analytic_cost_center_parent(monkeypatch):
    class _AnalyticParent:
        id = 55
        accepts_posting = True

    class _FakeCostCenter:
        id = _Column()
        company_id = _Column()
        deleted_at = _Column()
        query = _QueryStub(_AnalyticParent())

    monkeypatch.setattr(catalog_module, "FinancialCostCenter", _FakeCostCenter)

    error = FinancialCatalogService._validate_related_scope(
        catalog_type="cost_centers",
        company_id=9,
        data={"parent_id": 55},
    )

    assert error == "Centro analítico não pode ser usado como centro pai."
