from __future__ import annotations

from contextlib import contextmanager
import json
from pathlib import Path
from typing import Iterator

from playwright.sync_api import Browser, BrowserContext, Page, Playwright, sync_playwright

from app32.tests.e2e.config.environments import E2EEnvironmentSettings, E2EExecutionMode
from app32.tests.e2e.core.evidence import EvidenceCollector, EvidencePaths
from app32.tests.e2e.core.prod_safe_session_bootstrap import bootstrap_remote_prod_safe_storage_state


def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _has_auth_cookie(storage_state: dict) -> bool:
    for cookie in storage_state.get("cookies", []) or []:
        if str(cookie.get("name") or "").strip() == "gv_session" and str(cookie.get("value") or "").strip():
            return True
    return False


def _storage_state_has_auth_cookie(path: Path) -> bool:
    try:
        return _has_auth_cookie(json.loads(path.read_text(encoding="utf-8")))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return False


@contextmanager
def managed_page(
    settings: E2EEnvironmentSettings,
    evidence: EvidencePaths,
    collector: EvidenceCollector,
    *,
    use_storage_state: bool = True,
) -> Iterator[tuple[Playwright, Browser, BrowserContext, Page]]:
    must_bootstrap = use_storage_state and (
        not settings.storage_state_path.exists()
        or (
            settings.execution_mode is E2EExecutionMode.PROD_SAFE
            and not _storage_state_has_auth_cookie(settings.storage_state_path)
        )
    )
    if must_bootstrap:
        try:
            bootstrap_remote_prod_safe_storage_state(settings)
        except Exception:
            pass

    playwright = sync_playwright().start()
    browser_launcher = getattr(playwright, settings.browser_name)
    browser = browser_launcher.launch(headless=settings.headless)

    video_dir = evidence.videos_dir
    video_dir.mkdir(parents=True, exist_ok=True)
    context = browser.new_context(
        base_url=settings.base_url or None,
        ignore_https_errors=True,
        record_video_dir=str(video_dir),
        storage_state=(
            str(settings.storage_state_path)
            if use_storage_state and settings.storage_state_path.exists()
            else None
        ),
        viewport={"width": 1440, "height": 960},
    )
    context.tracing.start(screenshots=True, snapshots=True, sources=True)
    page = context.new_page()
    setattr(page, "_e2e_settings", settings)

    try:
        yield playwright, browser, context, page
    finally:
        trace_path = evidence.traces_dir / f"{evidence.run_id}.zip"
        _ensure_parent(trace_path)
        context.tracing.stop(path=str(trace_path))
        collector.register_artifact(
            artifact_type="trace",
            path=trace_path,
            label="playwright-trace",
        )
        storage_payload = context.storage_state()
        if _has_auth_cookie(storage_payload) and "/login" not in (page.url or ""):
            settings.storage_state_path.parent.mkdir(parents=True, exist_ok=True)
            context.storage_state(path=str(settings.storage_state_path))
            collector.register_artifact(
                artifact_type="storage_state",
                path=settings.storage_state_path,
                label="auth-storage-state",
            )
        context.close()
        browser.close()
        playwright.stop()
