from app import create_app
from models import db
from sqlalchemy import text

app = create_app()
with app.app_context():
    result = db.session.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='indicators'"))
    columns = [row[0] for row in result]
    required = ['responsible_id', 'polarity', 'formula', 'notes']
    for col in required:
        if col in columns:
            print(f"Col {col}: OK")
        else:
            print(f"Col {col}: MISSING")
