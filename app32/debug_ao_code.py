from app import create_app
from models import db, ProcessArea, MacroProcess, Process, Company

app = create_app()
with app.app_context():
    with open("verify_ao_data.txt", "w", encoding="utf-8") as f:
        f.write("Searching for 'AO.C.1.3' across all companies\n")
        f.write("="*50 + "\n")
        
        # Check Companies
        all_companies = Company.query.all()
        for c in all_companies:
            f.write(f"Company ID: {c.id} | Name: {c.name} | Code: {c.client_code}\n")
        f.write("\n")
        
        # Check Areas
        areas = ProcessArea.query.filter(ProcessArea.code.like('%AO%')).all()
        f.write(f"Found {len(areas)} areas with 'AO' in code\n")
        for a in areas:
            f.write(f"Area ID: {a.id} | Company ID: {a.company_id} | Code: {a.code} | Name: {a.name}\n")
        
        # Check Macros
        macros = MacroProcess.query.filter(MacroProcess.code.like('%AO%')).all()
        f.write(f"\nFound {len(macros)} macros with 'AO' in code\n")
        for m in macros:
            f.write(f"Macro ID: {m.id} | Company ID: {m.company_id} | Code: {m.code} | Name: {m.name}\n")

        # Check Processes
        procs = Process.query.filter(Process.code.like('%AO%')).all()
        f.write(f"\nFound {len(procs)} processes with 'AO' in code\n")
        for p in procs:
            f.write(f"Process ID: {p.id} | Company ID: {p.company_id} | Code: {p.code} | Name: {p.name}\n")
