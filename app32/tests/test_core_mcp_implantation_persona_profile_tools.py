from __future__ import annotations

from types import SimpleNamespace

import src.core.mcp_implantation_persona_profile_tools as tools_module
from services.implantation_persona_profile_service import (
    ImplantationPersonaProfileApplyResult,
    ImplantationPersonaProfilePreview,
    ImplantationPersonaProfileService,
)


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


def test_register_implantation_persona_profile_tools(monkeypatch):
    mcp = _FakeMCP()
    tools_module.register_implantation_persona_profile_tools(mcp)

    monkeypatch.setattr(
        tools_module,
        "get_sapiens_context",
        lambda: SimpleNamespace(user_id=77, company_id=12),
    )
    monkeypatch.setattr(
        ImplantationPersonaProfileService,
        "preview_update",
        lambda **kwargs: ImplantationPersonaProfilePreview(
            company_id=12,
            plan_id=12,
            plan_title="Implantação Vrs",
            segment_name=kwargs["segment_name"],
            persona_name=kwargs["persona_name"],
            before="antes",
            after=kwargs["profile_text"],
            has_changes=True,
            actor_user_id=77,
            actor_role="administrator",
        ),
    )
    monkeypatch.setattr(
        ImplantationPersonaProfileService,
        "apply_update",
        lambda **kwargs: ImplantationPersonaProfileApplyResult(
            company_id=12,
            plan_id=12,
            plan_title="Implantação Vrs",
            segment_name=kwargs["segment_name"],
            persona_name=kwargs["persona_name"],
            before="antes",
            after=kwargs["profile_text"],
            has_changes=True,
            actor_user_id=77,
            actor_role="administrator",
            saved=not kwargs.get("dry_run", False),
        ),
    )

    describe = mcp.registered["describe_app32_implantation_persona_profile_tool"]()
    assert describe["success"] is True
    assert "preview_app32_implantation_persona_profile_update_tool" in describe["data"]["operations"]

    preview = mcp.registered["preview_app32_implantation_persona_profile_update_tool"](
        plan_id=12,
        segment_name="Segmento X",
        persona_name="Persona Y",
        profile_text="perfil novo",
    )
    assert preview["success"] is True
    assert preview["data"]["after"] == "perfil novo"

    apply_result = mcp.registered["apply_app32_implantation_persona_profile_update_tool"](
        plan_id=12,
        segment_name="Segmento X",
        persona_name="Persona Y",
        profile_text="perfil novo",
    )
    assert apply_result["success"] is True
    assert apply_result["data"]["saved"] is True


def test_implantation_persona_profile_tools_require_context():
    mcp = _FakeMCP()
    tools_module.register_implantation_persona_profile_tools(mcp)

    tools_module.get_sapiens_context = lambda: SimpleNamespace(user_id=None, company_id=None)

    preview = mcp.registered["preview_app32_implantation_persona_profile_update_tool"](
        plan_id=12,
        segment_name="Segmento X",
        persona_name="Persona Y",
        profile_text="perfil novo",
    )

    assert preview["success"] is False
    assert preview["error"]["code"] == "missing_mcp_context"
