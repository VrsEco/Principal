from __future__ import annotations

from app32.tests.e2e.config.environments import E2EEnvironmentSettings, E2EExecutionMode


def validate_execution_contract(settings: E2EEnvironmentSettings) -> None:
    settings.validate_or_raise()
    if settings.execution_mode is E2EExecutionMode.PROD_SAFE:
        if settings.post_login_path not in {"/my-work", "/portal"}:
            raise ValueError(
                "PROD_SAFE exige post_login_path controlado (/my-work ou /portal)."
            )
