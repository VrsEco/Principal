
import sys
import os
from sqlalchemy import text

sys.path.append(os.getcwd())
try:
    from app import create_app, db
except ImportError:
    pass

def verify():
    app = create_app()
    with app.app_context():
        # Check plan_implantation_data
        try:
            with db.engine.connect() as conn:
                res = conn.execute(text("SELECT count(*) FROM plan_implantation_data"))
                print(f"plan_implantation_data count: {res.scalar()}")
        except Exception as e:
            print(f"Error querying plan_implantation_data: {e}")
            
        # Check plans
        try:
            with db.engine.connect() as conn:
                res = conn.execute(text("SELECT count(*) FROM plans"))
                print(f"plans count: {res.scalar()}")
        except Exception as e:
            print(f"Error querying plans: {e}")

if __name__ == "__main__":
    verify()
