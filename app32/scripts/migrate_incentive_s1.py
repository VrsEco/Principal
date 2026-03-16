"""
Migration: Incentive Module S1
- Adiciona colunas novas em incentive_indicators
- Cria tabela incentive_participants

Execução: python scripts/migrate_incentive_s1.py
"""
import os, sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[1]))
from scripts.deploy.configr_remote_helper import connect_ssh, APP_DIR


DDL_STATEMENTS = [
    # ── incentive_indicators: novas colunas ──────────────────────────────────
    "ALTER TABLE incentive_indicators ADD COLUMN IF NOT EXISTS collection_mode VARCHAR(30) NOT NULL DEFAULT 'auto_interno';",
    "ALTER TABLE incentive_indicators ADD COLUMN IF NOT EXISTS aggregation_function VARCHAR(30) NOT NULL DEFAULT 'score_ratio';",
    "ALTER TABLE incentive_indicators ADD COLUMN IF NOT EXISTS unit VARCHAR(20) DEFAULT 'pts';",
    "ALTER TABLE incentive_indicators ADD COLUMN IF NOT EXISTS source_detail JSONB;",

    # ── defaults seguros para colunas existentes que podem ser NOT NULL sem default ──
    "ALTER TABLE incentive_indicators ALTER COLUMN indicator_type SET DEFAULT 'individual';",
    "ALTER TABLE incentive_indicators ALTER COLUMN source_module SET DEFAULT 'manual';",

    # ── incentive_participants: nova tabela ───────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS incentive_participants (
        id SERIAL PRIMARY KEY,
        company_id INTEGER NOT NULL REFERENCES companies(id),
        rule_set_id INTEGER NOT NULL REFERENCES incentive_rule_sets(id),
        employee_id INTEGER NOT NULL REFERENCES employees(id),
        valor_base NUMERIC(15,2) NOT NULL DEFAULT 0,
        elegivel BOOLEAN DEFAULT TRUE,
        data_entrada DATE,
        notas TEXT,
        created_at TIMESTAMP DEFAULT NOW(),
        updated_at TIMESTAMP DEFAULT NOW()
    );
    """,
    "CREATE INDEX IF NOT EXISTS idx_inc_part_company ON incentive_participants(company_id);",
    "CREATE INDEX IF NOT EXISTS idx_inc_part_ruleset ON incentive_participants(rule_set_id);",
    "CREATE UNIQUE INDEX IF NOT EXISTS uq_inc_part_emp_plan ON incentive_participants(rule_set_id, employee_id);",
]


def run():
    ssh = connect_ssh()
    try:
        cmd = f"cd {APP_DIR} && grep DATABASE_URL .env | cut -d= -f2-"
        _, stdout, _ = ssh.exec_command(cmd)
        db_url = stdout.read().decode().strip()
        if not db_url:
            print("❌ DATABASE_URL não encontrada")
            return

        ok = 0
        for sql in DDL_STATEMENTS:
            sql_clean = sql.strip()
            if not sql_clean:
                continue
            _, stdout, stderr = ssh.exec_command(f'psql "{db_url}" -c "{sql_clean}"')
            out = stdout.read().decode().strip()
            err = stderr.read().decode().strip()
            short = sql_clean[:80].replace('\n', ' ')
            if err and 'ERROR' in err.upper():
                print(f"  ❌ {short}...\n     {err}")
            else:
                print(f"  ✅ {short}...")
                ok += 1

        print(f"\n🎯 Migration concluída: {ok}/{len(DDL_STATEMENTS)} statements OK")
    finally:
        ssh.close()


if __name__ == "__main__":
    run()
