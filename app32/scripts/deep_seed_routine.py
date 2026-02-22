import sys
import os
from datetime import datetime

# Padronizacao de caminho para raiz app32
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))

from app import create_app
from models import (
    db, Company, ProcessArea, MacroProcess, Process, 
    ProcessRoutine, ProcessStep, ProcessInstance
)

app = create_app()

def deep_seed_routine():
    with app.app_context():
        print("--- SIMULACAO DE ROTINA OPERACIONAL: TITAN CORP ---")
        
        company = Company.query.filter_by(name="Titan Corp").first()
        if not company:
            print("ERRO: Execute o seed da Titan Corp primeiro.")
            return

        # 1. AREA
        area = ProcessArea.query.filter_by(company_id=company.id, name="Operacoes de IA").first()
        if not area:
            area = ProcessArea(company_id=company.id, name="Operacoes de IA", code="IA-OPS")
            db.session.add(area)
            db.session.commit()

        # 2. MACRO
        macro = MacroProcess.query.filter_by(area_id=area.id, name="Ciclo de Vida do Modelo").first()
        if not macro:
            macro = MacroProcess(company_id=company.id, area_id=area.id, name="Ciclo de Vida do Modelo", code="CV-MOD")
            db.session.add(macro)
            db.session.commit()

        # 3. PROCESSO
        process = Process.query.filter_by(macro_id=macro.id, name="Curadoria de Dados").first()
        if not process:
            process = Process(company_id=company.id, macro_id=macro.id, name="Curadoria de Dados", code="DATA-CUR")
            db.session.add(process)
            db.session.commit()

        # 4. ROTINA
        routine = ProcessRoutine.query.filter_by(process_id=process.id, name="Higienizacao de Datasets").first()
        if not routine:
            routine = ProcessRoutine(process_id=process.id, name="Higienizacao de Datasets", code="POP-DATA-01")
            db.session.add(routine)
            db.session.commit()

        # 5. PASSOS (POP)
        print("-> Seed Passos (POP)")
        if ProcessStep.query.filter_by(routine_id=routine.id).count() == 0:
            s1 = ProcessStep(routine_id=routine.id, name="Deteccao de Corrupcao", description="Validar Hash", order_index=0)
            s2 = ProcessStep(routine_id=routine.id, name="Remocao de Duplicatas", description="Executar dedup", order_index=1)
            db.session.add_all([s1, s2])

        db.session.commit()
        print(f"\n--- SUCESSO: Rotina alimentada. ---")

if __name__ == "__main__":
    deep_seed_routine()
