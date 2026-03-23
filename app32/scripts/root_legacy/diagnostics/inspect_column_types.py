from app import create_app
from models import db
from sqlalchemy import text, inspect

app = create_app()

with app.app_context():
    inspector = inspect(db.engine)
    columns = inspector.get_columns('plans')
    print("Detalhes das colunas em 'plans':")
    for col in columns:
        print(f"Nome: {col['name']}, Tipo: {col['type']}")
