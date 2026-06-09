from pathlib import Path
from types import SimpleNamespace
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from api.routes import contracts as contracts_route


def test_contracts_list_tab_registry_removes_financeiro():
    keys = [item["key"] for item in contracts_route.CONTRACTS_LIST_TABS]

    assert "financeiro" not in keys
    assert keys == ["geral", "itens_valores", "faturamento", "fiscal", "observacoes"]


def test_contracts_list_legacy_financeiro_links_redirect_to_faturamento():
    assert contracts_route._normalize_contracts_list_tab("financeiro") == "faturamento"
    assert contracts_route._normalize_contracts_list_tab("dados_financeiro") == "faturamento"
    assert contracts_route._normalize_contracts_list_tab("cobranca") == "faturamento"


def test_contracts_list_template_no_longer_renders_financeiro_panel():
    template = (
        Path(__file__).resolve().parents[1]
        / "templates"
        / "modules"
        / "contracts"
        / "contracts_list.html"
    ).read_text(encoding="utf-8")

    assert "{% elif active_list_tab == 'financeiro' %}" not in template
    assert "<h2>Dados para Financeiro</h2>" not in template


def test_contracts_list_template_exposes_activate_contract_action_in_general_footer():
    template = (
        Path(__file__).resolve().parents[1]
        / "templates"
        / "modules"
        / "contracts"
        / "contracts_list.html"
    ).read_text(encoding="utf-8")

    assert 'value="activate_contract"' in template
    assert "Colocar em produção" in template


def test_contracts_list_detail_context_does_not_load_contract_financial_terms(monkeypatch):
    company = SimpleNamespace(id=9)
    contract = SimpleNamespace(
        id=56,
        company_id=9,
        due_rule="invoice:10",
        party=SimpleNamespace(id=3, code="CLI.003", name="Cliente legado"),
    )

    class _ForbiddenQuery:
        def filter_by(self, **kwargs):
            raise AssertionError("A tela simplificada não deve consultar ContractFinancialTerm.")

    monkeypatch.setattr(contracts_route, "ContractFinancialTerm", SimpleNamespace(query=_ForbiddenQuery()))
    monkeypatch.setattr(
        contracts_route,
        "ContractFiscalTerm",
        SimpleNamespace(query=SimpleNamespace(filter_by=lambda **kwargs: SimpleNamespace(first=lambda: "fiscal-terms"))),
    )
    monkeypatch.setattr(contracts_route.ContractService, "list_financial_references", lambda company_id: {"chart_accounts": []})
    monkeypatch.setattr(contracts_route.ContractService, "list_customer_parties", lambda company_id: [])
    monkeypatch.setattr(contracts_route.ContractService, "get_contract_operational_profile", lambda contract: "full")
    monkeypatch.setattr(
        contracts_route.ContractService,
        "parse_due_rule",
        lambda due_rule: {"reference": "invoice", "day": "10", "label": "10", "is_structured": True},
    )
    monkeypatch.setattr(contracts_route.ContractService, "list_contracting_legal_entities", lambda company_id: ["pj-1"])
    monkeypatch.setattr(contracts_route.ContractsCatalogService, "list_selectable_items", lambda company_id: ["item-1"])

    context = contracts_route._build_contracts_list_detail_context(company, contract)

    assert "financial_terms" not in context
    assert "contract_financial_titles" not in context
    assert context["fiscal_terms"] == "fiscal-terms"
    assert context["contract_catalog_items"] == ["item-1"]
    assert context["contracting_legal_entities"] == ["pj-1"]
    assert context["parties"][0].id == 3
