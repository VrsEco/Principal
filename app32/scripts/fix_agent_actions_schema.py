
import sys
import os
sys.path.append(os.getcwd())

from app import app
from models import db
from sqlalchemy import text

def fix_schema():
    with app.app_context():
        with db.engine.connect() as conn:
            # Check existing columns
            res = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name = 'agent_actions'"))
            cols = [r[0] for r in res]
            
            if 'backup_content' not in cols:
                print("Adding 'backup_content' to agent_actions...")
                conn.execute(text("ALTER TABLE agent_actions ADD COLUMN backup_content TEXT"))
                conn.commit()
            else:
                print("'backup_content' already exists.")

            if 'original_file' not in cols:
                 print("Adding 'original_file' to agent_actions...")
                 conn.execute(text("ALTER TABLE agent_actions ADD COLUMN original_file VARCHAR(255)"))
                 conn.commit()
            else:
                 print("'original_file' already exists.")
                 
            # Also check user_feedback just in case
            if 'user_feedback' not in cols:
                 print("Adding 'user_feedback' to agent_actions...")
                 conn.execute(text("ALTER TABLE agent_actions ADD COLUMN user_feedback TEXT"))
                 conn.commit()


if __name__ == "__main__":
    fix_schema()
