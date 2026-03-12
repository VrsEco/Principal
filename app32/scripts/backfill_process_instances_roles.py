#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Backfill idempotente para owner/responsible em process_instances.

Regras:
- Nunca sobrescreve valores já preenchidos na instância.
- Usa fallback do cadastro do processo apenas quando company_id coincide.
- Permite escopo por empresa e modo dry-run.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import text

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from database.postgres_helper import get_engine


@dataclass
class BackfillStats:
    owner_candidates: int = 0
    responsible_candidates: int = 0
    owner_updated: int = 0
    responsible_updated: int = 0


OWNER_CANDIDATES_SQL = text(
    """
    SELECT COUNT(*)
    FROM process_instances pi
    JOIN processes p
      ON p.id = pi.process_id
     AND p.company_id = pi.company_id
    WHERE pi.owner_employee_id IS NULL
      AND p.owner_employee_id IS NOT NULL
      AND (:company_id IS NULL OR pi.company_id = :company_id)
    """
)

RESPONSIBLE_CANDIDATES_SQL = text(
    """
    SELECT COUNT(*)
    FROM process_instances pi
    JOIN processes p
      ON p.id = pi.process_id
     AND p.company_id = pi.company_id
    WHERE pi.responsible_id IS NULL
      AND p.responsible_id IS NOT NULL
      AND (:company_id IS NULL OR pi.company_id = :company_id)
    """
)

OWNER_UPDATE_SQL = text(
    """
    UPDATE process_instances AS pi
       SET owner_employee_id = p.owner_employee_id,
           updated_at = NOW()
      FROM processes AS p
     WHERE p.id = pi.process_id
       AND p.company_id = pi.company_id
       AND pi.owner_employee_id IS NULL
       AND p.owner_employee_id IS NOT NULL
       AND (:company_id IS NULL OR pi.company_id = :company_id)
    """
)

RESPONSIBLE_UPDATE_SQL = text(
    """
    UPDATE process_instances AS pi
       SET responsible_id = p.responsible_id,
           updated_at = NOW()
      FROM processes AS p
     WHERE p.id = pi.process_id
       AND p.company_id = pi.company_id
       AND pi.responsible_id IS NULL
       AND p.responsible_id IS NOT NULL
       AND (:company_id IS NULL OR pi.company_id = :company_id)
    """
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Backfill owner/responsible em process_instances a partir de processes"
    )
    parser.add_argument("--company-id", type=int, default=None, help="Limita o backfill a uma empresa")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Aplica as atualizações. Sem esta flag, executa apenas dry-run.",
    )
    return parser.parse_args()


def collect_stats(company_id: int | None) -> BackfillStats:
    params = {"company_id": company_id}
    engine = get_engine()
    with engine.connect() as conn:
        owner_candidates = conn.execute(OWNER_CANDIDATES_SQL, params).scalar() or 0
        responsible_candidates = conn.execute(RESPONSIBLE_CANDIDATES_SQL, params).scalar() or 0
    return BackfillStats(
        owner_candidates=int(owner_candidates),
        responsible_candidates=int(responsible_candidates),
    )


def apply_backfill(company_id: int | None) -> BackfillStats:
    params = {"company_id": company_id}
    engine = get_engine()
    stats = collect_stats(company_id)

    with engine.begin() as conn:
        owner_result = conn.execute(OWNER_UPDATE_SQL, params)
        responsible_result = conn.execute(RESPONSIBLE_UPDATE_SQL, params)
        stats.owner_updated = int(owner_result.rowcount or 0)
        stats.responsible_updated = int(responsible_result.rowcount or 0)

    return stats


def main() -> int:
    args = parse_args()

    if not args.apply:
        stats = collect_stats(args.company_id)
        print("[DRY-RUN] Backfill de instâncias de processo")
        print(f"  Empresa alvo: {args.company_id if args.company_id is not None else 'todas'}")
        print(f"  Owner pendente com origem no processo: {stats.owner_candidates}")
        print(f"  Responsible pendente com origem no processo: {stats.responsible_candidates}")
        print("  Nenhuma alteração foi persistida.")
        return 0

    stats = apply_backfill(args.company_id)
    print("[APPLY] Backfill de instâncias de processo concluído")
    print(f"  Empresa alvo: {args.company_id if args.company_id is not None else 'todas'}")
    print(f"  Owner atualizados: {stats.owner_updated}")
    print(f"  Responsible atualizados: {stats.responsible_updated}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
