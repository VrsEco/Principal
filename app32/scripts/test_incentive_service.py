import os
from datetime import date, timedelta
from app import create_app
from services.incentive_service import IncentiveService
from models import Company, IncentiveFact, IncentiveIndicator, IncentiveRuleSet

def test_service():
    app = create_app()
    with app.app_context():
        company = Company.query.first()
        if not company:
            print("Nenhuma empresa para testar.")
            return

        print(f"--- Testando IncentiveService para {company.name} ---")
        
        today = date.today()
        start = today - timedelta(days=30)
        end = today + timedelta(days=1)

        # 1. Test Harvesting
        print("\n1. Executando Harvesting (Projetos e Ocorrências)...")
        IncentiveService.harvest_project_facts(company.id, start, end)
        IncentiveService.harvest_occurrence_facts(company.id, start, end)
        
        facts = IncentiveFact.query.filter_by(company_id=company.id).all()
        print(f"Fatos gerados: {len(facts)}")
        for f in facts:
            ind = IncentiveIndicator.query.get(f.indicator_id)
            print(f" - Indicador: {ind.name} | Valor: {f.value} | Colaborador ID: {f.employee_id}")

        # 2. Test Calculation
        print("\n2. Executando Cálculo de Incentivo...")
        ruleset = IncentiveRuleSet.query.filter_by(company_id=company.id).first()
        if ruleset:
            calc_res = IncentiveService.calculate_incentive(company.id, ruleset.id, start, end)
            print(f"Cálculo concluído! ID: {calc_res['calculation_id']}")
            print(f"Total a distribuir: {calc_res['total_payout']}")
            for p in calc_res['participants']:
                print(f" - Colaborador: {p['name']} | Bônus: {p['bonus']}")
        else:
            print("Nenhum RuleSet encontrado para calcular.")

        # 3. Test Governability Report
        print("\n3. Gerando Relatório de Governabilidade (Spider Web Data)...")
        report = IncentiveService.get_governability_report(company.id)
        if not report:
            print("Nenhuma conexão encontrada na matriz.")
        for item in report:
            print(f" - Cargo: {item['role']} -> Indicador: {item['indicator']} ({item['level']})")

if __name__ == "__main__":
    test_service()
