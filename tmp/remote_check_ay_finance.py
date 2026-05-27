import json
import sys
from pathlib import Path

BASE_DIR = Path(r'C:\GestaoVersus\app32\app32')
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from scripts.deploy.configr_remote_helper import connect_ssh, APP_DIR

REMOTE_FILE = f"{APP_DIR}/tmp_codex_check_ay_finance.py"
PY_PATH = "/srv/appgestaoversuscombr.45a4cd4b.configr.cloud/.virtualenv/3.12/bin/python"

remote_script = r'''
from app import create_app
from models import db
from sqlalchemy import text
import json
import sys

app = create_app('production')
with app.app_context():
    companies = db.session.execute(text("""
        select id, name
        from companies
        where name ilike :term
        order by id
    """), {"term": "%Save Water%"}).mappings().all()
    target = db.session.execute(text("""
        select id, name
        from companies
        where name = :name
        limit 1
    """), {"name": "AY - Save Water"}).mappings().first()

    result = {
        "companies": [dict(row) for row in companies],
        "target": dict(target) if target else None,
        "counts": None,
    }

    if target:
        cid = target["id"]
        tables = [
            "financial_schedules",
            "financial_entries",
            "financial_entry_allocations",
            "financial_settlements",
            "financial_settlement_components",
            "financial_title_adjustments",
            "financial_title_adjustment_allocations",
            "financial_title_calculation_logs",
            "financial_borderos",
            "financial_bordero_items",
            "financial_bordero_settlements",
            "financial_import_batches",
            "financial_import_rows",
            "financial_reconciliation_matches",
            "financial_classification_suggestions",
            "financial_ingestion_records"
        ]
        counts = {}
        for table in tables:
            count = db.session.execute(
                text(f"select count(*) as total from {table} where company_id = :cid and deleted_at is null"),
                {"cid": cid},
            ).scalar_one()
            counts[table] = count
        result["counts"] = counts

    print(json.dumps(result, ensure_ascii=False, indent=2))
'''

ssh = connect_ssh()
try:
    stdin, stdout, stderr = ssh.exec_command(f"cat > {REMOTE_FILE}")
    stdin.write(remote_script)
    stdin.channel.shutdown_write()
    setup_err = stderr.read().decode('utf-8', 'ignore')
    if setup_err:
        print(setup_err)

    cmd = (
        f"cd {APP_DIR} && "
        f"export FLASK_CONFIG=production APP_BOOTSTRAP_RUNTIME_SERVICES=0 APP_BOOTSTRAP_DB_SCHEMA=0 && "
        f"{PY_PATH} {REMOTE_FILE}"
    )
    stdin, stdout, stderr = ssh.exec_command(cmd)
    out = stdout.read().decode('utf-8', 'ignore')
    err = stderr.read().decode('utf-8', 'ignore')
    print(out)
    if err:
        print('STDERR_START')
        print(err)
        print('STDERR_END')
    ssh.exec_command(f"rm -f {REMOTE_FILE}")
finally:
    ssh.close()
