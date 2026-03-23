from app import create_app
from models import db
from sqlalchemy import text

app = create_app()
with app.app_context():
    result = db.session.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='indicators'"))
    columns = [row[0] for row in result]
    print(f"COLUMNS IN indicators: {columns}")
    
    if 'responsible_id' in columns:
        print("SUCCESS: responsible_id exists.")
    else:
        print("FAILURE: responsible_id MISSING.")
