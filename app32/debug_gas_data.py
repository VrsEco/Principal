from app import create_app
from models import db, Company, ProcessArea, MacroProcess, Process

app = create_app()

def inspect_gas_evolution_data():
    with app.app_context():
        # 1. Find the company
        # Trying exact match and partial match
        company = Company.query.filter(Company.name.ilike('%Gas%Evolution%')).first()
        
        if not company:
            print("❌ Company 'Gas Evolution' NOT FOUND.")
            # List all companies to help debugging
            all_companies = Company.query.limit(10).all()
            print("Available companies (first 10):")
            for c in all_companies:
                print(f" - ID: {c.id}, Name: {c.name}")
            return

        print(f"✅ Found Company: {company.name} (ID: {company.id})")
        
        # 2. Check Areas
        areas = ProcessArea.query.filter_by(company_id=company.id).all()
        print(f"\n--- Process Areas ({len(areas)}) ---")
        for area in areas:
            print(f"ID: {area.id}, Name: {area.name}")

        # 3. Check MacroProcesses
        macros = MacroProcess.query.filter_by(company_id=company.id).all()
        print(f"\n--- Macro Processes ({len(macros)}) ---")
        for macro in macros:
            print(f"ID: {macro.id}, Name: {macro.name}, Area ID: {macro.area_id}")

        # 4. Check Processes
        processes = Process.query.filter_by(company_id=company.id).all()
        print(f"\n--- Processes ({len(processes)}) ---")
        for proc in processes:
            print(f"ID: {proc.id}, Name: {proc.name}, Macro ID: {proc.macro_id}")

if __name__ == "__main__":
    inspect_gas_evolution_data()
