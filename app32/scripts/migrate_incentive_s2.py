"""
Migration: Incentive Module S2
- Adiciona vetor_type, incidencia, company_id em incentive_rules
- Adiciona description em incentive_rule_sets (caso não exista)

Execução: python scripts/migrate_incentive_s2.py
"""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[1]))
from scripts.deploy.configr_remote_helper import connect_ssh, APP_DIR

DDL = [
    # ── incentive_rules: novos campos ────────────────────────────────────────
    "ALTER TABLE incentive_rules ADD COLUMN IF NOT EXISTS company_id INTEGER REFERENCES companies(id);",
    "ALTER TABLE incentive_rules ADD COLUMN IF NOT EXISTS vetor_type VARCHAR(20) NOT NULL DEFAULT 'bonus';",
    "ALTER TABLE incentive_rules ADD COLUMN IF NOT EXISTS incidencia VARCHAR(20) NOT NULL DEFAULT 'individual';",
    "CREATE INDEX IF NOT EXISTS idx_inc_rules_company ON incentive_rules(company_id);",

    # ── incentive_rule_sets: garantir campo description ───────────────────────
    "ALTER TABLE incentive_rule_sets ADD COLUMN IF NOT EXISTS description TEXT;",
    "ALTER TABLE incentive_rule_sets ADD COLUMN IF NOT EXISTS valid_to DATE;",
]

def run():
    ssh = connect_ssh()
    try:
        _, out, _ = ssh.exec_command(f"cd {APP_DIR} && grep DATABASE_URL .env | cut -d= -f2-")
        db_url = out.read().decode().strip()
        if not db_url:
            print("❌ DATABASE_URL não encontrada"); return

        ok = 0
        for sql in DDL:
            _, stdout, stderr = ssh.exec_command(f'psql "{db_url}" -c "{sql.strip()}"')
            o = stdout.read().decode().strip()
            e = stderr.read().decode().strip()
            lbl = sql.strip()[:80].replace('\n', ' ')
            if 'ERROR' in e.upper() and 'already exists' not in e.lower():
                print(f"  ❌ {lbl}... | {e}")
            else:
                print(f"  ✅ {lbl}...")
                ok += 1

        print(f"\n🎯 S2 Migration: {ok}/{len(DDL)} OK")
    finally:
        ssh.close()

if __name__ == "__main__":
    run()
