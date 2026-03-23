from app import create_app
from models import db
from sqlalchemy import inspect

app = create_app()
with app.app_context():
    inspector = inspect(db.engine)
    columns = inspector.get_columns('indicators')
    for column in columns:
        print(f"Column: {column['name']}, Type: {column['type']}")
