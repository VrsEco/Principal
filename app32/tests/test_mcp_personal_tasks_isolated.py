"""Contract tests without importing Flask, schedulers or database connections."""
import ast
import os
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from sqlalchemy import column, func
from sqlalchemy.dialects import postgresql


@pytest.fixture
def service(monkeypatch):
    path = Path(__file__).parents[1] / "services/project_task_mcp_service.py"
    tree = ast.parse(path.read_text(encoding="utf-8-sig"))
    helper = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_coerce_positive_int")
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef))
    cls.body = [n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == "list_tasks"]
    namespace = {"Any": object, "os": os, "func": func}
    exec(compile(ast.Module(body=[helper, cls], type_ignores=[]), str(path), "exec"), namespace)
    query = Mock()
    query.filter.return_value = query
    query.order_by.return_value = query
    query.limit.return_value = query
    query.all.return_value = []
    employee_query = Mock()
    employee_query.filter.return_value = employee_query
    employee_query.one_or_none.return_value = SimpleNamespace(id=73)
    employee = SimpleNamespace(query=employee_query, user_id=column("user_id"),
        company_id=column("company_id"), status=column("employee_status"))
    monkeypatch.setitem(sys.modules, "models.employee", SimpleNamespace(Employee=employee))
    namespace["ProjectTask"] = SimpleNamespace(**{n: column(n) for n in
        ("employee_id", "project_id", "status", "stage", "completion_date", "updated_at", "id")})
    service = namespace["ProjectTaskMCPService"]
    service._base_query = Mock(return_value=query)
    return service, query, employee_query


def sql(expressions):
    return " ".join(str(e.compile(dialect=postgresql.dialect(),
        compile_kwargs={"literal_binds": True})) for e in expressions)


def test_mine_filters_by_authenticated_employee_before_limit(service):
    api, query, employees = service
    result, error = api.list_tasks(company_id=8, mine_only=True, open_only=True, actor_user_id=32)
    assert not error and result["employee_id"] == 73
    assert result["mine_only"] and result["open_only"]
    api._base_query.assert_called_once_with(company_id=8, include_deleted=False)
    employee_sql = sql(employees.filter.call_args.args)
    assert "user_id = 32" in employee_sql and "company_id = 8" in employee_sql
    filters = sql([e for call in query.filter.call_args_list for e in call.args])
    assert "employee_id = 73" in filters and "who" not in filters
    assert "completed" in filters and "cancelled" in filters
    assert "completion_date IS NULL" in filters


@pytest.mark.parametrize("actor", [None, 0])
def test_missing_identity_never_lists_company_tasks(service, actor):
    api, query, employees = service
    result, error = api.list_tasks(company_id=8, mine_only=True, actor_user_id=actor)
    assert error and result == {}
    query.all.assert_not_called()
    employees.filter.assert_not_called()


def test_missing_employee_never_falls_back_to_name_or_company(service):
    api, query, employees = service
    employees.one_or_none.return_value = None
    result, error = api.list_tasks(company_id=8, mine_only=True, actor_user_id=32)
    assert error and result == {}
    query.all.assert_not_called()


def test_legacy_listing_remains_explicitly_company_wide(service):
    api, query, employees = service
    result, error = api.list_tasks(company_id=8)
    assert not error and not result["mine_only"] and result["employee_id"] is None
    employees.filter.assert_not_called()
