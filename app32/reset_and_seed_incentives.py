from app import create_app
from models import db, Company, IncentiveIndicator, IncentiveRuleSet, IncentiveRule, Role, IncentiveGovernabilityMatrix, IncentiveFact, IncentiveCalculation, Employee
from services.incentive_service import IncentiveService
from datetime import datetime, date, timedelta
from decimal import Decimal
import logging

def reset_and_seed():
    app = create_app()
    with app.app_context():
        cid = 9 # Versus Principal
        company = Company.query.get(cid)
        if not company:
            print("Company 9 not found.")
            return

        print(f"--- RESETTING INCENTIVES FOR {company.name} ---")
        
        # 1. Clear Data
        IncentiveCalculation.query.filter_by(company_id=cid).delete()
        IncentiveFact.query.filter_by(company_id=cid).delete()
        IncentiveGovernabilityMatrix.query.filter_by(company_id=cid).delete()
        
        # Delete rules associated with company's rule sets
        rs_ids = [rs.id for rs in IncentiveRuleSet.query.filter_by(company_id=cid).all()]
        if rs_ids:
            IncentiveRule.query.filter(IncentiveRule.rule_set_id.in_(rs_ids)).delete(synchronize_session=False)
        
        IncentiveRuleSet.query.filter_by(company_id=cid).delete()
        IncentiveIndicator.query.filter_by(company_id=cid).delete()
        
        db.session.commit()
        print("Existing incentive data cleared.")

        # 2. Re-create Indicators
        indicators_data = [
            {"code": "FAT", "name": "Faturamento Mensal", "type": "collective", "module": "financeiro"},
            {"code": "EFI_IND", "name": "Eficiência Individual", "type": "individual", "module": "process"},
            {"code": "NPS", "name": "NPS (Satisfação Cliente)", "type": "collective", "module": "qualidade"},
            {"code": "AUDIT", "name": "Conformidade Auditoria", "type": "individual", "module": "quality"}
        ]

        inds = []
        for data in indicators_data:
            ind = IncentiveIndicator(
                company_id=cid,
                code=data["code"],
                name=data["name"],
                indicator_type=data["type"],
                source_module=data["module"],
                is_active=True
            )
            db.session.add(ind)
            inds.append(ind)
        db.session.flush()

        # 3. Create Rule Set
        rs = IncentiveRuleSet(
            company_id=cid,
            name="Plano Elite de Alta Performance v2.0",
            description="Modelo oficial de bônus baseado em KPIs da Engenharia de Elite.",
            periodicity="monthly",
            version=1,
            is_active=True
        )
        db.session.add(rs)
        db.session.flush()

        # 4. Create Rules
        # Weights: FAT(40%), EFI(30%), NPS(20%), AUDIT(10%)
        rules_config = [
            (inds[0], 0.40, 500000), # Target 500k
            (inds[1], 0.30, 100),    # Target 100 weight
            (inds[2], 0.20, 85),     # Target 85 NPS
            (inds[3], 0.10, 10)      # Target 10 audits
        ]

        for ind, weight, target in rules_config:
            rule = IncentiveRule(
                rule_set_id=rs.id,
                indicator_id=ind.id,
                weight=Decimal(str(weight)),
                target_value=Decimal(str(target)),
                min_threshold=Decimal('0.70'),
                max_cap=Decimal('1.50'),
                impact_type='multiplier' if ind.indicator_type == 'collective' else 'individual'
            )
            db.session.add(rule)
        
        db.session.commit()

        # 5. Populate Facts for Employees
        employees = Employee.query.filter_by(company_id=cid).all()
        if not employees:
            print("No employees found to seed facts.")
            return
            
        today = date.today()
        # Last month
        last_month_start = (today.replace(day=1) - timedelta(days=1)).replace(day=1)
        last_month_end = today.replace(day=1) - timedelta(days=1)
        
        # Collective Facts (FAT e NPS)
        db.session.add(IncentiveFact(
            company_id=cid, indicator_id=inds[0].id, employee_id=None,
            period_start=last_month_start, period_end=last_month_end,
            value=Decimal('520000'), status='verified'
        ))
        db.session.add(IncentiveFact(
            company_id=cid, indicator_id=inds[2].id, employee_id=None,
            period_start=last_month_start, period_end=last_month_end,
            value=Decimal('92'), status='verified'
        ))

        # Individual Facts
        import random
        for emp in employees:
            # Efficiency
            db.session.add(IncentiveFact(
                company_id=cid, indicator_id=inds[1].id, employee_id=emp.id,
                period_start=last_month_start, period_end=last_month_end,
                value=Decimal(str(random.randint(80, 120))), status='verified'
            ))
            # Audit
            db.session.add(IncentiveFact(
                company_id=cid, indicator_id=inds[3].id, employee_id=emp.id,
                period_start=last_month_start, period_end=last_month_end,
                value=Decimal(str(random.randint(8, 12))), status='verified'
            ))
        
        db.session.commit()
        print(f"Facts seeded for {len(employees)} employees.")

        # 6. Run Calculation
        print("Running calculation pipeline...")
        result = IncentiveService.calculate_incentive(cid, rs.id, last_month_start, last_month_end)
        
        if "error" in result:
            print(f"Calculation Error: {result['error']}")
        else:
            print(f"Calculation DONE. ID: {result['calculation_id']}, Total: {result['total_payout']}")
            # Force status to 'calculated' or 'approved' for display
            calc = IncentiveCalculation.query.get(result['calculation_id'])
            calc.status = 'calculated'
            db.session.commit()

        print("--- SEED COMPLETED SUCCESSFULLY ---")

if __name__ == "__main__":
    reset_and_seed()
