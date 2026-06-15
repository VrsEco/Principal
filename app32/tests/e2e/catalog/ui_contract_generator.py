from __future__ import annotations

import hashlib
import json
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    import yaml
except ModuleNotFoundError:  # pragma: no cover - fallback para runtime enxuto
    yaml = None

from app32.tests.e2e.catalog.ui_inventory_discovery import discover_ui_inventory


HIGH_RISK_HINTS = ("delete", "excluir", "remove", "remover", "baixar", "aprovar", "cancel", "cancelar")
PROCESSING_HINTS = ("gerar", "processar", "importar", "export", "pdf", "xlsx", "relatorio", "report")
SAVE_HINTS = ("save", "salvar", "submit", "criar", "create", "editar", "alterar")


@dataclass(frozen=True)
class UIHumanLikeContract:
    contract_id: str
    screen_id: str
    template: str
    route: str | None
    selector: str
    label: str | None
    element_type: str
    action_kind: str
    risk_level: str
    priority: str
    coverage_state: str
    execution_strategy: str
    data_strategy: str
    confirmation_strategy: str
    cleanup_strategy: str
    requires_company_id: bool
    requires_human_gate: bool
    source_contract_status: str


def _stable_contract_id(element: dict[str, Any]) -> str:
    raw = "|".join(
        str(element.get(key) or "")
        for key in ("screen_id", "template", "route", "selector", "element_type", "action_kind")
    )
    digest = hashlib.sha1(raw.encode("utf-8")).hexdigest()[:14]
    return f"ui_{digest}"


def _haystack(element: dict[str, Any]) -> str:
    return " ".join(
        str(element.get(key) or "").lower()
        for key in ("selector", "label", "element_type", "action_kind", "template", "route")
    )


def _risk_level(element: dict[str, Any]) -> str:
    haystack = _haystack(element)
    if element.get("requires_confirmation") or any(hint in haystack for hint in HIGH_RISK_HINTS):
        return "high"
    if element.get("requires_cleanup") or any(hint in haystack for hint in PROCESSING_HINTS):
        return "medium"
    return "low"


def _priority(element: dict[str, Any], risk_level: str) -> str:
    if risk_level == "high":
        return "p0"
    if element.get("requires_cleanup") or risk_level == "medium":
        return "p1"
    if element.get("requires_data"):
        return "p2"
    return "p3"


def _execution_strategy(element: dict[str, Any]) -> str:
    action = str(element.get("action_kind") or "")
    if action in {"fill", "select", "toggle"}:
        return "playwright_fill_validate"
    if action == "navigate":
        return "playwright_click_validate_navigation"
    if element.get("requires_cleanup"):
        return "playwright_or_api_mutation_with_rollback"
    return "playwright_click_validate_no_public_error"


def _data_strategy(element: dict[str, Any]) -> str:
    if not element.get("requires_data"):
        return "no_input_data"
    element_type = str(element.get("element_type") or "")
    if element_type == "select":
        return "select_first_safe_option"
    if "date" in element_type:
        return "synthetic_date_within_current_period"
    if "email" in element_type:
        return "synthetic_email_example_invalid"
    if "number" in element_type:
        return "synthetic_numeric_value"
    return "synthetic_text_marked_autoe2e"


def _confirmation_strategy(element: dict[str, Any], risk_level: str) -> str:
    if risk_level == "high":
        return "require_explicit_devfull_company_and_human_gate"
    if element.get("requires_confirmation"):
        return "confirm_modal_in_devfull_only"
    return "no_confirmation_expected"


def _cleanup_strategy(element: dict[str, Any], risk_level: str) -> str:
    if element.get("requires_cleanup") or risk_level in {"high", "medium"}:
        return "rollback_or_delete_and_residue_zero"
    return "no_persistent_mutation_expected"


def build_ui_human_like_contracts() -> dict[str, Any]:
    inventory = discover_ui_inventory()
    contracts: list[UIHumanLikeContract] = []
    for element in inventory.get("elements") or []:
        risk = _risk_level(element)
        contracts.append(
            UIHumanLikeContract(
                contract_id=_stable_contract_id(element),
                screen_id=str(element.get("screen_id") or ""),
                template=str(element.get("template") or ""),
                route=element.get("route"),
                selector=str(element.get("selector") or ""),
                label=element.get("label"),
                element_type=str(element.get("element_type") or ""),
                action_kind=str(element.get("action_kind") or ""),
                risk_level=risk,
                priority=_priority(element, risk),
                coverage_state="contracted_generated",
                execution_strategy=_execution_strategy(element),
                data_strategy=_data_strategy(element),
                confirmation_strategy=_confirmation_strategy(element, risk),
                cleanup_strategy=_cleanup_strategy(element, risk),
                requires_company_id=bool(element.get("requires_cleanup") or risk in {"high", "medium"}),
                requires_human_gate=bool(risk == "high"),
                source_contract_status=str(element.get("contract_status") or "discovered"),
            )
        )

    risk_counts = Counter(item.risk_level for item in contracts)
    priority_counts = Counter(item.priority for item in contracts)
    strategy_counts = Counter(item.execution_strategy for item in contracts)
    rollback_contracts = [item for item in contracts if item.cleanup_strategy == "rollback_or_delete_and_residue_zero"]
    return {
        "generated_at": datetime.now().isoformat(),
        "contracts_total": len(contracts),
        "screens_total": inventory.get("screens_total"),
        "elements_total": inventory.get("elements_total"),
        "risk_counts": dict(sorted(risk_counts.items())),
        "priority_counts": dict(sorted(priority_counts.items())),
        "execution_strategy_counts": dict(sorted(strategy_counts.items())),
        "rollback_required_total": len(rollback_contracts),
        "human_gate_required_total": sum(1 for item in contracts if item.requires_human_gate),
        "company_id_required_total": sum(1 for item in contracts if item.requires_company_id),
        "contracts": [asdict(item) for item in contracts],
        "p0_contracts": [asdict(item) for item in contracts if item.priority == "p0"][:300],
        "rollback_contracts": [asdict(item) for item in rollback_contracts[:500]],
    }


def write_ui_contracts_report(base_dir: Path) -> Path:
    report = build_ui_human_like_contracts()
    run_id = datetime.now().strftime("run_%Y%m%d_%H%M%S")
    target_dir = base_dir / "ui_contracts" / run_id / "reports"
    target_dir.mkdir(parents=True, exist_ok=True)

    json_path = target_dir / "ui_contracts.json"
    yaml_path = target_dir / "ui_contracts.yaml"
    summary_path = target_dir / "summary.json"
    manifest_path = target_dir / "manifest.json"

    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    if yaml is not None:
        yaml_path.write_text(yaml.safe_dump(report, allow_unicode=True, sort_keys=False), encoding="utf-8")
    else:
        yaml_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    summary = {
        "run_id": run_id,
        "generated_at": report["generated_at"],
        "contracts_total": report["contracts_total"],
        "screens_total": report["screens_total"],
        "elements_total": report["elements_total"],
        "risk_counts": report["risk_counts"],
        "priority_counts": report["priority_counts"],
        "execution_strategy_counts": report["execution_strategy_counts"],
        "rollback_required_total": report["rollback_required_total"],
        "human_gate_required_total": report["human_gate_required_total"],
        "company_id_required_total": report["company_id_required_total"],
        "json_path": str(json_path),
        "yaml_path": str(yaml_path),
    }
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    manifest_path.write_text(
        json.dumps(
            {
                "run_id": run_id,
                "environment": "DEV_FULL",
                "generated_at": report["generated_at"],
                "suite_id": "ui_human_like_contract_generation",
                "journeys": [
                    {
                        "journey": "governance::ui_human_like_contract_generation",
                        "suite_id": "ui_human_like_contract_generation",
                        "domain": "governance",
                        "status": "passed",
                        "failed_step": None,
                        "failure_type": None,
                    }
                ],
                "events": [{"event": "ui_human_like_contracts_generated", **summary}],
                "artifacts": [{"kind": "ui_contracts", "path": "ui_contracts.json"}],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return summary_path
