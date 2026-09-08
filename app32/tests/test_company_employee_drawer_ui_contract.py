from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_employee_registration_is_owned_by_collaborators_drawer():
    template = (ROOT / "templates/modules/companies/company_identity_v2.html").read_text(encoding="utf-8")
    script = (ROOT / "static/js/company_identity.js").read_text(encoding="utf-8")

    assert 'id="identityNewEmployee"' in template
    assert 'id="identityEmployeeDrawer"' in template
    assert 'id="identityEmployeeRole"' in template
    assert 'data-employee-mode="new"' in template
    assert 'data-employee-mode="existing"' in template
    assert 'id="identityEmployeeCreateRole"' in template
    assert 'id="identityNewEmployeeForm"' not in template
    assert "function openEmployeeDrawer()" in script
    assert "function saveEmployeeFromDrawer(event)" in script
    assert "identityEmployeeRole').value" in script
    assert "/roles/${roleId}/employees" in script
    assert "identityRoleId').value" not in script[script.index("function saveEmployeeFromDrawer(event)"):]


def test_employee_drawer_keeps_login_creation_out_of_org_registration():
    template = (ROOT / "templates/modules/companies/company_identity_v2.html").read_text(encoding="utf-8")
    script = (ROOT / "static/js/company_identity.js").read_text(encoding="utf-8")

    assert "Este cadastro não cria login" in template
    assert "Nenhum login será criado" in script
