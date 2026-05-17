from unittest.mock import patch

from src.core.mcp_sapiens_activation_tools import register_sapiens_activation_tools


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


def test_available_sapiens_squads_returns_selection_prompt_for_admin():
    mcp = _FakeMCP()
    register_sapiens_activation_tools(mcp)

    with patch("src.core.mcp_sapiens_activation_tools.get_http_request_context", return_value={"fallback_role": "administrador"}):
        payload = mcp.registered["describe_app32_available_sapiens_squads_tool"]()

    assert payload["success"] is True
    assert [item["choice_label"] for item in payload["data"]["available_squads"]] == ["Cliente", "Versus", "Engenharia"]
    assert payload["data"]["selection_prompt"] == "Escolha entre: Cliente, Versus ou Engenharia."


def test_resolve_sapiens_activation_requires_selection_when_multiple_squads():
    mcp = _FakeMCP()
    register_sapiens_activation_tools(mcp)

    with patch("src.core.mcp_sapiens_activation_tools.get_http_request_context", return_value={"fallback_role": "administrador"}):
        payload = mcp.registered["resolve_app32_sapiens_activation_tool"]()

    assert payload["success"] is True
    assert payload["data"]["selection_required"] is True
    assert payload["data"]["selection_prompt"] == "Escolha entre: Cliente, Versus ou Engenharia."


def test_resolve_sapiens_activation_returns_cliente_payload():
    mcp = _FakeMCP()
    register_sapiens_activation_tools(mcp)

    with patch(
        "src.core.mcp_sapiens_activation_tools.get_http_request_context",
        return_value={"fallback_role": "administrador", "company_id": 31},
    ):
        payload = mcp.registered["resolve_app32_sapiens_activation_tool"](squad="cliente")

    assert payload["success"] is True
    assert payload["data"]["selection_required"] is False
    assert payload["data"]["selected_squad"]["experience_label"] == "Sapiens Cliente"
    assert payload["data"]["session_title"] == "Sapiens Cliente Ativado"
    assert payload["data"]["session_badge"] == "Sapiens Cliente On"
    assert payload["data"]["startup_tools"][0] == "resolve_app32_instruction_bundle_tool"
