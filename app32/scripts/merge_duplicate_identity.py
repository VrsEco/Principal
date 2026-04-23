from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from dotenv import load_dotenv

from app import create_app
from services.identity.duplicate_identity_service import DuplicateIdentityService


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Executa merge transacional de usuário/colaborador duplicado.")
    parser.add_argument("--entity", choices=("user", "employee"), required=True)
    parser.add_argument("--keep-id", type=int, required=True, help="ID que será preservado")
    parser.add_argument("--merge-id", type=int, required=True, help="ID duplicado a ser absorvido")
    parser.add_argument("--company-id", type=int, default=None, help="Obrigatório para merge de employee")
    parser.add_argument("--apply", action="store_true", help="Aplica a mudança. Sem esta flag, executa dry-run.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    load_dotenv(BASE_DIR / ".env")
    os.environ.setdefault("APP_BOOTSTRAP_DB_SCHEMA", "0")
    os.environ.setdefault("APP_BOOTSTRAP_RUNTIME_SERVICES", "0")
    app = create_app(os.environ.get("FLASK_CONFIG") or "default")

    with app.app_context():
        if args.entity == "user":
            result = DuplicateIdentityService.merge_users(
                keep_user_id=args.keep_id,
                merge_user_id=args.merge_id,
                dry_run=not args.apply,
            )
        else:
            if args.company_id is None:
                raise SystemExit("--company-id é obrigatório para merge de employee")
            result = DuplicateIdentityService.merge_employees(
                company_id=args.company_id,
                keep_employee_id=args.keep_id,
                merge_employee_id=args.merge_id,
                dry_run=not args.apply,
            )

        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result.get("success") else 1


if __name__ == "__main__":
    raise SystemExit(main())
