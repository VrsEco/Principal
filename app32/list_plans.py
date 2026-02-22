from app import app
from models import db, Plan

def list_plans():
    with app.app_context():
        plans = Plan.query.all()
        for p in plans:
            print(f"ID: {p.id} | Title: {p.title} | Mode: {p.mode}")

if __name__ == "__main__":
    list_plans()
