from types import SimpleNamespace

import src.core.mcp_session_harness_tools as harness_tools


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


def test_session_harness_tools_describe_and_select(monkeypatch):
    identity = SimpleNamespace(token="secret", metadata={})
    monkeypatch.setattr(harness_tools, "get_http_request_identity", lambda: identity)
    fake_service = SimpleNamespace(
        describe_runtime_harness_scope=lambda **kwargs: {
            "user_id": 7,
            "active_company_id": 1,
            "active_harness_key": "harness_coordenador_cliente_v1",
        },
        select_runtime_harness=lambda **kwargs: {
            "user_id": 7,
            "active_company_id": 1,
            "active_harness_key": kwargs["harness_key"],
            "catalog_refresh_required": True,
        },
    )
    monkeypatch.setattr(harness_tools, "user_mcp_token_service", fake_service)
    mcp = _FakeMCP()
    harness_tools.register_session_harness_tools(mcp)

    described = mcp.registered["describe_app32_session_harness_tool"]()
    assert described["success"] is True
    assert described["data"]["active_harness_key"] == "harness_coordenador_cliente_v1"

    selected = mcp.registered["select_app32_session_harness_tool"]("harness_admfin_cliente_v1")
    assert selected["success"] is True
    assert selected["data"]["active_harness_key"] == "harness_admfin_cliente_v1"
    assert selected["data"]["catalog_refresh_required"] is True
