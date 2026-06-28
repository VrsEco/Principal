from __future__ import annotations

from app32.tests.e2e.catalog.ui_safe_contract_executor import _resolve_contract_route, _safe_contracts, _selector_present


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
    assert all(not item["requires_human_gate"] for item in contracts)


def test_resolve_contract_route_replaces_company_id_and_skips_invalid_contexts():
    assert _resolve_contract_route("/companies/<company_id>/edit", company_id=10) == ("/companies/10/edit", None)
    assert _resolve_contract_route("/auth/login", company_id=10)[1] == "public_auth_route_requires_unauthenticated_context"
    assert _resolve_contract_route("/projects/<project_id>/edit", company_id=10)[1] == "dynamic_route_requires_fixture_resolution"
