from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[4]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app32.tests.e2e.config.contracts import validate_execution_contract
from app32.tests.e2e.config.environments import E2EExecutionMode, load_environment_settings
from app32.tests.e2e.core.http_session import AuthenticatedHTTPSession
from app32.tests.e2e.data.meeting_builders import (
    build_meeting_draft_payload,
    build_meeting_execution_payload,
)
from app32.tests.e2e.tasks.meetings_tasks import MeetingsTasks


def main() -> None:
    settings = load_environment_settings()
    validate_execution_contract(settings)
    if settings.execution_mode is not E2EExecutionMode.DEV_FULL:
        raise SystemExit("Este script só pode rodar em DEV_FULL.")

    http = AuthenticatedHTTPSession.create(settings)
    http.login()
    http.select_company()

    tasks = MeetingsTasks(meetings_page=None, company_id=settings.company_id or 0)  # type: ignore[arg-type]
    run_marker = "AUTOE2E::manual"
    draft = tasks.build_create_request(build_meeting_draft_payload(run_marker=run_marker))
    create_response = http.request("POST", f"/meetings/api/company/{settings.company_id}/meeting", json_payload=draft)
    create_response.raise_for_status()
    created = create_response.json()

    meeting_id = created["meeting_id"]
    routes = tasks.route_map(meeting_id)
    update_response = http.request("PUT", routes.preliminares, json_payload=draft)
    update_response.raise_for_status()

    start_response = http.request("POST", routes.start, json_payload={"project_type": "new"})
    start_response.raise_for_status()

    execution = tasks.build_execution_request(build_meeting_execution_payload(run_marker=run_marker))
    execution_response = http.request("PUT", routes.execution, json_payload=execution)
    execution_response.raise_for_status()

    finish_response = http.request("POST", routes.finish, json_payload={})
    finish_response.raise_for_status()

    delete_response = http.request("DELETE", routes.delete)
    delete_response.raise_for_status()

    print(
        json.dumps(
            {
                "ok": True,
                "meeting_id": meeting_id,
                "create": created,
                "update": update_response.json(),
                "start": start_response.json(),
                "execution": execution_response.json(),
                "finish": finish_response.json(),
                "delete": delete_response.json(),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
