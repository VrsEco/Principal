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


def test_execution_workspace_uses_one_context_rail_on_the_right():
    source = _template_source()
    assert 'className = \'meeting-context-rail\'' in source
    assert 'Roteiro da reunião' in source
    assert "participantsCard.className = 'meeting-context-card meeting-participants-rail'" in source
    assert 'grid-template-columns:minmax(0,1fr) minmax(310px,350px)' in source


def test_execution_workspace_does_not_repeat_summary_metrics_in_context_rail():
    source = _template_source()
    assert 'meeting-summary-grid' not in source
    assert 'meeting-summary-topics' not in source
    assert 'meeting-summary-decisions' not in source
    assert 'meeting-summary-activities' not in source


def test_execution_workspace_removes_general_notes_and_observation_actions_from_ui():
    source = _template_source()
    assert "notesGroup.id = 'meeting-notes-group'" in source
    assert '#meeting-notes-group{display:none!important}' in source
    assert 'Adicionar observação' not in source


def test_discussions_are_newest_first_and_collapsible():
    source = _template_source()
    assert "orderedDiscussions = discussions.map((disc, index) => ({ disc, index })).reverse()" in source
    assert 'function toggleDiscussao(index)' in source
    assert 'class="discussion-accordion-header"' in source
    assert 'aria-expanded="${isExpanded' in source
    assert '+ Nova discussão' in source


def test_discussion_has_visually_separated_title_decision_and_activity_blocks():
    source = _template_source()
    assert 'Título do assunto' in source
    assert 'Discussão / decisão registrada' in source
    assert 'Atividades geradas' in source
    assert 'class="discussion-subsection"' in source
    assert 'class="discussion-activities-list"' in source
    assert 'function getActivityDiscussionIndex(activity)' in source


def test_save_and_finish_actions_are_created_in_the_editor_toolbar():
    source = _template_source()
    toolbar_block = source[source.index("const editorToolbar"):source.index("if (!document.getElementById('meeting-save-toast')")]
    assert "saveButton.id = 'btn-salvar-reuniao'" in toolbar_block
    assert "finishButton.id = 'btn-finalizar-reuniao-quick'" in toolbar_block
    assert 'editorToolbar.appendChild(saveButton)' in toolbar_block
    assert 'editorToolbar.appendChild(finishButton)' in toolbar_block


def test_legacy_activities_stay_on_the_first_subject_when_new_subjects_are_added():
    source = _template_source()
    assert 'return discussions.length ? 0 : null;' in source


def test_information_card_is_visible_for_new_meetings_and_hidden_for_execution():
    source = _template_source()
    assert "if (informationCard) informationCard.hidden = false;" in source
    assert "if (informationCard) informationCard.hidden = true;" in source
    assert ".meeting-information-card[hidden]{display:none!important}" in source


def test_external_participant_has_structured_contact_form_and_validation():
    source = _template_source()
    assert 'id="participant-external-name"' in source
    assert 'id="participant-external-email"' in source
    assert 'id="participant-external-whatsapp"' in source
    assert "Informe o e-mail ou o WhatsApp do convidado externo." in source
    assert "participants.external.push({ name, email, whatsapp: normalizedWhatsapp })" in source
    assert "? `55${whatsappDigits}`" in source


def test_external_participant_is_identified_as_minutes_recipient():
    source = _template_source()
    assert 'Externo · destinatário da ata' in source
    assert 'external-participant-meta' in source
    assert 'E-mail: ${escapeHtml(p.email)}' in source
    assert 'WhatsApp: ${escapeHtml(p.whatsapp)}' in source
