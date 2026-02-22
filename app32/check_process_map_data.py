
from app import create_app
from models import db, ProcessArea, MacroProcess, Process

app = create_app()
with app.app_context():
    company_id = 5
    areas = ProcessArea.query.filter_by(company_id=company_id).all()
    print(f"Company ID: {company_id}")
    print(f"Areas found: {len(areas)}")
    for a in areas:
        print(f"Area: ID={a.id}, Code={a.code}, Name={a.name}")
        macros = MacroProcess.query.filter_by(area_id=a.id).all()
        print(f"  Macros found: {len(macros)}")
        for m in macros:
            print(f"  Macro: ID={m.id}, Code={m.code}, Name={m.name}")
            procs = Process.query.filter_by(macro_id=m.id).all()
            print(f"    Processes found: {len(procs)}")
            for p in procs:
                print(f"    Process: ID={p.id}, Code={p.code}, Name={p.name}")
