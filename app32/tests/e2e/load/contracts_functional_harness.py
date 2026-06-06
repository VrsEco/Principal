from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode

from app32.tests.e2e.config.environments import E2EEnvironmentSettings
from app32.tests.e2e.core.functional_guards import contains_public_error, is_html_success
from app32.tests.e2e.core.http_session import AuthenticatedHTTPSession


@dataclass(frozen=True)
class ContractsFunctionalProbeResult:
    check_name: str
    route: str
    success: bool
    status_code: int
    details: dict[str, Any]


def _path_with_query(path: str, **params: Any) -> str:
    query = {
        key: value
        for key, value in params.items()
        if value not in (None, "")
    }
    if not query:
        return path
    return f"{path}?{urlencode(query)}"


def execute_contracts_functional_probe(*, settings: E2EEnvironmentSettings) -> list[ContractsFunctionalProbeResult]:
    http = AuthenticatedHTTPSession.create(settings)
    http.login()
    http.select_company()

    invoices_path = _path_with_query("/contracts/invoices", company_id=settings.company_id)
    invoices_html = http.request("GET", invoices_path)
    invoices_html.raise_for_status()
    http.assert_not_login_redirect(invoices_html, operation="contracts.fiscal_invoices_workspace")

    issuer_filter_path = _path_with_query(
        "/contracts/invoices",
        company_id=settings.company_id,
        issuer_legal_entity_id=999999999,
        fiscal_status="active",
    )
    issuer_filter_html = http.request("GET", issuer_filter_path)
    issuer_filter_html.raise_for_status()
    http.assert_not_login_redirect(issuer_filter_html, operation="contracts.fiscal_invoices_issuer_filter")

    return [
        ContractsFunctionalProbeResult(
            check_name="contracts.fiscal_invoices_workspace",
            route=invoices_path,
            success=is_html_success(
                invoices_html.text,
                all_markers=("Notas Fiscais", "Registros fiscais", "Ações em lote"),
            ),
            status_code=invoices_html.status_code,
            details={
                "content_type": str(invoices_html.headers.get("Content-Type") or ""),
                "has_public_error": contains_public_error(invoices_html.text),
            },
        ),
        ContractsFunctionalProbeResult(
            check_name="contracts.fiscal_invoices_issuer_filter",
            route=issuer_filter_path,
            success=is_html_success(
                issuer_filter_html.text,
                all_markers=("PJ emissora", 'name="issuer_legal_entity_id"', "Aplicar filtros"),
            ),
            status_code=issuer_filter_html.status_code,
            details={
                "content_type": str(issuer_filter_html.headers.get("Content-Type") or ""),
                "has_public_error": contains_public_error(issuer_filter_html.text),
                "filter_param": "issuer_legal_entity_id",
            },
        ),
        ContractsFunctionalProbeResult(
            check_name="contracts.fiscal_invoices_bulk_actions_panel",
            route=invoices_path,
            success=is_html_success(
                invoices_html.text,
                all_markers=("Organização fiscal", "Gerar planilha XLSX", "Upload planilha/XML/PDF"),
            ),
            status_code=invoices_html.status_code,
            details={
                "content_type": str(invoices_html.headers.get("Content-Type") or ""),
                "has_public_error": contains_public_error(invoices_html.text),
            },
        ),
    ]
