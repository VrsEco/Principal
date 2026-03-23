
from app import create_app
from models import db, Process, ProcessArea, MacroProcess
app = create_app()
with app.app_context():
    cid = 37
    procs = Process.query.filter_by(company_id=cid).all()
    print(f"PROCESS DIAGNOSIS FOR COMPANY {cid}")
    for p in procs:
        m = MacroProcess.query.get(p.macro_id)
        if m:
            a = ProcessArea.query.get(m.area_id)
            print(f"Process: {p.name} (ID {p.id}) -> Macro: {m.name} (ID {m.id}) -> Area: {a.name if a else 'NONE'} (ID {m.area_id})")
        else:
            print(f"Process: {p.name} (ID {p.id}) -> Macro ID {p.macro_id} NOT FOUND!")
