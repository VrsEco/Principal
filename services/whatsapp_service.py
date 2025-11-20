import logging
import os
import requests
from typing import List, Optional, Dict, Any
from datetime import datetime


class WhatsAppService:
    """Service for WhatsApp integration with multiple providers"""

    def __init__(self):
        self.provider = os.environ.get("WHATSAPP_PROVIDER", "z-api")
        self.api_key = os.environ.get("WHATSAPP_API_KEY")
        self.webhook_url = os.environ.get("WHATSAPP_WEBHOOK_URL")
        self.instance_id = os.environ.get("WHATSAPP_INSTANCE_ID")

    def send_message(
        self, phone_number: str, message: str, media_url: Optional[str] = None
    ) -> bool:
        """
        Send WhatsApp message

        Args:
            phone_number: Phone number with country code (e.g., 5511999999999)
            message: Message text
            media_url: URL of media to send (optional)

        Returns:
            True if sent successfully, False otherwise
        """
        try:
            if self.provider == "z-api":
                return self._send_zapi_message(phone_number, message, media_url)
            elif self.provider == "twilio":
                return self._send_twilio_message(phone_number, message, media_url)
            elif self.provider == "webhook":
                return self._send_webhook_message(phone_number, message, media_url)
            else:
                return self._send_local_message(phone_number, message, media_url)
        except Exception as e:
            logger.info(f"Error sending WhatsApp message: {e}")
            return False

    def _send_zapi_message(
        self, phone_number: str, message: str, media_url: Optional[str] = None
    ) -> bool:
        """Send message using Z-API"""
        if not all([self.api_key, self.instance_id]):
            logger.info("Z-API configuration incomplete")
            return False

        # Clean phone number (remove spaces, dashes, parentheses)
        clean_phone = "".join(filter(str.isdigit, phone_number))
        if not clean_phone.startswith("55"):  # Brazil country code
            clean_phone = "55" + clean_phone

        url = f"https://api.z-api.io/instances/{self.instance_id}/token/{self.api_key}/send-text"

        payload = {"phone": clean_phone, "message": message}

        if media_url:
            payload["media"] = media_url

        try:
            response = requests.post(url, json=payload, timeout=30)
            return response.status_code == 200
        except Exception as e:
            logger.info(f"Z-API error: {e}")
            return False

    def _send_twilio_message(
        self, phone_number: str, message: str, media_url: Optional[str] = None
    ) -> bool:
        """Send message using Twilio"""
        if not self.api_key:  # Twilio uses account_sid as api_key
            logger.info("Twilio configuration incomplete")
            return False

        # Clean phone number
        clean_phone = "".join(filter(str.isdigit, phone_number))
        if not clean_phone.startswith("55"):
            clean_phone = "55" + clean_phone

        url = f"https://api.twilio.com/2010-04-01/Accounts/{self.api_key}/Messages.json"

        payload = {
            "From": f"whatsapp:+{self.instance_id}",  # Twilio WhatsApp number
            "To": f"whatsapp:+{clean_phone}",
            "Body": message,
        }

        if media_url:
            payload["MediaUrl"] = media_url

        try:
            response = requests.post(
                url,
                data=payload,
                auth=(self.api_key, os.environ.get("TWILIO_AUTH_TOKEN")),
                timeout=30,
            )
            return response.status_code == 201
        except Exception as e:
            logger.info(f"Twilio error: {e}")
            return False

    def _send_webhook_message(
        self, phone_number: str, message: str, media_url: Optional[str] = None
    ) -> bool:
        """Send message using webhook"""
        if not self.webhook_url:
            logger.info("WhatsApp webhook URL not configured")
            return False

        payload = {
            "phone_number": phone_number,
            "message": message,
            "media_url": media_url,
            "timestamp": str(datetime.utcnow()),
        }

        try:
            response = requests.post(self.webhook_url, json=payload, timeout=30)
            return response.status_code == 200
        except Exception as e:
            logger.info(f"Webhook error: {e}")
            return False

    def _send_local_message(
        self, phone_number: str, message: str, media_url: Optional[str] = None
    ) -> bool:
        """Simulate WhatsApp message sending locally"""
        logger.info(f"LOCAL WHATSAPP SIMULATION:")
        logger.info(f"To: {phone_number}")
        logger.info(f"Message: {message}")
        if media_url:
            logger.info(f"Media: {media_url}")
        logger.info("=" * 50)
        return True

    def test_connection(self) -> Dict[str, Any]:
        """
        Testa a conexÃ£o com o provedor de WhatsApp configurado

        Returns:
            Resultado do teste de conexÃ£o
        """
        try:
            if self.provider == "z-api":
                return self._test_zapi_connection()
            elif self.provider == "twilio":
                return self._test_twilio_connection()
            elif self.provider == "webhook":
                return self._test_webhook_connection()
            else:
                return self._test_local_connection()
        except Exception as e:
            return {"success": False, "error": str(e), "provider": self.provider}

    def _test_zapi_connection(self) -> Dict[str, Any]:
        """Testa conexÃ£o com Z-API"""
        if not all([self.api_key, self.instance_id]):
            return {
                "success": False,
                "error": "ConfiguraÃ§Ã£o Z-API incompleta (API key e Instance ID necessÃ¡rios)",
                "provider": "z-api",
            }

        try:
            # Testar conexÃ£o Z-API
            url = f"https://api.z-api.io/instances/{self.instance_id}/token/{self.api_key}/status"
            response = requests.get(url, timeout=10)

            if response.status_code == 200:
                result = response.json()
                if result.get("status") == "connected":
                    return {
                        "success": True,
                        "provider": "z-api",
                        "message": "ConexÃ£o Z-API estabelecida com sucesso",
                    }
                else:
                    return {
                        "success": False,
                        "error": f'Z-API nÃ£o conectado: {result.get("status", "unknown")}',
                        "provider": "z-api",
                    }
            else:
                return {
                    "success": False,
                    "error": f"Erro HTTP {response.status_code}",
                    "provider": "z-api",
                }
        except Exception as e:
            return {"success": False, "error": str(e), "provider": "z-api"}

    def _test_twilio_connection(self) -> Dict[str, Any]:
        """Testa conexÃ£o com Twilio"""
        account_sid = os.environ.get("TWILIO_ACCOUNT_SID")
        auth_token = os.environ.get("TWILIO_AUTH_TOKEN")

        if not all([account_sid, auth_token]):
            return {
                "success": False,
                "error": "ConfiguraÃ§Ã£o Twilio incompleta (Account SID e Auth Token necessÃ¡rios)",
                "provider": "twilio",
            }

        try:
            # Testar conexÃ£o Twilio
            url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}.json"
            response = requests.get(url, auth=(account_sid, auth_token), timeout=10)

            if response.status_code == 200:
                return {
                    "success": True,
                    "provider": "twilio",
                    "message": "ConexÃ£o Twilio estabelecida com sucesso",
                }
            else:
                return {
                    "success": False,
                    "error": f"Erro HTTP {response.status_code}",
                    "provider": "twilio",
                }
        except Exception as e:
            return {"success": False, "error": str(e), "provider": "twilio"}

    def _test_webhook_connection(self) -> Dict[str, Any]:
        """Testa conexÃ£o com webhook"""
        if not self.webhook_url:
            return {
                "success": False,
                "error": "URL do webhook nÃ£o configurada",
                "provider": "webhook",
            }

        try:
            response = requests.post(
                self.webhook_url,
                json={"test": True, "message": "Teste de conexÃ£o WhatsApp"},
                timeout=10,
            )

            if response.status_code == 200:
                return {
                    "success": True,
                    "provider": "webhook",
                    "message": "ConexÃ£o com webhook estabelecida com sucesso",
                }
            else:
                return {
                    "success": False,
                    "error": f"Erro HTTP {response.status_code}",
                    "provider": "webhook",
                }
        except Exception as e:
            return {"success": False, "error": str(e), "provider": "webhook"}

    def _test_local_connection(self) -> Dict[str, Any]:
        """Testa conexÃ£o local"""
        return {
            "success": True,
            "provider": "local",
            "message": "Modo local ativo - WhatsApp simulado",
        }

    def send_welcome_message(
        self, phone_number: str, participant_name: str, plan_name: str
    ) -> bool:
        """Send welcome WhatsApp message to participant"""
        message = f"""
        ðŸŽ‰ *Bem-vindo ao Planejamento EstratÃ©gico!*

        OlÃ¡ *{participant_name}*!

        VocÃª foi convidado a participar do plano estratÃ©gico *"{plan_name}"*.

        Sua contribuiÃ§Ã£o Ã© muito importante para o sucesso desta iniciativa! ðŸš€

        Em breve vocÃª receberÃ¡ mais informaÃ§Ãµes sobre como participar.

        Se tiver alguma dÃºvida, nÃ£o hesite em entrar em contato conosco.

        Atenciosamente,
        Equipe de Planejamento EstratÃ©gico
        """

        return self.send_message(phone_number, message)

    def send_reminder_message(
        self,
        phone_number: str,
        participant_name: str,
        task_description: str,
        deadline: str,
    ) -> bool:
        """Send reminder WhatsApp message"""
        message = f"""
        â° *Lembrete Importante*

        OlÃ¡ *{participant_name}*!

        VocÃª tem uma tarefa pendente no planejamento estratÃ©gico:

        ðŸ“‹ *Tarefa:* {task_description}
        ðŸ“… *Prazo:* {deadline}

        Por favor, nÃ£o esqueÃ§a de concluir esta atividade.

        Obrigado pela sua contribuiÃ§Ã£o! ðŸ™
        """

        return self.send_message(phone_number, message)


# Singleton instance
whatsapp_service = WhatsAppService()
