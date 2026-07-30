from __future__ import annotations

from typing import Iterable

CANONICAL_TOOL_DOMAINS: tuple[str, ...] = (
    "routine",
    "projects",
    "processes",
    "meetings",
    "strategy",
    "consultive",
    "real_estate_auctions",
    "finance",
    "analytics",
    "workload",
    "identity_self_service",
    "identity_admin",
    "governance",
    "operations",
    "admin",
    "diagnostics",
    "knowledge",
    "general",
)

TOOL_DOMAIN_ALIASES: dict[str, str] = {
    "work": "routine",
    "tasks": "routine",
    "worklog": "routine",
    "process": "processes",
    "workflow": "processes",
    "auction": "real_estate_auctions",
    "auctions": "real_estate_auctions",
    "real_estate": "real_estate_auctions",
    "leiloes": "real_estate_auctions",
    "leilões": "real_estate_auctions",
    "identity": "identity_self_service",
    "my_profile": "identity_self_service",
    "my_companies": "identity_self_service",
    "my_contacts": "identity_self_service",
}

TOOL_DOMAIN_FAMILY_ALIASES: dict[str, tuple[str, ...]] = {
    "identity": ("identity_self_service", "identity_admin"),
    "identity_self_service": ("identity_admin",),
}


def normalize_tool_domain(domain: str | None) -> str | None:
    normalized = str(domain or "").strip().lower()
    if not normalized:
        return None
    return TOOL_DOMAIN_ALIASES.get(normalized, normalized)


def expand_tool_domain_aliases(domains: Iterable[str]) -> set[str]:
    expanded: set[str] = set()
    for raw_domain in domains:
        normalized = normalize_tool_domain(raw_domain)
        if not normalized:
            continue
        expanded.add(normalized)
        expanded.update(TOOL_DOMAIN_FAMILY_ALIASES.get(normalized, ()))
        if normalized == "routine":
            expanded.update({"work", "tasks", "worklog"})
        elif normalized == "processes":
            expanded.update({"process", "workflow"})
    return expanded

