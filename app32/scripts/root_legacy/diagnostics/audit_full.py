
import os
from app import create_app
from models import db, Process, Company, ProcessArea, MacroProcess

app = create_app()
with app.app_context():
    print("--- FULL DATABASE AUDIT ---")
    companies = Company.query.order_by(Company.id).all()
    for c in companies:
        p_count = Process.query.filter_by(company_id=c.id).count()
        a_count = ProcessArea.query.filter_by(company_id=c.id).count()
        m_count = MacroProcess.query.filter_by(company_id=c.id).count()
        print(f"[{c.id}] {c.name}: Areas={a_count}, Macros={m_count}, Processes={p_count}")
    
    total_p = Process.query.count()
    print(f"\nTotal Processes in DB: {total_p}")
