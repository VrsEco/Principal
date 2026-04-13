import os
from contextlib import contextmanager
from typing import Any, Dict, Optional, Tuple

from flask import Blueprint, current_app, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from database.postgresql_db import (
    create_integration,
    delete_integration,
    get_integration,
    list_integrations,
    update_integration,
)
from services.ai_service import AIService
from services.email_service import EmailService
from services.integration_catalog_service import IntegrationCatalogService
from services.integration_request_service import IntegrationRequestService
from services.instagram_service import InstagramService
from services.telegram_service import TelegramService
from services.tool_backlog_service import ToolBacklogService
from services.tool_first_catalog_service import ToolFirstCatalogService
from services.whatsapp_service import WhatsAppService
from services.workflow_backlog_service import WorkflowBacklogService
from services.workflow_spec_draft_service import WorkflowSpecDraftService
from services.workflow_workspace_service import WorkflowWorkspaceService
from utils.integration_settings import resolve_service_config

integrations_bp = Blueprint("integrations", __name__)


def _resolve_active_company():
    from api.routes.main import _resolve_active_company as _main_resolve_active_company

    return _main_resolve_active_company()


def _safe_active_company():
    try:
        return _resolve_active_company()
    except Exception:
        current_app.logger.exception("Falha ao resolver empresa ativa em integrações.")
        return None


def _fallback_integrations_shell(title: str, body: str, *, links: list[tuple[str, str]] | None = None) -> str:
    safe_links = links or []
    links_html = "".join(
        f'<a href="{href}" style="display:inline-flex;padding:10px 14px;border-radius:10px;border:1px solid #cbd5e1;text-decoration:none;color:#0f172a;font-weight:600;margin-right:8px;margin-top:8px;">{label}</a>'
        for label, href in safe_links
    )
    return f"""
    <!DOCTYPE html>
    <html lang="pt-BR">
      <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>{title}</title>
      </head>
      <body style="font-family:Inter,Arial,sans-serif;background:#f8fafc;color:#0f172a;margin:0;padding:32px;">
        <div style="max-width:960px;margin:0 auto;background:#fff;border:1px solid #e2e8f0;border-radius:18px;padding:24px;box-shadow:0 10px 30px rgba(15,23,42,.08);">
          <span style="display:inline-flex;padding:6px 12px;border-radius:999px;background:#dbeafe;color:#1d4ed8;font-weight:700;font-size:12px;">Modo de contingência</span>
          <h1 style="margin:16px 0 8px;">{title}</h1>
          <p style="margin:0 0 16px;color:#475569;">{body}</p>
          <div>{links_html}</div>
        </div>
      </body>
    </html>
    """

SUPPORTED_SERVICES = {"ai", "email", "whatsapp", "telegram", "instagram"}
SECRET_KEY_HINTS = ("password", "token", "secret", "api_key", "auth")
SERVICE_ORDER = ("ai", "email", "whatsapp", "telegram", "instagram")

FIELD_LABELS = {
    "api_key": "API key",
    "base_url": "Base URL",
    "url": "Webhook URL",
    "webhook_url": "Webhook URL",
    "server": "Servidor SMTP",
    "port": "Porta",
    "username": "Usuario SMTP",
    "password": "Senha SMTP",
    "inbound_protocol": "Protocolo inbound (POP3/IMAP)",
    "inbound_host": "Servidor inbound",
    "inbound_port": "Porta inbound",
    "inbound_username": "Usuario inbound",
    "inbound_password": "Senha inbound",
    "instance_id": "Instance ID",
    "client_token": "Client Token (Z-API)",
    "account_sid": "Account SID",
    "auth_token": "Auth Token",
    "whatsapp_number": "Numero WhatsApp",
    "bot_token": "Bot token",
    "bot_token_dev": "Bot token DEV",
    "bot_token_prod": "Bot token PROD",
    "webhook_path": "Webhook path",
    "external_url": "External URL",
    "access_token": "Access token",
    "business_account_id": "Business Account ID",
    "graph_api_base": "Graph API Base",
    "app_id": "App ID",
    "app_secret": "App secret",
    "verify_token": "Verify token",
}

SERVICE_REQUIREMENTS = {
    "ai": {
        "label": "Inteligencia Artificial",
        "registration": {
            "identity_field": None,
            "identity_location": "Nao se aplica (IA responde via outros canais).",
            "credentials_location": "Tabela integrations (type='ai') em configuracoes.",
            "scope": "global",
        },
        "webhook": {
            "path": None,
            "methods": [],
            "description": "Canal sem webhook proprio de entrada.",
        },
        "providers": {
            "openai": {
                "required_fields": ["api_key"],
                "external_services": [
                    "Conta OpenAI com billing habilitado",
                    "API key valida da OpenAI",
                ],
            },
            "anthropic": {
                "required_fields": ["api_key"],
                "external_services": [
                    "Conta Anthropic com acesso a API",
                    "API key valida da Anthropic",
                ],
            },
            "webhook": {
                "required_fields": ["url"],
                "external_services": [
                    "Endpoint HTTPS externo para processamento de IA",
                ],
            },
            "local": {
                "required_fields": [],
                "external_services": [
                    "Nenhum servico externo obrigatorio",
                ],
            },
            "disabled": {"required_fields": [], "external_services": []},
        },
    },
    "email": {
        "label": "Email",
        "registration": {
            "identity_field": "users.email",
            "identity_location": "Cadastro do usuario (campo Email).",
            "credentials_location": "Tabela integrations (type='email') com SMTP/POP3/IMAP/Webhook.",
            "scope": "user",
        },
        "webhook": {
            "path": "/webhook/email",
            "methods": ["POST"],
            "description": "Entrada de e-mails por webhook. POP3/IMAP pode ser usado em paralelo.",
        },
        "providers": {
            "smtp": {
                "required_fields": ["server", "port", "username", "password"],
                "external_services": [
                    "Provedor de e-mail com SMTP liberado (Gmail, Outlook, SES, etc.)",
                    "Caixa de e-mail para envio (e inbound opcional via POP3/IMAP)",
                ],
            },
            "webhook": {
                "required_fields": ["webhook_url"],
                "external_services": [
                    "Plataforma que entregue mensagens para webhook HTTP",
                ],
            },
            "local": {
                "required_fields": [],
                "external_services": [
                    "Nenhum servico externo obrigatorio",
                ],
            },
            "disabled": {"required_fields": [], "external_services": []},
        },
    },
    "whatsapp": {
        "label": "WhatsApp",
        "registration": {
            "identity_field": "users.whatsapp",
            "identity_location": "Cadastro do usuario (campo WhatsApp).",
            "credentials_location": "Tabela integrations (type='whatsapp').",
            "scope": "user",
        },
        "webhook": {
            "path": "/webhook/whatsapp",
            "methods": ["POST"],
            "description": "Entrada de mensagens via provedor WhatsApp.",
        },
        "providers": {
            "z-api": {
                "required_fields": ["api_key", "instance_id"],
                "external_services": [
                    "Conta Z-API",
                    "Instancia ativa no WhatsApp provider",
                    "Se sua conta exigir seguranca adicional, informe tambem o Client Token",
                ],
            },
            "twilio": {
                "required_fields": ["account_sid", "auth_token", "whatsapp_number"],
                "external_services": [
                    "Conta Twilio com WhatsApp habilitado",
                    "Numero/sender de WhatsApp aprovado no Twilio",
                ],
            },
            "webhook": {
                "required_fields": ["webhook_url"],
                "external_services": [
                    "Gateway externo que entregue e receba mensagens por webhook",
                ],
            },
            "local": {
                "required_fields": [],
                "external_services": [
                    "Nenhum servico externo obrigatorio",
                ],
            },
            "disabled": {"required_fields": [], "external_services": []},
        },
    },
    "telegram": {
        "label": "Telegram",
        "registration": {
            "identity_field": "users.telegram",
            "identity_location": "Cadastro do usuario (campo Telegram ID).",
            "credentials_location": "Tabela integrations (type='telegram').",
            "scope": "user",
        },
        "webhook": {
            "path": "/webhook/telegram",
            "methods": ["POST"],
            "description": "Webhook do bot Telegram para mensagens inbound.",
        },
        "providers": {
            "bot_api": {
                "required_fields": [
                    {
                        "any_of": ["bot_token", "bot_token_dev", "bot_token_prod"],
                        "label": "Bot token (unico ou DEV/PROD)",
                    }
                ],
                "external_services": [
                    "Bot criado no Telegram (BotFather)",
                    "URL publica HTTPS para webhook (quando setup_webhook estiver ativo)",
                ],
            },
            "webhook": {
                "required_fields": ["webhook_url"],
                "external_services": [
                    "Gateway externo para mensageria Telegram",
                ],
            },
            "local": {
                "required_fields": [],
                "external_services": [
                    "Nenhum servico externo obrigatorio",
                ],
            },
            "disabled": {"required_fields": [], "external_services": []},
        },
    },
    "instagram": {
        "label": "Instagram",
        "registration": {
            "identity_field": "users.instagram",
            "identity_location": "Cadastro do usuario (campo Instagram).",
            "credentials_location": "Tabela integrations (type='instagram').",
            "scope": "user",
        },
        "webhook": {
            "path": "/webhook/instagram",
            "methods": ["POST"],
            "description": "Entrada de mensagens do Instagram Direct.",
        },
        "providers": {
            "meta": {
                "required_fields": ["access_token", "business_account_id"],
                "external_services": [
                    "Conta Meta Developer com app configurado",
                    "Instagram Business conectado ao ecossistema Meta",
                ],
            },
            "webhook": {
                "required_fields": ["webhook_url"],
                "external_services": [
                    "Gateway externo para entrega de eventos Instagram",
                ],
            },
            "local": {
                "required_fields": [],
                "external_services": [
                    "Nenhum servico externo obrigatorio",
                ],
            },
            "disabled": {"required_fields": [], "external_services": []},
        },
    },
}


def _normalize_service(service: Optional[str]) -> str:
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


def _service_from_integration_identifier(identifier: Optional[str]) -> Optional[str]:
    raw = (identifier or "").strip().lower()
    if not raw:
        return None

    direct = _normalize_service(raw)
    if direct in SUPPORTED_SERVICES:
        return direct

    if raw.endswith("_integration"):
        candidate = _normalize_service(raw[: -len("_integration")])
        if candidate in SUPPORTED_SERVICES:
            return candidate

    return None


def _coalesce(*values):
    for value in values:
        if value is None:
            continue
        if isinstance(value, str) and not value.strip():
            continue
        return value
    return None


def _normalize_config(config: Any) -> Dict[str, Any]:
    return config if isinstance(config, dict) else {}


def _find_service_integration(service: str) -> Optional[Dict[str, Any]]:
    records = list_integrations()
    if not records:
        return None

    priority_id = f"{service}_integration"
    match = next((item for item in records if item.get("id") == priority_id), None)
    if match:
        return match

    for item in records:
        if _normalize_service(item.get("type")) == service:
            return item
    return None


def _default_service_config(service: str) -> Dict[str, Any]:
    return resolve_service_config(service)


def _resolve_service_config(service: str) -> Dict[str, Any]:
    return _default_service_config(service)


def _is_configured(service: str, provider: str, config: Dict[str, Any]) -> bool:
    service = _normalize_service(service)
    provider = (provider or "").strip().lower()
    if provider in {"", "disabled", "none"}:
        return False

    if service == "ai":
        if provider in {"openai", "anthropic"}:
            return bool(config.get("api_key"))
        if provider == "webhook":
            return bool(_coalesce(config.get("url"), config.get("webhook_url")))
        return True

    if service == "email":
        if provider == "smtp":
            return bool(
                config.get("server")
                and config.get("port")
                and config.get("username")
                and config.get("password")
            )
        if provider == "webhook":
            return bool(config.get("webhook_url"))
        if provider == "local":
            return True
        return False

    if service == "whatsapp":
        if provider == "z-api":
            return bool(config.get("api_key") and config.get("instance_id"))
        if provider == "twilio":
            return bool(
                _coalesce(config.get("account_sid"), config.get("api_key"))
                and config.get("auth_token")
                and _coalesce(config.get("whatsapp_number"), config.get("instance_id"))
            )
        if provider == "webhook":
            return bool(config.get("webhook_url"))
        if provider == "local":
            return True
        return False

    if service == "telegram":
        if provider == "bot_api":
            return bool(
                _coalesce(
                    config.get("bot_token"),
                    config.get("bot_token_prod"),
                    config.get("bot_token_dev"),
                )
            )
        if provider == "webhook":
            return bool(config.get("webhook_url"))
        if provider == "local":
            return True
        return False

    if service == "instagram":
        if provider == "meta":
            return bool(config.get("access_token") and config.get("business_account_id"))
        if provider == "webhook":
            return bool(config.get("webhook_url"))
        if provider == "local":
            return True
        return False

    return bool(config)


def _service_status(service: str) -> Dict[str, Any]:
    resolved = _resolve_service_config(service)
    provider = resolved["provider"]
    config = resolved["config"]
    configured = _is_configured(service, provider, config)
    return {
        "provider": provider,
        "configured": configured,
        "active": configured and provider not in {"disabled", "none"},
        "source": resolved["source"],
        "integration_id": resolved["integration_id"],
    }


def _service_config_payload(service: str) -> Dict[str, Any]:
    resolved = _resolve_service_config(service)
    provider = resolved["provider"]
    config = resolved["config"]
    configured = _is_configured(service, provider, config)
    return {
        "provider": provider,
        "configured": configured,
        "active": configured and provider not in {"disabled", "none"},
        "source": resolved["source"],
        "integration_id": resolved["integration_id"],
        "config": _sanitize_config(config),
    }


def _has_config_value(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, dict, tuple, set)):
        return bool(value)
    return True


def _field_label(field_key: str) -> str:
    if not field_key:
        return "Campo"
    return FIELD_LABELS.get(field_key, field_key.replace("_", " ").title())


def _normalize_requirement_field(item: Any) -> Optional[Dict[str, Any]]:
    if isinstance(item, str):
        key = item.strip()
        if not key:
            return None
        return {"key": key, "label": _field_label(key)}

    if not isinstance(item, dict):
        return None

    if "any_of" in item:
        raw_fields = item.get("any_of") or []
        any_of = [str(field).strip() for field in raw_fields if str(field).strip()]
        if not any_of:
            return None
        return {
            "any_of": any_of,
            "label": item.get("label") or " ou ".join(_field_label(field) for field in any_of),
        }

    key = str(item.get("key") or "").strip()
    if not key:
        return None
    return {
        "key": key,
        "label": item.get("label") or _field_label(key),
    }


def _is_requirement_satisfied(requirement: Dict[str, Any], config: Dict[str, Any]) -> bool:
    if "any_of" in requirement:
        return any(_has_config_value(config.get(field)) for field in requirement.get("any_of", []))
    return _has_config_value(config.get(requirement.get("key")))


def _provider_requirements_payload(service: str, provider: str, config: Dict[str, Any]) -> Dict[str, Any]:
    service_spec = SERVICE_REQUIREMENTS.get(service, {})
    provider_specs = service_spec.get("providers", {})
    provider_spec = provider_specs.get(provider) or provider_specs.get("default") or {}

    required_items = []
    for raw_item in provider_spec.get("required_fields", []):
        normalized = _normalize_requirement_field(raw_item)
        if normalized:
            required_items.append(normalized)

    missing_items = [
        item for item in required_items if not _is_requirement_satisfied(item, config)
    ]

    return {
        "provider": provider,
        "required_fields": required_items,
        "missing_fields": missing_items,
        "external_services": provider_spec.get("external_services", []),
    }


def _webhook_payload(service: str, base_url: str) -> Dict[str, Any]:
    service_spec = SERVICE_REQUIREMENTS.get(service, {})
    webhook = service_spec.get("webhook") or {}
    path = webhook.get("path")
    full_url = f"{base_url}{path}" if path else None
    return {
        "path": path,
        "full_url": full_url,
        "methods": webhook.get("methods", []),
        "description": webhook.get("description"),
    }


def _service_requirements_payload(service: str, base_url: str) -> Dict[str, Any]:
    resolved = _resolve_service_config(service)
    provider = resolved["provider"]
    config = resolved["config"]
    configured = _is_configured(service, provider, config)
    spec = SERVICE_REQUIREMENTS.get(service, {})

    return {
        "service": service,
        "label": spec.get("label", service.title()),
        "provider": provider,
        "configured": configured,
        "active": configured and provider not in {"disabled", "none"},
        "source": resolved["source"],
        "integration_id": resolved["integration_id"],
        "registration": spec.get("registration", {}),
        "webhook": _webhook_payload(service, base_url),
        "provider_requirements": _provider_requirements_payload(service, provider, config),
    }


def _mask_secret(value: Any) -> str:
    if value in (None, ""):
        return ""
    return "******"


def _sanitize_value(key: Any, value: Any) -> Any:
    if isinstance(value, dict):
        return {k: _sanitize_value(k, v) for k, v in value.items()}
    if isinstance(value, list):
        return [_sanitize_value(key, item) for item in value]

    key_l = str(key).lower()
    if any(hint in key_l for hint in SECRET_KEY_HINTS):
        return _mask_secret(value) if value else value
    return value


def _sanitize_config(config: Dict[str, Any]) -> Dict[str, Any]:
    return {key: _sanitize_value(key, value) for key, value in (config or {}).items()}


def _looks_masked_secret(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    text = value.strip()
    if not text or "*" not in text:
        return False
    star_count = text.count("*")
    return star_count >= max(2, len(text) // 2)


def _merge_existing_secret_values(payload: Dict[str, Any]) -> Dict[str, Any]:
    service = _normalize_service(payload.get("type"))
    integration_id = payload.get("id")
    incoming_config = _normalize_config(payload.get("config"))

    existing = get_integration(integration_id) if integration_id else None
    if not existing:
        existing = _find_service_integration(service)
    if not existing:
        payload["config"] = incoming_config
        return payload

    existing_config = _normalize_config(existing.get("config"))
    merged = dict(incoming_config)

    for key, old_value in existing_config.items():
        key_l = str(key).lower()
        if isinstance(old_value, dict):
            incoming_map = merged.get(key) if isinstance(merged.get(key), dict) else {}
            preserved_map = dict(incoming_map)
            changed = False
            for sub_key, sub_old in old_value.items():
                sub_key_l = str(sub_key).lower()
                if not any(hint in sub_key_l for hint in SECRET_KEY_HINTS):
                    continue
                sub_candidate = incoming_map.get(sub_key)
                if sub_key not in incoming_map or sub_candidate is None:
                    preserved_map[sub_key] = sub_old
                    changed = True
                    continue
                if isinstance(sub_candidate, str) and (
                    not sub_candidate.strip() or _looks_masked_secret(sub_candidate)
                ):
                    preserved_map[sub_key] = sub_old
                    changed = True
            if changed:
                merged[key] = preserved_map
            continue

        if not any(hint in key_l for hint in SECRET_KEY_HINTS):
            continue
        candidate = merged.get(key)
        if key not in merged or candidate is None:
            merged[key] = old_value
            continue
        if isinstance(candidate, str) and (
            not candidate.strip() or _looks_masked_secret(candidate)
        ):
            merged[key] = old_value

    payload["config"] = merged
    return payload


def _integration_to_response(item: Dict[str, Any]) -> Dict[str, Any]:
    service = _normalize_service(item.get("type"))
    config = _normalize_config(item.get("config"))
    provider = str(_coalesce(item.get("provider"), config.get("provider"), "unknown")).lower()
    configured = _is_configured(service, provider, config) if service in SUPPORTED_SERVICES else bool(config)

    response = dict(item)
    response["provider"] = provider
    response["configured"] = configured
    response["status"] = "active" if configured and provider not in {"disabled", "none"} else "inactive"
    response["config"] = _sanitize_config(config)
    return response


@contextmanager
def _temporary_env(overrides: Dict[str, Any]):
    marker = object()
    original = {}

    for key, value in overrides.items():
        original[key] = os.environ.get(key, marker)
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = str(value)

    try:
        yield
    finally:
        for key, value in original.items():
            if value is marker:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def _env_overrides_for_test(service: str, config: Dict[str, Any]) -> Dict[str, Any]:
    provider = (config.get("provider") or "disabled").strip().lower()
    overrides: Dict[str, Any] = {"APP32_INTEGRATIONS_TEST_MODE": "true"}

    if service == "ai":
        overrides.update({
            "AI_PROVIDER": provider,
            "AI_API_KEY": config.get("api_key"),
            "AI_WEBHOOK_URL": _coalesce(config.get("url"), config.get("webhook_url")),
            "AI_BASE_URL": config.get("base_url"),
        })
        return overrides

    if service == "email":
        overrides.update({
            "EMAIL_PROVIDER": provider,
            "MAIL_SERVER": config.get("server"),
            "MAIL_PORT": config.get("port"),
            "MAIL_USERNAME": config.get("username"),
            "MAIL_PASSWORD": config.get("password"),
            "MAIL_USE_TLS": "true" if config.get("use_tls", True) else "false",
            "EMAIL_WEBHOOK_URL": config.get("webhook_url"),
            "EMAIL_INBOUND_PROTOCOL": config.get("inbound_protocol"),
            "EMAIL_INBOUND_HOST": config.get("inbound_host"),
            "EMAIL_INBOUND_PORT": config.get("inbound_port"),
            "EMAIL_INBOUND_USERNAME": config.get("inbound_username"),
            "EMAIL_INBOUND_PASSWORD": config.get("inbound_password"),
            "EMAIL_INBOUND_USE_SSL": "true"
            if config.get("inbound_use_ssl", True)
            else "false",
        })
        return overrides

    if service == "whatsapp":
        account_sid = _coalesce(config.get("account_sid"), config.get("api_key"))
        whatsapp_number = _coalesce(config.get("whatsapp_number"), config.get("instance_id"))
        overrides.update({
            "WHATSAPP_PROVIDER": provider,
            "WHATSAPP_API_KEY": config.get("api_key") if provider != "twilio" else account_sid,
            "WHATSAPP_INSTANCE_ID": config.get("instance_id") if provider != "twilio" else whatsapp_number,
            "WHATSAPP_CLIENT_TOKEN": config.get("client_token"),
            "WHATSAPP_WEBHOOK_URL": config.get("webhook_url"),
            "TWILIO_ACCOUNT_SID": account_sid,
            "TWILIO_AUTH_TOKEN": config.get("auth_token"),
        })
        return overrides

    if service == "telegram":
        overrides.update({
            "TELEGRAM_PROVIDER": provider,
            "TELEGRAM_BOT_TOKEN": config.get("bot_token"),
            "TELEGRAM_BOT_TOKEN_DEV": config.get("bot_token_dev"),
            "TELEGRAM_BOT_TOKEN_PROD": config.get("bot_token_prod"),
            "TELEGRAM_ENV": config.get("telegram_env"),
            "TELEGRAM_WEBHOOK_URL": config.get("webhook_url"),
            "EXTERNAL_URL": config.get("external_url"),
            "TELEGRAM_SETUP_WEBHOOK": "true"
            if config.get("setup_webhook")
            else "false",
            "TELEGRAM_WEBHOOK_PATH": config.get("webhook_path"),
        })
        return overrides

    if service == "instagram":
        overrides.update({
            "INSTAGRAM_PROVIDER": provider,
            "INSTAGRAM_ACCESS_TOKEN": config.get("access_token"),
            "INSTAGRAM_BUSINESS_ACCOUNT_ID": config.get("business_account_id"),
            "INSTAGRAM_WEBHOOK_URL": config.get("webhook_url"),
            "INSTAGRAM_GRAPH_API_BASE": config.get("graph_api_base"),
            "INSTAGRAM_APP_ID": config.get("app_id"),
            "INSTAGRAM_APP_SECRET": config.get("app_secret"),
            "INSTAGRAM_VERIFY_TOKEN": config.get("verify_token"),
        })
        return overrides

    return overrides


def _execute_test(service: str, config: Dict[str, Any]) -> Dict[str, Any]:
    provider = (config.get("provider") or "disabled").strip().lower()
    if provider in {"disabled", "none", ""}:
        return {
            "success": False,
            "provider": provider,
            "error": "Servico desabilitado. Configure um provedor antes de testar.",
        }

    overrides = _env_overrides_for_test(service, config)
    with _temporary_env(overrides):
        if service == "ai":
            return AIService().test_connection()
        if service == "email":
            return EmailService().test_connection()
        if service == "whatsapp":
            return WhatsAppService().test_connection()
        if service == "telegram":
            return TelegramService().test_connection()
        if service == "instagram":
            return InstagramService().test_connection()

    return {"success": False, "error": f"Servico nao suportado: {service}"}


def _build_integration_payload(data: Dict[str, Any]) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    service = _normalize_service(data.get("type") or data.get("service"))
    if service not in SUPPORTED_SERVICES:
        return None, "Tipo de integracao invalido. Use: ai, email, whatsapp, telegram ou instagram."

    config = _normalize_config(data.get("config"))
    provider = str(_coalesce(data.get("provider"), config.get("provider"), "disabled")).strip().lower()
    integration_id = (data.get("id") or f"{service}_integration").strip()

    payload = {
        "id": integration_id,
        "name": data.get("name") or f"Integracao {service.title()}",
        "provider": provider,
        "type": service,
        "auth_type": data.get("auth_type") or provider or "api_key",
        "config": {**config, "provider": provider},
    }
    return payload, None


@integrations_bp.route("/integrations")
@login_required
def integrations_page():
    active_company = _safe_active_company()
    try:
        catalog = IntegrationCatalogService.build_api_mcp_catalog()
    except Exception:
        current_app.logger.exception("Falha ao montar catálogo API / MCP.")
        catalog = {"summary": {"total": 0, "available": 0, "planned": 0, "discovery": 0}, "integrations": []}

    try:
        return render_template(
            "integrations.html",
            active_company=active_company,
            integration_catalog=catalog,
        )
    except Exception:
        current_app.logger.exception("Falha ao renderizar tela API / MCP.")
        return _fallback_integrations_shell(
            "API / MCP",
            "A interface de integrações de negócio está em contingência. Você ainda pode acessar as configurações de canais enquanto concluímos a estabilização.",
            links=[
                ("Configurações de Canais", "/integrations/admin"),
                ("IA Corporativa", "/configs/ai"),
            ],
        )


@integrations_bp.route("/integrations/requests")
@login_required
def integration_requests_page():
    return redirect(url_for("integrations.integrations_page"))


@integrations_bp.route("/integrations/admin")
@login_required
def integrations_admin_page():
    active_company = _safe_active_company()
    try:
        catalog = IntegrationCatalogService.build_channel_catalog()
    except Exception:
        current_app.logger.exception("Falha ao montar catálogo de canais.")
        catalog = {"summary": {"total": 0, "available": 0, "planned": 0, "discovery": 0}, "integrations": []}

    try:
        return render_template(
            "integrations_admin.html",
            active_company=active_company,
            integration_catalog=catalog,
        )
    except Exception:
        current_app.logger.exception("Falha ao renderizar Configurações de Canais.")
        return _fallback_integrations_shell(
            "Configurações de Canais",
            "A console de canais está em contingência. Use a tela API / MCP enquanto estabilizamos a administração técnica.",
            links=[
                ("API / MCP", "/integrations"),
            ],
        )


@integrations_bp.route("/integrations/tools")
@login_required
def integrations_tools_page():
    active_company = _safe_active_company()
    try:
        catalog = ToolFirstCatalogService.build_catalog(active_company)
    except Exception:
        current_app.logger.exception("Falha ao montar catálogo de tools.")
        catalog = {
            "summary": {"domains": 0, "canonical_domains": 0, "wrapper_domains": 0},
            "domains": [],
            "discovery": {"rest_endpoint": "/api/configs/ai/mcp/tool-first-catalog"},
        }

    try:
        return render_template(
            "modules/operations/ai_tools_catalog.html",
            active_company=active_company,
            tool_catalog=catalog,
        )
    except Exception:
        current_app.logger.exception("Falha ao renderizar tela de Tools.")
        return _fallback_integrations_shell(
            "Tools",
            "A interface operacional de tools está em contingência. Use a API do catálogo enquanto concluímos a estabilização.",
            links=[
                ("API / MCP", "/integrations"),
                ("Configurações de Canais", "/integrations/admin"),
                ("API do catálogo", "/api/configs/ai/mcp/tool-first-catalog"),
            ],
        )


@integrations_bp.route("/integrations/workflows")
@login_required
def integrations_workflows_page():
    active_company = _safe_active_company()
    try:
        catalog = WorkflowWorkspaceService.build_catalog(active_company)
    except Exception:
        current_app.logger.exception("Falha ao montar catálogo de workflows.")
        catalog = {"summary": {"workflow_count": 0, "active_workflow_count": 0}, "workflows": []}

    try:
        return render_template(
            "workflows.html",
            active_company=active_company,
            workflow_catalog=catalog,
        )
    except Exception:
        current_app.logger.exception("Falha ao renderizar tela de Workflows.")
        return _fallback_integrations_shell(
            "Workflows",
            "A interface operacional de workflows está em contingência. Use o catálogo do Sapiens enquanto concluímos a estabilização.",
            links=[
                ("Sapiens", "/sapiens"),
                ("API / MCP", "/integrations"),
            ],
        )


@integrations_bp.route("/api/integrations/catalog", methods=["GET"])
@login_required
def integrations_catalog():
    try:
        catalog = IntegrationCatalogService.build_catalog()
    except Exception:
        current_app.logger.exception("Falha ao montar payload do catálogo de integrações.")
        return jsonify({"success": False, "error": "Não foi possível carregar o catálogo agora."}), 500

    return jsonify({"success": True, "catalog": catalog})


@integrations_bp.route("/api/integrations/catalog/<string:integration_key>", methods=["GET"])
@login_required
def integrations_catalog_detail(integration_key: str):
    item = IntegrationCatalogService.get_integration(integration_key)
    if item is None:
        return jsonify({"success": False, "error": "Integração não encontrada."}), 404
    return jsonify({"success": True, "integration": item})


@integrations_bp.route("/api/integrations/requests", methods=["GET"])
@login_required
def list_integration_requests():
    company = _safe_active_company()
    return jsonify(
        {
            "success": True,
            "requests": IntegrationRequestService.list_requests(
                company_id=getattr(company, "id", None),
                limit=request.args.get("limit", default=20, type=int),
                requester_user_id=int(current_user.id),
                requester_name=getattr(current_user, "name", None),
            ),
        }
    )


@integrations_bp.route("/api/integrations/tools/requests", methods=["GET"])
@login_required
def list_tool_requests():
    company = _safe_active_company()
    return jsonify(
        {
            "success": True,
            "requests": ToolBacklogService.list_requests(
                active_company=company,
                limit=request.args.get("limit", default=100, type=int),
                requester_user_id=int(current_user.id),
                requester_name=getattr(current_user, "name", None),
            ),
        }
    )


@integrations_bp.route("/api/integrations/tools/requests", methods=["POST"])
@login_required
def create_tool_request():
    company = _safe_active_company()
    payload = request.get_json(silent=True) or {}
    try:
        record = ToolBacklogService.create_request(
            payload,
            company_id=getattr(company, "id", None),
            requester_user_id=int(current_user.id),
            requester_name=getattr(current_user, "name", None),
        )
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 400

    return jsonify({"success": True, "request": record}), 201


@integrations_bp.route("/api/integrations/workflows/requests", methods=["GET"])
@login_required
def list_workflow_requests():
    company = _safe_active_company()
    return jsonify(
        {
            "success": True,
            "requests": WorkflowBacklogService.list_requests(
                active_company=company,
                limit=request.args.get("limit", default=100, type=int),
                requester_user_id=int(current_user.id),
                requester_name=getattr(current_user, "name", None),
            ),
        }
    )


@integrations_bp.route("/api/integrations/workflows/requests", methods=["POST"])
@login_required
def create_workflow_request():
    company = _safe_active_company()
    payload = request.get_json(silent=True) or {}
    try:
        record = WorkflowBacklogService.create_request(
            payload,
            company_id=getattr(company, "id", None),
            requester_user_id=int(current_user.id),
            requester_name=getattr(current_user, "name", None),
        )
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 400

    return jsonify({"success": True, "request": record}), 201


@integrations_bp.route("/api/integrations/workflows/spec-draft", methods=["POST"])
@login_required
def build_workflow_spec_draft():
    payload = request.get_json(silent=True) or {}
    try:
        draft = WorkflowSpecDraftService.build_draft(payload)
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 400
    return jsonify({"success": True, "spec_draft": draft})


@integrations_bp.route("/api/integrations/requests", methods=["POST"])
@login_required
def create_integration_request():
    company = _safe_active_company()
    company_id = getattr(company, "id", None)
    if not company_id:
        return jsonify({"success": False, "error": "Empresa ativa obrigatória para solicitar integração."}), 400

    payload = request.get_json(silent=True) or {}
    try:
        record = IntegrationRequestService.create_request(
            payload,
            company_id=int(company_id),
            requester_user_id=int(current_user.id),
            requester_name=getattr(current_user, "name", None),
        )
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 400

    return jsonify({"success": True, "request": record.to_dict()}), 201


@integrations_bp.route("/api/integrations/status", methods=["GET"])
@login_required
def integrations_status():
    return jsonify(
        {
            "success": True,
            "integrations": {
                "ai": _service_status("ai"),
                "email": _service_status("email"),
                "whatsapp": _service_status("whatsapp"),
                "telegram": _service_status("telegram"),
                "instagram": _service_status("instagram"),
            },
        }
    )


@integrations_bp.route("/api/integrations/configs", methods=["GET"])
@login_required
def integrations_configs():
    return jsonify(
        {
            "success": True,
            "services": {
                "ai": _service_config_payload("ai"),
                "email": _service_config_payload("email"),
                "whatsapp": _service_config_payload("whatsapp"),
                "telegram": _service_config_payload("telegram"),
                "instagram": _service_config_payload("instagram"),
            },
        }
    )


@integrations_bp.route("/api/integrations/requirements", methods=["GET"])
@login_required
def integrations_requirements():
    base_url = request.url_root.rstrip("/")
    channels = {
        service: _service_requirements_payload(service, base_url)
        for service in SERVICE_ORDER
    }
    return jsonify(
        {
            "success": True,
            "global_rules": {
                "accepted_users_only": True,
                "active_user_required": True,
                "identity_table": "users",
                "identity_fields": {
                    "email": "users.email",
                    "whatsapp": "users.whatsapp",
                    "telegram": "users.telegram",
                    "instagram": "users.instagram",
                },
                "notes": [
                    "Mensagens inbound sao processadas somente para usuarios cadastrados e ativos.",
                    "Credenciais de conexao ficam centralizadas em integrations.config por canal.",
                ],
            },
            "channels": channels,
        }
    )


@integrations_bp.route("/api/integrations", methods=["GET"])
@login_required
def get_integrations():
    items = [_integration_to_response(item) for item in list_integrations()]
    return jsonify({"success": True, "integrations": items})


@integrations_bp.route("/api/integrations", methods=["POST"])
@login_required
def create_or_update_integration():
    data = request.get_json(silent=True) or {}
    payload, error = _build_integration_payload(data)
    if error:
        return jsonify({"success": False, "error": error}), 400
    payload = _merge_existing_secret_values(payload)

    if not create_integration(payload):
        return jsonify({"success": False, "error": "Falha ao salvar integracao."}), 500

    saved = get_integration(payload["id"]) or payload
    return jsonify({"success": True, "integration": _integration_to_response(saved)})


@integrations_bp.route("/api/integrations/save", methods=["POST"])
@login_required
def save_integration_legacy():
    data = request.get_json(silent=True) or {}
    service = _normalize_service(data.get("service"))
    payload_data = {
        "id": f"{service}_integration",
        "name": f"Integracao {service.title()}",
        "type": service,
        "provider": _normalize_config(data.get("config")).get("provider"),
        "config": data.get("config") or {},
        "auth_type": _normalize_config(data.get("config")).get("provider"),
    }
    payload, error = _build_integration_payload(payload_data)
    if error:
        return jsonify({"success": False, "error": error}), 400
    payload = _merge_existing_secret_values(payload)

    if not create_integration(payload):
        return jsonify({"success": False, "error": "Falha ao salvar integracao."}), 500

    return jsonify({"success": True, "integration": _integration_to_response(payload)})


@integrations_bp.route("/api/integrations/<string:integration_id>", methods=["GET"])
@login_required
def get_single_integration(integration_id: str):
    item = get_integration(integration_id)
    if not item:
        return jsonify({"success": False, "error": "Integracao nao encontrada."}), 404
    return jsonify({"success": True, "integration": _integration_to_response(item)})


@integrations_bp.route("/api/integrations/<string:integration_id>", methods=["PUT", "PATCH"])
@login_required
def update_single_integration(integration_id: str):
    current = get_integration(integration_id)
    if not current:
        return jsonify({"success": False, "error": "Integracao nao encontrada."}), 404

    data = request.get_json(silent=True) or {}
    merged = {
        "id": integration_id,
        "name": data.get("name", current.get("name")),
        "provider": data.get("provider", current.get("provider")),
        "type": data.get("type", current.get("type")),
        "auth_type": data.get("auth_type", current.get("auth_type")),
        "config": data.get("config", current.get("config")),
    }
    payload, error = _build_integration_payload(merged)
    if error:
        return jsonify({"success": False, "error": error}), 400
    payload = _merge_existing_secret_values(payload)

    if not update_integration(integration_id, payload):
        return jsonify({"success": False, "error": "Falha ao atualizar integracao."}), 500

    saved = get_integration(integration_id) or payload
    return jsonify({"success": True, "integration": _integration_to_response(saved)})


@integrations_bp.route("/api/integrations/<string:integration_id>", methods=["DELETE"])
@login_required
def delete_single_integration(integration_id: str):
    if not delete_integration(integration_id):
        return jsonify({"success": False, "error": "Falha ao excluir integracao."}), 500
    return jsonify({"success": True})


@integrations_bp.route("/api/integrations/test/<string:service>", methods=["POST"])
@login_required
def test_service(service: str):
    normalized = _normalize_service(service)
    if normalized not in SUPPORTED_SERVICES:
        return jsonify({"success": False, "error": f"Servico invalido: {service}"}), 400

    resolved = _resolve_service_config(normalized)
    result = _execute_test(normalized, resolved["config"])
    return jsonify(
        {
            "success": bool(result.get("success")),
            "service": normalized,
            "source": resolved["source"],
            "integration_id": resolved["integration_id"],
            "result": result,
        }
    )


@integrations_bp.route("/api/integrations/<string:integration_id>/test", methods=["POST"])
@login_required
def test_integration_by_id(integration_id: str):
    item = get_integration(integration_id)
    if not item:
        fallback_service = _service_from_integration_identifier(integration_id)
        if not fallback_service:
            return jsonify({"success": False, "error": "Integracao nao encontrada."}), 404

        resolved = _resolve_service_config(fallback_service)
        result = _execute_test(fallback_service, resolved["config"])
        return jsonify(
            {
                "success": bool(result.get("success")),
                "service": fallback_service,
                "integration_id": resolved["integration_id"] or integration_id,
                "source": resolved["source"],
                "result": result,
            }
        )

    service = _normalize_service(item.get("type"))
    if service not in SUPPORTED_SERVICES:
        return jsonify(
            {
                "success": False,
                "error": "Teste suportado apenas para integracoes dos canais configuraveis.",
            }
        ), 400

    config = _normalize_config(item.get("config"))
    provider = str(_coalesce(config.get("provider"), item.get("provider"), "disabled")).lower()
    config = {**config, "provider": provider}
    result = _execute_test(service, config)

    return jsonify(
        {
            "success": bool(result.get("success")),
            "service": service,
            "integration_id": integration_id,
            "result": result,
        }
    )
