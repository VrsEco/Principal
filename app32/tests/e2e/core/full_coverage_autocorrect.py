from __future__ import annotations

import json
import os
import re
import ast
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    import yaml
except ModuleNotFoundError:  # pragma: no cover
    yaml = None

from app32.tests.e2e.catalog.drift_detector import detect_inventory_drift, discover_registered_routes, normalize_route
from app32.tests.e2e.catalog.inventory import iter_inventory_items
from app32.tests.e2e.catalog.suite_catalog import list_suite_catalog, repo_root
from app32.tests.e2e.catalog.ui_contract_generator import build_ui_human_like_contracts
from app32.tests.e2e.catalog.ui_inventory_discovery import discover_ui_inventory


AAJ1_PROJECT_CODE = "AA.J.1"
MUTATION_ADAPTER_MODULES = {"admin", "financial", "integrations", "meetings", "processes", "work_journey"}
DEDICATED_ADAPTER_REQUIRED_MODULES = {"ai", "consultive", "contracts", "real_estate", "workspace"}


CLASSIFIED_BACKLOG_GAP_TYPES = {
    "field_or_action_requires_human_gate",
    "route_mixed_get_and_mutation_without_rollback_contract",
    "route_mutation_without_rollback_contract",
}


def _is_classified_backlog_gap(gap_type: str) -> bool:
    return str(gap_type or "") in CLASSIFIED_BACKLOG_GAP_TYPES


@dataclass(frozen=True)
class CoverageGap:
    gap_id: str
    gap_type: str
    severity: str
    title: str
    description: str
    correction_kind: str
    correction_status: str
    correction_plan: list[str]
    metadata: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "gap_id": self.gap_id,
            "gap_type": self.gap_type,
            "severity": self.severity,
            "title": self.title,
            "description": self.description,
            "correction_kind": self.correction_kind,
            "correction_status": self.correction_status,
            "correction_plan": self.correction_plan,
            "metadata": self.metadata,
        }


def _safe_id(*parts: Any) -> str:
    raw = "::".join(str(part or "") for part in parts)
    value = re.sub(r"[^a-zA-Z0-9]+", "-", raw).strip("-").lower()
    return value[:180] or "gap"


def _route_module(route: str) -> str:
    normalized = normalize_route(route)
    if normalized.startswith("/api/ai/board") or normalized.startswith("/api/v2/chat"):
        return "ai"
    if normalized.startswith("/api/consultive"):
        return "consultive"
    if normalized.startswith("/api/real-estate-auctions"):
        return "real_estate"
    if normalized.startswith("/api/financial") or normalized.startswith("/api/incentive") or normalized.startswith("/api/v1/incentives"):
        return "financial"
    if normalized.startswith("/api/integrations") or normalized.startswith("/api-mcp") or normalized.startswith("/channels"):
        return "integrations"
    if normalized.startswith("/api/meetings"):
        return "meetings"
    if (
        normalized.startswith("/api/projects")
        or normalized.startswith("/api/process")
        or normalized.startswith("/api/macro-processes")
        or normalized.startswith("/api/process-instances")
        or normalized.startswith("/api/activity-work-logs")
        or normalized.startswith("/api/indicator")
        or normalized.startswith("/api/indicators")
        or normalized.startswith("/api/okrs")
        or normalized.startswith("/api/key-results")
        or normalized.startswith("/api/plans")
        or normalized.startswith("/api/resources")
        or normalized.startswith("/api/routines")
        or normalized.startswith("/api/occurrences")
        or normalized.startswith("/api/notes")
        or normalized.startswith("/api/strategy-alignment")
    ):
        return "processes"
    if "work-journey" in normalized or normalized.startswith("/api/user-employee"):
        return "work_journey"
    if (
        normalized.startswith("/api/companies")
        or normalized.startswith("/api/configs")
        or normalized.startswith("/api/agents")
        or normalized.startswith("/api/ai-monitoring")
        or normalized.startswith("/api/cadastro-agent")
        or normalized.startswith("/api/usuarios")
        or normalized.startswith("/api/internal-audit")
        or normalized.startswith("/api/qa/robot-tests")
    ):
        return "admin"
    if normalized.startswith("/my-work") or normalized.startswith("/main"):
        return "workspace"
    if normalized.startswith("/meetings"):
        return "meetings"
    if (
        normalized.startswith("/companies")
        or normalized.startswith("/company/")
        or normalized.startswith("/profile")
        or normalized.startswith("/auth/profile")
        or normalized.startswith("/agents")
    ):
        return "admin"
    if "work-journey" in normalized:
        return "work_journey"
    if normalized.startswith("/financial") or normalized.startswith("/incentives"):
        return "financial"
    if normalized.startswith("/contracts"):
        return "contracts"
    if normalized.startswith("/real-estate-auctions"):
        return "real_estate"
    if normalized.startswith("/api-mcp") or normalized.startswith("/channels") or normalized.startswith("/integrations"):
        return "integrations"
    if (
        normalized.startswith("/process")
        or normalized.startswith("/projects")
        or normalized.startswith("/indicators")
        or normalized.startswith("/plans")
    ):
        return "processes"
    if normalized.startswith("/usuarios"):
        return "admin"
    if normalized.startswith("/api/configs") or normalized.startswith("/qa"):
        return "governance"
    if normalized.startswith("/api/"):
        return "api"
    return "cross"


def _has_existing_mutation_adapter(route: str) -> bool:
    return _route_module(route) in MUTATION_ADAPTER_MODULES


def _is_operation_route(route: str) -> bool:
    normalized = normalize_route(route)
    return normalized.startswith("/api/") or _has_operation_hint(normalized)


def _has_operation_hint(route: str) -> bool:
    normalized = normalize_route(route)
    return any(
        token in normalized
        for token in (
            "save",
            "delete",
            "remove",
            "cancel",
            "approve",
            "export",
            "download",
            "generate",
            "import",
            "sync",
        )
    )


def _is_route_auto_contractable(route: str) -> bool:
    """Rotas que podem ganhar contrato sintético seguro sem mutação.

    Não executa a rota aqui; apenas evita tratar página/leitura como lacuna de
    contrato manual quando o robô já consegue gerar contrato de abertura/fixture.
    APIs e rotas com verbos operacionais continuam no backlog explícito.
    """
    normalized = normalize_route(route)
    if normalized.startswith("/api/"):
        return False
    if _is_operation_route(normalized):
        return False
    return True


def _literal_string(node: ast.AST) -> str | None:
    return node.value if isinstance(node, ast.Constant) and isinstance(node.value, str) else None


def _literal_methods(node: ast.AST | None) -> set[str] | None:
    if node is None:
        return None
    if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
        values = {_literal_string(item) for item in node.elts}
        methods = {str(value).upper() for value in values if value}
        return methods or None
    return None


def _join_route(prefix: str, route: str) -> str:
    prefix = str(prefix or "").rstrip("/")
    route = str(route or "")
    if not prefix:
        return normalize_route(route)
    if route.startswith(prefix + "/") or route == prefix:
        return normalize_route(route)
    return normalize_route(f"{prefix}/{route.lstrip('/')}")


def discover_registered_route_methods() -> dict[str, set[str]]:
    """Extrai métodos HTTP estáticos de decorators Flask/Blueprint.

    Fallback conservador: decorators sem `methods=[...]` são GET; rotas que não
    conseguimos inferir permanecem sem auto-contrato de API.
    """
    app_root = repo_root() / "app32"
    ignored = {"archive", "docs", "tests", "scripts", "__pycache__", ".agent"}
    route_methods: dict[str, set[str]] = {}
    resource_class_methods: dict[str, set[str]] = {}
    parsed_trees: list[ast.AST] = []
    for path in app_root.rglob("*.py"):
        if any(part in ignored for part in path.parts) or path.name.startswith(".codex_temp"):
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8-sig", errors="ignore"))
        except SyntaxError:
            continue
        parsed_trees.append(tree)
        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef):
                continue
            methods = {
                item.name.upper()
                for item in node.body
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
                and item.name.lower() in {"get", "post", "put", "patch", "delete"}
            }
            if methods:
                resource_class_methods[node.name] = methods

    for tree in parsed_trees:
        prefixes: dict[str, str] = {}
        for node in ast.walk(tree):
            if not isinstance(node, ast.Assign) or not isinstance(node.value, ast.Call):
                continue
            func = node.value.func
            if not isinstance(func, ast.Name) or func.id != "Blueprint":
                continue
            prefix = ""
            for kw in node.value.keywords:
                if kw.arg == "url_prefix":
                    prefix = _literal_string(kw.value) or ""
            for target in node.targets:
                if isinstance(target, ast.Name):
                    prefixes[target.id] = prefix

        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            for decorator in node.decorator_list:
                if not isinstance(decorator, ast.Call):
                    continue
                func = decorator.func
                if not isinstance(func, ast.Attribute) or func.attr != "route" or not decorator.args:
                    continue
                route_literal = _literal_string(decorator.args[0])
                if not route_literal:
                    continue
                prefix = prefixes.get(func.value.id, "") if isinstance(func.value, ast.Name) else ""
                methods_node = next((kw.value for kw in decorator.keywords if kw.arg == "methods"), None)
                methods = _literal_methods(methods_node) or {"GET"}
                normalized = _join_route(prefix, route_literal)
                route_methods.setdefault(normalized, set()).update(methods)

        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            if not isinstance(func, ast.Attribute) or func.attr != "add_resource" or len(node.args) < 2:
                continue
            resource_arg = node.args[0]
            if not isinstance(resource_arg, ast.Name):
                continue
            methods = resource_class_methods.get(resource_arg.id)
            if not methods:
                continue
            for route_arg in node.args[1:]:
                route_literal = _literal_string(route_arg)
                if not route_literal or not route_literal.startswith("/"):
                    continue
                route_methods.setdefault(normalize_route(route_literal), set()).update(methods)
    return route_methods


def _is_api_get_auto_contractable(route: str, methods: set[str] | None) -> bool:
    normalized = normalize_route(route)
    if not normalized.startswith("/api/"):
        return False
    if not methods:
        return False
    effective = {method for method in methods if method not in {"HEAD", "OPTIONS"}}
    return effective == {"GET"} and not _has_operation_hint(normalized)


def _is_get_report_download_auto_contractable(route: str, methods: set[str] | None) -> bool:
    normalized = normalize_route(route)
    if not methods:
        return False
    effective = {method for method in methods if method not in {"HEAD", "OPTIONS"}}
    if effective != {"GET"}:
        return False
    return any(token in normalized for token in ("export", "download", "report", "template", "imports"))


def _has_safe_get_method(methods: set[str] | None) -> bool:
    if not methods:
        return False
    return "GET" in {method for method in methods if method not in {"HEAD", "OPTIONS"}}


def _is_ai_validation_guard_contractable(route: str, methods: set[str] | None) -> bool:
    """Contratos negativos seguros de IA: validam payload obrigatório sem acionar grafo/LLM."""
    normalized = normalize_route(route)
    if _route_module(normalized) != "ai" or not methods:
        return False
    effective = {method for method in methods if method not in {"HEAD", "OPTIONS"}}
    return bool(effective) and effective.issubset({"POST"})


def _is_consultive_tenant_contract_covered(route: str, methods: set[str] | None, suites: set[str]) -> bool:
    """Cobertura consultive por harness tenant-safe com write-gate e services mockados."""
    if "consultive_tenant_contract_probe" not in suites:
        return False
    normalized = normalize_route(route)
    if _route_module(normalized) != "consultive" or not methods:
        return False
    effective = {method for method in methods if method not in {"HEAD", "OPTIONS"}}
    return bool(effective) and effective.issubset({"GET", "POST"})


def _is_real_estate_tenant_contract_covered(route: str, methods: set[str] | None, suites: set[str]) -> bool:
    """Cobertura real_estate por harness P1 tenant-safe, routes/templates/MCP, sem persistência."""
    if "real_estate_tenant_contract_probe" not in suites:
        return False
    normalized = normalize_route(route)
    if _route_module(normalized) != "real_estate" or not methods:
        return False
    effective = {method for method in methods if method not in {"HEAD", "OPTIONS"}}
    return bool(effective) and effective.issubset({"GET", "POST", "PUT", "PATCH", "DELETE"})


def _is_contracts_tenant_contract_covered(route: str, methods: set[str] | None, suites: set[str]) -> bool:
    """Cobertura contracts por harness P1 tenant-safe e probes funcionais sem mutação persistente."""
    if "contracts_tenant_contract_probe" not in suites:
        return False
    normalized = normalize_route(route)
    if _route_module(normalized) != "contracts":
        return False
    if not methods:
        return True
    effective = {method for method in methods if method not in {"HEAD", "OPTIONS"}}
    return bool(effective) and effective.issubset({"GET", "POST", "PUT", "PATCH", "DELETE"})


def _is_workspace_tenant_contract_covered(route: str, methods: set[str] | None, suites: set[str]) -> bool:
    """Cobertura workspace por harness funcional + contrato estrutural de human-gate."""
    if "workspace_tenant_contract_probe" not in suites:
        return False
    normalized = normalize_route(route)
    if _route_module(normalized) != "workspace":
        return False
    if not methods:
        return True
    effective = {method for method in methods if method not in {"HEAD", "OPTIONS"}}
    return bool(effective) and effective.issubset({"GET", "POST", "PUT", "PATCH", "DELETE"})


def _route_gap_type(route: str, methods: set[str] | None) -> str:
    normalized = normalize_route(route)
    if not methods:
        return "route_unknown_method_without_contract"
    effective = {method for method in methods if method not in {"HEAD", "OPTIONS"}}
    if normalized.startswith("/api/") and "GET" in effective and len(effective) > 1:
        return "route_mixed_get_and_mutation_without_rollback_contract"
    if effective and effective.issubset({"POST", "PUT", "PATCH", "DELETE"}):
        return "route_mutation_without_rollback_contract"
    return "route_without_contract"


def _contracted_routes() -> set[str]:
    return {normalize_route(item["route"]) for item in iter_inventory_items() if item.get("route")}


def _element_contract_key(*, template: Any, route: Any, selector: Any, element_type: Any, action_kind: Any) -> tuple[str, str, str, str, str]:
    return (
        str(template or ""),
        normalize_route(str(route or "")) if route else "",
        str(selector or ""),
        str(element_type or ""),
        str(action_kind or ""),
    )


def _generated_contract_index(payload: dict[str, Any]) -> dict[tuple[str, str, str, str, str], dict[str, Any]]:
    index: dict[tuple[str, str, str, str, str], dict[str, Any]] = {}
    for contract in payload.get("contracts") or []:
        key = _element_contract_key(
            template=contract.get("template"),
            route=contract.get("route"),
            selector=contract.get("selector"),
            element_type=contract.get("element_type"),
            action_kind=contract.get("action_kind"),
        )
        index[key] = contract
    return index


def discover_mcp_tool_inventory() -> dict[str, Any]:
    """Inventaria ferramentas MCP de forma estática e conservadora.

    O objetivo aqui é cobertura de governança: detectar superfícies `tool` que
    existem no código e precisam aparecer nos contratos/probes. A execução real
    continua nas suítes MCP já existentes, preservando MCP First e tenant-safe.
    """
    root = repo_root() / "app32"
    candidates: set[str] = set()
    files: list[str] = []
    patterns = [
        re.compile(r"@(?:mcp\.)?tool\([^)]*name=[\"']([^\"']+)[\"']", re.I),
        re.compile(r"register_tool\([\"']([^\"']+)[\"']", re.I),
        re.compile(r"Tool\([^)]*name=[\"']([^\"']+)[\"']", re.I),
        re.compile(r"[\"']tool_name[\"']\s*:\s*[\"']([^\"']+)[\"']", re.I),
    ]
    for path in root.rglob("*.py"):
        if any(part in {"tests", "__pycache__", "archive"} for part in path.parts):
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if "mcp" not in text.lower() and "tool" not in text.lower():
            continue
        found = False
        for pattern in patterns:
            for match in pattern.finditer(text):
                value = str(match.group(1) or "").strip()
                if value:
                    candidates.add(value)
                    found = True
        if found:
            files.append(str(path.relative_to(root)))
    return {
        "tools_total": len(candidates),
        "tools": sorted(candidates),
        "source_files": sorted(files),
    }


def build_autocorrection_execution_log(report: dict[str, Any]) -> dict[str, Any]:
    """Consolida o que o robô corrigiu automaticamente e o que virou backlog.

    Neste contexto, "correção automática" segura significa gerar/registrar
    contratos executáveis e acoplar esses contratos às suítes DEV_FULL já
    existentes, sem alterar regra de negócio nem executar mutação cega.
    Alterações destrutivas continuam exigindo rollback comprovado, adapter de
    domínio ou card AA.J.1.
    """
    matrix = report.get("coverage_matrix") or {}
    candidates = list(report.get("correction_candidates") or [])
    correction_groups = build_correction_groups(candidates)
    by_type: dict[str, list[dict[str, Any]]] = {}
    for candidate in candidates:
        by_type.setdefault(str(candidate.get("gap_type") or "unknown"), []).append(candidate)

    safe_generated = int(matrix.get("ui_elements_safe_executable_total") or 0)
    mutation_generated = int(matrix.get("ui_elements_mutation_with_rollback_total") or 0)
    human_gate = int(matrix.get("ui_elements_human_gate_required_total") or 0)
    route_auto_generated = int(matrix.get("app_routes_auto_contract_generated_total") or 0)
    api_get_auto_generated = int(matrix.get("api_get_routes_auto_contract_generated_total") or 0)
    api_get_partial_generated = int(matrix.get("api_get_partial_contract_generated_total") or 0)
    get_report_download_generated = int(matrix.get("get_report_download_contract_generated_total") or 0)
    ai_validation_guard_generated = int(matrix.get("ai_validation_guard_contract_generated_total") or 0)
    consultive_tenant_contract_covered = int(matrix.get("consultive_tenant_contract_covered_total") or 0)
    real_estate_tenant_contract_covered = int(matrix.get("real_estate_tenant_contract_covered_total") or 0)
    contracts_tenant_contract_covered = int(matrix.get("contracts_tenant_contract_covered_total") or 0)
    workspace_tenant_contract_covered = int(matrix.get("workspace_tenant_contract_covered_total") or 0)
    route_mutation_adapter_covered = int(matrix.get("route_mutation_existing_adapter_covered_total") or 0)
    ui_human_gate_adapter_covered = int(matrix.get("ui_human_gate_existing_adapter_covered_total") or 0)
    screen_auto_generated = int(matrix.get("ui_screens_auto_contract_generated_total") or 0)
    route_context = int(matrix.get("ui_elements_without_route_context_total") or 0)
    inactive_templates = int(matrix.get("ui_elements_in_inactive_templates_total") or 0)
    gap_counts = matrix.get("execution_backlog_by_type") or matrix.get("coverage_gaps_by_type") or {}
    route_gaps = sum(
        int(value or 0)
        for key, value in gap_counts.items()
        if str(key).startswith("route_")
    )
    screen_gaps = int(gap_counts.get("screen_without_contract") or 0)
    classified_policy_covered = int(matrix.get("classified_policy_covered_total") or 0)

    actions = [
        {
            "action_id": "ui_safe_contracts_generated",
            "status": "applied",
            "items_total": safe_generated,
            "evidence": "Contratos UI safe foram gerados e são consumidos pela suíte ui_safe_contract_execution.",
            "next_executor": "ui_safe_contract_execution",
        },
        {
            "action_id": "ui_mutation_contracts_routed",
            "status": "applied_with_gate",
            "items_total": max(mutation_generated - human_gate, 0),
            "evidence": "Contratos mutacionais sem human gate foram roteados para adapter transacional com rollback/resíduo zero.",
            "next_executor": "ui_mutation_contract_execution",
        },
        {
            "action_id": "route_page_contracts_generated",
            "status": "applied",
            "items_total": route_auto_generated,
            "evidence": "Rotas de página/leitura sem operação mutacional foram cobertas por contrato sintético de abertura/fixture.",
            "next_executor": "full_coverage_autocorrect_audit",
        },
        {
            "action_id": "api_get_contracts_generated",
            "status": "applied",
            "items_total": api_get_auto_generated,
            "evidence": "APIs GET sem verbo operacional foram cobertas por contrato sintético de leitura tenant-safe.",
            "next_executor": "full_coverage_autocorrect_audit",
        },
        {
            "action_id": "api_get_partial_contracts_generated",
            "status": "applied_with_remaining_mutation_backlog",
            "items_total": api_get_partial_generated,
            "evidence": "APIs mistas tiveram o método GET coberto por contrato sintético; métodos mutacionais continuam no backlog até adapter/rollback.",
            "next_executor": "full_coverage_autocorrect_audit",
        },
        {
            "action_id": "get_report_download_contracts_generated",
            "status": "applied",
            "items_total": get_report_download_generated,
            "evidence": "Rotas GET de relatório/export/template foram cobertas por contrato sintético seguro de download/renderização.",
            "next_executor": "report_download_probe",
        },
        {
            "action_id": "ai_validation_guard_contracts_generated",
            "status": "applied",
            "items_total": ai_validation_guard_generated,
            "evidence": "Rotas AI/agentic POST foram cobertas por contrato negativo de validação obrigatório, sem acionar LangGraph/LLM nem criar estado persistente.",
            "next_executor": "full_coverage_autocorrect_audit",
        },
        {
            "action_id": "consultive_tenant_contracts_covered",
            "status": "applied_with_tenant_safe_contract",
            "items_total": consultive_tenant_contract_covered,
            "evidence": "Rotas consultive GET/POST foram cobertas por harness tenant-safe com company_id ativo, write-gate e services mockados, sem mutação persistente.",
            "next_executor": "consultive_tenant_contract_probe",
        },
        {
            "action_id": "real_estate_tenant_contracts_covered",
            "status": "applied_with_tenant_safe_contract",
            "items_total": real_estate_tenant_contract_covered,
            "evidence": "Rotas real_estate foram cobertas por harness P1 tenant-safe de rotas/templates/service/MCP com services mockados, sem mutação persistente.",
            "next_executor": "real_estate_tenant_contract_probe",
        },
        {
            "action_id": "contracts_tenant_contracts_covered",
            "status": "applied_with_tenant_safe_contract",
            "items_total": contracts_tenant_contract_covered,
            "evidence": "Ações human-gate de contratos foram cobertas por contrato P1 tenant-safe: rotas autenticadas/scoped, templates parseáveis e controles críticos presentes, sem mutação persistente.",
            "next_executor": "contracts_tenant_contract_probe",
        },
        {
            "action_id": "workspace_tenant_contracts_covered",
            "status": "applied_with_tenant_safe_contract",
            "items_total": workspace_tenant_contract_covered,
            "evidence": "Ação human-gate do workspace foi coberta por probe funcional e contrato estrutural do botão de exclusão, sem executar exclusão cega.",
            "next_executor": "workspace_tenant_contract_probe",
        },
        {
            "action_id": "route_mutation_existing_adapters_covered",
            "status": "applied_with_rollback_adapter",
            "items_total": route_mutation_adapter_covered,
            "evidence": "Rotas mutacionais de domínios com suíte transacional DEV_FULL existente foram cobertas por adapter de domínio com rollback/resíduo zero.",
            "next_executor": "devfull_transactional_validation",
        },
        {
            "action_id": "ui_human_gate_existing_adapters_covered",
            "status": "applied_with_rollback_adapter",
            "items_total": ui_human_gate_adapter_covered,
            "evidence": "Ações UI inicialmente marcadas como human-gate foram migradas para cobertura automática quando a rota pertence a domínio com adapter DEV_FULL transacional e rollback/resíduo zero.",
            "next_executor": "ui_mutation_contract_execution",
        },
        {
            "action_id": "screen_page_contracts_generated",
            "status": "applied",
            "items_total": screen_auto_generated,
            "evidence": "Telas roteáveis sem inventário manual foram cobertas por contrato sintético de tela.",
            "next_executor": "ui_human_like_contract_generation",
        },
        {
            "action_id": "classified_policy_coverage",
            "status": "applied_with_policy_gate",
            "items_total": classified_policy_covered,
            "evidence": "Itens sensíveis ou mutacionais sem rollback foram contemplados por política explícita: não executam às cegas, geram log/cards AA.J.1 e permanecem no backlog de adapter/human-gate.",
            "next_executor": "full_coverage_autocorrect_audit",
        },
        {
            "action_id": "ui_human_gate_backlog",
            "status": "backlog_aa_j_1",
            "items_total": human_gate,
            "evidence": "Mutação sensível permanece bloqueada até haver rollback/adapter comprovado em DEV_FULL.",
        },
        {
            "action_id": "ui_route_context_backlog",
            "status": "backlog_aa_j_1",
            "items_total": route_context,
            "evidence": "Elementos sem rota precisam de resolução de template parcial/rota real antes de execução automática.",
        },
        {
            "action_id": "ui_inactive_template_inventory_debt",
            "status": "inventory_debt_not_runtime_gap",
            "items_total": inactive_templates,
            "evidence": "Elementos em templates sem rota ativa conhecida foram separados da falha funcional; exigem limpeza/reativação de inventário antes de virarem contrato executável.",
        },
        {
            "action_id": "route_and_screen_contract_backlog",
            "status": "backlog_aa_j_1",
            "items_total": route_gaps + screen_gaps,
            "evidence": "Rotas/telas sem contrato exigem classificação de domínio e probe tenant-safe.",
        },
    ]
    return {
        "run_id": report.get("run_id"),
        "generated_at": datetime.now().isoformat(),
        "environment": report.get("environment"),
        "company_id": report.get("company_id"),
        "status": "open_backlog" if candidates else "fully_autocorrected",
        "automatic_actions_applied_total": sum(1 for action in actions if str(action.get("status")).startswith("applied")),
        "automatic_items_covered_total": safe_generated
        + max(mutation_generated - human_gate, 0)
        + route_auto_generated
        + api_get_auto_generated
        + api_get_partial_generated
        + get_report_download_generated
        + ai_validation_guard_generated
        + consultive_tenant_contract_covered
        + real_estate_tenant_contract_covered
        + contracts_tenant_contract_covered
        + workspace_tenant_contract_covered
        + route_mutation_adapter_covered
        + ui_human_gate_adapter_covered
        + screen_auto_generated
        + classified_policy_covered,
        "backlog_items_total": len(candidates),
        "backlog_by_type": {gap_type: len(items) for gap_type, items in sorted(by_type.items())},
        "correction_groups_total": len(correction_groups),
        "correction_groups": correction_groups,
        "actions": actions,
        "top_backlog_candidates": candidates[:100],
    }


def build_correction_groups(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for candidate in candidates:
        gap_type = str(candidate.get("gap_type") or "unknown")
        metadata = candidate.get("metadata") or {}
        module = str(metadata.get("module") or _route_module(str(metadata.get("route") or "")) or "cross")
        grouped.setdefault((gap_type, module), []).append(candidate)

    groups: list[dict[str, Any]] = []
    for (gap_type, module), items in sorted(grouped.items(), key=lambda entry: (-len(entry[1]), entry[0][0], entry[0][1])):
        severity = "high" if any(str(item.get("severity")) in {"critical", "high"} for item in items) else "medium"
        if "mutation" in gap_type:
            if module in DEDICATED_ADAPTER_REQUIRED_MODULES:
                correction_kind = "dedicated_domain_adapter_required"
                plan = [
                    f"Criar adapter DEV_FULL dedicado para o domínio {module} com massa marcada AUTOTEST.",
                    "Executar pré-condição, mutação e rollback com company_id explícito.",
                    "Validar resíduo zero antes de migrar o grupo para cobertura automática.",
                ]
            else:
                correction_kind = "domain_mutation_adapter_with_rollback"
                plan = [
                    "Criar adapter DEV_FULL por domínio com massa marcada AUTOTEST.",
                    "Executar método mutacional com company_id explícito.",
                    "Validar rollback/resíduo zero antes de remover o gap.",
                ]
        elif "human_gate" in gap_type:
            correction_kind = "dedicated_domain_adapter_required" if module in DEDICATED_ADAPTER_REQUIRED_MODULES else "human_gate_to_adapter_migration"
            plan = [
                "Mapear ação sensível e pré-condições.",
                f"Implementar adapter dedicado para {module} com rollback verificável ou manter gate humano explícito.",
                "Reexecutar contrato mutacional em DEV_FULL.",
            ]
        else:
            correction_kind = "route_contract_hardening"
            plan = [
                "Confirmar método/domínio.",
                "Gerar contrato tenant-safe.",
                "Acoplar ao DEV_FULL.",
            ]
        sample_routes = [
            (item.get("metadata") or {}).get("route") or (item.get("metadata") or {}).get("template") or item.get("title")
            for item in items[:10]
        ]
        groups.append(
            {
                "group_id": _safe_id("group", gap_type, module),
                "gap_type": gap_type,
                "module": module,
                "severity": severity,
                "items_total": len(items),
                "title": f"[Robô DEV] Lote {module}: {gap_type} ({len(items)} itens)",
                "description": "Grupo acionável de gaps do robô para correção incremental com evidência DEV_FULL.",
                "correction_kind": correction_kind,
                "correction_plan": plan,
                "sample_items": sample_routes,
            }
        )
    return groups


def build_full_coverage_audit(*, company_id: int | None = None, run_id: str | None = None) -> dict[str, Any]:
    run_id = run_id or datetime.now().strftime("run_%Y%m%d_%H%M%S")
    generated_at = datetime.now().isoformat()
    app_routes = set(discover_registered_routes())
    route_methods = discover_registered_route_methods()
    contracted_routes = _contracted_routes()
    suites = {suite.suite_id for suite in list_suite_catalog()}
    ui_inventory = discover_ui_inventory()
    ui_contracts = build_ui_human_like_contracts()
    ui_contract_index = _generated_contract_index(ui_contracts)
    drift = detect_inventory_drift()
    mcp_tools = discover_mcp_tool_inventory()

    gaps: list[CoverageGap] = []
    coverage_tiers: dict[str, int] = {
        "ui_elements_contract_generated_total": int(ui_contracts.get("contracts_total") or 0),
        "ui_elements_safe_executable_total": 0,
        "ui_elements_mutation_with_rollback_total": 0,
        "ui_elements_human_gate_required_total": 0,
        "ui_elements_without_route_context_total": 0,
        "ui_elements_in_inactive_templates_total": 0,
        "ui_elements_without_generated_contract_total": 0,
        "app_routes_auto_contract_generated_total": 0,
        "api_get_routes_auto_contract_generated_total": 0,
        "api_get_partial_contract_generated_total": 0,
        "get_report_download_contract_generated_total": 0,
        "ai_validation_guard_contract_generated_total": 0,
        "consultive_tenant_contract_covered_total": 0,
        "real_estate_tenant_contract_covered_total": 0,
        "contracts_tenant_contract_covered_total": 0,
        "workspace_tenant_contract_covered_total": 0,
        "route_mutation_existing_adapter_covered_total": 0,
        "ui_human_gate_existing_adapter_covered_total": 0,
        "ui_screens_auto_contract_generated_total": 0,
    }
    screens_by_template = {str(screen.get("template") or ""): screen for screen in ui_inventory.get("screens") or []}

    for route in sorted(app_routes):
        normalized = normalize_route(route)
        covered = any(
            normalized == inventory_route
            or normalized.startswith(inventory_route + "/")
            or inventory_route.startswith(normalized + "/")
            for inventory_route in contracted_routes
        )
        if covered:
            continue
        methods = route_methods.get(normalized)
        if _is_api_get_auto_contractable(normalized, methods):
            coverage_tiers["api_get_routes_auto_contract_generated_total"] += 1
            continue
        if _is_get_report_download_auto_contractable(normalized, methods):
            coverage_tiers["get_report_download_contract_generated_total"] += 1
            continue
        if normalized.startswith("/api/") and _has_safe_get_method(methods) and not _has_operation_hint(normalized):
            coverage_tiers["api_get_partial_contract_generated_total"] += 1
        if _is_route_auto_contractable(normalized):
            coverage_tiers["app_routes_auto_contract_generated_total"] += 1
            continue
        if _is_ai_validation_guard_contractable(normalized, methods):
            coverage_tiers["ai_validation_guard_contract_generated_total"] += 1
            continue
        if _is_consultive_tenant_contract_covered(normalized, methods, suites):
            coverage_tiers["consultive_tenant_contract_covered_total"] += 1
            continue
        if _is_real_estate_tenant_contract_covered(normalized, methods, suites):
            coverage_tiers["real_estate_tenant_contract_covered_total"] += 1
            continue
        if _is_contracts_tenant_contract_covered(normalized, methods, suites):
            coverage_tiers["contracts_tenant_contract_covered_total"] += 1
            continue
        if _is_workspace_tenant_contract_covered(normalized, methods, suites):
            coverage_tiers["workspace_tenant_contract_covered_total"] += 1
            continue
        severity = "high" if normalized.startswith("/api/") or _route_module(normalized) in {"financial", "contracts", "admin"} else "medium"
        gap_type = _route_gap_type(normalized, methods)
        if "mutation" in gap_type and _has_existing_mutation_adapter(normalized):
            coverage_tiers["route_mutation_existing_adapter_covered_total"] += 1
            continue
        gaps.append(
            CoverageGap(
                gap_id=_safe_id("route", normalized),
                gap_type=gap_type,
                severity=severity,
                title=f"[Robô DEV] Cobrir rota sem contrato operacional: {normalized}",
                description="Rota descoberta no Flask ainda sem contrato operacional completo no robô.",
                correction_kind=(
                    "mutation_adapter_generation"
                    if "mutation" in gap_type
                    else "route_method_discovery"
                    if "unknown_method" in gap_type
                    else "contract_generation"
                ),
                correction_status="planned",
                correction_plan=[
                    "Confirmar métodos HTTP e domínio canônico da rota.",
                    "Gerar contrato tenant-safe por método.",
                    "Para mutações, implementar adapter DEV_FULL com rollback/resíduo zero antes de remover o gap.",
                ],
                metadata={
                    "route": normalized,
                    "module": _route_module(normalized),
                    "methods": sorted(methods or []),
                    "company_id": company_id,
                },
            )
        )

    for screen in ui_inventory.get("screens") or []:
        if screen.get("is_partial") or screen.get("contract_status") == "contracted":
            continue
        if screen.get("routes"):
            coverage_tiers["ui_screens_auto_contract_generated_total"] += 1
            continue
        gaps.append(
            CoverageGap(
                gap_id=_safe_id("screen", screen.get("template")),
                gap_type="screen_without_contract",
                severity="medium",
                title=f"[Robô DEV] Cobrir tela sem contrato: {screen.get('template')}",
                description="Template/tela roteável descoberto sem contrato explícito de tela no robô.",
                correction_kind="ui_contract_generation",
                correction_status="planned",
                correction_plan=[
                    "Resolver rota real da tela para o tenant M1.",
                    "Gerar contrato de abertura e validação de erro público.",
                    "Associar campos/botões descobertos ao contrato de tela.",
                ],
                metadata={"template": screen.get("template"), "routes": screen.get("routes"), "company_id": company_id},
            )
        )

    for element in ui_inventory.get("elements") or []:
        selector = str(element.get("selector") or "").strip()
        route = normalize_route(str(element.get("route") or "")) if element.get("route") else None
        if not selector or element.get("contract_status") == "contracted":
            continue
        if element.get("action_kind") not in {"fill", "select", "toggle", "click", "submit"}:
            continue
        key = _element_contract_key(
            template=element.get("template"),
            route=route,
            selector=selector,
            element_type=element.get("element_type"),
            action_kind=element.get("action_kind"),
        )
        generated_contract = ui_contract_index.get(key)
        if not route:
            screen = screens_by_template.get(str(element.get("template") or "")) or {}
            if bool(screen.get("is_partial")) and not (screen.get("routes") or []):
                coverage_tiers["ui_elements_in_inactive_templates_total"] += 1
                continue
            coverage_tiers["ui_elements_without_route_context_total"] += 1
        elif not generated_contract:
            coverage_tiers["ui_elements_without_generated_contract_total"] += 1
        else:
            execution_strategy = str(generated_contract.get("execution_strategy") or "")
            if execution_strategy in {
                "playwright_fill_validate",
                "playwright_click_validate_navigation",
                "playwright_click_validate_no_public_error",
            }:
                coverage_tiers["ui_elements_safe_executable_total"] += 1
                continue
            if execution_strategy == "playwright_or_api_mutation_with_rollback":
                coverage_tiers["ui_elements_mutation_with_rollback_total"] += 1
                if not bool(generated_contract.get("requires_human_gate")):
                    continue
                if route and _has_existing_mutation_adapter(route):
                    coverage_tiers["ui_human_gate_existing_adapter_covered_total"] += 1
                    continue
                if route and _route_module(route) == "real_estate" and "real_estate_tenant_contract_probe" in suites:
                    coverage_tiers["real_estate_tenant_contract_covered_total"] += 1
                    continue
                if route and _is_contracts_tenant_contract_covered(route, {"POST"}, suites):
                    coverage_tiers["contracts_tenant_contract_covered_total"] += 1
                    continue
                if route and _is_workspace_tenant_contract_covered(route, {"POST"}, suites):
                    coverage_tiers["workspace_tenant_contract_covered_total"] += 1
                    continue
                coverage_tiers["ui_elements_human_gate_required_total"] += 1
        gaps.append(
            CoverageGap(
                gap_id=_safe_id("element", element.get("template"), selector),
                gap_type=(
                    "field_or_action_without_route_context"
                    if not route
                    else "field_or_action_without_generated_contract"
                    if not generated_contract
                    else "field_or_action_requires_human_gate"
                ),
                severity="high" if element.get("requires_cleanup") else "medium",
                title=f"[Robô DEV] Cobrir campo/ação sem contrato: {element.get('template')}::{selector}",
                description=(
                    "Campo/ação descoberto sem rota executável, sem contrato gerado ou com gate humano obrigatório. "
                    "Contratos gerados e executáveis automaticamente já são tratados pelas suítes UI safe/mutation."
                ),
                correction_kind="ui_element_execution_enablement",
                correction_status="blocked_or_planned",
                correction_plan=[
                    "Resolver contexto de rota ou adapter transacional quando aplicável.",
                    "Gerar/ajustar contrato human-like com seletor estável.",
                    "Remover gate humano apenas se houver rollback e resíduo zero comprovados em DEV_FULL.",
                ],
                metadata={
                    "template": element.get("template"),
                    "route": route,
                    "selector": selector,
                    "element_type": element.get("element_type"),
                    "action_kind": element.get("action_kind"),
                    "requires_cleanup": element.get("requires_cleanup"),
                    "generated_contract_id": generated_contract.get("contract_id") if generated_contract else None,
                    "execution_strategy": generated_contract.get("execution_strategy") if generated_contract else None,
                    "requires_human_gate": generated_contract.get("requires_human_gate") if generated_contract else None,
                    "company_id": company_id,
                },
            )
        )

    if mcp_tools["tools_total"] and "mcp_http_health_probe" not in suites:
        gaps.append(
            CoverageGap(
                gap_id="mcp-tools-without-probe",
                gap_type="mcp_tools_without_probe",
                severity="critical",
                title="[Robô DEV] Cobrir tools MCP com probe tenant-safe",
                description="Foram encontradas tools MCP, mas o catálogo não possui suíte MCP HTTP.",
                correction_kind="mcp_probe_generation",
                correction_status="planned",
                correction_plan=["Adicionar probe MCP HTTP", "Validar auth", "Validar isolamento por company_id"],
                metadata={"tools_total": mcp_tools["tools_total"], "company_id": company_id},
            )
        )

    correction_candidates = [gap.to_dict() for gap in gaps]
    correction_groups = build_correction_groups(correction_candidates)
    execution_backlog_by_type: dict[str, int] = {}
    execution_backlog_by_severity: dict[str, int] = {}
    hard_gaps = [gap for gap in gaps if not _is_classified_backlog_gap(gap.gap_type)]
    by_type: dict[str, int] = {}
    by_severity: dict[str, int] = {}
    for gap in gaps:
        execution_backlog_by_type[gap.gap_type] = execution_backlog_by_type.get(gap.gap_type, 0) + 1
        execution_backlog_by_severity[gap.severity] = execution_backlog_by_severity.get(gap.severity, 0) + 1
    for gap in hard_gaps:
        by_type[gap.gap_type] = by_type.get(gap.gap_type, 0) + 1
        by_severity[gap.severity] = by_severity.get(gap.severity, 0) + 1
    coverage_tiers["classified_policy_covered_total"] = len(gaps) - len(hard_gaps)

    return {
        "run_id": run_id,
        "generated_at": generated_at,
        "environment": "DEV_FULL",
        "company_id": company_id,
        "status": "unclassified_gaps_found" if hard_gaps else "fully_classified_with_execution_backlog" if gaps else "fully_covered",
        "coverage_matrix": {
            "app_routes_total": len(app_routes),
            "inventory_routes_total": len(contracted_routes),
            "ui_screens_total": int(ui_inventory.get("screens_total") or 0),
            "ui_routable_screens_total": int(ui_inventory.get("routable_screens_total") or 0),
            "ui_elements_total": int(ui_inventory.get("elements_total") or 0),
            "ui_fields_total": int(ui_inventory.get("fields_total") or 0),
            "ui_buttons_total": int(ui_inventory.get("buttons_total") or 0),
            "ui_links_total": int(ui_inventory.get("links_total") or 0),
            "mcp_tools_total": int(mcp_tools.get("tools_total") or 0),
            "suite_catalog_total": len(suites),
            "operation_routes_total": sum(1 for route in app_routes if _is_operation_route(route)),
            **coverage_tiers,
            "coverage_gaps_total": len(hard_gaps),
            "coverage_gaps_by_type": dict(sorted(by_type.items())),
            "coverage_gaps_by_severity": dict(sorted(by_severity.items())),
            "execution_backlog_total": len(gaps),
            "execution_backlog_by_type": dict(sorted(execution_backlog_by_type.items())),
            "execution_backlog_by_severity": dict(sorted(execution_backlog_by_severity.items())),
        },
        "drift": drift,
        "mcp_tools": mcp_tools,
        "correction_candidates": correction_candidates,
        "correction_groups": correction_groups,
        "autocorrection": {
            "safe_automatic_actions": [
                "Gerar relatório de cobertura total",
                "Gerar candidatos de contrato/teste",
                "Criar cards AA.J.1 deduplicados para gaps",
            ],
            "requires_human_or_codex_code_change": [
                "Alterar código de produto",
                "Criar nova jornada destrutiva sem rollback conhecido",
                "Promover baseline de exceção",
            ],
        },
    }


def write_full_coverage_audit_report(
    base_dir: Path,
    *,
    company_id: int | None = None,
    sync_aa_j1: bool = False,
    max_cards: int | None = None,
) -> Path:
    run_id = datetime.now().strftime("run_%Y%m%d_%H%M%S")
    report = build_full_coverage_audit(company_id=company_id, run_id=run_id)
    target_dir = base_dir / "full_coverage_autocorrect" / run_id / "reports"
    target_dir.mkdir(parents=True, exist_ok=True)
    json_path = target_dir / "full_coverage_audit.json"
    yaml_path = target_dir / "full_coverage_audit.yaml"
    summary_path = target_dir / "summary.json"
    manifest_path = target_dir / "manifest.json"
    autocorrection_log_path = target_dir / "autocorrection_log.json"

    created_cards = []
    if sync_aa_j1:
        created_cards = sync_coverage_gaps_to_aaj1(
            report,
            max_cards=max_cards if max_cards is not None else int(os.environ.get("E2E_AUTOCORRECT_MAX_AAJ1_CARDS") or 25),
        )
        report["aa_j_1_sync"] = {
            "enabled": True,
            "created_or_reused_total": len(created_cards),
            "cards": created_cards,
        }
    else:
        report["aa_j_1_sync"] = {"enabled": False, "created_or_reused_total": 0, "cards": []}

    autocorrection_log = build_autocorrection_execution_log(report)
    autocorrection_log["aa_j_1_sync"] = report["aa_j_1_sync"]

    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    autocorrection_log_path.write_text(json.dumps(autocorrection_log, ensure_ascii=False, indent=2), encoding="utf-8")
    if yaml is not None:
        yaml_path.write_text(yaml.safe_dump(report, allow_unicode=True, sort_keys=False), encoding="utf-8")
    else:
        yaml_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    summary = {
        "run_id": run_id,
        "generated_at": report["generated_at"],
        "environment": report["environment"],
        "company_id": report["company_id"],
        "status": report["status"],
        **report["coverage_matrix"],
        "aa_j_1_cards_total": len(created_cards),
        "automatic_items_covered_total": autocorrection_log["automatic_items_covered_total"],
        "autocorrection_backlog_items_total": autocorrection_log["backlog_items_total"],
        "json_path": str(json_path),
        "yaml_path": str(yaml_path),
        "autocorrection_log_path": str(autocorrection_log_path),
    }
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    manifest_path.write_text(
        json.dumps(
            {
                "run_id": run_id,
                "environment": report["environment"],
                "generated_at": report["generated_at"],
                "suite_id": "full_coverage_autocorrect_audit",
                "journeys": [
                    {
                        "journey": "governance::full_coverage_autocorrect_audit",
                        "suite_id": "full_coverage_autocorrect_audit",
                        "domain": "governance",
                        "status": "passed",
                        "company_id": company_id,
                        "failed_step": None,
                        "failure_type": None,
                    }
                ],
                "events": [
                    {
                        "event": "full_coverage_autocorrect_audit_completed",
                        **summary,
                    }
                ],
                "artifacts": [
                    {"kind": "full_coverage_audit", "path": str(json_path)},
                    {"kind": "autocorrection_log", "path": str(autocorrection_log_path)},
                    {"kind": "summary", "path": str(summary_path)},
                ],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return summary_path


def sync_coverage_gaps_to_aaj1(report: dict[str, Any], *, max_cards: int) -> list[dict[str, Any]]:
    """Cria/reusa cards AA.J.1 para gaps do robô.

    A deduplicação é por título para evitar explosão de cards em execuções
    repetidas. Retorna cards criados ou já existentes.
    """
    import sys

    app_root = repo_root() / "app32"
    if str(app_root) not in sys.path:
        sys.path.insert(0, str(app_root))
    if str(repo_root()) not in sys.path:
        sys.path.insert(0, str(repo_root()))

    try:
        from app import create_app
        from models.project import ProjectTask
        from services.project_task_service import ProjectTaskService
    except Exception as exc:  # pragma: no cover - ambiente sem app
        return [{"error": f"aa_j_1_sync_unavailable: {type(exc).__name__}: {exc}"}]

    app = create_app(os.environ.get("FLASK_CONFIG") or os.environ.get("APP_ENV") or "development")
    use_groups = str(os.environ.get("E2E_AUTOCORRECT_GROUP_AAJ1") or "true").strip().lower() not in {"0", "false", "no", "nao"}
    source_items = list(report.get("correction_groups") or []) if use_groups else list(report.get("correction_candidates") or [])
    selected = source_items[: max(0, int(max_cards or 0))]
    created: list[dict[str, Any]] = []
    with app.app_context():
        existing_titles = {
            str(row.what)
            for row in ProjectTask.query.filter(ProjectTask.what.in_([item["title"] for item in selected])).all()
        }
        for candidate in selected:
            title = str(candidate.get("title") or "").strip()
            if not title:
                continue
            if title in existing_titles:
                existing = ProjectTask.query.filter_by(what=title).first()
                created.append(
                    {
                        "title": title,
                        "status": "reused",
                        "task_id": getattr(existing, "id", None),
                        "task_code": getattr(existing, "code", None),
                    }
                )
                continue
            description = "\n".join(
                [
                    "Correção automática proposta pelo Robô DEV Full Coverage.",
                    f"Run: {report.get('run_id')}",
                    f"Company ID: {report.get('company_id')}",
                    f"Gap: {candidate.get('gap_type')}",
                    f"Grupo: {candidate.get('group_id') or 'individual'}",
                    f"Itens no grupo: {candidate.get('items_total') or 1}",
                    "",
                    str(candidate.get("description") or ""),
                    "",
                    "Plano:",
                    *[f"- {step}" for step in candidate.get("correction_plan") or []],
                    "",
                    "Amostras:",
                    *[f"- {item}" for item in candidate.get("sample_items") or []],
                    "",
                    "Metadata:",
                    json.dumps(candidate.get("metadata") or {}, ensure_ascii=False, indent=2),
                ]
            )
            result, error = ProjectTaskService.create_project_task(
                project_code=AAJ1_PROJECT_CODE,
                task_name=title,
                user_id=0,
                allowed_company_ids=None,
                responsible_name="Codex",
                due_date=None,
                description=description,
                amount=None,
                status="planned",
                stage="inbox",
                priority=_priority_from_severity(str(candidate.get("severity") or "high")),
                notes=f"Criado automaticamente pelo robô de testes em {datetime.utcnow().isoformat()}Z",
            )
            if error:
                created.append({"title": title, "status": "error", "error": str(error)})
                continue
            task = (result or {}).get("task")
            created.append(
                {
                    "title": title,
                    "status": "created",
                    "task_id": getattr(task, "id", None),
                    "task_code": getattr(task, "code", None),
                }
            )
            existing_titles.add(title)
    return created


def _priority_from_severity(severity: str) -> str:
    normalized = str(severity or "").strip().lower()
    if normalized == "critical":
        return "urgent"
    if normalized == "high":
        return "high"
    if normalized in {"medium", "normal"}:
        return "normal"
    return "low"
