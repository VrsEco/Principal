import sys
import os
from datetime import datetime, date

# Padronizacao de caminho para raiz app32
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))

from app import create_app
from models import (
    db, Company, IndicatorGroup, Indicator, IndicatorGoal, IndicatorData
)

app = create_app()

def deep_seed_finance():
    with app.app_context():
        print("--- SIMULACAO DE PERFORMANCE FINANCEIRA: TITAN CORP ---")
        
        company = Company.query.filter_by(name="Titan Corp").first()
        if not company:
            print("ERRO: Execute o seed da Titan Corp primeiro.")
            return

        # 1. GRUPO
        group = IndicatorGroup.query.filter_by(company_id=company.id, code="FIN").first()
        if not group:
            group = IndicatorGroup(company_id=company.id, name="Financeiro", code="FIN")
            db.session.add(group)
            db.session.commit()

        # 2. INDICADOR: MRR (Check por CODE)
        ind_code = "MRR-01"
        indicator = Indicator.query.filter_by(code=ind_code).first()
        if not indicator:
            indicator = Indicator(
                company_id=company.id,
                group_id=group.id,
                name="Faturamento Mensal Recorrente (MRR)",
                code=ind_code,
                unit="R$",
                polarity="positive"
            )
            db.session.add(indicator)
            db.session.commit()

        # 3. META
        goal = IndicatorGoal.query.filter_by(indicator_id=indicator.id).first()
        if not goal:
            goal = IndicatorGoal(
                company_id=company.id,
                indicator_id=indicator.id,
                goal_value=4000000.00,
                goal_date=date(2026, 12, 31),
                status="active",
                goal_type="monthly"
            )
            db.session.add(goal)
            db.session.commit()

        # 4. REALIZADO
        data_records = [
            {"record_date": date(2026, 1, 31), "value": 850000.00},
            {"record_date": date(2026, 2, 28), "value": 1100000.00}
        ]
        
        for d_info in data_records:
            if not IndicatorData.query.filter_by(goal_id=goal.id, record_date=d_info['record_date']).first():
                db.session.add(IndicatorData(company_id=company.id, goal_id=goal.id, **d_info))

        db.session.commit()
        print(f"\n--- SUCESSO: Gestao Financeira da Titan Corp alimentada. ---")

if __name__ == "__main__":
    deep_seed_finance()
