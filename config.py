import os
from datetime import timedelta
from dotenv import load_dotenv
from urllib.parse import quote_plus

from utils.env_helpers import normalize_database_url

load_dotenv()


class Config:
    """Base configuration class"""

    SECRET_KEY = os.environ.get("SECRET_KEY") or "dev-secret-key-change-in-production"
    # IMPORTANTE: PostgreSQL como padrão (conforme APP30 migrado)
    # ✅ FIX: URL encoding na senha para evitar problemas com caracteres especiais (*)
    _default_password = quote_plus("*Paraiso1978")
    _env_database_url = normalize_database_url(os.environ.get("DATABASE_URL"))
    SQLALCHEMY_DATABASE_URI = (
        _env_database_url
        or f"postgresql://postgres:{_default_password}@localhost:5432/bd_app_versus"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Authentication
    LOGIN_DISABLED = os.environ.get("LOGIN_DISABLED", "False").lower() == "true"
    REMEMBER_COOKIE_DURATION = timedelta(
        days=7
    )  # Reduzido de 30 para 7 dias por segurança

    # Session Configuration (Segurança)
    SESSION_COOKIE_SECURE = (
        os.environ.get("SESSION_COOKIE_SECURE", "False").lower() == "true"
    )  # True em produção com HTTPS
    SESSION_COOKIE_HTTPONLY = True  # Previne acesso via JavaScript (XSS protection)
    SESSION_COOKIE_SAMESITE = "Lax"  # Proteção contra CSRF
    PERMANENT_SESSION_LIFETIME = timedelta(
        hours=24
    )  # Sessão expira em 24h se não marcar "lembrar-me"

    # Email Configuration
    MAIL_SERVER = os.environ.get("MAIL_SERVER")
    MAIL_PORT = int(os.environ.get("MAIL_PORT") or 587)
    MAIL_USE_TLS = os.environ.get("MAIL_USE_TLS", "true").lower() == "true"
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD")
    MAIL_DEFAULT_SENDER = os.environ.get("MAIL_DEFAULT_SENDER")

    # File Uploads
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    UPLOAD_FOLDER = os.environ.get("UPLOAD_FOLDER") or "uploads"
    ALLOWED_EXTENSIONS = {"pdf", "png", "jpg", "jpeg", "gif"}

    # AI Integration
    AI_PROVIDER = os.environ.get("AI_PROVIDER", "openai")  # openai, anthropic, local
    AI_API_KEY = os.environ.get("AI_API_KEY")
    AI_WEBHOOK_URL = os.environ.get("AI_WEBHOOK_URL")

    # WhatsApp Integration
    WHATSAPP_PROVIDER = os.environ.get(
        "WHATSAPP_PROVIDER", "z-api"
    )  # z-api, twilio, webhook
    WHATSAPP_API_KEY = os.environ.get("WHATSAPP_API_KEY")
    WHATSAPP_WEBHOOK_URL = os.environ.get("WHATSAPP_WEBHOOK_URL")

    # Redis for Celery
    REDIS_URL = os.environ.get("REDIS_URL") or "redis://localhost:6379/0"
    CELERY_BROKER_URL = REDIS_URL
    CELERY_RESULT_BACKEND = REDIS_URL

    # PDF Generation
    PDF_TEMP_FOLDER = os.environ.get("PDF_TEMP_FOLDER") or "temp_pdfs"

    # Rate Limiting
    RATELIMIT_STORAGE_URL = REDIS_URL


class DevelopmentConfig(Config):
    """Development configuration"""

    DEBUG = True
    TEMPLATES_AUTO_RELOAD = True  # Recarregar templates automaticamente
    SEND_FILE_MAX_AGE_DEFAULT = 0  # Sem cache de arquivos estáticos
    # IMPORTANTE: PostgreSQL como padrão (conforme APP30 migrado)
    # ✅ FIX: URL encoding na senha para evitar problemas com caracteres especiais (*)
    _dev_password = quote_plus("*Paraiso1978")
    _dev_database_url = normalize_database_url(os.environ.get("DEV_DATABASE_URL"))
    SQLALCHEMY_DATABASE_URI = (
        _dev_database_url
        or f"postgresql://postgres:{_dev_password}@localhost:5432/bd_app_versus"
    )


class ProductionConfig(Config):
    """Production configuration"""

    DEBUG = False
    _prod_database_url = normalize_database_url(os.environ.get("DATABASE_URL"))
    SQLALCHEMY_DATABASE_URI = (
        _prod_database_url or "postgresql://user:password@localhost/bd_app_versus"
    )


class TestingConfig(Config):
    """Testing configuration"""

    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False


config = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
    "default": DevelopmentConfig,
}
