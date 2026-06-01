from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from app32.tests.e2e.catalog.drift_detector import discover_registered_routes, normalize_route, routes_compatible
from app32.tests.e2e.catalog.inventory import iter_inventory_items


def _guess_module(route: str) -> str:
    normalized = normalize_route(route)
    if normalized == "/login" or normalized.startswith("/portal"):
        return "auth"
    if normalized.startswith("/my-work"):
        return "workspace"
    if normalized.startswith("/meetings"):
        return "meetings"
    if normalized.startswith("/api-mcp") or normalized.startswith("/channels") or normalized.startswith("/api/integrations"):
        return "integrations"
    if "work-journey" in normalized:
        return "work_journey"
    if normalized.startswith("/processes") or "/processes/" in normalized or normalized.startswith("/api/processes"):
        return "processes"
    if normalized.startswith("/financial"):
        return "financial"
    if normalized.startswith("/api/configs/qa/e2e") or normalized.startswith("/qa/e2e"):
        return "qa"
    return "cross"


def _guess_actions(route: str) -> list[str]:
    normalized = normalize_route(route)
    actions: list[str] = []
    if any(token in normalized for token in ("/export-pdf", "/export-xlsx", "/report")):
        actions.append("emitir_relatorio")
    if any(token in normalized for token in ("/bpmn-diagram", "/save", "/publish", "/finalizar", "/execucao")):
        actions.append("salvar")
    if normalized.startswith("/api/"):
        actions.append("consultar")
    if normalized.endswith("/bpmn-modeler"):
        actions.extend(["abrir_tela", "salvar"])
    if not actions and not normalized.startswith("/api/"):
        actions.append("abrir_tela")
    return sorted(set(actions))


def _looks_like_screen(route: str) -> bool:
    normalized = normalize_route(route)
    return not normalized.startswith("/api/")


def build_inventory_candidates() -> dict[str, Any]:
    inventory_items = iter_inventory_items()
    inventory_routes = [normalize_route(item["route"]) for item in inventory_items if item.get("route")]
    discovered_routes = sorted(set(discover_registered_routes()))

    candidates: list[dict[str, Any]] = []
    for route in discovered_routes:
        if any(routes_compatible(route, inventory_route) for inventory_route in inventory_routes):
            continue
        candidates.append(
            {
                "route": route,
                "module": _guess_module(route),
                "surface_type": "screen" if _looks_like_screen(route) else "route",
                "suggested_actions": _guess_actions(route),
                "system_description": "Rota descoberta automaticamente no código do app.",
                "coverage_description": "Precisa entrar no inventário oficial e ganhar teste da ação principal.",
            }
        )

    modules = sorted({candidate["module"] for candidate in candidates})
    return {
        "generated_at": datetime.now().isoformat(),
        "inventory_routes_total": len(inventory_routes),
        "discovered_routes_total": len(discovered_routes),
        "candidate_routes_total": len(candidates),
        "modules_detected": modules,
        "candidates": candidates,
    }


def write_inventory_candidates_report(base_dir: Path) -> Path:
    report = build_inventory_candidates()
    run_id = datetime.now().strftime("run_%Y%m%d_%H%M%S")
    target_dir = base_dir / "inventory_scan" / run_id / "reports"
    target_dir.mkdir(parents=True, exist_ok=True)

    json_path = target_dir / "inventory_candidates.json"
    yaml_path = target_dir / "inventory_candidates.yaml"
    summary_path = target_dir / "summary.json"

    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    yaml_path.write_text(yaml.safe_dump(report, allow_unicode=True, sort_keys=False), encoding="utf-8")
    summary_path.write_text(
        json.dumps(
            {
                "run_id": run_id,
                "generated_at": report["generated_at"],
                "candidate_routes_total": report["candidate_routes_total"],
                "inventory_routes_total": report["inventory_routes_total"],
                "discovered_routes_total": report["discovered_routes_total"],
                "modules_detected": report["modules_detected"],
                "json_path": str(json_path),
                "yaml_path": str(yaml_path),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return summary_path
