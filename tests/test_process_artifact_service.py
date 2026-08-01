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
    assert 'data-artifact-new="form"' in modeler_source
    assert 'data-artifact-new="check"' in modeler_source
    assert "/api/process-artifact-executions/${artifactExecutionId}" in runtime_source
