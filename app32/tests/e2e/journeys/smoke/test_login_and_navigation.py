from __future__ import annotations

import pytest
from playwright.sync_api import expect

from app32.tests.e2e.config.environments import E2EEnvironmentSettings
from app32.tests.e2e.core.auth import AuthPage
from app32.tests.e2e.data.run_context import RunContext


@pytest.mark.e2e
@pytest.mark.smoke
def test_login_and_reach_workspace(
    e2e_settings: E2EEnvironmentSettings,
    e2e_run_context: RunContext,
    page_context,
):
    if e2e_settings.missing_requirements:
        pytest.skip(
            "Configuração E2E incompleta. Defina: "
            + ", ".join(e2e_settings.missing_requirements)
        )

    _, _, _, page = page_context
    auth_page = AuthPage(page, e2e_settings)
    journey = e2e_run_context.reporter.start_journey(
        journey="smoke_login_and_workspace",
        run_id=e2e_run_context.evidence.run_id,
        company_id=e2e_settings.company_id,
        user_label=e2e_settings.username,
        metadata={"mode": e2e_settings.environment_name},
    )
    e2e_run_context.reporter.add_event("smoke_started", scenario="login_and_reach_workspace")
    journey.step("open_login", status="running")

    auth_page.open()
    journey.step("open_login", status="passed", details={"url": page.url})
    journey.step("submit_login", status="running")
    auth_page.login()
    journey.step("submit_login", status="passed")
    journey.step("resolve_workspace", status="running")
    auth_page.ensure_authenticated_workspace()

    page.wait_for_load_state("domcontentloaded")
    current_url = page.url
    assert any(
        token in current_url for token in ("/my-work", "/portal", e2e_settings.post_login_path)
    ), f"Login não chegou ao workspace esperado. URL atual: {current_url}"
    journey.step("resolve_workspace", status="passed", details={"final_url": current_url})

    screenshot_path = e2e_run_context.reporter.capture_screenshot(
        page,
        label="workspace-after-login",
        file_name=f"{e2e_run_context.evidence.run_id}_login_workspace.png",
    )
    journey.attach_artifact(
        artifact_type="screenshot",
        path=screenshot_path,
        label="workspace-after-login",
        metadata={"step": "resolve_workspace"},
    )
    expect(page.locator("body")).to_be_visible()
    e2e_run_context.reporter.add_event(
        "smoke_finished",
        scenario="login_and_reach_workspace",
        final_url=current_url,
    )
    journey.succeed()
