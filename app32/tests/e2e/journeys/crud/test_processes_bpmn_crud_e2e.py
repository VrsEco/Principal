from __future__ import annotations

import pytest

from app32.tests.e2e.config.environments import E2EExecutionMode
from app32.tests.e2e.core.http_session import AuthenticatedHTTPSession


def _valid_bpmn_xml(process_id: int, marker: str) -> str:
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL"
                  xmlns:bpmndi="http://www.omg.org/spec/BPMN/20100524/DI"
                  xmlns:dc="http://www.omg.org/spec/DD/20100524/DC"
                  id="Definitions_AUTOE2E_{process_id}"
                  targetNamespace="https://gestaoversus.com.br/e2e/{process_id}">
  <bpmn:process id="Process_AUTOE2E_{process_id}" name="{marker}" isExecutable="false">
    <bpmn:startEvent id="StartEvent_AUTOE2E_{process_id}" name="Início {marker}" />
  </bpmn:process>
  <bpmndi:BPMNDiagram id="BPMNDiagram_AUTOE2E_{process_id}">
    <bpmndi:BPMNPlane id="BPMNPlane_AUTOE2E_{process_id}" bpmnElement="Process_AUTOE2E_{process_id}">
      <bpmndi:BPMNShape id="StartEvent_AUTOE2E_{process_id}_di" bpmnElement="StartEvent_AUTOE2E_{process_id}">
        <dc:Bounds x="180" y="120" width="36" height="36" />
      </bpmndi:BPMNShape>
    </bpmndi:BPMNPlane>
  </bpmndi:BPMNDiagram>
</bpmn:definitions>
"""


def _discover_process_with_saved_diagram(http: AuthenticatedHTTPSession, company_id: int) -> tuple[int, dict]:
    payload = http.request_json("GET", f"/api/companies/{company_id}/processes", operation="processes.list")
    if not isinstance(payload, list) or not payload:
        raise RuntimeError(f"Nenhum processo acessível encontrado para company_id={company_id}.")
    for item in payload:
        if not isinstance(item, dict) or not item.get("id"):
            continue
        process_id = int(item["id"])
        diagram = http.request_json(
            "GET",
            f"/api/processes/{process_id}/bpmn-diagram",
            operation=f"processes.bpmn_diagram.{process_id}",
        )
        if diagram.get("id") and diagram.get("status") in {"draft", "published"}:
            return process_id, diagram
    raise RuntimeError(f"Nenhum processo com diagrama BPMN salvo encontrado para company_id={company_id}.")


@pytest.mark.e2e
@pytest.mark.dev_full
def test_processes_bpmn_diagram_transactional_dev_full(e2e_run_context):
    settings = e2e_run_context.settings
    if settings.execution_mode is not E2EExecutionMode.DEV_FULL:
        pytest.skip("BPMN transacional só roda em DEV_FULL.")
    if settings.missing_requirements:
        pytest.skip(f"Configuração E2E incompleta: {', '.join(settings.missing_requirements)}")
    if not settings.destructive_actions_allowed:
        pytest.skip("BPMN transacional exige E2E_DESTRUCTIVE_ACTIONS_ALLOWED=true.")

    company_id = int(settings.company_id or 0)
    marker = e2e_run_context.run_marker
    journey = e2e_run_context.reporter.start_journey(
        journey="processes_bpmn_diagram_transactional_e2e",
        run_id=e2e_run_context.evidence.run_id,
        company_id=company_id,
        user_label=settings.username,
        metadata={"domain": "processes", "mode": settings.execution_mode.value},
    )
    http = AuthenticatedHTTPSession.create(settings)
    process_id: int | None = None
    original_diagram: dict | None = None

    try:
        journey.step("http_login", status="running")
        http.login()
        http.select_company()
        journey.step("http_login", status="passed")

        journey.step("discover_process_diagram", status="running")
        process_id, original_diagram = _discover_process_with_saved_diagram(http, company_id)
        journey.step(
            "discover_process_diagram",
            status="passed",
            details={"process_id": process_id, "diagram_id": original_diagram.get("id")},
        )

        route = f"/api/processes/{process_id}/bpmn-diagram"
        journey.step("save_marked_bpmn_draft", status="running")
        marked_payload = {
            "id": original_diagram["id"],
            "name": f"{marker} BPMN transacional",
            "status": "draft",
            "bpmn_xml": _valid_bpmn_xml(process_id, marker),
            "svg_snapshot": f"<svg xmlns='http://www.w3.org/2000/svg'><title>{marker}</title></svg>",
            "png_snapshot": original_diagram.get("png_snapshot"),
            "metadata_json": {
                **(original_diagram.get("metadata_json") or {}),
                "e2e_marker": marker,
                "e2e_original_status": original_diagram.get("status"),
            },
        }
        save_response = http.request("PUT", route, json_payload=marked_payload)
        save_response.raise_for_status()
        saved_payload = save_response.json()
        assert saved_payload.get("status") == "draft"
        assert marker in str(saved_payload.get("name") or "")
        journey.step("save_marked_bpmn_draft", status="passed")

        journey.step("validate_marked_bpmn_persisted", status="running")
        persisted_payload = http.request_json("GET", route, operation="processes.bpmn_diagram.persisted")
        assert persisted_payload.get("id") == original_diagram.get("id")
        assert marker in str(persisted_payload.get("bpmn_xml") or "")
        journey.step("validate_marked_bpmn_persisted", status="passed")

    except Exception as exc:
        journey.fail(
            step="processes_bpmn_diagram_transactional_e2e",
            failure_type=exc.__class__.__name__,
            details={"error": str(exc), "process_id": process_id},
        )
        raise
    finally:
        if process_id is not None and original_diagram is not None and original_diagram.get("id"):
            journey.step(
                "restore_original_bpmn_diagram",
                status="running",
                details={"process_id": process_id, "diagram_id": original_diagram.get("id")},
            )
            restore_payload = {
                "id": original_diagram["id"],
                "name": original_diagram.get("name") or f"Processo {process_id}",
                "status": original_diagram.get("status") if original_diagram.get("status") in {"draft", "published"} else "draft",
                "bpmn_xml": original_diagram.get("bpmn_xml"),
                "svg_snapshot": original_diagram.get("svg_snapshot"),
                "png_snapshot": original_diagram.get("png_snapshot"),
                "metadata_json": original_diagram.get("metadata_json") or {},
            }
            restore_response = http.request("PUT", f"/api/processes/{process_id}/bpmn-diagram", json_payload=restore_payload)
            restore_response.raise_for_status()
            restored_payload = restore_response.json()
            assert restored_payload.get("id") == original_diagram.get("id")
            assert marker not in str(restored_payload.get("name") or "")
            assert marker not in str(restored_payload.get("bpmn_xml") or "")
            journey.step("restore_original_bpmn_diagram", status="passed")

    journey.succeed()
