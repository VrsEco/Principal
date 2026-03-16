from app import create_app
app = create_app()
from models import db, IncentiveRuleSet, IncentiveRule, Employee, IncentiveParticipant, IncentiveIndicator, IncentiveCalculation
from services.incentive_service import IncentiveService
from datetime import date
from decimal import Decimal

def run_simulation():
    with app.app_context():
        # Configuration
        company_id = 1
        today = date.today()
        p_start = date(today.year, today.month, 1)
        p_end = today
        
        # 1. Setup RuleSet with the requested limit
        rs = IncentiveRuleSet.query.filter_by(company_id=company_id).first()
        if not rs:
            rs = IncentiveRuleSet(company_id=company_id, name="Plano Teste Capped", periodicity="monthly")
            db.session.add(rs)
            db.session.commit()
        
        rs.max_red_total = Decimal('0.80') # LIMITADOR DE REDUTOR DE 0.8
        db.session.commit()

        # 2. Setup Indicator (Ensuring it is 'manual' so we can provide a fact)
        ind = IncentiveIndicator.query.filter_by(company_id=company_id, code="SIM_IND").first()
        if not ind:
            ind = IncentiveIndicator(
                company_id=company_id, 
                code="SIM_IND", 
                name="Indicador Simulação", 
                source_module="manual",
                collection_mode="manual"
            )
            db.session.add(ind)
            db.session.commit()
        else:
            ind.collection_mode = "manual"
            db.session.commit()

        # 3. Setup Participant
        emp = Employee.query.filter_by(company_id=company_id, status='active').first()
        if not emp:
            print("No active employee found.")
            return

        part = IncentiveParticipant.query.filter_by(rule_set_id=rs.id, employee_id=emp.id).first()
        if not part:
            part = IncentiveParticipant(company_id=company_id, rule_set_id=rs.id, employee_id=emp.id, valor_base=Decimal('5000.00'), elegivel=True)
            db.session.add(part)
        else:
            part.valor_base = Decimal('5000.00')
            part.elegivel = True
        db.session.commit()

        # 4. Insert Fact (100% attainment for the participant)
        from models import IncentiveFact
        IncentiveFact.query.filter_by(indicator_id=ind.id, employee_id=emp.id, period_start=p_start).delete()
        fact = IncentiveFact(
            company_id=company_id,
            indicator_id=ind.id,
            employee_id=emp.id,
            period_start=p_start,
            period_end=p_end,
            value=Decimal('100.00'), # Value = 100
            status='verified'
        )
        db.session.add(fact)
        db.session.commit()

        # 5. Setup Rules (Clean old simulation rules first)
        IncentiveRule.query.filter_by(rule_set_id=rs.id).delete()
        
        # Multiplier Total: 2.0 (Target is 100, Fact is 100 -> Atingimento 1.0)
        # 1.0 * 2.0 = 2.0 contribution
        rule_mult = IncentiveRule(
            rule_set_id=rs.id,
            indicator_id=ind.id,
            vetor_type='multiplicador',
            impact_value=Decimal('2.00'),
            target_value=Decimal('100.00'),
            order_index=1
        )
        db.session.add(rule_mult)

        # Reducer: 1.4
        # Since achievement = 1.0 (100%), Reducer formula = impact * (1 - achievement) = 1.4 * (1 - 1.0) = 0.
        # WAIT: The user wants "Redutor de 1.4". In the context of business rules, 
        # usually 1.4 is the "MAXIMUM penalty" if you do NOTHING (0% attainment).
        # To simulate a 1.4 reducer ACTIVE, we need achievement = 0.
        
        # Let's adjust the fact to 0 to simulate the REDUCER being at its peak (1.4)
        fact.value = Decimal('0.00')
        db.session.commit()
        # BUT then Multiplier would be 0. 
        # So we need TWO indicators if we want both active at a specific value, 
        # OR we just use a constant logic for this simulation.
        
        # Let's use two indicators to be precise.
        ind_mult = ind
        ind_red = IncentiveIndicator(
                company_id=company_id, 
                code="SIM_RED", 
                name="Ind Redutor", 
                source_module="manual",
                collection_mode="manual"
            )
        db.session.add(ind_red)
        db.session.commit()
        
        # Fact for Multiplier: 100% (Realized 100, Target 100) -> Contribution = 2.0
        fact_mult = fact
        fact_mult.value = Decimal('100.00')
        
        # Fact for Reducer: 0% (Realized 0, Target 100) -> Penalty = 1.4 * (1 - 0) = 1.4
        fact_red = IncentiveFact(
            company_id=company_id,
            indicator_id=ind_red.id,
            employee_id=emp.id,
            period_start=p_start,
            period_end=p_end,
            value=Decimal('0.00'),
            status='verified'
        )
        db.session.add(fact_red)
        
        rule_red = IncentiveRule(
            rule_set_id=rs.id,
            indicator_id=ind_red.id,
            vetor_type='redutor',
            impact_value=Decimal('1.40'),
            target_value=Decimal('100.00'),
            order_index=2
        )
        db.session.add(rule_red)
        db.session.commit()

        # 5. Run Calculation
        print(f"--- SIMULATION: MULT 2.0, RED 1.4, CAP 0.8 ---")
        results = IncentiveService.calculate_incentive(company_id, rs.id, p_start, p_end)
        
        emp_result = next((p for p in results['participants'] if p['employee_id'] == emp.id), None)
        if emp_result:
            print(f"Base: R$ {emp_result['base_value']}")
            print(f"Total Multiplicadores: {emp_result['sum_multipliers']} (Deveria ser 2.0)")
            print(f"Total Redutores: {emp_result['sum_reductions']} (Deveria ser 0.8 devido ao cap)")
            print(f"Fator de Score Final: {emp_result['total_score']} (Deveria ser 2.0 - 0.8 = 1.2)")
            print(f"Bônus Final: R$ {emp_result['bonus']}")
            
            # Create record to view
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
            print(f"View in UI: /incentives/statement/{calc.id}/{emp.id}")

if __name__ == "__main__":
    run_simulation()
