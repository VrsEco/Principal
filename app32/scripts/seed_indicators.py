from app import app, db
from models import Indicator, IndicatorGroup, Company

def seed_indicators():
    with app.app_context():
        # Get first company
        company = Company.query.first()
        if not company:
            print("No company found. Seed companies first.")
            return
            
        # Create a group
        group = IndicatorGroup.query.filter_by(name="Comercial").first()
        if not group:
            group = IndicatorGroup(
                company_id=company.id,
                code="COM",
                name="Comercial",
                description="Indicadores de vendas e marketing"
            )
            db.session.add(group)
            db.session.commit()
            print("Group 'Comercial' created.")
            
        # Create indicators
        indicators_data = [
            {
                "code": "IND-001",
                "name": "Faturamento Mensal",
                "unit": "R$",
                "polarity": "positive",
                "group_id": group.id
            },
            {
                "code": "IND-002",
                "name": "CAC (Custo de Aquisição)",
                "unit": "R$",
                "polarity": "negative",
                "group_id": group.id
            },
            {
                "code": "IND-003",
                "name": "Taxa de Conversão",
                "unit": "%",
                "polarity": "positive",
                "group_id": group.id
            }
        ]
        
        for data in indicators_data:
            ind = Indicator.query.filter_by(code=data["code"]).first()
            if not ind:
                ind = Indicator(
                    company_id=company.id,
                    **data
                )
                db.session.add(ind)
        
        db.session.commit()
        print("Indicators seeded successfully!")

if __name__ == "__main__":
    seed_indicators()
