from datetime import date
import inspect
from pathlib import Path
from types import SimpleNamespace
import importlib.util

from api.resources import project_task as project_task_resource
from models.project import Project
from schemas.project import projects_schema
from services.project_board_capacity_service import ProjectBoardCapacityService


def test_project_collection_schema_keeps_aggregate_stats_without_embedding_tasks(monkeypatch):
    monkeypatch.setattr(Project, "company_code", property(lambda self: "AA"))
    project = Project(id=31, company_id=9, name="DEV APP Gestão Versus")
    project._list_task_stats = {"total": 162, "open": 160, "completed": 2, "delayed": 1, "progress": 1}

    payload = projects_schema.dump([project])[0]

    assert payload["id"] == 31
    assert payload["code"] == "AA.J.31"
    assert "tasks" not in payload
    assert payload["task_stats"] == project._list_task_stats


def test_project_collection_schema_defaults_to_zero_stats(monkeypatch):
    monkeypatch.setattr(Project, "company_code", property(lambda self: "AA"))
    project = Project(id=32, company_id=9, name="Projeto sem atividades")

    payload = projects_schema.dump([project])[0]

    assert payload["task_stats"] == {
        "total": 0,
        "open": 0,
        "completed": 0,
        "delayed": 0,
        "progress": 0,
    }


def test_project_detail_schema_does_not_embed_tasks(monkeypatch):
    from schemas.project import project_schema

    monkeypatch.setattr(Project, "company_code", property(lambda self: "AA"))
    monkeypatch.setattr(Project, "task_stats", property(lambda self: {"total": 0, "open": 0, "completed": 0, "delayed": 0, "progress": 0}))
    project = Project(id=31, company_id=9, name="DEV APP Gestão Versus")

    payload = project_schema.dump(project)

    assert "tasks" not in payload
    assert payload["task_stats"]["total"] == 0


def test_compact_board_serializer_avoids_full_task_payload(monkeypatch):
    monkeypatch.setattr(
        project_task_resource.ProjectTaskDueDateChangeService,
        "build_task_context_map",
        lambda task_ids, company_id=None: {},
    )
    monkeypatch.setattr(
        project_task_resource.ProjectTaskDueDateChangeService,
        "empty_context",
        lambda: {"postponement_summary": {}},
    )
    task = SimpleNamespace(
        id=5108,
        code_sequence=3085,
        project_id=31,
        what="Entrega",
        who="Codex",
        employee_id=None,
        employee=None,
        due_date=date(2026, 8, 13),
        completion_date=None,
        how="Checklist",
        amount=None,
        status="planned",
        stage="todo",
        priority="high",
        notes="Evidência",
        score_weight=1,
        estimated_hours=2,
        worked_hours=1,
    )

    payload = project_task_resource._serialize_task_list_compact(
        [task],
        project=SimpleNamespace(code="AA.J.1"),
        company_id=9,
    )[0]

    assert payload["code"] == "AA.J.1.3085"
    assert payload["stage"] == "inbox"
    assert payload["due_date"] == "2026-08-13"
    assert "logs" not in payload
    assert "project_name" not in payload


def test_project_manage_uses_incremental_board_contract():
    template = (
        Path(__file__).resolve().parents[1]
        / "templates"
        / "modules"
        / "projects"
        / "project_manage.html"
    ).read_text(encoding="utf-8")

    assert "paginated: 'true'" in template
    assert "compact: 'true'" in template
    assert "per_page: '150'" in template
    assert "filterIncludeCompleted" in template
    assert "loadMoreTasks()" in template
    assert "Object.prototype.hasOwnProperty.call(currentTask, 'logs')" in template
    assert "kanbanCapacityGuardrail" in template
    assert "payload.capacity" in template


def test_project_analysis_all_tasks_excludes_soft_deleted_cards():
    source = inspect.getsource(project_task_resource.ProjectAllTasksResource.get)

    assert "ProjectTask.is_deleted.is_(False)" in source


def test_project_analysis_reports_completion_api_failure():
    template = (
        Path(__file__).resolve().parents[1]
        / "templates"
        / "modules"
        / "projects"
        / "project_analysis.html"
    ).read_text(encoding="utf-8")

    assert "Erro ao concluir atividade: " in template
    assert "errorPayload.error || errorPayload.message || 'Falha ao concluir atividade'" in template


def test_project_board_capacity_guardrail_thresholds():
    healthy = ProjectBoardCapacityService.build({"inbox": 499, "completed": 100})
    attention = ProjectBoardCapacityService.build({"inbox": 501, "completed": 100})
    critical = ProjectBoardCapacityService.build({"inbox": 1001, "completed": 100})

    assert healthy == {
        "status": "healthy",
        "open_count": 499,
        "soft_limit": 500,
        "hard_limit": 1000,
        "utilization_pct": 100,
        "rollover_recommended": False,
    }
    assert attention["status"] == "attention"
    assert attention["rollover_recommended"] is False
    assert critical["status"] == "critical"
    assert critical["rollover_recommended"] is True


def test_card_wrapper_uses_one_card_and_internal_checklist(monkeypatch):
    scripts_dir = (
        Path(__file__).resolve().parents[1]
        / ".agent"
        / "skills"
        / "aa-j-31-card-execution"
        / "scripts"
    )
    monkeypatch.syspath_prepend(str(scripts_dir))
    spec = importlib.util.spec_from_file_location(
        "aa_j_31_step_wrapper_contract",
        scripts_dir / "aa_j_31_step_wrapper.py",
    )
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)

    assert module._card_title("Entrega X") == "[Entrega X]"
    checklist = module._checklist(["mapear", "implementar", "validar"], completed_step=1, evidence="ok")
    assert "- [x] Passo 1 de 3: mapear" in checklist
    assert "- [ ] Passo 2 de 3: implementar" in checklist
    assert "Evidências:" in checklist

    parser = module.build_parser()
    args = parser.parse_args([
        "materialize",
        "--stage-name",
        "Entrega X",
        "--steps",
        "mapear",
        "implementar",
        "validar",
    ])
    assert args.project_code == "AA.ENGINEERING.CURRENT"


def test_transition_groups_step_cards_into_single_delivery():
    from scripts import transition_aa_j1_to_aa_j2 as transition

    first = SimpleNamespace(what="[Entrega Financeiro - Passo 1 de 3]")
    second = SimpleNamespace(what="[Entrega Financeiro - Passo 2 de 3]")

    assert transition._group_key(first) == transition._group_key(second)
    assert transition._delivery_title([first, second]) == "[Entrega Financeiro]"
