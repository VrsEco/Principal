
from app import create_app
from models import db, Process, ProcessArea, MacroProcess, Company
app = create_app()
with app.app_context():
    cid = 37
    company = Company.query.get(cid)
    print(f"--- ARQUITETURA PARA: {company.name if company else '???' } (ID {cid}) ---")
    
    areas = ProcessArea.query.filter_by(company_id=cid).all()
    if not areas:
        print("Nenhuma ÁREA encontrada para esta empresa.")
    
    for area in areas:
        print(f"\n[ÁREA] {area.name} (ID: {area.id}, Code: {area.code})")
        macros = MacroProcess.query.filter_by(area_id=area.id).all()
        if not macros:
            print("  (Sem Macroprocessos)")
        
        for macro in macros:
            print(f"  [MACRO] {macro.name} (ID: {macro.id}, Code: {macro.code}, Owner: {macro.owner})")
            procs = Process.query.filter_by(macro_id=macro.id).all()
            if not procs:
                print("    (Sem Processos)")
            
            for proc in procs:
                print(f"    [PROCESSO] {proc.name} (ID: {proc.id}, Code: {proc.code}, Stage: {proc.kanban_stage}, Active: {proc.is_active})")
