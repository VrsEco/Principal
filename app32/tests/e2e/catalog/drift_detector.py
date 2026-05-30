from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

from app32.tests.e2e.catalog.inventory import iter_inventory_items
from app32.tests.e2e.catalog.suite_catalog import list_suite_catalog


DECORATOR_ROUTE_PATTERN = re.compile(r'@[^\n]+?\.route\([\'\"]([^\'\"]+)')
RESOURCE_CALL_PATTERN = re.compile(r'add_resource\((.*?)\)', re.DOTALL)
STRING_LITERAL_PATTERN = re.compile(r'[\'\"]([^\'\"]+)[\'\"]')
BLUEPRINT_PREFIX_PATTERN = re.compile(r'Blueprint\([^\n]+?url_prefix\s*=\s*[\'\"]([^\'\"]+)')
PARAM_PATTERN = re.compile(r"<(?:(?:int|string|float|uuid|path):)?([^>]+)>")
IGNORED_PARTS = {"archive", "docs", "tests", "__pycache__", ".agent"}
GOVERNED_PREFIXES = (
    "/portal",
    "/my-work",
    "/meetings",
    "/api-mcp",
    "/channels",
    "/work-journey",
    "/companies/<company_id>/work-journey",
    "/api/companies/<company_id>/work-journey",
)


def normalize_route(route: str) -> str:
    normalized = PARAM_PATTERN.sub(lambda match: f"<{match.group(1)}>", str(route or "").strip())
    if not normalized.startswith("/"):
        normalized = "/" + normalized
    if normalized != "/" and normalized.endswith("/"):
        normalized = normalized.rstrip("/")
    return normalized


def routes_compatible(route_a: str, route_b: str) -> bool:
    normalized_a = normalize_route(route_a)
    normalized_b = normalize_route(route_b)
    segments_a = [segment for segment in normalized_a.strip("/").split("/") if segment]
    segments_b = [segment for segment in normalized_b.strip("/").split("/") if segment]
    if len(segments_a) != len(segments_b):
        return False
    for segment_a, segment_b in zip(segments_a, segments_b):
        if segment_a.startswith("<") and segment_a.endswith(">"):
            continue
        if segment_b.startswith("<") and segment_b.endswith(">"):
            continue
        if segment_a != segment_b:
            return False
    return True


def _iter_python_sources() -> list[Path]:
    repo_root = Path(__file__).resolve().parents[4]
    app_root = repo_root / "app32"
    paths: list[Path] = []
    for path in app_root.rglob("*.py"):
        if any(part in IGNORED_PARTS for part in path.parts):
            continue
        if path.name.startswith(".codex_temp"):
            continue
        paths.append(path)
    return paths


def _join_route(prefix: str, route: str) -> str:
    prefix = str(prefix or "").rstrip("/")
    route = str(route or "")
    if not prefix:
        return normalize_route(route)
    if route.startswith(prefix + "/") or route == prefix:
        return normalize_route(route)
    return normalize_route(f"{prefix}/{route.lstrip('/')}" )


def _extract_resource_routes(body: str) -> list[str]:
    discovered: list[str] = []
    for match in RESOURCE_CALL_PATTERN.finditer(body):
        call_body = match.group(1)
        quoted_values = STRING_LITERAL_PATTERN.findall(call_body)
        discovered.extend(
            normalize_route(value)
            for value in quoted_values
            if str(value).strip().startswith("/")
        )
    return discovered


def discover_registered_routes() -> list[str]:
    discovered: list[str] = []
    for path in _iter_python_sources():
        body = path.read_text(encoding="utf-8", errors="ignore")
        prefixes = [match.group(1) for match in BLUEPRINT_PREFIX_PATTERN.finditer(body)]
        decorator_routes = [match.group(1) for match in DECORATOR_ROUTE_PATTERN.finditer(body)]
        if prefixes:
            for route in decorator_routes:
                for prefix in prefixes:
                    discovered.append(_join_route(prefix, route))
        else:
            discovered.extend(normalize_route(route) for route in decorator_routes)
        discovered.extend(_extract_resource_routes(body))
    return sorted(set(discovered))


def _load_baseline() -> dict[str, list[str]]:
    baseline_path = Path(__file__).with_name("drift_baseline.yaml")
    if not baseline_path.exists():
        return {"accepted_uncovered_routes": [], "accepted_inventory_routes_not_found": []}
    payload = yaml.safe_load(baseline_path.read_text(encoding="utf-8")) or {}
    return {
        "accepted_uncovered_routes": [normalize_route(route) for route in payload.get("accepted_uncovered_routes") or []],
        "accepted_inventory_routes_not_found": [normalize_route(route) for route in payload.get("accepted_inventory_routes_not_found") or []],
    }


def _is_governed_route(route: str) -> bool:
    if route == "/login":
        return True
    return any(route == prefix or route.startswith(prefix + "/") for prefix in GOVERNED_PREFIXES)


def _is_route_covered(route: str, inventory_routes: set[str]) -> bool:
    return any(
        routes_compatible(route, inventory_route)
        or route.startswith(normalize_route(inventory_route) + "/")
        or normalize_route(inventory_route).startswith(normalize_route(route) + "/")
        for inventory_route in inventory_routes
    )


def detect_inventory_drift() -> dict[str, Any]:
    inventory_routes = {normalize_route(item["route"]) for item in iter_inventory_items() if item.get("route")}
    app_routes = set(discover_registered_routes())
    suites = {suite.suite_id for suite in list_suite_catalog()}
    baseline = _load_baseline()

    governed_routes = {route for route in app_routes if _is_governed_route(route)}
    uncovered = sorted(route for route in governed_routes if not _is_route_covered(route, inventory_routes))
    backlog_inventory = sorted(
        route for route in inventory_routes
        if not any(routes_compatible(route, app_route) for app_route in app_routes)
    )

    accepted_uncovered = set(baseline["accepted_uncovered_routes"])
    accepted_inventory_missing = set(baseline["accepted_inventory_routes_not_found"])

    unexpected_uncovered = sorted(route for route in uncovered if route not in accepted_uncovered)
    unexpected_inventory_missing = sorted(route for route in backlog_inventory if route not in accepted_inventory_missing)

    return {
        "inventory_routes_total": len(inventory_routes),
        "app_routes_total": len(app_routes),
        "suite_catalog_total": len(suites),
        "governed_routes_total": len(governed_routes),
        "critical_routes_without_inventory": unexpected_uncovered,
        "accepted_critical_routes_without_inventory": sorted(accepted_uncovered.intersection(uncovered)),
        "inventory_routes_not_found_in_app": unexpected_inventory_missing,
        "accepted_inventory_routes_not_found": sorted(accepted_inventory_missing.intersection(backlog_inventory)),
        "status": "drift" if unexpected_uncovered or unexpected_inventory_missing else "aligned",
    }
