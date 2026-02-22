from app import create_app, db
from sqlalchemy import text

app = create_app()
with app.app_context():
    print("Checking process_id = 171...")
    res_pr = db.session.execute(text("SELECT id, name, code, order_index FROM process_routines WHERE process_id = 171")).fetchall()
    print(f"process_routines: {res_pr}")
    
    res_r = db.session.execute(text("SELECT id, name, code, order_index FROM routines WHERE process_id = 171")).fetchall()
    print(f"routines: {res_r}")
