from __future__ import annotations

import os
from dataclasses import dataclass
from enum import Enum
from pathlib import Path


def _parse_bool(value: str | None, default: bool) -> bool:
    raw = str(value or "").strip().lower()
    if not raw:
        return default
    return raw in {"1", "true", "yes", "y", "on", "sim"}


class E2EExecutionMode(str, Enum):
    DEV_FULL = "DEV_FULL"
    PROD_SAFE = "PROD_SAFE"


@dataclass(frozen=True)
class E2EEnvironmentSettings:
    environment_name: str
    execution_mode: E2EExecutionMode
    base_url: str
    login_path: str
    post_login_path: str
    username: str
    password: str
    company_id: int | None
    headless: bool
    browser_name: str
    storage_state_path: Path
    outputs_dir: Path
    traces_dir: Path
    screenshots_dir: Path
    videos_dir: Path
    reports_dir: Path
    destructive_actions_allowed: bool
    requires_isolated_tenant: bool
    require_explicit_company: bool

    @property
    def login_url(self) -> str:
        return f"{self.base_url.rstrip('/')}{self.login_path}"

    @property
    def has_credentials(self) -> bool:
        return bool(self.base_url and self.username and self.password)

    @property
    def missing_requirements(self) -> list[str]:
        missing: list[str] = []
        if not self.base_url:
            missing.append("E2E_BASE_URL")
        if not self.username:
            missing.append("E2E_USERNAME")
        if not self.password:
            missing.append("E2E_PASSWORD")
        if self.require_explicit_company and self.company_id is None:
            missing.append("E2E_COMPANY_ID")
        return missing

    def validate_or_raise(self) -> None:
        missing = self.missing_requirements
        if missing:
            raise ValueError(
                "Configuração E2E incompleta para "
                f"{self.execution_mode.value}: {', '.join(missing)}"
            )
        if self.execution_mode is E2EExecutionMode.PROD_SAFE and self.destructive_actions_allowed:
            raise ValueError("PROD_SAFE não permite destructive_actions_allowed=True.")


def _resolve_execution_mode(raw_value: str | None) -> E2EExecutionMode:
    normalized = str(raw_value or "DEV_FULL").strip().upper()
    try:
        return E2EExecutionMode(normalized)
    except ValueError:
        return E2EExecutionMode.DEV_FULL


def _default_headless(mode: E2EExecutionMode) -> bool:
    return True if mode is E2EExecutionMode.PROD_SAFE else False


def _mode_defaults(mode: E2EExecutionMode) -> dict[str, bool]:
    if mode is E2EExecutionMode.PROD_SAFE:
        return {
            "destructive_actions_allowed": False,
            "requires_isolated_tenant": True,
            "require_explicit_company": True,
        }
    return {
        "destructive_actions_allowed": True,
        "requires_isolated_tenant": True,
        "require_explicit_company": True,
    }


def load_environment_settings() -> E2EEnvironmentSettings:
    repo_root = Path(__file__).resolve().parents[4]
    execution_mode = _resolve_execution_mode(os.environ.get("E2E_ENV_NAME"))
    defaults = _mode_defaults(execution_mode)
    outputs_dir = Path(
        os.environ.get(
            "E2E_OUTPUTS_DIR",
            str(repo_root / "app32" / "tests" / "e2e" / "outputs" / execution_mode.value.lower()),
        )
    )
    traces_dir = outputs_dir / "traces"
    screenshots_dir = outputs_dir / "screenshots"
    videos_dir = outputs_dir / "videos"
    reports_dir = outputs_dir / "reports"
    storage_state_path = outputs_dir / "storage_state.json"

    company_id_raw = str(os.environ.get("E2E_COMPANY_ID") or "").strip()
    company_id = int(company_id_raw) if company_id_raw.isdigit() else None

    settings = E2EEnvironmentSettings(
        environment_name=execution_mode.value,
        execution_mode=execution_mode,
        base_url=str(os.environ.get("E2E_BASE_URL") or "").strip(),
        login_path=str(os.environ.get("E2E_LOGIN_PATH") or "/auth/login").strip() or "/auth/login",
        post_login_path=str(os.environ.get("E2E_POST_LOGIN_PATH") or "/my-work").strip() or "/my-work",
        username=str(os.environ.get("E2E_USERNAME") or "").strip(),
        password=str(os.environ.get("E2E_PASSWORD") or ""),
        company_id=company_id,
        headless=_parse_bool(os.environ.get("E2E_HEADLESS"), _default_headless(execution_mode)),
        browser_name=str(os.environ.get("E2E_BROWSER") or "chromium").strip() or "chromium",
        storage_state_path=storage_state_path,
        outputs_dir=outputs_dir,
        traces_dir=traces_dir,
        screenshots_dir=screenshots_dir,
        videos_dir=videos_dir,
        reports_dir=reports_dir,
        destructive_actions_allowed=_parse_bool(
            os.environ.get("E2E_DESTRUCTIVE_ACTIONS_ALLOWED"),
            defaults["destructive_actions_allowed"],
        ),
        requires_isolated_tenant=_parse_bool(
            os.environ.get("E2E_REQUIRES_ISOLATED_TENANT"),
            defaults["requires_isolated_tenant"],
        ),
        require_explicit_company=_parse_bool(
            os.environ.get("E2E_REQUIRE_EXPLICIT_COMPANY"),
            defaults["require_explicit_company"],
        ),
    )
    return settings
