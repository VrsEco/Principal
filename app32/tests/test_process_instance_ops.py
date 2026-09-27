from __future__ import annotations

from datetime import date, timedelta

import pytest
from flask import Flask

from models import db
from models.company import Company
from models.employee import Employee
from models.process import (
    Process,
    ProcessActivityExecutionContract,
    ProcessInstance,
    ProcessInstanceExecution,
)
from models.process_artifact import (
    ProcessActivityArtifactDefinition,
    ProcessActivityArtifactExecution,
)
from src.intelligence import tools as tools_module
from src.intelligence.tooling.capabilities import infer_tool_action
from src.intelligence.tools_domains import process_instance_ops


@pytest.fixture()
def db_app():
    """Flask app com schema isolado em memória para os modelos do cohort
    `process_instances` (mesmo padrão de test_process_instance_pagination_contract.py)."""
    app = Flask(__name__)
    app.config.update(SQLALCHEMY_DATABASE_URI="sqlite://", SQLALCHEMY_TRACK_MODIFICATIONS=False, TESTING=True)
    db.init_app(app)
    with app.app_context():
        db.metadata.create_all(
            bind=db.engine,
            tables=[
                Company.__table__,
                Employee.__table__,
                Process.__table__,
                ProcessInstance.__table__,
                ProcessInstanceExecution.__table__,
                ProcessActivityExecutionContract.__table__,
                ProcessActivityArtifactDefinition.__table__,
                ProcessActivityArtifactExecution.__table__,
            ],
        )
        yield app
        db.session.remove()


def _seed_company_and_process(company_id: int, name: str):
    company = Company(id=company_id, name=f"Empresa {name}")
    process = Process(id=company_id, company_id=company_id, macro_id=1, name=f"Processo {name}")
    db.session.add_all([company, process])
    db.session.commit()
    return company, process


def _mock_active_company(monkeypatch, company_id):
    monkeypatch.setattr(process_instance_ops, "get_active_company_id", lambda: company_id)


def _mock_active_user(monkeypatch, user_id):
    monkeypatch.setattr(process_instance_ops, "get_active_user_id", lambda: user_id)


# ---------------------------------------------------------------------------
# list_open_process_instances
# ---------------------------------------------------------------------------


def test_list_open_process_instances_isolates_by_company_and_computes_overdue(db_app, monkeypatch):
    _seed_company_and_process(1, "A")
    _seed_company_and_process(2, "B")
    employee = Employee(id=10, company_id=1, name="Ana Colaboradora")
    db.session.add(employee)
    db.session.commit()

    today = date.today()
    overdue_a = ProcessInstance(
        company_id=1, process_id=1, title="Atrasada A",
        status="in_progress", due_date=today - timedelta(days=3), responsible_id=10,
    )
    pending_a = ProcessInstance(
        company_id=1, process_id=1, title="Aberta A",
        status="pending", due_date=today + timedelta(days=5),
    )
    completed_a = ProcessInstance(
        company_id=1, process_id=1, title="Concluida A",
        status="completed", due_date=today - timedelta(days=10),
    )
    overdue_b = ProcessInstance(
        company_id=2, process_id=2, title="Atrasada B",
        status="in_progress", due_date=today - timedelta(days=1),
    )
    db.session.add_all([overdue_a, pending_a, completed_a, overdue_b])
    db.session.commit()

    _mock_active_company(monkeypatch, 1)
    result = process_instance_ops.list_open_process_instances(company_id=1)

    assert result["success"] is True
    assert result["company_id"] == 1
    titles = {item["title"] for item in _augment_with_titles(result["instances"])}
    assert titles == {"Atrasada A", "Aberta A"}
    # Isolamento: nada da empresa 2 vaza para a consulta da empresa 1.
    assert all(item["id"] != overdue_b.id for item in result["instances"])

    overdue_item = next(item for item in result["instances"] if item["id"] == overdue_a.id)
    assert overdue_item["days_overdue"] == 3
    assert overdue_item["responsible_employee_id"] == 10
    assert overdue_item["responsible_name"] == "Ana Colaboradora"

    pending_item = next(item for item in result["instances"] if item["id"] == pending_a.id)
    assert pending_item["days_overdue"] == 0


def _augment_with_titles(instances):
    # Helper local para reaproveitar os títulos sem re-consultar o banco:
    # o serializer da tool não expõe `title`, então buscamos via ORM para asserts legíveis.
    from models.process import ProcessInstance as _PI

    result = []
    for item in instances:
        instance = _PI.query.get(item["id"])
        result.append({**item, "title": instance.title if instance else None})
    return result


def test_list_open_process_instances_denies_foreign_company_id(db_app, monkeypatch):
    _mock_active_company(monkeypatch, 1)

    result = process_instance_ops.list_open_process_instances(company_id=99)

    assert result["success"] is False
    assert "não pertence ao contexto" in result["error"]


def test_list_open_process_instances_includes_manual_reference_when_contract_linked(db_app, monkeypatch):
    _seed_company_and_process(1, "A")
    contract = ProcessActivityExecutionContract(
        company_id=1,
        process_id=1,
        bpmn_element_id="Activity_1",
        manual_reference_json={"feature_catalog_key": "conciliacao_bancaria"},
    )
    instance_with_manual = ProcessInstance(
        company_id=1, process_id=1, title="Com manual",
        status="pending", current_bpmn_element_id="Activity_1",
    )
    instance_without_manual = ProcessInstance(
        company_id=1, process_id=1, title="Sem manual", status="pending",
    )
    db.session.add_all([contract, instance_with_manual, instance_without_manual])
    db.session.commit()

    _mock_active_company(monkeypatch, 1)
    result = process_instance_ops.list_open_process_instances(company_id=1)

    with_manual = next(item for item in result["instances"] if item["id"] == instance_with_manual.id)
    without_manual = next(item for item in result["instances"] if item["id"] == instance_without_manual.id)

    assert with_manual["manual_reference"] == {"feature_catalog_key": "conciliacao_bancaria"}
    assert without_manual["manual_reference"] == {}


def test_list_open_process_instances_filters_by_assigned_to(db_app, monkeypatch):
    _seed_company_and_process(1, "A")
    employee = Employee(id=10, company_id=1, name="Ana")
    other_employee = Employee(id=11, company_id=1, name="Bruno")
    db.session.add_all([employee, other_employee])
    instance_ana = ProcessInstance(
        company_id=1, process_id=1, title="Da Ana", status="pending", responsible_id=10,
    )
    instance_bruno = ProcessInstance(
        company_id=1, process_id=1, title="Do Bruno", status="pending", executor_id=11,
    )
    db.session.add_all([instance_ana, instance_bruno])
    db.session.commit()

    _mock_active_company(monkeypatch, 1)
    result = process_instance_ops.list_open_process_instances(company_id=1, assigned_to=10)

    assert {item["id"] for item in result["instances"]} == {instance_ana.id}


# ---------------------------------------------------------------------------
# close_process_instance
# ---------------------------------------------------------------------------


def _seed_completed_artifact_execution(*, company_id, process_id, instance_id, execution_scope="process_instance", status="completed"):
    activity_execution = ProcessInstanceExecution(
        company_id=company_id,
        process_instance_id=instance_id,
        process_id=process_id,
        bpmn_element_id="Activity_1",
    )
    db.session.add(activity_execution)
    db.session.commit()

    definition = ProcessActivityArtifactDefinition(
        company_id=company_id,
        process_id=process_id,
        artifact_key="evidencia_encerramento",
        artifact_type="form",
        name="Evidência de encerramento",
        execution_scope=execution_scope,
    )
    db.session.add(definition)
    db.session.commit()

    artifact_execution = ProcessActivityArtifactExecution(
        company_id=company_id,
        process_instance_id=instance_id,
        activity_execution_id=activity_execution.id,
        artifact_definition_id=definition.id,
        artifact_key=definition.artifact_key,
        artifact_type=definition.artifact_type,
        artifact_version=1,
        scope_key=f"instance:{instance_id}",
        status=status,
    )
    db.session.add(artifact_execution)
    db.session.commit()
    return artifact_execution


def test_close_process_instance_refuses_without_valid_evidence(db_app, monkeypatch):
    _seed_company_and_process(1, "A")
    instance = ProcessInstance(company_id=1, process_id=1, title="A encerrar", status="in_progress")
    db.session.add(instance)
    db.session.commit()

    _mock_active_company(monkeypatch, 1)
    _mock_active_user(monkeypatch, 7)

    result = process_instance_ops.close_process_instance(company_id=1, instance_id=instance.id, evidence=999999)

    assert result["success"] is False
    assert "não fabrica evidência" in result["error"]

    db.session.expire_all()
    reloaded = ProcessInstance.query.get(instance.id)
    assert reloaded.status == "in_progress"


def test_close_process_instance_refuses_when_artifact_scope_is_activity_not_instance(db_app, monkeypatch):
    _seed_company_and_process(1, "A")
    instance = ProcessInstance(company_id=1, process_id=1, title="A encerrar", status="in_progress")
    db.session.add(instance)
    db.session.commit()

    artifact_execution = _seed_completed_artifact_execution(
        company_id=1, process_id=1, instance_id=instance.id, execution_scope="activity",
    )

    _mock_active_company(monkeypatch, 1)
    result = process_instance_ops.close_process_instance(
        company_id=1, instance_id=instance.id, evidence=artifact_execution.id,
    )

    assert result["success"] is False
    assert "não fabrica evidência" in result["error"]


def test_close_process_instance_succeeds_with_valid_completed_evidence(db_app, monkeypatch):
    _seed_company_and_process(1, "A")
    instance = ProcessInstance(company_id=1, process_id=1, title="A encerrar", status="in_progress")
    db.session.add(instance)
    db.session.commit()

    artifact_execution = _seed_completed_artifact_execution(
        company_id=1, process_id=1, instance_id=instance.id,
    )

    _mock_active_company(monkeypatch, 1)
    _mock_active_user(monkeypatch, 7)

    result = process_instance_ops.close_process_instance(
        company_id=1, instance_id=instance.id, evidence=artifact_execution.id,
    )

    assert result["success"] is True
    assert result["status"] == "completed"
    assert result["evidence_artifact_execution_id"] == artifact_execution.id

    db.session.expire_all()
    reloaded = ProcessInstance.query.get(instance.id)
    assert reloaded.status == "completed"
    assert reloaded.actual_end_date == date.today()
    assert "close_process_instance" in (reloaded.notes or "")


def test_close_process_instance_denies_cross_tenant_instance_and_evidence(db_app, monkeypatch):
    _seed_company_and_process(1, "A")
    _seed_company_and_process(2, "B")
    instance_company_b = ProcessInstance(company_id=2, process_id=2, title="Da empresa B", status="in_progress")
    db.session.add(instance_company_b)
    db.session.commit()

    artifact_execution_b = _seed_completed_artifact_execution(
        company_id=2, process_id=2, instance_id=instance_company_b.id,
    )

    # Empresa ativa é 1: nunca deve encontrar/encerrar instância da empresa 2,
    # mesmo com evidence válido *dentro* da empresa 2 (company_id+id sempre juntos).
    _mock_active_company(monkeypatch, 1)
    result = process_instance_ops.close_process_instance(
        company_id=1, instance_id=instance_company_b.id, evidence=artifact_execution_b.id,
    )

    assert result["success"] is False
    assert "não encontrada nesta empresa" in result["error"]

    db.session.expire_all()
    reloaded = ProcessInstance.query.get(instance_company_b.id)
    assert reloaded.status == "in_progress"


def test_close_process_instance_rejects_invalid_closure_status(db_app, monkeypatch):
    _seed_company_and_process(1, "A")
    instance = ProcessInstance(company_id=1, process_id=1, title="A encerrar", status="in_progress")
    db.session.add(instance)
    db.session.commit()

    _mock_active_company(monkeypatch, 1)
    result = process_instance_ops.close_process_instance(
        company_id=1, instance_id=instance.id, evidence=1, closure_status="bogus",
    )

    assert result["success"] is False
    assert "closure_status inválido" in result["error"]


# ---------------------------------------------------------------------------
# Wiring: tools.py wrappers e classificação de ação (human gate)
# ---------------------------------------------------------------------------


def test_tools_wrappers_delegate_to_process_instance_domain(monkeypatch):
    calls = []
    monkeypatch.setattr(
        tools_module.process_instance_ops_domain,
        "list_open_process_instances",
        lambda **kwargs: calls.append(("list", kwargs)) or {"success": True},
    )
    monkeypatch.setattr(
        tools_module.process_instance_ops_domain,
        "close_process_instance",
        lambda **kwargs: calls.append(("close", kwargs)) or {"success": True},
    )

    assert tools_module.list_open_process_instances.func(company_id=1) == {"success": True}
    assert tools_module.close_process_instance.func(instance_id=5, evidence=9, company_id=1) == {"success": True}

    assert calls == [
        ("list", {"company_id": 1, "status": None, "due_before": None, "assigned_to": None}),
        ("close", {"company_id": 1, "instance_id": 5, "evidence": 9, "closure_status": "completed"}),
    ]


def test_close_process_instance_action_is_classified_as_mutating_for_human_gate():
    """Regressão: sem mapear o prefixo `close_`, `infer_tool_action` retorna None e o
    gate de alto risco em `evaluate_tool_policy` (action in MUTATING_ACTIONS) nunca
    dispara, abrindo um bypass silencioso do human_gate. Deve classificar como `update`,
    no mesmo grupo semântico de `complete_`/`finish_`."""
    from src.intelligence.security.tool_policy import MUTATING_ACTIONS

    action = infer_tool_action("close_process_instance", "processes")
    assert action == "update"
    assert action in MUTATING_ACTIONS
