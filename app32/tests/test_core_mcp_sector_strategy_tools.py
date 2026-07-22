import src.core.mcp_sector_strategy_tools as sector_tools
from services.sector_strategy_structure_service import SectorStrategyStructureService


class _FakeMCP:
    def __init__(self):
        self.registered = {}

    def tool(self, *args, **kwargs):
        def decorator(func):
            self.registered[kwargs.get("name") or func.__name__] = func
            return func
        if args and callable(args[0]):
            return decorator(args[0])
        return decorator


def test_sector_structure_tool_requires_human_confirmation(monkeypatch):
    monkeypatch.setattr(
        sector_tools,
        "get_http_request_context",
        lambda: {"user_id": 44, "company_id": 13, "accessible_company_ids": [13]},
    )
    mcp = _FakeMCP()
    sector_tools.register_sector_strategy_tools(mcp)

    result = mcp.registered["create_sector_okr_structure_tool"](
        company_id=13,
        payload={"okrs": []},
        confirmed_mutation=False,
        user_id=44,
    )

    assert result["success"] is False
    assert result["error"]["code"] == "sector_structure_forbidden"
    assert result["meta"]["human_gate_required"] is True


def test_sector_structure_tool_delegates_authenticated_tenant(monkeypatch):
    captured = {}
    monkeypatch.setattr(
        sector_tools,
        "get_http_request_context",
        lambda: {"user_id": 44, "company_id": 13, "accessible_company_ids": [13]},
    )

    def fake_execute(**kwargs):
        captured.update(kwargs)
        return {"company_id": kwargs["company_id"], "created": {"okrs": [1]}}

    monkeypatch.setattr(sector_tools.SectorStrategyStructureService, "execute", fake_execute)
    mcp = _FakeMCP()
    sector_tools.register_sector_strategy_tools(mcp)

    result = mcp.registered["create_sector_okr_structure_tool"](
        company_id=13,
        payload={"okrs": [{"objective": "Teste"}]},
        confirmed_mutation=True,
        user_id=44,
    )

    assert result["success"] is True
    assert captured["company_id"] == 13
    assert captured["user_id"] == 44
    assert captured["confirmed_mutation"] is True


def test_identity_resolution_accepts_legacy_ativo_status():
    assert SectorStrategyStructureService._is_active_status("Ativo") is True
    assert SectorStrategyStructureService._is_active_status("inactive") is False
