from pathlib import Path
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
