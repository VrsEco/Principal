from pathlib import Path


def test_company_role_permissions_ui_contracts_are_present():
    template = Path("app32/templates/modules/companies/company_form_v2.html").read_text(encoding="utf-8")
    script = Path("app32/static/js/company_role_permissions.js").read_text(encoding="utf-8")
    css = Path("app32/static/css/company_role_permissions.css").read_text(encoding="utf-8")

    assert 'id="role-permission-matrix"' in template
    assert 'id="role-permission-search"' in template
    assert 'id="role-permission-preset"' in template
    assert 'id="role-permission-preset-name"' in template
    assert 'id="role-permission-preset-description"' in template
    assert 'id="role-permission-preset-delete"' in template
    assert '/api/companies/${companyId}/permission-catalog' in script
    assert '/api/companies/${this.companyId}/role-permission-presets' in script
    assert 'applyPreset(presetKey)' in script
    assert 'saveCompanyPreset()' in script
    assert 'deleteSelectedCompanyPreset()' in script
    assert 'data-indeterminate="true"' in script or 'data-indeterminate="${indeterminate}"' in script
    assert 'window.rolePermissionMatrix' in script
    assert '.role-permissions-table' in css
    assert '.role-permission-checkbox' in css
    assert '.role-permission-badge--inherit' in css
    assert '.role-permissions-preset-editor' in css
