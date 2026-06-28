from __future__ import annotations

from app32.tests.e2e.catalog.ui_dynamic_fixture_resolver import DynamicFixtureResolver
from app32.tests.e2e.catalog.ui_mutation_contract_executor import _mutation_contracts
from app32.tests.e2e.catalog.ui_safe_contract_executor import _resolve_contract_route, _safe_contracts, _selector_present
from app32.tests.e2e.config.environments import E2EEnvironmentSettings, E2EExecutionMode
from pathlib import Path


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



def _settings(company_id=10, user_id=3):
    return E2EEnvironmentSettings(
        environment_name="DEV_FULL",
        execution_mode=E2EExecutionMode.DEV_FULL,
        base_url="https://example.invalid",
        login_path="/login",
        post_login_path="/my-work",
        username="",
        password="",
        company_id=company_id,
        user_id=user_id,
        headless=True,
        browser_name="chromium",
        storage_state_path=Path("/tmp/storage.json"),
        outputs_dir=Path("/tmp"),
        traces_dir=Path("/tmp/traces"),
        screenshots_dir=Path("/tmp/screenshots"),
        videos_dir=Path("/tmp/videos"),
        reports_dir=Path("/tmp/reports"),
        destructive_actions_allowed=True,
        requires_isolated_tenant=True,
        require_explicit_company=True,
    )


def test_dynamic_fixture_resolver_resolves_static_tenant_values():
    resolver = DynamicFixtureResolver(_settings(company_id=10, user_id=3))
    result = resolver.resolve_route("/companies/<company_id>/users/<user_id>")

    assert result.resolved
    assert result.resolved_route == "/companies/10/users/3"
    assert result.resolved_values == {"company_id": 10, "user_id": 3}


def test_resolve_contract_route_uses_fixture_resolver_when_available():
    resolver = DynamicFixtureResolver(_settings(company_id=10, user_id=3))

    assert _resolve_contract_route("/companies/<company_id>/edit", company_id=10, fixture_resolver=resolver) == (
        "/companies/10/edit",
        None,
    )


def test_mutation_contracts_are_cataloged_separately_from_safe_contracts():
    contracts = _mutation_contracts(50)

    assert len(contracts) <= 50
    assert contracts
    assert all(item["execution_strategy"] == "playwright_or_api_mutation_with_rollback" for item in contracts)
    assert all(item["cleanup_strategy"] == "rollback_or_delete_and_residue_zero" for item in contracts)
