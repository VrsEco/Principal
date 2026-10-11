import inspect

import pytest

from src.core.mcp_financial_tools import _bound_payload, register_financial_mcp_tools

TOOLS = """create_financial_automation_rule create_financial_bordero create_financial_bordero_settlement
create_financial_budget_contract create_financial_budget_document create_financial_budget_line
create_financial_budget_version create_financial_catalog_item create_financial_classification_rule
create_financial_closing create_financial_direct_entry create_financial_import_batch
create_financial_ingestion_record create_financial_schedule replace_financial_allocations
upsert_financial_budget_matrix upsert_financial_domain_enablement""".split()


class _FakeMcp:
    def __init__(self):
        self.tools = {}

    def tool(self, *args, **kwargs):
        def register(fn):
            self.tools[fn.__name__] = fn
            return fn

        return register


@pytest.fixture(scope="module")
def tools():
    fake = _FakeMcp()
    register_financial_mcp_tools(fake)
    return fake.tools


@pytest.mark.parametrize("name", TOOLS)
def test_financial_write_tool_has_first_level_company_id(tools, name):
    params = list(inspect.signature(tools[name]).parameters)
    assert params[0] == "company_id", name


@pytest.mark.parametrize("name", TOOLS)
def test_financial_write_tool_rejects_invalid_company_before_any_service(tools, name):
    fn = tools[name]
    kwargs = {p: ("x" if p != "payload" else {}) for p in inspect.signature(fn).parameters}
    kwargs["company_id"] = 0
    result = fn(**kwargs)
    assert result["success"] is False and "company_id" in result["error"]


def test_bound_payload_sets_tenant_and_rejects_divergence():
    bound, error = _bound_payload(7, {"x": 1})
    assert error is None and bound == {"x": 1, "company_id": 7}
    assert _bound_payload(7, {"company_id": "7"})[1] is None
    assert "diverge" in _bound_payload(7, {"company_id": 8})[1]["error"]
    assert "inválido" in _bound_payload(7, {"company_id": "abc"})[1]["error"]
    assert _bound_payload(True, {})[1] is not None
