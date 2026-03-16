
from app import create_app
from models import db
from sqlalchemy import text

app = create_app()
with app.app_context():
    print("Colunas em incentive_indicators:")
    res = db.session.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name = 'incentive_indicators'"))
    for row in res:
        print(row[0])
    
    print("\nColunas em incentive_rules:")
    res = db.session.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name = 'incentive_rules'"))
    for row in res:
        print(row[0])

    print("\nColunas em incentive_rule_sets:")
    res = db.session.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name = 'incentive_rule_sets'"))
    for row in res:
        print(row[0])
