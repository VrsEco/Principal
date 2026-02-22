import sys
import os
from app import app
from models import db
from models.company import Company

def check_db():
    print("--- Database Check ---")
    with app.app_context():
        try:
            count = Company.query.count()
            print(f"✅ Connection successful. Total companies: {count}")
            companies = Company.query.all()
            for c in companies:
                print(f"   - [{c.id}] {c.name} ({c.client_code})")
        except Exception as e:
            print(f"❌ Database error: {e}")

def check_routes():
    print("\n--- Route Check ---")
    api_routes = [str(p) for p in app.url_map.iter_rules() if '/api/' in str(p)]
    if api_routes:
        print("✅ API routes found:")
        for r in api_routes:
            print(f"   - {r}")
    else:
        print("❌ NO API routes found!")

if __name__ == "__main__":
    check_db()
    check_routes()
