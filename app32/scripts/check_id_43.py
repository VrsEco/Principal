from app import create_app, db
from sqlalchemy import text

app = create_app()
with app.app_context():
    res = db.session.execute(text("SELECT id, name, process_id FROM routines WHERE id = 43")).fetchone()
    print(f"Routine 43 in 'routines': {res}")
    res2 = db.session.execute(text("SELECT id, name, process_id FROM process_routines WHERE id = 43")).fetchone()
    print(f"Routine 43 in 'process_routines': {res2}")
