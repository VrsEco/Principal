import sys
import os

# Raiz do projeto
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))

from app import create_app
from models import db
from sqlalchemy import text

app = create_app()

def create_performance_views():
    with app.app_context():
        print("[DBA] Criando MATERIALIZED VIEWS para ganho de performance...")
        
        # Consolida secoes de plano
        sql_view = """
        DO $$ 
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_matviews WHERE matviewname = 'mv_plan_progress') THEN
                CREATE MATERIALIZED VIEW mv_plan_progress AS
                SELECT 
                    plan_id,
                    company_id,
                    COUNT(*) FILTER (WHERE status = 'completed') as completed_sections,
                    COUNT(*) as total_sections,
                    CASE 
                        WHEN COUNT(*) > 0 THEN ROUND((COUNT(*) FILTER (WHERE status = 'completed')::float / COUNT(*)::float) * 100) 
                        ELSE 0 
                    END as progress_pct
                FROM plan_sections
                GROUP BY plan_id, company_id;
                
                CREATE UNIQUE INDEX idx_mv_plan_progress_id ON mv_plan_progress (plan_id);
            END IF;
        END $$;
        """
        
        try:
            db.session.execute(text(sql_view))
            db.session.commit()
            print("SUCCESS: View 'mv_plan_progress' verificada/criada.")
        except Exception as e:
            db.session.rollback()
            print(f"FAILED: {str(e)}")

if __name__ == "__main__":
    create_performance_views()
