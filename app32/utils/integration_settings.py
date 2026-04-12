from __future__ import annotations

import os
from typing import Any, Dict, Optional

from database.postgresql_db import get_integration, list_integrations


SUPPORTED_SERVICES = {"ai", "email", "whatsapp", "telegram", "instagram"}


def normalize_service(service: Optional[str]) -> str:
    value = (service or "").strip().lower().replace("_", "-")
    aliases = {
        "ia": "ai",
        "mail": "email",
        "e-mail": "email",
        "wpp": "whatsapp",
        "whats": "whatsapp",
        "ig": "instagram",
        "insta": "instagram",
        "tg": "telegram",
    }
    return aliases.get(value, value)


def coalesce(*values: Any) -> Any:
    for value in values:
        if value is None:
            continue
        if isinstance(value, str) and not value.strip():
            continue
        return value
    return None


def normalize_config(config: Any) -> Dict[str, Any]:
    return config if isinstance(config, dict) else {}


def _find_service_integration(service: str) -> Optional[Dict[str, Any]]:
    normalized_service = normalize_service(service)
    if normalized_service not in SUPPORTED_SERVICES:
        return None

    priority_id = f"{normalized_service}_integration"
    try:
        record = get_integration(priority_id)
        if record:
            return record
    except Exception:
        pass

    try:
        records = list_integrations() or []
    except Exception:
        return None

    for item in records:
        if item.get("id") == priority_id:
            return item

    for item in records:
        if normalize_service(item.get("type")) == normalized_service:
            return item
    return None


def _default_service_config(service: str) -> Dict[str, Any]:
    service = normalize_service(service)

    if service == "ai":
        provider = str(
            coalesce(
                os.environ.get("AI_PROVIDER"),
                "openai",
            )
        ).strip().lower()
        return {
            "provider": provider,
            "config": {
                "provider": provider,
                "api_key": coalesce(
                    os.environ.get("OPENAI_API_KEY"),
                    os.environ.get("AI_API_KEY"),
                ),
                "url": os.environ.get("AI_WEBHOOK_URL"),
                "webhook_url": os.environ.get("AI_WEBHOOK_URL"),
                "base_url": os.environ.get("AI_BASE_URL", "https://api.openai.com/v1"),
                "model": os.environ.get("AI_MODEL"),
            },
            "source": "environment",
            "integration_id": None,
        }

    if service == "email":
        provider = str(coalesce(os.environ.get("EMAIL_PROVIDER"), "smtp")).strip().lower()
        return {
            "provider": provider,
            "config": {
                "provider": provider,
                "server": os.environ.get("MAIL_SERVER"),
                "port": os.environ.get("MAIL_PORT"),
                "username": os.environ.get("MAIL_USERNAME"),
                "password": os.environ.get("MAIL_PASSWORD"),
                "default_sender": os.environ.get("MAIL_DEFAULT_SENDER"),
                "from_name": os.environ.get("MAIL_FROM_NAME"),
                "webhook_url": os.environ.get("EMAIL_WEBHOOK_URL"),
                "webhook_secret": coalesce(
                    os.environ.get("EMAIL_WEBHOOK_SECRET"),
                    os.environ.get("WEBHOOK_SHARED_SECRET"),
                ),
                "use_tls": os.environ.get("MAIL_USE_TLS", "true").strip().lower() == "true",
                "use_ssl": os.environ.get("MAIL_USE_SSL", "false").strip().lower() == "true",
                "inbound_protocol": os.environ.get("EMAIL_INBOUND_PROTOCOL", "pop3"),
                "inbound_host": os.environ.get("EMAIL_INBOUND_HOST"),
                "inbound_port": os.environ.get("EMAIL_INBOUND_PORT"),
                "inbound_username": os.environ.get("EMAIL_INBOUND_USERNAME"),
                "inbound_password": os.environ.get("EMAIL_INBOUND_PASSWORD"),
                "inbound_use_ssl": os.environ.get("EMAIL_INBOUND_USE_SSL", "true").strip().lower() == "true",
            },
            "source": "environment",
            "integration_id": None,
        }

    if service == "whatsapp":
        provider = str(coalesce(os.environ.get("WHATSAPP_PROVIDER"), "z-api")).strip().lower()
        account_sid = coalesce(
            os.environ.get("TWILIO_ACCOUNT_SID"),
            os.environ.get("WHATSAPP_API_KEY"),
        )
        return {
            "provider": provider,
            "config": {
                "provider": provider,
                "api_key": os.environ.get("WHATSAPP_API_KEY"),
                "instance_id": os.environ.get("WHATSAPP_INSTANCE_ID"),
                "client_token": os.environ.get("WHATSAPP_CLIENT_TOKEN"),
                "webhook_url": os.environ.get("WHATSAPP_WEBHOOK_URL"),
                "webhook_secret": coalesce(
                    os.environ.get("WHATSAPP_WEBHOOK_SECRET"),
                    os.environ.get("WEBHOOK_SHARED_SECRET"),
                ),
                "account_sid": account_sid,
                "auth_token": os.environ.get("TWILIO_AUTH_TOKEN"),
                "whatsapp_number": os.environ.get("WHATSAPP_INSTANCE_ID"),
            },
            "source": "environment",
            "integration_id": None,
        }

    if service == "telegram":
        provider = str(coalesce(os.environ.get("TELEGRAM_PROVIDER"), "bot_api")).strip().lower()
        return {
            "provider": provider,
            "config": {
                "provider": provider,
                "bot_token": coalesce(
                    os.environ.get("TELEGRAM_BOT_TOKEN"),
                    os.environ.get("TELEGRAM_BOT_TOKEN_PROD"),
                    os.environ.get("TELEGRAM_BOT_TOKEN_DEV"),
                ),
                "bot_token_dev": os.environ.get("TELEGRAM_BOT_TOKEN_DEV"),
                "bot_token_prod": os.environ.get("TELEGRAM_BOT_TOKEN_PROD"),
                "telegram_env": os.environ.get("TELEGRAM_ENV"),
                "webhook_url": os.environ.get("TELEGRAM_WEBHOOK_URL"),
                "webhook_secret": coalesce(
                    os.environ.get("TELEGRAM_WEBHOOK_SECRET"),
                    os.environ.get("WEBHOOK_SHARED_SECRET"),
                ),
                "external_url": os.environ.get("EXTERNAL_URL"),
                "setup_webhook": os.environ.get("TELEGRAM_SETUP_WEBHOOK", "false").strip().lower() == "true",
                "webhook_path": os.environ.get("TELEGRAM_WEBHOOK_PATH", "/webhook/telegram"),
            },
            "source": "environment",
            "integration_id": None,
        }

    if service == "instagram":
        provider = str(coalesce(os.environ.get("INSTAGRAM_PROVIDER"), "meta")).strip().lower()
        return {
            "provider": provider,
            "config": {
                "provider": provider,
                "access_token": os.environ.get("INSTAGRAM_ACCESS_TOKEN"),
                "business_account_id": os.environ.get("INSTAGRAM_BUSINESS_ACCOUNT_ID"),
                "webhook_url": os.environ.get("INSTAGRAM_WEBHOOK_URL"),
                "webhook_secret": coalesce(
                    os.environ.get("INSTAGRAM_WEBHOOK_SECRET"),
                    os.environ.get("WEBHOOK_SHARED_SECRET"),
                ),
                "graph_api_base": os.environ.get("INSTAGRAM_GRAPH_API_BASE", "https://graph.facebook.com/v21.0"),
                "app_id": os.environ.get("INSTAGRAM_APP_ID"),
                "app_secret": os.environ.get("INSTAGRAM_APP_SECRET"),
                "verify_token": os.environ.get("INSTAGRAM_VERIFY_TOKEN"),
            },
            "source": "environment",
            "integration_id": None,
        }

    return {"provider": "disabled", "config": {}, "source": "environment", "integration_id": None}


def resolve_service_config(service: str) -> Dict[str, Any]:
    normalized_service = normalize_service(service)
    if os.environ.get("APP32_INTEGRATIONS_TEST_MODE", "").strip().lower() == "true":
        return _default_service_config(normalized_service)

    db_record = _find_service_integration(normalized_service)
    if db_record:
        config = normalize_config(db_record.get("config"))
        provider = str(coalesce(config.get("provider"), db_record.get("provider"), "disabled")).strip().lower()
        return {
            "provider": provider,
            "config": {**config, "provider": provider},
            "source": "database",
            "integration_id": db_record.get("id"),
        }
    return _default_service_config(normalized_service)


def resolve_ai_runtime_config() -> Dict[str, Any]:
    resolved = resolve_service_config("ai")
    config = normalize_config(resolved.get("config"))
    provider = str(coalesce(config.get("provider"), resolved.get("provider"), "openai")).strip().lower()
    return {
        **resolved,
        "provider": provider,
        "api_key": coalesce(config.get("api_key"), config.get("openai_api_key")),
        "base_url": coalesce(config.get("base_url"), "https://api.openai.com/v1"),
        "webhook_url": coalesce(config.get("url"), config.get("webhook_url")),
        "model": config.get("model"),
        "timeout": config.get("timeout"),
    }


def resolve_openai_api_key() -> Optional[str]:
    ai_config = resolve_ai_runtime_config()
    if ai_config.get("provider") == "openai":
        return ai_config.get("api_key")
    return coalesce(
        ai_config.get("api_key"),
        os.environ.get("OPENAI_API_KEY"),
        os.environ.get("AI_API_KEY"),
    )


def resolve_telegram_bot_token() -> tuple[Optional[str], str]:
    resolved = resolve_service_config("telegram")
    config = normalize_config(resolved.get("config"))
    telegram_env = str(coalesce(config.get("telegram_env"), os.environ.get("TELEGRAM_ENV"), "")).strip().lower()
    flask_env = str(coalesce(os.environ.get("FLASK_ENV"), os.environ.get("FLASK_CONFIG"), "")).strip().lower()
    is_prod = telegram_env in {"prod", "production", "live"} or flask_env in {"prod", "production"}
    if is_prod:
        return coalesce(config.get("bot_token_prod"), config.get("bot_token")), "PROD"

    is_dev = telegram_env in {"dev", "development", "local", "test"} or flask_env in {"dev", "development", "default", "testing"}
    if is_dev:
        return coalesce(config.get("bot_token_dev"), config.get("bot_token")), "DEV"

    return coalesce(config.get("bot_token_prod"), config.get("bot_token"), config.get("bot_token_dev")), "PROD"


def resolve_webhook_secret(service: str) -> str:
    resolved = resolve_service_config(service)
    config = normalize_config(resolved.get("config"))
    return str(
        coalesce(
            config.get("webhook_secret"),
            config.get("secret"),
            os.environ.get(f"{normalize_service(service).upper()}_WEBHOOK_SECRET"),
            os.environ.get("WEBHOOK_SHARED_SECRET"),
            "",
        )
        or ""
    ).strip()
