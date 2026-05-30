from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app32.tests.e2e.config.environments import E2EEnvironmentSettings
from app32.tests.e2e.core.http_session import AuthenticatedHTTPSession
from app32.tests.e2e.tasks.work_journey_tasks import WorkJourneyTasks


@dataclass(frozen=True)
class WorkJourneyFunctionalProbeResult:
    check_name: str
    route: str
    success: bool
    status_code: int
    details: dict[str, Any]


PUBLIC_ERROR_PATTERNS = (
    "Erro interno do servidor",
    "Erro interno",
    "Tente novamente ou contate o suporte",
)


def _contains_public_error(text: str) -> bool:
    normalized = str(text or "").lower()
    return any(pattern.lower() in normalized for pattern in PUBLIC_ERROR_PATTERNS)


def execute_work_journey_functional_probe(*, settings: E2EEnvironmentSettings) -> list[WorkJourneyFunctionalProbeResult]:
    http = AuthenticatedHTTPSession.create(settings)
    http.login()
    http.select_company()

    tasks = WorkJourneyTasks(work_journey_page=None, company_id=settings.company_id or 0)  # type: ignore[arg-type]
    board_route = tasks.route_map().board
    board_payload = http.request_json("GET", board_route, operation="work_journey.board")
    employee_id = int((((board_payload.get("data") or {}).get("employee") or {}).get("id")) or 0)
    if employee_id <= 0:
        raise RuntimeError(f"Board da jornada não retornou employee_id válido: {board_payload}")

    manual_tasks_payload = http.request_json(
        "GET",
        f"/api/companies/{settings.company_id or ''}/work-journey/manual-tasks?employee_id={employee_id}",
        operation="work_journey.manual_tasks",
    )

    page_route = f"/companies/{settings.company_id or ''}/work-journey"
    page_response = http.request("GET", page_route)
    page_response.raise_for_status()
    http.assert_not_login_redirect(page_response, operation="work_journey.page")
    page_html = page_response.text or ""

    return [
        WorkJourneyFunctionalProbeResult(
            check_name="work_journey.board",
            route=board_route,
            success=bool(board_payload.get("success")) and isinstance((board_payload.get("data") or {}).get("employee"), dict),
            status_code=200,
            details={"employee_id": employee_id},
        ),
        WorkJourneyFunctionalProbeResult(
            check_name="work_journey.manual_tasks",
            route=f"/api/companies/{settings.company_id or ''}/work-journey/manual-tasks",
            success=bool(manual_tasks_payload.get("success")) and isinstance((manual_tasks_payload.get("data") or {}).get("items"), list),
            status_code=200,
            details={"items_count": len(((manual_tasks_payload.get("data") or {}).get("items") or []))},
        ),
        WorkJourneyFunctionalProbeResult(
            check_name="work_journey.page",
            route=page_route,
            success=(
                any(marker in page_html for marker in ("data-work-journey-root", "id=\"workJourneyRoot\"", "work-journey-board"))
                and not _contains_public_error(page_html)
            ),
            status_code=page_response.status_code,
            details={
                "has_page_marker": any(marker in page_html for marker in ("data-work-journey-root", "id=\"workJourneyRoot\"", "work-journey-board")),
                "has_public_error": _contains_public_error(page_html),
            },
        ),
    ]
