from types import SimpleNamespace

from src.core.mcp_session_company_tools import register_session_company_tools


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


def test_session_company_tools_describe_and_select(monkeypatch):
    import src.core.mcp_session_company_tools as module

    monkeypatch.setattr(
        module,
        "get_http_request_identity",
        lambda: SimpleNamespace(token="mcpu_token", metadata={"client_name": "Claude"}),
    )
    monkeypatch.setattr(
        module,
        "user_mcp_token_service",
        SimpleNamespace(
            describe_runtime_company_scope=lambda **kwargs: {
                "user_id": 7,
                "active_company_id": None,
                "accessible_company_ids": [10, 12],
                "selection_required_for_mutations": True,
            },
            select_runtime_company=lambda **kwargs: {
                "user_id": 7,
                "active_company_id": 10,
                "active_company_label": "Empresa 10",
                "accessible_company_ids": [10, 12],
                "selection_required_for_mutations": False,
            },
            clear_runtime_company=lambda **kwargs: {
                "user_id": 7,
                "active_company_id": None,
                "accessible_company_ids": [10, 12],
                "selection_required_for_mutations": True,
            },
        ),
    )

    mcp = _FakeMCP()
    register_session_company_tools(mcp)

    described = mcp.registered["describe_app32_session_company_scope_tool"]()
    selected = mcp.registered["select_app32_session_company_tool"](10)
    cleared = mcp.registered["clear_app32_session_company_tool"]()

    assert described["success"] is True
    assert described["data"]["selection_required_for_mutations"] is True
    assert selected["success"] is True
    assert selected["data"]["active_company_id"] == 10
    assert cleared["success"] is True
    assert cleared["data"]["active_company_id"] is None


def test_session_company_tools_return_unauthorized_without_identity(monkeypatch):
    import src.core.mcp_session_company_tools as module

    monkeypatch.setattr(module, "get_http_request_identity", lambda: None)

    mcp = _FakeMCP()
    register_session_company_tools(mcp)

    payload = mcp.registered["describe_app32_session_company_scope_tool"]()

    assert payload["success"] is False
    assert payload["error"]["code"] == "mcp_session_company_unauthorized"
