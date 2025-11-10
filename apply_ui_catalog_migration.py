#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Aplicar migration do catálogo de UI (ui_catalog).
"""

from pathlib import Path

from database.postgres_helper import get_engine
from sqlalchemy import text


SQL_FILE = Path("migrations/20251108_create_ui_catalog.sql")


def apply_migration() -> None:
    """Executa a migration SQL responsável pela tabela ui_catalog."""
    if not SQL_FILE.exists():
        raise FileNotFoundError(f"Arquivo de migration não encontrado: {SQL_FILE}")

    engine = get_engine()

    with engine.begin() as conn, SQL_FILE.open("r", encoding="utf-8") as handle:
        sql_content = handle.read()

        statements = [
            statement.strip()
            for statement in sql_content.split(";")
            if statement.strip()
            and not statement.strip().startswith("--")
            and not statement.strip().startswith("/*")
        ]

        total = len(statements)
        for index, statement in enumerate(statements, start=1):
            preview = statement.replace("\n", " ")[:80]
            print(f"[{index}/{total}] Executando: {preview}...")
            try:
                conn.execute(text(statement))
            except Exception as exc:  # pylint: disable=broad-except
                message = str(exc).lower()
                if "already exists" in message or "já existe" in message or "duplicate key" in message:
                    print("  ⚠️ Já existente, seguindo adiante.")
                    continue
                raise

    print("\n✅ Migration ui_catalog aplicada com sucesso!")


if __name__ == "__main__":
    try:
        apply_migration()
    except Exception as error:  # pylint: disable=broad-except
        print(f"\n❌ Erro ao aplicar migration ui_catalog: {error}")
        raise





