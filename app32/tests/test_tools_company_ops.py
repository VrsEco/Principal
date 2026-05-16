from types import SimpleNamespace

import models.company as company_model
import utils.permissions as permissions
from src.intelligence.tools_domains import company_ops


class DummyCompany:
    def __init__(self, company_id=10, **overrides):
        self.id = company_id
        self.name = overrides.get("name", "Empresa Teste")
        self.legal_name = overrides.get("legal_name", "")
        self.cnpj = overrides.get("cnpj", "")
        self.client_code = overrides.get("client_code", "ET")
        self.description = overrides.get("description", "")
        self.segment = overrides.get("segment", "")
        self.size = overrides.get("size", "")
        self.city = overrides.get("city", "")
        self.state = overrides.get("state", "")
        self.coverage_physical = overrides.get("coverage_physical", "")
        self.coverage_online = overrides.get("coverage_online", "")
        self.experience_total = overrides.get("experience_total", "")
        self.experience_segment = overrides.get("experience_segment", "")
        self.mission = overrides.get("mission", "")
        self.vision = overrides.get("vision", "")
        self.values = overrides.get("values", "")
        self.logo_primary = overrides.get("logo_primary", "")
        self.logo_secondary = overrides.get("logo_secondary", "")
        self.logo_icon = overrides.get("logo_icon", "")
        self.is_active = overrides.get("is_active", True)

    @property
    def logo_count(self):
        return len([item for item in (self.logo_primary, self.logo_secondary, self.logo_icon) if item])

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "legal_name": self.legal_name,
            "cnpj": self.cnpj,
            "client_code": self.client_code,
            "description": self.description,
            "segment": self.segment,
            "size": self.size,
            "city": self.city,
            "state": self.state,
            "coverage_physical": self.coverage_physical,
            "coverage_online": self.coverage_online,
            "experience_total": self.experience_total,
            "experience_segment": self.experience_segment,
            "mission": self.mission,
            "vision": self.vision,
            "values": self.values,
            "logo_primary": self.logo_primary,
            "logo_secondary": self.logo_secondary,
            "logo_icon": self.logo_icon,
            "is_active": self.is_active,
            "logo_count": self.logo_count,
        }


class FakeQuery:
    def __init__(self, company):
        self.company = company

    def get(self, company_id):
        if self.company and int(company_id) == self.company.id:
            return self.company
        return None


def _configure_access(monkeypatch, company):
    monkeypatch.setattr(company_ops, "get_active_user", lambda: SimpleNamespace(id=7))
    monkeypatch.setattr(company_ops, "get_active_user_id", lambda: 7)
    monkeypatch.setattr(company_ops, "get_active_company_id", lambda: company.id)
    monkeypatch.setattr(company_model, "Company", SimpleNamespace(query=FakeQuery(company)))
    monkeypatch.setattr(permissions, "is_platform_admin", lambda user=None: False)
    monkeypatch.setattr(permissions, "can_access_company", lambda company_id, user=None: True)
    monkeypatch.setattr(permissions, "get_access_profile", lambda company_id, user=None: "client")


def test_get_company_profile_returns_structured_payload(monkeypatch):
    company = DummyCompany(segment="Consultoria", city="Salvador", state="BA")
    _configure_access(monkeypatch, company)

    payload = company_ops.get_company_profile()

    assert payload["success"] is True
    assert payload["company_id"] == 10
    assert payload["company"]["name"] == "Empresa Teste"
    assert payload["company"]["access_profile"] == "client"
    assert "segment" in payload["company"]["editable_fields"]


def test_update_company_profile_applies_whitelisted_changes(monkeypatch):
    company = DummyCompany()
    _configure_access(monkeypatch, company)
    commit_calls = []

    monkeypatch.setattr(
        company_ops,
        "company_schema",
        SimpleNamespace(
            load=lambda changes, instance=None, partial=True: [
                setattr(instance, key, value) for key, value in changes.items()
            ]
            and instance
        ),
    )
    monkeypatch.setattr(
        company_ops,
        "db",
        SimpleNamespace(session=SimpleNamespace(commit=lambda: commit_calls.append("commit"), rollback=lambda: None)),
    )

    payload = company_ops.update_company_profile(
        company_id=10,
        changes={"segment": "Serviços", "city": "Feira de Santana", "nao_permitido": "x"},
    )

    assert payload["success"] is True
    assert payload["updated_fields"] == ["city", "segment"]
    assert payload["ignored_fields"] == ["nao_permitido"]
    assert payload["company"]["segment"] == "Serviços"
    assert payload["company"]["city"] == "Feira de Santana"
    assert commit_calls == ["commit"]


def test_get_company_registration_diagnostics_reports_missing_fields(monkeypatch):
    company = DummyCompany(
        legal_name="Empresa Teste Ltda",
        cnpj="12.345.678/0001-90",
        segment="Consultoria",
        size="Médio",
        city="Salvador",
        state="BA",
    )
    _configure_access(monkeypatch, company)

    payload = company_ops.get_company_registration_diagnostics(company_id=10)

    assert payload["success"] is True
    assert payload["company_name"] == "Empresa Teste"
    assert "mission" in payload["missing_fields"]
    assert payload["groups"]["identificacao"]["completion_percent"] > 0
    assert payload["recommended_next_steps"]
