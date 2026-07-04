from __future__ import annotations

import re
from pathlib import Path

from jinja2 import Environment


REPO_ROOT = Path(__file__).resolve().parents[2]


P1_APP32_TEMPLATE_CONTRACTS = [
    "app32/templates/legacy/company_details.html",
    "app32/templates/legacy/grv_occurrences_v2.html",
    "app32/templates/legacy/grv_project_manage.html",
    "app32/templates/legacy/grv_projects_analysis.html",
    "app32/templates/legacy/grv_projects_portfolios.html",
    "app32/templates/legacy/grv_projects_projects.html",
    "app32/templates/legacy/grv_routine_incidents.html",
    "app32/templates/legacy/grv_routine_incidents_OLD_BACKUP.html",
    "app32/templates/legacy/grv_routine_work_distribution.html",
    "app32/templates/legacy/projects_sidebar.html",
    "app32/templates/modules/companies/company_identity_v2.html",
    "app32/templates/modules/consultive/structural_front.html",
    "app32/templates/modules/my_work/_agendas_panel.html",
    "app32/templates/modules/my_work/my_work_report_compact_print.html",
    "app32/templates/modules/my_work/my_work_v2.html",
    "app32/templates/modules/my_work_modals.html",
    "app32/templates/modules/projects/project_form_v2.html",
    "app32/templates/modules/projects/project_task_v2.html",
    "app32/templates/modules/projects/projects_v2.html",
    "app32/templates/project_portfolios.html",
    "app32/templates/report_settings.html",
    "app32/templates/usuarios/editar.html",
]

CONTROL_RE = re.compile(r"<(?:input|select|textarea|button|a|form)\b", re.I)


def test_app32_p1_templates_have_parseable_ui_contracts():
    env = Environment()
    missing = []
    invalid = []
    without_controls = []

    for relative_template in P1_APP32_TEMPLATE_CONTRACTS:
        path = REPO_ROOT / relative_template
        if not path.exists():
            missing.append(relative_template)
            continue
        source = path.read_text(encoding="utf-8", errors="ignore")
        try:
            env.parse(source)
        except Exception as exc:  # pragma: no cover
            invalid.append(f"{relative_template}: {exc}")
        if not CONTROL_RE.search(source):
            without_controls.append(relative_template)

    assert missing == []
    assert invalid == []
    assert without_controls == []
