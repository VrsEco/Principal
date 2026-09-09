import pytest

from services.people_workspace_service import PeopleWorkspaceService, PeopleWorkspaceValidationError


@pytest.mark.parametrize('profile', ['administrator', 'client', 'collaborator'])
def test_accepts_only_official_people_profiles(profile):
    result = PeopleWorkspaceService._normalize_user_payload(
        {'name': 'Ana', 'email': 'ana@example.com', 'password': 'segredo123', 'access_profile': profile},
        creating=True,
    )
    assert result['access_profile'] == profile


@pytest.mark.parametrize('profile', ['', 'admin', 'manager', 'employee', True])
def test_rejects_non_official_people_profiles(profile):
    with pytest.raises(PeopleWorkspaceValidationError):
        PeopleWorkspaceService._normalize_user_payload(
            {'name': 'Ana', 'email': 'ana@example.com', 'password': 'segredo123', 'access_profile': profile},
            creating=True,
        )


def test_user_requires_password_only_when_creating_global_account():
    assert PeopleWorkspaceService._normalize_user_payload({'is_active': False}, creating=False) == {'is_active': False}
    with pytest.raises(PeopleWorkspaceValidationError, match='senha temporária'):
        PeopleWorkspaceService._normalize_user_payload(
            {'name': 'Ana', 'email': 'ana@example.com', 'access_profile': 'client'}, creating=True
        )


def test_people_workspace_route_contract_is_tenant_scoped():
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    source = (root / 'api/routes/companies.py').read_text(encoding='utf-8')
    assert "/api/companies/<int:company_id>/people/workspace" in source
    assert "/api/companies/<int:company_id>/people/users" in source
    assert "/api/companies/<int:company_id>/people/employees" in source
    assert "@permission_required('companies', 'edit')" in source
