"""
Migration completa: verifica TODAS as colunas do modelo Indicator
e adiciona o que falta no banco (local ou produção).
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from models import db
from sqlalchemy import text

def column_exists(conn, table, column):
    r = conn.execute(text(
        "SELECT COUNT(*) FROM information_schema.columns "
        "WHERE table_name=:t AND column_name=:c"
    ), {"t": table, "c": column})
    return r.scalar() > 0

def table_exists(conn, table):
    r = conn.execute(text(
        "SELECT COUNT(*) FROM information_schema.tables "
        "WHERE table_name=:t AND table_schema='public'"
    ), {"t": table})
    return r.scalar() > 0

def run():
    app = create_app()
    with app.app_context():
        conn = db.engine.connect()

        print("=== MIGRATION COMPLETA: Indicator Schema ===\n")

        # ── 1. Tabelas auxiliares ─────────────────────────────────────────────

        if not table_exists(conn, 'indicator_groups'):
            print("Criando tabela indicator_groups...")
            conn.execute(text("""
                CREATE TABLE indicator_groups (
                    id SERIAL PRIMARY KEY,
                    company_id INTEGER NOT NULL REFERENCES companies(id),
                    parent_id INTEGER REFERENCES indicator_groups(id),
                    code VARCHAR(50) NOT NULL,
                    name VARCHAR(200) NOT NULL,
                    description TEXT,
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                )
            """))
            conn.commit()
            print("  ✓ indicator_groups criada")
        else:
            print("  - indicator_groups já existe")

        if not table_exists(conn, 'indicator_tree'):
            print("Criando tabela indicator_tree...")
            conn.execute(text("""
                CREATE TABLE indicator_tree (
                    id SERIAL PRIMARY KEY,
                    company_id INTEGER NOT NULL REFERENCES companies(id),
                    parent_id INTEGER REFERENCES indicator_tree(id),
                    code VARCHAR(50) NOT NULL,
                    name VARCHAR(255) NOT NULL,
                    description TEXT,
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                )
            """))
            conn.commit()
            print("  ✓ indicator_tree criada")
        else:
            print("  - indicator_tree já existe")

        # ── 2. Colunas da tabela indicators ──────────────────────────────────
        print("\nVerificando colunas da tabela indicators:")

        all_columns = [
            # (nome_coluna, definição_sql)
            ("tree_id",              "INTEGER REFERENCES indicator_tree(id)"),
            ("full_code",            "VARCHAR(100)"),
            ("group_id",             "INTEGER REFERENCES indicator_groups(id)"),
            ("description",          "TEXT"),
            ("indicator_type",       "VARCHAR(50) DEFAULT 'individual'"),
            ("source_module",        "VARCHAR(50) DEFAULT 'manual'"),
            ("source_id",            "INTEGER"),
            ("collection_mode",      "VARCHAR(30) DEFAULT 'manual'"),
            ("aggregation_function", "VARCHAR(30) DEFAULT 'sum'"),
            ("unit",                 "VARCHAR(50) DEFAULT 'pts'"),
            ("polarity",             "VARCHAR(20) DEFAULT 'positive'"),
            ("formula",              "TEXT"),
            ("process_id",           "INTEGER REFERENCES processes(id)"),
            ("project_id",           "INTEGER REFERENCES projects(id)"),
            ("collaborators",        "JSONB"),
            ("data_source",          "TEXT"),
            ("notes",                "TEXT"),
            ("okr_reference",        "VARCHAR(255)"),
            ("okr_level",            "VARCHAR(50)"),
            ("is_active",            "BOOLEAN DEFAULT TRUE"),
            ("created_at",           "TIMESTAMP DEFAULT NOW()"),
            ("updated_at",           "TIMESTAMP DEFAULT NOW()"),
        ]

        added = 0
        for col_name, col_def in all_columns:
            if not column_exists(conn, 'indicators', col_name):
                try:
                    conn.execute(text(f"ALTER TABLE indicators ADD COLUMN {col_name} {col_def}"))
                    conn.commit()
                    print(f"  ✓  ADICIONADA: {col_name}")
                    added += 1
                except Exception as e:
                    conn.rollback()
                    print(f"  ✗  ERRO em {col_name}: {e}")
            else:
                print(f"  -  OK: {col_name}")

        # ── 3. Tabelas de metas e dados ───────────────────────────────────────
        if not table_exists(conn, 'indicator_goals'):
            print("\nCriando tabela indicator_goals...")
            conn.execute(text("""
                CREATE TABLE indicator_goals (
                    id SERIAL PRIMARY KEY,
                    company_id INTEGER NOT NULL REFERENCES companies(id),
                    indicator_id INTEGER NOT NULL REFERENCES indicators(id) ON DELETE CASCADE,
                    goal_value NUMERIC(15,4) NOT NULL,
                    goal_date DATE NOT NULL,
                    period_start DATE,
                    period_end DATE,
                    responsible_id INTEGER REFERENCES employees(id),
                    status VARCHAR(50) DEFAULT 'active',
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                )
            """))
            conn.commit()
            print("  ✓ indicator_goals criada")
        else:
            print("\n  - indicator_goals já existe")

        if not table_exists(conn, 'indicator_data'):
            print("Criando tabela indicator_data...")
            conn.execute(text("""
                CREATE TABLE indicator_data (
                    id SERIAL PRIMARY KEY,
                    company_id INTEGER NOT NULL REFERENCES companies(id),
                    indicator_id INTEGER NOT NULL REFERENCES indicators(id) ON DELETE CASCADE,
                    employee_id INTEGER REFERENCES employees(id),
                    period_start DATE,
                    period_end DATE,
                    reference_date DATE NOT NULL,
                    value NUMERIC(15,4) NOT NULL,
                    raw_value NUMERIC(15,4),
                    source VARCHAR(50) DEFAULT 'manual',
                    source_ref VARCHAR(255),
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                )
            """))
            conn.commit()
            print("  ✓ indicator_data criada")
        else:
            print("  - indicator_data já existe")

        # ── 4. Índice único em full_code ──────────────────────────────────────
        try:
            conn.execute(text(
                "CREATE UNIQUE INDEX IF NOT EXISTS ix_indicators_full_code "
                "ON indicators(full_code) WHERE full_code IS NOT NULL"
            ))
            conn.commit()
            print("\n  ✓ Índice ix_indicators_full_code: OK")
        except Exception as e:
            conn.rollback()
            print(f"\n  - Índice full_code: {e}")

        conn.close()
        print(f"\n=== CONCLUÍDO: {added} colunas adicionadas ===")

if __name__ == "__main__":
    run()
