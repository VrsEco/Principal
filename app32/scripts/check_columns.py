from models import db, Routine, ProcessRoutine
from app import app

def check_columns(model):
    print(f"\nColumns for {model.__tablename__}:")
    for column in model.__table__.columns:
        print(f" - {column.name}: {column.type}")

with app.app_context():
    check_columns(Routine)
    check_columns(ProcessRoutine)
