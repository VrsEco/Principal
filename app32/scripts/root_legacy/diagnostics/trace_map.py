
from app import create_app
from models import db, Process, ProcessArea, MacroProcess
app = create_app()
with app.app_context():
    cid = 37
    areas = ProcessArea.query.filter_by(company_id=cid).all()
    print(f"Areas for 37: {[a.name for a in areas]}")
    for a in areas:
        macros = MacroProcess.query.filter_by(area_id=a.id).all()
        print(f"  Macro for {a.name}: {[m.name for m in macros]}")
        for m in macros:
            procs = Process.query.filter_by(macro_id=m.id).all()
            print(f"    Processes for {m.name}: {[p.name for p in procs]}")
