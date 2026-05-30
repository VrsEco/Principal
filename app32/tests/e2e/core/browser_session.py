from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from playwright.sync_api import Browser, BrowserContext, Page, Playwright, sync_playwright

from app32.tests.e2e.config.environments import E2EEnvironmentSettings
from app32.tests.e2e.core.evidence import EvidenceCollector, EvidencePaths


def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _has_auth_cookie(storage_state: dict) -> bool:
    for cookie in storage_state.get("cookies", []) or []:
        if str(cookie.get("name") or "").strip() == "gv_session" and str(cookie.get("value") or "").strip():
            return True
    return False


@contextmanager
def managed_page(
    settings: E2EEnvironmentSettings,
    evidence: EvidencePaths,
    collector: EvidenceCollector,
) -> Iterator[tuple[Playwright, Browser, BrowserContext, Page]]:
    playwright = sync_playwright().start()
    browser_launcher = getattr(playwright, settings.browser_name)
    browser = browser_launcher.launch(headless=settings.headless)

    video_dir = evidence.videos_dir
    video_dir.mkdir(parents=True, exist_ok=True)
    context = browser.new_context(
        base_url=settings.base_url or None,
        ignore_https_errors=True,
        record_video_dir=str(video_dir),
        storage_state=str(settings.storage_state_path) if settings.storage_state_path.exists() else None,
        viewport={"width": 1440, "height": 960},
    )
    context.tracing.start(screenshots=True, snapshots=True, sources=True)
    page = context.new_page()

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
