from app import create_app
from models import db
from sqlalchemy import inspect

app = create_app()
with app.app_context():
    inspector = inspect(db.engine)
    cols = [c['name'] for c in inspector.get_columns('incentive_rules')]
    print(f"COLUNAS_ATUAIS: {','.join(cols)}")
    
    # Verifica se o ID 20 existe
    from models import IncentiveRuleSet
    rs = IncentiveRuleSet.query.get(20)
    print(f"RuleSet 20 existe? {rs is not None}")
