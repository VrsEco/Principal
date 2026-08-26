"""Gerencia o repertório versionado de casos da skill."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


LIBRARY = Path(__file__).resolve().parents[1] / "references" / "cases.json"
VALID_STATUS = {"candidate", "reference", "retired"}
REQUIRED = {
    "id",
    "title",
    "version",
    "status",
    "tags",
    "source_refs",
    "reusable_patterns",
    "context_specific",
    "known_corrections",
    "superseded_by",
}


def load(path: Path = LIBRARY) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def save(data: dict[str, Any], path: Path = LIBRARY) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def validate(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if data.get("schema_version") != 1:
        errors.append("schema_version deve ser 1")
    cases = data.get("cases")
    if not isinstance(cases, list):
        return errors + ["cases deve ser uma lista"]
    ids: set[str] = set()
    by_id: dict[str, dict[str, Any]] = {}
    for index, case in enumerate(cases, start=1):
        if not isinstance(case, dict):
            errors.append(f"caso {index} deve ser objeto")
            continue
        missing = REQUIRED - set(case)
        if missing:
            errors.append(f"caso {index}: campos ausentes {sorted(missing)}")
        case_id = case.get("id")
        if not isinstance(case_id, str) or not case_id.strip():
            errors.append(f"caso {index}: id inválido")
            continue
        if case_id in ids:
            errors.append(f"id duplicado: {case_id}")
        ids.add(case_id)
        by_id[case_id] = case
        if case.get("status") not in VALID_STATUS:
            errors.append(f"{case_id}: status inválido")
        for field in ("tags", "source_refs", "reusable_patterns", "context_specific", "known_corrections"):
            if not isinstance(case.get(field), list):
                errors.append(f"{case_id}: {field} deve ser lista")
    for case_id, case in by_id.items():
        replacement = case.get("superseded_by")
        if replacement and replacement not in by_id:
            errors.append(f"{case_id}: superseded_by desconhecido: {replacement}")
        if case.get("status") == "retired" and not replacement:
            errors.append(f"{case_id}: caso retired deve indicar superseded_by")
    return errors


def find_case(data: dict[str, Any], case_id: str) -> dict[str, Any]:
    for case in data["cases"]:
        if case["id"] == case_id:
            return case
    raise SystemExit(f"Caso não encontrado: {case_id}")


def command_validate(_: argparse.Namespace) -> None:
    errors = validate(load())
    if errors:
        raise SystemExit("\n".join(errors))
    print(f"OK: {LIBRARY}")


def command_list(_: argparse.Namespace) -> None:
    data = load()
    for case in data["cases"]:
        print(f"{case['status']:9} {case['id']:38} {case['title']} ({case['version']})")


def command_add(args: argparse.Namespace) -> None:
    data = load()
    incoming = json.loads(Path(args.input).read_text(encoding="utf-8"))
    case = incoming.get("case", incoming)
    if any(item["id"] == case.get("id") for item in data["cases"]):
        raise SystemExit(f"Caso já existe: {case.get('id')}")
    data["cases"].append(case)
    errors = validate(data)
    if errors:
        raise SystemExit("\n".join(errors))
    save(data)
    print(f"Adicionado como {case['status']}: {case['id']}")


def command_promote(args: argparse.Namespace) -> None:
    data = load()
    case = find_case(data, args.case_id)
    case["status"] = "reference"
    if args.replace:
        old = find_case(data, args.replace)
        if old["id"] == case["id"]:
            raise SystemExit("Um caso não pode substituir a si mesmo")
        old["status"] = "retired"
        old["superseded_by"] = case["id"]
    errors = validate(data)
    if errors:
        raise SystemExit("\n".join(errors))
    save(data)
    print(f"Promovido: {case['id']}")


def command_retire(args: argparse.Namespace) -> None:
    data = load()
    case = find_case(data, args.case_id)
    find_case(data, args.replaced_by)
    if case["id"] == args.replaced_by:
        raise SystemExit("Um caso não pode substituir a si mesmo")
    case["status"] = "retired"
    case["superseded_by"] = args.replaced_by
    errors = validate(data)
    if errors:
        raise SystemExit("\n".join(errors))
    save(data)
    print(f"Aposentado: {case['id']} -> {args.replaced_by}")


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    sub = result.add_subparsers(dest="command", required=True)
    p = sub.add_parser("validate")
    p.set_defaults(func=command_validate)
    p = sub.add_parser("list")
    p.set_defaults(func=command_list)
    p = sub.add_parser("add")
    p.add_argument("--input", required=True)
    p.set_defaults(func=command_add)
    p = sub.add_parser("promote")
    p.add_argument("--case-id", required=True)
    p.add_argument("--replace")
    p.set_defaults(func=command_promote)
    p = sub.add_parser("retire")
    p.add_argument("--case-id", required=True)
    p.add_argument("--replaced-by", required=True)
    p.set_defaults(func=command_retire)
    return result


if __name__ == "__main__":
    args = parser().parse_args()
    args.func(args)
