import os
import sys
from datetime import date

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import services.financial_budget_service as budget_service_module
import services.financial_budget_version_clone_service as clone_module
import services.financial_budget_workspace_service as workspace_module
from models.financial_budget import FinancialBudgetContract, FinancialBudgetLine, FinancialBudgetVersion
from services.financial_budget_service import FinancialBudgetService
from services.financial_budget_version_clone_service import FinancialBudgetVersionCloneService
from services.financial_budget_workspace_service import FinancialBudgetWorkspaceService


class _SimpleObj:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

    def to_dict(self):
        return dict(self.__dict__)


class _Column:
    def __eq__(self, other):
        return ("eq", other)

    def is_(self, other):
        return ("is", other)

    def asc(self):
        return self


class _QueryStub:
    def __init__(self, result=None, items=None):
        self.result = result
        self.items = items or []
        self.filters = []

    def filter(self, *args, **kwargs):
        self.filters.append((args, kwargs))
        return self

    def order_by(self, *args, **kwargs):
        return self

    def first(self):
        return self.result

    def all(self):
        return self.items


class _FirstSequenceQuery(_QueryStub):
    def __init__(self, first_results=None, items=None):
        super().__init__(result=None, items=items)
        self.first_results = list(first_results or [])

    def first(self):
        if self.first_results:
            return self.first_results.pop(0)
        return None


def test_budget_entities_to_dict_include_responsible_employee():
    employee = _SimpleObj(id=77, name="Ana Responsável")

    version = FinancialBudgetVersion(
        company_id=9,
        code="AA.O.1",
        name="CAPEX 2026",
        scenario_type="original",
        status="draft",
        period_start=date(2026, 1, 1),
        period_end=date(2026, 12, 31),
        responsible_employee_id=77,
    )
    version.responsible_employee = employee

    line = FinancialBudgetLine(
        company_id=9,
        budget_version_id=1,
        line_code="AA.O.1.1",
        line_name="Verba 01",
        budget_view="competence",
        movement_nature="debit",
        planned_amount=1000,
        responsible_employee_id=77,
    )
    line.responsible_employee = employee

    contract = FinancialBudgetContract(
        company_id=9,
        budget_line_id=1,
        contract_code="AA.O.1.1.1",
        name="Contrato 01",
        status="draft",
        contract_amount=500,
        responsible_employee_id=77,
    )
    contract.responsible_employee = employee

    assert version.to_dict()["responsible_employee_id"] == 77
    assert version.to_dict()["responsible_employee_name"] == "Ana Responsável"
    assert line.to_dict()["responsible_employee_id"] == 77
    assert line.to_dict()["responsible_employee_name"] == "Ana Responsável"
    assert contract.to_dict()["responsible_employee_id"] == 77
    assert contract.to_dict()["responsible_employee_name"] == "Ana Responsável"


def test_create_version_rejects_responsible_employee_outside_company(monkeypatch):
    class _BudgetVersionStub:
        query = _QueryStub(result=None)
        company_id = _Column()
        code = _Column()
        deleted_at = _Column()

        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)

        def to_dict(self):
            return dict(self.__dict__)

    monkeypatch.setattr(budget_service_module, "FinancialBudgetVersion", _BudgetVersionStub)
    monkeypatch.setattr(budget_service_module.FinancialBudgetService, "_next_budget_sequence", lambda company_id: 9)
    monkeypatch.setattr(budget_service_module.FinancialService, "_ensure_company_scope", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        budget_service_module.FinancialCatalogService,
        "validate_reference_ids",
        lambda **kwargs: "Colaborador responsável não encontrado no escopo da empresa.",
    )

    result, error = FinancialBudgetService.create_version(
        payload={
            "company_id": 9,
            "code": "AA.O.9",
            "name": "Budget com responsável inválido",
            "scenario_type": "original",
            "status": "draft",
            "period_start": date(2026, 1, 1),
            "period_end": date(2026, 12, 31),
            "responsible_employee_id": 999,
        },
        allowed_company_ids=[9],
    )

    assert result is None
    assert error == "Colaborador responsável não encontrado no escopo da empresa."


def test_budget_service_list_options_includes_company_employees(monkeypatch):
    chart_query = _QueryStub(
        items=[
            _SimpleObj(
                id=1,
                name="Receita",
                code="1.1.01",
                parent_id=None,
                movement_nature="credit",
                accepts_posting=True,
                is_active=True,
            )
        ]
    )
    center_query = _QueryStub(
        items=[
            _SimpleObj(
                id=2,
                name="Operações",
                code="CC01",
                parent_id=None,
                accepts_posting=True,
                is_active=True,
            )
        ]
    )
    employee_query = _QueryStub(items=[_SimpleObj(id=7, name="Ana", email="ana@versus.com", department="Financeiro", status="active")])

    monkeypatch.setattr(budget_service_module.FinancialService, "_ensure_company_scope", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        budget_service_module,
        "FinancialChartAccount",
        type("ChartAccountStub", (), {"query": chart_query, "company_id": _Column(), "deleted_at": _Column(), "is_active": _Column(), "name": _Column()}),
    )
    monkeypatch.setattr(
        budget_service_module,
        "FinancialCostCenter",
        type("CostCenterStub", (), {"query": center_query, "company_id": _Column(), "deleted_at": _Column(), "is_active": _Column(), "name": _Column()}),
    )
    monkeypatch.setattr(
        budget_service_module,
        "Employee",
        type("EmployeeStub", (), {"query": employee_query, "company_id": _Column(), "name": _Column(), "id": _Column()}),
    )

    result, error = FinancialBudgetService.list_options(company_id=9, allowed_company_ids=[9])

    assert error is None
    assert result["chart_accounts"] == [
        {
            "id": 1,
            "name": "Receita",
            "code": "1.1.01",
            "parent_id": None,
            "movement_nature": "credit",
            "accepts_posting": True,
            "is_active": True,
        }
    ]
    assert result["cost_centers"] == [
        {
            "id": 2,
            "name": "Operações",
            "code": "CC01",
            "parent_id": None,
            "accepts_posting": True,
            "is_active": True,
        }
    ]
    assert result["employees"] == [
        {
            "id": 7,
            "name": "Ana",
            "email": "ana@versus.com",
            "department": "Financeiro",
            "status": "active",
        }
    ]


def test_create_line_validates_responsible_employee_scope(monkeypatch):
    captured = {}

    def _capture_reference(**kwargs):
        captured["reference_kwargs"] = kwargs
        return "Colaborador responsável não encontrado no escopo da empresa."

    monkeypatch.setattr(workspace_module.FinancialService, "_ensure_company_scope", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        workspace_module.FinancialBudgetWorkspaceService,
        "_get_version",
        lambda **kwargs: _SimpleObj(id=1, company_id=9, budget_seq=1, code="AA.O.1"),
    )
    monkeypatch.setattr(
        workspace_module.FinancialCatalogService,
        "validate_reference_ids",
        _capture_reference,
    )

    result, error = FinancialBudgetWorkspaceService.create_line(
        payload={
            "company_id": 9,
            "budget_version_id": 1,
            "line_code": "AUTO",
            "line_name": "Verba com responsável inválido",
            "planned_amount": 100,
            "movement_nature": "debit",
            "responsible_employee_id": 333,
        },
        allowed_company_ids=[9],
    )

    assert result is None
    assert error == "Colaborador responsável não encontrado no escopo da empresa."
    assert captured["reference_kwargs"]["employee_id"] == 333


def test_update_contract_validates_responsible_employee_scope(monkeypatch):
    captured = {}
    contract = _SimpleObj(
        id=6,
        company_id=9,
        contract_code="AA.O.1.1.1",
        budget_line_id=3,
        counterparty_id=44,
        responsible_employee_id=12,
        contract_amount=1000,
        start_date=None,
        end_date=None,
    )

    def _capture_reference(**kwargs):
        captured["reference_kwargs"] = kwargs
        return "Colaborador responsável não encontrado no escopo da empresa."

    monkeypatch.setattr(workspace_module.FinancialService, "_ensure_company_scope", lambda *args, **kwargs: None)
    monkeypatch.setattr(workspace_module.FinancialBudgetWorkspaceService, "_get_contract", lambda **kwargs: contract)
    monkeypatch.setattr(
        workspace_module.FinancialCatalogService,
        "validate_reference_ids",
        _capture_reference,
    )

    result, error = FinancialBudgetWorkspaceService.update_contract(
        company_id=9,
        contract_id=6,
        payload={"responsible_employee_id": 555},
        allowed_company_ids=[9],
    )

    assert result is None
    assert error == "Colaborador responsável não encontrado no escopo da empresa."
    assert captured["reference_kwargs"]["employee_id"] == 555


def test_duplicate_version_copies_responsible_employees(monkeypatch):
    captured = {"versions": [], "lines": []}

    class _SessionStub:
        @staticmethod
        def add(obj):
            if hasattr(obj, "budget_version_id"):
                obj.id = 200 + len(captured["lines"])
                captured["lines"].append(obj)
            else:
                obj.id = 100
                captured["versions"].append(obj)

        @staticmethod
        def flush():
            return None

        @staticmethod
        def commit():
            return None

        @staticmethod
        def rollback():
            return None

    source_version = _SimpleObj(
        id=10,
        company_id=9,
        code="AA.O.1",
        name="Orçamento Base",
        scenario_type="original",
        status="draft",
        period_start=date(2026, 1, 1),
        period_end=date(2026, 12, 31),
        notes="Base",
        metadata_json={},
        responsible_employee_id=41,
    )
    source_line = _SimpleObj(
        id=20,
        company_id=9,
        budget_version_id=10,
        line_code="AA.O.1.1",
        line_name="Verba 01",
        line_order=10,
        budget_view="competence",
        movement_nature="debit",
        planned_amount=250,
        chart_account_id=None,
        cost_center_id=None,
        responsible_employee_id=42,
        activity_id=None,
        process_instance_id=None,
        routine_id=None,
        notes=None,
        is_active=True,
        metadata_json={},
    )

    version_query = _FirstSequenceQuery(first_results=[source_version, None])
    line_query = _QueryStub(items=[source_line])
    amount_query = _QueryStub(items=[])

    monkeypatch.setattr(clone_module.FinancialService, "_ensure_company_scope", lambda *args, **kwargs: None)
    monkeypatch.setattr(clone_module.db, "session", _SessionStub())
    monkeypatch.setattr(
        clone_module,
        "FinancialBudgetVersion",
        type("VersionStub", (), {"query": version_query, "id": _Column(), "company_id": _Column(), "code": _Column(), "deleted_at": _Column(), "__init__": lambda self, **kwargs: self.__dict__.update(kwargs), "to_dict": lambda self: dict(self.__dict__)}),
    )
    monkeypatch.setattr(
        clone_module,
        "FinancialBudgetLine",
        type("LineStub", (), {"query": line_query, "company_id": _Column(), "budget_version_id": _Column(), "deleted_at": _Column(), "line_order": _Column(), "id": _Column(), "__init__": lambda self, **kwargs: self.__dict__.update(kwargs)}),
    )
    monkeypatch.setattr(
        clone_module,
        "FinancialBudgetAmount",
        type("AmountStub", (), {"query": amount_query, "company_id": _Column(), "budget_line_id": _Column(), "deleted_at": _Column(), "period_month": _Column(), "id": _Column(), "__init__": lambda self, **kwargs: self.__dict__.update(kwargs)}),
    )

    result, error = FinancialBudgetVersionCloneService.duplicate_version(
        company_id=9,
        source_version_id=10,
        payload={"code": "AA.O.2", "name": "Orçamento Cópia"},
        allowed_company_ids=[9],
    )

    assert error is None
    assert result["responsible_employee_id"] == 41
    assert captured["versions"][0].responsible_employee_id == 41
    assert captured["lines"][0].responsible_employee_id == 42
