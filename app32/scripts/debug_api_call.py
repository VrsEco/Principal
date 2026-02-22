
import sys
import os
import json

sys.path.append(os.getcwd())

from app import app
from models import db
from sqlalchemy import text

def debug_api():
    with app.app_context():
        # Find company with routines
        with db.engine.connect() as conn:
            companies = conn.execute(text("SELECT id, name FROM companies")).fetchall()
            target_company = None
            for c in companies:
                rc = conn.execute(text("SELECT count(*) FROM routines WHERE company_id = :cid"), {'cid': c.id}).scalar()
                if rc > 0:
                    target_company = c
                    print(f"Company {c.id} ({c.name}) has {rc} routines. Simulating API call...")
                    break
            
            if not target_company:
                print("No routines found in ANY company!")
                return
            
            # Simulate api_get_process_routines logic
            cursor = conn.execute(
                text("""
                    SELECT
                        r.id,
                        r.name,
                        r.process_id,
                        p.code AS process_code,
                        p.name AS process_name
                    FROM routines r
                    LEFT JOIN processes p ON r.process_id = p.id
                    WHERE r.company_id = :cid
                """),
                {'cid': target_company.id}
            )
            rows = cursor.fetchall()
            routines = [dict(row._mapping) for row in rows]
            print(f"API Returned {len(routines)} routines:")
            for r in routines:
                print(f"  ID: {r['id']}, Name: {r['name']}, ProcessID: {r['process_id']} (Type: {type(r['process_id'])})")

if __name__ == "__main__":
    debug_api()
