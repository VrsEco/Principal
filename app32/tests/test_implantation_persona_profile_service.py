from __future__ import annotations

from types import SimpleNamespace

import pytest

import services.implantation_persona_profile_service as service_module
from services.implantation_persona_profile_service import (
    ImplantationPersonaProfilePermissionError,
    ImplantationPersonaProfileService,
)


def _sample_model_content() -> dict:
    return {
        "segments": [
            {
                "name": "Revendedores / Instaladores Credenciados",
                "personas": [
                    {
                        "name": "Persona Principal",
                        "profile": "perfil antigo",
                    }
                ],
            }
        ]
    }


def test_preview_update_returns_before_after(monkeypatch):
    plan = SimpleNamespace(id=12, title="Implantação Vrs", mode="implantation")
    section = SimpleNamespace(content=_sample_model_content())

    monkeypatch.setattr(service_module.db.session, "get", lambda *_args, **_kwargs: SimpleNamespace(id=7))
    monkeypatch.setattr(service_module, "get_access_profile", lambda company_id, user=None: "administrator")
    monkeypatch.setattr(service_module.PlanService, "get_plan", lambda plan_id, company_id: plan)
    monkeypatch.setattr(
        service_module.PlanService,
        "get_implantation_data",
        lambda plan_id, company_id, section_key: section,
    )

    preview = ImplantationPersonaProfileService.preview_update(
        actor_user_id=7,
        company_id=12,
        plan_id=12,
        segment_name="Revendedores / Instaladores Credenciados",
        persona_name="Persona Principal",
        profile_text="perfil novo",
    )

    assert preview.plan_title == "Implantação Vrs"
    assert preview.before == "perfil antigo"
    assert preview.after == "perfil novo"
    assert preview.has_changes is True
    assert preview.actor_role == "administrator"


def test_apply_update_persists_content(monkeypatch):
    plan = SimpleNamespace(id=12, title="Implantação Vrs", mode="implantation")
    section = SimpleNamespace(content=_sample_model_content())
    captured: dict = {}

    monkeypatch.setattr(service_module.db.session, "get", lambda *_args, **_kwargs: SimpleNamespace(id=7))
    monkeypatch.setattr(service_module, "get_access_profile", lambda company_id, user=None: "administrator")
    monkeypatch.setattr(service_module.PlanService, "get_plan", lambda plan_id, company_id: plan)
    monkeypatch.setattr(
        service_module.PlanService,
        "get_implantation_data",
        lambda plan_id, company_id, section_key: section,
    )

    def _save_implantation_data(plan_id, company_id, section_key, content):
        captured["payload"] = {
            "plan_id": plan_id,
            "company_id": company_id,
            "section_key": section_key,
            "content": content,
        }
        return SimpleNamespace(content=content)

    monkeypatch.setattr(service_module.PlanService, "save_implantation_data", _save_implantation_data)

    result = ImplantationPersonaProfileService.apply_update(
        actor_user_id=7,
        company_id=12,
        plan_id=12,
        segment_name="Revendedores / Instaladores Credenciados",
        persona_name="Persona Principal",
        profile_text="perfil novo",
    )

    assert result.saved is True
    assert captured["payload"]["section_key"] == "model"
    persona = captured["payload"]["content"]["segments"][0]["personas"][0]
    assert persona["profile"] == "perfil novo"


def test_preview_update_denies_collaborator(monkeypatch):
    monkeypatch.setattr(service_module.db.session, "get", lambda *_args, **_kwargs: SimpleNamespace(id=7))
    monkeypatch.setattr(service_module, "get_access_profile", lambda company_id, user=None: "collaborator")

    with pytest.raises(ImplantationPersonaProfilePermissionError):
        ImplantationPersonaProfileService.preview_update(
            actor_user_id=7,
            company_id=12,
            plan_id=12,
            segment_name="Revendedores / Instaladores Credenciados",
            persona_name="Persona Principal",
            profile_text="perfil novo",
        )
