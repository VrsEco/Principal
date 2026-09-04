from decimal import Decimal
from pathlib import Path

import pytest

from services.company_role_hierarchy_service import (
    CompanyRoleHierarchyService as Service,
    RoleHierarchyValidationError,
)


@pytest.mark.parametrize("value", [True, False, None, "", 1.5, "2.1", -1, "NaN", "Infinity", 2147483648])
def test_reject_invalid_headcount(value):
    with pytest.raises(RoleHierarchyValidationError):
        Service._normalize_payload(1, {"title": "Analista", "headcount_planned": value})


@pytest.mark.parametrize("value", [0, 2, "3", "4.0"])
def test_accept_integer_headcount(value):
    result = Service._normalize_payload(1, {"title": "Analista", "headcount_planned": value})
    assert result["headcount_planned"] == int(float(value))


@pytest.mark.parametrize("value", [True, False, 0, -1, 169, "NaN", "Infinity", "abc", 40.001])
def test_reject_invalid_weekly_hours(value):
    with pytest.raises(RoleHierarchyValidationError):
        Service._normalize_payload(1, {"title": "Analista", "weekly_hours": value})


@pytest.mark.parametrize("value,expected", [(None, None), ("", None), (40, Decimal("40")), ("36.25", Decimal("36.25"))])
def test_optional_weekly_hours(value, expected):
    assert Service._normalize_payload(1, {"title": "Analista", "weekly_hours": value})["weekly_hours"] == expected


@pytest.mark.parametrize("value", [True, False, 1.5, "2.5", -1, 0, "NaN", "Infinity"])
def test_parent_id_is_not_coerced(value):
    with pytest.raises(RoleHierarchyValidationError):
        Service._optional_int(value)


def test_role_without_occupant_or_login():
    assert Service._normalize_payload(1, {"title": " Analista "}) == {"title": "Analista"}


def test_partial_update_does_not_reset_omitted_fields():
    assert Service._normalize_payload(1, {"notes": "Responsável pela entrega"}, role_id=2) == {
        "notes": "Responsável pela entrega"
    }


@pytest.mark.parametrize("value", [[], {}, 12, True])
def test_reject_non_text_responsibilities(value):
    with pytest.raises(RoleHierarchyValidationError):
        Service._normalize_payload(1, {"title": "Analista", "notes": value})


def test_empty_responsibilities_clear_field():
    assert Service._normalize_payload(1, {"notes": "  "}, role_id=2) == {"notes": None}


def test_editor_capacity_fields_contract():
    root = Path(__file__).resolve().parents[1]
    template = (root / "templates/modules/companies/company_identity_v2.html").read_text(encoding="utf-8")
    script = (root / "static/js/company_identity.js").read_text(encoding="utf-8")
    for field in ("identityRoleWeeklyHours", "identityRoleNotes"):
        assert f'id="{field}"' in template
        assert f"byId('{field}').value" in script
    assert "identityRoleEditorForm').reportValidity()" in script
    assert "headcount_planned: Number(" in script


@pytest.mark.parametrize("value", [True, 7, [], {}, "a" * 10001])
def test_qualification_requirements_validate_type_and_size(value):
    with pytest.raises(RoleHierarchyValidationError):
        Service._normalize_payload(1, {"qualification_requirements": value}, role_id=2)


@pytest.mark.parametrize("value,expected", [(None, None), ("  ", None), (" Excel avançado ", "Excel avançado"), ("a" * 10000, "a" * 10000)])
def test_qualification_requirements_normalization(value, expected):
    assert Service._normalize_payload(1, {"qualification_requirements": value}, role_id=2) == {"qualification_requirements": expected}


def test_qualification_requirements_serialized_in_role_and_summary():
    from models import Role
    from services.company_identity_service import CompanyIdentityService
    role = Role(id=2, company_id=1, title="Analista", qualification_requirements="Excel avançado")
    assert role.to_dict()["qualification_requirements"] == "Excel avançado"
    assert CompanyIdentityService._serialize_role(role, [])["qualification_requirements"] == "Excel avançado"


def test_qualification_form_contract():
    root = Path(__file__).resolve().parents[1]
    template = (root / 'templates/modules/companies/company_identity_v2.html').read_text(encoding='utf-8')
    script = (root / 'static/js/company_identity_qualifications.js').read_text(encoding='utf-8')
    assert 'identityQualificationForm' in template
    assert 'qualification-evidences' in script
    assert 'não confirma aderência' in script
