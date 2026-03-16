
import os, sys
sys.path.append(os.getcwd())
from app import create_app
from models import db
from sqlalchemy import text

app = create_app()
with app.app_context():
    sql_commands = [
        """
        CREATE TABLE IF NOT EXISTS incentive_indicator_tree (
            id SERIAL PRIMARY KEY,
            company_id INTEGER NOT NULL REFERENCES companies(id),
            parent_id INTEGER REFERENCES incentive_indicator_tree(id),
            code VARCHAR(50) NOT NULL,
            name VARCHAR(255) NOT NULL,
            description TEXT,
            created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT (now() at time zone 'utc'),
            updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT (now() at time zone 'utc')
        );
        """,
        """
        ALTER TABLE incentive_indicators ADD COLUMN IF NOT EXISTS tree_id INTEGER REFERENCES incentive_indicator_tree(id);
        """,
        """
        ALTER TABLE incentive_indicators ADD COLUMN IF NOT EXISTS full_code VARCHAR(100);
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_incentive_indicators_full_code ON incentive_indicators(full_code);
        """,
        """
        CREATE TABLE IF NOT EXISTS incentive_targets (
            id SERIAL PRIMARY KEY,
            company_id INTEGER NOT NULL REFERENCES companies(id),
            indicator_id INTEGER NOT NULL REFERENCES incentive_indicators(id),
            period_start DATE NOT NULL,
            period_end DATE NOT NULL,
            target_value NUMERIC(15,4) NOT NULL,
            notes TEXT,
            created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT (now() at time zone 'utc'),
            updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT (now() at time zone 'utc')
        );
        """
    ]

    for sql in sql_commands:
        try:
            db.session.execute(text(sql))
            db.session.commit()
            print(f"Executed success: {sql[:50]}...")
        except Exception as e:
            db.session.rollback()
            print(f"Error executing SQL: {str(e)}")

    print("DB Migration completed.")
