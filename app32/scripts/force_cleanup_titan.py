
import sys
import os
from sqlalchemy import text

sys.path.append(os.getcwd())
from app import create_app, db

app = create_app()

def force_cleanup(company_id=36):
    with app.app_context():
        print(f"--- FORCE CLEANUP COMPANY {company_id} ---")
        
        # Get tables in dependency order (parents first)
        metadata = db.metadata
        sorted_tables = metadata.sorted_tables # This gives parents first usually?
        # actually sorted_tables Dependency sort: "tables are sorted in an order suitable for creation" (parents first).
        # We need Drop order (children first).
        
        tables_reversed = list(reversed(sorted_tables))
        
        for table in tables_reversed:
            t_name = table.name
            # Check if table has company_id column
            if 'company_id' in table.columns:
                print(f"Cleaning {t_name}...")
                try:
                    db.session.execute(text(f"DELETE FROM {t_name} WHERE company_id = :cid"), {'cid': company_id})
                except Exception as e:
                    print(f"Error cleaning {t_name}: {e}")
            else:
                # Special cases if indirectly linked?
                # e.g. project_tasks linked to project?
                # If deleted via project cascade, fine. 
                # But sorted_tables handles FKs. 
                # If project_tasks has FK to projects, it appears AFTER projects in sorted list? No, BEFORE in sorted? 
                # Create: Project, then Task.
                # Drop: Task, then Project.
                # So Reversed List = Task, Project.
                # Project has company_id. Task usually doesn't? Let's check.
                if t_name == 'project_tasks':
                    print(f"Cleaning {t_name} (indirect)...")
                    try:
                        db.session.execute(text(f"DELETE FROM {t_name} WHERE project_id IN (SELECT id FROM projects WHERE company_id = :cid)"), {'cid': company_id})
                    except: pass
                
                # Add logic for other indirect tables if necessary
                pass

        try:
            db.session.commit()
            print("--- CLEANUP SUCCESSFUL ---")
        except Exception as e:
            print(f"--- CLEANUP FAILED COMMIT: {e}")
            db.session.rollback()

if __name__ == "__main__":
    force_cleanup()
