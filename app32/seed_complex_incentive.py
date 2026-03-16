import os
import sys
import traceback
from datetime import date, datetime
from decimal import Decimal

# Add current directory to path
sys.path.append(os.getcwd())

from app import create_app
from models import (
    db, Company, Employee, IndicatorTree, Indicator, 
    IndicatorGoal, IndicatorData, IncentiveRuleSet, 
    IncentiveRule, IncentiveParticipant, IncentiveCalculation
)

app = create_app()

def seed_complex():
    try:
        with app.app_context():
            # 1. Get Company: Gás Evolution
            company = Company.query.filter(Company.name.ilike('%Gas Evolution%')).first()
            if not company:
                print("Gás Evolution not found. Aborting.")
                return
            cid = company.id
            print(f"--- Seeding Complex Case for: {company.name} (ID: {cid}) ---")

            # 2. Get Indicator Tree
            tree = IndicatorTree.query.filter_by(company_id=cid).first()
            if not tree:
                tree = IndicatorTree(company_id=cid, name="Árvore Estratégica Gás Evolution")
                db.session.add(tree)
                db.session.flush()

            # 3. Create Indicators
            indicators_data = [
                {"code": "EBITDA", "name": "EBITDA Mensal", "type": "result", "polarity": "positive", "unit": "R$"},
                {"code": "CHURN", "name": "Churn Rate (Cancelamentos)", "type": "result", "polarity": "negative", "unit": "%"},
                {"code": "ACID", "name": "Acidentes de Trabalho", "type": "occurrence", "polarity": "negative", "unit": "un"},
                {"code": "NPS_G", "name": "NPS Global", "type": "result", "polarity": "positive", "unit": "pts"}
            ]

            inds = {}
            for row in indicators_data:
                code = f"{row['code']}_ULTRA_{cid}" 
                ind = Indicator.query.filter_by(company_id=cid, code=code).first()
                if not ind:
                    ind = Indicator(
                        company_id=cid,
                        tree_id=tree.id,
                        code=code,
                        full_code=f"GE.ULTRA.{row['code']}.{cid}",
                        name=f"{row['name']} (Ultra)",
                        indicator_type=row['type'],
                        polarity=row['polarity'],
                        unit=row['unit'],
                        is_active=True,
                        measurement_frequency='monthly'
                    )
                    db.session.add(ind)
                    db.session.flush()
                inds[row['code']] = ind

            # 4. Set Goals for February 2026
            start_date = date(2026, 2, 1)
            end_date = date(2026, 2, 28)
            
            goals_config = {
                "EBITDA": {"val": 500000},
                "CHURN": {"val": 2},
                "ACID": {"val": 0},
                "NPS_G": {"val": 85}
            }

            goals = {}
            for key, config in goals_config.items():
                ind = inds[key]
                goal = IndicatorGoal.query.filter_by(indicator_id=ind.id, period_start=start_date).first()
                if not goal:
                    goal = IndicatorGoal(
                        company_id=cid,
                        indicator_id=ind.id,
                        code=f"GU_{key}_{cid}_{datetime.now().strftime('%M%S')}",
                        goal_value=config['val'],
                        period_start=start_date,
                        period_end=end_date,
                        status="active"
                    )
                    db.session.add(goal)
                    db.session.flush()
                goals[key] = goal

            # 5. Create RuleSet (The Plan)
            ts = datetime.now().strftime("%H%M%S")
            plan_name = f"Plano Estratégico GVT ({ts})"
            rs = IncentiveRuleSet(
                company_id=cid,
                name=plan_name,
                description="Fechamento ultra completo com 4 vetores.",
                periodicity="monthly",
                is_active=True
            )
            db.session.add(rs)
            db.session.flush()

            # 6. Add Rules
            db.session.add(IncentiveRule(company_id=cid, rule_set_id=rs.id, indicator_id=inds['EBITDA'].id, vetor_type="bonus", impact_value=1.0, incidencia="coletiva_empresa", order_index=1))
            db.session.add(IncentiveRule(company_id=cid, rule_set_id=rs.id, indicator_id=inds['CHURN'].id, vetor_type="multiplicador", impact_value=1.2, incidencia="coletiva_empresa", order_index=2))
            db.session.add(IncentiveRule(company_id=cid, rule_set_id=rs.id, indicator_id=inds['NPS_G'].id, vetor_type="multiplicador", impact_value=1.1, incidencia="individual", order_index=3))
            db.session.add(IncentiveRule(company_id=cid, rule_set_id=rs.id, indicator_id=inds['ACID'].id, vetor_type="bloqueador", impact_value=0, incidencia="coletiva_empresa", order_index=4))

            # 7. Collective Data (WITH goal_id)
            db.session.add(IndicatorData(company_id=cid, indicator_id=inds['EBITDA'].id, goal_id=goals['EBITDA'].id, measured_value=550000, measured_date=end_date, period_start=start_date, period_end=end_date, status='verified'))
            db.session.add(IndicatorData(company_id=cid, indicator_id=inds['CHURN'].id, goal_id=goals['CHURN'].id, measured_value=1.1, measured_date=end_date, period_start=start_date, period_end=end_date, status='verified'))
            db.session.add(IndicatorData(company_id=cid, indicator_id=inds['ACID'].id, goal_id=goals['ACID'].id, measured_value=0, measured_date=end_date, period_start=start_date, period_end=end_date, status='verified'))

            # 8. Participants and Individual Data
            names = ["Fabiano Ferreira", "Quesia", "Sandro", "Victor"]
            for name in names:
                emp = Employee.query.filter(Employee.name.ilike(f"%{name}%"), Employee.company_id == cid).first()
                if emp:
                    db.session.add(IncentiveParticipant(company_id=cid, rule_set_id=rs.id, employee_id=emp.id, valor_base=Decimal('3000') if name != "Fabiano Ferreira" else Decimal('5000'), elegivel=True))
                    # Individual Fact (NPS) with goal_id
                    db.session.add(IndicatorData(
                        company_id=cid, indicator_id=inds['NPS_G'].id, goal_id=goals['NPS_G'].id, 
                        employee_id=emp.id, measured_value=92 if name == "Fabiano Ferreira" else 72, 
                        measured_date=end_date, period_start=start_date, period_end=end_date, status='verified'
                    ))

            db.session.commit()
            print(f"Plan '{plan_name}' seeded successfully.")
            print(f"Participants: {len(names)}")
    except Exception:
        traceback.print_exc()

if __name__ == "__main__":
    seed_complex()
