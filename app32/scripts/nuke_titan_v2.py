
import sys
import os
from sqlalchemy import text

sys.path.append(os.getcwd())
from app import create_app, db

app = create_app()

def nuke_titan(cid=36):
    with app.app_context():
        print(f"--- NUKING TITAN CORP (ID {cid}) ---")
        
        # 1. Indirect deletions (Tables without company_id)
        # Order matters: Children first
        
        indirect_stmts = [
            # Projects & Activities
            ("project_activity_collaborators", "activity_id IN (SELECT id FROM project_activities WHERE project_id IN (SELECT id FROM projects WHERE company_id = :cid))"),
            ("project_activity_comments", "activity_id IN (SELECT id FROM project_activities WHERE project_id IN (SELECT id FROM projects WHERE company_id = :cid))"),
            ("project_activities", "project_id IN (SELECT id FROM projects WHERE company_id = :cid)"),
            ("project_tasks", "project_id IN (SELECT id FROM projects WHERE company_id = :cid)"),
            
            # Key Results
            ("key_results", "okr_global_id IN (SELECT id FROM okrs_global WHERE company_id = :cid)"),
            ("key_result_areas", "okr_area_id IN (SELECT id FROM okrs_area WHERE company_id = :cid)"),
            
            # Plan Children
            ("plan_drivers", "plan_id IN (SELECT id FROM plans WHERE company_id = :cid)"),
            ("plan_participants", "plan_id IN (SELECT id FROM plans WHERE company_id = :cid)"),
            ("plan_section_status", "plan_id IN (SELECT id FROM plans WHERE company_id = :cid)"),
            ("plan_implantation_data", "plan_id IN (SELECT id FROM plans WHERE company_id = :cid)"),
            
            # Process Children
            ("process_steps", "routine_id IN (SELECT id FROM routines WHERE company_id = :cid)"),
            
            # Meeting Children
            ("meeting_agenda_items", "meeting_id IN (SELECT id FROM meetings WHERE company_id = :cid)"),
            ("meeting_participants", "meeting_id IN (SELECT id FROM meetings WHERE company_id = :cid)"),
            
            # Indicators
            ("indicator_data", "indicator_id IN (SELECT id FROM indicators WHERE company_id = :cid)"),
            ("indicator_goals", "indicator_id IN (SELECT id FROM indicators WHERE company_id = :cid)"),
            
            # Teams
            ("team_members", "team_id IN (SELECT id FROM teams WHERE company_id = :cid)"),
        ]

        for table, condition in indirect_stmts:
            try:
                # Check if table exists first? execute handles it
                db.session.execute(text(f"DELETE FROM {table} WHERE {condition}"), {'cid': cid})
                print(f"Deleted indirect: {table}")
            except Exception as e:
                # Table might not exist or other error
                txt = str(e).lower()
                if "does not exist" in txt or "undefined table" in txt:
                    pass
                else:
                    print(f"Error deleting {table}: {e}")

        db.session.commit()
        
        # 2. Direct deletions (Tables with company_id)
        # Use metadata to find dependency order
        metadata = db.metadata
        sorted_tables = list(reversed(metadata.sorted_tables))
        
        for table in sorted_tables:
            t_name = table.name
            if 'company_id' in table.columns:
                try:
                    res = db.session.execute(text(f"DELETE FROM {t_name} WHERE company_id = :cid"), {'cid': cid})
                    if res.rowcount > 0:
                        print(f"Deleted direct: {t_name} ({res.rowcount} rows)")
                except Exception as e:
                    print(f"Error cleaning {t_name}: {e}")

        db.session.commit()
        print("--- NUKE COMPLETE ---")

if __name__ == "__main__":
    nuke_titan()
