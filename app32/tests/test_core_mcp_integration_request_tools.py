from types import SimpleNamespace

from src.core.mcp_integration_request_tools import register_integration_request_tools


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


def test_integration_request_tools_register(monkeypatch):
    mcp = _FakeMCP()
    monkeypatch.setattr(
        "src.core.mcp_integration_request_tools.IntegrationCatalogService.build_catalog",
        lambda: {"summary": {"total": 4}, "integrations": []},
    )
    monkeypatch.setattr(
        "src.core.mcp_integration_request_tools.IntegrationRequestService.create_request",
        lambda payload, **kwargs: SimpleNamespace(to_dict=lambda: {"id": 1, "backlog_task_id": 456, **payload}),
    )

    register_integration_request_tools(mcp)

    assert mcp.registered["list_app32_integrations_catalog"]()["summary"]["total"] == 4
    response = mcp.registered["request_new_app32_integration"](
        company_id=31,
        requester_user_id=9,
        title="Open Finance",
        business_domain="Financeiro",
        integration_mode="consume",
        technical_channel="api_mcp",
        external_system="Banco X",
        objective="Consumir extratos bancários para conciliação operacional.",
        data_summary="Extratos e saldos.",
    )
    assert response["success"] is True
    assert response["request"]["backlog_task_id"] == 456
