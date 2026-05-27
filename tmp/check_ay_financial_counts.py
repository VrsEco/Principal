import json
import psycopg2

conn = psycopg2.connect(host='localhost', port=5432, dbname='bdversusv2_prodclone', user='postgres', password='*Paraiso1978')
cur = conn.cursor()
cur.execute("select id, name from companies where name ilike '%Save Water%' order by id")
rows = cur.fetchall()
print('COMPANIES', rows)
cur.execute("select id from companies where name = 'AY - Save Water'")
row = cur.fetchone()
print('TARGET', row[0] if row else None)
if row:
    cid = row[0]
    tables = [
        'financial_entries','financial_schedules','financial_settlements',
        'financial_import_batches','financial_import_rows','financial_reconciliation_matches',
        'financial_classification_suggestions','financial_ingestion_records',
        'financial_borderos','financial_bordero_items','financial_bordero_settlements'
    ]
    counts = {}
    for t in tables:
        cur.execute(f"select count(*) from {t} where company_id = %s and deleted_at is null", (cid,))
        counts[t] = cur.fetchone()[0]
    print(json.dumps(counts, ensure_ascii=False, indent=2))
cur.close()
conn.close()
