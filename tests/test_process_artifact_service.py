import sys
from pathlib import Path
from types import SimpleNamespace

import pytest


ROOT = Path(__file__).resolve().parents[1]
APP_DIR = ROOT / "app32"
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from models.process_artifact import (  # noqa: E402
    ProcessActivityArtifactDefinition,
    ProcessActivityArtifactExecution,
    ProcessActivityArtifactLink,
)
from services import process_artifact_service as service  # noqa: E402


def test_artifact_models_require_company_id_and_expected_constraints():
    for model in (
        ProcessActivityArtifactDefinition,
        ProcessActivityArtifactLink,
        ProcessActivityArtifactExecution,
    ):
        assert model.__table__.columns["company_id"].nullable is False

    definition_constraints = {constraint.name for constraint in ProcessActivityArtifactDefinition.__table__.constraints}
    link_constraints = {constraint.name for constraint in ProcessActivityArtifactLink.__table__.constraints}
    execution_constraints = {constraint.name for constraint in ProcessActivityArtifactExecution.__table__.constraints}

    assert "uq_process_artifact_definition_version" in definition_constraints
    assert "uq_process_artifact_link_activity_definition" in link_constraints
    assert "uq_process_artifact_execution_activity_definition" in execution_constraints


@pytest.mark.parametrize("artifact_type", ("pop", "form", "check", "ai", "data_in", "data_out"))
def test_normalize_artifact_type_accepts_canonical_types(artifact_type):
    assert service.normalize_artifact_type(artifact_type) == artifact_type


def test_normalize_artifact_type_rejects_unknown_type():
    with pytest.raises(service.ProcessArtifactValidationError, match="Tipo de artefato inválido"):
        service.normalize_artifact_type("spreadsheet")


def test_validate_form_configuration_rejects_duplicate_field_ids():
    config = {
        "sections": [
            {"id": "main", "title": "Principal", "fields": [{"id": "customer", "label": "Cliente", "type": "text"}]},
            {"id": "extra", "title": "Extra", "fields": [{"id": "customer", "label": "Cliente novamente", "type": "text"}]},
        ]
    }
    with pytest.raises(service.ProcessArtifactValidationError, match="IDs de campos devem ser únicos"):
        service.validate_artifact_configuration("form", config)


def test_validate_form_configuration_rejects_unknown_field_type():
    config = {
        "sections": [
            {"id": "main", "title": "Principal", "fields": [{"id": "customer", "label": "Cliente", "type": "spreadsheet"}]},
        ]
    }
    with pytest.raises(service.ProcessArtifactValidationError, match="Tipo de campo inválido"):
        service.validate_artifact_configuration("form", config)


def test_validate_check_configuration_requires_unique_item_ids():
    config = {
        "items": [
            {"id": "document", "label": "Documento conferido"},
            {"id": "document", "label": "Documento validado"},
        ]
    }
    with pytest.raises(service.ProcessArtifactValidationError, match="IDs duplicados"):
        service.validate_artifact_configuration("check", config)


def test_build_definition_snapshot_hydrates_legacy_pop_without_mutating_definition():
    routine = SimpleNamespace(
        id=91,
        code="AA.C.1.01",
        name="Conferir cadastro",
        description="POP atualizado",
        bpmn_element_id="Activity_Check",
        bpmn_element_type="bpmn:Task",
        bpmn_data_objects=[{"id": "Data_1", "name": "Cadastro"}],
    )
    definition = SimpleNamespace(
        artifact_type="pop",
        legacy_process_routine=routine,
        to_dict=lambda: {
            "id": 7,
            "name": "Nome no primeiro backfill",
            "description": "Descrição inicial",
            "artifact_type": "pop",
        },
    )

    snapshot = service.build_definition_snapshot(definition)

    assert snapshot["name"] == "Conferir cadastro"
    assert snapshot["description"] == "POP atualizado"
    assert snapshot["legacy_pop"]["process_routine_id"] == 91
    assert snapshot["legacy_pop"]["bpmn_data_objects"][0]["name"] == "Cadastro"


def test_evaluate_required_artifacts_blocks_only_incomplete_required_items():
    executions = [
        SimpleNamespace(
            id=1,
            status="completed",
            definition_snapshot_json={"link": {"is_required": True}},
        ),
        SimpleNamespace(
            id=2,
            status="in_progress",
            definition_snapshot_json={"link": {"is_required": True}},
        ),
        SimpleNamespace(
            id=3,
            status="pending",
            definition_snapshot_json={"link": {"is_required": False}},
        ),
    ]

    result = service.evaluate_required_artifacts(executions)

    assert result == {
        "required_total": 2,
        "required_completed": 1,
        "activity_may_complete": False,
        "blocking_artifact_execution_ids": [2],
    }


def test_evaluate_required_artifacts_allows_completion_when_required_items_finish():
    executions = [
        SimpleNamespace(
            id=1,
            status="completed",
            definition_snapshot_json={"link": {"is_required": True}},
        ),
        SimpleNamespace(
            id=2,
            status="skipped",
            definition_snapshot_json={
                "link": {
                    "is_required": True,
                    "completion_policy_json": {"allow_skip": True},
                }
            },
        ),
    ]

    result = service.evaluate_required_artifacts(executions)

    assert result["activity_may_complete"] is True
    assert result["blocking_artifact_execution_ids"] == []


def test_evaluate_required_artifacts_rejects_unauthorized_skip():
    execution = SimpleNamespace(
        id=9,
        status="skipped",
        definition_snapshot_json={
            "link": {
                "is_required": True,
                "completion_policy_json": {"allow_skip": False},
            }
        },
    )

    result = service.evaluate_required_artifacts([execution])

    assert result["activity_may_complete"] is False
    assert result["blocking_artifact_execution_ids"] == [9]


def test_ensure_pop_artifact_uses_tenant_process_and_deterministic_legacy_key(monkeypatch):
    class FakeQuery:
        @staticmethod
        def filter_by(**_kwargs):
            return SimpleNamespace(first=lambda: None)

    fake_definition_model = SimpleNamespace(query=FakeQuery())
    created_definition = SimpleNamespace(id=501)
    linked = SimpleNamespace(id=601)
    calls = {}

    def fake_create(company_id, process_id, payload, *, commit):
        calls["create"] = (company_id, process_id, payload, commit)
        return created_definition

    def fake_link(company_id, process_id, definition_id, payload, *, commit):
        calls["link"] = (company_id, process_id, definition_id, payload, commit)
        return linked

    monkeypatch.setattr(service, "ProcessActivityArtifactDefinition", fake_definition_model)
    monkeypatch.setattr(service, "create_artifact_definition", fake_create)
    monkeypatch.setattr(service, "link_artifact_to_activity", fake_link)
    monkeypatch.setattr(service.db.session, "commit", lambda: calls.setdefault("committed", True))

    routine = SimpleNamespace(
        id=77,
        company_id=9,
        process_id=2,
        code="AA.C.1.1.01",
        name="Atividade 01",
        description="POP legado",
        bpmn_element_id="Activity_01",
        bpmn_element_type="bpmn:Task",
        order_index=4,
    )

    definition, link, created = service.ensure_pop_artifact_for_routine(routine)

    assert definition is created_definition
    assert link is linked
    assert created is True
    assert calls["create"][0:2] == (9, 2)
    assert calls["create"][2]["artifact_key"] == "legacy-pop-77"
    assert calls["create"][2]["artifact_type"] == "pop"
    assert calls["link"][0:3] == (9, 2, 501)
    assert calls["link"][3]["bpmn_element_id"] == "Activity_01"
    assert calls["committed"] is True


def test_update_form_execution_requires_mandatory_answers(monkeypatch):
    execution = SimpleNamespace(
        id=81,
        artifact_type="form",
        status="in_progress",
        output_json={},
        evidence_json={},
        error_json={},
        started_at=None,
        completed_at=None,
        definition_snapshot_json={
            "configuration_json": {
                "sections": [
                    {
                        "id": "main",
                        "title": "Principal",
                        "fields": [{"id": "customer", "label": "Cliente", "type": "text", "required": True}],
                    }
                ]
            }
        },
    )
    monkeypatch.setattr(service, "get_artifact_execution", lambda company_id, artifact_execution_id: execution)

    with pytest.raises(service.ProcessArtifactValidationError, match="Campo obrigatório não preenchido"):
        service.update_artifact_execution(9, 81, {"status": "completed", "output_json": {"answers": {}}})


def test_update_form_execution_completes_valid_submission(monkeypatch):
    calls = {}
    execution = SimpleNamespace(
        id=82,
        artifact_type="form",
        status="in_progress",
        output_json={},
        evidence_json={},
        error_json={"previous": "error"},
        started_at=None,
        completed_at=None,
        definition_snapshot_json={
            "configuration_json": {
                "sections": [
                    {
                        "id": "main",
                        "title": "Principal",
                        "fields": [{"id": "customer", "label": "Cliente", "type": "text", "required": True}],
                    }
                ]
            }
        },
    )
    monkeypatch.setattr(service, "get_artifact_execution", lambda company_id, artifact_execution_id: execution)
    monkeypatch.setattr(service.db.session, "commit", lambda: calls.setdefault("committed", True))

    result = service.update_artifact_execution(
        9,
        82,
        {"status": "completed", "output_json": {"answers": {"customer": "Versus"}}},
    )

    assert result.status == "completed"
    assert result.output_json["answers"]["customer"] == "Versus"
    assert result.started_at is not None
    assert result.completed_at is not None
    assert result.error_json == {}
    assert calls["committed"] is True


def test_update_check_execution_requires_evidence_and_blocks_rejection(monkeypatch):
    execution = SimpleNamespace(
        id=83,
        artifact_type="check",
        status="in_progress",
        output_json={},
        evidence_json={},
        error_json={},
        started_at=None,
        completed_at=None,
        definition_snapshot_json={
            "configuration_json": {
                "failure_behavior": "block",
                "items": [
                    {
                        "id": "document",
                        "label": "Documento conferido",
                        "required": True,
                        "evidence_required": True,
                        "allow_na": False,
                    }
                ],
            }
        },
    )
    monkeypatch.setattr(service, "get_artifact_execution", lambda company_id, artifact_execution_id: execution)

    with pytest.raises(service.ProcessArtifactValidationError, match="Evidência obrigatória ausente"):
        service.update_artifact_execution(
            9,
            83,
            {"status": "completed", "output_json": {"answers": {"document": {"status": "accepted"}}}},
        )

    with pytest.raises(service.ProcessArtifactValidationError, match="Item reprovado bloqueia"):
        service.update_artifact_execution(
            9,
            83,
            {
                "status": "completed",
                "output_json": {"answers": {"document": {"status": "rejected"}}},
                "evidence_json": {"document": "evidence:123"},
            },
        )


def test_artifact_editor_and_runtime_routes_are_registered_in_app_source():
    app_source = (APP_DIR / "app.py").read_text(encoding="utf-8")
    routes_source = (APP_DIR / "api" / "routes" / "processes.py").read_text(encoding="utf-8")
    modeler_source = (APP_DIR / "static" / "js" / "process_bpmn_modeler.js").read_text(encoding="utf-8")
    runtime_source = (APP_DIR / "static" / "js" / "process_instance_runtime.js").read_text(encoding="utf-8")

    assert "/api/processes/<int:process_id>/activity-artifacts" in app_source
    assert "/api/process-activity-artifacts/<int:artifact_id>/publish" in app_source
    assert "/api/process-artifact-executions/<int:artifact_execution_id>" in app_source
    assert "/processes/<int:process_id>/artifacts/new/<string:artifact_type>" in routes_source
    assert "/processes/<int:process_id>/artifacts/<int:artifact_id>/edit" in routes_source
    assert "App32ArtifactContextPadProvider" in modeler_source
    assert "openArtifactQuickMenu" in modeler_source
    assert "['pop', 'form', 'check', 'ai', 'data_in', 'data_out']" in modeler_source
    assert "openAiDialog" in modeler_source
    assert "openArtifactEditorFromMarker" in modeler_source
    assert "element.dblclick" in modeler_source
    assert "name: item.marker" in modeler_source
    assert "/api/process-artifact-executions/${artifactExecutionId}" in runtime_source


def test_modeler_uses_contextual_artifact_menu_and_on_demand_ai_dialog():
    template_source = (APP_DIR / "templates" / "modules" / "processes" / "bpmn_modeler.html").read_text(encoding="utf-8")
    editor_source = (APP_DIR / "templates" / "modules" / "processes" / "data_artifact_editor.html").read_text(encoding="utf-8")
    routes_source = (APP_DIR / "api" / "routes" / "processes.py").read_text(encoding="utf-8")

    assert 'id="bpmnArtifactQuickMenu"' in template_source
    assert 'id="bpmnAiDialog" hidden' in template_source
    assert "bpmn-ai-sidebar" not in template_source
    assert "data_artifact_editor.html" in routes_source
    assert "{'form', 'check', 'data_in', 'data_out'}" in routes_source
    assert "artifact-editor--{{ 'data-in' if is_input else 'data-out' }}" in editor_source
    assert "completion_policy_json:{mode:'successful_transfer'" in editor_source


def test_artifact_editors_have_direct_return_to_modeler():
    for template_name in ("form_artifact_editor.html", "check_artifact_editor.html", "data_artifact_editor.html"):
        source = (APP_DIR / "templates" / "modules" / "processes" / template_name).read_text(encoding="utf-8")
        assert "processes.process_bpmn_modeler" in source
        assert "Voltar ao Modeler" in source
        assert "history.back()" not in source


def test_artifact_editors_use_shared_responsive_ui_shell():
    template_names = (
        "form_artifact_editor.html",
        "check_artifact_editor.html",
        "data_artifact_editor.html",
    )
    for template_name in template_names:
        source = (APP_DIR / "templates" / "modules" / "processes" / template_name).read_text(encoding="utf-8")
        assert "{% block head %}" in source
        assert "{% block extra_head %}" not in source
        assert "static_asset_version('css/process_artifact_editor.css')" in source
        assert "artifact-editor__eyebrow" in source
        assert "artifact-editor__sidebar-head" in source
        assert "artifact-status" in source

    css_source = (APP_DIR / "static" / "css" / "process_artifact_editor.css").read_text(encoding="utf-8")
    assert ".artifact-editor--check" in css_source
    assert ".artifact-editor--data-in" in css_source
    assert ".artifact-editor--data-out" in css_source
    assert ".artifact-row--check" in css_source
    assert "@media (max-width: 900px)" in css_source


def test_pop_focus_and_modeler_follow_compact_artifact_ui_pattern():
    details_source = (APP_DIR / "templates" / "modules" / "processes" / "process_details_v2.html").read_text(encoding="utf-8")
    modeler_template = (APP_DIR / "templates" / "modules" / "processes" / "bpmn_modeler.html").read_text(encoding="utf-8")
    modeler_css = (APP_DIR / "static" / "css" / "process_bpmn_modeler.css").read_text(encoding="utf-8")

    assert "process-details--pop-focus" in details_source
    assert "pop-artifact-focus-hero" in details_source
    assert "Editor de POP" in details_source
    assert "Voltar ao Modeler" in details_source
    assert "popFocusRoutineContext" in details_source
    assert "bpmn-modeler-hero__identity" in modeler_template
    assert "bpmn-modeler-hero__badge" in modeler_template
    assert 'data-action="save"><i class="fas fa-save"' in modeler_template
    assert "bpmn-tool-btn--icon" in modeler_template
    assert "grid-template-columns: minmax(390px, 1.4fr)" in modeler_css
    assert "@media (max-width: 680px)" in modeler_css


def test_new_bpmn_tasks_use_the_defined_minimum_size_as_default():
    modeler_source = (APP_DIR / "static" / "js" / "process_bpmn_modeler.js").read_text(encoding="utf-8")

    assert "const OPERATIONAL_ACTIVITY_MIN_WIDTH = 240;" in modeler_source
    assert "const OPERATIONAL_ACTIVITY_MIN_HEIGHT = 72;" in modeler_source
    assert "applyOperationalActivityDefaultSize(shape);" in modeler_source
    assert "width: OPERATIONAL_ACTIVITY_MIN_WIDTH" in modeler_source
    assert "height: OPERATIONAL_ACTIVITY_MIN_HEIGHT" in modeler_source


def test_modeler_has_persistent_contextual_color_palette_for_bpmn_elements():
    modeler_source = (APP_DIR / "static" / "js" / "process_bpmn_modeler.js").read_text(encoding="utf-8")
    template_source = (APP_DIR / "templates" / "modules" / "processes" / "bpmn_modeler.html").read_text(encoding="utf-8")
    css_source = (APP_DIR / "static" / "css" / "process_bpmn_modeler.css").read_text(encoding="utf-8")

    assert "const BPMN_COLOR_PALETTE" in modeler_source
    assert "app32-color-element" in modeler_source
    assert "modeling.setColor([element], value);" in modeler_source
    assert "applyDefaultBpmnColor(shape)" in modeler_source
    assert "bpmn:StartEvent" in modeler_source
    assert "bpmn:EndEvent" in modeler_source
    assert 'id="bpmnColorMenu" hidden' in template_source
    assert 'id="bpmnColorSwatches"' in template_source
    assert "app32-color-entry" in css_source


def test_artifact_creation_stays_in_modeler_until_double_click():
    modeler_source = (APP_DIR / "static" / "js" / "process_bpmn_modeler.js").read_text(encoding="utf-8")
    template_source = (APP_DIR / "templates" / "modules" / "processes" / "bpmn_modeler.html").read_text(encoding="utf-8")
    configure_source = modeler_source.split("async function configureContextArtifact", 1)[1].split("function installAiInspector", 1)[0]

    assert "modeler.get('selection')?.select(marker);" in configure_source
    assert "Dê dois cliques no artefato para configurá-lo" in configure_source
    assert "openAiDialog(target)" not in configure_source
    assert "window.location.href" not in configure_source
    assert "openArtifactEditorFromMarker" in modeler_source
    assert "element.dblclick" in modeler_source
    assert "Visão geral dos artefatos" not in template_source
    assert 'data-action="inspect-elements"' not in template_source
    assert 'id="bpmnPopBindingPanel"' not in template_source


def test_list_process_artifacts_filters_type_when_activity_is_provided(monkeypatch):
    monkeypatch.setattr(service, "_get_process", lambda company_id, process_id: object())
    monkeypatch.setattr(
        service,
        "list_activity_artifacts",
        lambda company_id, process_id, bpmn_element_id: [
            {"id": 1, "artifact_type": "form"},
            {"id": 2, "artifact_type": "data_in"},
        ],
    )

    result = service.list_process_artifact_definitions(
        9,
        2,
        artifact_type="data_in",
        bpmn_element_id="Activity_1",
    )

    assert result == [{"id": 2, "artifact_type": "data_in"}]


def test_process_details_exposes_artifact_views_in_one_flat_navigation_line():
    source = (APP_DIR / "templates" / "modules" / "processes" / "process_details_v2.html").read_text(encoding="utf-8")

    nav = source.split('<div class="tabs-nav process-tabs-nav"', 1)[1].split('</div>', 1)[0]
    expected_tabs = ("sipoc", "resources", "modeling", "pops", "forms", "checks", "ai", "routine", "indicators")
    for tab in expected_tabs:
        assert f"switchTab('{tab}')" in nav
    assert "flex-wrap: nowrap" in source
    assert "overflow-x: auto" in source
    assert "flex-wrap: wrap" not in source.split(".process-tabs-nav", 2)[2].split("}", 1)[0]


def test_process_details_loads_and_renders_forms_checks_and_ai_contracts():
    source = (APP_DIR / "templates" / "modules" / "processes" / "process_details_v2.html").read_text(encoding="utf-8")

    assert 'id="tab-forms"' in source
    assert 'id="tab-checks"' in source
    assert 'id="tab-ai"' in source
    assert "/api/processes/${processId}/activity-artifacts" in source
    assert "/api/processes/${processId}/activity-execution-contracts" in source
    assert "renderArtifactOverview('form')" in source
    assert "renderArtifactOverview('check')" in source
    assert "renderAiOverview()" in source
    assert "Adicionar no Modeler" in source
    assert "Configurar no Modeler" in source
