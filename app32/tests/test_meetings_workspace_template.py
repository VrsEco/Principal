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


def test_new_meeting_has_explicit_title_persistence_action():
    source = _template_source()
    assert 'id="btn-save-meeting-title"' in source
    assert 'onclick="salvarTituloReuniao()"' in source
    assert 'function salvarTituloReuniao()' in source
    assert "titleInput.addEventListener('keydown'" in source


def test_sidebar_uses_discussion_shortcuts_without_reusable_agenda():
    source = _template_source()
    assert 'id="meeting-topic-shortcuts"' in source
    assert 'function renderTopicShortcuts()' in source
    assert 'function focarTemaDiscussao(index)' in source
    assert 'Reutilizar' not in source
    assert 'saved-agenda-modal' not in source
    assert 'agenda-item-input' not in source


def test_topic_and_decision_counters_use_discussions_not_legacy_agenda():
    source = _template_source()
    assert "'meeting-counter-topics': (discussions || [])" in source
    assert "'meeting-counter-decisions': (discussions || [])" in source
    assert "'meeting-counter-topics': (agendaItems || [])" not in source


def test_activity_editor_captures_budget_effort_and_priority():
    source = _template_source()
    assert 'data-activity-field="budget"' in source
    assert 'data-activity-field="estimated_hours"' in source
    assert 'data-activity-field="priority"' in source
    assert "budget: activity.budget || activity.amount || ''" in source


def test_meetings_workspace_preserves_mcp_stable_ids_and_project_task_link():
    source = _template_source()
    assert "createWorkspaceItemId('topic')" in source
    assert "createWorkspaceItemId('activity')" in source
    assert "project_task_id: activity.project_task_id || null" in source
    assert "disc.discussion || disc.decision || ''" in source
