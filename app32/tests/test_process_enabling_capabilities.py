from pathlib import Path
from types import SimpleNamespace
import sys

import pytest

APP_ROOT = Path(__file__).resolve().parents[1]
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from models import ProcessExecutionPlan
from services import process_resource_service as service


ROOT = APP_ROOT


class _SessionStub:
    def __init__(self):
        self.added = []
        self.commits = 0

    def add(self, item):
        self.added.append(item)

    def commit(self):
        self.commits += 1

    def flush(self):
        pass


def test_create_resource_uses_short_name_and_tenant_dimension(monkeypatch):
    session = _SessionStub()
    dimension = SimpleNamespace(id=17, name="Pessoas, Papéis e Competências")
    monkeypatch.setattr(service.db, "session", session)
    monkeypatch.setattr(service, "_resolve_capability_dimension", lambda company_id, payload: dimension)
    monkeypatch.setattr(service, "_legacy_type_for_dimension", lambda dimension, payload: "people")

    capability = service.create_resource(
        9,
        {
            "dimension_id": 17,
            "name": "Analista Fiscal",
        },
    )

    assert capability.company_id == 9
    assert capability.dimension_id == 17
    assert capability.item_name == "Analista Fiscal"
    assert capability.subtype == "Pessoas, Papéis e Competências"
    assert capability.type == "people"
    assert session.added == [capability]
    assert session.commits == 1


def test_process_capability_link_records_condition_criticality_and_gap(monkeypatch):
    session = _SessionStub()
    capability = SimpleNamespace(id=31, is_active=True, unit_value=None, operational_capacity_value=None, quantity=None)
    monkeypatch.setattr(service.db, "session", session)
    monkeypatch.setattr(service, "_get_process_for_company", lambda company_id, process_id: SimpleNamespace(id=process_id, macro_id=4))
    monkeypatch.setattr(service, "_get_resource_for_company", lambda company_id, resource_id: capability)
    monkeypatch.setattr(service, "_validate_process_routine", lambda *args: None)
    monkeypatch.setattr(service, "get_process_execution_plan", lambda *args: None)

    link = service.create_process_resource_link(
        9,
        545,
        {
            "resource_id": 31,
            "required_condition": "Licença ativa e parametrizada",
            "criticality": "critical",
            "gap_notes": "Integração contábil pendente",
        },
    )

    assert link.company_id == 9
    assert link.process_id == 545
    assert link.resource_id == 31
    assert link.required_condition == "Licença ativa e parametrizada"
    assert link.criticality == "critical"
    assert link.gap_notes == "Integração contábil pendente"


def test_invalid_capability_criticality_is_rejected():
    with pytest.raises(service.ProcessResourceValidationError, match="criticidade"):
        service._criticality_or_none("urgent")


def test_canonical_routes_and_legacy_aliases_coexist():
    app_source = (ROOT / "app.py").read_text(encoding="utf-8")
    assert "'/api/enabling-dimensions'" in app_source
    assert "'/api/enabling-resources'" in app_source
    assert "'/api/processes/<int:process_id>/capabilities'" in app_source
    assert "'/api/resources'" in app_source
    assert "'/api/processes/<int:process_id>/resources'" in app_source


def test_execution_plan_normalizes_frequency_to_month():
    plan = ProcessExecutionPlan(frequency_count=15, frequency_period="day", working_days_per_month=22)
    assert plan.monthly_instances() == 330


def test_planned_utilization_can_expose_overload():
    resource = SimpleNamespace(operational_capacity_value=100, operational_capacity_period="month", quantity=None, unit_value=None)
    metrics = service._calculate_link_usage_metrics(
        resource,
        {"used_quantity_per_execution": 2, "estimated_monthly_instances": 100},
    )
    assert float(metrics["usage_percentage"]) == 200


def test_ui_separates_dimensions_resources_and_execution_plan():
    architecture = (ROOT / "templates/modules/processes/process_map_v2.html").read_text(encoding="utf-8")
    process_detail = (ROOT / "templates/modules/processes/process_details_v2.html").read_text(encoding="utf-8")
    assert "Dimensões e Recursos Habilitadores" in architecture
    assert "formCapabilityDimension" in architecture
    assert "enablingDimensionsFormSection" in architecture
    assert "enablingResourcesFormSection" in architecture
    assert "Catálogo corporativo" in architecture or "catálogo corporativo" in architecture
    assert "enablingResourceMacroId" not in architecture
    assert "Recursos Habilitadores do Processo" in process_detail
    assert "processExecutionPlanForm" in process_detail
    assert "Condição requerida" in process_detail
    assert "Criticidade" in process_detail
    assert "resource-capacity-card__summary" in process_detail
    assert "resource-capacity-meter__track" in process_detail
    assert "Alocação / condição" in process_detail
    assert "Demanda do processo" in process_detail
    assert "Capacidade não informada" in process_detail


def test_process_ui_populates_resource_catalog_as_soon_as_request_finishes():
    process_detail = (ROOT / "templates/modules/processes/process_details_v2.html").read_text(encoding="utf-8")

    catalog_loader = process_detail.split("async function fetchResourceCatalog()", 1)[1].split(
        "async function fetchIndicators()", 1
    )[0]

    assert "state.process?.company_id || companyId" in catalog_loader
    assert "cache: 'no-store'" in catalog_loader
    assert "populateResourceCatalogSelect();" in catalog_loader
    assert "populateResourceCatalogSelect(e.message" in catalog_loader
    assert "Nenhum recurso habilitador ativo cadastrado" in process_detail
