import json
from pathlib import Path
import shutil
import subprocess

import pytest


ROOT_DIR = Path(__file__).resolve().parents[2]
APP_ROOT = ROOT_DIR / "app32" if (ROOT_DIR / "app32").exists() else ROOT_DIR


@pytest.mark.skipif(shutil.which("node") is None, reason="Node.js não disponível")
def test_my_work_report_payload_preserves_empty_project_and_process_selection():
    script_path = APP_ROOT / "static" / "js" / "my-work.js"
    node_script = f"""
const fs = require('fs');
const vm = require('vm');
const source = fs.readFileSync({json.dumps(str(script_path))}, 'utf8');
const sandbox = {{
  window: {{}},
  document: {{ addEventListener() {{}}, getElementById() {{ return null; }} }},
  console: {{ log() {{}}, warn() {{}}, error() {{}} }},
  setTimeout() {{}}, clearTimeout() {{}}, setInterval() {{}}, clearInterval() {{}},
  URLSearchParams,
}};
vm.createContext(sandbox);
vm.runInContext(source, sandbox);
const result = vm.runInContext(`
  state.selectedCompanyIds = [11];
  state.projectsDirectory = [{{ id: 101, company_id: 11, title: 'Projeto' }}];
  state.processesDirectory = [{{ id: 201, company_id: 11, name: 'Processo' }}];
  state.selectedProjectIds = [];
  state.selectedProcessIds = [];
  JSON.stringify(buildReportFiltersPayload());
`, sandbox);
process.stdout.write(result);
"""

    completed = subprocess.run(
        ["node", "-e", node_script],
        check=True,
        capture_output=True,
        text=True,
    )

    assert json.loads(completed.stdout) == {
        "company_ids": [11],
        "project_selection": "none",
        "process_selection": "none",
        "delivery_tags": ["open"],
    }


def test_normalized_process_activity_exposes_canonical_owner_id():
    from services.my_work.process_service import _process_row_from_normalized
    from api.routes.my_work import _activity_matches_process_owner

    row = _process_row_from_normalized({
        "instance_id": 1,
        "company_id": 11,
        "process_id": 22,
        "owner_id": 104,
        "owner_name": "Responsável do processo",
    })

    assert row["owner_id"] == 104
    assert row["owner_name"] == "Responsável do processo"
    assert _activity_matches_process_owner(row, [104]) is True
    assert _activity_matches_process_owner(row, [105]) is False


def test_my_work_template_busts_report_filter_asset_cache():
    template = APP_ROOT / "templates" / "modules" / "my_work" / "my_work_v2.html"

    assert "20260908-mywork-report-filter-parity" in template.read_text(encoding="utf-8")
