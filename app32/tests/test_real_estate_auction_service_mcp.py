from decimal import Decimal

import pytest

from services.real_estate_auction_service import RealEstateAuctionError, RealEstateAuctionService


def test_property_payload_normalization_applies_defaults_and_tenant_safe_fields():
    payload = RealEstateAuctionService._normalize_property_payload(
        {
            "code": " GDI-001 ",
            "address": " Rua Exemplo, 100 ",
            "state": "bahia",
            "appraisal_value": "450000.25",
            "metadata_json": {"origin": "gandu"},
        },
        partial=False,
    )

    assert payload["code"] == "GDI-001"
    assert payload["address"] == "Rua Exemplo, 100"
    assert payload["state"] == "BA"
    assert payload["appraisal_value"] == Decimal("450000.25")
    assert payload["status"] == "in_analysis"
    assert payload["triage_status"] == "pending"
    assert payload["occupied"] is True
    assert payload["metadata_json"] == {"origin": "gandu"}
    assert "company_id" not in payload


def test_property_payload_rejects_invalid_status():
    with pytest.raises(RealEstateAuctionError) as exc:
        RealEstateAuctionService._normalize_property_payload(
            {
                "code": "GDI-001",
                "address": "Rua Exemplo",
                "status": "global",
            },
            partial=False,
        )

    assert "status" in str(exc.value)


def test_tenant_settings_default_when_company_has_no_row(monkeypatch):
    class _EmptySettingsQuery:
        def first(self):
            return None

    monkeypatch.setattr(RealEstateAuctionService, "_require_company", staticmethod(lambda company_id: object()))
    monkeypatch.setattr(RealEstateAuctionService, "_settings_query", staticmethod(lambda company_id: _EmptySettingsQuery()))

    settings = RealEstateAuctionService.get_tenant_settings(company_id=7)

    assert settings["company_id"] == 7
    assert settings["module_enabled"] is False
    assert settings["display_name"] == "Leilões Imobiliários"


def test_real_estate_auction_capabilities_are_registered():
    from src.intelligence.tool_catalog import catalog

    capabilities = {
        capability.name: capability
        for capability in catalog.iter_capabilities(domain="real_estate_auctions")
    }

    assert "get_real_estate_auction_workspace_tool" in capabilities
    assert "create_real_estate_auction_property_tool" in capabilities
    assert "upsert_real_estate_auction_financial_sheet_tool" in capabilities
    assert "create_real_estate_auction_source_tool" in capabilities
    assert capabilities["create_real_estate_auction_property_tool"].human_gate is True
    assert "mcp_user" in capabilities["list_real_estate_auction_properties_tool"].scopes
    assert "mcp_analytics" in capabilities["list_real_estate_auction_properties_tool"].scopes
    assert capabilities["upsert_real_estate_auction_settings_tool"].risk.value == "high"
    assert capabilities["upsert_real_estate_auction_financial_sheet_tool"].permissions == ("real_estate_auctions.manage_financial_sheet",)


def test_financial_sheet_and_source_payload_normalization_are_tenant_safe():
    sheet = RealEstateAuctionService._normalize_financial_sheet_payload(
        {
            "winning_bid": "310000.50",
            "capital_cost_months": "8",
            "minimum_profit_percent": "18.5",
        }
    )
    source = RealEstateAuctionService._normalize_source_payload(
        {
            "name": " Portal Caixa ",
            "domain": " caixa.gov.br ",
            "base_url": " https://caixa.gov.br/imoveis ",
            "active": "1",
        },
        partial=False,
    )

    assert sheet["winning_bid"] == Decimal("310000.50")
    assert sheet["capital_cost_months"] == 8
    assert sheet["minimum_profit_percent"] == Decimal("18.5")
    assert "company_id" not in sheet
    assert source["name"] == "Portal Caixa"
    assert source["domain"] == "caixa.gov.br"
    assert source["base_url"] == "https://caixa.gov.br/imoveis"
    assert source["active"] is True
    assert "company_id" not in source


def test_group_properties_by_status_preserves_known_columns():
    grouped = RealEstateAuctionService.group_properties_by_status(
        [
            {"id": 1, "status": "in_analysis"},
            {"id": 2, "status": "in_analysis"},
            {"id": 3, "status": "sold"},
        ]
    )
    bucket_map = {item["status"]: item for item in grouped}

    assert bucket_map["in_analysis"]["count"] == 2
    assert bucket_map["sold"]["count"] == 1
    assert bucket_map["awaiting_auction"]["count"] == 0


def test_mcp_real_estate_auction_tools_return_standard_envelope(monkeypatch):
    from src.core import mcp_real_estate_auction_tools as tools_module

    class _FakeMCP:
        def __init__(self):
            self.registered = {}

        def tool(self, *args, **kwargs):
            explicit_name = kwargs.get("name")

            def _decorator(func):
                self.registered[explicit_name or func.__name__] = func
                return func

            if args and callable(args[0]) and not kwargs:
                return _decorator(args[0])
            return _decorator

    monkeypatch.setattr(tools_module, "_run", lambda callback, *args, **kwargs: callback(*args, **kwargs))
    monkeypatch.setattr(
        tools_module.RealEstateAuctionService,
        "get_tenant_settings",
        staticmethod(lambda company_id: {"company_id": company_id, "module_enabled": True}),
    )
    monkeypatch.setattr(
        tools_module.RealEstateAuctionService,
        "list_properties",
        staticmethod(lambda company_id, **filters: [{"company_id": company_id, "code": "GDI-001"}]),
    )
    monkeypatch.setattr(
        tools_module.RealEstateAuctionService,
        "list_sources",
        staticmethod(lambda company_id: [{"company_id": company_id, "name": "Portal Caixa"}]),
    )

    fake_mcp = _FakeMCP()
    tools_module.register_real_estate_auction_tools(fake_mcp)

    settings_response = fake_mcp.registered["get_real_estate_auction_settings_tool"](company_id=7)
    list_response = fake_mcp.registered["list_real_estate_auction_properties_tool"](company_id=7, limit=10)
    source_response = fake_mcp.registered["list_real_estate_auction_sources_tool"](company_id=7)

    assert settings_response["success"] is True
    assert settings_response["meta"]["domain"] == "real_estate_auctions"
    assert settings_response["meta"]["company_id"] == 7
    assert list_response["data"] == [{"company_id": 7, "code": "GDI-001"}]
    assert source_response["data"] == [{"company_id": 7, "name": "Portal Caixa"}]


def test_mcp_real_estate_auction_tools_wrap_domain_errors(monkeypatch):
    from src.core import mcp_real_estate_auction_tools as tools_module

    class _FakeMCP:
        def __init__(self):
            self.registered = {}

        def tool(self, *args, **kwargs):
            def _decorator(func):
                self.registered[func.__name__] = func
                return func

            return _decorator

    def _raise(*args, **kwargs):
        raise RealEstateAuctionError("módulo não habilitado")

    monkeypatch.setattr(tools_module, "_run", lambda callback, *args, **kwargs: callback(*args, **kwargs))
    monkeypatch.setattr(tools_module.RealEstateAuctionService, "create_property", staticmethod(_raise))

    fake_mcp = _FakeMCP()
    tools_module.register_real_estate_auction_tools(fake_mcp)
    response = fake_mcp.registered["create_real_estate_auction_property_tool"](
        company_id=7,
        payload={"code": "GDI-001", "address": "Rua Exemplo"},
    )

    assert response["success"] is False
    assert response["error"]["code"] == "real_estate_auction_invalid_request"
    assert response["meta"]["human_gate_required"] is True


def test_mcp_real_estate_auction_financial_sheet_tool_is_registered_as_write(monkeypatch):
    from src.core import mcp_real_estate_auction_tools as tools_module

    class _FakeMCP:
        def __init__(self):
            self.registered = {}

        def tool(self, *args, **kwargs):
            def _decorator(func):
                self.registered[func.__name__] = func
                return func

            return _decorator

    monkeypatch.setattr(tools_module, "_run", lambda callback, *args, **kwargs: callback(*args, **kwargs))
    monkeypatch.setattr(
        tools_module.RealEstateAuctionService,
        "upsert_financial_sheet",
        staticmethod(lambda company_id, property_id, payload: {"company_id": company_id, "property_id": property_id, **payload}),
    )

    fake_mcp = _FakeMCP()
    tools_module.register_real_estate_auction_tools(fake_mcp)
    response = fake_mcp.registered["upsert_real_estate_auction_financial_sheet_tool"](
        company_id=7,
        property_id=11,
        payload={"winning_bid": 250000},
    )

    assert response["success"] is True
    assert response["meta"]["human_gate_required"] is True
    assert response["data"]["property_id"] == 11
