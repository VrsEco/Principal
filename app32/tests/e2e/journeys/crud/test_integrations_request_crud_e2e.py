from __future__ import annotations

from pathlib import Path
import asyncio
import json
import sys

import pytest

from app32.tests.e2e.config.environments import E2EEnvironmentSettings, E2EExecutionMode
from app32.tests.e2e.core.http_session import AuthenticatedHTTPSession


def _suffix(run_id: str) -> str:
    return "".join(ch for ch in run_id if ch.isdigit())[-10:] or "0000000000"


def _ensure_app_dir_on_path() -> None:
    app_dir = Path(__file__).resolve().parents[4]
    if str(app_dir) not in sys.path:
        sys.path.insert(0, str(app_dir))


@pytest.mark.e2e
@pytest.mark.dev_full
def test_integrations_request_transactional_e2e(
    e2e_settings: E2EEnvironmentSettings,
    e2e_run_context,
):
    if e2e_settings.execution_mode is not E2EExecutionMode.DEV_FULL:
        pytest.skip("CRUD de integração destrutivo só deve rodar em DEV_FULL.")
    if e2e_settings.missing_requirements:
        pytest.skip(
            "Configuração E2E incompleta. Defina: "
            + ", ".join(e2e_settings.missing_requirements)
        )
    if not e2e_settings.company_id:
        pytest.skip("E2E_COMPANY_ID obrigatório para jornada de integrações.")

    company_id = int(e2e_settings.company_id)
    run_id = e2e_run_context.evidence.run_id
    marker = f"AUTOE2E::{run_id}"
    suffix = _suffix(run_id)

    journey = e2e_run_context.reporter.start_journey(
        journey="integrations_request_transactional_e2e",
        run_id=run_id,
        company_id=company_id,
        user_label=e2e_settings.username,
        metadata={"domain": "integrations", "mode": e2e_settings.environment_name},
    )

    http = AuthenticatedHTTPSession.create(e2e_settings)
    journey.step("http_login", status="running")
    login_payload = http.login()
    http.select_company()
    journey.step("http_login", status="passed", details={"redirect": login_payload.get("redirect")})

    request_id: int | None = None
    backlog_task_id: int | None = None

    try:
        journey.step("validate_catalog_and_page", status="running")
        catalog_payload = http.request_json(
            "GET",
            "/api/integrations/catalog",
            operation="integrations.catalog",
        )
        assert catalog_payload.get("success") is True
        assert isinstance(catalog_payload.get("catalog"), dict)

        page = http.request("GET", "/api-mcp")
        page.raise_for_status()
        http.assert_not_login_redirect(page, operation="integrations.page")
        assert "#integrationsWorkspace" in (page.text or "") or "API / MCP" in (page.text or "")
        journey.step("validate_catalog_and_page", status="passed")

        journey.step("validate_mcp_health", status="running")
        if http.local_client is not None:
            _ensure_app_dir_on_path()
            from src.core.mcp_http_server import _healthz

            health = asyncio.run(_healthz(None))  # type: ignore[arg-type]
            payload = json.loads(health.body.decode("utf-8"))
            assert payload.get("ok") is True
            health_details = {"status_code": 200, "route": "/healthz", "mode": "dev_local_mcp_health"}
        else:
            health = http.session.get(
                f"{e2e_settings.base_url.rstrip('/')}/mcp/healthz",
                timeout=e2e_settings.request_timeout_seconds,
            )
            health.raise_for_status()
            assert health.status_code == 200
            health_details = {"status_code": health.status_code, "route": "/mcp/healthz"}
        journey.step("validate_mcp_health", status="passed", details=health_details)

        journey.step("create_integration_request", status="running")
        create_payload = {
            "title": f"Solicitação QA Integração {suffix}",
            "business_domain": "QA",
            "integration_mode": "bidirectional",
            "technical_channel": "api_mcp",
            "source_channel": "e2e_devfull",
            "external_system": f"Sandbox QA Integrações {suffix}",
            "objective": (
                f"{marker} Validar criação transacional de solicitação fake de integração, "
                "sem acionar provedor externo real."
            ),
            "data_summary": (
                f"{marker} Payload sintético com metadados de conectividade API/MCP, "
                "sem dados pessoais ou credenciais reais."
            ),
            "frequency": "on_demand",
            "urgency": "low",
            "compliance_level": "internal",
            "provider_contact": "qa-integracoes@example.invalid",
            "provider_docs_url": "https://example.invalid/integracoes/qa",
            "notes": f"{marker} Criar, listar, validar card de backlog derivado e excluir tudo no teardown.",
        }
        created = http.request_json(
            "POST",
            "/api/integrations/requests",
            json_payload=create_payload,
            operation="integrations.requests.create",
        )
        record = created["request"]
        request_id = int(record["id"])
        backlog_task_id = int(record["backlog_task_id"]) if record.get("backlog_task_id") else None
        assert record["company_id"] == company_id
        assert record["technical_channel"] == "api_mcp"
        assert record["source_channel"] == "e2e_devfull"
        journey.step(
            "create_integration_request",
            status="passed",
            details={"request_id": request_id, "backlog_task_id": backlog_task_id},
        )

        journey.step("list_and_validate_request", status="running")
        listed = http.request_json(
            "GET",
            "/api/integrations/requests?limit=50",
            operation="integrations.requests.list",
        )
        requests = listed.get("requests") or []
        matched = [item for item in requests if str(item.get("id")) == str(request_id)]
        assert matched, f"Solicitação criada não retornou na lista: {request_id}"
        assert str(matched[0].get("objective") or "").find(marker) >= 0
        if backlog_task_id is not None:
            assert int(matched[0].get("backlog_task_id") or 0) == backlog_task_id
        journey.step("list_and_validate_request", status="passed")

        journey.step("delete_integration_request", status="running")
        deleted = http.request_json(
            "DELETE",
            f"/api/integrations/requests/{request_id}",
            operation="integrations.requests.delete",
        )
        assert deleted.get("success") is True
        deleted_payload = deleted.get("deleted") or {}
        assert int(deleted_payload.get("id") or 0) == request_id
        if backlog_task_id is not None:
            assert int(deleted_payload.get("deleted_backlog_task_id") or 0) == backlog_task_id
        request_id = None
        journey.step("delete_integration_request", status="passed", details=deleted_payload)

        journey.step("confirm_request_removed", status="running")
        listed_after_delete = http.request_json(
            "GET",
            "/api/integrations/requests?limit=50",
            operation="integrations.requests.list_after_delete",
        )
        assert not [
            item
            for item in (listed_after_delete.get("requests") or [])
            if str(item.get("id")) == str(deleted_payload.get("id"))
        ]
        journey.step("confirm_request_removed", status="passed")

    except Exception as exc:
        journey.fail(
            step="integrations_transactional_runtime",
            failure_type="http_runtime_error",
            details={"error": str(exc), "request_id": request_id, "backlog_task_id": backlog_task_id},
        )
        raise
    finally:
        if request_id is not None:
            journey.step("delete_integration_request_cleanup", status="running", details={"request_id": request_id})
            cleanup = http.request("DELETE", f"/api/integrations/requests/{request_id}")
            if cleanup.status_code not in {200, 404}:
                cleanup.raise_for_status()
            journey.step("delete_integration_request_cleanup", status="passed", details={"status_code": cleanup.status_code})

    journey.succeed()
