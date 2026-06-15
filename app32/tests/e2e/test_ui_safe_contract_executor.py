from __future__ import annotations

from app32.tests.e2e.catalog.ui_safe_contract_executor import _safe_contracts, _selector_present


def test_selector_present_handles_common_selectors():
    body = """
    <html><body>
      <input id="email" name="email">
      <a href="/my-work">Meu Trabalho</a>
      <button data-testid="save-action">Salvar</button>
    </body></html>
    """

    assert _selector_present(body, "#email")
    assert _selector_present(body, "input[name='email']")
    assert _selector_present(body, "a[href='/my-work']")
    assert _selector_present(body, "[data-testid='save-action']")


def test_safe_contracts_excludes_mutation_and_high_risk_contracts():
    contracts = _safe_contracts(25)

    assert len(contracts) <= 25
    assert contracts
    assert all(item["risk_level"] == "low" for item in contracts)
    assert all(not item["requires_company_id"] for item in contracts)
    assert all(not item["requires_human_gate"] for item in contracts)
