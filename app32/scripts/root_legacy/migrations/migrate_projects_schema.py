import os
from app import app
from models import db, Project, Plan
from sqlalchemy import text

def migrate():
    with app.app_context():
        # 1. Add company_id column to projects
        try:
            db.session.execute(text("ALTER TABLE projects ADD COLUMN company_id INTEGER REFERENCES companies(id)"))
            db.session.commit()
            print("Successfully added company_id column to projects table.")
        except Exception as e:
            db.session.rollback()
            print(f"Adding company_id column failed (might already exist): {e}")

        # 2. Add priority column to projects (checking if it exists)
        try:
            db.session.execute(text("ALTER TABLE projects ADD COLUMN priority VARCHAR(20) DEFAULT 'medium'"))
            db.session.commit()
            print("Successfully added priority column to projects table.")
        except Exception as e:
            db.session.rollback()
            print(f"Adding priority column failed (might already exist): {e}")

        # 3. Populate company_id from plans
        try:
            db.session.execute(text("""
                UPDATE projects 
                SET company_id = plans.company_id 
                FROM plans 
                WHERE projects.plan_id = plans.id 
                AND projects.company_id IS NULL
            """))
            db.session.commit()
            print("Successfully populated company_id for existing projects.")
        except Exception as e:
            db.session.rollback()
            print(f"Populating company_id failed: {e}")

        # 4. For projects without plans (if any already existed somehow), 
        # we might need to find another way or just set it to a default 
        # but since it was required before, it shouldn't be a big issue yet.
        # However, if there are orphans, we might have a problem.

if __name__ == "__main__":
    migrate()
