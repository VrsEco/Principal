from __future__ import annotations

import argparse
import json
import os
import sys

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
APP_DIR = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

from app import create_app  # noqa: E402
from services.financial_bank_statement_repair_service import FinancialBankStatementRepairService  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Backfill tenant-safe para movimentos faltantes no Extrato Bancário."
    )
    parser.add_argument("--company-id", type=int, required=True, help="Empresa alvo. Obrigatório para preservar multi-tenancy.")
    parser.add_argument("--limit", type=int, default=None, help="Limite opcional de itens por etapa.")
    parser.add_argument("--apply", action="store_true", help="Aplica alterações. Sem esta flag executa apenas dry-run.")
    parser.add_argument("--config", default=os.environ.get("FLASK_CONFIG") or "default")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    app = create_app(args.config)
    with app.app_context():
        result = FinancialBankStatementRepairService.repair_bank_statement_movements(
            company_id=args.company_id,
            apply=bool(args.apply),
            limit=args.limit,
        )
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    return 0 if not result.get("transfer_settlements", {}).get("errors") else 2


if __name__ == "__main__":
    raise SystemExit(main())
