from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


def inventory_path() -> Path:
    return Path(__file__).resolve().parent / "inventory.yaml"


def load_inventory() -> dict[str, Any]:
    data = yaml.safe_load(inventory_path().read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Inventory E2E inválido: raiz deve ser objeto.")
    return data


def iter_inventory_items() -> list[dict[str, Any]]:
    data = load_inventory()
    modules = data.get("modules") or []
    items: list[dict[str, Any]] = []
    for module in modules:
        for item in module.get("items") or []:
            normalized = dict(item)
            normalized["module"] = module.get("name")
            normalized["criticality"] = module.get("criticality")
            items.append(normalized)
    return items
