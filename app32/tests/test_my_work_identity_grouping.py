import inspect
import json
from pathlib import Path
import shutil
import subprocess
import sys

import pytest


ROOT_DIR = Path(__file__).resolve().parents[2]
APP_ROOT = ROOT_DIR / "app32" if (ROOT_DIR / "app32").exists() else ROOT_DIR
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))


def test_my_work_identity_resolution_does_not_grant_access_by_email():
    from services.my_work import employee_service

    source = inspect.getsource(employee_service.get_user_associated_companies)

    assert "results_by_email" not in source
    assert "lower(Employee.email" not in source
    assert "UserEmployeeAssignment.user_id" in source
    assert "Employee.user_id == user_id" in source


def test_active_associations_exclude_inactive_employee_and_company(monkeypatch):
    from services.my_work import discovery_service

    monkeypatch.setattr(
        discovery_service,
        "get_user_associated_companies",
        lambda user_id: [
            {"company_id": 1, "employee_id": 10, "employee_status": "active", "is_active": True},
            {"company_id": 2, "employee_id": 20, "employee_status": "inactive", "is_active": True},
            {"company_id": 3, "employee_id": 30, "employee_status": "active", "is_active": False},
            {"company_id": 4, "employee_id": 40, "employee_status": None, "is_active": True},
        ],
    )

    result = discovery_service._get_active_associated_companies(11)

    assert [(item["company_id"], item["employee_id"]) for item in result] == [(1, 10), (4, 40)]


@pytest.mark.skipif(shutil.which("node") is None, reason="Node.js não disponível")
def test_collaborator_filter_groups_user_but_preserves_employee_ids():
    script_path = APP_ROOT / "static" / "js" / "my-work.js"
    node_script = f"""
const fs = require('fs');
const vm = require('vm');
const source = fs.readFileSync({json.dumps(str(script_path))}, 'utf8');
const sandbox = {{
  window: {{}},
  document: {{ addEventListener() {{}}, getElementById() {{ return null; }} }},
  console: {{ log() {{}}, warn() {{}}, error() {{}} }},
  setTimeout() {{}},
  clearTimeout() {{}},
  setInterval() {{}},
  clearInterval() {{}},
  URLSearchParams,
}};
vm.createContext(sandbox);
vm.runInContext(source, sandbox);
const result = vm.runInContext(`
  state.selectedCompanyIds = [1, 2];
  state.collaborators = [
    {{ id: 101, user_id: 7, name: 'Ana', company_id: 1, company_name: 'Empresa A' }},
    {{ id: 202, user_id: 7, name: 'Ana', company_id: 2, company_name: 'Empresa B' }},
    {{ id: 303, user_id: null, name: 'Terceiro', company_id: 1, company_name: 'Empresa A' }}
  ];
  JSON.stringify(getCollaboratorOptions());
`, sandbox);
process.stdout.write(result);
"""

    completed = subprocess.run(
        ["node", "-e", node_script],
        check=True,
        capture_output=True,
        text=True,
    )
    options = json.loads(completed.stdout)

    ana = next(option for option in options if option["label"] == "Ana")
    third_party = next(option for option in options if option["label"] == "Terceiro")
    assert ana["id"] == "user:7"
    assert ana["valueIds"] == [101, 202]
    assert "2 empresas" in ana["helper"]
    assert third_party["id"] == "employee:303"
    assert third_party["valueIds"] == [303]
