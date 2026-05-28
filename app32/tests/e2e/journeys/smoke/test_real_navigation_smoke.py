from __future__ import annotations

import pytest

from app32.tests.e2e.config.environments import E2EEnvironmentSettings
from app32.tests.e2e.config.smoke_targets import SMOKE_TARGETS
from app32.tests.e2e.core.auth import AuthPage
from app32.tests.e2e.core.navigation import NavigationSmoke
from app32.tests.e2e.data.run_context import RunContext


@pytest.mark.e2e
@pytest.mark.smoke
def test_real_navigation_smoke(
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
    navigator = NavigationSmoke(page)
    journey = e2e_run_context.reporter.start_journey(
        journey="smoke_real_navigation",
        run_id=e2e_run_context.evidence.run_id,
        company_id=e2e_settings.company_id,
        user_label=e2e_settings.username,
        metadata={"targets": [t.key for t in SMOKE_TARGETS[1:]]},
    )

    e2e_run_context.reporter.add_event("real_navigation_smoke_started", targets=[t.key for t in SMOKE_TARGETS[1:]])
    journey.step("authenticate", status="running")
    auth_page.open()
    auth_page.login()
    auth_page.ensure_authenticated_workspace()
    journey.step("authenticate", status="passed", details={"url": page.url})

    for target in SMOKE_TARGETS[1:]:
        journey.step(target.key, status="running", details={"route": target.route})
        navigator.open_target(target)
        shot = e2e_run_context.reporter.capture_screenshot(
            page,
            label=f"smoke-{target.key}",
            file_name=f"{e2e_run_context.evidence.run_id}_{target.key.replace('.', '_')}.png",
        )
        journey.attach_artifact(
            artifact_type="screenshot",
            path=shot,
            label=f"smoke-{target.key}",
            metadata={"target": target.key, "url": page.url},
        )
        e2e_run_context.reporter.add_event(
            "real_navigation_target_ok",
            key=target.key,
            url=page.url,
        )
        journey.step(target.key, status="passed", details={"url": page.url})

    e2e_run_context.reporter.add_event("real_navigation_smoke_finished", final_url=page.url)
    journey.succeed()
