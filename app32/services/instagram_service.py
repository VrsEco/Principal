import logging
import os
from typing import Any, Dict, Optional

import requests

logger = logging.getLogger(__name__)


class InstagramService:
    """Service for Instagram integration and connection checks."""

    def __init__(self):
        self.provider = os.environ.get("INSTAGRAM_PROVIDER", "meta").strip().lower()
        self.access_token = os.environ.get("INSTAGRAM_ACCESS_TOKEN")
        self.business_account_id = os.environ.get("INSTAGRAM_BUSINESS_ACCOUNT_ID")
        self.webhook_url = os.environ.get("INSTAGRAM_WEBHOOK_URL")
        self.graph_api_base = os.environ.get(
            "INSTAGRAM_GRAPH_API_BASE", "https://graph.facebook.com/v21.0"
        ).rstrip("/")
        self.app_id = os.environ.get("INSTAGRAM_APP_ID")
        self.app_secret = os.environ.get("INSTAGRAM_APP_SECRET")
        self.verify_token = os.environ.get("INSTAGRAM_VERIFY_TOKEN")

    def send_message(self, recipient_id: str, message: str) -> bool:
        try:
            if self.provider == "meta":
                return self._send_meta_message(recipient_id, message)
            if self.provider == "webhook":
                return self._send_webhook_message(recipient_id, message)
            return self._send_local_message(recipient_id, message)
        except Exception:
            logger.exception("Error sending Instagram message")
            return False

    def _send_meta_message(self, recipient_id: str, message: str) -> bool:
        if not all([self.access_token, self.business_account_id, recipient_id]):
            logger.warning("Instagram Meta configuration incomplete")
            return False

        url = f"{self.graph_api_base}/{self.business_account_id}/messages"
        payload = {
            "recipient": {"id": str(recipient_id)},
            "message": {"text": message},
            "messaging_type": "RESPONSE",
            "access_token": self.access_token,
        }
        try:
            response = requests.post(url, json=payload, timeout=20)
            return response.status_code == 200
        except Exception:
            logger.exception("Instagram Meta send error")
            return False

    def _send_webhook_message(self, recipient_id: str, message: str) -> bool:
        if not self.webhook_url:
            logger.warning("Instagram webhook URL not configured")
            return False
        payload = {"recipient_id": str(recipient_id), "message": message}
        try:
            response = requests.post(self.webhook_url, json=payload, timeout=20)
            return response.status_code == 200
        except Exception:
            logger.exception("Instagram webhook send error")
            return False

    def _send_local_message(self, recipient_id: str, message: str) -> bool:
        logger.info(
            "LOCAL INSTAGRAM SIMULATION recipient_id=%s message=%s",
            recipient_id,
            message,
        )
        return True

    def test_connection(self) -> Dict[str, Any]:
        try:
            if self.provider == "meta":
                return self._test_meta_connection()
            if self.provider == "webhook":
                return self._test_webhook_connection()
            return self._test_local_connection()
        except Exception as e:
            return {"success": False, "provider": self.provider, "error": str(e)}

    def _test_meta_connection(self) -> Dict[str, Any]:
        if not all([self.access_token, self.business_account_id]):
            return {
                "success": False,
                "provider": "meta",
                "error": "Configuração Meta incompleta (access token + business account id).",
            }

        try:
            fields = "id,username,followers_count"
            url = (
                f"{self.graph_api_base}/{self.business_account_id}"
                f"?fields={fields}&access_token={self.access_token}"
            )
            response = requests.get(url, timeout=10)
            if response.status_code != 200:
                return {
                    "success": False,
                    "provider": "meta",
                    "error": f"Erro HTTP {response.status_code}",
                }

            payload = response.json()
            if payload.get("error"):
                return {
                    "success": False,
                    "provider": "meta",
                    "error": payload["error"].get("message", "Erro na API Meta"),
                }

            return {
                "success": True,
                "provider": "meta",
                "message": "Conexão com Instagram Graph API estabelecida",
                "account": {
                    "id": payload.get("id"),
                    "username": payload.get("username"),
                    "followers_count": payload.get("followers_count"),
                },
            }
        except Exception as e:
            return {"success": False, "provider": "meta", "error": str(e)}

    def _test_webhook_connection(self) -> Dict[str, Any]:
        if not self.webhook_url:
            return {
                "success": False,
                "provider": "webhook",
                "error": "URL do webhook Instagram não configurada",
            }
        try:
            response = requests.post(
                self.webhook_url,
                json={"test": True, "message": "Teste de conexão Instagram"},
                timeout=10,
            )
            if response.status_code == 200:
                return {
                    "success": True,
                    "provider": "webhook",
                    "message": "Conexão com webhook Instagram estabelecida",
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
            "message": "Modo local ativo - Instagram simulado",
        }


instagram_service = InstagramService()
