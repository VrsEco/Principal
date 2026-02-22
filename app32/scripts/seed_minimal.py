import sys
import os
from datetime import datetime

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))
from app import create_app
from models import db, Company, ProcessArea, MacroProcess, Process

app = create_app()
with app.app_context():
    print("--- SEED ROTINA MINIMALISTA ---")
    c = Company.query.filter_by(name="Titan Corp").first()
    if not c:
        c = Company(name="Titan Corp")
        db.session.add(c)
        db.session.commit()
    
    area = ProcessArea(company_id=c.id, name="Operacoes de IA", code="IA-OPS")
    db.session.add(area)
    db.session.commit()
    print(f"Area {area.id} criada.")
    
    macro = MacroProcess(company_id=c.id, area_id=area.id, name="Ciclo de Vida", code="CV")
    db.session.add(macro)
    db.session.commit()
    print(f"Macro {macro.id} criada.")

    proc = Process(company_id=c.id, macro_id=macro.id, name="Curadoria", code="CUR")
    db.session.add(proc)
    db.session.commit()
    print(f"Processo {proc.id} criado.")
