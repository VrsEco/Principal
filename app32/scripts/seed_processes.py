from app import app
from models import db, Company, ProcessArea, MacroProcess, Process, ProcessRoutine, ProcessStep

def seed_processes():
    with app.app_context():
        # Get demo company
        company = Company.query.filter_by(client_code="VT001").first()
        if not company:
            print("Company VT001 not found. Run seed-demo first.")
            return

        # Check if areas exist
        if ProcessArea.query.filter_by(company_id=company.id).first():
            # If areas exist, check if routines exist. If not, maybe we can just add them.
            if ProcessRoutine.query.first():
                print("Processes and routines already seeded.")
                return
        else:
            print("Seeding processes background...")
            # 1. AREAS
            financeiro = ProcessArea(company_id=company.id, code="FIN", name="Financeiro", color="#3b82f6", order_index=1)
            rh = ProcessArea(company_id=company.id, code="RH", name="Recursos Humanos", color="#ef4444", order_index=2)
            comercial = ProcessArea(company_id=company.id, code="COM", name="Comercial", color="#10b981", order_index=3)
            
            db.session.add_all([financeiro, rh, comercial])
            db.session.commit()

            # 2. MACROS
            gestao_caixa = MacroProcess(company_id=company.id, area_id=financeiro.id, code="FIN.01", name="Gestão de Caixa", owner="Diretor Financeiro")
            talentos = MacroProcess(company_id=company.id, area_id=rh.id, code="RH.01", name="Atração de Talentos", owner="HRBP")
            
            db.session.add_all([gestao_caixa, talentos])
            db.session.commit()

            # 3. PROCESSES
            p_pagar = Process(company_id=company.id, macro_id=gestao_caixa.id, code="FIN.01.01", name="Contas a Pagar", responsible="Analista Financeiro", kanban_stage="stable")
            db.session.add(p_pagar)
            db.session.commit()

        # Add Routines and Steps to "Contas a Pagar"
        cp = Process.query.filter_by(name="Contas a Pagar").first()
        if cp and not ProcessRoutine.query.filter_by(process_id=cp.id).first():
            print("Seeding routines for Contas a Pagar...")
            r1 = ProcessRoutine(process_id=cp.id, code="R-01", name="Recepção de Notas", description="Processo de entrada de documentos fiscais.", order_index=1)
            r2 = ProcessRoutine(process_id=cp.id, code="R-02", name="Programação de Pagamento", description="Agendamento no ERP e aprovação.", order_index=2)
            db.session.add_all([r1, r2])
            db.session.commit()

            s1 = ProcessStep(routine_id=r1.id, name="Validar XML no portal", description="Checar se a nota está autorizada na SEFAZ.", order_index=1)
            s2 = ProcessStep(routine_id=r1.id, name="Conferir Pedido de Compra", description="Bater itens da nota com o pedido no sistema.", order_index=2)
            s3 = ProcessStep(routine_id=r2.id, name="Lançar no ERP", description="Inserir fatura no módulo financeiro.", order_index=1)
            
            db.session.add_all([s1, s2, s3])
            db.session.commit()
            print("Routines and steps seeded!")

        print("Seed operation complete.")

if __name__ == "__main__":
    seed_processes()
