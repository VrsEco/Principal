"""Processa retentativas de provisionamento de identidade APP32 -> Keycloak.

Pode ser acionado pelo scheduler da aplicação ou por cron. Não recebe senha e
não cria grants fora dos vínculos ativos User/Employee já persistidos.
"""
from __future__ import annotations

import argparse
import json

from app import create_app
from services.identity_provisioning_outbox_service import identity_provisioning_outbox_service


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=25)
    args = parser.parse_args()
    app = create_app("production")
    with app.app_context():
        results = identity_provisioning_outbox_service.process_due(limit=args.limit)
    print(json.dumps({"processed": len(results), "results": results}, ensure_ascii=False))
    return 0 if all(item.get("success") for item in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
