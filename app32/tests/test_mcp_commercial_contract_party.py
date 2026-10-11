from types import SimpleNamespace

import pytest

from src.core import mcp_commercial_tools


class _FakeMcp:
    def __init__(self):
        self.tools = {}

    def tool(self, *args, **kwargs):
        def register(fn):
            self.tools[fn.__name__] = fn
            return fn

        return register


@pytest.fixture()
def tool(monkeypatch):
    seen = {}
    from services.contracts_service import ContractService

    monkeypatch.setattr(mcp_commercial_tools, "get_http_request_context", lambda: {"user_id": 3})
    monkeypatch.setattr(
        ContractService,
        "get_party_by_counterparty_id",
        staticmethod(lambda company_id, counterparty_id: SimpleNamespace(id=10) if counterparty_id == 121 else None),
    )

    def create_contract(*, company_id, payload, user_id):
        seen.update(company_id=company_id, payload=payload, user_id=user_id)
        return SimpleNamespace(to_dict=lambda: {"id": 83, "party_id": payload.get("party_id")})

    monkeypatch.setattr(ContractService, "create_contract", staticmethod(create_contract))
    fake = _FakeMcp()
    mcp_commercial_tools.register_commercial_mcp_tools(fake)
    fake.seen = seen
    return fake


def _run(monkeypatch):
    import flask

    monkeypatch.setattr(flask, "has_app_context", lambda: True)


def test_counterparty_id_from_the_customers_listing_is_translated_to_the_party(tool, monkeypatch):
    _run(monkeypatch)
    out = tool.tools["create_commercial_contract"](10, {"title": "T", "counterparty_id": 121})
    assert out["success"] is True and out["item"]["party_id"] == 10
    assert "counterparty_id" not in tool.seen["payload"]


def test_explicit_party_id_wins_and_unknown_counterparty_is_refused(tool, monkeypatch):
    _run(monkeypatch)
    assert tool.tools["create_commercial_contract"](10, {"title": "T", "party_id": 11, "counterparty_id": 121})["item"]["party_id"] == 11
    out = tool.tools["create_commercial_contract"](10, {"title": "T", "counterparty_id": 999})
    assert out["success"] is False and "counterparty_id" in out["error"]
    assert tool.tools["create_commercial_contract"](10, {"title": "T", "counterparty_id": "x"})["success"] is False
