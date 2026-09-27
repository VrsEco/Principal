import inspect
from datetime import date
from pathlib import Path

import pytest
from flask import Flask

from api.resources.process import ProcessInstanceListResource
from models import db
from models.company import Company
from models.process import Process, ProcessActivityExecutionContract, ProcessInstance


def test_process_instance_list_exposes_opt_in_pagination_without_breaking_legacy_list():
    source = inspect.getsource(ProcessInstanceListResource.get)

    assert "ProcessInstance.query.filter_by(company_id=company_id)" in source
    assert "paginated = (request.args.get('paginated') or 'false').lower() == 'true'" in source
    assert "query = query.filter(ProcessInstance.status == status)" in source
    assert "ProcessInstance.instance_code.ilike(pattern)" in source
    assert "per_page = min(max(request.args.get('per_page', 50, type=int) or 50, 1), 100)" in source
    assert "query.offset((page - 1) * per_page).limit(per_page).all()" in source
    assert "'pagination': {'page': page" in source
    assert "return results, 200" in source


def test_process_instances_page_uses_server_filters_and_incremental_rendering():
    root = Path(__file__).resolve().parents[1]
    template = (root / "templates" / "modules" / "processes" / "process_instances_list.html").read_text(encoding="utf-8")

    assert "paginated: 'true'" in template
    assert "params.set(['status', 'priority', 'process_id'][index], value)" in template
    assert "params.set('search', search)" in template
    assert "loadInstances({ append: true })" in template
    assert "Carregar mais (${allInstances.length} de ${instancesPagination.total})" in template


@pytest.fixture()
def db_app():
    """Flask app context with an isolated in-memory schema for the process
    instance / activity execution contract models used by the migration
    20260927_1000_add_activity_manual_reference_and_open_instance_index."""
    app = Flask(__name__)
    app.config.update(SQLALCHEMY_DATABASE_URI="sqlite://", SQLALCHEMY_TRACK_MODIFICATIONS=False, TESTING=True)
    db.init_app(app)
    with app.app_context():
        db.metadata.create_all(bind=db.engine, tables=[
            Company.__table__,
            Process.__table__,
            ProcessInstance.__table__,
            ProcessActivityExecutionContract.__table__,
        ])
        yield app
        db.session.remove()


def _seed_company_and_process(company_id, name):
    company = Company(id=company_id, name=f"Empresa {name}")
    process = Process(id=company_id, company_id=company_id, macro_id=1, name=f"Processo {name}")
    db.session.add_all([company, process])
    db.session.commit()
    return company, process


def test_activity_execution_contract_manual_reference_json_round_trip(db_app):
    _seed_company_and_process(1, "A")

    manual_reference = {
        "feature_catalog_key": "conciliacao_bancaria",
        "domain_playbook_key": "financeiro.conciliacao",
        "version": 1,
    }
    contract = ProcessActivityExecutionContract(
        company_id=1,
        process_id=1,
        bpmn_element_id="Activity_1",
        manual_reference_json=manual_reference,
    )
    db.session.add(contract)
    db.session.commit()
    contract_id = contract.id

    db.session.expire_all()
    reloaded = ProcessActivityExecutionContract.query.get(contract_id)

    assert reloaded.manual_reference_json == manual_reference
    assert reloaded.to_dict()["manual_reference_json"] == manual_reference


def test_activity_execution_contract_manual_reference_json_defaults_to_empty_dict(db_app):
    _seed_company_and_process(1, "A")

    contract = ProcessActivityExecutionContract(company_id=1, process_id=1)
    db.session.add(contract)
    db.session.commit()
    contract_id = contract.id

    db.session.expire_all()
    reloaded = ProcessActivityExecutionContract.query.get(contract_id)

    assert reloaded.manual_reference_json == {}
    assert reloaded.to_dict()["manual_reference_json"] == {}


def test_open_overdue_process_instances_query_filters_by_tenant_status_and_due_date(db_app):
    _seed_company_and_process(1, "A")
    _seed_company_and_process(2, "B")

    today = date(2026, 9, 27)
    open_statuses = ("pending", "in_progress", "paused", "waiting_external")

    overdue_company_a = ProcessInstance(
        company_id=1, process_id=1, title="Instancia atrasada A",
        status="in_progress", due_date=date(2026, 9, 1),
    )
    open_not_overdue_company_a = ProcessInstance(
        company_id=1, process_id=1, title="Instancia aberta A",
        status="pending", due_date=date(2026, 10, 1),
    )
    completed_company_a = ProcessInstance(
        company_id=1, process_id=1, title="Instancia concluida A",
        status="completed", due_date=date(2026, 9, 1),
    )
    overdue_company_b = ProcessInstance(
        company_id=2, process_id=2, title="Instancia atrasada B",
        status="in_progress", due_date=date(2026, 9, 1),
    )
    db.session.add_all([
        overdue_company_a, open_not_overdue_company_a, completed_company_a, overdue_company_b,
    ])
    db.session.commit()

    results = (
        ProcessInstance.query
        .filter(ProcessInstance.company_id == 1)
        .filter(ProcessInstance.status.in_(open_statuses))
        .filter(ProcessInstance.due_date <= today)
        .order_by(ProcessInstance.due_date.asc())
        .all()
    )

    assert [instance.title for instance in results] == ["Instancia atrasada A"]
    assert all(instance.company_id == 1 for instance in results)

    # A mesma consulta na empresa B so deve enxergar dados da empresa B (isolamento por tenant).
    results_company_b = (
        ProcessInstance.query
        .filter(ProcessInstance.company_id == 2)
        .filter(ProcessInstance.status.in_(open_statuses))
        .filter(ProcessInstance.due_date <= today)
        .all()
    )

    assert [instance.title for instance in results_company_b] == ["Instancia atrasada B"]