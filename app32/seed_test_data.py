import sys
import os
from datetime import datetime, date, timedelta
from decimal import Decimal

# Add project root to sys.path
sys.path.append(os.path.abspath('.'))

from app import create_app
from models import db, Company, Indicator, IndicatorTree, IndicatorGoal, IndicatorData, IncentiveRuleSet, IncentiveRule, IncentiveParticipant, Employee

app = create_app()

def seed():
    with app.app_context():
        # 1. Get Company
        company = Company.query.filter(Company.name.ilike('%Gas Evolution%')).first()
        if not company:
            company = Company.query.first()
        
        if not company:
            print("No company found.")
            return
        cid = company.id
        print(f"Using Company: {company.name} (ID: {cid})")

        # 2. Get Employee (preferably one with a user_id)
        emp = Employee.query.filter_by(company_id=cid).filter(Employee.user_id.isnot(None)).first()
        if not emp:
            emp = Employee.query.filter_by(company_id=cid).first()
        
        if not emp:
            print("No employee found.")
            return
        print(f"Using Employee: {emp.name} (ID: {emp.id})")

        # 3. Create/Get IndicatorTree
        tree = IndicatorTree.query.filter_by(company_id=cid).first()
        if not tree:
            tree = IndicatorTree(
                company_id=cid,
                code="1",
                name="Performance Operacional"
            )
            db.session.add(tree)
            db.session.flush()

        # 4. Create Indicators
        # Indicator 1: Faturamento (Result)
        ind_code1 = f"FAT_{cid}_001"
        ind1 = Indicator.query.filter_by(company_id=cid, code=ind_code1).first()
        if not ind1:
            ind1 = Indicator(
                company_id=cid,
                tree_id=tree.id,
                code=ind_code1,
                full_code=f"{company.client_code or 'VS'}.I.FAT.{cid}.001",
                name="Faturamento Bruto (Teste)",
                indicator_type="result",
                polarity="positive",
                unit="R$",
                is_active=True
            )
            db.session.add(ind1)
            db.session.flush()

        # Indicator 2: NPS (Multiplier)
        ind_code2 = f"QUAL_{cid}_001"
        ind2 = Indicator.query.filter_by(company_id=cid, code=ind_code2).first()
        if not ind2:
            ind2 = Indicator(
                company_id=cid,
                tree_id=tree.id,
                code=ind_code2,
                full_code=f"{company.client_code or 'VS'}.I.QUAL.{cid}.001",
                name="NPS / Qualidade (Teste)",
                indicator_type="result",
                polarity="positive",
                unit="%",
                is_active=True
            )
            db.session.add(ind2)
            db.session.flush()

        # 5. Create Goals for LAST MONTH (Reference period for closing tests)
        today = date.today()
        # Find first day of last month
        first_day_this_month = today.replace(day=1)
        last_day_last_month = first_day_this_month - timedelta(days=1)
        first_day_last_month = last_day_last_month.replace(day=1)
        
        start_date = first_day_last_month
        end_date = last_day_last_month
        
        print(f"Goal Period: {start_date} to {end_date}")

        goal1 = IndicatorGoal.query.filter_by(indicator_id=ind1.id, period_start=start_date).first()
        if not goal1:
            goal1 = IndicatorGoal(
                company_id=cid,
                indicator_id=ind1.id,
                goal_value=100000,
                period_start=start_date,
                period_end=end_date,
                status="active",
                performance_ranges={"red": 80, "yellow": 90, "green": 100}
            )
            db.session.add(goal1)

        goal2 = IndicatorGoal.query.filter_by(indicator_id=ind2.id, period_start=start_date).first()
        if not goal2:
            goal2 = IndicatorGoal(
                company_id=cid,
                indicator_id=ind2.id,
                goal_value=90,
                period_start=start_date,
                period_end=end_date,
                status="active",
                performance_ranges={"red": 70, "yellow": 85, "green": 95}
            )
            db.session.add(goal2)
        
        db.session.flush()

        # 6. Create Data (Facts)
        # Ind1: Realized 110% (Achievement = 1.1)
        # individual fact for the target employee
        data1 = IndicatorData.query.filter_by(indicator_id=ind1.id, employee_id=emp.id, period_start=start_date).first()
        if not data1:
            data1 = IndicatorData(
                company_id=cid,
                indicator_id=ind1.id,
                goal_id=goal1.id,
                employee_id=emp.id,
                measured_value=110000,
                measured_date=end_date,
                period_start=start_date,
                period_end=end_date,
                status="verified",
                is_manual=False
            )
            db.session.add(data1)

        # Ind2: Realized 95% (Achievement = 95/90 = 1.055)
        # Flagging as manual adjustment to test visual indicator
        data2 = IndicatorData.query.filter_by(indicator_id=ind2.id, employee_id=emp.id, period_start=start_date).first()
        if not data2:
            data2 = IndicatorData(
                company_id=cid,
                indicator_id=ind2.id,
                goal_id=goal2.id,
                employee_id=emp.id,
                measured_value=95,
                measured_date=end_date,
                period_start=start_date,
                period_end=end_date,
                status="manual_override",
                is_manual=True,
                notes="Ajuste manual decorrente de auditoria de tickets."
            )
            db.session.add(data2)

        # 7. Create RuleSet
        ts = datetime.now().strftime("%H:%M")
        plan_name = f"Plano Estratégico ({ts})"
        rs = IncentiveRuleSet(
            company_id=cid,
            name=plan_name,
            description="Plano padrão para testes de bônus e multiplicadores.",
            periodicity="monthly",
            is_active=True
        )
        db.session.add(rs)
        db.session.flush()

        # 8. Create Rules
        # Rule 1: Faturamento -> Multiplicador Base (Impacto 1.0 se bater a meta)
        rule1 = IncentiveRule.query.filter_by(rule_set_id=rs.id, indicator_id=ind1.id).first()
        if not rule1:
            rule1 = IncentiveRule(
                company_id=cid,
                rule_set_id=rs.id,
                indicator_id=ind1.id,
                vetor_type="bonus", # contribui para o bônus principal
                impact_value=1.0, 
                calculation_mode="ranges",
                use_indicator_goal=True,
                order_index=1,
                incidencia="individual"
            )
            db.session.add(rule1)

        # Rule 2: QUALIDADE -> Multiplicador Adicional (Impacto 0.2 se bater a meta)
        rule2 = IncentiveRule.query.filter_by(rule_set_id=rs.id, indicator_id=ind2.id).first()
        if not rule2:
            rule2 = IncentiveRule(
                company_id=cid,
                rule_set_id=rs.id,
                indicator_id=ind2.id,
                vetor_type="multiplicador",
                impact_value=1.2,
                calculation_mode="ranges",
                use_indicator_goal=True,
                order_index=2,
                incidencia="individual"
            )
            db.session.add(rule2)

        # 9. Add Participant
        part = IncentiveParticipant.query.filter_by(rule_set_id=rs.id, employee_id=emp.id).first()
        if not part:
            part = IncentiveParticipant(
                company_id=cid,
                rule_set_id=rs.id,
                employee_id=emp.id,
                valor_base=3000.0,
                elegivel=True
            )
            db.session.add(part)

        db.session.commit()
        print("--- SUMMARY ---")
        print(f"Period: {start_date.strftime('%m/%Y')}")
        print(f"RuleSet: {rs.name}")
        print(f"Participant: {emp.name} (Base Wage: R$ 3000,00)")
        print(f"Indicador 1 (FAT): Realizado R$ 110k / Meta R$ 100k -> 110% Achiv.")
        print(f"Indicador 2 (NPS): Realizado 95% / Meta 90% -> 105% Achiv. (MANUAL)")
        print("Data seeded successfully!")

if __name__ == "__main__":
    seed()
