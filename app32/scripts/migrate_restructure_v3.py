
import psycopg2
from urllib.parse import urlparse
import os

def load_env():
    if os.path.exists('.env'):
        with open('.env') as f:
            for line in f:
                if '=' in line:
                    key, value = line.strip().split('=', 1)
                    os.environ[key] = value

def run_migration():
    load_env()
    db_url = os.environ.get('DATABASE_URL')
    if not db_url:
        print("DATABASE_URL not found")
        return

    result = urlparse(db_url)
    conn = psycopg2.connect(
        database=result.path[1:],
        user=result.username,
        password=result.password,
        host=result.hostname,
        port=result.port
    )
    conn.autocommit = True
    
    try:
        cur = conn.cursor()
        
        sql = """
        DO $$
        BEGIN
            -- 1. Create independent tree table
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

            -- 2. Migrate tree data from incentive (if exists)
            IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'incentive_indicator_tree') THEN
                INSERT INTO indicator_tree (id, company_id, parent_id, code, name, description, created_at, updated_at)
                SELECT id, company_id, parent_id, code, name, description, created_at, updated_at
                FROM incentive_indicator_tree
                ON CONFLICT (id) DO NOTHING;
                
                PERFORM setval('indicator_tree_id_seq', (SELECT MAX(id) FROM indicator_tree));
            END IF;

            -- 3. Prepare main indicators table
            ALTER TABLE indicators ADD COLUMN IF NOT EXISTS tree_id INTEGER REFERENCES indicator_tree(id);
            ALTER TABLE indicators ADD COLUMN IF NOT EXISTS full_code VARCHAR(100);
            ALTER TABLE indicators ADD COLUMN IF NOT EXISTS indicator_type VARCHAR(50) DEFAULT 'individual';
            ALTER TABLE indicators ADD COLUMN IF NOT EXISTS source_module VARCHAR(50) DEFAULT 'manual';
            ALTER TABLE indicators ADD COLUMN IF NOT EXISTS source_id INTEGER;
            ALTER TABLE indicators ADD COLUMN IF NOT EXISTS collection_mode VARCHAR(30) DEFAULT 'manual';
            ALTER TABLE indicators ADD COLUMN IF NOT EXISTS aggregation_function VARCHAR(30) DEFAULT 'sum';
            ALTER TABLE indicators ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE;
            ALTER TABLE indicators ADD COLUMN IF NOT EXISTS description TEXT;

            IF NOT EXISTS (SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace WHERE c.relname = 'idx_indicators_full_code') THEN
                CREATE INDEX idx_indicators_full_code ON indicators(full_code);
            END IF;

            -- 4. Unify indicators: Move from incentive_indicators to indicators
            IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'incentive_indicators') THEN
                INSERT INTO indicators (company_id, tree_id, full_code, code, name, description, indicator_type, source_module, source_id, collection_mode, aggregation_function, unit, polarity, is_active)
                SELECT company_id, tree_id, full_code, code, name, description, indicator_type, source_module, source_id, collection_mode, aggregation_function, unit, polarity, is_active
                FROM incentive_indicators
                ON CONFLICT (code) DO UPDATE SET
                    tree_id = EXCLUDED.tree_id,
                    full_code = EXCLUDED.full_code,
                    indicator_type = EXCLUDED.indicator_type,
                    source_module = EXCLUDED.source_module,
                    aggregation_function = EXCLUDED.aggregation_function;
            END IF;

            -- 5. Create performance tables
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

            -- 6. Re-link Incentive Rules to correct Indicators
            IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'incentive_indicators') THEN
                UPDATE incentive_rules ir
                SET indicator_id = ind.id
                FROM indicators ind
                JOIN incentive_indicators iind ON ind.code = iind.code
                WHERE ir.indicator_id = iind.id;
                
                -- Also update other tables that might lead to incentive_indicators
                IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'incentive_facts') THEN
                    UPDATE incentive_facts fact
                    SET indicator_id = ind.id
                    FROM indicators ind
                    JOIN incentive_indicators iind ON ind.code = iind.code
                    WHERE fact.indicator_id = iind.id;
                END IF;
            END IF;

        END $$;
        """
        
        cur.execute(sql)
        print("Migration restructure_v3 completed successfully.")
        
        cur.close()
    except Exception as e:
        print(f"Error during migration: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    run_migration()
