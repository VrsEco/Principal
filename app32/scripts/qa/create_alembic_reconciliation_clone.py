"""Cria uma cópia PostgreSQL descartável para reconciliação Alembic.

Não remove bancos, não altera a origem e não executa migrations. O nome do
alvo é restrito ao padrão de laboratório R04 para impedir uso acidental em
ambientes da aplicação.
"""

from __future__ import annotations

import argparse
import re
from urllib.parse import urlsplit, urlunsplit

import psycopg2
from psycopg2 import sql


TARGET_NAME_PATTERN = re.compile(r"^app32_oauth_r04_\d{8}$")


def maintenance_url(source_url: str) -> tuple[str, str]:
    parsed = urlsplit(source_url)
    source_database = parsed.path.lstrip("/")
    if not source_database:
        raise ValueError("A URL de origem deve informar o banco PostgreSQL.")
    return urlunsplit((parsed.scheme, parsed.netloc, "/postgres", parsed.query, parsed.fragment)), source_database


def create_clone(*, source_url: str, target_database: str) -> None:
    if not TARGET_NAME_PATTERN.fullmatch(target_database):
        raise ValueError("O alvo deve seguir app32_oauth_r04_YYYYMMDD.")

    admin_url, source_database = maintenance_url(source_url)
    if source_database == target_database:
        raise ValueError("Origem e alvo não podem ser o mesmo banco.")

    connection = psycopg2.connect(admin_url)
    try:
        connection.autocommit = True
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", (target_database,))
            if cursor.fetchone():
                raise RuntimeError("O banco-alvo já existe; este utilitário nunca o remove nem o reutiliza.")
            cursor.execute(
                sql.SQL("CREATE DATABASE {} TEMPLATE {}").format(
                    sql.Identifier(target_database), sql.Identifier(source_database)
                )
            )
    finally:
        connection.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-url", required=True, help="URL PostgreSQL da cópia isolada de origem.")
    parser.add_argument("--target-database", required=True, help="Nome novo do clone R04.")
    args = parser.parse_args()
    create_clone(source_url=args.source_url, target_database=args.target_database)
    print("Clone descartável R04 criado; nenhuma migration foi executada.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
