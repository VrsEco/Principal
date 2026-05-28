import os
from datetime import timedelta
from dotenv import load_dotenv
from pathlib import Path

from utils.env_helpers import normalize_database_url
from utils.security import env_csv, env_flag, get_or_create_dev_secret

# Força o carregamento do .env local.
# Ordem:
# 1. app32/.env  -> canônico quando a app roda a partir do package root
# 2. ../.env     -> fallback para launcher local e execuções a partir do repo root
_ENV_CANDIDATES = [
    Path(__file__).resolve().parent / ".env",
    Path(__file__).resolve().parent.parent / ".env",
]
for _env_path in _ENV_CANDIDATES:
    if _env_path.exists():
        load_dotenv(dotenv_path=_env_path, override=False)

class Config:
    """Base configuration class"""

    SECRET_KEY = get_or_create_dev_secret()
    _env_database_url = normalize_database_url(os.environ.get("DATABASE_URL"))
    SQLALCHEMY_DATABASE_URI = _env_database_url or "postgresql://postgres@localhost:5432/bdversusv2"
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Authentication
    LOGIN_DISABLED = env_flag("LOGIN_DISABLED", default=False)
    REMEMBER_COOKIE_DURATION = timedelta(
        days=7
    )  # Reduzido de 30 para 7 dias por segurança

    # Session Configuration (Segurança)
    SESSION_COOKIE_SECURE = env_flag("SESSION_COOKIE_SECURE", default=False)
    SESSION_COOKIE_HTTPONLY = True  # Previne acesso via JavaScript (XSS protection)
    SESSION_COOKIE_SAMESITE = "Lax"  # Proteção contra CSRF
    SESSION_COOKIE_NAME = os.environ.get("SESSION_COOKIE_NAME", "gv_session")
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SAMESITE = "Lax"
    REMEMBER_COOKIE_SECURE = env_flag("REMEMBER_COOKIE_SECURE", default=False)
    PERMANENT_SESSION_LIFETIME = timedelta(
        hours=24
    )  # Sessão expira em 24h se não marcar "lembrar-me"
    SECURITY_ENFORCE_CSRF_SAME_ORIGIN = env_flag("SECURITY_ENFORCE_CSRF_SAME_ORIGIN", default=True)
    SECURITY_ALLOWED_HOSTS = env_csv("SECURITY_ALLOWED_HOSTS")
    SECURITY_TRUSTED_ORIGINS = env_csv("SECURITY_TRUSTED_ORIGINS")
    SECURITY_HSTS_SECONDS = int(os.environ.get("SECURITY_HSTS_SECONDS") or 31536000)
    SECURITY_PROXY_FIX_X_FOR = int(os.environ.get("SECURITY_PROXY_FIX_X_FOR") or 1)
    SECURITY_PROXY_FIX_X_PROTO = int(os.environ.get("SECURITY_PROXY_FIX_X_PROTO") or 1)
    SECURITY_PROXY_FIX_X_HOST = int(os.environ.get("SECURITY_PROXY_FIX_X_HOST") or 1)
    DEV_ROUTES_ENABLED = env_flag("DEV_ROUTES_ENABLED", default=False)
    WEBHOOK_SHARED_SECRET = os.environ.get("WEBHOOK_SHARED_SECRET")
    WHATSAPP_WEBHOOK_SECRET = os.environ.get("WHATSAPP_WEBHOOK_SECRET")
    TELEGRAM_WEBHOOK_SECRET = os.environ.get("TELEGRAM_WEBHOOK_SECRET")
    EMAIL_WEBHOOK_SECRET = os.environ.get("EMAIL_WEBHOOK_SECRET")

    # Email Configuration
    MAIL_SERVER = os.environ.get("MAIL_SERVER")
    MAIL_PORT = int(os.environ.get("MAIL_PORT") or 587)
    MAIL_USE_TLS = os.environ.get("MAIL_USE_TLS", "true").lower() == "true"
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD")
    MAIL_DEFAULT_SENDER = os.environ.get("MAIL_DEFAULT_SENDER")
    EMAIL_PROVIDER = os.environ.get("EMAIL_PROVIDER", "smtp")
    EMAIL_WEBHOOK_URL = os.environ.get("EMAIL_WEBHOOK_URL")
    EMAIL_INBOUND_PROTOCOL = os.environ.get("EMAIL_INBOUND_PROTOCOL", "pop3")
    EMAIL_INBOUND_HOST = os.environ.get("EMAIL_INBOUND_HOST")
    EMAIL_INBOUND_PORT = int(os.environ.get("EMAIL_INBOUND_PORT") or 995)
    EMAIL_INBOUND_USERNAME = os.environ.get("EMAIL_INBOUND_USERNAME")
    EMAIL_INBOUND_PASSWORD = os.environ.get("EMAIL_INBOUND_PASSWORD")
    EMAIL_INBOUND_USE_SSL = (
        os.environ.get("EMAIL_INBOUND_USE_SSL", "true").lower() == "true"
    )
    EMAIL_AUTO_REPLY = os.environ.get("EMAIL_AUTO_REPLY", "false").lower() == "true"

    # File Uploads
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    UPLOAD_FOLDER = os.environ.get("UPLOAD_FOLDER") or "uploads"
    ALLOWED_EXTENSIONS = {"pdf", "png", "jpg", "jpeg", "gif"}

    # Google Cloud Storage
    GCS_BUCKET = os.environ.get("GCS_BUCKET")
    GOOGLE_APPLICATION_CREDENTIALS = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")

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
    WHATSAPP_INSTANCE_ID = os.environ.get("WHATSAPP_INSTANCE_ID")
    WHATSAPP_CLIENT_TOKEN = os.environ.get("WHATSAPP_CLIENT_TOKEN")
    TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID")
    TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN")

    # Telegram Integration
    TELEGRAM_PROVIDER = os.environ.get("TELEGRAM_PROVIDER", "bot_api")
    TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
    TELEGRAM_BOT_TOKEN_DEV = os.environ.get("TELEGRAM_BOT_TOKEN_DEV")
    TELEGRAM_BOT_TOKEN_PROD = os.environ.get("TELEGRAM_BOT_TOKEN_PROD")
    TELEGRAM_WEBHOOK_URL = os.environ.get("TELEGRAM_WEBHOOK_URL")
    TELEGRAM_WEBHOOK_PATH = os.environ.get("TELEGRAM_WEBHOOK_PATH", "/webhook/telegram")
    TELEGRAM_ENV = os.environ.get("TELEGRAM_ENV")

    # Instagram Integration
    INSTAGRAM_PROVIDER = os.environ.get("INSTAGRAM_PROVIDER", "meta")
    INSTAGRAM_ACCESS_TOKEN = os.environ.get("INSTAGRAM_ACCESS_TOKEN")
    INSTAGRAM_BUSINESS_ACCOUNT_ID = os.environ.get("INSTAGRAM_BUSINESS_ACCOUNT_ID")
    INSTAGRAM_WEBHOOK_URL = os.environ.get("INSTAGRAM_WEBHOOK_URL")
    INSTAGRAM_GRAPH_API_BASE = os.environ.get(
        "INSTAGRAM_GRAPH_API_BASE", "https://graph.facebook.com/v21.0"
    )
    INSTAGRAM_APP_ID = os.environ.get("INSTAGRAM_APP_ID")
    INSTAGRAM_APP_SECRET = os.environ.get("INSTAGRAM_APP_SECRET")
    INSTAGRAM_VERIFY_TOKEN = os.environ.get("INSTAGRAM_VERIFY_TOKEN")

    # Redis for Celery
    REDIS_URL = os.environ.get("REDIS_URL") or "redis://localhost:6379/0"
    CELERY_BROKER_URL = REDIS_URL
    CELERY_RESULT_BACKEND = REDIS_URL

    # PDF Generation
    PDF_TEMP_FOLDER = os.environ.get("PDF_TEMP_FOLDER") or "temp_pdfs"

    # Rate Limiting
    RATELIMIT_STORAGE_URL = REDIS_URL

    # Telegram Webhook
    EXTERNAL_URL = os.environ.get("EXTERNAL_URL")
    TELEGRAM_SETUP_WEBHOOK = env_flag("TELEGRAM_SETUP_WEBHOOK", default=False)


class DevelopmentConfig(Config):
    """Development configuration"""

    DEBUG = True
    TEMPLATES_AUTO_RELOAD = True  # Recarregar templates automaticamente
    SEND_FILE_MAX_AGE_DEFAULT = 0  # Sem cache de arquivos estáticos
    _dev_database_url = normalize_database_url(os.environ.get("DEV_DATABASE_URL"))
    SQLALCHEMY_DATABASE_URI = (
        _dev_database_url
        or Config._env_database_url
        or "postgresql://postgres@localhost:5432/bdversusv2"
    )
    DEV_ROUTES_ENABLED = env_flag("DEV_ROUTES_ENABLED", default=True)


class ProductionConfig(Config):
    """Production configuration"""

    DEBUG = False
    SESSION_COOKIE_SECURE = True
    REMEMBER_COOKIE_SECURE = True
    _prod_database_url = normalize_database_url(os.environ.get("DATABASE_URL"))
    SQLALCHEMY_DATABASE_URI = _prod_database_url
    SECRET_KEY = os.environ.get("SECRET_KEY")
    DEV_ROUTES_ENABLED = False


class TestingConfig(Config):
    """Testing configuration"""

    TESTING = True
    # For testing, use a separate test database or mock
    SQLALCHEMY_DATABASE_URI = "postgresql://postgres:password@localhost:5432/bd_app_versus_test"
    WTF_CSRF_ENABLED = False
    SECURITY_ENFORCE_CSRF_SAME_ORIGIN = False
    DEV_ROUTES_ENABLED = True


config = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
    "default": DevelopmentConfig,
}
