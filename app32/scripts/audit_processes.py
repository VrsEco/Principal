from app import app
from models import db
from models.process import Process, ProcessInstance
from models.company import Company
from models.routine import Routine # Assuming Routine model exists or table 'routines'

def audit_data():
    with app.app_context():
        print("--- AUDITORIA DE DADOS DE PROCESSOS ---")
        companies = Company.query.all()
        print(f"Total Companies: {len(companies)}")
        
        total_processes = Process.query.count()
        print(f"Total Processes (Global): {total_processes}")
        
        # Check routines via SQL since model might be ambiguous in my context
        with db.engine.connect() as conn:
            result = conn.execute(db.text("SELECT COUNT(*) FROM routines"))
            total_routines = result.scalar()
            print(f"Total Routines (Global): {total_routines}")
            
            print("\n--- DETALHAMENTO POR EMPRESA (TOP 5) ---")
            for company in companies[:5]:
                p_count = Process.query.filter_by(company_id=company.id).count()
                
                # Routines
                r_count = conn.execute(
                    db.text("SELECT COUNT(*) FROM routines WHERE company_id = :cid"),
                    {"cid": company.id}
                ).scalar()
                
                print(f"Company ID {company.id} ({company.name}): {p_count} Processes, {r_count} Routines")

if __name__ == "__main__":
    audit_data()
