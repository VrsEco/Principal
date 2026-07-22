from pathlib import Path

TEMPLATE = Path(__file__).resolve().parents[1] / "templates" / "meetings_manage.html"


def _template_source():
    return TEMPLATE.read_text(encoding="utf-8")


def test_meetings_workspace_hides_scheduling_flow_but_preserves_legacy_contract_fields():
    source = _template_source()
    assert "meeting-legacy-tabs" in source
    assert "meeting-scheduling-fields" in source
    assert ".meeting-legacy-tabs,.meeting-scheduling-fields,.meeting-scheduling-only{display:none!important}" in source
    assert 'id="meeting-scheduled-date"' in source
    assert 'id="meeting-scheduled-time"' in source
    assert 'id="meeting-planned-duration"' in source


def test_meetings_workspace_is_decision_and_delivery_oriented():
    source = _template_source()
    assert "meeting-app32-workspace-shell" in source
    assert "meeting-counter-topics" in source
    assert "meeting-counter-decisions" in source
    assert "meeting-counter-activities" in source
    assert "Temas discutidos e decis&otilde;es" in source
    assert "Atividades e projetos gerados" in source


def test_meetings_requests_keep_explicit_company_scope():
    source = _template_source()
    assert "const meetingsCompanyId = {{ company.id|tojson }};" in source
    company_query = "?company_id=$" + "{meetingsCompanyId}"
    assert company_query in source
