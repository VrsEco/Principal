"""Valida estrutura e encadeamento básico de catálogo de processos em JSON."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


LEVELS = ("area", "macroprocess", "process", "activity")
PARENT = {"area": None, "macroprocess": "area", "process": "macroprocess", "activity": "process"}


def validate(payload: dict[str, Any]) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    company_id = payload.get("company_id")
    if not isinstance(company_id, int) or isinstance(company_id, bool) or company_id <= 0:
        errors.append("company_id deve ser inteiro positivo")
    items = payload.get("items")
    if not isinstance(items, list):
        return errors + ["items deve ser uma lista"], warnings

    codes = [item.get("code") for item in items if isinstance(item, dict)]
    duplicates = [code for code, count in Counter(codes).items() if code and count > 1]
    for code in duplicates:
        errors.append(f"código duplicado: {code}")
    by_code = {item.get("code"): item for item in items if isinstance(item, dict) and item.get("code")}
    children = Counter(item.get("parent_code") for item in items if isinstance(item, dict))

    for index, item in enumerate(items, start=1):
        if not isinstance(item, dict):
            errors.append(f"item {index} deve ser objeto")
            continue
        code = item.get("code") or f"item {index}"
        level = item.get("level")
        if level not in LEVELS:
            errors.append(f"{code}: nível inválido: {level}")
            continue
        if not str(item.get("name") or "").strip():
            errors.append(f"{code}: nome obrigatório")
        parent_code = item.get("parent_code")
        expected = PARENT[level]
        if expected is None:
            if parent_code:
                errors.append(f"{code}: área não deve ter parent_code")
        else:
            parent = by_code.get(parent_code)
            if not parent:
                errors.append(f"{code}: parent_code inexistente: {parent_code}")
            elif parent.get("level") != expected:
                errors.append(f"{code}: pai deve ser {expected}, encontrado {parent.get('level')}")
        if level in {"macroprocess", "process"} and not item.get("receiver"):
            warnings.append(f"{code}: recebedor não informado")
        if level == "process":
            for field in ("trigger", "input", "output"):
                if not item.get(field):
                    warnings.append(f"{code}: {field} não informado")
        if level != "activity" and children[code] == 0:
            warnings.append(f"{code}: sem decomposição no nível seguinte")
    return errors, warnings


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("catalog")
    args = parser.parse_args()
    path = Path(args.catalog)
    payload = json.loads(path.read_text(encoding="utf-8"))
    errors, warnings = validate(payload)
    for item in warnings:
        print(f"WARN: {item}")
    for item in errors:
        print(f"ERROR: {item}")
    if errors:
        raise SystemExit(1)
    print(f"OK: {path} ({len(payload.get('items', []))} itens, {len(warnings)} alertas)")


if __name__ == "__main__":
    main()
