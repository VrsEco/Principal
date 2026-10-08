"""Relatório de drift do mcp-versus (Fase 4, modo "só compara").

Compara as fontes que hoje definem o que o MCP expõe e o que cada usuário pode
fazer: catálogo de capabilities, listas fixas do registro de surfaces, matriz de
permissões, playbooks e RBAC por domínio. Não altera nada e não é importado pelo
runtime; serve ao teste de contrato e ao comando ``scripts/qa/mcp_drift_report.py``.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any


def _published_static_names(registry: Any) -> set[str]:
    """Nomes que o registro publica por listas fixas (PILOT_* e STATUS_*)."""
    names: set[str] = set()
    for attr in dir(registry):
        if not attr.isupper() or not attr.endswith("TOOL_NAMES"):
            continue
        if not (attr.startswith("PILOT_") or attr.startswith("STATUS_")):
            continue
        value = getattr(registry, attr)
        if isinstance(value, (set, frozenset, tuple, list)):
            names |= {item for item in value if isinstance(item, str)}
    return names


def compute_drift() -> dict[str, Any]:
    from src.core import mcp_surface_registry as registry
    from src.intelligence.mcp_contracts.permission_matrix import APP32_PERMISSION_MATRIX_MANIFEST
    from src.intelligence.mcp_contracts.playbooks import APP32_SURFACE_PLAYBOOKS_MANIFEST
    from src.intelligence.security import tenant_rbac
    from src.intelligence.tool_catalog import catalog

    tools = catalog.get_capability_manifest(include_tools=True).get("tools", [])
    by_name = {tool["name"]: tool for tool in tools}
    catalog_domains = {tool["domain"] for tool in tools}

    matrix_domains: set[str] = set()
    for group in (APP32_PERMISSION_MATRIX_MANIFEST.matrices, APP32_PERMISSION_MATRIX_MANIFEST.overlay_matrices):
        for matrix in group or ():
            matrix_domains |= {rule.domain for rule in matrix.domains}

    playbook_domains: set[str] = set()
    for playbook in APP32_SURFACE_PLAYBOOKS_MANIFEST.playbooks:
        playbook_domains |= set(playbook.allowed_domains)

    rbac_domains = set(tenant_rbac.DOMAIN_MATRIX)
    published = _published_static_names(registry)

    per_domain: dict[str, dict[str, int]] = defaultdict(lambda: {"total": 0, "published": 0})
    for tool in tools:
        per_domain[tool["domain"]]["total"] += 1
        if tool["name"] in published:
            per_domain[tool["domain"]]["published"] += 1

    scope_combinations = Counter(tuple(sorted(tool.get("scopes") or ())) for tool in tools)

    return {
        "catalog_total": len(tools),
        "published_static": len(published & set(by_name)),
        "published_not_in_catalog": sorted(published - set(by_name)),
        "domains_missing_in_permission_matrix": sorted(catalog_domains - matrix_domains),
        "domains_missing_in_playbooks": sorted(catalog_domains - playbook_domains),
        "domains_missing_in_tenant_rbac": sorted(catalog_domains - rbac_domains),
        "tools_without_permissions": sorted(
            t["name"] for t in tools
            if not t.get("permissions") and "no_permission_required" not in (t.get("tags") or ())
        ),
        "tools_explicitly_public": sorted(
            t["name"] for t in tools
            if not t.get("permissions") and "no_permission_required" in (t.get("tags") or ())
        ),
        "scope_combinations": len(scope_combinations),
        "per_domain": {domain: dict(counts) for domain, counts in sorted(per_domain.items())},
    }


def render_report(data: dict[str, Any]) -> str:
    total = data["catalog_total"] or 1
    lines = [
        "# Drift do mcp-versus (modo só compara)",
        "",
        f"- Capabilities no catálogo: {data['catalog_total']}",
        f"- Publicáveis pelas listas fixas do registro: {data['published_static']} "
        f"({100 * data['published_static'] / total:.0f}%)",
        f"- Combinações distintas de escopos entre as tools: {data['scope_combinations']}",
        "",
        "## Divergências entre fontes",
        f"- Domínios do catálogo fora da matriz de permissões: {data['domains_missing_in_permission_matrix']}",
        f"- Domínios do catálogo fora dos playbooks: {data['domains_missing_in_playbooks']}",
        f"- Domínios do catálogo fora do RBAC por domínio: {data['domains_missing_in_tenant_rbac']}",
        f"- Tools sem permissão declarada: {data['tools_without_permissions']}",
        f"- Tools explicitamente públicas (sem permissão, por decisão): {data['tools_explicitly_public']}",
        f"- Nomes do registro ausentes do catálogo: {data['published_not_in_catalog']}",
        "",
        "## Exposição por domínio (catálogo × publicáveis no mcp-versus)",
        "| domínio | capabilities | publicáveis |",
        "|---|---:|---:|",
    ]
    for domain, counts in data["per_domain"].items():
        lines.append(f"| {domain} | {counts['total']} | {counts['published']} |")
    return "\n".join(lines)
