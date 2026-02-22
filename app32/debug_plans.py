from app import create_app
from models import db, Plan

app = create_app()
with app.app_context():
    plans = Plan.query.order_by(Plan.id.desc()).limit(5).all()
    for p in plans:
        print(f"ID: {p.id}, Name: {p.name}, Mode: {p.plan_mode}, Date: {p.start_date}")
