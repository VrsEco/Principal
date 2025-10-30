"""
Configuração de Desenvolvimento para GestaoVersus (APP30)
Seguindo TECH_STACK.md e CODING_STANDARDS.md
"""

import os
from datetime import timedelta

from utils.env_helpers import normalize_database_url


class DevelopmentConfig:
    """Configuração para ambiente de desenvolvimento."""
    
    # ===== AMBIENTE =====
    ENV = 'development'
    DEBUG = True
    TESTING = False
    
    # ===== APLICAÇÃO =====
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-not-for-production')
    
    # ===== BANCO DE DADOS =====
    # APP30: Sempre usar PostgreSQL (migração completa concluída)
    _current_database_url = normalize_database_url(os.getenv('DATABASE_URL'))
    if not _current_database_url:
        _current_database_url = normalize_database_url(os.getenv('DEV_DATABASE_URL'))
    SQLALCHEMY_DATABASE_URI = _current_database_url or 'postgresql://postgres:*Paraiso1978@localhost:5432/bd_app_versus'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = True  # Ver queries no console
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 5,
        'pool_recycle': 3600,
    }
    
    # ===== SESSÃO =====
    SESSION_COOKIE_SECURE = False  # Desenvolvimento sem HTTPS
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = timedelta(days=1)
    SESSION_COOKIE_NAME = 'gestaoversos_dev_session'
    
    # ===== SEGURANÇA =====
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = None
    
    # ===== UPLOAD =====
    UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', './uploads')
    MAX_CONTENT_LENGTH = 52428800  # 50MB
    ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'gif', 'doc', 'docx', 'xls', 'xlsx'}
    
    # ===== EMAIL (Mock) =====
    MAIL_SERVER = os.getenv('MAIL_SERVER', 'localhost')
    MAIL_PORT = int(os.getenv('MAIL_PORT', 1025))
    MAIL_USE_TLS = False
    MAIL_USE_SSL = False
    MAIL_USERNAME = None
    MAIL_PASSWORD = None
    MAIL_DEFAULT_SENDER = 'dev@localhost'
    
    # ===== REDIS (Opcional em dev) =====
    REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6380/0')
    
    # ===== CELERY (Opcional em dev) =====
    CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', REDIS_URL)
    CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND', REDIS_URL)
    CELERY_TASK_ALWAYS_EAGER = True  # Executar tarefas sincronamente em dev
    
    # ===== IA / OPENAI (Mock) =====
    AI_PROVIDER = os.getenv('AI_PROVIDER', 'local')
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', 'dev-openai-key')
    AI_MODEL = 'gpt-3.5-turbo'
    AI_MAX_TOKENS = 1000
    
    # ===== WHATSAPP (Mock) =====
    WHATSAPP_PROVIDER = os.getenv('WHATSAPP_PROVIDER', 'local')
    WHATSAPP_API_KEY = 'dev-key'
    WHATSAPP_INSTANCE_ID = 'dev-instance'
    
    # ===== BACKUP =====
    BACKUP_DIR = os.getenv('BACKUP_DIR', './backups')
    BACKUP_RETENTION_DAYS = 7
    
    # ===== LOGS =====
    LOG_LEVEL = 'DEBUG'
    LOG_DIR = os.getenv('LOG_DIR', './logs')
    LOG_MAX_BYTES = 10485760  # 10MB
    LOG_BACKUP_COUNT = 5
    
    # ===== DOMÍNIO =====
    DOMAIN = 'localhost:5002'
    ALLOWED_HOSTS = ['localhost', '127.0.0.1']
    
    # ===== MONITORING =====
    ENABLE_METRICS = False


