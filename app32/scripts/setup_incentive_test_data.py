import os
from datetime import date, datetime
from decimal import Decimal
from app import create_app
from models import (
    db, Company, Role, Employee, IncentiveIndicator, 
    IncentiveRuleSet, IncentiveRule, IncentiveGovernabilityMatrix,
    Occurrence
)

def setup():
    app = create_app()
    with app.app_context():
        # 1. Get a company (preferably a test one or the first one)
        company = Company.query.first()
        if not company:
            print("Nenhuma empresa encontrada.")
            return

        print(f"Usando Empresa: {company.name} (ID: {company.id})")

        # 2. Setup Indicators
        # Individual Performance
        ind_vendas = IncentiveIndicator.query.filter_by(company_id=company.id, code='IND_VENDAS').first()
        if not ind_vendas:
            ind_vendas = IncentiveIndicator(
                company_id=company.id,
                code='IND_VENDAS',
                name='Volume de Vendas Mensal',
                indicator_type='individual',
                source_module='manual'
            )
            db.session.add(ind_vendas)

        # Risk / Quality (Occurrences)
        ind_erros = IncentiveIndicator.query.filter_by(company_id=company.id, code='RED_ERROS').first()
        if not ind_erros:
            ind_erros = IncentiveIndicator(
                company_id=company.id,
                code='RED_ERROS',
                name='Ocorrência de Erros Críticos',
                indicator_type='risk',
                source_module='occurrence'
            )
            db.session.add(ind_erros)

        db.session.commit()
        print("Indicadores configurados.")

        # 3. Setup RuleSet and Rules
        ruleset = IncentiveRuleSet.query.filter_by(company_id=company.id, name='Plano 2026 Teste').first()
        if not ruleset:
            ruleset = IncentiveRuleSet(
                company_id=company.id,
                name='Plano 2026 Teste',
                periodicity='monthly',
                is_active=True,
                valid_from=date(2026, 1, 1)
            )
            db.session.add(ruleset)
            db.session.flush()

            # Rule 1: Individual Target
            r1 = IncentiveRule(
                rule_set_id=ruleset.id,
                indicator_id=ind_vendas.id,
                weight=Decimal('1.0'),
                target_value=Decimal('100.0'), # meta de 100
                impact_type='individual',
                order_index=1
            )
            db.session.add(r1)

            # Rule 2: Risk Reducer
            r2 = IncentiveRule(
                rule_set_id=ruleset.id,
                indicator_id=ind_erros.id,
                weight=Decimal('0.2'), # 20% de peso no redutor
                target_value=Decimal('1.0'), # meta de apenas 1 erro
                impact_type='reducer',
                order_index=2
            )
            db.session.add(r2)
            print("RuleSet e Regras configuradas.")

        # 4. Setup Matrix (Governance)
        role = Role.query.filter_by(company_id=company.id).first()
        if role:
            entry = IncentiveGovernabilityMatrix.query.filter_by(
                company_id=company.id, 
                role_id=role.id, 
                indicator_id=ind_vendas.id
            ).first()
            if not entry:
                entry = IncentiveGovernabilityMatrix(
                    company_id=company.id,
                    role_id=role.id,
                    indicator_id=ind_vendas.id,
                    governability_level='direct'
                )
                db.session.add(entry)
            print(f"Matriz de Governabilidade configurada para o cargo: {role.title}")

        # 4. Create some test occurrences to harvest
        emp = Employee.query.filter_by(company_id=company.id).first()
        if emp:
            occ = Occurrence(
                company_id=company.id,
                employee_id=emp.id,
                title='Erro de Processo Teste',
                type='negative',
                score=-10,
                created_at=datetime.utcnow()
            )
            db.session.add(occ)
            print(f"Ocorrência de teste criada para: {emp.name}")

        db.session.commit()
        print("Setup concluído com sucesso.")

if __name__ == "__main__":
    setup()
