from app import create_app
from models import db, Company, IncentiveIndicator, IncentiveRuleSet, IncentiveRule, Role, IncentiveGovernabilityMatrix
from datetime import datetime
from decimal import Decimal

def seed_incentives():
    app = create_app()
    with app.app_context():
        # Seed for Gandu (7) and Versus (9)
        target_ids = [7, 9]
        for cid in target_ids:
            company = Company.query.get(cid)
            if not company:
                continue
            
            print(f"Seeding incentives for company: {company.name} (ID: {company.id})")

            # 1. Indicators
            indicators_data = [
                {"code": "FAT", "name": "Faturamento Bruto", "type": "individual", "module": "financeiro"},
                {"code": "NPS", "name": "NPS Geral", "type": "collective", "module": "qualidade"},
                {"code": "CHURN", "name": "Churn Rate", "type": "reducer", "module": "operacional"},
                {"code": "EFI", "name": "Eficiência Operacional", "type": "individual", "module": "process"}
            ]

            inds = []
            for ind_data in indicators_data:
                ind = IncentiveIndicator.query.filter_by(company_id=company.id, code=ind_data["code"]).first()
                if not ind:
                    ind = IncentiveIndicator(
                        company_id=company.id,
                        code=ind_data["code"],
                        name=ind_data["name"],
                        indicator_type=ind_data["type"],
                        source_module=ind_data["module"],
                        is_active=True
                    )
                    db.session.add(ind)
                    db.session.flush()
                inds.append(ind)
            
            db.session.commit()

            # 2. Rule Set
            rs = IncentiveRuleSet.query.filter_by(company_id=company.id).first()
            if not rs:
                rs = IncentiveRuleSet(
                    company_id=company.id,
                    name="Plano de Performance 2026",
                    description="Plano padrão de meritocracia estratégica.",
                    periodicity="monthly"
                )
                db.session.add(rs)
                db.session.commit()
            
            print(f"Rule Set: {rs.name} (ID: {rs.id})")

            # 3. Rules
            if not IncentiveRule.query.filter_by(rule_set_id=rs.id).first():
                for idx, ind in enumerate(inds):
                    rule = IncentiveRule(
                        rule_set_id=rs.id,
                        indicator_id=ind.id,
                        weight=Decimal('0.25'), # 25% each
                        target_value=Decimal('100.00'),
                        min_threshold=Decimal('0.80'),
                        max_cap=Decimal('1.20'),
                        impact_type='multiplier' if ind.indicator_type == 'collective' else ('reducer' if ind.indicator_type == 'reducer' else 'individual'),
                        order_index=idx
                    )
                    db.session.add(rule)
                db.session.commit()
                print(f"Added {len(inds)} rules to Rule Set.")

            # 4. Roles and Matrix (for spider web)
            roles = Role.query.filter_by(company_id=company.id).all()
            if not roles:
                role_names = ["Diretor Comercial", "Gerente de Projetos", "Analista de Qualidade"]
                for name in role_names:
                    r = Role(company_id=company.id, title=name)
                    db.session.add(r)
                db.session.commit()
                roles = Role.query.filter_by(company_id=company.id).all()

            for role in roles:
                for ind in inds[:2]:
                    exists = IncentiveGovernabilityMatrix.query.filter_by(
                        company_id=company.id, role_id=role.id, indicator_id=ind.id
                    ).first()
                    if not exists:
                        matrix = IncentiveGovernabilityMatrix(
                            company_id=company.id,
                            role_id=role.id,
                            indicator_id=ind.id,
                            governability_level="direct"
                        )
                        db.session.add(matrix)
            
            db.session.commit()
            print(f"Seed for CID {company.id} completed successfully.")

if __name__ == "__main__":
    seed_incentives()
