"""
SQLite database implementation
⚠️ DESATIVADO - Sistema migrado para PostgreSQL
Este módulo está mantido apenas como referência histórica
"""

import sqlite3
import json
from datetime import datetime, date
from typing import List, Dict, Any, Optional, Tuple
from .base import DatabaseInterface

class SQLiteDatabase(DatabaseInterface):
    """
    ⚠️ CLASSE DESATIVADA ⚠️
    
    O sistema foi migrado para PostgreSQL.
    Se você está vendo este erro, significa que alguma parte do código
    ainda está tentando usar SQLite.
    
    AÇÃO NECESSÁRIA:
    - Verifique o traceback para identificar onde SQLite está sendo chamado
    - Atualize o código para usar PostgreSQL
    - Configure DB_TYPE=postgresql no arquivo .env
    """
    
    def __init__(self, *args, **kwargs):
        """
        ⚠️ SQLite DESATIVADO ⚠️
        
        O APP30 foi migrado para PostgreSQL.
        Não é mais permitido usar SQLite.
        
        Para corrigir este erro:
        1. Verifique o arquivo .env: DB_TYPE=postgresql
        2. Verifique a variável DATABASE_URL aponta para PostgreSQL
        3. Identifique no traceback onde SQLite está sendo instanciado
        4. Atualize o código para usar config_database.get_db()
        """
        raise RuntimeError(
            "❌ ERRO: SQLite está DESATIVADO!\n\n"
            "O sistema APP30 foi completamente migrado para PostgreSQL.\n\n"
            "SQLite não deve mais ser usado. Se você está vendo este erro,\n"
            "significa que alguma parte do código ainda está tentando\n"
            "instanciar uma conexão SQLite.\n\n"
            "VERIFIQUE:\n"
            "  1. Arquivo .env tem DB_TYPE=postgresql\n"
            "  2. DATABASE_URL aponta para postgresql://...\n"
            "  3. Não há import de sqlite3 sendo usado\n"
            "  4. Use config_database.get_db() para obter conexão\n\n"
            "TRACEBACK acima mostra ONDE o erro aconteceu.\n"
            "Corrija aquele ponto do código para usar PostgreSQL.\n"
        )


    def _raise_implantation_disabled(self):
        raise RuntimeError("Funcionalidades de implantacao estao disponiveis apenas no backend PostgreSQL.")

    def get_implantation_dashboard(self, plan_id: int):
        self._raise_implantation_disabled()

    def list_implantation_phases(self, plan_id: int):
        self._raise_implantation_disabled()

    def list_implantation_checkpoints(self, plan_id: int):
        self._raise_implantation_disabled()

    def list_alignment_members(self, plan_id: int):
        self._raise_implantation_disabled()

    def get_alignment_overview(self, plan_id: int):
        self._raise_implantation_disabled()

    def list_alignment_principles(self, plan_id: int):
        self._raise_implantation_disabled()

    def list_alignment_agenda(self, plan_id: int):
        self._raise_implantation_disabled()

    def get_alignment_project(self, plan_id: int):
        self._raise_implantation_disabled()

    def list_plan_segments(self, plan_id: int):
        self._raise_implantation_disabled()

    def create_plan_segment(self, plan_id: int, data: Dict[str, Any]) -> int:
        self._raise_implantation_disabled()

    def update_plan_segment(self, segment_id: int, plan_id: int, data: Dict[str, Any]) -> bool:
        self._raise_implantation_disabled()

    def delete_plan_segment(self, segment_id: int, plan_id: int) -> bool:
        self._raise_implantation_disabled()

    def list_plan_structures(self, plan_id: int):
        self._raise_implantation_disabled()

    def list_plan_structure_installments(self, plan_id: int):
        self._raise_implantation_disabled()

    def create_plan_structure(self, plan_id: int, data: Dict[str, Any]) -> int:
        self._raise_implantation_disabled()

    def update_plan_structure(self, structure_id: int, plan_id: int, data: Dict[str, Any]) -> bool:
        self._raise_implantation_disabled()

    def delete_plan_structure(self, structure_id: int, plan_id: int) -> bool:
        self._raise_implantation_disabled()

    def create_plan_structure_installment(self, structure_id: int, data: Dict[str, Any]) -> int:
        self._raise_implantation_disabled()

    def delete_plan_structure_installments(self, structure_id: int) -> bool:
        self._raise_implantation_disabled()

    def list_plan_structure_capacities(self, plan_id: int):
        self._raise_implantation_disabled()

    def create_plan_structure_capacity(self, plan_id: int, data):
        self._raise_implantation_disabled()

    def update_plan_structure_capacity(self, capacity_id: int, plan_id: int, data):
        self._raise_implantation_disabled()

    def delete_plan_structure_capacity(self, capacity_id: int, plan_id: int):
        self._raise_implantation_disabled()

    def list_plan_finance_premises(self, plan_id: int):
        self._raise_implantation_disabled()

    def list_plan_finance_investments(self, plan_id: int):
        self._raise_implantation_disabled()

    def list_plan_finance_sources(self, plan_id: int):
        self._raise_implantation_disabled()

    def list_plan_finance_business_periods(self, plan_id: int):
        self._raise_implantation_disabled()

    def list_plan_finance_business_distribution(self, plan_id: int):
        self._raise_implantation_disabled()

    def list_plan_finance_variable_costs(self, plan_id: int):
        self._raise_implantation_disabled()

    def list_plan_finance_result_rules(self, plan_id: int):
        self._raise_implantation_disabled()

    def list_plan_finance_investor_periods(self, plan_id: int):
        self._raise_implantation_disabled()

    def get_plan_finance_metrics(self, plan_id: int):
        self._raise_implantation_disabled()

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
        cursor.execute('SELECT code FROM processes WHERE id = ?', (process_id,))
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
        """
        Mapeia o estágio do Kanban para o nível de estruturação.
        - Caixa de Entrada / Fora de Escopo → '' (Fora de Escopo)
        - Modelando / Implantando / Estabilizando → 'in_progress'
        - Estável → 'stabilized'
        """
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
        cursor.execute('SELECT client_code FROM companies WHERE id = ?', (company_id,))
        row = cursor.fetchone()
        # Converter para dict se for sqlite3.Row
        if row:
            row_dict = dict(row) if hasattr(row, 'keys') else {'client_code': row[0]}
            prefix = self._sanitize_company_code(row_dict.get('client_code'), company_id)
        else:
            prefix = self._sanitize_company_code(None, company_id)

        cursor.execute(
            'SELECT COALESCE(MAX(code_sequence), 0) AS max_seq FROM company_projects WHERE company_id = ?',
            (company_id,)
        )
        result = cursor.fetchone()
        # Converter para dict se for sqlite3.Row
        if result:
            result_dict = dict(result) if hasattr(result, 'keys') else {'max_seq': result[0]}
            next_sequence = (result_dict.get('max_seq') or 0) + 1
        else:
            next_sequence = 1
        code = f"{prefix}.J.{next_sequence}"
        return code, next_sequence

    def _ensure_meetings_schema(self, cursor):
        """Create meetings table (and adjustments) when missing."""
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS meetings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL,
                project_id INTEGER,
                title TEXT NOT NULL,
                scheduled_date DATE,
                scheduled_time TEXT,
                actual_date DATE,
                actual_time TEXT,
                status TEXT DEFAULT 'draft',
                invite_notes TEXT,
                meeting_notes TEXT,
                guests_json TEXT,
                agenda_json TEXT,
                participants_json TEXT,
                discussions_json TEXT,
                activities_json TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (company_id) REFERENCES companies (id),
                FOREIGN KEY (project_id) REFERENCES company_projects (id)
            )
        ''')
        cursor.execute('PRAGMA table_info(meetings)')
        meeting_columns = {row[1] for row in cursor.fetchall()}
        required_columns = {
            'actual_date': "ALTER TABLE meetings ADD COLUMN actual_date DATE",
            'actual_time': "ALTER TABLE meetings ADD COLUMN actual_time TEXT",
            'status': "ALTER TABLE meetings ADD COLUMN status TEXT DEFAULT 'draft'",
            'invite_notes': "ALTER TABLE meetings ADD COLUMN invite_notes TEXT",
            'meeting_notes': "ALTER TABLE meetings ADD COLUMN meeting_notes TEXT",
            'guests_json': "ALTER TABLE meetings ADD COLUMN guests_json TEXT",
            'agenda_json': "ALTER TABLE meetings ADD COLUMN agenda_json TEXT",
            'participants_json': "ALTER TABLE meetings ADD COLUMN participants_json TEXT",
            'discussions_json': "ALTER TABLE meetings ADD COLUMN discussions_json TEXT",
            'activities_json': "ALTER TABLE meetings ADD COLUMN activities_json TEXT",
        }
        for column, statement in required_columns.items():
            if column not in meeting_columns:
                cursor.execute(statement)
        
        # Criar tabela de itens de pauta reutilizáveis
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS meeting_agenda_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                usage_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (company_id) REFERENCES companies (id)
            )
        ''')

        cursor.execute('''
            CREATE TRIGGER IF NOT EXISTS trg_meetings_updated_at
            AFTER UPDATE ON meetings
            FOR EACH ROW
            BEGIN
                UPDATE meetings
                SET updated_at = CURRENT_TIMESTAMP
                WHERE id = NEW.id;
            END;
        ''')

    @staticmethod
    def _decode_json_column(value: Optional[str], default):
        if not value:
            return default
        try:
            return json.loads(value)
        except Exception:
            return default

    @staticmethod
    def _encode_json_value(value):
        if value is None:
            return None
        if isinstance(value, str):
            cleaned = value.strip()
            return cleaned if cleaned else None
        try:
            return json.dumps(value, ensure_ascii=False)
        except Exception:
            return None

    def _serialize_meeting_row(self, row: sqlite3.Row) -> Dict[str, Any]:
        """Convert raw database row to structured meeting payload."""
        # Converter sqlite3.Row para dict para poder usar .get()
        row_dict = dict(row)
        return {
            'id': row_dict['id'],
            'company_id': row_dict['company_id'],
            'project_id': row_dict['project_id'],
            'project_title': row_dict.get('project_title'),
            'project_code': row_dict.get('project_code'),
            'title': row_dict['title'],
            'scheduled_date': row_dict['scheduled_date'],
            'scheduled_time': row_dict['scheduled_time'],
            'actual_date': row_dict.get('actual_date'),
            'actual_time': row_dict.get('actual_time'),
            'status': row_dict.get('status', 'draft'),
            'invite_notes': row_dict.get('invite_notes'),
            'meeting_notes': row_dict.get('meeting_notes'),
            'guests': self._decode_json_column(row_dict.get('guests_json'), {'internal': [], 'external': []}),
            'agenda': self._decode_json_column(row_dict.get('agenda_json'), []),
            'participants': self._decode_json_column(row_dict.get('participants_json'), {'internal': [], 'external': []}),
            'discussions': self._decode_json_column(row_dict.get('discussions_json'), []),
            'activities': self._decode_json_column(row_dict.get('activities_json'), []),
            'created_at': row_dict['created_at'],
            'updated_at': row_dict['updated_at'],
        }
    
    # ⚠️ __init__ ORIGINAL DESATIVADO - Classe bloqueada no topo
    # def __init__(self, db_path: str = 'pevapp22.db'):
    #     self.db_path = db_path
    #     self.init_database()
    #     self.seed_data()
    
    def _get_connection(self):
        """Get database connection"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def init_database(self) -> bool:
        """Initialize database and create tables"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Create tables
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS companies (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    legal_name TEXT,
                    industry TEXT,
                    size TEXT,
                    description TEXT,
                    client_code TEXT,
                    mvv_mission TEXT,
                    mvv_vision TEXT,
                    mvv_values TEXT,
                    pev_config TEXT,
                    grv_config TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Ensure client_code column exists (for existing databases)
            try:
                cursor.execute('PRAGMA table_info(companies)')
                columns = {row[1] for row in cursor.fetchall()}
                if 'client_code' not in columns:
                    cursor.execute('ALTER TABLE companies ADD COLUMN client_code TEXT')
            except Exception:
                pass
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS plans (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    company_id INTEGER,
                    name TEXT NOT NULL,
                    description TEXT,
                    start_date DATE,
                    end_date DATE,
                    year INTEGER,
                    status TEXT DEFAULT 'active',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (company_id) REFERENCES companies (id)
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS participants (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    plan_id INTEGER,
                    employee_id INTEGER,
                    name TEXT NOT NULL,
                    role TEXT,
                    relation TEXT,
                    email TEXT,
                    cpf TEXT,
                    phone TEXT,
                    status TEXT DEFAULT 'active',
                    email_confirmed BOOLEAN DEFAULT FALSE,
                    whatsapp_confirmed BOOLEAN DEFAULT FALSE,
                    message_sent BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP,
                    FOREIGN KEY (plan_id) REFERENCES plans (id),
                    FOREIGN KEY (employee_id) REFERENCES employees (id)
                )
            ''')
            
            # Ensure employee_id column exists (for existing databases)
            try:
                cursor.execute('PRAGMA table_info(participants)')
                columns = {row[1] for row in cursor.fetchall()}
                if 'employee_id' not in columns:
                    cursor.execute('ALTER TABLE participants ADD COLUMN employee_id INTEGER')
            except Exception:
                pass
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS company_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    plan_id INTEGER,
                    trade_name TEXT,
                    legal_name TEXT,
                    cnpj TEXT,
                    coverage_physical TEXT,
                    coverage_online TEXT,
                    experience_total TEXT,
                    experience_segment TEXT,
                    cnaes TEXT,
                    mission TEXT,
                    vision TEXT,
                    company_values TEXT,
                    headcount_strategic INTEGER DEFAULT 0,
                    headcount_tactical INTEGER DEFAULT 0,
                    headcount_operational INTEGER DEFAULT 0,
                    financials TEXT,
                    financial_total_revenue TEXT,
                    financial_total_margin TEXT,
                    other_information TEXT,
                    process_map_file TEXT,
                    org_chart_file TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (plan_id) REFERENCES plans (id)
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS drivers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    plan_id INTEGER,
                    title TEXT NOT NULL,
                    description TEXT,
                    status TEXT DEFAULT 'draft',
                    priority TEXT,
                    owner TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (plan_id) REFERENCES plans (id)
                )
            ''')

            # Roles (Funções) - company-level
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS roles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    company_id INTEGER NOT NULL,
                    title TEXT NOT NULL,
                    parent_role_id INTEGER,
                    reports_to TEXT,
                    department TEXT,
                    color TEXT,
                    headcount_planned INTEGER DEFAULT 0,
                    weekly_hours INTEGER DEFAULT 40,
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (company_id) REFERENCES companies (id),
                    FOREIGN KEY (parent_role_id) REFERENCES roles (id)
                )
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS employees (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    company_id INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    email TEXT,
                    phone TEXT,
                    role_id INTEGER,
                    department TEXT,
                    hire_date TEXT,
                    status TEXT DEFAULT 'active',
                    weekly_hours REAL DEFAULT 40,
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (company_id) REFERENCES companies (id) ON DELETE CASCADE,
                    FOREIGN KEY (role_id) REFERENCES roles (id) ON DELETE SET NULL
                )
            ''')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_employees_company ON employees(company_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_employees_role ON employees(role_id)')
            
            # Process Areas - Áreas de Gestão
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS process_areas (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    company_id INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    code TEXT,
                    description TEXT,
                    order_index INTEGER DEFAULT 0,
                    color TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (company_id) REFERENCES companies (id)
                )
            ''')
            
            # Ensure code column exists in process_areas (for existing databases)
            try:
                cursor.execute('PRAGMA table_info(process_areas)')
                columns = {row[1] for row in cursor.fetchall()}
                if 'code' not in columns:
                    cursor.execute('ALTER TABLE process_areas ADD COLUMN code TEXT')
            except Exception:
                pass
            
            # Macro Processes
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS macro_processes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    company_id INTEGER NOT NULL,
                    area_id INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    code TEXT,
                    owner TEXT,
                    description TEXT,
                    order_index INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (company_id) REFERENCES companies (id),
                    FOREIGN KEY (area_id) REFERENCES process_areas (id)
                )
            ''')
            
            # Processes
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS processes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    company_id INTEGER NOT NULL,
                    macro_id INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    code TEXT,
                    structuring_level TEXT,
                    performance_level TEXT,
                    responsible TEXT,
                    description TEXT,
                    order_index INTEGER DEFAULT 0,
                    kanban_stage TEXT DEFAULT 'inbox',
                    flow_document TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (company_id) REFERENCES companies (id),
                    FOREIGN KEY (macro_id) REFERENCES macro_processes (id)
                )
            ''')

            try:
                cursor.execute('PRAGMA table_info(processes)')
                process_columns = {row[1] for row in cursor.fetchall()}
                if 'kanban_stage' not in process_columns:
                    cursor.execute("ALTER TABLE processes ADD COLUMN kanban_stage TEXT DEFAULT 'inbox'")
                if 'flow_document' not in process_columns:
                    cursor.execute("ALTER TABLE processes ADD COLUMN flow_document TEXT")
                if 'notes' not in process_columns:
                    cursor.execute("ALTER TABLE processes ADD COLUMN notes TEXT")
                
                # Add layout column to process_activity_entries if it doesn't exist
                cursor.execute('PRAGMA table_info(process_activity_entries)')
                entry_columns = {row[1] for row in cursor.fetchall()}
                if 'layout' not in entry_columns:
                    cursor.execute("ALTER TABLE process_activity_entries ADD COLUMN layout TEXT DEFAULT 'dual'")
            except Exception:
                pass

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS process_activities (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    process_id INTEGER NOT NULL,
                    code TEXT NOT NULL,
                    name TEXT NOT NULL,
                    layout TEXT DEFAULT 'single',
                    order_index INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (process_id) REFERENCES processes (id)
                )
            ''')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS process_activity_entries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    activity_id INTEGER NOT NULL,
                    order_index INTEGER DEFAULT 0,
                    text_content TEXT,
                    image_path TEXT,
                    image_width INTEGER DEFAULT 280,
                    layout TEXT DEFAULT 'dual',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (activity_id) REFERENCES process_activities (id)
                )
            ''')
            
            # ===== TABELAS DE ROTINAS =====
            # Tabela principal de rotinas
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS routines (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    company_id INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    description TEXT,
                    is_active INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (company_id) REFERENCES companies (id)
                )
            ''')
            
            # Tabela de gatilhos (triggers) e prazos
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS routine_triggers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    routine_id INTEGER NOT NULL,
                    trigger_type TEXT NOT NULL, -- 'daily', 'weekly', 'monthly', 'yearly'
                    trigger_value TEXT NOT NULL, -- '12:00', 'monday', '01', '01/03'
                    deadline_value INTEGER NOT NULL, -- valor numérico (quantos dias/horas)
                    deadline_unit TEXT NOT NULL, -- 'hours', 'days'
                    is_active INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (routine_id) REFERENCES routines (id) ON DELETE CASCADE
                )
            ''')
            
            # Tabela de tarefas geradas pelas rotinas
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS routine_tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    routine_id INTEGER NOT NULL,
                    trigger_id INTEGER NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT,
                    scheduled_date TIMESTAMP NOT NULL, -- quando foi agendada
                    deadline_date TIMESTAMP NOT NULL, -- prazo limite
                    status TEXT DEFAULT 'pending', -- 'pending', 'in_progress', 'completed', 'overdue'
                    completed_at TIMESTAMP,
                    completed_by TEXT,
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (routine_id) REFERENCES routines (id) ON DELETE CASCADE,
                    FOREIGN KEY (trigger_id) REFERENCES routine_triggers (id)
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS okrs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    plan_id INTEGER,
                    title TEXT NOT NULL,
                    description TEXT,
                    type TEXT, -- 'global' or 'area'
                    area TEXT,
                    status TEXT DEFAULT 'draft',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (plan_id) REFERENCES plans (id)
                )
            ''')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS okr_preliminary_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    plan_id INTEGER NOT NULL,
                    analysis TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (plan_id) REFERENCES plans (id)
                )
            ''')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS okr_area_preliminary_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    plan_id INTEGER NOT NULL,
                    analysis TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (plan_id) REFERENCES plans (id)
                )
            ''')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS okr_global_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    plan_id INTEGER NOT NULL,
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
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (plan_id) REFERENCES plans (id)
                )
            ''')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS okr_global_key_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    okr_id INTEGER NOT NULL,
                    label TEXT NOT NULL,
                    target TEXT,
                    deadline TEXT,
                    owner_id INTEGER,
                    owner TEXT,
                    indicator_id INTEGER,
                    position INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (okr_id) REFERENCES okr_global_records (id) ON DELETE CASCADE
                )
            ''')

            # Ensure legacy databases have the new OKR linking columns
            cursor.execute("PRAGMA table_info('okr_global_records')")
            okr_global_columns = {row[1] for row in cursor.fetchall()}
            if 'owner_id' not in okr_global_columns:
                cursor.execute("ALTER TABLE okr_global_records ADD COLUMN owner_id INTEGER")

            cursor.execute("PRAGMA table_info('okr_global_key_results')")
            okr_global_kr_columns = {row[1] for row in cursor.fetchall()}
            if 'owner_id' not in okr_global_kr_columns:
                cursor.execute("ALTER TABLE okr_global_key_results ADD COLUMN owner_id INTEGER")
            if 'indicator_id' not in okr_global_kr_columns:
                cursor.execute("ALTER TABLE okr_global_key_results ADD COLUMN indicator_id INTEGER")

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS workshop_discussions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    plan_id INTEGER NOT NULL,
                    section_type TEXT NOT NULL,
                    content TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (plan_id) REFERENCES plans (id)
                )
            ''')

            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS projects (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    plan_id INTEGER,
                    title TEXT NOT NULL,
                    description TEXT,
                    status TEXT DEFAULT 'planned',
                    priority TEXT,
                    owner TEXT,
                    start_date DATE,
                    end_date DATE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (plan_id) REFERENCES plans (id)
                )
            ''')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS company_projects (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    company_id INTEGER NOT NULL,
                    plan_id INTEGER,
                    plan_type TEXT,
                    title TEXT NOT NULL,
                    description TEXT,
                    status TEXT DEFAULT 'planned',
                    priority TEXT,
                    owner TEXT,
                    responsible_id INTEGER,
                    start_date DATE,
                    end_date DATE,
                    okr_area_ref TEXT,
                    okr_reference TEXT,
                    indicator_reference TEXT,
                    activities TEXT,
                    notes TEXT,
                    code TEXT,
                    code_sequence INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (company_id) REFERENCES companies (id),
                    FOREIGN KEY (plan_id) REFERENCES plans (id)
                )
            ''')

            try:
                cursor.execute('PRAGMA table_info(company_projects)')
                project_columns = {row[1] for row in cursor.fetchall()}
                if 'plan_type' not in project_columns:
                    cursor.execute('ALTER TABLE company_projects ADD COLUMN plan_type TEXT')
                if 'responsible_id' not in project_columns:
                    cursor.execute('ALTER TABLE company_projects ADD COLUMN responsible_id INTEGER')
                if 'okr_reference' not in project_columns:
                    cursor.execute('ALTER TABLE company_projects ADD COLUMN okr_reference TEXT')
                if 'indicator_reference' not in project_columns:
                    cursor.execute('ALTER TABLE company_projects ADD COLUMN indicator_reference TEXT')
                if 'code' not in project_columns:
                    cursor.execute('ALTER TABLE company_projects ADD COLUMN code TEXT')
                if 'code_sequence' not in project_columns:
                    cursor.execute('ALTER TABLE company_projects ADD COLUMN code_sequence INTEGER')
            except Exception as column_err:
                print(f"Aviso: nao foi possivel ajustar colunas de company_projects: {column_err}")

            try:
                cursor.execute('SELECT DISTINCT company_id FROM company_projects')
                company_rows = cursor.fetchall()
                for company_row in company_rows:
                    company_id = company_row['company_id']
                    cursor.execute('SELECT client_code FROM companies WHERE id = ?', (company_id,))
                    company_code_row = cursor.fetchone()
                    if company_code_row and company_code_row['client_code']:
                        company_code = ''.join(ch for ch in company_code_row['client_code'].strip().upper() if ch.isalnum())
                    else:
                        company_code = str(company_id).zfill(2)

                    cursor.execute('''
                        SELECT id
                        FROM company_projects
                        WHERE company_id = ?
                          AND (code IS NULL OR code = '' OR code_sequence IS NULL)
                        ORDER BY created_at ASC, id ASC
                    ''', (company_id,))
                    pending_projects = cursor.fetchall()
                    if not pending_projects:
                        continue

                    cursor.execute('''
                        SELECT COALESCE(MAX(code_sequence), 0) AS max_seq
                        FROM company_projects
                        WHERE company_id = ?
                          AND code_sequence IS NOT NULL
                    ''', (company_id,))
                    max_seq_row = cursor.fetchone()
                    current_seq = max_seq_row['max_seq'] if max_seq_row and max_seq_row['max_seq'] else 0

                    for project in pending_projects:
                        current_seq += 1
                        project_code = f"{company_code}.J.{current_seq}"
                        cursor.execute(
                            'UPDATE company_projects SET code = ?, code_sequence = ? WHERE id = ?',
                            (project_code, current_seq, project['id'])
                        )
            except Exception as backfill_err:
                print(f"Aviso: falha ao atribuir codigos de projeto existentes: {backfill_err}")

            cursor.execute('''
                CREATE TRIGGER IF NOT EXISTS trg_company_projects_updated_at
                AFTER UPDATE ON company_projects
                FOR EACH ROW
                BEGIN
                    UPDATE company_projects
                    SET updated_at = CURRENT_TIMESTAMP
                    WHERE id = NEW.id;
                END;
            ''')

            # Meetings module schema
            self._ensure_meetings_schema(cursor)

            cursor.execute('''
                INSERT INTO company_projects (
                    id, company_id, plan_id, title, description, status, priority,
                    owner, start_date, end_date, okr_area_ref, activities, notes,
                    created_at, updated_at
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
                    p.start_date,
                    p.end_date,
                    NULL,
                    NULL,
                    NULL,
                    p.created_at,
                    p.updated_at
                FROM projects p
                LEFT JOIN plans pl ON pl.id = p.plan_id
                LEFT JOIN company_projects cp ON cp.id = p.id
                WHERE cp.id IS NULL
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS interviews (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    plan_id INTEGER,
                    participant_name TEXT NOT NULL,
                    consultant_name TEXT NOT NULL,
                    interview_date DATE,
                    format TEXT, -- 'Presencial', 'Online', 'Telefone'
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (plan_id) REFERENCES plans (id)
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS plan_sections (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    plan_id INTEGER,
                    section_name TEXT NOT NULL, -- 'interviews', 'drivers', 'okrs', etc.
                    status TEXT DEFAULT 'open', -- 'open', 'closed'
                    closed_by TEXT, -- Nome do usuário que fechou
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
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    plan_id INTEGER,
                    participants TEXT NOT NULL, -- JSON array de IDs dos participantes
                    consultants TEXT NOT NULL, -- JSON array de nomes dos consultores
                    vision_date DATE,
                    format TEXT, -- 'Presencial', 'Online', 'Telefone'
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (plan_id) REFERENCES plans (id)
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS market_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    plan_id INTEGER,
                    participants TEXT NOT NULL, -- Texto livre dos participantes
                    consultants TEXT NOT NULL, -- Texto livre dos consultores
                    market_date DATE,
                    format TEXT, -- 'Presencial', 'Online', 'Telefone'
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
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
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
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
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
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
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
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
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
                    cache_enabled INTEGER DEFAULT 1,
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
            cursor.executemany('INSERT INTO companies (name) VALUES (?)', companies)
            
            # Get company IDs
            cursor.execute('SELECT id FROM companies ORDER BY id')
            company_ids = [row[0] for row in cursor.fetchall()]
            
            # Insert sample plans
            plans = [
                (company_ids[0], 'Transformacao Digital 2025', 2025),
                (company_ids[1], 'Expansao Mercado 2025', 2025),
                (company_ids[2], 'Reestruturacao 2025', 2025)
            ]
            cursor.executemany('INSERT INTO plans (company_id, name, year) VALUES (?, ?, ?)', plans)
            
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
            cursor.executemany('INSERT INTO participants (plan_id, name, role, email, phone) VALUES (?, ?, ?, ?, ?)', participants)
            
            # Insert sample company data
            company_data = [
                (plan_ids[0], 'Alimentos Tia Sonia', 'Tia Sonia Alimentos Ltda', '12.345.678/0001-90', 'regional', 'internet-nacional', 'Alimentar familias com qualidade', 'Ser referencia em alimentos saudaveis', 'Qualidade, Inovacao, Sustentabilidade', 2, 5, 15),
                (plan_ids[1], 'Tech Solutions', 'Tech Solutions Ltda', '98.765.432/0001-10', 'nacional', 'internet-global', 'Transformar negocios com tecnologia', 'Liderar inovacao tecnologica', 'Inovacao, Excelencia, Colaboracao', 3, 8, 25),
                (plan_ids[2], 'Consultoria ABC', 'ABC Consultoria Ltda', '11.222.333/0001-44', 'regional', 'internet-nacional', 'Consultoria estrategica de qualidade', 'Ser referencia em consultoria', 'Etica, Qualidade, Resultados', 1, 3, 8)
            ]
            cursor.executemany('''INSERT INTO company_data 
                (plan_id, trade_name, legal_name, cnpj, coverage_physical, coverage_online, 
                 mission, vision, company_values, headcount_strategic, headcount_tactical, headcount_operational) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', company_data)
            
            # Insert sample drivers
            drivers = [
                (plan_ids[0], 'Digitalizacao de processos', 'Implementar sistemas digitais para otimizar operacoes', 'approved', 'high', 'Marcos Fenecio'),
                (plan_ids[0], 'Capacitacao da equipe', 'Treinar equipe em novas tecnologias', 'review', 'medium', 'Ana Souza'),
                (plan_ids[0], 'Otimizacao de processos', 'Melhorar eficiencia operacional', 'approved', 'high', 'Carlos Silva'),
                (plan_ids[1], 'Expansao de mercado', 'Ampliar atuacao para novos segmentos', 'draft', 'high', 'João Santos'),
                (plan_ids[2], 'Reestruturacao organizacional', 'Reorganizar estrutura da empresa', 'draft', 'medium', 'Maria Oliveira')
            ]
            cursor.executemany('INSERT INTO drivers (plan_id, title, description, status, priority, owner) VALUES (?, ?, ?, ?, ?, ?)', drivers)
            
            # Insert sample OKRs
            okrs = [
                (plan_ids[0], 'Digitalizar 80% dos processos', 'Implementar sistemas digitais', 'global', None, 'draft'),
                (plan_ids[0], 'Capacitar 100% da equipe', 'Treinamento em novas tecnologias', 'area', 'RH', 'draft'),
                (plan_ids[0], 'Reduzir custos em 15%', 'Otimizacao de processos', 'global', None, 'draft'),
                (plan_ids[1], 'Expandir para 3 novos mercados', 'Ampliacao de atuacao', 'global', None, 'draft'),
                (plan_ids[2], 'Reestruturar organizacao', 'Nova estrutura organizacional', 'global', None, 'draft')
            ]
            cursor.executemany('INSERT INTO okrs (plan_id, title, description, type, area, status) VALUES (?, ?, ?, ?, ?, ?)', okrs)
            
            # Insert sample projects (stored in company_projects)
            sample_projects = [
                (plan_ids[0], 'Sistema de Gestao', 'Implementar ERP', 'in_progress', 'high', 'Marcos Fenecio', '2025-01-01', '2025-06-30'),
                (plan_ids[0], 'Treinamento Digital', 'Capacitar equipe', 'planned', 'medium', 'Ana Souza', '2025-02-01', '2025-04-30'),
                (plan_ids[0], 'Otimizacao Logistica', 'Melhorar distribuicao', 'completed', 'high', 'Carlos Silva', '2024-10-01', '2024-12-31'),
                (plan_ids[1], 'Expansao Norte', 'Abrir filial no Norte', 'planned', 'high', 'João Santos', '2025-03-01', '2025-12-31'),
                (plan_ids[2], 'Reestruturacao RH', 'Nova estrutura de RH', 'planned', 'medium', 'Maria Oliveira', '2025-01-15', '2025-05-15')
            ]
            cursor.execute('SELECT id, company_id FROM plans WHERE id IN ({})'.format(','.join('?' for _ in plan_ids)), tuple(plan_ids))
            plan_company_map = {row[0]: row[1] for row in cursor.fetchall()}
            cursor.executemany('''INSERT INTO company_projects (
                company_id, plan_id, title, description, status, priority, owner, start_date, end_date, okr_area_ref, activities, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', [
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
        
        cursor.execute('SELECT * FROM companies WHERE id = ?', (company_id,))
        row = cursor.fetchone()
        
        conn.close()
        return dict(row) if row else None

    def _ensure_roles_columns(self, cursor):
        """Ensure new columns on roles table exist for backward compatibility."""
        try:
            cursor.execute('PRAGMA table_info(roles)')
            columns = {row[1] for row in cursor.fetchall()}
            if 'parent_role_id' not in columns:
                cursor.execute('ALTER TABLE roles ADD COLUMN parent_role_id INTEGER')
            if 'department' not in columns:
                cursor.execute('ALTER TABLE roles ADD COLUMN department TEXT')
            if 'color' not in columns:
                cursor.execute('ALTER TABLE roles ADD COLUMN color TEXT')
        except Exception as exc:
            print(f"Error ensuring roles columns: {exc}")

    def _ensure_employees_schema(self, cursor):
        """Ensure employees table and columns exist."""
        try:
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS employees (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    company_id INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    email TEXT,
                    phone TEXT,
                    role_id INTEGER,
                    department TEXT,
                    hire_date TEXT,
                    status TEXT DEFAULT 'active',
                    weekly_hours REAL DEFAULT 40,
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (company_id) REFERENCES companies (id) ON DELETE CASCADE,
                    FOREIGN KEY (role_id) REFERENCES roles (id) ON DELETE SET NULL
                )
            ''')
            cursor.execute('PRAGMA table_info(employees)')
            columns = {row[1] for row in cursor.fetchall()}
            if 'status' not in columns:
                cursor.execute("ALTER TABLE employees ADD COLUMN status TEXT DEFAULT 'active'")
            if 'notes' not in columns:
                cursor.execute('ALTER TABLE employees ADD COLUMN notes TEXT')
            if 'updated_at' not in columns:
                cursor.execute('ALTER TABLE employees ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP')
            if 'weekly_hours' not in columns:
                cursor.execute('ALTER TABLE employees ADD COLUMN weekly_hours REAL DEFAULT 40')
            if 'whatsapp' not in columns:
                cursor.execute('ALTER TABLE employees ADD COLUMN whatsapp TEXT')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_employees_company ON employees(company_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_employees_role ON employees(role_id)')
        except Exception as exc:
            print(f"Error ensuring employees schema: {exc}")

    # Roles CRUD
    def list_roles(self, company_id: int) -> List[Dict[str, Any]]:
        conn = self._get_connection()
        cursor = conn.cursor()
        self._ensure_roles_columns(cursor)
        cursor.execute('SELECT * FROM roles WHERE company_id = ? ORDER BY title', (company_id,))
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
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
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
                    title = ?, parent_role_id = ?, department = ?, color = ?, headcount_planned = ?, weekly_hours = ?, notes = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
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
            cursor.execute('DELETE FROM roles WHERE id = ?', (role_id,))
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
        status = str(status_raw).strip().lower() if isinstance(status_raw, str) else 'active'
        if not status:
            status = 'active'

        hire_date_value = employee.get('hire_date')
        hire_date: Optional[str] = None
        if isinstance(hire_date_value, (datetime, date)):
            hire_date = hire_date_value.strftime('%Y-%m-%d')
        elif isinstance(hire_date_value, str):
            hire_date_value = hire_date_value.strip()
            hire_date = hire_date_value or None

        role_id_value = employee.get('role_id')
        role_id: Optional[int]
        if isinstance(role_id_value, str):
            role_id_value = role_id_value.strip()
            if not role_id_value:
                role_id = None
            else:
                try:
                    role_id = int(role_id_value)
                except ValueError:
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
        cursor = conn.cursor()
        self._ensure_employees_schema(cursor)
        try:
            self._ensure_roles_columns(cursor)
        except Exception:
            pass
        cursor.execute('''
            SELECT e.*, r.title AS role_name
            FROM employees e
            LEFT JOIN roles r ON e.role_id = r.id
            WHERE e.company_id = ?
            ORDER BY LOWER(COALESCE(e.name, '')) ASC, e.id ASC
        ''', (company_id,))
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return rows

    def get_employee(self, company_id: int, employee_id: int) -> Optional[Dict[str, Any]]:
        conn = self._get_connection()
        cursor = conn.cursor()
        self._ensure_employees_schema(cursor)
        try:
            self._ensure_roles_columns(cursor)
        except Exception:
            pass
        cursor.execute('''
            SELECT e.*, r.title AS role_name
            FROM employees e
            LEFT JOIN roles r ON e.role_id = r.id
            WHERE e.company_id = ? AND e.id = ?
            LIMIT 1
        ''', (company_id, employee_id))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    def create_employee(self, company_id: int, employee_data: Dict[str, Any]) -> Optional[int]:
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            self._ensure_employees_schema(cursor)
            normalized = self._normalize_employee_payload(employee_data)
            cursor.execute('''
                INSERT INTO employees (
                    company_id, name, email, phone, role_id, department, hire_date, status, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            new_id = cursor.lastrowid
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
        try:
            cursor = conn.cursor()
            self._ensure_employees_schema(cursor)
            normalized = self._normalize_employee_payload(employee_data)
            cursor.execute('''
                UPDATE employees
                SET name = ?, email = ?, phone = ?, role_id = ?, department = ?, hire_date = ?, status = ?, notes = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ? AND company_id = ?
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
        try:
            cursor = conn.cursor()
            self._ensure_employees_schema(cursor)
            cursor.execute('DELETE FROM employees WHERE id = ? AND company_id = ?', (employee_id, company_id))
            conn.commit()
            return cursor.rowcount > 0
        except Exception as exc:
            conn.rollback()
            print(f"Error deleting employee: {exc}")
            return False
        finally:
            conn.close()
    
    # ===== CÓDIGO AUTOMÁTICO - SISTEMA DE CODIFICAÇÃO =====
    def _generate_area_code(self, company_id: int, area_id: int) -> str:
        """
        Gera código para área baseado em:
        - Código do cliente (ex: AO, AB, AC, etc.)
        - Tipo: C (processos) ou J (projetos)
        - Número sequencial da área
        Retorna: AO.C.1, AO.C.2, etc.
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Buscar código do cliente
        cursor.execute('SELECT client_code FROM companies WHERE id = ?', (company_id,))
        row = cursor.fetchone()
        client_code = row['client_code'] if row and row['client_code'] else 'XX'
        
        # Buscar order_index da área para usar como número
        cursor.execute('SELECT order_index FROM process_areas WHERE id = ?', (area_id,))
        area_row = cursor.fetchone()
        area_number = area_row['order_index'] if area_row and area_row['order_index'] > 0 else area_id
        
        conn.close()
        return f"{client_code}.C.{area_number}"
    
    def _generate_macro_code(self, company_id: int, area_id: int, macro_id: int) -> str:
        """
        Gera código para macroprocesso baseado em:
        - Código da área
        - Número sequencial do macro dentro da área
        Retorna: AO.C.1.2, AO.C.1.3, etc.
        """
        area_code = self._generate_area_code(company_id, area_id)
        
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Buscar order_index do macro para usar como número
        cursor.execute('SELECT order_index FROM macro_processes WHERE id = ?', (macro_id,))
        macro_row = cursor.fetchone()
        macro_number = macro_row['order_index'] if macro_row and macro_row['order_index'] > 0 else macro_id
        
        conn.close()
        return f"{area_code}.{macro_number}"
    
    def _generate_process_code(self, company_id: int, macro_id: int, process_id: int) -> str:
        """
        Gera código completo para processo baseado em:
        - Código do macroprocesso
        - Número sequencial do processo dentro do macro
        Retorna: AO.C.1.2.11, AO.C.1.2.12, etc.
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Buscar area_id do macro
        cursor.execute('SELECT area_id FROM macro_processes WHERE id = ?', (macro_id,))
        macro_row = cursor.fetchone()
        if not macro_row:
            return f"XX.C.0.0.{process_id}"
        
        area_id = macro_row['area_id']
        macro_code = self._generate_macro_code(company_id, area_id, macro_id)
        
        # Buscar order_index do processo para usar como número
        cursor.execute('SELECT order_index FROM processes WHERE id = ?', (process_id,))
        process_row = cursor.fetchone()
        process_number = process_row['order_index'] if process_row and process_row['order_index'] > 0 else process_id
        
        conn.close()
        return f"{macro_code}.{process_number}"
    
    def _update_area_code(self, area_id: int, company_id: int) -> bool:
        """Atualiza o código de uma área"""
        try:
            code = self._generate_area_code(company_id, area_id)
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute('UPDATE process_areas SET code = ? WHERE id = ?', (code, area_id))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error updating area code: {e}")
            return False
    
    def _update_macro_code(self, macro_id: int, company_id: int, area_id: int) -> bool:
        """Atualiza o código de um macroprocesso"""
        try:
            code = self._generate_macro_code(company_id, area_id, macro_id)
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute('UPDATE macro_processes SET code = ? WHERE id = ?', (code, macro_id))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error updating macro code: {e}")
            return False
    
    def _update_process_code(self, process_id: int, company_id: int, macro_id: int) -> bool:
        """Atualiza o código de um processo"""
        try:
            code = self._generate_process_code(company_id, macro_id, process_id)
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute('UPDATE processes SET code = ? WHERE id = ?', (code, process_id))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error updating process code: {e}")
            return False
    
    # Process Areas CRUD
    def list_process_areas(self, company_id: int) -> List[Dict[str, Any]]:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM process_areas WHERE company_id = ? ORDER BY code, order_index, name', (company_id,))
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
                cursor.execute('SELECT MAX(order_index) as max_order FROM process_areas WHERE company_id = ?', (company_id,))
                row = cursor.fetchone()
                max_order = row['max_order'] if row and row['max_order'] else 0
                order_index = max_order + 1
            
            # Gerar código automático: {CLIENT_CODE}.C.{SEQUENCE}
            cursor.execute('SELECT client_code FROM companies WHERE id = ?', (company_id,))
            company_row = cursor.fetchone()
            client_code = company_row['client_code'] if company_row and company_row['client_code'] else 'XX'
            
            # Código da área: CLIENT.C.SEQUENCE
            area_code = f"{client_code}.C.{area.get('code', order_index)}"
            
            cursor.execute('''
                INSERT INTO process_areas (company_id, code, name, description, order_index, color)
                VALUES (?, ?, ?, ?, ?, ?)
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
            cursor.execute('SELECT company_id FROM process_areas WHERE id = ?', (area_id,))
            row = cursor.fetchone()
            if not row:
                return False
            company_id = row['company_id']
            
            # Gerar código automático: {CLIENT_CODE}.C.{SEQUENCE}
            cursor.execute('SELECT client_code FROM companies WHERE id = ?', (company_id,))
            company_row = cursor.fetchone()
            client_code = company_row['client_code'] if company_row and company_row['client_code'] else 'XX'
            
            # Código da área: CLIENT.C.SEQUENCE
            order_index = int(area.get('order_index') or 0)
            area_code = f"{client_code}.C.{area.get('code', order_index)}"
            
            cursor.execute('''
                UPDATE process_areas SET
                    code = ?, name = ?, description = ?, order_index = ?, color = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
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
            cursor.execute('DELETE FROM process_areas WHERE id = ?', (area_id,))
            conn.commit()
            conn.close()
            return True
        except Exception as exc:
            print(f"Error deleting process area: {exc}")
            return False
    
    # Macro Processes CRUD
    def get_macro_process(self, macro_id: int) -> Optional[Dict[str, Any]]:
        """Get a single macro process by ID"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM macro_processes WHERE id = ?', (macro_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None
    
    def list_macro_processes(self, company_id: int) -> List[Dict[str, Any]]:
        conn = self._get_connection()
        cursor = conn.cursor()
        # Order by area and sequence to ensure stable listing even before code generation
        cursor.execute('SELECT * FROM macro_processes WHERE company_id = ? ORDER BY area_id, order_index, name', (company_id,))
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
                cursor.execute('SELECT MAX(order_index) as max_order FROM macro_processes WHERE company_id = ? AND area_id = ?', (company_id, area_id))
                row = cursor.fetchone()
                max_order = row['max_order'] if row and row['max_order'] else 0
                order_index = max_order + 1
            
            cursor.execute('''
                INSERT INTO macro_processes (company_id, area_id, name, owner, description, order_index)
                VALUES (?, ?, ?, ?, ?, ?)
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
    
    def update_macro_process(self, macro_id: int, macro: Dict[str, Any]) -> bool:
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Primeiro, obter o company_id e area_id para regenerar o código
            cursor.execute('SELECT company_id, area_id FROM macro_processes WHERE id = ?', (macro_id,))
            row = cursor.fetchone()
            if not row:
                conn.close()
                return False
                
            company_id = row['company_id']
            area_id = int(macro.get('area_id'))
            
            cursor.execute('''
                UPDATE macro_processes SET
                    area_id = ?, name = ?, owner = ?, description = ?, order_index = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
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
            cursor.execute('DELETE FROM macro_processes WHERE id = ?', (macro_id,))
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
        cursor.execute('SELECT * FROM processes WHERE company_id = ? ORDER BY code, order_index, name', (company_id,))
        rows = []
        for row in cursor.fetchall():
            as_dict = dict(row)
            as_dict['kanban_stage'] = self._normalize_process_stage(as_dict.get('kanban_stage'))
            rows.append(as_dict)
        conn.close()
        return rows

    def get_process_artifact_presence(self, company_id: int) -> Dict[int, Dict[str, bool]]:
        """
        Recupera indicadores booleanos sobre artefatos já produzidos
        para cada processo (rotinas, POP e indicadores).
        Mantido para compatibilidade, embora o app utilize PostgreSQL.
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        summary: Dict[int, Dict[str, bool]] = {}

        def _slot(process_id: Optional[int]) -> Optional[Dict[str, bool]]:
            if not process_id:
                return None
            if process_id not in summary:
                summary[process_id] = {
                    'has_routine': False,
                    'has_pop': False,
                    'has_indicator': False
                }
            return summary[process_id]

        def _run_query(query: str, params: tuple, flag_key: str, id_field: str = 'process_id') -> None:
            try:
                cursor.execute(query, params)
                for row in cursor.fetchall():
                    record = dict(row)
                    slot = _slot(record.get(id_field))
                    if slot:
                        slot[flag_key] = (record.get('total') or 0) > 0
            except Exception as exc:
                print(f"[SQLite] Warning while gathering process artifact presence ({flag_key}): {exc}")

        try:
            _run_query('''
                SELECT process_id, COUNT(*) AS total
                FROM routines
                WHERE company_id = ? AND process_id IS NOT NULL AND is_active = 1
                GROUP BY process_id
            ''', (company_id,), 'has_routine')

            _run_query('''
                SELECT p.id AS process_id, COUNT(a.id) AS total
                FROM processes p
                JOIN process_activities a ON a.process_id = p.id
                WHERE p.company_id = ?
                GROUP BY p.id
            ''', (company_id,), 'has_pop')

            _run_query('''
                SELECT process_id, COUNT(*) AS total
                FROM indicators
                WHERE company_id = ? AND process_id IS NOT NULL
                GROUP BY process_id
            ''', (company_id,), 'has_indicator')

            return summary
        finally:
            conn.close()
    
    def create_process(self, company_id: int, process: Dict[str, Any]) -> Optional[int]:
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            macro_id = int(process.get('macro_id'))
            
            # Se order_index não foi fornecido, calcular o próximo dentro do macro
            order_index = process.get('order_index')
            if not order_index or order_index == 0:
                cursor.execute('SELECT MAX(order_index) as max_order FROM processes WHERE company_id = ? AND macro_id = ?', (company_id, macro_id))
                row = cursor.fetchone()
                max_order = row['max_order'] if row and row['max_order'] else 0
                order_index = max_order + 1
            
            # Gerar código automático: {MACRO_CODE}.{SEQUENCE}
            cursor.execute('SELECT code FROM macro_processes WHERE id = ?', (macro_id,))
            macro_row = cursor.fetchone()
            macro_code = macro_row['code'] if macro_row and macro_row['code'] else 'XX'
            
            # Código do processo: MACRO_CODE.SEQUENCE
            process_code = f"{macro_code}.{order_index}"
            
            stage = self._normalize_process_stage(process.get('kanban_stage') or process.get('stage'))
            # Mapear automaticamente o stage do Kanban para o nível de estruturação
            structuring_level = self._kanban_stage_to_structuring_level(stage)

            cursor.execute('''
                INSERT INTO processes (company_id, macro_id, code, name, structuring_level, performance_level, responsible, description, order_index, kanban_stage)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
    
    def update_process(self, process_id: int, process: Dict[str, Any]) -> bool:
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            macro_id = int(process.get('macro_id'))
            order_index = int(process.get('order_index') or 0)
            
            # Gerar código automático: {MACRO_CODE}.{SEQUENCE}
            cursor.execute('SELECT code FROM macro_processes WHERE id = ?', (macro_id,))
            macro_row = cursor.fetchone()
            macro_code = macro_row['code'] if macro_row and macro_row['code'] else 'XX'
            
            # Código do processo: MACRO_CODE.SEQUENCE
            process_code = f"{macro_code}.{order_index}"
            
            stage = self._normalize_process_stage(process.get('kanban_stage') or process.get('stage'))
            # Mapear automaticamente o stage do Kanban para o nível de estruturação
            structuring_level = self._kanban_stage_to_structuring_level(stage)

            cursor.execute('''
                UPDATE processes SET
                    macro_id = ?, code = ?, name = ?, structuring_level = ?, performance_level = ?, responsible = ?, description = ?, order_index = ?, kanban_stage = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
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
                SET kanban_stage = ?, structuring_level = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
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
                SET notes = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (notes, process_id))
            conn.commit()
            conn.close()
            return cursor.rowcount > 0
        except Exception as exc:
            print(f"Error updating process notes: {exc}")
            return False

    def get_process(self, process_id: int) -> Optional[Dict[str, Any]]:
        """Retrieve a single process by ID."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM processes WHERE id = ?', (process_id,))
        row = cursor.fetchone()
        conn.close()
        if not row:
            return None
        record = dict(row)
        record['kanban_stage'] = self._normalize_process_stage(record.get('kanban_stage'))
        return record

    def set_process_flow_document(self, process_id: int, path: Optional[str]) -> bool:
        """Associate a flow document (PDF ou imagem) to a process."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(
                '''
                UPDATE processes
                SET flow_document = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
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
    def list_process_activities(self, process_id: int) -> List[Dict[str, Any]]:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            '''
            SELECT * FROM process_activities
            WHERE process_id = ?
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
            '''.format(','.join('?' for _ in activity_ids)),
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

    def get_process_activity(self, activity_id: int) -> Optional[Dict[str, Any]]:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM process_activities WHERE id = ?', (activity_id,))
        row = cursor.fetchone()
        conn.close()
        if not row:
            return None
        data = dict(row)
        data['code_suffix'] = self._extract_activity_suffix(data.get('code'))
        return data

    def create_process_activity(self, process_id: int, activity: Dict[str, Any]) -> Optional[int]:
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            order_index = activity.get('order_index')
            if not order_index or order_index <= 0:
                cursor.execute(
                    'SELECT MAX(order_index) as max_order FROM process_activities WHERE process_id = ?',
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
                VALUES (?, ?, ?, ?, ?)
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

    def update_process_activity(self, activity_id: int, activity: Dict[str, Any]) -> bool:
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            suffix = self._normalize_activity_suffix(activity.get('code_suffix') or activity.get('suffix'))
            current = None
            if suffix:
                cursor.execute('SELECT process_id FROM process_activities WHERE id = ?', (activity_id,))
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
                SET name = ?, layout = ?, order_index = ?, code = COALESCE(?, code), updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
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
            cursor.execute('DELETE FROM process_activity_entries WHERE activity_id = ?', (activity_id,))
            cursor.execute('DELETE FROM process_activities WHERE id = ?', (activity_id,))
            conn.commit()
            conn.close()
            return cursor.rowcount > 0
        except Exception as exc:
            print(f"Error deleting process activity: {exc}")
            return False

    def create_process_activity_entry(self, activity_id: int, entry: Dict[str, Any]) -> Optional[int]:
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            order_index = entry.get('order_index')
            if not order_index or order_index <= 0:
                cursor.execute(
                    'SELECT MAX(order_index) as max_order FROM process_activity_entries WHERE activity_id = ?',
                    (activity_id,)
                )
                row = cursor.fetchone()
                max_order = row['max_order'] if row and row['max_order'] else 0
                order_index = max_order + 1

            cursor.execute(
                '''
                INSERT INTO process_activity_entries (activity_id, order_index, text_content, image_path, image_width, layout)
                VALUES (?, ?, ?, ?, ?, ?)
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

    def update_process_activity_entry(self, entry_id: int, entry: Dict[str, Any]) -> bool:
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(
                '''
                UPDATE process_activity_entries
                SET text_content = ?, image_path = ?, order_index = ?, image_width = ?, layout = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
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
            cursor.execute('DELETE FROM process_activity_entries WHERE id = ?', (entry_id,))
            conn.commit()
            conn.close()
            return cursor.rowcount > 0
        except Exception as exc:
            print(f"Error deleting process activity entry: {exc}")
            return False

    def list_process_activity_entries(self, activity_id: int) -> List[Dict[str, Any]]:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            '''
            SELECT * FROM process_activity_entries
            WHERE activity_id = ?
            ORDER BY order_index, id
            ''',
            (activity_id,)
        )
        rows = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return rows

    def get_process_activity_entry(self, entry_id: int) -> Optional[Dict[str, Any]]:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM process_activity_entries WHERE id = ?', (entry_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None
    
    def delete_process(self, process_id: int) -> bool:
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute('DELETE FROM processes WHERE id = ?', (process_id,))
            conn.commit()
            conn.close()
            return True
        except Exception as exc:
            print(f"Error deleting process: {exc}")
            return False
    
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

    def update_company_mvv(self, company_id: int, mission: str, vision: str, values: str) -> bool:
        """Update company-level MVV fields"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE companies SET
                    mvv_mission = ?, mvv_vision = ?, mvv_values = ?
                WHERE id = ?
            ''', (mission, vision, values, company_id))
            conn.commit()
            conn.close()
            return True
        except Exception as exc:
            print(f"Error updating company MVV: {exc}")
            return False

    def get_company_profile(self, company_id: int) -> Optional[Dict[str, Any]]:
        """Get full company profile including configs"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM companies WHERE id = ?', (company_id,))
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
                    name = ?, legal_name = ?, industry = ?, size = ?, description = ?,
                    client_code = ?,
                    mvv_mission = ?, mvv_vision = ?, mvv_values = ?,
                    pev_config = ?, grv_config = ?
                WHERE id = ?
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
    def get_plans_by_company(self, company_id: int) -> List[Dict[str, Any]]:
        """Get plans for a company"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM plans WHERE company_id = ? ORDER BY name', (company_id,))
        plans = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        return plans
    
    def get_plan(self, plan_id: int) -> Optional[Dict[str, Any]]:
        """Get plan by ID"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM plans WHERE id = ?', (plan_id,))
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
            WHERE p.id = ?
        ''', (plan_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        return dict(row) if row else None
    
    # Participant operations
    def get_participants(self, plan_id: int) -> List[Dict[str, Any]]:
        """Get participants for a plan"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM participants WHERE plan_id = ? ORDER BY name', (plan_id,))
        participants = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        return participants
    
    def add_participant(self, plan_id: int, participant_data: Dict[str, Any]) -> Optional[int]:
        """Add new participant and return the ID"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO participants (plan_id, employee_id, name, role, relation, email, cpf, phone, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                plan_id,
                participant_data.get('employee_id'),
                participant_data.get('name'),
                participant_data.get('role'),
                participant_data.get('relation'),
                participant_data.get('email'),
                participant_data.get('cpf'),
                participant_data.get('phone'),
                participant_data.get('status', 'active')
            ))
            
            participant_id = cursor.lastrowid
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
            
            cursor.execute('SELECT * FROM participants WHERE id = ?', (participant_id,))
            row = cursor.fetchone()
            
            conn.close()
            
            if row:
                return {
                    'id': row[0],
                    'plan_id': row[1],
                    'name': row[2],
                    'role': row[3],
                    'email': row[4],
                    'phone': row[5],
                    'created_at': row[6],
                    'relation': row[7],
                    'cpf': row[8],
                    'status': row[9],
                    'message_sent': bool(row[10]) if len(row) > 10 else False,
                    'email_confirmed': bool(row[11]) if len(row) > 11 else False,
                    'whatsapp_confirmed': bool(row[12]) if len(row) > 12 else False,
                    'updated_at': row[13] if len(row) > 13 else None
                }
            return None
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
                SET name = ?, role = ?, relation = ?, email = ?, cpf = ?, phone = ?, status = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
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
            
            cursor.execute('DELETE FROM participants WHERE id = ?', (participant_id,))
            
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
            
            cursor.execute('UPDATE participants SET status = ? WHERE id = ?', (status, participant_id))
            
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
            
            cursor.execute('SELECT * FROM message_templates WHERE plan_id = ?', (plan_id,))
            rows = cursor.fetchall()
            
            conn.close()
            
            templates = []
            for row in rows:
                templates.append({
                    'id': row[0],
                    'plan_id': row[1],
                    'message_type': row[2],
                    'subject': row[3],
                    'content': row[4],
                    'created_at': row[5],
                    'updated_at': row[6]
                })
            return templates
        except Exception as e:
            print(f"Error getting message templates: {e}")
            return []
    
    def get_message_template(self, plan_id: int, message_type: str) -> Optional[Dict[str, Any]]:
        """Get specific message template"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM message_templates WHERE plan_id = ? AND message_type = ?', (plan_id, message_type))
            row = cursor.fetchone()
            
            conn.close()
            
            if row:
                return {
                    'id': row[0],
                    'plan_id': row[1],
                    'message_type': row[2],
                    'subject': row[3],
                    'content': row[4],
                    'created_at': row[5],
                    'updated_at': row[6]
                }
            return None
        except Exception as e:
            print(f"Error getting message template: {e}")
            return None
    
    def save_message_template(self, plan_id: int, message_type: str, subject: str, content: str) -> bool:
        """Save or update message template"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Check if template exists
            cursor.execute('SELECT id FROM message_templates WHERE plan_id = ? AND message_type = ?', (plan_id, message_type))
            existing = cursor.fetchone()
            
            if existing:
                # Update existing template
                cursor.execute('''
                    UPDATE message_templates 
                    SET subject = ?, content = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE plan_id = ? AND message_type = ?
                ''', (subject, content, plan_id, message_type))
            else:
                # Insert new template
                cursor.execute('''
                    INSERT INTO message_templates (plan_id, message_type, subject, content)
                    VALUES (?, ?, ?, ?)
                ''', (plan_id, message_type, subject, content))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error saving message template: {e}")
            return False
    
    def _ensure_company_data_columns(self, cursor):
        """Add missing columns to company_data table if needed."""
        try:
            cursor.execute('PRAGMA table_info(company_data)')
            columns = {row[1] for row in cursor.fetchall()}
            if 'financial_total_revenue' not in columns:
                cursor.execute('ALTER TABLE company_data ADD COLUMN financial_total_revenue TEXT')
            if 'financial_total_margin' not in columns:
                cursor.execute('ALTER TABLE company_data ADD COLUMN financial_total_margin TEXT')
            if 'other_information' not in columns:
                cursor.execute('ALTER TABLE company_data ADD COLUMN other_information TEXT')
            if 'grv_mvv_in_use' not in columns:
                cursor.execute('ALTER TABLE company_data ADD COLUMN grv_mvv_in_use INTEGER DEFAULT 0')
        except Exception as exc:
            print(f"Error ensuring company_data columns: {exc}")


    # Company data operations
    def get_company_data(self, plan_id: int) -> Optional[Dict[str, Any]]:
        """Get company data for a plan"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM company_data WHERE plan_id = ?', (plan_id,))
        row = cursor.fetchone()
        
        conn.close()
        return dict(row) if row else None
    
    def update_company_analyses(self, plan_id: int, data: Dict[str, Any]) -> bool:
        """Update only analysis fields in company data"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Check if company data exists
            cursor.execute('SELECT id FROM company_data WHERE plan_id = ?', (plan_id,))
            existing = cursor.fetchone()
            
            if existing:
                # Update only analysis fields
                cursor.execute('''
                    UPDATE company_data SET
                        ai_insights = ?, consultant_analysis = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE plan_id = ?
                ''', (
                    data.get('ai_insights'),
                    data.get('consultant_analysis'),
                    plan_id
                ))
            else:
                # Insert new record with only analysis fields
                cursor.execute('''
                    INSERT INTO company_data (plan_id, ai_insights, consultant_analysis)
                    VALUES (?, ?, ?)
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


    def update_company_data(self, plan_id: int, data: Dict[str, Any]) -> bool:
        """Update company data"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            self._ensure_company_data_columns(cursor)
            
            # Check if company data exists
            cursor.execute('SELECT id FROM company_data WHERE plan_id = ?', (plan_id,))
            existing = cursor.fetchone()
            
            if existing:
                # Update existing
                cursor.execute('''
                    UPDATE company_data SET
                        trade_name = ?, legal_name = ?, cnpj = ?, coverage_physical = ?, coverage_online = ?,
                        experience_total = ?, experience_segment = ?, cnaes = ?,
                        mission = ?, vision = ?, company_values = ?, headcount_strategic = ?, headcount_tactical = ?, headcount_operational = ?,
                        financials = ?, financial_total_revenue = ?, financial_total_margin = ?,
                        other_information = ?, ai_insights = ?, consultant_analysis = ?,
                        process_map_file = ?, org_chart_file = ?, grv_mvv_in_use = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE plan_id = ?
                ''', (
                    data.get('trade_name'),
                    data.get('legal_name'),
                    data.get('cnpj'),
                    data.get('coverage_physical'),
                    data.get('coverage_online'),
                    data.get('experience_total'),
                    data.get('experience_segment'),
                    json.dumps(data.get('cnaes', [])),
                    data.get('mission'),
                    data.get('vision'),
                    data.get('company_values'),
                    int(data.get('headcount_strategic') or 0),
                    int(data.get('headcount_tactical') or 0),
                    int(data.get('headcount_operational') or 0),
                    json.dumps(data.get('financials', [])),
                    data.get('financial_total_revenue'),
                    data.get('financial_total_margin'),
                    data.get('other_information'),
                    data.get('ai_insights'),
                    data.get('consultant_analysis'),
                    data.get('process_map_file'),
                    data.get('org_chart_file'),
                    int(data.get('grv_mvv_in_use') or 0),
                    plan_id
                ))
            else:
                # Insert new
                cursor.execute('''
                INSERT INTO company_data 
                (plan_id, trade_name, legal_name, cnpj, coverage_physical, coverage_online, 
                 experience_total, experience_segment, cnaes,
                 mission, vision, company_values, headcount_strategic, headcount_tactical, headcount_operational,
                 financials, financial_total_revenue, financial_total_margin, other_information, ai_insights, consultant_analysis, process_map_file, org_chart_file, grv_mvv_in_use) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                plan_id,
                data.get('trade_name'),
                data.get('legal_name'),
                data.get('cnpj'),
                data.get('coverage_physical'),
                data.get('coverage_online'),
                data.get('experience_total'),
                data.get('experience_segment'),
                json.dumps(data.get('cnaes', [])),
                data.get('mission'),
                data.get('vision'),
                data.get('company_values'),
                int(data.get('headcount_strategic') or 0),
                int(data.get('headcount_tactical') or 0),
                int(data.get('headcount_operational') or 0),
                json.dumps(data.get('financials', [])),
                data.get('financial_total_revenue'),
                data.get('financial_total_margin'),
                data.get('other_information'),
                data.get('ai_insights'),
                data.get('consultant_analysis'),
                data.get('process_map_file'),
                data.get('org_chart_file'),
                int(data.get('grv_mvv_in_use') or 0)
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
        
        cursor.execute('SELECT * FROM drivers WHERE plan_id = ? ORDER BY created_at', (plan_id,))
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
                VALUES (?, ?, ?, ?, ?, ?)
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
                WHERE plan_id = ?
                ORDER BY created_at DESC
            ''', (plan_id,))
            records = []
            for row in cursor.fetchall():
                records.append({
                    'id': row['id'],
                    'plan_id': row['plan_id'],
                    'analysis': row['analysis'],
                    'created_at': row['created_at'],
                    'updated_at': row['updated_at']
                })
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
                WHERE id = ?
            ''', (record_id,))
            row = cursor.fetchone()
            conn.close()
            if row:
                return {
                    'id': row['id'],
                    'plan_id': row['plan_id'],
                    'analysis': row['analysis'],
                    'created_at': row['created_at'],
                    'updated_at': row['updated_at']
                }
            return None
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
                VALUES (?, ?)
            ''', (plan_id, analysis))
            new_id = cursor.lastrowid
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
                SET analysis = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (analysis, record_id))
            conn.commit()
            conn.close()
            return cursor.rowcount > 0
        except Exception as e:
            print(f"Error updating preliminary OKR record: {e}")
            return False

    def delete_okr_preliminary_record(self, record_id: int) -> bool:
        '''Delete a preliminary OKR analysis'''
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute('DELETE FROM okr_preliminary_records WHERE id = ?', (record_id,))
            conn.commit()
            conn.close()
            return cursor.rowcount > 0
        except Exception as e:
            print(f"Error deleting preliminary OKR record: {e}")
            return False

    # OKR Area preliminary records operations
    def add_okr_area_preliminary_record(self, plan_id: int, analysis: str) -> Optional[int]:
        '''Create a preliminary area OKR analysis and return its ID'''
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO okr_area_preliminary_records (plan_id, analysis)
                VALUES (?, ?)
            ''', (plan_id, analysis))
            new_id = cursor.lastrowid
            conn.commit()
            conn.close()
            return new_id
        except Exception as e:
            print(f"Error adding preliminary area OKR record: {e}")
            return None

    def update_okr_area_preliminary_record(self, record_id: int, analysis: str) -> bool:
        '''Update a preliminary area OKR analysis'''
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE okr_area_preliminary_records
                SET analysis = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (analysis, record_id))
            conn.commit()
            conn.close()
            return cursor.rowcount > 0
        except Exception as e:
            print(f"Error updating preliminary area OKR record: {e}")
            return False

    def delete_okr_area_preliminary_record(self, record_id: int) -> bool:
        '''Delete a preliminary area OKR analysis'''
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute('DELETE FROM okr_area_preliminary_records WHERE id = ?', (record_id,))
            conn.commit()
            conn.close()
            return cursor.rowcount > 0
        except Exception as e:
            print(f"Error deleting preliminary area OKR record: {e}")
            return False

    def get_okr_area_preliminary_records(self, plan_id: int) -> List[Dict[str, Any]]:
        '''Get all preliminary area OKR records for a plan'''
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, plan_id, analysis, created_at, updated_at
                FROM okr_area_preliminary_records
                WHERE plan_id = ?
                ORDER BY created_at DESC
            ''', (plan_id,))
            records = []
            for row in cursor.fetchall():
                records.append({
                    'id': row[0],
                    'plan_id': row[1],
                    'analysis': row[2],
                    'created_at': row[3],
                    'updated_at': row[4]
                })
            conn.close()
            return records
        except Exception as e:
            print(f"Error getting preliminary area OKR records: {e}")
            return []

    # OKR Global records operations
    def get_global_okr_records(self, plan_id: int, stage: str) -> List[Dict[str, Any]]:
        '''Get OKR records for a plan and stage'''
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, plan_id, stage, objective, okr_type, type_display, owner_id, owner, deadline, observations, directional, created_at, updated_at
                FROM okr_global_records
                WHERE plan_id = ? AND stage = ?
                ORDER BY created_at DESC
            ''', (plan_id, stage))
            records = []
            for row in cursor.fetchall():
                okr_id = row['id']
                cursor.execute('''
                    SELECT id, okr_id, label, target, deadline, owner_id, owner, indicator_id, position
                    FROM okr_global_key_results
                    WHERE okr_id = ?
                    ORDER BY position ASC, id ASC
                ''', (okr_id,))
                key_results = [
                    {
                        'id': kr['id'],
                        'okr_id': kr['okr_id'],
                        'label': kr['label'],
                        'target': kr['target'],
                        'deadline': kr['deadline'],
                        'owner_id': kr['owner_id'],
                        'owner': kr['owner'],
                        'indicator_id': kr['indicator_id'],
                        'position': kr['position']
                    }
                    for kr in cursor.fetchall()
                ]
                # Convert datetime strings to datetime objects
                record_data = {
                    'id': row['id'],
                    'plan_id': row['plan_id'],
                    'stage': row['stage'],
                    'objective': row['objective'],
                    'okr_type': row['okr_type'],
                    'type_display': row['type_display'],
                    'owner_id': row['owner_id'],
                    'owner': row['owner'],
                    'deadline': row['deadline'],
                    'observations': row['observations'],
                    'directional': row['directional'],
                    'created_at': row['created_at'],
                    'updated_at': row['updated_at'],
                    'key_results': key_results
                }
                
                # Convert datetime fields from strings to datetime objects
                from datetime import datetime
                for field in ['created_at', 'updated_at', 'deadline']:
                    if field in record_data and record_data[field]:
                        try:
                            if isinstance(record_data[field], str):
                                if 'T' in record_data[field] or '+' in record_data[field]:
                                    record_data[field] = datetime.fromisoformat(record_data[field].replace('Z', '+00:00'))
                                else:
                                    # Try to parse as date string (YYYY-MM-DD)
                                    record_data[field] = datetime.strptime(record_data[field], '%Y-%m-%d')
                        except:
                            pass  # Keep original value if conversion fails
                
                # Also convert key result deadlines
                for kr in record_data['key_results']:
                    if 'deadline' in kr and kr['deadline']:
                        try:
                            if isinstance(kr['deadline'], str):
                                if 'T' in kr['deadline'] or '+' in kr['deadline']:
                                    kr['deadline'] = datetime.fromisoformat(kr['deadline'].replace('Z', '+00:00'))
                                else:
                                    kr['deadline'] = datetime.strptime(kr['deadline'], '%Y-%m-%d')
                        except:
                            pass
                
                records.append(record_data)
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
                WHERE id = ?
            ''', (okr_id,))
            row = cursor.fetchone()
            if not row:
                conn.close()
                return None
            cursor.execute('''
                SELECT id, okr_id, label, target, deadline, owner_id, owner, indicator_id, position
                FROM okr_global_key_results
                WHERE okr_id = ?
                ORDER BY position ASC, id ASC
            ''', (okr_id,))
            key_results = [
                {
                    'id': kr['id'],
                    'okr_id': kr['okr_id'],
                    'label': kr['label'],
                    'target': kr['target'],
                    'deadline': kr['deadline'],
                    'owner_id': kr['owner_id'],
                    'owner': kr['owner'],
                    'indicator_id': kr['indicator_id'],
                    'position': kr['position']
                }
                for kr in cursor.fetchall()
            ]
            conn.close()
            return {
                'id': row['id'],
                'plan_id': row['plan_id'],
                'stage': row['stage'],
                'objective': row['objective'],
                'okr_type': row['okr_type'],
                'type_display': row['type_display'],
                'owner_id': row['owner_id'],
                'owner': row['owner'],
                'deadline': row['deadline'],
                'observations': row['observations'],
                'directional': row['directional'],
                'created_at': row['created_at'],
                'updated_at': row['updated_at'],
                'key_results': key_results
            }
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
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            okr_id = cursor.lastrowid
            for position, kr in enumerate(key_results):
                cursor.execute('''
                    INSERT INTO okr_global_key_results (okr_id, label, target, deadline, owner_id, owner, indicator_id, position)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
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
                SET objective = ?, okr_type = ?, type_display = ?, owner_id = ?, owner = ?, deadline = ?, observations = ?, directional = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
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
            cursor.execute('DELETE FROM okr_global_key_results WHERE okr_id = ?', (okr_id,))
            for position, kr in enumerate(key_results):
                cursor.execute('''
                    INSERT INTO okr_global_key_results (okr_id, label, target, deadline, owner_id, owner, indicator_id, position)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
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
            cursor.execute('DELETE FROM okr_global_key_results WHERE okr_id = ?', (okr_id,))
            cursor.execute('DELETE FROM okr_global_records WHERE id = ?', (okr_id,))
            conn.commit()
            conn.close()
            return cursor.rowcount > 0
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
            placeholders = ','.join(['?'] * len(okr_ids))
            cursor.execute(f'DELETE FROM okr_global_key_results WHERE okr_id IN ({placeholders})', okr_ids)
            cursor.execute(f'DELETE FROM okr_global_records WHERE plan_id = ? AND stage = ? AND id IN ({placeholders})', [plan_id, stage, *okr_ids])
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
                WHERE plan_id = ? AND stage = ? AND (objective LIKE ? OR owner LIKE ? OR observations LIKE ?)
                ORDER BY created_at DESC
            ''', (plan_id, stage, like_query, like_query, like_query))
            results = []
            for row in cursor.fetchall():
                cursor.execute('''
                    SELECT id, okr_id, label, target, deadline, owner_id, owner, indicator_id, position
                    FROM okr_global_key_results
                    WHERE okr_id = ?
                    ORDER BY position ASC, id ASC
                ''', (row['id'],))
                key_results = [
                    {
                        'id': kr['id'],
                        'okr_id': kr['okr_id'],
                        'label': kr['label'],
                        'target': kr['target'],
                        'deadline': kr['deadline'],
                        'owner_id': kr['owner_id'],
                        'owner': kr['owner'],
                        'indicator_id': kr['indicator_id'],
                        'position': kr['position']
                    }
                    for kr in cursor.fetchall()
                ]
                results.append({
                    'id': row['id'],
                    'plan_id': row['plan_id'],
                    'stage': row['stage'],
                    'objective': row['objective'],
                    'okr_type': row['okr_type'],
                    'type_display': row['type_display'],
                    'owner_id': row['owner_id'],
                    'owner': row['owner'],
                    'deadline': row['deadline'],
                    'observations': row['observations'],
                    'directional': row['directional'],
                    'created_at': row['created_at'],
                    'updated_at': row['updated_at'],
                    'key_results': key_results
                })
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
            WHERE p.company_id = ?
            ORDER BY p.created_at ASC, p.id ASC
        ''', (company_id,))
        projects = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return projects
    
    def _create_company_project_with_cursor(self, cursor, company_id: int, project_data: Dict[str, Any]) -> Optional[int]:
        plan_id = project_data.get('plan_id')
        plan_type = project_data.get('plan_type')

        if plan_id:
            cursor.execute('SELECT company_id FROM plans WHERE id = ?', (plan_id,))
            plan_row = cursor.fetchone()
            if plan_row:
                # Converter para dict se for sqlite3.Row
                plan_dict = dict(plan_row) if hasattr(plan_row, 'keys') else {'company_id': plan_row[0]}
                if plan_dict.get('company_id') == company_id:
                    plan_type = plan_type or 'PEV'
                else:
                    cursor.execute('SELECT company_id FROM portfolios WHERE id = ?', (plan_id,))
                    portfolio_row = cursor.fetchone()
                    if portfolio_row:
                        portfolio_dict = dict(portfolio_row) if hasattr(portfolio_row, 'keys') else {'company_id': portfolio_row[0]}
                        if portfolio_dict.get('company_id') == company_id:
                            plan_type = plan_type or 'GRV'
                        else:
                            plan_id = None
                            if plan_type in ('PEV', 'GRV'):
                                plan_type = None
                    else:
                        plan_id = None
                        if plan_type in ('PEV', 'GRV'):
                            plan_type = None
            else:
                plan_id = None
                if plan_type in ('PEV', 'GRV'):
                    plan_type = None

        if plan_type:
            plan_type = str(plan_type).strip().upper()

        code, sequence = self._compute_next_project_code(cursor, company_id)

        activities_payload = project_data.get('activities')
        if isinstance(activities_payload, str):
            activities_json = activities_payload
        elif activities_payload is not None:
            activities_json = json.dumps(activities_payload, ensure_ascii=False)
        else:
            activities_json = None

        cursor.execute('''
            INSERT INTO company_projects (
                company_id, plan_id, plan_type, title, description, status, priority,
                owner, responsible_id, start_date, end_date,
                okr_area_ref, okr_reference, indicator_reference,
                activities, notes, code, code_sequence
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            company_id,
            plan_id,
            plan_type,
            project_data.get('title'),
            project_data.get('description'),
            project_data.get('status', 'planned'),
            project_data.get('priority'),
            project_data.get('owner'),
            project_data.get('responsible_id'),
            project_data.get('start_date'),
            project_data.get('end_date'),
            project_data.get('okr_area_ref'),
            project_data.get('okr_reference'),
            project_data.get('indicator_reference'),
            activities_json,
            project_data.get('notes'),
            code,
            sequence
        ))
        return cursor.lastrowid
    
    def create_company_project(self, company_id: int, project_data: Dict[str, Any]) -> Optional[int]:
        """Create a project linked to a company (plan optional)."""
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            project_id = self._create_company_project_with_cursor(cursor, company_id, project_data)
            conn.commit()
            return project_id
        except Exception as exc:
            print(f"Error creating company project: {exc}")
            if conn:
                try:
                    conn.rollback()
                except Exception:
                    pass
            return None
        finally:
            if conn:
                conn.close()
    
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
            WHERE p.plan_id = ?
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

            cursor.execute('SELECT company_id FROM plans WHERE id = ?', (plan_id,))
            plan_row = cursor.fetchone()
            if not plan_row or plan_row['company_id'] is None:
                conn.close()
                return False
            company_id = plan_row['company_id']
            
            cursor.execute('''
                INSERT INTO company_projects (
                    company_id, plan_id, title, description, status, priority,
                    owner, start_date, end_date, okr_area_ref, activities, notes
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            print(f"Error adding project: {e}")
            return False
    
    def update_project(self, project_id: int, project_data: Dict[str, Any]) -> bool:
        """Update existing project"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE company_projects SET 
                    title = ?, description = ?, status = ?, priority = ?, 
                    owner = ?, start_date = ?, end_date = ?, okr_area_ref = ?, 
                    activities = ?, notes = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
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
            print(f"Error updating project: {e}")
            return False
    
    def delete_project(self, project_id: int) -> bool:
        """Delete project"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute('DELETE FROM company_projects WHERE id = ?', (project_id,))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error deleting project: {e}")
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
                WHERE p.id = ?
            ''', (project_id,))
            row = cursor.fetchone()
            conn.close()
            return dict(row) if row else None
        except Exception as e:
            print(f"Error getting project: {e}")
            return None

    def get_company_project(self, company_id: int, project_id: int) -> Optional[Dict[str, Any]]:
        """Get project ensuring it belongs to the specified company"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT
                p.*,
                pl.name AS plan_name
            FROM company_projects p
            LEFT JOIN plans pl ON pl.id = p.plan_id
            WHERE p.id = ? AND p.company_id = ?
        ''', (project_id, company_id))
        row = cursor.fetchone()
        conn.close()
        if row:
            return dict(row)
        return None

    def list_company_meetings(self, company_id: int) -> List[Dict[str, Any]]:
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            self._ensure_meetings_schema(cursor)
            cursor.execute('''
                SELECT
                    m.*,
                    cp.title AS project_title,
                    cp.code AS project_code
                FROM meetings m
                LEFT JOIN company_projects cp ON cp.id = m.project_id
                WHERE m.company_id = ?
                ORDER BY
                    CASE WHEN m.scheduled_date IS NULL THEN 1 ELSE 0 END,
                    m.scheduled_date ASC,
                    CASE WHEN m.scheduled_time IS NULL THEN '23:59' ELSE m.scheduled_time END ASC,
                    m.created_at DESC
            ''', (company_id,))
            rows = cursor.fetchall()
            return [self._serialize_meeting_row(row) for row in rows]
        finally:
            conn.close()

    def get_meeting(self, meeting_id: int) -> Optional[Dict[str, Any]]:
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            self._ensure_meetings_schema(cursor)
            cursor.execute('''
                SELECT
                    m.*,
                    cp.title AS project_title,
                    cp.code AS project_code
                FROM meetings m
                LEFT JOIN company_projects cp ON cp.id = m.project_id
                WHERE m.id = ?
            ''', (meeting_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return self._serialize_meeting_row(row)
        finally:
            conn.close()

    def create_meeting(self, company_id: int, meeting_data: Dict[str, Any]) -> Optional[int]:
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            self._ensure_meetings_schema(cursor)

            project_id = meeting_data.get('project_id')
            project_payload = meeting_data.get('project')
            if not project_id and project_payload:
                project_id = self._create_company_project_with_cursor(cursor, company_id, project_payload)

            guests_json = self._encode_json_value(meeting_data.get('guests'))
            agenda_json = self._encode_json_value(meeting_data.get('agenda'))
            participants_json = self._encode_json_value(meeting_data.get('participants'))
            discussions_json = self._encode_json_value(meeting_data.get('discussions'))
            activities_json = self._encode_json_value(meeting_data.get('activities'))

            cursor.execute('''
                INSERT INTO meetings (
                    company_id, project_id, title,
                    scheduled_date, scheduled_time,
                    invite_notes, meeting_notes,
                    guests_json, agenda_json, participants_json,
                    discussions_json, activities_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                company_id,
                project_id,
                meeting_data.get('title'),
                meeting_data.get('scheduled_date'),
                meeting_data.get('scheduled_time'),
                meeting_data.get('invite_notes'),
                meeting_data.get('meeting_notes'),
                guests_json,
                agenda_json,
                participants_json,
                discussions_json,
                activities_json
            ))
            meeting_id = cursor.lastrowid
            conn.commit()
            return meeting_id
        except Exception as exc:
            print(f"Error creating meeting: {exc}")
            if conn:
                try:
                    conn.rollback()
                except Exception:
                    pass
            return None
        finally:
            if conn:
                conn.close()

    def update_meeting(self, meeting_id: int, meeting_data: Dict[str, Any]) -> bool:
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            self._ensure_meetings_schema(cursor)

            guests_json = self._encode_json_value(meeting_data.get('guests'))
            agenda_json = self._encode_json_value(meeting_data.get('agenda'))
            participants_json = self._encode_json_value(meeting_data.get('participants'))
            discussions_json = self._encode_json_value(meeting_data.get('discussions'))
            activities_json = self._encode_json_value(meeting_data.get('activities'))

            cursor.execute('''
                UPDATE meetings SET
                    title = COALESCE(?, title),
                    scheduled_date = COALESCE(?, scheduled_date),
                    scheduled_time = COALESCE(?, scheduled_time),
                    actual_date = COALESCE(?, actual_date),
                    actual_time = COALESCE(?, actual_time),
                    status = COALESCE(?, status),
                    invite_notes = COALESCE(?, invite_notes),
                    meeting_notes = COALESCE(?, meeting_notes),
                    guests_json = COALESCE(?, guests_json),
                    agenda_json = COALESCE(?, agenda_json),
                    participants_json = COALESCE(?, participants_json),
                    discussions_json = COALESCE(?, discussions_json),
                    activities_json = COALESCE(?, activities_json),
                    project_id = COALESCE(?, project_id),
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (
                meeting_data.get('title'),
                meeting_data.get('scheduled_date'),
                meeting_data.get('scheduled_time'),
                meeting_data.get('actual_date'),
                meeting_data.get('actual_time'),
                meeting_data.get('status'),
                meeting_data.get('invite_notes'),
                meeting_data.get('meeting_notes'),
                guests_json,
                agenda_json,
                participants_json,
                discussions_json,
                activities_json,
                meeting_data.get('project_id'),
                meeting_id
            ))
            conn.commit()
            return cursor.rowcount > 0
        except Exception as exc:
            print(f"Error updating meeting: {exc}")
            if conn:
                try:
                    conn.rollback()
                except Exception:
                    pass
            return False
        finally:
            if conn:
                conn.close()

    def delete_meeting(self, meeting_id: int) -> bool:
        """Delete a meeting"""
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            self._ensure_meetings_schema(cursor)
            cursor.execute('DELETE FROM meetings WHERE id = ?', (meeting_id,))
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
    def create_company(self, company_data: Dict[str, Any]) -> Optional[int]:
        """Create new company and return company ID"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO companies (name, client_code, legal_name, industry, size, description)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                company_data.get('name'),
                self._normalize_client_code(company_data.get('client_code')),
                company_data.get('legal_name'),
                company_data.get('industry'),
                company_data.get('size'),
                company_data.get('description')
            ))
            
            company_id = cursor.lastrowid
            conn.commit()
            conn.close()
            return company_id
        except Exception as e:
            print(f"Error creating company: {e}")
            return None
    
    def delete_company(self, company_id: int) -> bool:
        """Delete company by ID with all dependencies"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Habilitar foreign keys
            cursor.execute('PRAGMA foreign_keys = ON')
            
            # Verificar se a empresa existe
            cursor.execute('SELECT id FROM companies WHERE id = ?', (company_id,))
            if not cursor.fetchone():
                conn.close()
                return False
            
            # Lista de tabelas que referenciam companies (em ordem de dependência)
            dependent_tables = [
                'indicator_data',
                'indicator_goals', 
                'indicators',
                'indicator_groups',
                'occurrences',
                'process_instances',
                'meeting_agenda_items',
                'meetings',
                'user_logs',
                'company_projects',
                'portfolios',
                'employees',
                'processes',
                'macro_processes',
                'process_areas',
                'routines',
                'roles',
                'plans'
            ]
            
            # Deletar registros dependentes
            for table in dependent_tables:
                try:
                    # Verificar se a tabela tem coluna company_id
                    cursor.execute(f"PRAGMA table_info({table})")
                    columns = [row[1] for row in cursor.fetchall()]
                    if 'company_id' in columns:
                        cursor.execute(f'DELETE FROM {table} WHERE company_id = ?', (company_id,))
                        print(f"Deleted from {table}: {cursor.rowcount} records")
                except Exception as e:
                    print(f"Warning: Could not delete from {table}: {e}")
                    continue
            
            # Deletar a empresa
            cursor.execute('DELETE FROM companies WHERE id = ?', (company_id,))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error deleting company: {e}")
            return False
    
    # Plan creation
    def create_plan(self, plan_data: Dict[str, Any]) -> Optional[int]:
        """Create new plan and return plan ID"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Check if plan_mode column exists, if not, create it
            try:
                cursor.execute("PRAGMA table_info(plans)")
                columns = {row[1] for row in cursor.fetchall()}
                if 'plan_mode' not in columns:
                    cursor.execute('ALTER TABLE plans ADD COLUMN plan_mode TEXT DEFAULT "evolucao"')
                    conn.commit()
            except Exception as col_error:
                print(f"Warning: Could not check/add plan_mode column: {col_error}")
            
            cursor.execute('''
                INSERT INTO plans (company_id, name, description, start_date, end_date, status, plan_mode)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                plan_data.get('company_id'),
                plan_data.get('name'),
                plan_data.get('description'),
                plan_data.get('start_date'),
                plan_data.get('end_date'),
                plan_data.get('status', 'active'),
                plan_data.get('plan_mode', 'evolucao')
            ))
            
            plan_id = cursor.lastrowid
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
                SELECT * FROM interviews WHERE plan_id = ? ORDER BY created_at DESC
            ''', (plan_id,))
            
            interviews = []
            for row in cursor.fetchall():
                interviews.append({
                    'id': row[0],
                    'plan_id': row[1],
                    'participant_name': row[2],
                    'consultant_name': row[3],
                    'interview_date': row[4],
                    'format': row[5],
                    'notes': row[6],
                    'created_at': row[7],
                    'updated_at': row[8]
                })
            
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
                VALUES (?, ?, ?, ?, ?, ?)
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
            
            cursor.execute('SELECT * FROM interviews WHERE id = ?', (interview_id,))
            row = cursor.fetchone()
            
            conn.close()
            if row:
                return {
                    'id': row[0],
                    'plan_id': row[1],
                    'participant_name': row[2],
                    'consultant_name': row[3],
                    'interview_date': row[4],
                    'format': row[5],
                    'notes': row[6],
                    'created_at': row[7],
                    'updated_at': row[8]
                }
            return None
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
                    participant_name = ?, consultant_name = ?, interview_date = ?, 
                    format = ?, notes = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
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
            
            cursor.execute('DELETE FROM interviews WHERE id = ?', (interview_id,))
            
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
                SELECT * FROM plan_sections WHERE plan_id = ? AND section_name = ?
            ''', (plan_id, section_name))
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                result = {
                    'id': row[0],
                    'plan_id': row[1],
                    'section_name': row[2],
                    'status': row[3],
                    'closed_by': row[4],
                    'closed_at': row[5],
                    'notes': row[6],
                    'created_at': row[7],
                    'updated_at': row[8]
                }
                # Add adjustments field if it exists
                if len(row) > 9:
                    result['adjustments'] = row[9]
                return result
            return None
        except Exception as e:
            print(f"Error getting section status: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def update_section_status(self, plan_id: int, section_name: str, status: str, closed_by: str = None, notes: str = None) -> bool:
        """Update section status"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Verificar se já existe um registro
            cursor.execute('SELECT id FROM plan_sections WHERE plan_id = ? AND section_name = ?', (plan_id, section_name))
            existing = cursor.fetchone()
            
            if existing:
                # Para seções que armazenam dados JSON no campo notes, preservar os dados existentes
                json_sections = [
                    'directionals-approvals', 
                    'area-okr-workshop', 
                    'final-area-okr',
                    'workshop-final-okr',
                    'okr-approvals'
                ]
                
                if section_name in json_sections:
                    # Buscar dados existentes
                    import json
                    cursor.execute('SELECT notes FROM plan_sections WHERE plan_id = ? AND section_name = ?', (plan_id, section_name))
                    existing_data = cursor.fetchone()
                    
                    if existing_data and existing_data[0]:
                        # Preservar dados existentes e adicionar motivo da conclusão se fornecido
                        try:
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
                        status = ?, closed_by = ?, closed_at = ?, notes = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE plan_id = ? AND section_name = ?
                ''', (status, closed_by, 
                      'CURRENT_TIMESTAMP' if status == 'closed' else None, 
                      notes, plan_id, section_name))
            else:
                # Criar novo registro
                cursor.execute('''
                    INSERT INTO plan_sections (plan_id, section_name, status, closed_by, closed_at, notes)
                    VALUES (?, ?, ?, ?, ?, ?)
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
            print(f"DEBUG DB: update_section_consultant_notes called - plan_id: {plan_id}, section_name: {section_name}")
            print(f"DEBUG DB: consultant_notes length: {len(consultant_notes) if consultant_notes else 0}")
            
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Verificar se já existe registro
            cursor.execute('''
                SELECT id FROM plan_sections 
                WHERE plan_id = ? AND section_name = ?
            ''', (plan_id, section_name))
            
            existing = cursor.fetchone()
            print(f"DEBUG DB: Existing record found: {existing is not None}")
            
            if existing:
                # Atualizar registro existente
                cursor.execute('''
                    UPDATE plan_sections 
                    SET notes = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE plan_id = ? AND section_name = ?
                ''', (consultant_notes, plan_id, section_name))
                print(f"DEBUG DB: Updated existing record")
            else:
                # Criar novo registro
                cursor.execute('''
                    INSERT INTO plan_sections (plan_id, section_name, status, notes)
                    VALUES (?, ?, 'open', ?)
                ''', (plan_id, section_name, consultant_notes))
                print(f"DEBUG DB: Created new record")
            
            conn.commit()
            conn.close()
            print(f"DEBUG DB: Database operation completed successfully")
            return True
        except Exception as e:
            print(f"DEBUG DB: Error updating section consultant notes: {e}")
            return False
    
    def update_section_adjustments(self, plan_id: int, section_name: str, adjustments: str) -> bool:
        """Update section adjustments"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # First, ensure the plan_sections table has an adjustments column
            # Check if column exists, if not add it
            cursor.execute("PRAGMA table_info(plan_sections)")
            columns = [column[1] for column in cursor.fetchall()]
            if 'adjustments' not in columns:
                cursor.execute('ALTER TABLE plan_sections ADD COLUMN adjustments TEXT')
            
            # Verificar se já existe registro
            cursor.execute('''
                SELECT id FROM plan_sections 
                WHERE plan_id = ? AND section_name = ?
            ''', (plan_id, section_name))
            
            existing = cursor.fetchone()
            
            if existing:
                # Atualizar registro existente
                cursor.execute('''
                    UPDATE plan_sections 
                    SET adjustments = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE plan_id = ? AND section_name = ?
                ''', (adjustments, plan_id, section_name))
            else:
                # Criar novo registro
                cursor.execute('''
                    INSERT INTO plan_sections (plan_id, section_name, status, adjustments)
                    VALUES (?, ?, 'open', ?)
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
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM vision_records WHERE plan_id = ? ORDER BY created_at DESC
            ''', (plan_id,))
            
            records = []
            for row in cursor.fetchall():
                records.append({
                    'id': row[0],
                    'plan_id': row[1],
                    'participants': row[2] or '',  # Texto livre
                    'consultants': row[3] or '',   # Texto livre
                    'vision_date': row[4],
                    'format': row[5],
                    'notes': row[6],
                    'created_at': row[7],
                    'updated_at': row[8]
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
                VALUES (?, ?, ?, ?, ?, ?)
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
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM vision_records WHERE id = ?', (vision_id,))
            row = cursor.fetchone()
            
            conn.close()
            if row:
                return {
                    'id': row[0],
                    'plan_id': row[1],
                    'participants': row[2] or '',
                    'consultants': row[3] or '',
                    'vision_date': row[4],
                    'format': row[5],
                    'notes': row[6],
                    'created_at': row[7],
                    'updated_at': row[8]
                }
            return None
        except Exception as e:
            print(f"Error getting vision record: {e}")
            return None
    
    def update_vision_record(self, vision_id: int, vision_data: Dict[str, Any]) -> bool:
        """Update vision record data"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE vision_records SET 
                    participants = ?, consultants = ?, vision_date = ?, 
                    format = ?, notes = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
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
            
            cursor.execute('DELETE FROM vision_records WHERE id = ?', (vision_id,))
            
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
                SELECT * FROM market_records WHERE plan_id = ? ORDER BY created_at DESC
            ''', (plan_id,))
            
            records = []
            for row in cursor.fetchall():
                records.append({
                    'id': row[0],
                    'plan_id': row[1],
                    'participants': row[2] or '',  # Texto livre
                    'consultants': row[3] or '',   # Texto livre
                    'market_date': row[4],
                    'format': row[5],
                    'global_context': row[6],
                    'sector_context': row[7],
                    'market_size': row[8],
                    'growth_space': row[9],
                    'threats': row[10],
                    'consumer_behavior': row[11],
                    'competition': row[12],
                    'notes': row[13],
                    'created_at': row[14],
                    'updated_at': row[15]
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
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            
            cursor.execute('SELECT * FROM market_records WHERE id = ?', (market_id,))
            row = cursor.fetchone()
            
            conn.close()
            if row:
                return {
                    'id': row[0],
                    'plan_id': row[1],
                    'participants': row[2] or '',
                    'consultants': row[3] or '',
                    'market_date': row[4],
                    'format': row[5],
                    'global_context': row[6],
                    'sector_context': row[7],
                    'market_size': row[8],
                    'growth_space': row[9],
                    'threats': row[10],
                    'consumer_behavior': row[11],
                    'competition': row[12],
                    'notes': row[13],
                    'created_at': row[14],
                    'updated_at': row[15]
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
                    participants = ?, consultants = ?, market_date = ?, 
                    format = ?, global_context = ?, sector_context = ?, 
                    market_size = ?, growth_space = ?, threats = ?, 
                    consumer_behavior = ?, competition = ?, notes = ?, 
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
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
            
            cursor.execute('DELETE FROM market_records WHERE id = ?', (market_id,))
            
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
                WHERE plan_id = ?
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
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                WHERE id = ?
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
                SET participants = ?, consultants = ?, company_date = ?, 
                    bsc_financial = ?, bsc_commercial = ?, bsc_process = ?, 
                    bsc_learning = ?, tri_commercial = ?, tri_adm_fin = ?, 
                    tri_operational = ?, notes = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
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
            
            cursor.execute('DELETE FROM company_records WHERE id = ?', (company_id,))
            
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
                WHERE plan_id = ?
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
                VALUES (?, ?, ?, ?, ?, ?)
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
                WHERE id = ?
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
                SET topic = ?, description = ?, consensus = ?, priority = ?, notes = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
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
            
            cursor.execute('DELETE FROM alignment_records WHERE id = ?', (alignment_id,))
            
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
                WHERE plan_id = ?
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
                VALUES (?, ?, ?, ?, ?, ?)
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
                WHERE id = ?
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
                SET issue = ?, description = ?, severity = ?, impact = ?, notes = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
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
            
            cursor.execute('DELETE FROM misalignment_records WHERE id = ?', (misalignment_id,))
            
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
                SELECT id, title, description, status, owner, notes, created_at, updated_at, type, priority
                FROM directional_records 
                WHERE plan_id = ?
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
                    'updated_at': row[7],
                    'type': row[8],
                    'priority': row[9]
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
                WHERE plan_id = ? AND (status = 'final' OR status = 'approved')
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
                INSERT INTO directional_records (plan_id, title, description, status, owner, notes, type, priority)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                plan_id,
                directional_data.get('title', ''),
                directional_data.get('description', ''),
                directional_data.get('status', 'draft'),
                directional_data.get('owner'),
                directional_data.get('notes'),
                directional_data.get('type'),
                directional_data.get('priority')
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
                SELECT id, title, description, status, owner, notes, created_at, updated_at, type, priority
                FROM directional_records 
                WHERE id = ?
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
                    'updated_at': row[7],
                    'type': row[8],
                    'priority': row[9]
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
                SET title = ?, description = ?, status = ?, owner = ?, notes = ?, type = ?, priority = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (
                directional_data.get('title', ''),
                directional_data.get('description', ''),
                directional_data.get('status', 'draft'),
                directional_data.get('owner'),
                directional_data.get('notes'),
                directional_data.get('type'),
                directional_data.get('priority'),
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
            
            cursor.execute('DELETE FROM directional_records WHERE id = ?', (directional_id,))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error deleting directional record: {e}")
            return False

    # Investment contributions operations (new structure)
    def get_plan_investment_categories(self, plan_id: int) -> List[Dict[str, Any]]:
        """Get investment categories (Capital de Giro, Imobilizado)"""
        # TODO: Implementar quando houver tabela de categorias de investimento
        return []

    def get_plan_investment_items(self, category_id: int) -> List[Dict[str, Any]]:
        """Get investment items for a category"""
        # TODO: Implementar quando houver tabela de itens de investimento
        return []

    def list_plan_investment_contributions(self, item_id: int) -> List[Dict[str, Any]]:
        """List investment contributions for an item"""
        # TODO: Implementar quando houver tabela de contribuições de investimento
        return []

    def create_plan_investment_contribution(self, item_id: int, data: Dict[str, Any]) -> int:
        """Create an investment contribution (aporte)"""
        # TODO: Implementar quando houver tabela de contribuições de investimento
        return 0

    def update_plan_investment_contribution(self, contribution_id: int, data: Dict[str, Any]) -> bool:
        """Update an investment contribution"""
        # TODO: Implementar quando houver tabela de contribuições de investimento
        return True

    def delete_plan_investment_contribution(self, contribution_id: int) -> bool:
        """Delete an investment contribution"""
        # TODO: Implementar quando houver tabela de contribuições de investimento
        return True

    def list_plan_funding_sources(self, plan_id: int) -> List[Dict[str, Any]]:
        """List funding sources (Fornecedores, Empréstimos, Sócios)"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, plan_id, source_type, source_name, amount, notes, created_at
                FROM plan_finance_sources
                WHERE plan_id = ?
                ORDER BY created_at DESC
            ''', (plan_id,))
            rows = cursor.fetchall()
            conn.close()
            return [dict(row) for row in rows]
        except Exception as e:
            print(f"Error listing funding sources: {e}")
            return []

    def create_plan_funding_source(self, plan_id: int, data: Dict[str, Any]) -> int:
        """Create a funding source"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO plan_finance_sources (plan_id, source_type, source_name, amount, notes, created_at)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ''', (
                plan_id,
                data.get('source_type', ''),
                data.get('source_name', ''),
                data.get('amount', 0),
                data.get('notes', '')
            ))
            new_id = cursor.lastrowid
            conn.commit()
            conn.close()
            return new_id
        except Exception as e:
            print(f"Error creating funding source: {e}")
            return 0

    def update_plan_funding_source(self, source_id: int, plan_id: int, data: Dict[str, Any]) -> bool:
        """Update a funding source"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE plan_finance_sources
                SET source_type = ?, source_name = ?, amount = ?, notes = ?
                WHERE id = ? AND plan_id = ?
            ''', (
                data.get('source_type', ''),
                data.get('source_name', ''),
                data.get('amount', 0),
                data.get('notes', ''),
                source_id,
                plan_id
            ))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error updating funding source: {e}")
            return False

    def delete_plan_funding_source(self, source_id: int, plan_id: int) -> bool:
        """Delete a funding source"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                DELETE FROM plan_finance_sources
                WHERE id = ? AND plan_id = ?
            ''', (source_id, plan_id))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error deleting funding source: {e}")
            return False

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
            cursor.execute('SELECT * FROM ai_agents WHERE id = ?', (agent_id,))
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
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                1 if str(agent_data.get('cache_enabled', 'true')).lower() in ('1','true','yes') else 0,
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
                    name = ?, description = ?, version = ?, status = ?, page = ?, section = ?, button_text = ?,
                    required_data = ?, optional_data = ?, prompt_template = ?, format_type = ?, output_field = ?,
                    response_template = ?, timeout = ?, max_retries = ?, execution_mode = ?, cache_enabled = ?,
                    updated_at = ?
                WHERE id = ?
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
                1 if str(agent_data.get('cache_enabled', 'true')).lower() in ('1','true','yes') else 0,
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
            cursor.execute('DELETE FROM ai_agents WHERE id = ?', (agent_id,))
            conn.commit()
            deleted = cursor.rowcount
            conn.close()
            return deleted > 0
        except Exception as e:
            print(f"Error deleting AI agent: {e}")
            return False

    # Workshop Discussions CRUD Operations
    def get_workshop_discussions(self, plan_id: int, section_type: str = 'preliminary') -> Optional[Dict[str, Any]]:
        """Get workshop discussions for a plan and section type"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id, content, created_at, updated_at
                FROM workshop_discussions 
                WHERE plan_id = ? AND section_type = ?
                ORDER BY updated_at DESC
                LIMIT 1
            ''', (plan_id, section_type))
            
            result = cursor.fetchone()
            conn.close()
            
            if result:
                return {
                    'id': result[0],
                    'content': result[1],
                    'created_at': result[2],
                    'updated_at': result[3]
                }
            return None
            
        except Exception as e:
            print(f"Error getting workshop discussions: {e}")
            return None

    def save_workshop_discussions(self, plan_id: int, section_type: str, content: str) -> bool:
        """Save workshop discussions"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Check if discussion already exists
            cursor.execute('''
                SELECT id FROM workshop_discussions 
                WHERE plan_id = ? AND section_type = ?
            ''', (plan_id, section_type))
            
            existing = cursor.fetchone()
            
            if existing:
                # Update existing discussion
                cursor.execute('''
                    UPDATE workshop_discussions 
                    SET content = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (content, existing[0]))
            else:
                # Create new discussion
                cursor.execute('''
                    INSERT INTO workshop_discussions (plan_id, section_type, content)
                    VALUES (?, ?, ?)
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
            
            cursor.execute('''
                DELETE FROM workshop_discussions 
                WHERE plan_id = ? AND section_type = ?
            ''', (plan_id, section_type))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            print(f"Error deleting workshop discussions: {e}")
            return False

    # ===== ROTINAS - CRUD =====

    def get_routines(self, company_id: int) -> List[Dict[str, Any]]:
        """Get all routines for a company"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM routines 
            WHERE company_id = ? AND is_active = 1
            ORDER BY name
        ''', (company_id,))
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def get_routine(self, routine_id: int) -> Optional[Dict[str, Any]]:
        """Get a specific routine by ID"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM routines WHERE id = ?', (routine_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    def create_routine(self, company_id: int, name: str, description: str = '') -> Optional[int]:
        """Create a new routine"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO routines (company_id, name, description)
                VALUES (?, ?, ?)
            ''', (company_id, name, description))
            new_id = cursor.lastrowid
            conn.commit()
            conn.close()
            return new_id
        except Exception as e:
            print(f"Error creating routine: {e}")
            return None

    def update_routine(self, routine_id: int, name: str, description: str) -> bool:
        """Update a routine"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE routines 
                SET name = ?, description = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
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
            cursor.execute('UPDATE routines SET is_active = 0 WHERE id = ?', (routine_id,))
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
            WHERE routine_id = ? AND is_active = 1
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
                VALUES (?, ?, ?, ?, ?)
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
                SET trigger_type = ?, trigger_value = ?, deadline_value = ?, 
                    deadline_unit = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
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
            cursor.execute('UPDATE routine_triggers SET is_active = 0 WHERE id = ?', (trigger_id,))
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
                WHERE r.company_id = ? AND rt.status = ?
                ORDER BY rt.deadline_date ASC
            ''', (company_id, status))
        else:
            cursor.execute('''
                SELECT rt.* FROM routine_tasks rt
                JOIN routines r ON r.id = rt.routine_id
                WHERE r.company_id = ?
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
                VALUES (?, ?, ?, ?, ?, ?)
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
                    SET status = ?, completed_at = CURRENT_TIMESTAMP, completed_by = ?, 
                        notes = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (status, completed_by, notes, task_id))
            else:
                cursor.execute('''
                    UPDATE routine_tasks 
                    SET status = ?, notes = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (status, notes, task_id))
            
            conn.commit()
            conn.close()
            return cursor.rowcount > 0
        except Exception as e:
            print(f"Error updating routine task status: {e}")
            return False

    def get_overdue_tasks(self, company_id: int) -> List[Dict[str, Any]]:
        """Get all overdue tasks for a company"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT rt.* FROM routine_tasks rt
            JOIN routines r ON r.id = rt.routine_id
            WHERE r.company_id = ? 
            AND rt.status IN ('pending', 'in_progress')
            AND rt.deadline_date < CURRENT_TIMESTAMP
            ORDER BY rt.deadline_date ASC
        ''', (company_id,))
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def get_upcoming_tasks(self, company_id: int, days: int = 7) -> List[Dict[str, Any]]:
        """Get upcoming tasks for the next N days"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT rt.* FROM routine_tasks rt
            JOIN routines r ON r.id = rt.routine_id
            WHERE r.company_id = ? 
            AND rt.status IN ('pending', 'in_progress')
            AND rt.deadline_date >= CURRENT_TIMESTAMP
            AND rt.deadline_date <= datetime(CURRENT_TIMESTAMP, '+' || ? || ' days')
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
            WHERE id = ?
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
        cursor.execute("SELECT id FROM ai_agents WHERE id = ?", (agent_config['id'],))
        if cursor.fetchone():
            conn.close()
            return False
        
        cursor.execute("""
            INSERT INTO ai_agents (
                id, name, description, version, status, page, section, button_text,
                required_data, optional_data, prompt_template, format_type,
                output_field, response_template, timeout, max_retries,
                execution_mode, cache_enabled, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                name = ?, description = ?, version = ?, status = ?, page = ?,
                section = ?, button_text = ?, required_data = ?, optional_data = ?,
                prompt_template = ?, format_type = ?, output_field = ?,
                response_template = ?, timeout = ?, max_retries = ?,
                execution_mode = ?, cache_enabled = ?, updated_at = ?
            WHERE id = ?
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
            cursor.execute("DELETE FROM agent_integrations WHERE agent_id = ?", (agent_id,))
        except Exception:
            pass
        cursor.execute("DELETE FROM ai_agents WHERE id = ?", (agent_id,))
        
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
    conn = sqlite3.connect('pevapp22.db')
    conn.row_factory = sqlite3.Row
    return conn

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
        cursor.execute("SELECT id, name, provider, type, auth_type, config, created_at, updated_at FROM integrations WHERE id = ?", (integration_id,))
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
            VALUES (?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))
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
            UPDATE integrations SET name = ?, provider = ?, type = ?, auth_type = ?, config = ?, updated_at = datetime('now')
            WHERE id = ?
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
        cursor.execute("DELETE FROM agent_integrations WHERE integration_id = ?", (integration_id,))
        cursor.execute("DELETE FROM integrations WHERE id = ?", (integration_id,))
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
        cursor.execute("DELETE FROM agent_integrations WHERE agent_id = ?", (agent_id,))
        for iid in (integration_ids or []):
            cursor.execute("INSERT OR IGNORE INTO agent_integrations (agent_id, integration_id) VALUES (?, ?)", (agent_id, iid))
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
            WHERE ai.agent_id = ?
        """, (agent_id,))
        rows = cursor.fetchall()
        conn.close()
        return [ {'id': r[0], 'name': r[1], 'provider': r[2], 'type': r[3], 'auth_type': r[4]} for r in rows ]
    except Exception as e:
        print(f"Error getting agent integrations: {e}")
        return []

    # ===== ROTINAS - CRUD =====

    def get_routines(self, company_id: int) -> List[Dict[str, Any]]:
        """Get all routines for a company"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM routines 
            WHERE company_id = ? AND is_active = 1
            ORDER BY name
        ''', (company_id,))
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def get_routine(self, routine_id: int) -> Optional[Dict[str, Any]]:
        """Get a specific routine by ID"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM routines WHERE id = ?', (routine_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    def create_routine(self, company_id: int, name: str, description: str = '') -> Optional[int]:
        """Create a new routine"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO routines (company_id, name, description)
                VALUES (?, ?, ?)
            ''', (company_id, name, description))
            new_id = cursor.lastrowid
            conn.commit()
            conn.close()
            return new_id
        except Exception as e:
            print(f"Error creating routine: {e}")
            return None

    def update_routine(self, routine_id: int, name: str, description: str) -> bool:
        """Update a routine"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE routines 
                SET name = ?, description = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
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
            cursor.execute('UPDATE routines SET is_active = 0 WHERE id = ?', (routine_id,))
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
            WHERE routine_id = ? AND is_active = 1
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
                VALUES (?, ?, ?, ?, ?)
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
                SET trigger_type = ?, trigger_value = ?, deadline_value = ?, 
                    deadline_unit = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
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
            cursor.execute('UPDATE routine_triggers SET is_active = 0 WHERE id = ?', (trigger_id,))
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
                WHERE r.company_id = ? AND rt.status = ?
                ORDER BY rt.deadline_date ASC
            ''', (company_id, status))
        else:
            cursor.execute('''
                SELECT rt.* FROM routine_tasks rt
                JOIN routines r ON r.id = rt.routine_id
                WHERE r.company_id = ?
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
                VALUES (?, ?, ?, ?, ?, ?)
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
                    SET status = ?, completed_at = CURRENT_TIMESTAMP, completed_by = ?, 
                        notes = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (status, completed_by, notes, task_id))
            else:
                cursor.execute('''
                    UPDATE routine_tasks 
                    SET status = ?, notes = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (status, notes, task_id))
            
            conn.commit()
            conn.close()
            return cursor.rowcount > 0
        except Exception as e:
            print(f"Error updating routine task status: {e}")
            return False

    def get_overdue_tasks(self, company_id: int) -> List[Dict[str, Any]]:
        """Get all overdue tasks for a company"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT rt.* FROM routine_tasks rt
            JOIN routines r ON r.id = rt.routine_id
            WHERE r.company_id = ? 
            AND rt.status IN ('pending', 'in_progress')
            AND rt.deadline_date < CURRENT_TIMESTAMP
            ORDER BY rt.deadline_date ASC
        ''', (company_id,))
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def get_upcoming_tasks(self, company_id: int, days: int = 7) -> List[Dict[str, Any]]:
        """Get upcoming tasks for the next N days"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT rt.* FROM routine_tasks rt
            JOIN routines r ON r.id = rt.routine_id
            WHERE r.company_id = ? 
            AND rt.status IN ('pending', 'in_progress')
            AND rt.deadline_date >= CURRENT_TIMESTAMP
            AND rt.deadline_date <= datetime(CURRENT_TIMESTAMP, '+' || ? || ' days')
            ORDER BY rt.deadline_date ASC
        ''', (company_id, days))
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]


# ===== Module-level exports (for backward compatibility) =====
