from app import app
from models import db, Company, ProcessArea, MacroProcess, Process
import sys

def check_data():
    with app.app_context():
        # Busca a empresa
        search_term = "Versus"
        print(f"Buscando empresas com o termo: '{search_term}'...")
        companies = Company.query.filter(Company.name.ilike(f'%{search_term}%')).all()
        
        if not companies:
            print(f"Nenhuma empresa contendo '{search_term}' encontrada.")
            return

        print("Empresas encontradas:")
        for c in companies:
            print(f"- {c.name} (ID: {c.id})")
        
        # Tenta encontrar a mais provável
        company = None
        for c in companies:
            if "AA -" in c.name or "Versus Gestão Corporativa" in c.name or "Versus Gestao Corporativa" in c.name:
                company = c
                break
        
        if not company:
            print("\nNão foi possível identificar a empresa exata solicitada.")
            return

        print(f"\nSelecionada: {company.name} (ID: {company.id})")

        print("-" * 50)

        # Buscar Áreas
        areas = ProcessArea.query.filter_by(company_id=company.id).order_by(ProcessArea.order_index).all()
        if not areas:
            print("Nenhuma área cadastrada.")
            return

        for area in areas:
            print(f"\n[ÁREA] {area.name} (ID: {area.id})")
            
            # Buscar Macroprocessos
            macros = MacroProcess.query.filter_by(area_id=area.id).order_by(MacroProcess.order_index).all()
            if not macros:
                print("  (Sem macroprocessos)")
                continue

            for macro in macros:
                print(f"  [MACRO] {macro.name} (ID: {macro.id})")
                
                # Buscar Processos
                processes = Process.query.filter_by(macro_id=macro.id).order_by(Process.order_index).all()
                if not processes:
                    print("    (Sem processos)")
                    continue

                for process in processes:
                    print(f"    [PROCESSO] {process.name} (ID: {process.id})")

if __name__ == "__main__":
    check_data()
