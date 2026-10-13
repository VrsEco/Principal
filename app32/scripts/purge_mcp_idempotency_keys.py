"""Limpeza manual das chaves de idempotência do mcp-versus (a tarefa diária já faz isso sozinha).

Uso (no servidor, na pasta app32, com o Python do ambiente virtual):
    python scripts/purge_mcp_idempotency_keys.py              # simulação: só conta o que seria removido
    python scripts/purge_mcp_idempotency_keys.py --apply      # remove de fato
    python scripts/purge_mcp_idempotency_keys.py --days 0     # considera todas as já vencidas

Por padrão respeita a retenção de 7 dias depois do vencimento. Sem ``--apply`` não grava nada.
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import timedelta

os.environ.setdefault("APP_BOOTSTRAP_DB_SCHEMA", "0")
os.environ.setdefault("APP_BOOTSTRAP_RUNTIME_SERVICES", "0")
sys.path.insert(0, os.getcwd())

try:
    from dotenv import load_dotenv

    load_dotenv(".env")
except Exception:  # pragma: no cover
    pass


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--apply", action="store_true", help="remove de fato (padrão: só conta)")
    parser.add_argument("--days", type=int, default=7, help="retenção em dias depois do vencimento (padrão 7)")
    args = parser.parse_args(argv)

    from app import create_app

    app = create_app()
    with app.app_context():
        from services import mcp_idempotency_service as service

        retention = timedelta(days=max(0, args.days))
        pending = service.count_expired(retention)
        print(f"P| linhas vencidas há mais de {retention.days} dia(s): {pending}")
        if not args.apply:
            print("P| simulação: nada foi removido (use --apply para remover)")
            return 0
        removed = 0
        while True:
            batch = service.purge_expired(limit=1000, older_than=retention)
            removed += batch
            if batch < 1000:
                break
        print(f"P| removidas: {removed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
