import logging
import os
from typing import Any, Dict, Optional

import requests

logger = logging.getLogger(__name__)
from utils.integration_settings import resolve_service_config, resolve_telegram_bot_token


class TelegramService:
    """Service for Telegram integration and connectivity checks."""

    def __init__(self):
        resolved = resolve_service_config("telegram")
        config = resolved.get("config") or {}
        self.provider = str(resolved.get("provider") or "bot_api").strip().lower()
        self.bot_token = config.get("bot_token")
        self.bot_token_dev = config.get("bot_token_dev")
        self.bot_token_prod = config.get("bot_token_prod")
        self.telegram_env = str(config.get("telegram_env") or "").strip().lower()
        self.flask_env = (
            os.environ.get("FLASK_ENV") or os.environ.get("FLASK_CONFIG") or ""
        ).strip().lower()
        self.webhook_url = config.get("webhook_url")
        self.external_url = config.get("external_url")
        self.webhook_path = config.get("webhook_path") or "/webhook/telegram"
        self.setup_webhook = bool(config.get("setup_webhook"))

    def send_message(
        self, chat_id: str, message: str, parse_mode: str = "HTML"
    ) -> bool:
        try:
            if self.provider == "bot_api":
                return self._send_bot_api_message(chat_id, message, parse_mode=parse_mode)
            if self.provider == "webhook":
                return self._send_webhook_message(chat_id, message)
            return self._send_local_message(chat_id, message)
        except Exception:
            logger.exception("Error sending Telegram message")
            return False

    def _send_bot_api_message(
        self, chat_id: str, message: str, parse_mode: str = "HTML"
    ) -> bool:
        token = self._resolve_bot_token()
        if not token:
            logger.warning("Telegram token not configured")
            return False

        payload = {"chat_id": str(chat_id), "text": message, "parse_mode": parse_mode}
        try:
            response = requests.post(
                self._telegram_api_url(token, "sendMessage"),
                json=payload,
                timeout=20,
            )
            if response.status_code != 200:
                return False
            data = response.json()
            return bool(data.get("ok"))
        except Exception:
            logger.exception("Telegram Bot API send error")
            return False

    def _send_webhook_message(self, chat_id: str, message: str) -> bool:
        if not self.webhook_url:
            logger.warning("Telegram webhook URL not configured")
            return False

        payload = {"chat_id": str(chat_id), "message": message}
        try:
            response = requests.post(self.webhook_url, json=payload, timeout=20)
            return response.status_code == 200
        except Exception:
            logger.exception("Telegram webhook send error")
            return False

    def _send_local_message(self, chat_id: str, message: str) -> bool:
        logger.info("LOCAL TELEGRAM SIMULATION chat_id=%s message=%s", chat_id, message)
        return True

    def test_connection(self) -> Dict[str, Any]:
        try:
            if self.provider == "bot_api":
                return self._test_bot_api_connection()
            if self.provider == "webhook":
                return self._test_webhook_connection()
            return self._test_local_connection()
        except Exception as e:
            return {"success": False, "error": str(e), "provider": self.provider}

    def _test_bot_api_connection(self) -> Dict[str, Any]:
        token = self._resolve_bot_token()
        if not token:
            return {
                "success": False,
                "provider": "bot_api",
                "error": "Token do bot Telegram não configurado",
            }

        try:
            response = requests.get(
                self._telegram_api_url(token, "getMe"),
                timeout=10,
            )
            if response.status_code != 200:
                return {
                    "success": False,
                    "provider": "bot_api",
                    "error": f"Erro HTTP {response.status_code}",
                }

            payload = response.json()
            if not payload.get("ok"):
                return {
                    "success": False,
                    "provider": "bot_api",
                    "error": payload.get("description", "Falha no getMe"),
                }

            result = payload.get("result", {})
            output: Dict[str, Any] = {
                "success": True,
                "provider": "bot_api",
                "message": "Conexão com Telegram Bot API estabelecida",
                "bot": {
                    "id": result.get("id"),
                    "username": result.get("username"),
                    "first_name": result.get("first_name"),
                },
            }

            if self.setup_webhook and self.external_url:
                output["webhook"] = self._inspect_webhook(token)
            return output
        except Exception as e:
            return {"success": False, "provider": "bot_api", "error": str(e)}

    def _inspect_webhook(self, token: str) -> Dict[str, Any]:
        expected_url = f"{self.external_url.rstrip('/')}{self.webhook_path}"
        try:
            response = requests.get(
                self._telegram_api_url(token, "getWebhookInfo"),
                timeout=10,
            )
            if response.status_code != 200:
                return {
                    "success": False,
                    "expected_url": expected_url,
                    "error": f"Erro HTTP {response.status_code} ao consultar webhook",
                }

            data = response.json()
            if not data.get("ok"):
                return {
                    "success": False,
                    "expected_url": expected_url,
                    "error": data.get("description", "Falha ao consultar webhook"),
                }

            webhook_info = data.get("result", {})
            current_url = webhook_info.get("url")
            return {
                "success": current_url == expected_url,
                "expected_url": expected_url,
                "current_url": current_url,
                "pending_update_count": webhook_info.get("pending_update_count"),
            }
        except Exception as e:
            return {"success": False, "expected_url": expected_url, "error": str(e)}

    def _test_webhook_connection(self) -> Dict[str, Any]:
        if not self.webhook_url:
            return {
                "success": False,
                "provider": "webhook",
                "error": "URL do webhook Telegram não configurada",
            }

        try:
            response = requests.post(
                self.webhook_url,
                json={"test": True, "message": "Teste de conexão Telegram"},
                timeout=10,
            )
            if response.status_code == 200:
                return {
                    "success": True,
                    "provider": "webhook",
                    "message": "Conexão com webhook Telegram estabelecida",
                }
            return {
                "success": False,
                "provider": "webhook",
                "error": f"Erro HTTP {response.status_code}",
            }
        except Exception as e:
            return {"success": False, "provider": "webhook", "error": str(e)}

    def _test_local_connection(self) -> Dict[str, Any]:
        return {
            "success": True,
            "provider": "local",
            "message": "Modo local ativo - Telegram simulado",
        }

    def _resolve_bot_token(self) -> Optional[str]:
        token, _ = resolve_telegram_bot_token()
        return token

    @staticmethod
    def _telegram_api_url(token: str, method: str) -> str:
        return f"https://api.telegram.org/bot{token}/{method}"


telegram_service = TelegramService()
