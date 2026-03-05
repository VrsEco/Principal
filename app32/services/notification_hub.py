from typing import Any, Dict, Iterable, Optional, Union

from models.user import User
from services.ai_service import AIService
from services.email_service import EmailService
from services.instagram_service import InstagramService
from services.telegram_service import TelegramService
from services.whatsapp_service import WhatsAppService


class NotificationHub:
    """
    Hub unificado de notificações.
    Regras e governança são centralizadas; execução é individual por canal.
    """

    def __init__(self):
        self.email = EmailService()
        self.whatsapp = WhatsAppService()
        self.telegram = TelegramService()
        self.instagram = InstagramService()
        self.ai = AIService()

    @staticmethod
    def _as_list(value: Union[str, Iterable[str]]) -> list[str]:
        if isinstance(value, str):
            return [value]
        return [item for item in value if item]

    @staticmethod
    def _validate_user(user: Optional[User]) -> Optional[Dict[str, Any]]:
        if not user:
            return {"success": False, "error": "Usuário não encontrado"}
        if not user.is_active:
            return {"success": False, "error": "Usuário inativo"}
        return None

    def send_email(
        self,
        to_emails: Union[str, Iterable[str]],
        subject: str,
        body: str,
        html_body: Optional[str] = None,
    ) -> Dict[str, Any]:
        recipients = self._as_list(to_emails)
        ok = self.email.send_email(recipients, subject, body, html_body=html_body)
        return {"success": ok, "channel": "email", "recipients": recipients}

    def send_whatsapp(self, phone_number: str, message: str) -> Dict[str, Any]:
        ok = self.whatsapp.send_message(phone_number, message)
        return {"success": ok, "channel": "whatsapp", "recipient": phone_number}

    def send_telegram(
        self, chat_id: str, message: str, parse_mode: str = "HTML"
    ) -> Dict[str, Any]:
        ok = self.telegram.send_message(chat_id, message, parse_mode=parse_mode)
        return {"success": ok, "channel": "telegram", "recipient": chat_id}

    def send_instagram(self, recipient_id: str, message: str) -> Dict[str, Any]:
        ok = self.instagram.send_message(recipient_id, message)
        return {"success": ok, "channel": "instagram", "recipient": recipient_id}

    def send_to_user(
        self,
        user: Optional[User],
        channel: str,
        message: str,
        subject: Optional[str] = None,
        html_body: Optional[str] = None,
        recipient_id: Optional[str] = None,
        parse_mode: str = "HTML",
    ) -> Dict[str, Any]:
        validation = self._validate_user(user)
        if validation:
            return validation

        normalized = (channel or "").strip().lower()
        if normalized == "email":
            if not user.email:
                return {"success": False, "error": "Usuário sem e-mail cadastrado"}
            return self.send_email(
                user.email,
                subject or "Notificação - Gestão Versus",
                message,
                html_body=html_body,
            )

        if normalized == "whatsapp":
            if not user.whatsapp:
                return {"success": False, "error": "Usuário sem WhatsApp cadastrado"}
            return self.send_whatsapp(user.whatsapp, message)

        if normalized == "telegram":
            if not user.telegram:
                return {"success": False, "error": "Usuário sem Telegram cadastrado"}
            return self.send_telegram(user.telegram, message, parse_mode=parse_mode)

        if normalized == "instagram":
            target = recipient_id or getattr(user, "instagram", None)
            if not target:
                return {
                    "success": False,
                    "error": "Usuário sem Instagram cadastrado",
                }
            return self.send_instagram(target, message)

        return {"success": False, "error": f"Canal não suportado: {channel}"}

    def test_channel(self, channel: str) -> Dict[str, Any]:
        normalized = (channel or "").strip().lower()
        if normalized == "ai":
            return self.ai.test_connection()
        if normalized == "email":
            return self.email.test_connection()
        if normalized == "whatsapp":
            return self.whatsapp.test_connection()
        if normalized == "telegram":
            return self.telegram.test_connection()
        if normalized == "instagram":
            return self.instagram.test_connection()
        return {"success": False, "error": f"Canal não suportado: {channel}"}


notification_hub = NotificationHub()
