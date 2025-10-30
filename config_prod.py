"""
Configuração de Produção para GestaoVersus (APP30)
Seguindo TECH_STACK.md e CODING_STANDARDS.md
"""

import os
from datetime import timedelta

from utils.env_helpers import normalize_database_url


class ProductionConfig:
    """Configuração para ambiente de produção."""
    
    # ===== AMBIENTE =====
    ENV = 'production'
    DEBUG = False
    TESTING = False
    
    # ===== APLICAÇÃO =====
    SECRET_KEY = os.getenv('SECRET_KEY')
    if not SECRET_KEY:
        raise ValueError("SECRET_KEY não definida em produção!")
    
    # ===== BANCO DE DADOS =====
    _prod_database_url = normalize_database_url(os.getenv('DATABASE_URL'))
    if not _prod_database_url:
        raise ValueError("DATABASE_URL não definida em produção!")
    SQLALCHEMY_DATABASE_URI = _prod_database_url

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 10,
        'pool_recycle': 3600,
        'pool_pre_ping': True,
        'max_overflow': 20
    }
    
    # ===== SESSÃO =====
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = timedelta(hours=1)
    SESSION_COOKIE_NAME = 'gestaoversos_session'
    
    # ===== SEGURANÇA =====
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = None
    
    # ===== UPLOAD =====
    UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', '/app/uploads')
    MAX_CONTENT_LENGTH = int(os.getenv('MAX_CONTENT_LENGTH', 52428800))  # 50MB
    ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'gif', 'doc', 'docx', 'xls', 'xlsx'}
    
    # ===== EMAIL =====
    MAIL_SERVER = os.getenv('MAIL_SERVER')
    MAIL_PORT = int(os.getenv('MAIL_PORT', 587))
    MAIL_USE_TLS = os.getenv('MAIL_USE_TLS', 'True').lower() == 'true'
    MAIL_USE_SSL = os.getenv('MAIL_USE_SSL', 'False').lower() == 'true'
    MAIL_USERNAME = os.getenv('MAIL_USERNAME')
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.getenv('MAIL_DEFAULT_SENDER', 'noreply@congigr.com')
    
    # ===== REDIS =====
    REDIS_URL = os.getenv('REDIS_URL', 'redis://redis:6379/0')
    
    # ===== CELERY =====
    CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', REDIS_URL)
    CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND', REDIS_URL)
    
    # ===== IA / OPENAI =====
    AI_PROVIDER = os.getenv('AI_PROVIDER', 'openai')
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    AI_MODEL = os.getenv('AI_MODEL', 'gpt-4')
    AI_MAX_TOKENS = int(os.getenv('AI_MAX_TOKENS', 2000))
    
    # ===== WHATSAPP =====
    WHATSAPP_PROVIDER = os.getenv('WHATSAPP_PROVIDER', 'z-api')
    WHATSAPP_API_KEY = os.getenv('WHATSAPP_API_KEY')
    WHATSAPP_INSTANCE_ID = os.getenv('WHATSAPP_INSTANCE_ID')
    
    # ===== BACKUP =====
    AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
    AWS_REGION = os.getenv('AWS_REGION', 'us-east-1')
    S3_BUCKET = os.getenv('S3_BUCKET')
    
    GCS_BUCKET = os.getenv('GCS_BUCKET')
    GOOGLE_APPLICATION_CREDENTIALS = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
    
    BACKUP_DIR = os.getenv('BACKUP_DIR', '/app/backups')
    BACKUP_RETENTION_DAYS = int(os.getenv('BACKUP_RETENTION_DAYS', 30))
    
    # ===== LOGS =====
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_DIR = os.getenv('LOG_DIR', '/app/logs')
    LOG_MAX_BYTES = int(os.getenv('LOG_MAX_BYTES', 10485760))  # 10MB
    LOG_BACKUP_COUNT = int(os.getenv('LOG_BACKUP_COUNT', 10))
    
    # ===== DOMÍNIO =====
    DOMAIN = os.getenv('DOMAIN', 'congigr.com')
    ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', 'congigr.com,www.congigr.com').split(',')
    
    # ===== RATE LIMITING =====
    RATELIMIT_STORAGE_URL = REDIS_URL
    RATELIMIT_STRATEGY = 'fixed-window'
    
    # ===== MONITORING =====
    SENTRY_DSN = os.getenv('SENTRY_DSN')
    ENABLE_METRICS = os.getenv('ENABLE_METRICS', 'True').lower() == 'true'


