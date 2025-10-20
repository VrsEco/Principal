"""
PostgreSQL database implementation
"""

from datetime import datetime, date, time
import re
from typing import List, Dict, Any, Optional, Tuple
from .base import DatabaseInterface
from .postgres_helper import connect as pg_connect

class PostgreSQLDatabase(DatabaseInterface):
    """PostgreSQL database implementation usando pg8000"""
    
    def __init__(self, host: str = 'localhost', port: int = 5432, 
                 database: str = 'pevapp22', user: str = 'postgres', 
                 password: str = 'password'):
        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self.password = password
        # Não inicializar database - já está migrado
        # self.init_database()
        # self.seed_data()
    
    def _get_connection(self):
        """Get database connection usando postgres_helper"""
        return pg_connect()

    def _convert_params(self, sql, params):
        """Converte SQL e parâmetros de %s para :param_N"""
        if not params:
            return sql, {}
        
        # Se params for tupla/lista, converter para dict numerado
        if isinstance(params, (tuple, list)):
            param_dict = {}
            new_sql = sql
            
            # Encontrar todos os %s e substituir por :param_N
            count = 0
            def replace_placeholder(match):
                nonlocal count
                param_name = f'param_{count}'
                count += 1
                return f':{param_name}'
            
            new_sql = re.sub(r'%s', replace_placeholder, new_sql)
            
            # Criar dicionário de parâmetros
            for i, value in enumerate(params):
                param_dict[f'param_{i}'] = value
            
            return new_sql, param_dict
        
        return sql, params

    def _format_date_value(self, value: Any) -> Optional[str]:
        """Convert date/datetime values to ISO strings for JSON responses"""
        if isinstance(value, datetime):
            return value.date().isoformat()
        if isinstance(value, date):
            return value.isoformat()
        return value

    def _format_time_value(self, value: Any) -> Optional[str]:
        """Normalize time objects to HH:MM strings"""
        if isinstance(value, time):
            return value.strftime('%H:%M')
        return value

    def _format_datetime_value(self, value: Any) -> Optional[str]:
        """Convert datetime values to ISO strings preserving time information"""
        if isinstance(value, datetime):
            return value.isoformat(sep=' ', timespec='seconds')
        return value

    
    def init_database(self) -> bool:
        """Initialize database and create tables"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Create tables
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS companies (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    legal_name VARCHAR(255),
                    industry VARCHAR(255),
                    size VARCHAR(50),
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS plans (
                    id SERIAL PRIMARY KEY,
                    company_id INTEGER,
                    name VARCHAR(255) NOT NULL,
                    description TEXT,
                    start_date DATE,
                    end_date DATE,
                    year INTEGER,
                    status VARCHAR(50) DEFAULT 'active',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (company_id) REFERENCES companies (id)
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS participants (
                    id SERIAL PRIMARY KEY,
                    plan_id INTEGER,
                    name VARCHAR(255) NOT NULL,
                    role VARCHAR(255),
                    relation VARCHAR(255),
                    email VARCHAR(255),
                    cpf VARCHAR(20),
                    phone VARCHAR(50),
                    status VARCHAR(20) DEFAULT 'active',
                    email_confirmed BOOLEAN DEFAULT FALSE,
                    whatsapp_confirmed BOOLEAN DEFAULT FALSE,
                    message_sent BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP,
                    FOREIGN KEY (plan_id) REFERENCES plans (id)
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS company_data (
                    id SERIAL PRIMARY KEY,
                    plan_id INTEGER,
                    trade_name VARCHAR(255),
                    legal_name VARCHAR(255),
                    cnpj VARCHAR(20),
                    coverage_physical VARCHAR(50),
                    coverage_online VARCHAR(50),
                    mission TEXT,
                    vision TEXT,
                    company_values TEXT,
                    headcount_strategic INTEGER DEFAULT 0,
                    headcount_tactical INTEGER DEFAULT 0,
                    headcount_operational INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (plan_id) REFERENCES plans (id)
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS drivers (
                    id SERIAL PRIMARY KEY,
                    plan_id INTEGER,
                    title VARCHAR(255) NOT NULL,
                    description TEXT,
                    status VARCHAR(50) DEFAULT 'draft',
                    priority VARCHAR(50),
                    owner VARCHAR(255),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (plan_id) REFERENCES plans (id)
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS roles (
                    id SERIAL PRIMARY KEY,
                    company_id INTEGER NOT NULL REFERENCES companies (id) ON DELETE CASCADE,
                    title VARCHAR(255) NOT NULL,
                    parent_role_id INTEGER REFERENCES roles (id) ON DELETE SET NULL,
                    reports_to VARCHAR(255),
                    department VARCHAR(255),
                    color VARCHAR(50),
                    headcount_planned INTEGER DEFAULT 0,
                    weekly_hours INTEGER DEFAULT 40,
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS employees (
                    id SERIAL PRIMARY KEY,
                    company_id INTEGER NOT NULL REFERENCES companies (id) ON DELETE CASCADE,
                    name VARCHAR(255) NOT NULL,
                    email VARCHAR(255),
                    phone VARCHAR(100),
                    role_id INTEGER REFERENCES roles (id) ON DELETE SET NULL,
                    department VARCHAR(255),
                    hire_date DATE,
                    status VARCHAR(50) DEFAULT 'active',
                    weekly_hours REAL DEFAULT 40,
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_employees_company ON employees(company_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_employees_role ON employees(role_id)')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS okrs (
                    id SERIAL PRIMARY KEY,
                    plan_id INTEGER,
                    title VARCHAR(255) NOT NULL,
                    description TEXT,
                    type VARCHAR(50), -- 'global' or 'area'
                    area VARCHAR(100),
                    status VARCHAR(50) DEFAULT 'draft',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (plan_id) REFERENCES plans (id)
                )
            ''')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS okr_preliminary_records (
                    id SERIAL PRIMARY KEY,
                    plan_id INTEGER NOT NULL REFERENCES plans (id) ON DELETE CASCADE,
                    analysis TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS okr_global_records (
                    id SERIAL PRIMARY KEY,
                    plan_id INTEGER NOT NULL REFERENCES plans (id) ON DELETE CASCADE,
                    stage TEXT NOT NULL,
                    objective TEXT NOT NULL,
                    okr_type TEXT NOT NULL,
                    type_display TEXT,
                    owner_id INTEGER,
                    owner TEXT,
                    deadline TEXT,
                    observations TEXT,
                    directional TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS okr_global_key_results (
                    id SERIAL PRIMARY KEY,
                    okr_id INTEGER NOT NULL REFERENCES okr_global_records (id) ON DELETE CASCADE,
                    label TEXT NOT NULL,
                    target TEXT,
                    deadline TEXT,
                    owner_id INTEGER,
                    owner TEXT,
                    indicator_id INTEGER,
                    position INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            cursor.execute('ALTER TABLE okr_global_records ADD COLUMN IF NOT EXISTS owner_id INTEGER')
            cursor.execute('ALTER TABLE okr_global_key_results ADD COLUMN IF NOT EXISTS owner_id INTEGER')
            cursor.execute('ALTER TABLE okr_global_key_results ADD COLUMN IF NOT EXISTS indicator_id INTEGER')

            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS projects (
                    id SERIAL PRIMARY KEY,
                    plan_id INTEGER,
                    title VARCHAR(255) NOT NULL,
                    description TEXT,
                    status VARCHAR(50) DEFAULT 'planned',
                    priority VARCHAR(50),
                    owner VARCHAR(255),
                    start_date DATE,
                    end_date DATE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (plan_id) REFERENCES plans (id)
                )
            ''')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS company_projects (
                    id SERIAL PRIMARY KEY,
                    company_id INTEGER NOT NULL,
                    plan_id INTEGER,
                    title VARCHAR(255) NOT NULL,
                    description TEXT,
                    status VARCHAR(50) DEFAULT 'planned',
                    priority VARCHAR(50),
                    owner VARCHAR(255),
                    responsible_id INTEGER,
                    start_date DATE,
                    end_date DATE,
                    okr_area_ref VARCHAR(255),
                    okr_reference VARCHAR(255),
                    indicator_reference VARCHAR(255),
                    activities JSONB,
                    notes TEXT,
                    code VARCHAR(64),
                    code_sequence INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (company_id) REFERENCES companies (id),
                    FOREIGN KEY (plan_id) REFERENCES plans (id)
                )
            ''')

            cursor.execute("ALTER TABLE company_projects ADD COLUMN IF NOT EXISTS responsible_id INTEGER")
            cursor.execute("ALTER TABLE company_projects ADD COLUMN IF NOT EXISTS okr_reference VARCHAR(255)")
            cursor.execute("ALTER TABLE company_projects ADD COLUMN IF NOT EXISTS indicator_reference VARCHAR(255)")
            cursor.execute("ALTER TABLE company_projects ADD COLUMN IF NOT EXISTS code VARCHAR(64)")
            cursor.execute("ALTER TABLE company_projects ADD COLUMN IF NOT EXISTS code_sequence INTEGER")

            cursor.execute('''
                CREATE OR REPLACE FUNCTION trg_company_projects_updated_at()
                RETURNS TRIGGER AS $$
                BEGIN
                    NEW.updated_at := CURRENT_TIMESTAMP;
                    RETURN NEW;
                END;
                $$ LANGUAGE plpgsql;
            ''')

            cursor.execute('''
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM pg_trigger WHERE tgname = 'trg_company_projects_updated_at_row'
                    ) THEN
                        CREATE TRIGGER trg_company_projects_updated_at_row
                        BEFORE UPDATE ON company_projects
                        FOR EACH ROW
                        EXECUTE PROCEDURE trg_company_projects_updated_at();
                    END IF;
                END;
                $$;
            ''')

            cursor.execute('''
                INSERT INTO company_projects (
                    id, company_id, plan_id, title, description, status, priority,
                    owner, responsible_id, start_date, end_date, okr_area_ref,
                    okr_reference, indicator_reference, activities, notes,
                    code, code_sequence, created_at, updated_at
                )
                SELECT
                    p.id,
                    COALESCE(pl.company_id, 0),
                    p.plan_id,
                    p.title,
                    p.description,
                    p.status,
                    p.priority,
                    p.owner,
                    NULL,
                    p.start_date,
                    p.end_date,
                    NULL,
                    NULL,
                    NULL,
                    NULL,
                    NULL,
                    NULL,
                    NULL,
                    p.created_at,
                    p.updated_at
                FROM projects p
                LEFT JOIN plans pl ON pl.id = p.plan_id
                LEFT JOIN company_projects cp ON cp.id = p.id
                WHERE cp.id IS NULL;
            ''')

            cursor.execute('''
                SELECT setval(
                    'company_projects_id_seq',
                    COALESCE((SELECT MAX(id) FROM company_projects), 0) + 1,
                    false
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS interviews (
                    id SERIAL PRIMARY KEY,
                    plan_id INTEGER,
                    participant_name VARCHAR(255) NOT NULL,
                    consultant_name VARCHAR(255) NOT NULL,
                    interview_date DATE,
                    format VARCHAR(50), -- 'Presencial', 'Online', 'Telefone'
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (plan_id) REFERENCES plans (id)
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS plan_sections (
                    id SERIAL PRIMARY KEY,
                    plan_id INTEGER,
                    section_name VARCHAR(100) NOT NULL, -- 'interviews', 'drivers', 'okrs', etc.
                    status VARCHAR(20) DEFAULT 'open', -- 'open', 'closed'
                    closed_by VARCHAR(255), -- Nome do usuário que fechou
                    closed_at TIMESTAMP,
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (plan_id) REFERENCES plans (id),
                    UNIQUE(plan_id, section_name)
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS vision_records (
                    id SERIAL PRIMARY KEY,
                    plan_id INTEGER,
                    participants TEXT NOT NULL, -- JSON array de IDs dos participantes
                    consultants TEXT NOT NULL, -- JSON array de nomes dos consultores
                    vision_date DATE,
                    format VARCHAR(50), -- 'Presencial', 'Online', 'Telefone'
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (plan_id) REFERENCES plans (id)
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS market_records (
                    id SERIAL PRIMARY KEY,
                    plan_id INTEGER,
                    participants TEXT NOT NULL, -- Texto livre dos participantes
                    consultants TEXT NOT NULL, -- Texto livre dos consultores
                    market_date DATE,
                    format VARCHAR(50), -- 'Presencial', 'Online', 'Telefone'
                    global_context TEXT,
                    sector_context TEXT,
                    market_size TEXT,
                    growth_space TEXT,
                    threats TEXT,
                    consumer_behavior TEXT,
                    competition TEXT,
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (plan_id) REFERENCES plans (id)
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS company_records (
                    id SERIAL PRIMARY KEY,
                    plan_id INTEGER,
                    participants TEXT NOT NULL, -- Texto livre dos participantes
                    consultants TEXT NOT NULL, -- Texto livre dos consultores
                    company_date DATE,
                    bsc_financial TEXT,
                    bsc_commercial TEXT,
                    bsc_process TEXT,
                    bsc_learning TEXT,
                    tri_commercial TEXT,
                    tri_adm_fin TEXT,
                    tri_operational TEXT,
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (plan_id) REFERENCES plans (id)
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS alignment_records (
                    id SERIAL PRIMARY KEY,
                    plan_id INTEGER,
                    topic TEXT NOT NULL,
                    description TEXT NOT NULL,
                    consensus TEXT,
                    priority TEXT,
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (plan_id) REFERENCES plans (id)
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS misalignment_records (
                    id SERIAL PRIMARY KEY,
                    plan_id INTEGER,
                    issue TEXT NOT NULL,
                    description TEXT NOT NULL,
                    severity TEXT,
                    impact TEXT,
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (plan_id) REFERENCES plans (id)
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS directional_records (
                    id SERIAL PRIMARY KEY,
                    plan_id INTEGER,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL,
                    status TEXT DEFAULT 'draft',
                    owner TEXT,
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (plan_id) REFERENCES plans (id)
                )
            ''')

            # AI Agents configuration table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS ai_agents (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT,
                    version TEXT DEFAULT '1.0',
                    status TEXT DEFAULT 'active',
                    page TEXT NOT NULL,
                    section TEXT NOT NULL,
                    button_text TEXT NOT NULL,
                    required_data TEXT,
                    optional_data TEXT,
                    prompt_template TEXT,
                    format_type TEXT DEFAULT 'markdown',
                    output_field TEXT DEFAULT 'ai_insights',
                    response_template TEXT,
                    timeout INTEGER DEFAULT 300,
                    max_retries INTEGER DEFAULT 3,
                    execution_mode TEXT DEFAULT 'sequential',
                    cache_enabled BOOLEAN DEFAULT TRUE,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            ''')
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error initializing database: {e}")
            return False
    
    def seed_data(self) -> bool:
        """Seed database with initial data"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Check if data already exists
            cursor.execute('SELECT COUNT(*) FROM companies')
            if cursor.fetchone()[0] > 0:
                conn.close()
                return True
            
            # Insert sample companies
            companies = [
                ('Alimentos Tia Sonia',),
                ('Tech Solutions',),
                ('Consultoria ABC',)
            ]
            cursor.executemany('INSERT INTO companies (name) VALUES (%s)', companies)
            
            # Get company IDs
            cursor.execute('SELECT id FROM companies ORDER BY id')
            company_ids = [row[0] for row in cursor.fetchall()]
            
            # Insert sample plans
            plans = [
                (company_ids[0], 'Transformacao Digital 2025', 2025),
                (company_ids[1], 'Expansao Mercado 2025', 2025),
                (company_ids[2], 'Reestruturacao 2025', 2025)
            ]
            cursor.executemany('INSERT INTO plans (company_id, name, year) VALUES (%s, %s, %s)', plans)
            
            # Get plan IDs
            cursor.execute('SELECT id FROM plans ORDER BY id')
            plan_ids = [row[0] for row in cursor.fetchall()]
            
            # Insert sample participants
            participants = [
                (plan_ids[0], 'Ana Souza', 'Diretora', 'ana@tiasonia.com', '(11) 99999-0001'),
                (plan_ids[0], 'Carlos Silva', 'Gerente', 'carlos@tiasonia.com', '(11) 99999-0002'),
                (plan_ids[0], 'Marcos Fenecio', 'Consultor', 'marcos@consultoria.com', '(11) 99999-0003'),
                (plan_ids[1], 'João Santos', 'CEO', 'joao@techsolutions.com', '(11) 99999-0004'),
                (plan_ids[2], 'Maria Oliveira', 'Diretora', 'maria@consultoriaabc.com', '(11) 99999-0005')
            ]
            cursor.executemany('INSERT INTO participants (plan_id, name, role, email, phone) VALUES (%s, %s, %s, %s, %s)', participants)
            
            # Insert sample company data
            company_data = [
                (plan_ids[0], 'Alimentos Tia Sonia', 'Tia Sonia Alimentos Ltda', '12.345.678/0001-90', 'regional', 'internet-nacional', 'Alimentar familias com qualidade', 'Ser referencia em alimentos saudaveis', 'Qualidade, Inovacao, Sustentabilidade', 2, 5, 15),
                (plan_ids[1], 'Tech Solutions', 'Tech Solutions Ltda', '98.765.432/0001-10', 'nacional', 'internet-global', 'Transformar negocios com tecnologia', 'Liderar inovacao tecnologica', 'Inovacao, Excelencia, Colaboracao', 3, 8, 25),
                (plan_ids[2], 'Consultoria ABC', 'ABC Consultoria Ltda', '11.222.333/0001-44', 'regional', 'internet-nacional', 'Consultoria estrategica de qualidade', 'Ser referencia em consultoria', 'Etica, Qualidade, Resultados', 1, 3, 8)
            ]
            cursor.executemany('''INSERT INTO company_data 
                (plan_id, trade_name, legal_name, cnpj, coverage_physical, coverage_online, 
                 mission, vision, company_values, headcount_strategic, headcount_tactical, headcount_operational) 
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)''', company_data)
            
            # Insert sample drivers
            drivers = [
                (plan_ids[0], 'Digitalizacao de processos', 'Implementar sistemas digitais para otimizar operacoes', 'approved', 'high', 'Marcos Fenecio'),
                (plan_ids[0], 'Capacitacao da equipe', 'Treinar equipe em novas tecnologias', 'review', 'medium', 'Ana Souza'),
                (plan_ids[0], 'Otimizacao de processos', 'Melhorar eficiencia operacional', 'approved', 'high', 'Carlos Silva'),
                (plan_ids[1], 'Expansao de mercado', 'Ampliar atuacao para novos segmentos', 'draft', 'high', 'João Santos'),
                (plan_ids[2], 'Reestruturacao organizacional', 'Reorganizar estrutura da empresa', 'draft', 'medium', 'Maria Oliveira')
            ]
            cursor.executemany('INSERT INTO drivers (plan_id, title, description, status, priority, owner) VALUES (%s, %s, %s, %s, %s, %s)', drivers)
            
            # Insert sample OKRs
            okrs = [
                (plan_ids[0], 'Digitalizar 80% dos processos', 'Implementar sistemas digitais', 'global', None, 'draft'),
                (plan_ids[0], 'Capacitar 100% da equipe', 'Treinamento em novas tecnologias', 'area', 'RH', 'draft'),
                (plan_ids[0], 'Reduzir custos em 15%', 'Otimizacao de processos', 'global', None, 'draft'),
                (plan_ids[1], 'Expandir para 3 novos mercados', 'Ampliacao de atuacao', 'global', None, 'draft'),
                (plan_ids[2], 'Reestruturar organizacao', 'Nova estrutura organizacional', 'global', None, 'draft')
            ]
            cursor.executemany('INSERT INTO okrs (plan_id, title, description, type, area, status) VALUES (%s, %s, %s, %s, %s, %s)', okrs)
            
            # Insert sample projects (stored in company_projects)
            sample_projects = [
                (plan_ids[0], 'Sistema de Gestao', 'Implementar ERP', 'in_progress', 'high', 'Marcos Fenecio', '2025-01-01', '2025-06-30'),
                (plan_ids[0], 'Treinamento Digital', 'Capacitar equipe', 'planned', 'medium', 'Ana Souza', '2025-02-01', '2025-04-30'),
                (plan_ids[0], 'Otimizacao Logistica', 'Melhorar distribuicao', 'completed', 'high', 'Carlos Silva', '2024-10-01', '2024-12-31'),
                (plan_ids[1], 'Expansao Norte', 'Abrir filial no Norte', 'planned', 'high', 'João Santos', '2025-03-01', '2025-12-31'),
                (plan_ids[2], 'Reestruturacao RH', 'Nova estrutura de RH', 'planned', 'medium', 'Maria Oliveira', '2025-01-15', '2025-05-15')
            ]
            cursor.execute('SELECT id, company_id FROM plans WHERE id = ANY(%s)', (plan_ids,))
            plan_company_map = {row[0]: row[1] for row in cursor.fetchall()}
            cursor.executemany('''INSERT INTO company_projects (
                company_id, plan_id, title, description, status, priority, owner, start_date, end_date, okr_area_ref, activities, notes
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)''', [
                (
                    plan_company_map.get(plan_id),
                    plan_id,
                    title,
                    description,
                    status,
                    priority,
                    owner,
                    start_date,
                    end_date,
                    None,
                    None,
                    None
                )
                for plan_id, title, description, status, priority, owner, start_date, end_date in sample_projects
            ])
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error seeding data: {e}")
            return False
    
    # Company operations
    def get_companies(self) -> List[Dict[str, Any]]:
        """Get all companies"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM companies ORDER BY name')
        companies = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        return companies
    
    def get_company(self, company_id: int) -> Optional[Dict[str, Any]]:
        """Get company by ID"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM companies WHERE id = %s', (company_id,))
        row = cursor.fetchone()
        
        conn.close()
        return dict(row) if row else None
    
    # Plan operations
    def get_plans_by_company(self, company_id: int) -> List[Dict[str, Any]]:
        """Get plans for a company"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM plans WHERE company_id = %s ORDER BY name', (company_id,))
        plans = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        return plans
    
    def get_plan(self, plan_id: int) -> Optional[Dict[str, Any]]:
        """Get plan by ID"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM plans WHERE id = %s', (plan_id,))
        row = cursor.fetchone()
        
        conn.close()
        return dict(row) if row else None
    
    def get_plan_with_company(self, plan_id: int) -> Optional[Dict[str, Any]]:
        """Get plan with company information"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT p.*, c.name as company_name 
            FROM plans p 
            JOIN companies c ON p.company_id = c.id 
            WHERE p.id = %s
        ''', (plan_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        return dict(row) if row else None
    
    # Participant operations
    def get_participants(self, plan_id: int) -> List[Dict[str, Any]]:
        """Get participants for a plan"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM participants WHERE plan_id = %s ORDER BY name', (plan_id,))
        participants = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        return participants
    
    def add_participant(self, plan_id: int, participant_data: Dict[str, Any]) -> Optional[int]:
        """Add new participant and return the ID"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO participants (plan_id, name, role, relation, email, cpf, phone, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            ''', (
                plan_id,
                participant_data.get('name'),
                participant_data.get('role'),
                participant_data.get('relation'),
                participant_data.get('email'),
                participant_data.get('cpf'),
                participant_data.get('phone'),
                participant_data.get('status', 'active')
            ))
            
            participant_id = cursor.fetchone()[0]
            conn.commit()
            conn.close()
            return participant_id
        except Exception as e:
            print(f"Error adding participant: {e}")
            return None
    
    def get_participant(self, participant_id: int) -> Optional[Dict[str, Any]]:
        """Get participant by ID"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM participants WHERE id = %s', (participant_id,))
            row = cursor.fetchone()
            
            conn.close()
            return dict(row) if row else None
        except Exception as e:
            print(f"Error getting participant: {e}")
            return None
    
    def update_participant(self, participant_id: int, participant_data: Dict[str, Any]) -> bool:
        """Update participant data"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE participants 
                SET name = %s, role = %s, relation = %s, email = %s, cpf = %s, phone = %s, status = %s, updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
            ''', (
                participant_data.get('name'),
                participant_data.get('role'),
                participant_data.get('relation'),
                participant_data.get('email'),
                participant_data.get('cpf'),
                participant_data.get('phone'),
                participant_data.get('status'),
                participant_id
            ))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error updating participant: {e}")
            return False
    
    def delete_participant(self, participant_id: int) -> bool:
        """Delete participant"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('DELETE FROM participants WHERE id = %s', (participant_id,))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error deleting participant: {e}")
            return False
    
    def update_participant_status(self, participant_id: int, status: str) -> bool:
        """Update participant status"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('UPDATE participants SET status = %s WHERE id = %s', (status, participant_id))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error updating participant status: {e}")
            return False
    
    # Message Templates Methods
    def get_message_templates(self, plan_id: int) -> List[Dict[str, Any]]:
        """Get message templates for a plan"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM message_templates WHERE plan_id = %s', (plan_id,))
            rows = cursor.fetchall()
            
            conn.close()
            return [dict(row) for row in rows]
        except Exception as e:
            print(f"Error getting message templates: {e}")
            return []
    
    def get_message_template(self, plan_id: int, message_type: str) -> Optional[Dict[str, Any]]:
        """Get specific message template"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM message_templates WHERE plan_id = %s AND message_type = %s', (plan_id, message_type))
            row = cursor.fetchone()
            
            conn.close()
            return dict(row) if row else None
        except Exception as e:
            print(f"Error getting message template: {e}")
            return None
    
    def save_message_template(self, plan_id: int, message_type: str, subject: str, content: str) -> bool:
        """Save or update message template"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Check if template exists
            cursor.execute('SELECT id FROM message_templates WHERE plan_id = %s AND message_type = %s', (plan_id, message_type))
            existing = cursor.fetchone()
            
            if existing:
                # Update existing template
                cursor.execute('''
                    UPDATE message_templates 
                    SET subject = %s, content = %s, updated_at = CURRENT_TIMESTAMP
                    WHERE plan_id = %s AND message_type = %s
                ''', (subject, content, plan_id, message_type))
            else:
                # Insert new template
                cursor.execute('''
                    INSERT INTO message_templates (plan_id, message_type, subject, content)
                    VALUES (%s, %s, %s, %s)
                ''', (plan_id, message_type, subject, content))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error saving message template: {e}")
            return False
    
    # Company data operations
    def get_company_data(self, plan_id: int) -> Optional[Dict[str, Any]]:
        """Get company data for a plan"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM company_data WHERE plan_id = %s', (plan_id,))
        row = cursor.fetchone()
        
        conn.close()
        return dict(row) if row else None
    
    def update_company_data(self, plan_id: int, data: Dict[str, Any]) -> bool:
        """Update company data"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("ALTER TABLE company_data ADD COLUMN IF NOT EXISTS other_information TEXT")
            
            # Check if company data exists
            cursor.execute('SELECT id FROM company_data WHERE plan_id = %s', (plan_id,))
            existing = cursor.fetchone()
            
            if existing:
                # Update existing
                cursor.execute('''
                    UPDATE company_data SET
                        trade_name = %s, legal_name = %s, cnpj = %s, coverage_physical = %s, coverage_online = %s,
                        mission = %s, vision = %s, company_values = %s, headcount_strategic = %s, headcount_tactical = %s, headcount_operational = %s,
                        other_information = %s,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE plan_id = %s
                ''', (
                    data.get('trade_name'),
                    data.get('legal_name'),
                    data.get('cnpj'),
                    data.get('coverage_physical'),
                    data.get('coverage_online'),
                    data.get('mission'),
                    data.get('vision'),
                    data.get('company_values'),
                    int(data.get('headcount_strategic', 0)),
                    int(data.get('headcount_tactical', 0)),
                    int(data.get('headcount_operational', 0)),
                    data.get('other_information'),
                    plan_id
                ))
            else:
                # Insert new
                cursor.execute('''
                    INSERT INTO company_data 
                    (plan_id, trade_name, legal_name, cnpj, coverage_physical, coverage_online, 
                     mission, vision, company_values, headcount_strategic, headcount_tactical, headcount_operational, other_information)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ''', (
                    plan_id,
                    data.get('trade_name'),
                    data.get('legal_name'),
                    data.get('cnpj'),
                    data.get('coverage_physical'),
                    data.get('coverage_online'),
                    data.get('mission'),
                    data.get('vision'),
                    data.get('company_values'),
                    int(data.get('headcount_strategic', 0)),
                    int(data.get('headcount_tactical', 0)),
                    int(data.get('headcount_operational', 0)),
                    data.get('other_information')
                ))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error updating company data: {e}")
            return False
    
    # Driver operations
    def get_drivers(self, plan_id: int) -> List[Dict[str, Any]]:
        """Get drivers for a plan"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM drivers WHERE plan_id = %s ORDER BY created_at', (plan_id,))
        drivers = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        return drivers
    
    def add_driver(self, plan_id: int, driver_data: Dict[str, Any]) -> bool:
        """Add new driver"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO drivers (plan_id, title, description, status, priority, owner)
                VALUES (%s, %s, %s, %s, %s, %s)
            ''', (
                plan_id,
                driver_data.get('title'),
                driver_data.get('description'),
                driver_data.get('status', 'draft'),
                driver_data.get('priority'),
                driver_data.get('owner')
            ))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error adding driver: {e}")
            return False
    
    # OKR Global preliminary analysis operations
    def get_okr_preliminary_records(self, plan_id: int) -> List[Dict[str, Any]]:
        '''Get preliminary OKR analyses for a plan'''
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, plan_id, analysis, created_at, updated_at
                FROM okr_preliminary_records
                WHERE plan_id = %s
                ORDER BY created_at DESC
            ''', (plan_id,))
            records = [dict(row) for row in cursor.fetchall()]
            conn.close()
            return records
        except Exception as e:
            print(f"Error getting preliminary OKR records: {e}")
            return []

    def get_okr_preliminary_record(self, record_id: int) -> Optional[Dict[str, Any]]:
        '''Get a preliminary OKR analysis by ID'''
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, plan_id, analysis, created_at, updated_at
                FROM okr_preliminary_records
                WHERE id = %s
            ''', (record_id,))
            row = cursor.fetchone()
            conn.close()
            return dict(row) if row else None
        except Exception as e:
            print(f"Error getting preliminary OKR record: {e}")
            return None

    def add_okr_preliminary_record(self, plan_id: int, analysis: str) -> Optional[int]:
        '''Create a preliminary OKR analysis and return its ID'''
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO okr_preliminary_records (plan_id, analysis)
                VALUES (%s, %s)
                RETURNING id
            ''', (plan_id, analysis))
            new_id = cursor.fetchone()[0]
            conn.commit()
            conn.close()
            return new_id
        except Exception as e:
            print(f"Error adding preliminary OKR record: {e}")
            return None

    def update_okr_preliminary_record(self, record_id: int, analysis: str) -> bool:
        '''Update a preliminary OKR analysis'''
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE okr_preliminary_records
                SET analysis = %s, updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
            ''', (analysis, record_id))
            conn.commit()
            rows_affected = cursor.rowcount
            conn.close()
            return rows_affected > 0
        except Exception as e:
            print(f"Error updating preliminary OKR record: {e}")
            return False

    def delete_okr_preliminary_record(self, record_id: int) -> bool:
        '''Delete a preliminary OKR analysis'''
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute('DELETE FROM okr_preliminary_records WHERE id = %s', (record_id,))
            conn.commit()
            rows_affected = cursor.rowcount
            conn.close()
            return rows_affected > 0
        except Exception as e:
            print(f"Error deleting preliminary OKR record: {e}")
            return False

    # OKR Global records operations
    def get_global_okr_records(self, plan_id: int, stage: str) -> List[Dict[str, Any]]:
        '''Get OKR records for a plan and stage'''
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, plan_id, stage, objective, okr_type, type_display, owner_id, owner, deadline, observations, directional, created_at, updated_at
                FROM okr_global_records
                WHERE plan_id = %s AND stage = %s
                ORDER BY created_at DESC
            ''', (plan_id, stage))
            rows = cursor.fetchall()
            records = []
            for row in rows:
                cursor.execute('''
                    SELECT id, okr_id, label, target, deadline, owner_id, owner, indicator_id, position
                    FROM okr_global_key_results
                    WHERE okr_id = %s
                    ORDER BY position ASC, id ASC
                ''', (row['id'],))
                key_results = [dict(kr) for kr in cursor.fetchall()]
                record = dict(row)
                record['key_results'] = key_results
                records.append(record)
            conn.close()
            return records
        except Exception as e:
            print(f"Error getting global OKR records: {e}")
            return []

    def get_global_okr_record(self, okr_id: int) -> Optional[Dict[str, Any]]:
        '''Get a single OKR record with its key results'''
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, plan_id, stage, objective, okr_type, type_display, owner_id, owner, deadline, observations, directional, created_at, updated_at
                FROM okr_global_records
                WHERE id = %s
            ''', (okr_id,))
            row = cursor.fetchone()
            if not row:
                conn.close()
                return None
            cursor.execute('''
                SELECT id, okr_id, label, target, deadline, owner_id, owner, indicator_id, position
                FROM okr_global_key_results
                WHERE okr_id = %s
                ORDER BY position ASC, id ASC
            ''', (okr_id,))
            key_results = [dict(kr) for kr in cursor.fetchall()]
            record = dict(row)
            record['key_results'] = key_results
            conn.close()
            return record
        except Exception as e:
            print(f"Error getting global OKR record: {e}")
            return None

    def add_global_okr_record(self, plan_id: int, stage: str, okr_data: Dict[str, Any], key_results: List[Dict[str, Any]]) -> Optional[int]:
        '''Create a new OKR record and return its ID'''
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO okr_global_records (plan_id, stage, objective, okr_type, type_display, owner_id, owner, deadline, observations, directional)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            ''', (
                plan_id,
                stage,
                okr_data.get('objective', ''),
                okr_data.get('okr_type', ''),
                okr_data.get('type_display'),
                okr_data.get('owner_id'),
                okr_data.get('owner'),
                okr_data.get('deadline'),
                okr_data.get('observations'),
                okr_data.get('directional')
            ))
            okr_id = cursor.fetchone()[0]
            for position, kr in enumerate(key_results):
                cursor.execute('''
                    INSERT INTO okr_global_key_results (okr_id, label, target, deadline, owner_id, owner, indicator_id, position)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ''', (
                    okr_id,
                    kr.get('label', ''),
                    kr.get('target'),
                    kr.get('deadline'),
                    kr.get('owner_id'),
                    kr.get('owner'),
                    kr.get('indicator_id'),
                    position
                ))
            conn.commit()
            conn.close()
            return okr_id
        except Exception as e:
            print(f"Error adding global OKR record: {e}")
            return None

    def update_global_okr_record(self, okr_id: int, okr_data: Dict[str, Any], key_results: List[Dict[str, Any]]) -> bool:
        '''Update an existing OKR record'''
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE okr_global_records
                SET objective = %s, okr_type = %s, type_display = %s, owner_id = %s, owner = %s, deadline = %s, observations = %s, directional = %s, updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
            ''', (
                okr_data.get('objective', ''),
                okr_data.get('okr_type', ''),
                okr_data.get('type_display'),
                okr_data.get('owner_id'),
                okr_data.get('owner'),
                okr_data.get('deadline'),
                okr_data.get('observations'),
                okr_data.get('directional'),
                okr_id
            ))
            cursor.execute('DELETE FROM okr_global_key_results WHERE okr_id = %s', (okr_id,))
            for position, kr in enumerate(key_results):
                cursor.execute('''
                    INSERT INTO okr_global_key_results (okr_id, label, target, deadline, owner_id, owner, indicator_id, position)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ''', (
                    okr_id,
                    kr.get('label', ''),
                    kr.get('target'),
                    kr.get('deadline'),
                    kr.get('owner_id'),
                    kr.get('owner'),
                    kr.get('indicator_id'),
                    position
                ))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error updating global OKR record: {e}")
            return False

    def delete_global_okr_record(self, okr_id: int) -> bool:
        '''Delete an OKR record and its key results'''
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute('DELETE FROM okr_global_key_results WHERE okr_id = %s', (okr_id,))
            cursor.execute('DELETE FROM okr_global_records WHERE id = %s', (okr_id,))
            conn.commit()
            rows_affected = cursor.rowcount
            conn.close()
            return rows_affected > 0
        except Exception as e:
            print(f"Error deleting global OKR record: {e}")
            return False

    def bulk_delete_global_okr_records(self, plan_id: int, stage: str, okr_ids: List[int]) -> int:
        '''Bulk delete OKR records for a stage and return deleted count'''
        if not okr_ids:
            return 0
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            placeholders = ','.join(['%s'] * len(okr_ids))
            cursor.execute(f'DELETE FROM okr_global_key_results WHERE okr_id IN ({placeholders})', tuple(okr_ids))
            params = (plan_id, stage, *okr_ids)
            cursor.execute(f'DELETE FROM okr_global_records WHERE plan_id = %s AND stage = %s AND id IN ({placeholders})', params)
            deleted = cursor.rowcount
            conn.commit()
            conn.close()
            return deleted
        except Exception as e:
            print(f"Error bulk deleting OKR records: {e}")
            return 0

    def search_global_okr_records(self, plan_id: int, stage: str, query: str) -> List[Dict[str, Any]]:
        '''Search OKR records by objective, owner or observations'''
        try:
            like_query = f"%{query}%"
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, plan_id, stage, objective, okr_type, type_display, owner_id, owner, deadline, observations, directional, created_at, updated_at
                FROM okr_global_records
                WHERE plan_id = %s AND stage = %s AND (objective ILIKE %s OR owner ILIKE %s OR observations ILIKE %s)
                ORDER BY created_at DESC
            ''', (plan_id, stage, like_query, like_query, like_query))
            rows = cursor.fetchall()
            results = []
            for row in rows:
                cursor.execute('''
                    SELECT id, okr_id, label, target, deadline, owner_id, owner, indicator_id, position
                    FROM okr_global_key_results
                    WHERE okr_id = %s
                    ORDER BY position ASC, id ASC
                ''', (row['id'],))
                key_results = [dict(kr) for kr in cursor.fetchall()]
                record = dict(row)
                record['key_results'] = key_results
                results.append(record)
            conn.close()
            return results
        except Exception as e:
            print(f"Error searching OKR records: {e}")
            return []

    # Project operations
    def get_company_projects(self, company_id: int) -> List[Dict[str, Any]]:
        """Get all projects for a company"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT
                p.*,
                pl.name AS plan_name
            FROM company_projects p
            LEFT JOIN plans pl ON pl.id = p.plan_id
            WHERE p.company_id = %s
            ORDER BY p.created_at ASC, p.id ASC
        ''', (company_id,))
        projects = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return projects

    def get_projects(self, plan_id: int) -> List[Dict[str, Any]]:
        """Get projects for a plan"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT
                p.*,
                pl.name AS plan_name
            FROM company_projects p
            LEFT JOIN plans pl ON pl.id = p.plan_id
            WHERE p.plan_id = %s
            ORDER BY p.created_at ASC, p.id ASC
        ''', (plan_id,))
        projects = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return projects

    def add_project(self, plan_id: int, project_data: Dict[str, Any]) -> bool:
        """Add new project"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute('SELECT company_id FROM plans WHERE id = %s', (plan_id,))
            plan_row = cursor.fetchone()
            if not plan_row or plan_row[0] is None:
                conn.close()
                return False
            company_id = plan_row[0]

            cursor.execute('''
                INSERT INTO company_projects (
                    company_id, plan_id, title, description, status, priority,
                    owner, start_date, end_date, okr_area_ref, activities, notes
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ''', (
                company_id,
                plan_id,
                project_data.get('title'),
                project_data.get('description'),
                project_data.get('status', 'planned'),
                project_data.get('priority'),
                project_data.get('owner'),
                project_data.get('start_date'),
                project_data.get('end_date'),
                project_data.get('okr_area_ref'),
                project_data.get('activities'),
                project_data.get('notes')
            ))

            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error adding project (PostgreSQL): {e}")
            return False

    def update_project(self, project_id: int, project_data: Dict[str, Any]) -> bool:
        """Update existing project"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE company_projects SET
                    title = %s,
                    description = %s,
                    status = %s,
                    priority = %s,
                    owner = %s,
                    start_date = %s,
                    end_date = %s,
                    okr_area_ref = %s,
                    activities = %s,
                    notes = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
            ''', (
                project_data.get('title'),
                project_data.get('description'),
                project_data.get('status', 'planned'),
                project_data.get('priority'),
                project_data.get('owner'),
                project_data.get('start_date'),
                project_data.get('end_date'),
                project_data.get('okr_area_ref'),
                project_data.get('activities'),
                project_data.get('notes'),
                project_id
            ))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error updating project (PostgreSQL): {e}")
            return False

    def delete_project(self, project_id: int) -> bool:
        """Delete project"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute('DELETE FROM company_projects WHERE id = %s', (project_id,))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error deleting project (PostgreSQL): {e}")
            return False

    def get_project(self, project_id: int) -> Optional[Dict[str, Any]]:
        """Get single project by ID"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                SELECT
                    p.*,
                    pl.name AS plan_name
                FROM company_projects p
                LEFT JOIN plans pl ON pl.id = p.plan_id
                WHERE p.id = %s
            ''', (project_id,))
            row = cursor.fetchone()
            conn.close()
            return dict(row) if row else None
        except Exception as e:
            print(f"Error getting project (PostgreSQL): {e}")
            return None

    def get_company_project(self, company_id: int, project_id: int) -> Optional[Dict[str, Any]]:
        """Get project ensuring it belongs to a company"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT
                p.*,
                pl.name AS plan_name
            FROM company_projects p
            LEFT JOIN plans pl ON pl.id = p.plan_id
            WHERE p.id = %s AND p.company_id = %s
        ''', (project_id, company_id))
        row = cursor.fetchone()
        conn.close()
        if row:
            return dict(row)
        return None
    
    # Company creation
    def create_company(self, company_data: Dict[str, Any]) -> Optional[int]:
        """Create new company and return company ID"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO companies (name, legal_name, industry, size, description)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id
            ''', (
                company_data.get('name'),
                company_data.get('legal_name'),
                company_data.get('industry'),
                company_data.get('size'),
                company_data.get('description')
            ))
            
            company_id = cursor.fetchone()[0]
            conn.commit()
            conn.close()
            return company_id
        except Exception as e:
            print(f"Error creating company: {e}")
            return None
    
    # Plan creation
    def create_plan(self, plan_data: Dict[str, Any]) -> Optional[int]:
        """Create new plan and return plan ID"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO plans (company_id, name, description, start_date, end_date, status)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id
            ''', (
                plan_data.get('company_id'),
                plan_data.get('name'),
                plan_data.get('description'),
                plan_data.get('start_date'),
                plan_data.get('end_date'),
                plan_data.get('status', 'active')
            ))
            
            plan_id = cursor.fetchone()[0]
            conn.commit()
            conn.close()
            return plan_id
        except Exception as e:
            print(f"Error creating plan: {e}")
            return None
    
    # Interview operations
    def get_interviews(self, plan_id: int) -> List[Dict[str, Any]]:
        """Get interviews for a plan"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM interviews WHERE plan_id = %s ORDER BY created_at DESC
            ''', (plan_id,))
            
            interviews = [dict(row) for row in cursor.fetchall()]
            conn.close()
            return interviews
        except Exception as e:
            print(f"Error getting interviews: {e}")
            return []
    
    def add_interview(self, plan_id: int, interview_data: Dict[str, Any]) -> bool:
        """Add new interview"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO interviews (plan_id, participant_name, consultant_name, interview_date, format, notes)
                VALUES (%s, %s, %s, %s, %s, %s)
            ''', (
                plan_id,
                interview_data.get('participant_name'),
                interview_data.get('consultant_name'),
                interview_data.get('interview_date'),
                interview_data.get('format'),
                interview_data.get('notes')
            ))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error adding interview: {e}")
            return False
    
    def get_interview(self, interview_id: int) -> Optional[Dict[str, Any]]:
        """Get interview by ID"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM interviews WHERE id = %s', (interview_id,))
            row = cursor.fetchone()
            
            conn.close()
            return dict(row) if row else None
        except Exception as e:
            print(f"Error getting interview: {e}")
            return None
    
    def update_interview(self, interview_id: int, interview_data: Dict[str, Any]) -> bool:
        """Update interview data"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE interviews SET 
                    participant_name = %s, consultant_name = %s, interview_date = %s, 
                    format = %s, notes = %s, updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
            ''', (
                interview_data.get('participant_name'),
                interview_data.get('consultant_name'),
                interview_data.get('interview_date'),
                interview_data.get('format'),
                interview_data.get('notes'),
                interview_id
            ))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error updating interview: {e}")
            return False
    
    def delete_interview(self, interview_id: int) -> bool:
        """Delete interview"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('DELETE FROM interviews WHERE id = %s', (interview_id,))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error deleting interview: {e}")
            return False
    
    # Plan Section operations
    def get_section_status(self, plan_id: int, section_name: str) -> Optional[Dict[str, Any]]:
        """Get section status for a plan"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM plan_sections WHERE plan_id = %s AND section_name = %s
            ''', (plan_id, section_name))
            
            row = cursor.fetchone()
            conn.close()
            
            return dict(row) if row else None
        except Exception as e:
            print(f"Error getting section status: {e}")
            return None
    
    def update_section_status(self, plan_id: int, section_name: str, status: str, closed_by: str = None, notes: str = None) -> bool:
        """Update section status"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Verificar se já existe um registro
            cursor.execute('SELECT id FROM plan_sections WHERE plan_id = %s AND section_name = %s', (plan_id, section_name))
            existing = cursor.fetchone()
            
            if existing:
                # Para seções que armazenam dados JSON no campo notes, preservar os dados existentes
                if section_name == 'directionals-approvals':
                    # Buscar dados existentes
                    cursor.execute('SELECT notes FROM plan_sections WHERE plan_id = %s AND section_name = %s', (plan_id, section_name))
                    existing_data = cursor.fetchone()
                    
                    if existing_data and existing_data[0]:
                        # Preservar dados existentes e adicionar motivo da conclusão se fornecido
                        try:
                            import json
                            existing_notes = json.loads(existing_data[0])
                            if isinstance(existing_notes, dict):
                                if notes:  # Se foi fornecido um motivo da conclusão
                                    existing_notes['conclusion_reason'] = notes
                                notes = json.dumps(existing_notes)
                            else:
                                # Se os dados existentes não são um dict, manter como estão
                                notes = existing_data[0]
                        except:
                            # Se não conseguir fazer parse, manter dados existentes
                            notes = existing_data[0]
                    else:
                        # Se não há dados existentes, usar apenas o motivo se fornecido
                        if notes:
                            notes = json.dumps({'conclusion_reason': notes})
                        else:
                            notes = None
                
                # Atualizar registro existente
                cursor.execute('''
                    UPDATE plan_sections SET 
                        status = %s, closed_by = %s, closed_at = %s, notes = %s, updated_at = CURRENT_TIMESTAMP
                    WHERE plan_id = %s AND section_name = %s
                ''', (status, closed_by, 
                      'CURRENT_TIMESTAMP' if status == 'closed' else None, 
                      notes, plan_id, section_name))
            else:
                # Criar novo registro
                cursor.execute('''
                    INSERT INTO plan_sections (plan_id, section_name, status, closed_by, closed_at, notes)
                    VALUES (%s, %s, %s, %s, %s, %s)
                ''', (plan_id, section_name, status, closed_by,
                      'CURRENT_TIMESTAMP' if status == 'closed' else None, notes))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error updating section status: {e}")
            return False
    
    def update_section_consultant_notes(self, plan_id: int, section_name: str, consultant_notes: str) -> bool:
        """Update section consultant notes"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Verificar se já existe registro
            cursor.execute('''
                SELECT id FROM plan_sections 
                WHERE plan_id = %s AND section_name = %s
            ''', (plan_id, section_name))
            
            existing = cursor.fetchone()
            
            if existing:
                # Atualizar registro existente
                cursor.execute('''
                    UPDATE plan_sections 
                    SET notes = %s, updated_at = CURRENT_TIMESTAMP
                    WHERE plan_id = %s AND section_name = %s
                ''', (consultant_notes, plan_id, section_name))
            else:
                # Criar novo registro
                cursor.execute('''
                    INSERT INTO plan_sections (plan_id, section_name, status, notes)
                    VALUES (%s, %s, 'open', %s)
                ''', (plan_id, section_name, consultant_notes))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error updating section consultant notes: {e}")
            return False
    
    def update_section_adjustments(self, plan_id: int, section_name: str, adjustments: str) -> bool:
        """Update section adjustments"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # First, ensure the plan_sections table has an adjustments column
            try:
                cursor.execute('ALTER TABLE plan_sections ADD COLUMN adjustments TEXT')
                conn.commit()
            except Exception:
                # Column already exists, ignore error
                pass
            
            # Verificar se já existe registro
            cursor.execute('''
                SELECT id FROM plan_sections 
                WHERE plan_id = %s AND section_name = %s
            ''', (plan_id, section_name))
            
            existing = cursor.fetchone()
            
            if existing:
                # Atualizar registro existente
                cursor.execute('''
                    UPDATE plan_sections 
                    SET adjustments = %s, updated_at = CURRENT_TIMESTAMP
                    WHERE plan_id = %s AND section_name = %s
                ''', (adjustments, plan_id, section_name))
            else:
                # Criar novo registro
                cursor.execute('''
                    INSERT INTO plan_sections (plan_id, section_name, status, adjustments)
                    VALUES (%s, %s, 'open', %s)
                ''', (plan_id, section_name, adjustments))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error updating section adjustments: {e}")
            return False
    
    # Vision Records operations
    def get_vision_records(self, plan_id: int) -> List[Dict[str, Any]]:
        """Get vision records for a plan"""
        try:
            import json
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM vision_records WHERE plan_id = %s ORDER BY created_at DESC
            ''', (plan_id,))
            
            records = []
            for row in cursor.fetchall():
                records.append({
                    'id': row['id'],
                    'plan_id': row['plan_id'],
                    'participants': row['participants'] or '',  # Texto livre
                    'consultants': row['consultants'] or '',     # Texto livre
                    'vision_date': row['vision_date'],
                    'format': row['format'],
                    'notes': row['notes'],
                    'created_at': row['created_at'],
                    'updated_at': row['updated_at']
                })
            
            conn.close()
            return records
        except Exception as e:
            print(f"Error getting vision records: {e}")
            return []
    
    def add_vision_record(self, plan_id: int, vision_data: Dict[str, Any]) -> bool:
        """Add new vision record"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO vision_records (plan_id, participants, consultants, vision_date, format, notes)
                VALUES (%s, %s, %s, %s, %s, %s)
            ''', (
                plan_id,
                vision_data.get('participants', ''),
                vision_data.get('consultants', ''),
                vision_data.get('vision_date'),
                vision_data.get('format'),
                vision_data.get('notes')
            ))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error adding vision record: {e}")
            return False
    
    def get_vision_record(self, vision_id: int) -> Optional[Dict[str, Any]]:
        """Get vision record by ID"""
        try:
            import json
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM vision_records WHERE id = %s', (vision_id,))
            row = cursor.fetchone()
            
            conn.close()
            if row:
                return {
                    'id': row['id'],
                    'plan_id': row['plan_id'],
                    'participants': row['participants'] or '',
                    'consultants': row['consultants'] or '',
                    'vision_date': row['vision_date'],
                    'format': row['format'],
                    'notes': row['notes'],
                    'created_at': row['created_at'],
                    'updated_at': row['updated_at']
                }
            return None
        except Exception as e:
            print(f"Error getting vision record: {e}")
            return None
    
    def update_vision_record(self, vision_id: int, vision_data: Dict[str, Any]) -> bool:
        """Update vision record data"""
        try:
            import json
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE vision_records SET 
                    participants = %s, consultants = %s, vision_date = %s, 
                    format = %s, notes = %s, updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
            ''', (
                vision_data.get('participants', ''),
                vision_data.get('consultants', ''),
                vision_data.get('vision_date'),
                vision_data.get('format'),
                vision_data.get('notes'),
                vision_id
            ))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error updating vision record: {e}")
            return False
    
    def delete_vision_record(self, vision_id: int) -> bool:
        """Delete vision record"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('DELETE FROM vision_records WHERE id = %s', (vision_id,))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error deleting vision record: {e}")
            return False
    
    # Market Records Methods
    def get_market_records(self, plan_id: int) -> List[Dict[str, Any]]:
        """Get market records for a plan"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM market_records WHERE plan_id = %s ORDER BY created_at DESC
            ''', (plan_id,))
            
            records = []
            for row in cursor.fetchall():
                records.append({
                    'id': row['id'],
                    'plan_id': row['plan_id'],
                    'participants': row['participants'] or '',  # Texto livre
                    'consultants': row['consultants'] or '',     # Texto livre
                    'market_date': row['market_date'],
                    'format': row['format'],
                    'global_context': row['global_context'],
                    'sector_context': row['sector_context'],
                    'market_size': row['market_size'],
                    'growth_space': row['growth_space'],
                    'threats': row['threats'],
                    'consumer_behavior': row['consumer_behavior'],
                    'competition': row['competition'],
                    'notes': row['notes'],
                    'created_at': row['created_at'],
                    'updated_at': row['updated_at']
                })
            
            conn.close()
            return records
        except Exception as e:
            print(f"Error getting market records: {e}")
            return []
    
    def add_market_record(self, plan_id: int, market_data: Dict[str, Any]) -> bool:
        """Add new market record"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO market_records (plan_id, participants, consultants, market_date, format, 
                                          global_context, sector_context, market_size, growth_space, 
                                          threats, consumer_behavior, competition, notes)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ''', (
                plan_id,
                market_data.get('participants', ''),
                market_data.get('consultants', ''),
                market_data.get('market_date'),
                market_data.get('format'),
                market_data.get('global_context'),
                market_data.get('sector_context'),
                market_data.get('market_size'),
                market_data.get('growth_space'),
                market_data.get('threats'),
                market_data.get('consumer_behavior'),
                market_data.get('competition'),
                market_data.get('notes')
            ))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error adding market record: {e}")
            return False
    
    def get_market_record(self, market_id: int) -> Optional[Dict[str, Any]]:
        """Get market record by ID"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM market_records WHERE id = %s', (market_id,))
            row = cursor.fetchone()
            
            conn.close()
            if row:
                return {
                    'id': row['id'],
                    'plan_id': row['plan_id'],
                    'participants': row['participants'] or '',
                    'consultants': row['consultants'] or '',
                    'market_date': row['market_date'],
                    'format': row['format'],
                    'global_context': row['global_context'],
                    'sector_context': row['sector_context'],
                    'market_size': row['market_size'],
                    'growth_space': row['growth_space'],
                    'threats': row['threats'],
                    'consumer_behavior': row['consumer_behavior'],
                    'competition': row['competition'],
                    'notes': row['notes'],
                    'created_at': row['created_at'],
                    'updated_at': row['updated_at']
                }
            return None
        except Exception as e:
            print(f"Error getting market record: {e}")
            return None
    
    def update_market_record(self, market_id: int, market_data: Dict[str, Any]) -> bool:
        """Update market record data"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE market_records SET 
                    participants = %s, consultants = %s, market_date = %s, 
                    format = %s, global_context = %s, sector_context = %s, 
                    market_size = %s, growth_space = %s, threats = %s, 
                    consumer_behavior = %s, competition = %s, notes = %s, 
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
            ''', (
                market_data.get('participants', ''),
                market_data.get('consultants', ''),
                market_data.get('market_date'),
                market_data.get('format'),
                market_data.get('global_context'),
                market_data.get('sector_context'),
                market_data.get('market_size'),
                market_data.get('growth_space'),
                market_data.get('threats'),
                market_data.get('consumer_behavior'),
                market_data.get('competition'),
                market_data.get('notes'),
                market_id
            ))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error updating market record: {e}")
            return False
    
    def delete_market_record(self, market_id: int) -> bool:
        """Delete market record"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('DELETE FROM market_records WHERE id = %s', (market_id,))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error deleting market record: {e}")
            return False
    
    # Company Records Methods
    def get_company_records(self, plan_id: int) -> List[Dict[str, Any]]:
        """Get company records for a plan"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id, participants, consultants, company_date, bsc_financial, 
                       bsc_commercial, bsc_process, bsc_learning, tri_commercial, 
                       tri_adm_fin, tri_operational, notes, created_at, updated_at
                FROM company_records 
                WHERE plan_id = %s
                ORDER BY created_at DESC
            ''', (plan_id,))
            
            records = []
            for row in cursor.fetchall():
                records.append({
                    'id': row[0],
                    'participants': row[1],
                    'consultants': row[2],
                    'company_date': row[3],
                    'bsc_financial': row[4],
                    'bsc_commercial': row[5],
                    'bsc_process': row[6],
                    'bsc_learning': row[7],
                    'tri_commercial': row[8],
                    'tri_adm_fin': row[9],
                    'tri_operational': row[10],
                    'notes': row[11],
                    'created_at': row[12],
                    'updated_at': row[13]
                })
            
            conn.close()
            return records
        except Exception as e:
            print(f"Error getting company records: {e}")
            return []
    
    def add_company_record(self, plan_id: int, company_data: Dict[str, Any]) -> bool:
        """Add new company record"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO company_records (plan_id, participants, consultants, company_date,
                                          bsc_financial, bsc_commercial, bsc_process, bsc_learning,
                                          tri_commercial, tri_adm_fin, tri_operational, notes)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ''', (
                plan_id,
                company_data.get('participants', ''),
                company_data.get('consultants', ''),
                company_data.get('company_date'),
                company_data.get('bsc_financial'),
                company_data.get('bsc_commercial'),
                company_data.get('bsc_process'),
                company_data.get('bsc_learning'),
                company_data.get('tri_commercial'),
                company_data.get('tri_adm_fin'),
                company_data.get('tri_operational'),
                company_data.get('notes')
            ))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error adding company record: {e}")
            return False
    
    def get_company_record(self, company_id: int) -> Optional[Dict[str, Any]]:
        """Get company record by ID"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id, participants, consultants, company_date, bsc_financial, 
                       bsc_commercial, bsc_process, bsc_learning, tri_commercial, 
                       tri_adm_fin, tri_operational, notes, created_at, updated_at
                FROM company_records 
                WHERE id = %s
            ''', (company_id,))
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return {
                    'id': row[0],
                    'participants': row[1],
                    'consultants': row[2],
                    'company_date': row[3],
                    'bsc_financial': row[4],
                    'bsc_commercial': row[5],
                    'bsc_process': row[6],
                    'bsc_learning': row[7],
                    'tri_commercial': row[8],
                    'tri_adm_fin': row[9],
                    'tri_operational': row[10],
                    'notes': row[11],
                    'created_at': row[12],
                    'updated_at': row[13]
                }
            return None
        except Exception as e:
            print(f"Error getting company record: {e}")
            return None
    
    def update_company_record(self, company_id: int, company_data: Dict[str, Any]) -> bool:
        """Update company record data"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE company_records 
                SET participants = %s, consultants = %s, company_date = %s, 
                    bsc_financial = %s, bsc_commercial = %s, bsc_process = %s, 
                    bsc_learning = %s, tri_commercial = %s, tri_adm_fin = %s, 
                    tri_operational = %s, notes = %s, updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
            ''', (
                company_data.get('participants', ''),
                company_data.get('consultants', ''),
                company_data.get('company_date'),
                company_data.get('bsc_financial'),
                company_data.get('bsc_commercial'),
                company_data.get('bsc_process'),
                company_data.get('bsc_learning'),
                company_data.get('tri_commercial'),
                company_data.get('tri_adm_fin'),
                company_data.get('tri_operational'),
                company_data.get('notes'),
                company_id
            ))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error updating company record: {e}")
            return False
    
    def delete_company_record(self, company_id: int) -> bool:
        """Delete company record"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('DELETE FROM company_records WHERE id = %s', (company_id,))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error deleting company record: {e}")
            return False
    
    # Alignment Records Methods
    def get_alignment_records(self, plan_id: int) -> List[Dict[str, Any]]:
        """Get alignment records for a plan"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id, topic, description, consensus, priority, notes, created_at, updated_at
                FROM alignment_records 
                WHERE plan_id = %s
                ORDER BY created_at DESC
            ''', (plan_id,))
            
            records = []
            for row in cursor.fetchall():
                records.append({
                    'id': row[0],
                    'topic': row[1],
                    'description': row[2],
                    'consensus': row[3],
                    'priority': row[4],
                    'notes': row[5],
                    'created_at': row[6],
                    'updated_at': row[7]
                })
            
            conn.close()
            return records
        except Exception as e:
            print(f"Error getting alignment records: {e}")
            return []
    
    def add_alignment_record(self, plan_id: int, alignment_data: Dict[str, Any]) -> bool:
        """Add new alignment record"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO alignment_records (plan_id, topic, description, consensus, priority, notes)
                VALUES (%s, %s, %s, %s, %s, %s)
            ''', (
                plan_id,
                alignment_data.get('topic', ''),
                alignment_data.get('description', ''),
                alignment_data.get('consensus'),
                alignment_data.get('priority'),
                alignment_data.get('notes')
            ))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error adding alignment record: {e}")
            return False
    
    def get_alignment_record(self, alignment_id: int) -> Optional[Dict[str, Any]]:
        """Get alignment record by ID"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id, topic, description, consensus, priority, notes, created_at, updated_at
                FROM alignment_records 
                WHERE id = %s
            ''', (alignment_id,))
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return {
                    'id': row[0],
                    'topic': row[1],
                    'description': row[2],
                    'consensus': row[3],
                    'priority': row[4],
                    'notes': row[5],
                    'created_at': row[6],
                    'updated_at': row[7]
                }
            return None
        except Exception as e:
            print(f"Error getting alignment record: {e}")
            return None
    
    def update_alignment_record(self, alignment_id: int, alignment_data: Dict[str, Any]) -> bool:
        """Update alignment record data"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE alignment_records 
                SET topic = %s, description = %s, consensus = %s, priority = %s, notes = %s, updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
            ''', (
                alignment_data.get('topic', ''),
                alignment_data.get('description', ''),
                alignment_data.get('consensus'),
                alignment_data.get('priority'),
                alignment_data.get('notes'),
                alignment_id
            ))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error updating alignment record: {e}")
            return False
    
    def delete_alignment_record(self, alignment_id: int) -> bool:
        """Delete alignment record"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('DELETE FROM alignment_records WHERE id = %s', (alignment_id,))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error deleting alignment record: {e}")
            return False
    
    # Misalignment Records Methods
    def get_misalignment_records(self, plan_id: int) -> List[Dict[str, Any]]:
        """Get misalignment records for a plan"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id, issue, description, severity, impact, notes, created_at, updated_at
                FROM misalignment_records 
                WHERE plan_id = %s
                ORDER BY created_at DESC
            ''', (plan_id,))
            
            records = []
            for row in cursor.fetchall():
                records.append({
                    'id': row[0],
                    'issue': row[1],
                    'description': row[2],
                    'severity': row[3],
                    'impact': row[4],
                    'notes': row[5],
                    'created_at': row[6],
                    'updated_at': row[7]
                })
            
            conn.close()
            return records
        except Exception as e:
            print(f"Error getting misalignment records: {e}")
            return []
    
    def add_misalignment_record(self, plan_id: int, misalignment_data: Dict[str, Any]) -> bool:
        """Add new misalignment record"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO misalignment_records (plan_id, issue, description, severity, impact, notes)
                VALUES (%s, %s, %s, %s, %s, %s)
            ''', (
                plan_id,
                misalignment_data.get('issue', ''),
                misalignment_data.get('description', ''),
                misalignment_data.get('severity'),
                misalignment_data.get('impact'),
                misalignment_data.get('notes')
            ))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error adding misalignment record: {e}")
            return False
    
    def get_misalignment_record(self, misalignment_id: int) -> Optional[Dict[str, Any]]:
        """Get misalignment record by ID"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id, issue, description, severity, impact, notes, created_at, updated_at
                FROM misalignment_records 
                WHERE id = %s
            ''', (misalignment_id,))
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return {
                    'id': row[0],
                    'issue': row[1],
                    'description': row[2],
                    'severity': row[3],
                    'impact': row[4],
                    'notes': row[5],
                    'created_at': row[6],
                    'updated_at': row[7]
                }
            return None
        except Exception as e:
            print(f"Error getting misalignment record: {e}")
            return None
    
    def update_misalignment_record(self, misalignment_id: int, misalignment_data: Dict[str, Any]) -> bool:
        """Update misalignment record data"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE misalignment_records 
                SET issue = %s, description = %s, severity = %s, impact = %s, notes = %s, updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
            ''', (
                misalignment_data.get('issue', ''),
                misalignment_data.get('description', ''),
                misalignment_data.get('severity'),
                misalignment_data.get('impact'),
                misalignment_data.get('notes'),
                misalignment_id
            ))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error updating misalignment record: {e}")
            return False
    
    def delete_misalignment_record(self, misalignment_id: int) -> bool:
        """Delete misalignment record"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('DELETE FROM misalignment_records WHERE id = %s', (misalignment_id,))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error deleting misalignment record: {e}")
            return False
    
    # Directional Records Methods
    def get_directional_records(self, plan_id: int) -> List[Dict[str, Any]]:
        """Get directional records for a plan"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id, title, description, status, owner, notes, created_at, updated_at
                FROM directional_records 
                WHERE plan_id = %s
                ORDER BY created_at DESC
            ''', (plan_id,))
            
            records = []
            for row in cursor.fetchall():
                records.append({
                    'id': row[0],
                    'title': row[1],
                    'description': row[2],
                    'status': row[3],
                    'owner': row[4],
                    'notes': row[5],
                    'created_at': row[6],
                    'updated_at': row[7]
                })
            
            conn.close()
            return records
        except Exception as e:
            print(f"Error getting directional records: {e}")
            return []
    
    def get_directionals_final_records(self, plan_id: int) -> List[Dict[str, Any]]:
        """Get final directional records for a plan (status = 'final' or 'approved')"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id, title, description, status, owner, notes, created_at, updated_at
                FROM directional_records 
                WHERE plan_id = %s AND (status = 'final' OR status = 'approved')
                ORDER BY created_at DESC
            ''', (plan_id,))
            
            records = []
            for row in cursor.fetchall():
                records.append({
                    'id': row[0],
                    'title': row[1],
                    'description': row[2],
                    'status': row[3],
                    'owner': row[4],
                    'notes': row[5],
                    'created_at': row[6],
                    'updated_at': row[7]
                })
            
            conn.close()
            return records
        except Exception as e:
            print(f"Error getting final directional records: {e}")
            return []
    
    def add_directional_record(self, plan_id: int, directional_data: Dict[str, Any]) -> bool:
        """Add new directional record"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO directional_records (plan_id, title, description, status, owner, notes)
                VALUES (%s, %s, %s, %s, %s, %s)
            ''', (
                plan_id,
                directional_data.get('title', ''),
                directional_data.get('description', ''),
                directional_data.get('status', 'draft'),
                directional_data.get('owner'),
                directional_data.get('notes')
            ))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error adding directional record: {e}")
            return False
    
    def get_directional_record(self, directional_id: int) -> Optional[Dict[str, Any]]:
        """Get directional record by ID"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id, title, description, status, owner, notes, created_at, updated_at
                FROM directional_records 
                WHERE id = %s
            ''', (directional_id,))
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return {
                    'id': row[0],
                    'title': row[1],
                    'description': row[2],
                    'status': row[3],
                    'owner': row[4],
                    'notes': row[5],
                    'created_at': row[6],
                    'updated_at': row[7]
                }
            return None
        except Exception as e:
            print(f"Error getting directional record: {e}")
            return None
    
    def update_directional_record(self, directional_id: int, directional_data: Dict[str, Any]) -> bool:
        """Update directional record data"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE directional_records 
                SET title = %s, description = %s, status = %s, owner = %s, notes = %s, updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
            ''', (
                directional_data.get('title', ''),
                directional_data.get('description', ''),
                directional_data.get('status', 'draft'),
                directional_data.get('owner'),
                directional_data.get('notes'),
                directional_id
            ))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error updating directional record: {e}")
            return False
    
    def delete_directional_record(self, directional_id: int) -> bool:
        """Delete directional record"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('DELETE FROM directional_records WHERE id = %s', (directional_id,))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error deleting directional record: {e}")
            return False

    def _ensure_employees_schema(self, cursor) -> None:
        """Ensure employees table and columns exist."""
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS employees (
                id SERIAL PRIMARY KEY,
                company_id INTEGER NOT NULL REFERENCES companies (id) ON DELETE CASCADE,
                name VARCHAR(255) NOT NULL,
                email VARCHAR(255),
                phone VARCHAR(100),
                role_id INTEGER REFERENCES roles (id) ON DELETE SET NULL,
                department VARCHAR(255),
                hire_date DATE,
                status VARCHAR(50) DEFAULT 'active',
                weekly_hours REAL DEFAULT 40,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cursor.execute('''
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name = 'employees' AND column_name = 'notes'
                ) THEN
                    ALTER TABLE employees ADD COLUMN notes TEXT;
                END IF;
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name = 'employees' AND column_name = 'status'
                ) THEN
                    ALTER TABLE employees ADD COLUMN status VARCHAR(50) DEFAULT 'active';
                END IF;
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name = 'employees' AND column_name = 'updated_at'
                ) THEN
                    ALTER TABLE employees ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
                END IF;
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name = 'employees' AND column_name = 'weekly_hours'
                ) THEN
                    ALTER TABLE employees ADD COLUMN weekly_hours REAL DEFAULT 40;
                END IF;
            END
            $$;
        ''')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_employees_company ON employees(company_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_employees_role ON employees(role_id)')
        cursor.connection.commit()

    def _normalize_employee_payload(self, employee: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize employee payload into sanitized dictionary."""
        def _clean_text(value: Any) -> Optional[str]:
            if value is None:
                return None
            value = str(value).strip()
            return value or None

        name_raw = employee.get('name', '')
        name = str(name_raw).strip() if name_raw is not None else ''
        if not name:
            raise ValueError('Nome é obrigatório')

        email = _clean_text(employee.get('email'))
        phone = _clean_text(employee.get('phone'))
        department = _clean_text(employee.get('department'))
        notes = _clean_text(employee.get('notes'))

        status_raw = employee.get('status', 'active')
        if isinstance(status_raw, str):
            status = status_raw.strip().lower() or 'active'
        else:
            status = 'active'

        hire_date_value = employee.get('hire_date')
        hire_date: Optional[str] = None
        if isinstance(hire_date_value, (datetime, date)):
            hire_date = hire_date_value.strftime('%Y-%m-%d')
        elif isinstance(hire_date_value, str):
            value = hire_date_value.strip()
            hire_date = value or None

        role_id_value = employee.get('role_id')
        if isinstance(role_id_value, str):
            role_id_value = role_id_value.strip()
            if role_id_value:
                try:
                    role_id = int(role_id_value)
                except ValueError:
                    role_id = None
            else:
                role_id = None
        elif isinstance(role_id_value, (int, float)):
            try:
                role_id = int(role_id_value)
            except (TypeError, ValueError):
                role_id = None
        else:
            role_id = None

        return {
            'name': name,
            'email': email,
            'phone': phone,
            'role_id': role_id,
            'department': department,
            'hire_date': hire_date,
            'status': status,
            'notes': notes
        }

    def list_employees(self, company_id: int) -> List[Dict[str, Any]]:
        conn = self._get_connection()
        ensure_cursor = conn.cursor()
        self._ensure_employees_schema(ensure_cursor)
        ensure_cursor.close()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT e.*, r.title AS role_name
            FROM employees e
            LEFT JOIN roles r ON e.role_id = r.id
            WHERE e.company_id = %s
            ORDER BY LOWER(COALESCE(e.name, '')) ASC, e.id ASC
        ''', (company_id,))
        rows = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return rows

    def get_employee(self, company_id: int, employee_id: int) -> Optional[Dict[str, Any]]:
        conn = self._get_connection()
        ensure_cursor = conn.cursor()
        self._ensure_employees_schema(ensure_cursor)
        ensure_cursor.close()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT e.*, r.title AS role_name
            FROM employees e
            LEFT JOIN roles r ON e.role_id = r.id
            WHERE e.company_id = %s AND e.id = %s
            LIMIT 1
        ''', (company_id, employee_id))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    def create_employee(self, company_id: int, employee_data: Dict[str, Any]) -> Optional[int]:
        conn = self._get_connection()
        ensure_cursor = conn.cursor()
        self._ensure_employees_schema(ensure_cursor)
        ensure_cursor.close()
        try:
            cursor = conn.cursor()
            normalized = self._normalize_employee_payload(employee_data)
            cursor.execute('''
                INSERT INTO employees (
                    company_id, name, email, phone, role_id, department, hire_date, status, notes
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            ''', (
                company_id,
                normalized['name'],
                normalized['email'],
                normalized['phone'],
                normalized['role_id'],
                normalized['department'],
                normalized['hire_date'],
                normalized['status'],
                normalized['notes']
            ))
            new_id = cursor.fetchone()[0]
            conn.commit()
            return new_id
        except ValueError:
            conn.rollback()
            raise
        except Exception as exc:
            conn.rollback()
            print(f"Error creating employee: {exc}")
            return None
        finally:
            conn.close()

    def update_employee(self, company_id: int, employee_id: int, employee_data: Dict[str, Any]) -> bool:
        conn = self._get_connection()
        ensure_cursor = conn.cursor()
        self._ensure_employees_schema(ensure_cursor)
        ensure_cursor.close()
        try:
            cursor = conn.cursor()
            normalized = self._normalize_employee_payload(employee_data)
            cursor.execute('''
                UPDATE employees
                SET name = %s, email = %s, phone = %s, role_id = %s, department = %s,
                    hire_date = %s, status = %s, notes = %s, updated_at = CURRENT_TIMESTAMP
                WHERE id = %s AND company_id = %s
            ''', (
                normalized['name'],
                normalized['email'],
                normalized['phone'],
                normalized['role_id'],
                normalized['department'],
                normalized['hire_date'],
                normalized['status'],
                normalized['notes'],
                employee_id,
                company_id
            ))
            conn.commit()
            return cursor.rowcount > 0
        except ValueError:
            conn.rollback()
            raise
        except Exception as exc:
            conn.rollback()
            print(f"Error updating employee: {exc}")
            return False
        finally:
            conn.close()

    def delete_employee(self, company_id: int, employee_id: int) -> bool:
        conn = self._get_connection()
        ensure_cursor = conn.cursor()
        self._ensure_employees_schema(ensure_cursor)
        ensure_cursor.close()
        try:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM employees WHERE id = %s AND company_id = %s', (employee_id, company_id))
            conn.commit()
            return cursor.rowcount > 0
        except Exception as exc:
            conn.rollback()
            print(f"Error deleting employee: {exc}")
            return False
        finally:
            conn.close()

    # AI Agents configuration operations
    def get_ai_agents(self) -> List[Dict[str, Any]]:
        """List all AI agents configurations"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM ai_agents ORDER BY name')
            rows = cursor.fetchall()
            conn.close()
            return [dict(row) for row in rows]
        except Exception as e:
            print(f"Error getting AI agents: {e}")
            return []

    def get_ai_agent(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get a single AI agent configuration by ID"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM ai_agents WHERE id = %s', (agent_id,))
            row = cursor.fetchone()
            conn.close()
            return dict(row) if row else None
        except Exception as e:
            print(f"Error getting AI agent: {e}")
            return None

    def create_ai_agent(self, agent_data: Dict[str, Any]) -> bool:
        """Create a new AI agent configuration"""
        try:
            now = datetime.utcnow().isoformat()
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO ai_agents (
                    id, name, description, version, status, page, section, button_text,
                    required_data, optional_data, prompt_template, format_type, output_field,
                    response_template, timeout, max_retries, execution_mode, cache_enabled,
                    created_at, updated_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ''', (
                agent_data.get('id'),
                agent_data.get('name'),
                agent_data.get('description'),
                agent_data.get('version', '1.0'),
                agent_data.get('status', 'active'),
                agent_data.get('page'),
                agent_data.get('section'),
                agent_data.get('button_text'),
                agent_data.get('required_data'),
                agent_data.get('optional_data'),
                agent_data.get('prompt_template'),
                agent_data.get('format_type', 'markdown'),
                agent_data.get('output_field', 'ai_insights'),
                agent_data.get('response_template'),
                int(agent_data.get('timeout', 300)),
                int(agent_data.get('max_retries', 3)),
                agent_data.get('execution_mode', 'sequential'),
                True if str(agent_data.get('cache_enabled', 'true')).lower() in ('1','true','yes') else False,
                now,
                now
            ))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error creating AI agent: {e}")
            return False

    def update_ai_agent(self, agent_id: str, agent_data: Dict[str, Any]) -> bool:
        """Update an existing AI agent configuration"""
        try:
            now = datetime.utcnow().isoformat()
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE ai_agents SET
                    name = %s, description = %s, version = %s, status = %s, page = %s, section = %s, button_text = %s,
                    required_data = %s, optional_data = %s, prompt_template = %s, format_type = %s, output_field = %s,
                    response_template = %s, timeout = %s, max_retries = %s, execution_mode = %s, cache_enabled = %s,
                    updated_at = %s
                WHERE id = %s
            ''', (
                agent_data.get('name'),
                agent_data.get('description'),
                agent_data.get('version', '1.0'),
                agent_data.get('status', 'active'),
                agent_data.get('page'),
                agent_data.get('section'),
                agent_data.get('button_text'),
                agent_data.get('required_data'),
                agent_data.get('optional_data'),
                agent_data.get('prompt_template'),
                agent_data.get('format_type', 'markdown'),
                agent_data.get('output_field', 'ai_insights'),
                agent_data.get('response_template'),
                int(agent_data.get('timeout', 300)),
                int(agent_data.get('max_retries', 3)),
                agent_data.get('execution_mode', 'sequential'),
                True if str(agent_data.get('cache_enabled', 'true')).lower() in ('1','true','yes') else False,
                now,
                agent_id
            ))
            conn.commit()
            conn.close()
            return cursor.rowcount > 0
        except Exception as e:
            print(f"Error updating AI agent: {e}")
            return False

    def delete_ai_agent(self, agent_id: str) -> bool:
        """Delete an AI agent configuration"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute('DELETE FROM ai_agents WHERE id = %s', (agent_id,))
            conn.commit()
            deleted = cursor.rowcount
            conn.close()
            return deleted > 0
        except Exception as e:
            print(f"Error deleting AI agent: {e}")
            return False
    
    # ========== MÉTODOS ADICIONAIS PARA COMPLETAR A INTERFACE ==========
    
    def add_okr_area_preliminary_record(self, plan_id: int, analysis: str) -> Optional[int]:
        """Create a preliminary area OKR analysis and return the new ID"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO okr_area_preliminary_records (plan_id, analysis) VALUES (%s, %s) RETURNING id",
                (plan_id, analysis)
            )
            result = cursor.fetchone()
            conn.commit()
            conn.close()
            return result[0] if result else None
        except Exception as e:
            print(f"Error adding okr_area_preliminary_record: {e}")
            return None
    
    def update_okr_area_preliminary_record(self, record_id: int, analysis: str) -> bool:
        """Update a preliminary area OKR analysis"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE okr_area_preliminary_records SET analysis = %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s",
                (analysis, record_id)
            )
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error updating okr_area_preliminary_record: {e}")
            return False
    
    def delete_okr_area_preliminary_record(self, record_id: int) -> bool:
        """Delete a preliminary area OKR analysis"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM okr_area_preliminary_records WHERE id = %s", (record_id,))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error deleting okr_area_preliminary_record: {e}")
            return False
    
    def get_okr_area_preliminary_records(self, plan_id: int) -> List[Dict[str, Any]]:
        """Get all preliminary area OKR records for a plan"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM okr_area_preliminary_records WHERE plan_id = %s", (plan_id,))
            rows = cursor.fetchall()
            conn.close()
            return [dict(row) for row in rows]
        except Exception as e:
            print(f"Error getting okr_area_preliminary_records: {e}")
            return []
    
    def create_company_project(self, company_id: int, project_data: Dict[str, Any]) -> Optional[int]:
        """Create a project scoped to a company"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO company_projects (company_id, title, description, status, priority, owner, start_date, end_date, notes)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            ''', (
                company_id,
                project_data.get('title'),
                project_data.get('description'),
                project_data.get('status', 'planned'),
                project_data.get('priority'),
                project_data.get('owner'),
                project_data.get('start_date'),
                project_data.get('end_date'),
                project_data.get('notes')
            ))
            result = cursor.fetchone()
            conn.commit()
            conn.close()
            return result[0] if result else None
        except Exception as e:
            print(f"Error creating company_project: {e}")
            return None
    
    def list_company_meetings(self, company_id: int) -> List[Dict[str, Any]]:
        """List meetings registered for a company"""
        try:
            import json
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Fazer JOIN com company_projects para pegar project_title e project_code
            cursor.execute('''
                SELECT
                    m.*,
                    cp.title AS project_title,
                    cp.code AS project_code
                FROM meetings m
                LEFT JOIN company_projects cp ON cp.id = m.project_id
                WHERE m.company_id = %s
                ORDER BY
                    CASE WHEN m.scheduled_date IS NULL THEN 1 ELSE 0 END,
                    m.scheduled_date DESC,
                    CASE WHEN m.scheduled_time IS NULL THEN '23:59' ELSE m.scheduled_time END DESC,
                    m.created_at DESC
            ''', (company_id,))
            rows = cursor.fetchall()
            conn.close()
            
            # Parse JSON fields for each meeting
            meetings = []
            json_fields = {
                'guests_json': 'guests',
                'agenda_json': 'agenda',
                'participants_json': 'participants',
                'discussions_json': 'discussions',
                'activities_json': 'activities'
            }
            
            for row in rows:
                meeting = dict(row)
                
                # Parse JSON fields
                for json_field, target_field in json_fields.items():
                    if json_field in meeting and meeting[json_field]:
                        try:
                            if isinstance(meeting[json_field], str):
                                meeting[target_field] = json.loads(meeting[json_field])
                            else:
                                meeting[target_field] = meeting[json_field]
                        except (json.JSONDecodeError, TypeError):
                            meeting[target_field] = None
                    else:
                        meeting[target_field] = None
                
                # Garantir que todos os campos estejam presentes
                meeting.setdefault('scheduled_date', None)
                meeting.setdefault('scheduled_time', None)
                meeting.setdefault('actual_date', None)
                meeting.setdefault('actual_time', None)
                meeting.setdefault('status', 'draft')
                meeting.setdefault('project_title', None)
                meeting.setdefault('project_code', None)

                meeting['scheduled_date'] = self._format_date_value(meeting.get('scheduled_date'))
                meeting['actual_date'] = self._format_date_value(meeting.get('actual_date'))
                meeting['created_at'] = self._format_datetime_value(meeting.get('created_at'))
                meeting['updated_at'] = self._format_datetime_value(meeting.get('updated_at'))
                meeting['scheduled_time'] = self._format_time_value(meeting.get('scheduled_time'))
                meeting['actual_time'] = self._format_time_value(meeting.get('actual_time'))
                
                meetings.append(meeting)
            
            return meetings
        except Exception as e:
            print(f"Error listing company meetings: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def get_meeting(self, meeting_id: int) -> Optional[Dict[str, Any]]:
        """Retrieve a single meeting by ID"""
        try:
            import json
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Fazer JOIN com company_projects para pegar project_title e project_code
            cursor.execute('''
                SELECT
                    m.*,
                    cp.title AS project_title,
                    cp.code AS project_code
                FROM meetings m
                LEFT JOIN company_projects cp ON cp.id = m.project_id
                WHERE m.id = %s
            ''', (meeting_id,))
            row = cursor.fetchone()
            conn.close()
            
            if not row:
                return None
            
            meeting = dict(row)
            
            # Parse JSON fields
            json_fields = {
                'guests_json': 'guests',
                'agenda_json': 'agenda',
                'participants_json': 'participants',
                'discussions_json': 'discussions',
                'activities_json': 'activities'
            }
            
            for json_field, target_field in json_fields.items():
                if json_field in meeting and meeting[json_field]:
                    try:
                        if isinstance(meeting[json_field], str):
                            meeting[target_field] = json.loads(meeting[json_field])
                        else:
                            meeting[target_field] = meeting[json_field]
                    except (json.JSONDecodeError, TypeError):
                        meeting[target_field] = None
                else:
                    meeting[target_field] = None
            
            # Garantir que todos os campos estejam presentes
            meeting.setdefault('scheduled_date', None)
            meeting.setdefault('scheduled_time', None)
            meeting.setdefault('actual_date', None)
            meeting.setdefault('actual_time', None)
            meeting.setdefault('status', 'draft')
            meeting.setdefault('invite_notes', None)
            meeting.setdefault('meeting_notes', None)
            meeting.setdefault('project_title', None)
            meeting.setdefault('project_code', None)

            meeting['scheduled_date'] = self._format_date_value(meeting.get('scheduled_date'))
            meeting['actual_date'] = self._format_date_value(meeting.get('actual_date'))
            meeting['created_at'] = self._format_datetime_value(meeting.get('created_at'))
            meeting['updated_at'] = self._format_datetime_value(meeting.get('updated_at'))
            meeting['scheduled_time'] = self._format_time_value(meeting.get('scheduled_time'))
            meeting['actual_time'] = self._format_time_value(meeting.get('actual_time'))
            
            return meeting
        except Exception as e:
            print(f"❌ Error getting meeting: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def create_meeting(self, company_id: int, meeting_data: Dict[str, Any]) -> Optional[int]:
        """Create a meeting record and return its ID"""
        try:
            import json
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Encode JSON fields
            guests_json = json.dumps(meeting_data.get('guests', {'internal': [], 'external': []}), ensure_ascii=False) if meeting_data.get('guests') else None
            agenda_json = json.dumps(meeting_data.get('agenda', []), ensure_ascii=False) if meeting_data.get('agenda') else None
            participants_json = json.dumps(meeting_data.get('participants', {'internal': [], 'external': []}), ensure_ascii=False) if meeting_data.get('participants') else None
            discussions_json = json.dumps(meeting_data.get('discussions', []), ensure_ascii=False) if meeting_data.get('discussions') else None
            activities_json = json.dumps(meeting_data.get('activities', []), ensure_ascii=False) if meeting_data.get('activities') else None
            
            cursor.execute('''
                INSERT INTO meetings (
                    company_id, project_id, title,
                    scheduled_date, scheduled_time,
                    invite_notes, meeting_notes,
                    guests_json, agenda_json, participants_json,
                    discussions_json, activities_json, status
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            ''', (
                company_id,
                meeting_data.get('project_id'),
                meeting_data.get('title'),
                meeting_data.get('scheduled_date'),
                meeting_data.get('scheduled_time'),
                meeting_data.get('invite_notes'),
                meeting_data.get('meeting_notes'),
                guests_json,
                agenda_json,
                participants_json,
                discussions_json,
                activities_json,
                meeting_data.get('status', 'draft')
            ))
            result = cursor.fetchone()
            conn.commit()
            conn.close()
            return result[0] if result else None
        except Exception as e:
            print(f"Error creating meeting: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def update_meeting(self, meeting_id: int, meeting_data: Dict[str, Any]) -> bool:
        """Update meeting information"""
        try:
            import json
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Construir SET clause dinamicamente
            set_clauses = []
            params = []
            
            # Campos simples
            for key, value in meeting_data.items():
                if key in ['title', 'scheduled_date', 'scheduled_time', 'actual_date', 'actual_time', 
                          'status', 'invite_notes', 'meeting_notes', 'project_id']:
                    if value is not None:
                        set_clauses.append(f"{key} = %s")
                        params.append(value)
            
            # Campos JSON
            if 'guests' in meeting_data and meeting_data['guests'] is not None:
                set_clauses.append("guests_json = %s")
                params.append(json.dumps(meeting_data['guests'], ensure_ascii=False))
            
            if 'agenda' in meeting_data and meeting_data['agenda'] is not None:
                set_clauses.append("agenda_json = %s")
                params.append(json.dumps(meeting_data['agenda'], ensure_ascii=False))
            
            if 'participants' in meeting_data and meeting_data['participants'] is not None:
                set_clauses.append("participants_json = %s")
                params.append(json.dumps(meeting_data['participants'], ensure_ascii=False))
            
            if 'discussions' in meeting_data and meeting_data['discussions'] is not None:
                set_clauses.append("discussions_json = %s")
                params.append(json.dumps(meeting_data['discussions'], ensure_ascii=False))
            
            if 'activities' in meeting_data and meeting_data['activities'] is not None:
                set_clauses.append("activities_json = %s")
                params.append(json.dumps(meeting_data['activities'], ensure_ascii=False))
            
            if set_clauses:
                params.append(meeting_id)
                sql = f"UPDATE meetings SET {', '.join(set_clauses)}, updated_at = CURRENT_TIMESTAMP WHERE id = %s"
                cursor.execute(sql, tuple(params))
                conn.commit()
            
            conn.close()
            return True
        except Exception as e:
            print(f"Error updating meeting: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def delete_company(self, company_id: int) -> bool:
        """Delete company by ID"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM companies WHERE id = %s", (company_id,))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error deleting company: {e}")
            return False
    
    def get_workshop_discussions(self, plan_id: int, section_type: str = 'preliminary') -> Optional[Dict[str, Any]]:
        """Get workshop discussions for a plan and section type"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM workshop_discussions WHERE plan_id = %s AND section_type = %s",
                (plan_id, section_type)
            )
            row = cursor.fetchone()
            conn.close()
            return dict(row) if row else None
        except Exception as e:
            print(f"Error getting workshop discussions: {e}")
            return None
    
    def save_workshop_discussions(self, plan_id: int, section_type: str, content: str) -> bool:
        """Save workshop discussions"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Verificar se existe
            cursor.execute(
                "SELECT id FROM workshop_discussions WHERE plan_id = %s AND section_type = %s",
                (plan_id, section_type)
            )
            exists = cursor.fetchone()
            
            if exists:
                cursor.execute('''
                    UPDATE workshop_discussions 
                    SET content = %s, updated_at = CURRENT_TIMESTAMP 
                    WHERE plan_id = %s AND section_type = %s
                ''', (content, plan_id, section_type))
            else:
                cursor.execute('''
                    INSERT INTO workshop_discussions (plan_id, section_type, content) 
                    VALUES (%s, %s, %s)
                ''', (plan_id, section_type, content))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error saving workshop discussions: {e}")
            return False
    
    def delete_workshop_discussions(self, plan_id: int, section_type: str) -> bool:
        """Delete workshop discussions"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM workshop_discussions WHERE plan_id = %s AND section_type = %s",
                (plan_id, section_type)
            )
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error deleting workshop discussions: {e}")
            return False
    
    # ========== MÉTODOS PRIVADOS DE SCHEMA E NORMALIZAÇÃO ==========
    
    def _normalize_client_code(self, code: Optional[str]) -> Optional[str]:
        """Normalize client code to up to 3 alphanumeric characters or None"""
        if not code:
            return None
        normalized = ''.join(ch for ch in code.strip().upper() if ch.isalnum())
        if not normalized:
            return None
        return normalized[:3]
    
    def _normalize_activity_suffix(self, suffix: Optional[str]) -> Optional[str]:
        """Ensure activity suffix is a two-digit numeric string."""
        if suffix is None:
            return None
        suffix = ''.join(ch for ch in str(suffix).strip() if ch.isdigit())
        if not suffix:
            return None
        if len(suffix) > 2:
            suffix = suffix[-2:]
        return suffix.zfill(2)
    
    def _extract_activity_suffix(self, activity_code: Optional[str]) -> str:
        """Extract suffix from activity code (last segment)."""
        if not activity_code:
            return ''
        parts = str(activity_code).split('.')
        return parts[-1] if parts else ''
    
    def _build_activity_code(self, process_id: int, cursor, suffix: str) -> str:
        """Compose full activity code using process code and suffix."""
        cursor.execute('SELECT code FROM processes WHERE id = %s', (process_id,))
        row = cursor.fetchone()
        base_code = (row['code'] if row and row['code'] else f"PROC-{process_id}").strip()
        base_code = base_code.rstrip('.')
        return f"{base_code}.{suffix}"
    
    def _normalize_process_stage(self, stage: Optional[str]) -> str:
        """Coerce provided stage to a supported Kanban stage slug."""
        allowed_stages = {
            'inbox',          # Caixa de Entrada
            'out_of_scope',   # Fora de Escopo
            'designing',      # Modelando
            'deploying',      # Implantando
            'stabilizing',    # Estabilizando
            'stable'          # Estável
        }
        if not stage:
            return 'inbox'
        normalized = stage.strip().lower().replace('-', '_')
        return normalized if normalized in allowed_stages else 'inbox'
    
    def _kanban_stage_to_structuring_level(self, stage: str) -> str:
        """Mapeia o estágio do Kanban para o nível de estruturação."""
        stage_mapping = {
            'inbox': '',
            'out_of_scope': '',
            'designing': 'in_progress',
            'deploying': 'in_progress',
            'stabilizing': 'in_progress',
            'stable': 'stabilized'
        }
        return stage_mapping.get(stage, '')
    
    def _sanitize_company_code(self, raw_code: Optional[str], company_id: int) -> str:
        """Sanitize company code fallback used to compose project identifiers."""
        if raw_code:
            cleaned = ''.join(ch for ch in str(raw_code).strip().upper() if ch.isalnum())
            if cleaned:
                return cleaned
        return str(company_id).zfill(2)
    
    def _compute_next_project_code(self, cursor, company_id: int) -> Tuple[str, int]:
        """Return next project code and sequence for a company."""
        cursor.execute('SELECT client_code FROM companies WHERE id = %s', (company_id,))
        row = cursor.fetchone()
        if row:
            row_dict = dict(row) if hasattr(row, 'keys') else {'client_code': row[0]}
            prefix = self._sanitize_company_code(row_dict.get('client_code'), company_id)
        else:
            prefix = self._sanitize_company_code(None, company_id)
        
        cursor.execute(
            'SELECT COALESCE(MAX(code_sequence), 0) AS max_seq FROM company_projects WHERE company_id = %s',
            (company_id,)
        )
        result = cursor.fetchone()
        if result:
            result_dict = dict(result) if hasattr(result, 'keys') else {'max_seq': result[0]}
            next_sequence = (result_dict.get('max_seq') or 0) + 1
        else:
            next_sequence = 1
        code = f"{prefix}.J.{next_sequence}"
        return code, next_sequence
    
    @staticmethod
    def _decode_json_column(value: Optional[str], default):
        """Decode JSON column value"""
        if not value:
            return default
        try:
            import json
            return json.loads(value)
        except Exception:
            return default
    
    @staticmethod
    def _encode_json_value(value):
        """Encode value to JSON"""
        if value is None:
            return None
        if isinstance(value, str):
            cleaned = value.strip()
            return cleaned if cleaned else None
        try:
            import json
            return json.dumps(value, ensure_ascii=False)
        except Exception:
            return None
    
    def _ensure_roles_columns(self, cursor):
        """Ensure roles table columns exist (PostgreSQL version)"""
        try:
            # No PostgreSQL, verificar colunas via information_schema
            cursor.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'roles' AND table_schema = 'public'
            """)
            columns = {row[0] for row in cursor.fetchall()}
            
            # Adicionar colunas faltantes
            if 'parent_role_id' not in columns:
                cursor.execute('ALTER TABLE roles ADD COLUMN parent_role_id INTEGER')
            if 'department' not in columns:
                cursor.execute('ALTER TABLE roles ADD COLUMN department TEXT')
            if 'color' not in columns:
                cursor.execute('ALTER TABLE roles ADD COLUMN color TEXT')
            if 'headcount_planned' not in columns:
                cursor.execute('ALTER TABLE roles ADD COLUMN headcount_planned INTEGER')
            if 'weekly_hours' not in columns:
                cursor.execute('ALTER TABLE roles ADD COLUMN weekly_hours INTEGER')
        except Exception as exc:
            print(f"Error ensuring roles columns: {exc}")
    
    def _ensure_employees_schema(self, cursor):
        """Ensure employees table exists (PostgreSQL version)"""
        # No PostgreSQL, a tabela já foi criada na migração
        # Este método é apenas para compatibilidade
        pass

    # ========== MÉTODOS COPIADOS DO SQLITE (ADAPTADOS) ==========

    def list_process_areas(self, company_id: int) -> List[Dict[str, Any]]:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM process_areas WHERE company_id = %s ORDER BY code, order_index, name', (company_id,))
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return rows
    


    def create_process_area(self, company_id: int, area: Dict[str, Any]) -> Optional[int]:
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Se order_index não foi fornecido, calcular o próximo
            order_index = area.get('order_index')
            if not order_index or order_index == 0:
                cursor.execute('SELECT MAX(order_index) as max_order FROM process_areas WHERE company_id = %s', (company_id,))
                row = cursor.fetchone()
                max_order = row['max_order'] if row and row['max_order'] else 0
                order_index = max_order + 1
            
            # Gerar código automático: {CLIENT_CODE}.C.{SEQUENCE}
            cursor.execute('SELECT client_code FROM companies WHERE id = %s', (company_id,))
            company_row = cursor.fetchone()
            client_code = company_row['client_code'] if company_row and company_row['client_code'] else 'XX'
            
            # Código da área: CLIENT.C.SEQUENCE
            area_code = f"{client_code}.C.{area.get('code', order_index)}"
            
            cursor.execute('''
                INSERT INTO process_areas (company_id, code, name, description, order_index, color)
                VALUES (%s, %s, %s, %s, %s, %s)
            ''', (
                company_id,
                area_code,
                area.get('name'),
                area.get('description'),
                int(order_index),
                area.get('color')
            ))
            new_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            return new_id
        except Exception as exc:
            print(f"Error creating process area: {exc}")
            return None
    


    def update_process_area(self, area_id: int, area: Dict[str, Any]) -> bool:
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Obter company_id da área
            cursor.execute('SELECT company_id FROM process_areas WHERE id = %s', (area_id,))
            row = cursor.fetchone()
            if not row:
                return False
            company_id = row['company_id']
            
            # Gerar código automático: {CLIENT_CODE}.C.{SEQUENCE}
            cursor.execute('SELECT client_code FROM companies WHERE id = %s', (company_id,))
            company_row = cursor.fetchone()
            client_code = company_row['client_code'] if company_row and company_row['client_code'] else 'XX'
            
            # Código da área: CLIENT.C.SEQUENCE
            order_index = int(area.get('order_index') or 0)
            area_code = f"{client_code}.C.{area.get('code', order_index)}"
            
            cursor.execute('''
                UPDATE process_areas SET
                    code = %s, name = %s, description = %s, order_index = %s, color = %s, updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
            ''', (
                area_code,
                area.get('name'),
                area.get('description'),
                order_index,
                area.get('color'),
                area_id
            ))
            conn.commit()
            conn.close()
            return True
        except Exception as exc:
            print(f"Error updating process area: {exc}")
            return False
    


    def delete_process_area(self, area_id: int) -> bool:
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute('DELETE FROM process_areas WHERE id = %s', (area_id,))
            conn.commit()
            conn.close()
            return True
        except Exception as exc:
            print(f"Error deleting process area: {exc}")
            return False
    
    # Macro Processes CRUD


    def list_macro_processes(self, company_id: int) -> List[Dict[str, Any]]:
        conn = self._get_connection()
        cursor = conn.cursor()
        # Order by area and sequence to ensure stable listing even before code generation
        cursor.execute('SELECT * FROM macro_processes WHERE company_id = %s ORDER BY area_id, order_index, name', (company_id,))
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return rows
    


    def create_macro_process(self, company_id: int, macro: Dict[str, Any]) -> Optional[int]:
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            area_id = int(macro.get('area_id'))
            
            # Se order_index não foi fornecido, calcular o próximo dentro da área
            order_index = macro.get('order_index')
            if not order_index or order_index == 0:
                cursor.execute('SELECT MAX(order_index) as max_order FROM macro_processes WHERE company_id = %s AND area_id = %s', (company_id, area_id))
                row = cursor.fetchone()
                max_order = row['max_order'] if row and row['max_order'] else 0
                order_index = max_order + 1
            
            cursor.execute('''
                INSERT INTO macro_processes (company_id, area_id, name, owner, description, order_index)
                VALUES (%s, %s, %s, %s, %s, %s)
            ''', (
                company_id,
                area_id,
                macro.get('name'),
                macro.get('owner'),
                macro.get('description'),
                int(order_index)
            ))
            new_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            # Gerar e atualizar código automaticamente
            self._update_macro_code(new_id, company_id, area_id)
            
            return new_id
        except Exception as exc:
            print(f"Error creating macro process: {exc}")
            return None
    


    def get_macro_process(self, macro_id: int) -> Optional[Dict[str, Any]]:
        """Get a single macro process by ID"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM macro_processes WHERE id = %s', (macro_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None
    


    def update_macro_process(self, macro_id: int, macro: Dict[str, Any]) -> bool:
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Primeiro, obter o company_id e area_id para regenerar o código
            cursor.execute('SELECT company_id, area_id FROM macro_processes WHERE id = %s', (macro_id,))
            row = cursor.fetchone()
            if not row:
                conn.close()
                return False
                
            company_id = row['company_id']
            area_id = int(macro.get('area_id'))
            
            cursor.execute('''
                UPDATE macro_processes SET
                    area_id = %s, name = %s, owner = %s, description = %s, order_index = %s, updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
            ''', (
                area_id,
                macro.get('name'),
                macro.get('owner'),
                macro.get('description'),
                int(macro.get('order_index') or 0),
                macro_id
            ))
            conn.commit()
            conn.close()
            
            # Regenerar código automaticamente após a atualização
            self._update_macro_code(macro_id, company_id, area_id)
            
            return True
        except Exception as exc:
            print(f"Error updating macro process: {exc}")
            return False
    


    def delete_macro_process(self, macro_id: int) -> bool:
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute('DELETE FROM macro_processes WHERE id = %s', (macro_id,))
            conn.commit()
            conn.close()
            return True
        except Exception as exc:
            print(f"Error deleting macro process: {exc}")
            return False
    
    # Processes CRUD


    def list_processes(self, company_id: int) -> List[Dict[str, Any]]:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM processes WHERE company_id = %s ORDER BY code, order_index, name', (company_id,))
        rows = []
        for row in cursor.fetchall():
            as_dict = dict(row)
            as_dict['kanban_stage'] = self._normalize_process_stage(as_dict.get('kanban_stage'))
            rows.append(as_dict)
        conn.close()
        return rows
    


    def create_process(self, company_id: int, process: Dict[str, Any]) -> Optional[int]:
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            macro_id = int(process.get('macro_id'))
            
            # Se order_index não foi fornecido, calcular o próximo dentro do macro
            order_index = process.get('order_index')
            if not order_index or order_index == 0:
                cursor.execute('SELECT MAX(order_index) as max_order FROM processes WHERE company_id = %s AND macro_id = %s', (company_id, macro_id))
                row = cursor.fetchone()
                max_order = row['max_order'] if row and row['max_order'] else 0
                order_index = max_order + 1
            
            # Gerar código automático: {MACRO_CODE}.{SEQUENCE}
            cursor.execute('SELECT code FROM macro_processes WHERE id = %s', (macro_id,))
            macro_row = cursor.fetchone()
            macro_code = macro_row['code'] if macro_row and macro_row['code'] else 'XX'
            
            # Código do processo: MACRO_CODE.SEQUENCE
            process_code = f"{macro_code}.{order_index}"
            
            stage = self._normalize_process_stage(process.get('kanban_stage') or process.get('stage'))
            # Mapear automaticamente o stage do Kanban para o nível de estruturação
            structuring_level = self._kanban_stage_to_structuring_level(stage)

            cursor.execute('''
                INSERT INTO processes (company_id, macro_id, code, name, structuring_level, performance_level, responsible, description, order_index, kanban_stage)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ''', (
                company_id,
                macro_id,
                process_code,
                process.get('name'),
                structuring_level,
                process.get('performance_level'),
                process.get('responsible'),
                process.get('description'),
                int(order_index),
                stage
            ))
            new_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            return new_id
        except Exception as exc:
            print(f"Error creating process: {exc}")
            return None
    


    def get_process(self, process_id: int) -> Optional[Dict[str, Any]]:
        """Retrieve a single process by ID."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM processes WHERE id = %s', (process_id,))
        row = cursor.fetchone()
        conn.close()
        if not row:
            return None
        record = dict(row)
        record['kanban_stage'] = self._normalize_process_stage(record.get('kanban_stage'))
        return record



    def update_process(self, process_id: int, process: Dict[str, Any]) -> bool:
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            macro_id = int(process.get('macro_id'))
            order_index = int(process.get('order_index') or 0)
            
            # Gerar código automático: {MACRO_CODE}.{SEQUENCE}
            cursor.execute('SELECT code FROM macro_processes WHERE id = %s', (macro_id,))
            macro_row = cursor.fetchone()
            macro_code = macro_row['code'] if macro_row and macro_row['code'] else 'XX'
            
            # Código do processo: MACRO_CODE.SEQUENCE
            process_code = f"{macro_code}.{order_index}"
            
            stage = self._normalize_process_stage(process.get('kanban_stage') or process.get('stage'))
            # Mapear automaticamente o stage do Kanban para o nível de estruturação
            structuring_level = self._kanban_stage_to_structuring_level(stage)

            cursor.execute('''
                UPDATE processes SET
                    macro_id = %s, code = %s, name = %s, structuring_level = %s, performance_level = %s, responsible = %s, description = %s, order_index = %s, kanban_stage = %s, updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
            ''', (
                macro_id,
                process_code,
                process.get('name'),
                structuring_level,
                process.get('performance_level'),
                process.get('responsible'),
                process.get('description'),
                order_index,
                stage,
                process_id
            ))
            conn.commit()
            conn.close()
            return True
        except Exception as exc:
            print(f"Error updating process: {exc}")
            return False



    def delete_process(self, process_id: int) -> bool:
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute('DELETE FROM processes WHERE id = %s', (process_id,))
            conn.commit()
            conn.close()
            return True
        except Exception as exc:
            print(f"Error deleting process: {exc}")
            return False
    


    def update_process_stage(self, process_id: int, stage: str) -> Optional[str]:
        """Update only the Kanban stage of a process and return the normalized stage."""
        try:
            normalized_stage = self._normalize_process_stage(stage)
            # Mapear automaticamente o stage do Kanban para o nível de estruturação
            structuring_level = self._kanban_stage_to_structuring_level(normalized_stage)
            
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE processes
                SET kanban_stage = %s, structuring_level = %s, updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
            ''', (normalized_stage, structuring_level, process_id))
            conn.commit()
            conn.close()
            return normalized_stage if cursor.rowcount > 0 else None
        except Exception as exc:
            print(f"Error updating process stage: {exc}")
            return None



    def update_process_notes(self, process_id: int, notes: str) -> bool:
        """Update only the notes field of a process."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE processes
                SET notes = %s, updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
            ''', (notes, process_id))
            conn.commit()
            conn.close()
            return cursor.rowcount > 0
        except Exception as exc:
            print(f"Error updating process notes: {exc}")
            return False



    def set_process_flow_document(self, process_id: int, path: Optional[str]) -> bool:
        """Associate a flow document (PDF ou imagem) to a process."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(
                '''
                UPDATE processes
                SET flow_document = %s, updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
                ''',
                (path, process_id)
            )
            conn.commit()
            conn.close()
            return cursor.rowcount > 0
        except Exception as exc:
            print(f"Error setting process flow document: {exc}")
            return False

    # POP activities


    def get_process_map(self, company_id: int) -> Dict[str, Any]:
        """Get complete process map structure"""
        areas = self.list_process_areas(company_id)
        macros = self.list_macro_processes(company_id)
        processes = self.list_processes(company_id)
        
        # Group macros by area
        for area in areas:
            area['macros'] = [m for m in macros if m['area_id'] == area['id']]
            # Group processes by macro
            for macro in area['macros']:
                macro['processes'] = [p for p in processes if p['macro_id'] == macro['id']]
        
        return {'areas': areas}



    def list_process_activities(self, process_id: int) -> List[Dict[str, Any]]:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            '''
            SELECT * FROM process_activities
            WHERE process_id = %s
            ORDER BY order_index, id
            ''',
            (process_id,)
        )
        activities = [dict(row) for row in cursor.fetchall()]
        if not activities:
            conn.close()
            return []

        for activity in activities:
            activity['code_suffix'] = self._extract_activity_suffix(activity.get('code'))

        activity_ids = [a['id'] for a in activities]
        cursor.execute(
            '''
            SELECT * FROM process_activity_entries
            WHERE activity_id IN ({})
            ORDER BY order_index, id
            '''.format(','.join('%s' for _ in activity_ids)),
            activity_ids
        )
        entry_rows = cursor.fetchall()
        conn.close()

        entries_by_activity = {}
        for entry in entry_rows:
            entry_dict = dict(entry)
            entries_by_activity.setdefault(entry_dict['activity_id'], []).append(entry_dict)

        for activity in activities:
            activity['entries'] = entries_by_activity.get(activity['id'], [])

        return activities



    def create_process_activity(self, process_id: int, activity: Dict[str, Any]) -> Optional[int]:
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            order_index = activity.get('order_index')
            if not order_index or order_index <= 0:
                cursor.execute(
                    'SELECT MAX(order_index) as max_order FROM process_activities WHERE process_id = %s',
                    (process_id,)
                )
                row = cursor.fetchone()
                max_order = row['max_order'] if row and row['max_order'] else 0
                order_index = max_order + 1

            suffix = self._normalize_activity_suffix(activity.get('code_suffix') or activity.get('suffix'))
            if suffix is None:
                conn.close()
                return None
            full_code = self._build_activity_code(process_id, cursor, suffix)

            cursor.execute(
                '''
                INSERT INTO process_activities (process_id, code, name, layout, order_index)
                VALUES (%s, %s, %s, %s, %s)
                ''',
                (
                    process_id,
                    full_code,
                    activity.get('name'),
                    activity.get('layout') or 'single',
                    order_index
                )
            )
            new_id = cursor.lastrowid
            conn.commit()
            conn.close()
            return new_id
        except Exception as exc:
            print(f"Error creating process activity: {exc}")
            return None



    def get_process_activity(self, activity_id: int) -> Optional[Dict[str, Any]]:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM process_activities WHERE id = %s', (activity_id,))
        row = cursor.fetchone()
        conn.close()
        if not row:
            return None
        data = dict(row)
        data['code_suffix'] = self._extract_activity_suffix(data.get('code'))
        return data



    def update_process_activity(self, activity_id: int, activity: Dict[str, Any]) -> bool:
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            suffix = self._normalize_activity_suffix(activity.get('code_suffix') or activity.get('suffix'))
            current = None
            if suffix:
                cursor.execute('SELECT process_id FROM process_activities WHERE id = %s', (activity_id,))
                current = cursor.fetchone()
                if not current:
                    conn.close()
                    return False
                full_code = self._build_activity_code(current['process_id'], cursor, suffix)
            else:
                full_code = activity.get('code')
            cursor.execute(
                '''
                UPDATE process_activities
                SET name = %s, layout = %s, order_index = %s, code = COALESCE(%s, code), updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
                ''',
                (
                    activity.get('name'),
                    activity.get('layout') or 'single',
                    activity.get('order_index') or 0,
                    full_code,
                    activity_id
                )
            )
            conn.commit()
            conn.close()
            return cursor.rowcount > 0
        except Exception as exc:
            print(f"Error updating process activity: {exc}")
            return False



    def delete_process_activity(self, activity_id: int) -> bool:
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute('DELETE FROM process_activity_entries WHERE activity_id = %s', (activity_id,))
            cursor.execute('DELETE FROM process_activities WHERE id = %s', (activity_id,))
            conn.commit()
            conn.close()
            return cursor.rowcount > 0
        except Exception as exc:
            print(f"Error deleting process activity: {exc}")
            return False



    def list_process_activity_entries(self, activity_id: int) -> List[Dict[str, Any]]:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            '''
            SELECT * FROM process_activity_entries
            WHERE activity_id = %s
            ORDER BY order_index, id
            ''',
            (activity_id,)
        )
        rows = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return rows



    def create_process_activity_entry(self, activity_id: int, entry: Dict[str, Any]) -> Optional[int]:
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            order_index = entry.get('order_index')
            if not order_index or order_index <= 0:
                cursor.execute(
                    'SELECT MAX(order_index) as max_order FROM process_activity_entries WHERE activity_id = %s',
                    (activity_id,)
                )
                row = cursor.fetchone()
                max_order = row['max_order'] if row and row['max_order'] else 0
                order_index = max_order + 1

            cursor.execute(
                '''
                INSERT INTO process_activity_entries (activity_id, order_index, text_content, image_path, image_width, layout)
                VALUES (%s, %s, %s, %s, %s, %s)
                ''',
                (
                    activity_id,
                    order_index,
                    entry.get('text_content'),
                    entry.get('image_path'),
                    entry.get('image_width') or 280,
                    entry.get('layout', 'dual')
                )
            )
            new_id = cursor.lastrowid
            conn.commit()
            conn.close()
            return new_id
        except Exception as exc:
            print(f"Error creating process activity entry: {exc}")
            return None



    def get_process_activity_entry(self, entry_id: int) -> Optional[Dict[str, Any]]:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM process_activity_entries WHERE id = %s', (entry_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None
    


    def update_process_activity_entry(self, entry_id: int, entry: Dict[str, Any]) -> bool:
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(
                '''
                UPDATE process_activity_entries
                SET text_content = %s, image_path = %s, order_index = %s, image_width = %s, layout = %s, updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
                ''',
                (
                    entry.get('text_content'),
                    entry.get('image_path'),
                    entry.get('order_index') or 0,
                    entry.get('image_width') or 280,
                    entry.get('layout', 'dual'),
                    entry_id
                )
            )
            conn.commit()
            conn.close()
            return cursor.rowcount > 0
        except Exception as exc:
            print(f"Error updating process activity entry: {exc}")
            return False



    def delete_process_activity_entry(self, entry_id: int) -> bool:
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute('DELETE FROM process_activity_entries WHERE id = %s', (entry_id,))
            conn.commit()
            conn.close()
            return cursor.rowcount > 0
        except Exception as exc:
            print(f"Error deleting process activity entry: {exc}")
            return False



    def list_roles(self, company_id: int) -> List[Dict[str, Any]]:
        conn = self._get_connection()
        cursor = conn.cursor()
        self._ensure_roles_columns(cursor)
        cursor.execute('SELECT * FROM roles WHERE company_id = %s ORDER BY title', (company_id,))
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return rows



    def create_role(self, company_id: int, role: Dict[str, Any]) -> Optional[int]:
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            self._ensure_roles_columns(cursor)
            # Coerce parent_role_id
            parent_id = role.get('parent_role_id')
            if parent_id in ("", None):
                parent_id = None
            else:
                try:
                    parent_id = int(parent_id)
                except Exception:
                    parent_id = None
            cursor.execute('''
                INSERT INTO roles (company_id, title, parent_role_id, department, color, headcount_planned, weekly_hours, notes)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ''', (
                company_id,
                role.get('title'),
                parent_id,
                role.get('department'),
                role.get('color'),
                int(role.get('headcount_planned') or 0),
                int(role.get('weekly_hours') or 0),
                role.get('notes')
            ))
            new_id = cursor.lastrowid
            conn.commit()
            conn.close()
            return new_id
        except Exception as exc:
            print(f"Error creating role: {exc}")
            return None



    def update_role(self, role_id: int, role: Dict[str, Any]) -> bool:
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            self._ensure_roles_columns(cursor)
            parent_id = role.get('parent_role_id')
            if parent_id in ("", None):
                parent_id = None
            else:
                try:
                    parent_id = int(parent_id)
                except Exception:
                    parent_id = None
            cursor.execute('''
                UPDATE roles SET
                    title = %s, parent_role_id = %s, department = %s, color = %s, headcount_planned = %s, weekly_hours = %s, notes = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
            ''', (
                role.get('title'),
                parent_id,
                role.get('department'),
                role.get('color'),
                int(role.get('headcount_planned') or 0),
                int(role.get('weekly_hours') or 0),
                role.get('notes'),
                role_id
            ))
            conn.commit()
            conn.close()
            return True
        except Exception as exc:
            print(f"Error updating role: {exc}")
            return False



    def delete_role(self, role_id: int) -> bool:
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute('DELETE FROM roles WHERE id = %s', (role_id,))
            conn.commit()
            conn.close()
            return True
        except Exception as exc:
            print(f"Error deleting role: {exc}")
            return False



    def get_roles_tree(self, company_id: int) -> List[Dict[str, Any]]:
        """Return roles in hierarchical tree form"""
        # list_roles ensures columns exist
        roles = self.list_roles(company_id)
        role_by_id = {r['id']: {**r, 'children': []} for r in roles}
        roots: List[Dict[str, Any]] = []
        for r in role_by_id.values():
            parent_id = r.get('parent_role_id')
            if parent_id and parent_id in role_by_id:
                role_by_id[parent_id]['children'].append(r)
            else:
                roots.append(r)
        return roots

    # Employees CRUD


    def get_routines(self, company_id: int) -> List[Dict[str, Any]]:
        """Get all routines for a company"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM routines 
            WHERE company_id = %s AND is_active = 1
            ORDER BY name
        ''', (company_id,))
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]



    def create_routine(self, company_id: int, name: str, description: str = '') -> Optional[int]:
        """Create a new routine"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO routines (company_id, name, description)
                VALUES (%s, %s, %s)
            ''', (company_id, name, description))
            new_id = cursor.lastrowid
            conn.commit()
            conn.close()
            return new_id
        except Exception as e:
            print(f"Error creating routine: {e}")
            return None



    def get_routine(self, routine_id: int) -> Optional[Dict[str, Any]]:
        """Get a specific routine by ID"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM routines WHERE id = %s', (routine_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None



    def update_routine(self, routine_id: int, name: str, description: str) -> bool:
        """Update a routine"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE routines 
                SET name = %s, description = %s, updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
            ''', (name, description, routine_id))
            conn.commit()
            conn.close()
            return cursor.rowcount > 0
        except Exception as e:
            print(f"Error updating routine: {e}")
            return False



    def delete_routine(self, routine_id: int) -> bool:
        """Soft delete a routine"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute('UPDATE routines SET is_active = 0 WHERE id = %s', (routine_id,))
            conn.commit()
            conn.close()
            return cursor.rowcount > 0
        except Exception as e:
            print(f"Error deleting routine: {e}")
            return False

    # ===== ROUTINE TRIGGERS - CRUD =====



    def get_routine_triggers(self, routine_id: int) -> List[Dict[str, Any]]:
        """Get all triggers for a routine"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM routine_triggers 
            WHERE routine_id = %s AND is_active = 1
            ORDER BY trigger_type, trigger_value
        ''', (routine_id,))
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]



    def create_routine_trigger(self, routine_id: int, trigger_type: str, trigger_value: str, 
                              deadline_value: int, deadline_unit: str) -> Optional[int]:
        """Create a new trigger for a routine"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO routine_triggers 
                (routine_id, trigger_type, trigger_value, deadline_value, deadline_unit)
                VALUES (%s, %s, %s, %s, %s)
            ''', (routine_id, trigger_type, trigger_value, deadline_value, deadline_unit))
            new_id = cursor.lastrowid
            conn.commit()
            conn.close()
            return new_id
        except Exception as e:
            print(f"Error creating routine trigger: {e}")
            return None



    def update_routine_trigger(self, trigger_id: int, trigger_type: str, trigger_value: str,
                              deadline_value: int, deadline_unit: str) -> bool:
        """Update a routine trigger"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE routine_triggers 
                SET trigger_type = %s, trigger_value = %s, deadline_value = %s, 
                    deadline_unit = %s, updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
            ''', (trigger_type, trigger_value, deadline_value, deadline_unit, trigger_id))
            conn.commit()
            conn.close()
            return cursor.rowcount > 0
        except Exception as e:
            print(f"Error updating routine trigger: {e}")
            return False



    def delete_routine_trigger(self, trigger_id: int) -> bool:
        """Soft delete a routine trigger"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute('UPDATE routine_triggers SET is_active = 0 WHERE id = %s', (trigger_id,))
            conn.commit()
            conn.close()
            return cursor.rowcount > 0
        except Exception as e:
            print(f"Error deleting routine trigger: {e}")
            return False

    # ===== ROUTINE TASKS - CRUD =====



    def get_routine_tasks(self, company_id: int, status: str = None) -> List[Dict[str, Any]]:
        """Get routine tasks for a company, optionally filtered by status"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        if status:
            cursor.execute('''
                SELECT rt.* FROM routine_tasks rt
                JOIN routines r ON r.id = rt.routine_id
                WHERE r.company_id = %s AND rt.status = %s
                ORDER BY rt.deadline_date ASC
            ''', (company_id, status))
        else:
            cursor.execute('''
                SELECT rt.* FROM routine_tasks rt
                JOIN routines r ON r.id = rt.routine_id
                WHERE r.company_id = %s
                ORDER BY rt.deadline_date ASC
            ''', (company_id,))
        
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]



    def create_routine_task(self, routine_id: int, trigger_id: int, title: str, description: str,
                           scheduled_date: str, deadline_date: str) -> Optional[int]:
        """Create a new routine task"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO routine_tasks 
                (routine_id, trigger_id, title, description, scheduled_date, deadline_date)
                VALUES (%s, %s, %s, %s, %s, %s)
            ''', (routine_id, trigger_id, title, description, scheduled_date, deadline_date))
            new_id = cursor.lastrowid
            conn.commit()
            conn.close()
            return new_id
        except Exception as e:
            print(f"Error creating routine task: {e}")
            return None



    def update_routine_task_status(self, task_id: int, status: str, completed_by: str = None, notes: str = None) -> bool:
        """Update the status of a routine task"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            if status == 'completed':
                cursor.execute('''
                    UPDATE routine_tasks 
                    SET status = %s, completed_at = CURRENT_TIMESTAMP, completed_by = %s, 
                        notes = %s, updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                ''', (status, completed_by, notes, task_id))
            else:
                cursor.execute('''
                    UPDATE routine_tasks 
                    SET status = %s, notes = %s, updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                ''', (status, notes, task_id))
            
            conn.commit()
            conn.close()
            return cursor.rowcount > 0
        except Exception as e:
            print(f"Error updating routine task status: {e}")
            return False



    def get_upcoming_tasks(self, company_id: int, days: int = 7) -> List[Dict[str, Any]]:
        """Get upcoming tasks for the next N days"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT rt.* FROM routine_tasks rt
            JOIN routines r ON r.id = rt.routine_id
            WHERE r.company_id = %s 
            AND rt.status IN ('pending', 'in_progress')
            AND rt.deadline_date >= CURRENT_TIMESTAMP
            AND rt.deadline_date <= datetime(CURRENT_TIMESTAMP, '+' || %s || ' days')
            ORDER BY rt.deadline_date ASC
        ''', (company_id, days))
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

# AI Agents Management Functions
def get_ai_agents():
    """Get all AI agents"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, name, description, version, status, page, section, 
                   button_text, required_data, optional_data, prompt_template,
                   format_type, output_field, response_template, timeout,
                   max_retries, execution_mode, cache_enabled, created_at, updated_at
            FROM ai_agents
            ORDER BY created_at DESC
        """)
        
        results = cursor.fetchall()
        conn.close()
        
        agents = []
        for result in results:
            try:
                required_data = json.loads(result[8]) if result[8] else []
                optional_data = json.loads(result[9]) if result[9] else []
            except (json.JSONDecodeError, TypeError):
                required_data = []
                optional_data = []
            
            agents.append({
                'id': result[0],
                'name': result[1],
                'description': result[2],
                'version': result[3],
                'status': result[4],
                'activation': {
                    'page': result[5],
                    'page_label': get_page_label(result[5]),
                    'section': result[6],
                    'section_label': get_section_label(result[6]),
                    'button_text': result[7]
                },
                'input_data': {
                    'required': required_data,
                    'optional': optional_data
                },
                'prompt_template': result[10],
                'response_format': {
                    'type': result[11],
                    'output_field': result[12],
                    'template': result[13]
                },
                'advanced_settings': {
                    'timeout': result[14],
                    'max_retries': result[15],
                    'execution_mode': result[16],
                    'cache_enabled': bool(result[17])
                },
                'created_at': result[18],
                'updated_at': result[19]
            })
        
        return agents
        
    except Exception as e:
        print(f"Erro ao buscar agentes de IA: {e}")
        return []

def get_ai_agent(agent_id):
    """Get specific AI agent"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, name, description, version, status, page, section, 
                   button_text, required_data, optional_data, prompt_template,
                   format_type, output_field, response_template, timeout,
                   max_retries, execution_mode, cache_enabled, created_at, updated_at
            FROM ai_agents
            WHERE id = %s
        """, (agent_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            try:
                required_data = json.loads(result[8]) if result[8] else []
                optional_data = json.loads(result[9]) if result[9] else []
            except (json.JSONDecodeError, TypeError):
                required_data = []
                optional_data = []
            
            return {
                'id': result[0],
                'name': result[1],
                'description': result[2],
                'version': result[3],
                'status': result[4],
                'activation': {
                    'page': result[5],
                    'page_label': get_page_label(result[5]),
                    'section': result[6],
                    'section_label': get_section_label(result[6]),
                    'button_text': result[7]
                },
                'input_data': {
                    'required': required_data,
                    'optional': optional_data
                },
                'prompt_template': result[10],
                'response_format': {
                    'type': result[11],
                    'output_field': result[12],
                    'template': result[13]
                },
                'advanced_settings': {
                    'timeout': result[14],
                    'max_retries': result[15],
                    'execution_mode': result[16],
                    'cache_enabled': bool(result[17])
                },
                'created_at': result[18],
                'updated_at': result[19]
            }
        
        return None
        
    except Exception as e:
        print(f"Erro ao buscar agente de IA: {e}")
        return None

def create_ai_agent(agent_config):
    """Create new AI agent"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Check if agent already exists
        cursor.execute("SELECT id FROM ai_agents WHERE id = %s", (agent_config['id'],))
        if cursor.fetchone():
            conn.close()
            return False
        
        cursor.execute("""
            INSERT INTO ai_agents (
                id, name, description, version, status, page, section, button_text,
                required_data, optional_data, prompt_template, format_type,
                output_field, response_template, timeout, max_retries,
                execution_mode, cache_enabled, created_at, updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            agent_config['id'],
            agent_config['name'],
            agent_config['description'],
            agent_config['version'],
            agent_config['status'],
            agent_config['activation']['page'],
            agent_config['activation']['section'],
            agent_config['activation']['button_text'],
            json.dumps(agent_config['input_data']['required']),
            json.dumps(agent_config['input_data']['optional']),
            agent_config['prompt_template'],
            agent_config['response_format']['type'],
            agent_config['response_format']['output_field'],
            agent_config['response_format']['template'],
            agent_config['advanced_settings']['timeout'],
            agent_config['advanced_settings']['max_retries'],
            agent_config['advanced_settings']['execution_mode'],
            agent_config['advanced_settings']['cache_enabled'],
            datetime.now().isoformat(),
            datetime.now().isoformat()
        ))
        
        conn.commit()
        conn.close()
        return True
        
    except Exception as e:
        print(f"Erro ao criar agente de IA: {e}")
        return False

def update_ai_agent(agent_id, agent_config):
    """Update AI agent"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE ai_agents SET
                name = %s, description = %s, version = %s, status = %s, page = %s,
                section = %s, button_text = %s, required_data = %s, optional_data = %s,
                prompt_template = %s, format_type = %s, output_field = %s,
                response_template = %s, timeout = %s, max_retries = %s,
                execution_mode = %s, cache_enabled = %s, updated_at = %s
            WHERE id = %s
        """, (
            agent_config['name'],
            agent_config['description'],
            agent_config['version'],
            agent_config['status'],
            agent_config['activation']['page'],
            agent_config['activation']['section'],
            agent_config['activation']['button_text'],
            json.dumps(agent_config['input_data']['required']),
            json.dumps(agent_config['input_data']['optional']),
            agent_config['prompt_template'],
            agent_config['response_format']['type'],
            agent_config['response_format']['output_field'],
            agent_config['response_format']['template'],
            agent_config['advanced_settings']['timeout'],
            agent_config['advanced_settings']['max_retries'],
            agent_config['advanced_settings']['execution_mode'],
            agent_config['advanced_settings']['cache_enabled'],
            datetime.now().isoformat(),
            agent_id
        ))
        
        conn.commit()
        conn.close()
        return True
        
    except Exception as e:
        print(f"Erro ao atualizar agente de IA: {e}")
        return False

def delete_ai_agent(agent_id):
    """Delete AI agent"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        # remove links first if table exists
        try:
            cursor.execute("DELETE FROM agent_integrations WHERE agent_id = %s", (agent_id,))
        except Exception:
            pass
        cursor.execute("DELETE FROM ai_agents WHERE id = %s", (agent_id,))
        
        conn.commit()
        conn.close()
        return True
        
    except Exception as e:
        print(f"Erro ao excluir agente de IA: {e}")
        return False

def get_page_label(page):
    """Get human-readable page label"""
    labels = {
        'company': 'Dados da Organização',
        'participants': 'Participantes',
        'drivers': 'Direcionadores',
        'okr-global': 'OKRs Globais',
        'okr-area': 'OKRs de Área',
        'projects': 'Projetos',
        'reports': 'Relatórios'
    }
    return labels.get(page, page)

def get_section_label(section):
    """Get human-readable section label"""
    labels = {
        'analyses': 'Análises',
        'summary': 'Resumo Executivo',
        'interviews': 'Entrevistas',
        'vision': 'Visão',
        'market': 'Mercado',
        'company': 'Empresa'
    }
    return labels.get(section, section)

# Integrations CRUD helpers
def get_connection():
    """Get database connection"""
    from database.postgres_helper import connect as pg_connect
    return pg_connect()

def ensure_integrations_tables():
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS integrations (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                provider TEXT NOT NULL,
                type TEXT NOT NULL,
                auth_type TEXT NOT NULL,
                config TEXT,
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now'))
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS agent_integrations (
                agent_id TEXT NOT NULL,
                integration_id TEXT NOT NULL,
                PRIMARY KEY (agent_id, integration_id),
                FOREIGN KEY (agent_id) REFERENCES ai_agents(id) ON DELETE CASCADE,
                FOREIGN KEY (integration_id) REFERENCES integrations(id) ON DELETE CASCADE
            )
        """)
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error ensuring integrations tables: {e}")
        return False

def list_integrations():
    try:
        ensure_integrations_tables()
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, provider, type, auth_type, config, created_at, updated_at FROM integrations ORDER BY name")
        rows = cursor.fetchall()
        conn.close()
        import json as _json
        items = []
        for r in rows:
            try:
                cfg = _json.loads(r[5]) if r[5] else {}
            except Exception:
                cfg = {}
            items.append({
                'id': r[0], 'name': r[1], 'provider': r[2], 'type': r[3], 'auth_type': r[4],
                'config': cfg, 'created_at': r[6], 'updated_at': r[7]
            })
        return items
    except Exception as e:
        print(f"Error listing integrations: {e}")
        return []

def get_integration(integration_id):
    try:
        ensure_integrations_tables()
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, provider, type, auth_type, config, created_at, updated_at FROM integrations WHERE id = %s", (integration_id,))
        r = cursor.fetchone()
        conn.close()
        if not r:
            return None
        import json as _json
        try:
            cfg = _json.loads(r[5]) if r[5] else {}
        except Exception:
            cfg = {}
        return {
            'id': r[0], 'name': r[1], 'provider': r[2], 'type': r[3], 'auth_type': r[4],
            'config': cfg, 'created_at': r[6], 'updated_at': r[7]
        }
    except Exception as e:
        print(f"Error getting integration: {e}")
        return None

def create_integration(item):
    try:
        ensure_integrations_tables()
        conn = get_connection()
        cursor = conn.cursor()
        import json as _json
        cursor.execute("""
            INSERT INTO integrations (id, name, provider, type, auth_type, config, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, datetime('now'), datetime('now'))
        """, (
            item['id'], item['name'], item['provider'], item['type'], item['auth_type'], _json.dumps(item.get('config') or {})
        ))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error creating integration: {e}")
        return False

def update_integration(integration_id, item):
    try:
        ensure_integrations_tables()
        conn = get_connection()
        cursor = conn.cursor()
        import json as _json
        cursor.execute("""
            UPDATE integrations SET name = %s, provider = %s, type = %s, auth_type = %s, config = %s, updated_at = datetime('now')
            WHERE id = %s
        """, (
            item['name'], item['provider'], item['type'], item['auth_type'], _json.dumps(item.get('config') or {}), integration_id
        ))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error updating integration: {e}")
        return False

def delete_integration(integration_id):
    try:
        ensure_integrations_tables()
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM agent_integrations WHERE integration_id = %s", (integration_id,))
        cursor.execute("DELETE FROM integrations WHERE id = %s", (integration_id,))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error deleting integration: {e}")
        return False

def set_agent_integrations(agent_id, integration_ids):
    try:
        ensure_integrations_tables()
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM agent_integrations WHERE agent_id = %s", (agent_id,))
        for iid in (integration_ids or []):
            cursor.execute("INSERT OR IGNORE INTO agent_integrations (agent_id, integration_id) VALUES (%s, %s)", (agent_id, iid))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error setting agent integrations: {e}")
        return False

def get_agent_integrations(agent_id):
    try:
        ensure_integrations_tables()
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT i.id, i.name, i.provider, i.type, i.auth_type
            FROM agent_integrations ai JOIN integrations i ON i.id = ai.integration_id
            WHERE ai.agent_id = %s
        """, (agent_id,))
        rows = cursor.fetchall()
        conn.close()
        return [ {'id': r[0], 'name': r[1], 'provider': r[2], 'type': r[3], 'auth_type': r[4]} for r in rows ]
    except Exception as e:
        print(f"Error getting agent integrations: {e}")
        return []

    # ===== ROTINAS - CRUD =====



    def get_overdue_tasks(self, company_id: int) -> List[Dict[str, Any]]:
        """Get all overdue tasks for a company"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT rt.* FROM routine_tasks rt
            JOIN routines r ON r.id = rt.routine_id
            WHERE r.company_id = %s 
            AND rt.status IN ('pending', 'in_progress')
            AND rt.deadline_date < CURRENT_TIMESTAMP
            ORDER BY rt.deadline_date ASC
        ''', (company_id,))
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]



    def get_company_profile(self, company_id: int) -> Optional[Dict[str, Any]]:
        """Get full company profile including configs"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM companies WHERE id = %s', (company_id,))
        row = cursor.fetchone()
        conn.close()
        if not row:
            return None
        data = dict(row)
        # Parse JSON configs if present
        try:
            data['pev_config'] = json.loads(data.get('pev_config') or '{}')
        except Exception:
            data['pev_config'] = {}
        try:
            data['grv_config'] = json.loads(data.get('grv_config') or '{}')
        except Exception:
            data['grv_config'] = {}
        return data



    def update_company_profile(self, company_id: int, profile: Dict[str, Any]) -> bool:
        """Update company profile fields including configs"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE companies SET
                    name = %s, legal_name = %s, industry = %s, size = %s, description = %s,
                    client_code = %s,
                    mvv_mission = %s, mvv_vision = %s, mvv_values = %s,
                    pev_config = %s, grv_config = %s
                WHERE id = %s
            ''', (
                profile.get('name'),
                profile.get('legal_name'),
                profile.get('industry'),
                profile.get('size'),
                profile.get('description'),
                self._normalize_client_code(profile.get('client_code')),
                profile.get('mvv_mission'),
                profile.get('mvv_vision'),
                profile.get('mvv_values'),
                json.dumps(profile.get('pev_config') or {}),
                json.dumps(profile.get('grv_config') or {}),
                company_id
            ))
            conn.commit()
            conn.close()
            return True
        except Exception as exc:
            print(f"Error updating company profile: {exc}")
            return False
    
    # Plan operations


    def update_company_mvv(self, company_id: int, mission: str, vision: str, values: str) -> bool:
        """Update company-level MVV fields"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE companies SET
                    mvv_mission = %s, mvv_vision = %s, mvv_values = %s
                WHERE id = %s
            ''', (mission, vision, values, company_id))
            conn.commit()
            conn.close()
            return True
        except Exception as exc:
            print(f"Error updating company MVV: {exc}")
            return False



    def update_company_analyses(self, plan_id: int, data: Dict[str, Any]) -> bool:
        """Update only analysis fields in company data"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Check if company data exists
            cursor.execute('SELECT id FROM company_data WHERE plan_id = %s', (plan_id,))
            existing = cursor.fetchone()
            
            if existing:
                # Update only analysis fields
                cursor.execute('''
                    UPDATE company_data SET
                        ai_insights = %s, consultant_analysis = %s, updated_at = CURRENT_TIMESTAMP
                    WHERE plan_id = %s
                ''', (
                    data.get('ai_insights'),
                    data.get('consultant_analysis'),
                    plan_id
                ))
            else:
                # Insert new record with only analysis fields
                cursor.execute('''
                    INSERT INTO company_data (plan_id, ai_insights, consultant_analysis)
                    VALUES (%s, %s, %s)
                ''', (
                    plan_id,
                    data.get('ai_insights'),
                    data.get('consultant_analysis')
                ))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error updating company analyses: {e}")
            return False




    def delete_meeting(self, meeting_id: int) -> bool:
        """Delete a meeting"""
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            self._ensure_meetings_schema(cursor)
            cursor.execute('DELETE FROM meetings WHERE id = %s', (meeting_id,))
            conn.commit()
            return cursor.rowcount > 0
        except Exception as exc:
            print(f"Error deleting meeting: {exc}")
            if conn:
                try:
                    conn.rollback()
                except Exception:
                    pass
            return False
        finally:
            if conn:
                conn.close()
    
    # Company creation

