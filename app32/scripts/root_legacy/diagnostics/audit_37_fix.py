
from app import create_app
from models import db, Process, ProcessArea, MacroProcess, Company

app = create_app()
with app.app_context():
    cid = 37
    company = Company.query.get(cid)
    
    with open('audit_37_clean.txt', 'w', encoding='utf-8') as f:
        f.write(f"--- DATABASE AUDIT: {company.name if company else '???' } (ID {cid}) ---\n")
        
        areas = ProcessArea.query.filter_by(company_id=cid).order_by(ProcessArea.id).all()
        f.write(f"Total Areas: {len(areas)}\n")
        
        for area in areas:
            f.write(f"\n[AREA] {area.name} (ID: {area.id}, Code: {area.code})\n")
            macros = MacroProcess.query.filter_by(area_id=area.id).order_by(MacroProcess.id).all()
            f.write(f"  Total Macros in Area: {len(macros)}\n")
            
            for macro in macros:
                f.write(f"  [MACRO] {macro.name} (ID: {macro.id}, Code: {macro.code}, Owner: {macro.owner})\n")
                procs = Process.query.filter_by(macro_id=macro.id).order_by(Process.id).all()
                f.write(f"    Total Processes in Macro: {len(procs)}\n")
                
                for proc in procs:
                    f.write(f"    [PROCESS] {proc.name} (ID: {proc.id}, Code: {proc.code}, Stage: {proc.kanban_stage}, Active: {proc.is_active})\n")
        
        f.write("\n--- END OF AUDIT ---\n")

print("Audit complete. Check audit_37_clean.txt")
