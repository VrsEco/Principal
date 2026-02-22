from app import create_app
from models import db, Plan, PlanImplantationData, Company
from services.plan_service import PlanService
import json

def seed_finance():
    app = create_app()
    with app.app_context():
        # Get or create a test company
        company = Company.query.filter_by(name="Test Company").first()
        if not company:
            company = Company(name="Test Company")
            db.session.add(company)
            db.session.commit()

        # Create a test plan
        plan = Plan.query.filter_by(title="Plano de Expansão TESTE").first()
        if not plan:
            plan = Plan(
                title="Plano de Expansão TESTE",
                company_id=company.id,
                mode='implantation'
            )
            db.session.add(plan)
            db.session.commit()

        # 1. Seed Model Data (Products)
        model_content = {
            "products": [
                {
                    "name": "Produto A",
                    "sale_price": 1000.0,
                    "variable_costs_value": 350.0,
                    "variable_expenses_value": 150.0,
                    "market_share_goal_monthly_units": 100,
                    "ramp_up_entries": [
                        {"month_period": "2025.01", "percentage": 10},
                        {"month_period": "2025.02", "percentage": 30},
                        {"month_period": "2025.03", "percentage": 60},
                        {"month_period": "2025.04", "percentage": 100},
                        {"month_period": "2025.05", "percentage": 100},
                        {"month_period": "2025.06", "percentage": 100}
                    ]
                }
            ],
            "segments": []
        }
        PlanService.save_implantation_data(plan.id, company.id, 'model', model_content)

        # 2. Seed Execution Data (Investments and Fixed Costs)
        exec_content = {
            "areas": {
                "admin": {
                    "items": [
                        {
                            "description": "Aluguel Admin (Despesa Fixa)",
                            "classification": "mensal",
                            "item_type": "infra",
                            "value": 2000,
                            "payments": [
                                {"date": "2025.01", "amount": 2000},
                                {"date": "2025.02", "amount": 2000},
                                {"date": "2025.03", "amount": 2000}
                            ]
                        }
                    ]
                },
                "operacional": {
                    "items": [
                        {
                            "description": "Equipe Op (Custo Fixo)",
                            "classification": "contratação",
                            "item_type": "pessoas",
                            "value": 5000,
                            "payments": [
                                {"date": "2025.01", "amount": 5000},
                                {"date": "2025.02", "amount": 5000},
                                {"date": "2025.03", "amount": 5000}
                            ]
                        }
                    ]
                }
            }
        }
        PlanService.save_implantation_data(plan.id, company.id, 'execution', exec_content)

        # 3. Seed Finance Premises
        fin_content = {
            "analysis_params": {"period_months": 24, "opportunity_cost_annual": 12.0},
            "working_capital": {"cash_reserve": 10000, "receivables_days": 30, "inventory_days": 0, "payable_days": 30},
            "sources": {"Aporte": 50000},
            "source_dates": {"Aporte": "2025.01"},
            "profit_distribution": [{"description": "Dividendos", "percentage": 50}]
        }
        PlanService.save_implantation_data(plan.id, company.id, 'finance', fin_content)

        # 4. Verify Consolidation
        consolidated = PlanService.get_consolidated_finance(plan.id, company.id)
        if consolidated and 'metrics' in consolidated:
            print(f"Plan ID: {plan.id}")
            print(f"VPL: {consolidated['metrics']['vpl']}")
            print(f"TIR: {consolidated['metrics']['tir']}%")
            print(f"Payback: {consolidated['metrics']['payback']} meses")
            
            if consolidated['timeline']:
                m1 = consolidated['timeline'][0]
                print(f"\nDRE Mês 1 ({m1['period']}):")
                print(f"  Faturamento: {m1['revenue']}")
                print(f"  Custos Var: {m1['variable_costs']}")
                print(f"  Desp Var: {m1['variable_expenses']}")
                print(f"  GMC: {m1['gmc']}")
                print(f"  Custos Fixos: {m1['fixed_costs']}")
                print(f"  Desp Fixas: {m1['fixed_expenses']}")
                print(f"  Resultado: {m1['operating_result']}")
        
        print("\nSeed financeiro concluído com sucesso!")

if __name__ == "__main__":
    seed_finance()
