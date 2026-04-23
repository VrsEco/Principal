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
    parser = argparse.ArgumentParser(description="Audita usuários e colaboradores duplicados.")
    parser.add_argument("--company-id", type=int, default=None, help="Filtra duplicidades de colaboradores por empresa.")
    parser.add_argument(
        "--type",
        choices=("all", "users", "employees"),
        default="all",
        help="Tipo de auditoria.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    load_dotenv(BASE_DIR / ".env")
    os.environ.setdefault("APP_BOOTSTRAP_DB_SCHEMA", "0")
    os.environ.setdefault("APP_BOOTSTRAP_RUNTIME_SERVICES", "0")
    app = create_app(os.environ.get("FLASK_CONFIG") or "default")
    with app.app_context():
        payload: dict[str, object] = {}
        if args.type in {"all", "users"}:
            payload["users"] = DuplicateIdentityService.audit_duplicate_users()
        if args.type in {"all", "employees"}:
            payload["employees"] = DuplicateIdentityService.audit_duplicate_employees(company_id=args.company_id)
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
