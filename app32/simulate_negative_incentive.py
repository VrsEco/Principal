from app import create_app
app = create_app()
from models import db, IncentiveRuleSet, IncentiveRule, Employee, IncentiveParticipant, IncentiveIndicator, IncentiveCalculation
from services.incentive_service import IncentiveService
from datetime import date, timedelta
import json
from decimal import Decimal

def run_simulation():
    with app.app_context():
        # 1. Setup Mock Environment
        company_id = 1 # Assuming standard dev company id
        
        # Clean up existing test data for today
        today = date.today()
        p_start = date(today.year, today.month, 1)
        p_end = today
        
        # Find or create a RuleSet
        rs = IncentiveRuleSet.query.filter_by(company_id=company_id).first()
        if not rs:
            rs = IncentiveRuleSet(company_id=company_id, name="Plano Simulação", periodicity="monthly")
            db.session.add(rs)
            db.session.commit()
            print(f"Created RuleSet: {rs.id}")

        # Update RuleSet: Global Max Reduction = 0.8
        rs.max_red_total = Decimal('0.80') 
        db.session.commit()
        print(f"Set Global Max Reduction: {rs.max_red_total}")

        # Ensure we have an Indicator
        ind = IncentiveIndicator.query.filter_by(company_id=company_id).first()
        if not ind:
            ind = IncentiveIndicator(company_id=company_id, code="SIM_IND", name="Indicador Simulação", source_module="manual")
            db.session.add(ind)
            db.session.commit()

        # Clean existing rules for simulation
        IncentiveRule.query.filter_by(rule_set_id=rs.id).delete()
        
        # 1. Multiplier Rule (Total 2.0)
        # Note: Sum of multipliers is additive. To get 2.0 total, we can use one rule of 2.0
        rule_mult = IncentiveRule(
            rule_set_id=rs.id,
            indicator_id=ind.id,
            vetor_type='multiplicador',
            impact_value=Decimal('2.00'),
            target_value=Decimal('100.00'),
            order_index=1
        )
        db.session.add(rule_mult)

        # 2. Reducer Rule (Total 1.4)
        rule_red = IncentiveRule(
            rule_set_id=rs.id,
            indicator_id=ind.id,
            vetor_type='redutor',
            impact_value=Decimal('1.40'),
            target_value=Decimal('100.00'),
            order_index=2
        )
        db.session.add(rule_red)
        db.session.commit()
        print(f"Added Vetors: Multiplier 2.0, Reducer 1.4")
        db.session.add(rule_red)
        db.session.commit()
        print(f"Added Massive Reducer Rule: {rule_red.id}")

        # Ensure some participants
        emp = Employee.query.filter_by(company_id=company_id, status='active').first()
        if not emp:
            print("No active employee found for simulation.")
            return

        part = IncentiveParticipant.query.filter_by(rule_set_id=rs.id, employee_id=emp.id).first()
        if not part:
            part = IncentiveParticipant(company_id=company_id, rule_set_id=rs.id, employee_id=emp.id, valor_base=Decimal('5000.00'), elegivel=True)
            db.session.add(part)
            db.session.commit()
        else:
            part.valor_base = Decimal('5000.00')
            part.elegivel = True
            db.session.commit()

        # 2. Run Calculation
        print(f"Running calculation for Employee: {emp.name}, Base: {part.valor_base}")
        results = IncentiveService.calculate_incentive(company_id, rs.id, p_start, p_end)
        
        # Verify result logic
        emp_result = next((p for p in results['participants'] if p['employee_id'] == emp.id), None)
        if emp_result:
            print("\nSIMULATION RESULTS:")
            print(f"Final Bonus: {emp_result['bonus']}")
            print(f"Unclamped Bonus: {emp_result['unclamped_bonus']}")
            print(f"Final Multiplier (Score): {emp_result['total_score']}")
            print(f"Unclamped Multiplier: {emp_result.get('unclamped_multiplier')}")
            print(f"Sum Multipliers (Piso 1.0): {emp_result.get('sum_multipliers')}")
            print(f"Sum Reductions (Capped by 0.5): {emp_result.get('sum_reductions')}")
            
            # Save to a new calculation record so we can view it in the UI
            calc = IncentiveCalculation(
                company_id=company_id,
                rule_set_id=rs.id,
                period_start=p_start,
                period_end=p_end,
                status='preview',
                results_payload=results
            )
            db.session.add(calc)
            db.session.commit()
            print(f"\nSaved Calculation ID: {calc.id}")
            print(f"URL TO VIEW EXTRATO: /incentives/statement/{calc.id}/{emp.id}")
        else:
            print("Failed to find employee in results.")

if __name__ == "__main__":
    run_simulation()
