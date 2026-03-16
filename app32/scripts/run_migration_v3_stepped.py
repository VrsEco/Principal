
import sys
import os
from pathlib import Path
import base64

# Add project root to sys.path
sys.path.append(str(Path(__file__).resolve().parents[1]))
from scripts.deploy.configr_remote_helper import connect_ssh, APP_DIR

def run_remote_migration():
    ssh = connect_ssh()
    try:
        # 1. Ensure columns exist in indicators (Core)
        cols_to_add = [
            ("tree_id", "INTEGER"),
            ("full_code", "VARCHAR(100)"),
            ("indicator_type", "VARCHAR(50) DEFAULT 'individual'"),
            ("source_module", "VARCHAR(50) DEFAULT 'manual'"),
            ("source_id", "INTEGER"),
            ("collection_mode", "VARCHAR(30) DEFAULT 'manual'"),
            ("aggregation_function", "VARCHAR(30) DEFAULT 'sum'"),
            ("is_active", "BOOLEAN DEFAULT TRUE"),
            ("description", "TEXT"),
            ("polarity", "VARCHAR(20) DEFAULT 'positive'"),
            ("unit", "VARCHAR(50)"),
            ("formula", "TEXT")
        ]
        
        print("Ensuring core columns exist in indicators...")
        for col, dtype in cols_to_add:
            cmd = f"cd {APP_DIR} && export $(grep -v '^#' .env | xargs) && psql $DATABASE_URL -c \"ALTER TABLE indicators ADD COLUMN IF NOT EXISTS {col} {dtype};\""
            ssh.exec_command(cmd)

        # 2. Main Script Block (Tree, Goals, Data, and Data migration)
        sql_block = """
        -- 1. Tree
        CREATE TABLE IF NOT EXISTS indicator_tree (
            id SERIAL PRIMARY KEY,
            company_id INTEGER NOT NULL,
            parent_id INTEGER REFERENCES indicator_tree(id),
            code VARCHAR(50) NOT NULL,
            name VARCHAR(255) NOT NULL,
            description TEXT,
            created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );

        -- 2. Constraints
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM information_schema.table_constraints WHERE constraint_name = 'indicators_tree_id_fkey') THEN
                ALTER TABLE indicators ADD CONSTRAINT indicators_tree_id_fkey FOREIGN KEY (tree_id) REFERENCES indicator_tree(id);
            END IF;
            
            IF NOT EXISTS (SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace WHERE c.relname = 'idx_indicators_full_code') THEN
                CREATE INDEX idx_indicators_full_code ON indicators(full_code);
            END IF;
        END $$;

        -- 3. Data Migration (Disentangling from Incentive)
        DO $$
        BEGIN
            IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'incentive_indicators') THEN
                
                -- Migrate indicators that only exist in the incentive module bundle
                INSERT INTO indicators (company_id, tree_id, full_code, code, name, description, indicator_type, source_module, source_id, collection_mode, aggregation_function, unit, is_active)
                SELECT company_id, tree_id, full_code, code, name, description, indicator_type, source_module, source_id, collection_mode, aggregation_function, unit, is_active
                FROM incentive_indicators
                ON CONFLICT (code) DO UPDATE SET
                    tree_id = EXCLUDED.tree_id,
                    full_code = EXCLUDED.full_code,
                    indicator_type = EXCLUDED.indicator_type,
                    source_module = EXCLUDED.source_module,
                    aggregation_function = EXCLUDED.aggregation_function,
                    unit = EXCLUDED.unit;
                    
                -- Update rules to point to the unified core indicator table
                UPDATE incentive_rules ir
                SET indicator_id = ind.id
                FROM indicators ind
                JOIN incentive_indicators iind ON ind.code = iind.code
                WHERE ir.indicator_id = iind.id;
                
                -- Migrate existing incentive targets to the new general indicator goals
                IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'incentive_targets') THEN
                    INSERT INTO indicator_goals (company_id, indicator_id, goal_value, goal_date, period_start, period_end, notes, created_at)
                    SELECT t.company_id, ind.id, t.target_value, t.period_end, t.period_start, t.period_end, t.notes, t.created_at
                    FROM incentive_targets t
                    JOIN incentive_indicators iind ON t.indicator_id = iind.id
                    JOIN indicators ind ON ind.code = iind.code
                    ON CONFLICT DO NOTHING;
                END IF;
            END IF;
        END $$;

        -- 4. Unified Performance Tables (Permanent)
        CREATE TABLE IF NOT EXISTS indicator_goals (
            id SERIAL PRIMARY KEY,
            company_id INTEGER NOT NULL,
            indicator_id INTEGER NOT NULL REFERENCES indicators(id),
            goal_value NUMERIC(15, 4) NOT NULL,
            goal_date DATE NOT NULL,
            period_start DATE,
            period_end DATE,
            responsible_id INTEGER,
            status VARCHAR(50) DEFAULT 'active',
            notes TEXT,
            created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS indicator_data (
            id SERIAL PRIMARY KEY,
            company_id INTEGER NOT NULL,
            indicator_id INTEGER NOT NULL REFERENCES indicators(id),
            goal_id INTEGER REFERENCES indicator_goals(id),
            measured_value NUMERIC(15, 4) NOT NULL,
            measured_date DATE NOT NULL,
            period_start DATE,
            period_end DATE,
            employee_id INTEGER,
            collaborator_id INTEGER,
            source_ref VARCHAR(255),
            evidence_payload JSONB,
            notes TEXT,
            created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
        """
        
        b64_sql = base64.b64encode(sql_block.encode()).decode()
        remote_file = f"{APP_DIR}/migrate_restructure_v3_final.sql"
        ssh.exec_command(f"echo {b64_sql} | base64 -d > {remote_file}")
        
        final_cmd = f"cd {APP_DIR} && export $(grep -v '^#' .env | xargs) && psql $DATABASE_URL -f {remote_file}"
        print(f"Running core migration block...")
        stdin, stdout, stderr = ssh.exec_command(final_cmd)
        
        out = stdout.read().decode()
        err = stderr.read().decode()
        
        print("STDOUT:")
        print(out)
        print("STDERR:")
        print(err)
        
        ssh.exec_command(f"rm {remote_file}")
        print("Disentanglement process finished.")
    finally:
        ssh.close()

if __name__ == "__main__":
    run_remote_migration()
