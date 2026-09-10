from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

os.environ.setdefault("APP_BOOTSTRAP_RUNTIME_SERVICES", "0")
os.environ.setdefault("APP_BOOTSTRAP_DB_SCHEMA", "0")

from app import create_app  # noqa: E402
from models import Company, db  # noqa: E402
from models.contracts import ContractCatalogItem  # noqa: E402


CATALOG_BLUEPRINT = (
    {
        "code": "1",
        "parent_code": None,
        "name": "Soluções Versus",
        "description": None,
        "selectable": False,
        "active": True,
    },
    {
        "code": "1.01",
        "parent_code": "1",
        "name": "Sustentação Recorrente",
        "description": None,
        "selectable": False,
        "active": True,
    },
    {
        "code": "1.01.001",
        "parent_code": "1.01",
        "name": "Performance Hub",
        "description": "Modelo recorrente de sustentação, cadência e operação assistida da Versus.",
        "selectable": True,
        "active": True,
        "legacy_compatible": True,
    },
    {
        "code": "1.02",
        "parent_code": "1",
        "name": "Necessidades Urgentes",
        "description": None,
        "selectable": False,
        "active": True,
    },
    {
        "code": "1.02.001",
        "parent_code": "1.02",
        "name": "Intervenção de Necessidade Urgente",
        "description": "Projeto ou programa para tratar uma dor específica e relevante.",
        "selectable": True,
        "active": False,
        "enforce_contract": True,
    },
    {
        "code": "1.03",
        "parent_code": "1",
        "name": "Estruturação Empresarial",
        "description": None,
        "selectable": False,
        "active": True,
    },
    {
        "code": "1.03.001",
        "parent_code": "1.03",
        "name": "Diagnóstico Inicial — Fase 00",
        "description": "Qualificação aprofundada, priorização e definição do trilho metodológico.",
        "selectable": True,
        "active": False,
        "enforce_contract": True,
    },
    {
        "code": "1.03.002",
        "parent_code": "1.03",
        "name": "Programa de Estruturação Empresarial",
        "description": "Estruturação faseada de capacidades gerenciais duradouras, com gates.",
        "selectable": True,
        "active": False,
        "enforce_contract": True,
    },
)


def _catalog_items_by_code(company_id: int) -> dict[str, ContractCatalogItem]:
    return {
        item.code: item
        for item in ContractCatalogItem.query.filter(
            ContractCatalogItem.company_id == company_id,
            ContractCatalogItem.deleted_at.is_(None),
        ).all()
    }


def run(*, company_id: int, expected_company_name: str | None, dry_run: bool) -> dict:
    company = Company.query.filter(Company.id == company_id).first()
    if not company:
        raise SystemExit(f"Empresa não localizada: company_id={company_id}.")
    if expected_company_name and expected_company_name.casefold() not in str(company.name or "").casefold():
        raise SystemExit(
            f"Empresa divergente para o backfill: esperado={expected_company_name!r}, atual={company.name!r}."
        )

    by_code = _catalog_items_by_code(company_id)
    created: list[str] = []
    updated: list[str] = []
    unchanged: list[str] = []

    for definition in CATALOG_BLUEPRINT:
        parent_code = definition["parent_code"]
        parent = by_code.get(parent_code) if parent_code else None
        if parent_code and not parent:
            raise RuntimeError(f"Pai {parent_code} não foi materializado antes de {definition['code']}.")

        item = by_code.get(definition["code"])
        if not item:
            metadata = {}
            if definition.get("enforce_contract"):
                metadata["commercial_contract_enforced"] = True
            if definition.get("legacy_compatible"):
                metadata["commercial_contract_legacy"] = True
            item = ContractCatalogItem(
                company_id=company_id,
                parent_id=parent.id if parent else None,
                code=definition["code"],
                name=definition["name"],
                item_kind="service",
                description=definition["description"],
                unit_code="servico" if definition["selectable"] else None,
                accepts_contracting=definition["selectable"],
                is_active=definition["active"],
                metadata_json=metadata,
            )
            db.session.add(item)
            db.session.flush()
            by_code[item.code] = item
            created.append(item.code)
            continue

        changed = False
        target_parent_id = parent.id if parent else None
        if item.parent_id != target_parent_id:
            item.parent_id = target_parent_id
            changed = True
        if item.name != definition["name"]:
            item.name = definition["name"]
            changed = True
        if definition["description"] and not str(item.description or "").strip():
            item.description = definition["description"]
            changed = True
        if bool(item.accepts_contracting) != bool(definition["selectable"]):
            item.accepts_contracting = bool(definition["selectable"])
            changed = True
        if not definition["selectable"] and not item.is_active:
            item.is_active = True
            changed = True
        metadata = dict(item.metadata_json or {})
        if definition.get("enforce_contract") and metadata.get("commercial_contract_enforced") is not True:
            metadata["commercial_contract_enforced"] = True
            item.metadata_json = metadata
            changed = True
        if definition.get("legacy_compatible") and "commercial_contract_legacy" not in metadata:
            metadata["commercial_contract_legacy"] = True
            item.metadata_json = metadata
            changed = True
        (updated if changed else unchanged).append(item.code)

    result = {
        "company_id": company_id,
        "company_name": company.name,
        "created": created,
        "updated": updated,
        "unchanged": unchanged,
        "dry_run": dry_run,
    }
    if dry_run:
        db.session.rollback()
    else:
        db.session.commit()
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Backfill idempotente do catálogo oficial de ofertas da Versus.")
    parser.add_argument("--company-id", type=int, required=True)
    parser.add_argument("--expected-company-name", default="Versus")
    parser.add_argument("--apply", action="store_true", help="Sem esta flag, executa dry-run e rollback.")
    parser.add_argument("--config", default="production")
    args = parser.parse_args()

    app = create_app(args.config)
    with app.app_context():
        result = run(
            company_id=args.company_id,
            expected_company_name=args.expected_company_name,
            dry_run=not args.apply,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
