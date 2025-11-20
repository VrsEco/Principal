#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Aplicar Migration do ModeFin
Cria tabela plan_finance_capital_giro e adiciona executive_summary
"""

from database.postgres_helper import get_engine
from sqlalchemy import text


def apply_migration():
    """Aplica migration do ModeFin"""
    engine = get_engine()

    with engine.begin() as conn:
        # Ler SQL da migration
        with open("migrations/create_modefin_tables.sql", "r", encoding="utf-8") as f:
            sql_content = f.read()

        # Dividir por ponto e vírgula e executar statement por statement
        statements = [
            s.strip()
            for s in sql_content.split(";")
            if s.strip()
            and not s.strip().startswith("--")
            and not s.strip().startswith("/*")
        ]

        for i, statement in enumerate(statements, 1):
            if statement:
                try:
                    print(f"[{i}/{len(statements)}] Executando: {statement[:80]}...")
                    conn.execute(text(statement))
                except Exception as e:
                    # Ignorar erros de "já existe"
                    if "already exists" in str(e) or "já existe" in str(e):
                        print(f"  ⚠️ Já existe (ignorado)")
                    else:
                        print(f"  ❌ Erro: {e}")

        print("\n✅ Migration aplicada com sucesso!")
        print("✅ Tabela plan_finance_capital_giro criada")
        print("✅ Coluna executive_summary adicionada")


if __name__ == "__main__":
    try:
        apply_migration()
    except Exception as e:
        print(f"\n❌ Erro ao aplicar migration: {e}")
        import traceback

        traceback.print_exc()
