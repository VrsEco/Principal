from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app32.tests.e2e.config.environments import E2EEnvironmentSettings
from app32.tests.e2e.core.functional_guards import contains_public_error, is_html_success
from app32.tests.e2e.core.http_session import AuthenticatedHTTPSession


@dataclass(frozen=True)
class ProcessesFunctionalProbeResult:
    check_name: str
    route: str
    success: bool
    status_code: int
    details: dict[str, Any]


def _discover_process(http: AuthenticatedHTTPSession, company_id: int) -> dict[str, Any]:
    payload = http.request_json(
        "GET",
        f"/api/companies/{company_id}/processes",
        operation="processes.list",
    )
    if not isinstance(payload, list) or not payload:
        raise RuntimeError(f"Nenhum processo acessível encontrado para company_id={company_id}.")
    selected = payload[0]
    if not selected.get("id"):
        raise RuntimeError(f"Payload de processo inválido para company_id={company_id}: {selected}")
    return selected


def execute_processes_functional_probe(*, settings: E2EEnvironmentSettings) -> list[ProcessesFunctionalProbeResult]:
    if settings.company_id is None:
        raise RuntimeError("E2E_COMPANY_ID é obrigatório para probe de processos.")

    http = AuthenticatedHTTPSession.create(settings)
    http.login()
    http.select_company()

    selected = _discover_process(http, settings.company_id)
    process_id = int(selected["id"])

    detail_payload = http.request_json(
        "GET",
        f"/api/processes/{process_id}",
        operation="processes.detail",
    )

    modeler_route = f"/processes/{process_id}/bpmn-modeler"
    modeler_response = http.request("GET", modeler_route)
    modeler_response.raise_for_status()
    http.assert_not_login_redirect(modeler_response, operation="processes.bpmn_modeler")
    modeler_html = modeler_response.text or ""

    diagram_payload = http.request_json(
        "GET",
        f"/api/processes/{process_id}/bpmn-diagram",
        operation="processes.bpmn_diagram",
    )

    portal_detail_route = f"/companies/{settings.company_id}/process-portal/processes/{process_id}"
    portal_detail_response = http.request("GET", portal_detail_route)
    portal_detail_response.raise_for_status()
    http.assert_not_login_redirect(portal_detail_response, operation="processes.portal_detail_page")

    portal_detail_payload = http.request_json(
        "GET",
        f"/api/companies/{settings.company_id}/process-portal/processes/{process_id}",
        operation="processes.portal_detail_api",
    )
    portal_detail_data = portal_detail_payload.get("data") if isinstance(portal_detail_payload, dict) else None
    portal_detail_data = portal_detail_data if isinstance(portal_detail_data, dict) else {}

    strategic_route = f"/companies/{settings.company_id}/process-portal/strategic-management?period=month&audience=client"
    strategic_response = http.request("GET", strategic_route)
    strategic_response.raise_for_status()
    http.assert_not_login_redirect(strategic_response, operation="processes.strategic_management_page")

    strategic_payload = http.request_json(
        "GET",
        f"/api/companies/{settings.company_id}/process-portal/strategic-management?period=month&audience=client",
        operation="processes.strategic_management_api_client",
    )
    strategic_data = strategic_payload.get("data") if isinstance(strategic_payload, dict) else None
    strategic_data = strategic_data if isinstance(strategic_data, dict) else {}

    results = [
        ProcessesFunctionalProbeResult(
            check_name="processes.list",
            route=f"/api/companies/{settings.company_id}/processes",
            success=True,
            status_code=200,
            details={"process_id": process_id, "process_code": selected.get("code")},
        ),
        ProcessesFunctionalProbeResult(
            check_name="processes.detail",
            route=f"/api/processes/{process_id}",
            success=bool(detail_payload.get("id")) and int(detail_payload.get("company_id") or 0) == settings.company_id,
            status_code=200,
            details={"has_bpmn_flow": bool((detail_payload.get("bpmn_flow") or {}).get("bpmn_xml"))},
        ),
        ProcessesFunctionalProbeResult(
            check_name="processes.bpmn_modeler",
            route=modeler_route,
            success=is_html_success(modeler_html, any_markers=("Salvar rascunho", "bpmn-modeler-shell")),
            status_code=modeler_response.status_code,
            details={
                "has_save_button": "Salvar rascunho" in modeler_html,
                "has_public_error": contains_public_error(modeler_html),
            },
        ),
        ProcessesFunctionalProbeResult(
            check_name="processes.portal_detail_page",
            route=portal_detail_route,
            success=is_html_success(
                portal_detail_response.text,
                any_markers=("Estrutura/Recursos", "Processo", "Recursos"),
            ),
            status_code=portal_detail_response.status_code,
            details={
                "has_resources_action": "Estrutura/Recursos" in portal_detail_response.text,
                "has_public_error": contains_public_error(portal_detail_response.text),
            },
        ),
        ProcessesFunctionalProbeResult(
            check_name="processes.portal_detail_resources_contract",
            route=f"/api/companies/{settings.company_id}/process-portal/processes/{process_id}",
            success=(
                isinstance(portal_detail_data.get("resources"), dict)
                and isinstance((portal_detail_data.get("stats") or {}).get("resource_count"), int)
            ),
            status_code=200,
            details={
                "resource_count": (portal_detail_data.get("stats") or {}).get("resource_count"),
                "has_grouped_resources": isinstance((portal_detail_data.get("resources") or {}).get("grouped"), dict),
                "contract": "detalhe do portal deve expor resources e stats.resource_count para a nova aba Estrutura/Recursos.",
            },
        ),
        ProcessesFunctionalProbeResult(
            check_name="processes.strategic_management_page_client",
            route=strategic_route,
            success=is_html_success(
                strategic_response.text,
                any_markers=("smpLayerStack", "Painel", "Gestão Estratégica"),
            ),
            status_code=strategic_response.status_code,
            details={
                "has_mobile_actions": "smpMobileActionsToggle" in strategic_response.text,
                "has_public_error": contains_public_error(strategic_response.text),
            },
        ),
        ProcessesFunctionalProbeResult(
            check_name="processes.strategic_management_api_client",
            route=f"/api/companies/{settings.company_id}/process-portal/strategic-management?period=month&audience=client",
            success=(
                strategic_data.get("audience") == "client"
                and isinstance((strategic_data.get("structuring_trail") or {}).get("phases"), list)
                and any(group.get("key") == "team_efficiency" for group in (strategic_data.get("groups") or []) if isinstance(group, dict))
            ),
            status_code=200,
            details={
                "audience": strategic_data.get("audience"),
                "groups": [group.get("key") for group in (strategic_data.get("groups") or []) if isinstance(group, dict)],
                "contract": "painel estratégico deve aceitar audience=client, expor trilha de estruturação e grupo team_efficiency.",
            },
        ),
        ProcessesFunctionalProbeResult(
            check_name="processes.bpmn_diagram",
            route=f"/api/processes/{process_id}/bpmn-diagram",
            success=isinstance(diagram_payload, dict) and "status" in diagram_payload,
            status_code=200,
            details={"status": diagram_payload.get("status"), "diagram_id": diagram_payload.get("id")},
        ),
    ]

    save_payload = {
        "id": diagram_payload.get("id"),
        "name": detail_payload.get("name") or selected.get("name") or f"Processo {process_id}",
        "status": "draft",
        "bpmn_xml": diagram_payload.get("bpmn_xml")
        or "<bpmn:definitions xmlns:bpmn='http://www.omg.org/spec/BPMN/20100524/MODEL'><bpmn:process id='Process_1' isExecutable='false'/></bpmn:definitions>",
        "svg_snapshot": diagram_payload.get("svg_snapshot") or "<svg xmlns='http://www.w3.org/2000/svg'></svg>",
        "metadata_json": diagram_payload.get("metadata_json") or {"source": "e2e_processes_functional_probe"},
    }
    save_response = http.request(
        "PUT",
        f"/api/processes/{process_id}/bpmn-diagram",
        json_payload=save_payload,
    )
    save_response.raise_for_status()
    http.assert_not_login_redirect(save_response, operation="processes.bpmn_save")
    save_payload_response = http._json_or_raise(save_response, operation="processes.bpmn_save")
    results.append(
        ProcessesFunctionalProbeResult(
            check_name="processes.bpmn_save",
            route=f"/api/processes/{process_id}/bpmn-diagram",
            success=isinstance(save_payload_response, dict) and save_payload_response.get("status") == "draft",
            status_code=save_response.status_code,
            details={"status": save_payload_response.get("status"), "diagram_id": save_payload_response.get("id")},
        )
    )

    return results
