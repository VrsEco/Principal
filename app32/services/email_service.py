import logging
import os
import smtplib
import poplib
import imaplib
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.image import MIMEImage
from email import encoders
from email.utils import formataddr
from typing import List, Optional, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class EmailService:
    """Service for email integration with multiple providers"""

    def __init__(self):
        self.provider = os.environ.get("EMAIL_PROVIDER", "smtp")
        self.smtp_server = os.environ.get("MAIL_SERVER")
        self.smtp_port = int(os.environ.get("MAIL_PORT") or 587)
        self.smtp_username = os.environ.get("MAIL_USERNAME")
        self.smtp_secret = os.environ.get("MAIL_PASSWORD")
        self.default_sender = os.environ.get("MAIL_DEFAULT_SENDER")
        self.from_name = os.environ.get(
            "MAIL_FROM_NAME", "Sapiens (Versus Gestão Corporativa)"
        )
        self.webhook_url = os.environ.get("EMAIL_WEBHOOK_URL")
        self.inbound_protocol = (
            os.environ.get("EMAIL_INBOUND_PROTOCOL", "").strip().lower()
        )
        self.inbound_host = os.environ.get("EMAIL_INBOUND_HOST")
        self.inbound_port = int(os.environ.get("EMAIL_INBOUND_PORT") or 0)
        self.inbound_username = os.environ.get("EMAIL_INBOUND_USERNAME")
        self.inbound_password = os.environ.get("EMAIL_INBOUND_PASSWORD")
        self.inbound_use_ssl = (
            os.environ.get("EMAIL_INBOUND_USE_SSL", "true").strip().lower() == "true"
        )

    def send_email(
        self,
        to_emails: List[str],
        subject: str,
        body: str,
        html_body: Optional[str] = None,
        attachments: Optional[List[str]] = None,
    ) -> bool:
        """
        Send email to recipients

        Args:
            to_emails: List of recipient email addresses
            subject: Email subject
            body: Plain text body
            html_body: HTML body (optional)
            attachments: List of file paths to attach

        Returns:
            True if sent successfully, False otherwise
        """
        try:
            if self.provider == "smtp":
                return self._send_smtp_email(
                    to_emails, subject, body, html_body, attachments
                )
            elif self.provider == "webhook":
                return self._send_webhook_email(
                    to_emails, subject, body, html_body, attachments
                )
            else:
                return self._send_local_email(
                    to_emails, subject, body, html_body, attachments
                )
        except Exception:
            logger.exception("Error sending email")
            return False

    def _send_smtp_email(
        self,
        to_emails: List[str],
        subject: str,
        body: str,
        html_body: Optional[str] = None,
        attachments: Optional[List[str]] = None,
    ) -> bool:
        """Send email using SMTP"""
        if not all([self.smtp_server, self.smtp_username, self.smtp_secret]):
            logger.warning("SMTP configuration incomplete")
            return False

        try:
            # Create message
            msg = MIMEMultipart("alternative")
            sender_value = self._resolve_sender_header()
            msg["From"] = sender_value
            msg["To"] = ", ".join(to_emails)
            msg["Subject"] = subject

            # Add text body
            text_part = MIMEText(body, "plain", "utf-8")
            msg.attach(text_part)

            # Add HTML body if provided
            if html_body:
                html_part = MIMEText(html_body, "html", "utf-8")
                msg.attach(html_part)
                self._attach_inline_logo_if_requested(msg=msg, html_body=html_body)

            # Add attachments
            if attachments:
                for file_path in attachments:
                    if os.path.exists(file_path):
                        with open(file_path, "rb") as attachment:
                            part = MIMEBase("application", "octet-stream")
                            part.set_payload(attachment.read())
                            encoders.encode_base64(part)
                            part.add_header(
                                "Content-Disposition",
                                f"attachment; filename= {os.path.basename(file_path)}",
                            )
                            msg.attach(part)

            # Send email
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.smtp_username, self.smtp_secret)
            server.send_message(msg)
            server.quit()

            return True

        except Exception:
            logger.exception("SMTP error")
            return False

    def _resolve_sender_header(self) -> str:
        if self.default_sender:
            return self.default_sender
        if self.smtp_username:
            return formataddr((self.from_name, self.smtp_username))
        return self.from_name

    def _attach_inline_logo_if_requested(self, msg: MIMEMultipart, html_body: Optional[str]) -> None:
        if not html_body:
            return

        cid = "versus_signature_logo"
        if f"cid:{cid}" not in html_body:
            return

        candidates = [
            os.path.join(os.getcwd(), "static", "img", "logo-versus-slogan.png"),
            os.path.join(os.getcwd(), "static", "img", "versus-logo.png"),
            os.path.join(os.getcwd(), "static", "img", "logo-versus.png"),
        ]

        for file_path in candidates:
            if not os.path.exists(file_path):
                continue
            try:
                with open(file_path, "rb") as img_file:
                    img = MIMEImage(img_file.read())
                img.add_header("Content-ID", f"<{cid}>")
                img.add_header(
                    "Content-Disposition",
                    "inline",
                    filename=os.path.basename(file_path),
                )
                msg.attach(img)
                return
            except Exception:
                logger.exception("Falha ao anexar logo inline para assinatura.")
                return

        logger.warning("Logo de assinatura solicitada, mas arquivo não encontrado em static/img.")

    def _send_webhook_email(
        self,
        to_emails: List[str],
        subject: str,
        body: str,
        html_body: Optional[str] = None,
        attachments: Optional[List[str]] = None,
    ) -> bool:
        """Send email using webhook"""
        if not self.webhook_url:
            logger.warning("Email webhook URL not configured")
            return False

        payload = {
            "to_emails": to_emails,
            "subject": subject,
            "body": body,
            "html_body": html_body,
            "attachments": attachments,
            "timestamp": str(datetime.utcnow()),
        }

        try:
            response = requests.post(self.webhook_url, json=payload, timeout=30)
            return response.status_code == 200
        except Exception:
            logger.exception("Webhook error")
            return False

    def _send_local_email(
        self,
        to_emails: List[str],
        subject: str,
        body: str,
        html_body: Optional[str] = None,
        attachments: Optional[List[str]] = None,
    ) -> bool:
        """Simulate email sending locally"""
        logger.info(
            "LOCAL EMAIL SIMULATION to=%s subject=%s attachments=%s",
            ", ".join(to_emails),
            subject,
            attachments,
        )
        return True

    def test_connection(self) -> Dict[str, Any]:
        """
        Testa a conexÃ£o com o provedor de email configurado

        Returns:
            Resultado do teste de conexÃ£o
        """
        try:
            if self.provider == "smtp":
                result = self._test_smtp_connection()
            elif self.provider == "webhook":
                result = self._test_webhook_connection()
            else:
                result = self._test_local_connection()

            if self._has_inbound_config():
                inbound_result = self._test_inbound_connection()
                result["inbound"] = inbound_result
                if not inbound_result.get("success"):
                    result["success"] = False
            else:
                result["inbound"] = {
                    "success": True,
                    "enabled": False,
                    "message": "Leitura inbound não configurada",
                }

            return result
        except Exception as e:
            return {"success": False, "error": str(e), "provider": self.provider}

    def _has_inbound_config(self) -> bool:
        protocol = (self.inbound_protocol or "").strip().lower()
        return bool(
            protocol
            and self.inbound_host
            and self.inbound_username
            and self.inbound_password
        )

    def _test_inbound_connection(self) -> Dict[str, Any]:
        """Testa conexão de leitura de e-mails (POP3/IMAP)."""
        protocol = (self.inbound_protocol or "").strip().lower()
        if protocol in {"pop3", "pop3_ssl", "pop3s"}:
            return self._test_pop3_connection()
        if protocol in {"imap", "imap_ssl", "imaps"}:
            return self._test_imap_connection()
        return {
            "success": False,
            "enabled": True,
            "provider": protocol or "unknown",
            "error": "Protocolo inbound inválido. Use POP3 ou IMAP.",
        }

    def _test_pop3_connection(self) -> Dict[str, Any]:
        port = self.inbound_port or (995 if self.inbound_use_ssl else 110)
        try:
            if self.inbound_use_ssl:
                client = poplib.POP3_SSL(self.inbound_host, port, timeout=10)
            else:
                client = poplib.POP3(self.inbound_host, port, timeout=10)
            client.user(self.inbound_username)
            client.pass_(self.inbound_password)
            client.quit()
            return {
                "success": True,
                "enabled": True,
                "provider": "pop3",
                "message": f"Conexão POP3 estabelecida com {self.inbound_host}:{port}",
            }
        except Exception as e:
            return {
                "success": False,
                "enabled": True,
                "provider": "pop3",
                "error": str(e),
            }

    def _test_imap_connection(self) -> Dict[str, Any]:
        port = self.inbound_port or (993 if self.inbound_use_ssl else 143)
        try:
            if self.inbound_use_ssl:
                client = imaplib.IMAP4_SSL(self.inbound_host, port)
            else:
                client = imaplib.IMAP4(self.inbound_host, port)
            client.login(self.inbound_username, self.inbound_password)
            client.logout()
            return {
                "success": True,
                "enabled": True,
                "provider": "imap",
                "message": f"Conexão IMAP estabelecida com {self.inbound_host}:{port}",
            }
        except Exception as e:
            return {
                "success": False,
                "enabled": True,
                "provider": "imap",
                "error": str(e),
            }

    def _test_smtp_connection(self) -> Dict[str, Any]:
        """Testa conexÃ£o SMTP"""
        if not all([self.smtp_server, self.smtp_username, self.smtp_secret]):
            return {
                "success": False,
                "error": "ConfiguraÃ§Ã£o SMTP incompleta",
                "provider": "smtp",
            }

        try:
            # Testar conexÃ£o SMTP
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.smtp_username, self.smtp_secret)
            server.quit()

            return {
                "success": True,
                "provider": "smtp",
                "message": f"ConexÃ£o SMTP estabelecida com {self.smtp_server}:{self.smtp_port}",
            }
        except Exception as e:
            return {"success": False, "error": str(e), "provider": "smtp"}

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
                json={"test": True, "message": "Teste de conexÃ£o"},
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
            "message": "Modo local ativo - email simulado",
        }

    def send_welcome_email(
        self, participant_email: str, participant_name: str, plan_name: str
    ) -> bool:
        """Send welcome email to participant"""
        subject = f"Bem-vindo ao Planejamento EstratÃ©gico - {plan_name}"

        body = f"""
        OlÃ¡ {participant_name},
        
        Bem-vindo ao processo de planejamento estratÃ©gico da empresa!
        
        VocÃª foi convidado a participar do plano "{plan_name}" e sua contribuiÃ§Ã£o Ã© muito importante para o sucesso desta iniciativa.
        
        Em breve vocÃª receberÃ¡ mais informaÃ§Ãµes sobre como participar e contribuir com o processo.
        
        Se tiver alguma dÃºvida, nÃ£o hesite em entrar em contato conosco.
        
        Atenciosamente,
        Equipe de Planejamento EstratÃ©gico
        """

        html_body = f"""
        <html>
        <body>
            <h2>Bem-vindo ao Planejamento EstratÃ©gico!</h2>
            <p>OlÃ¡ <strong>{participant_name}</strong>,</p>
            <p>Bem-vindo ao processo de planejamento estratÃ©gico da empresa!</p>
            <p>VocÃª foi convidado a participar do plano <strong>"{plan_name}"</strong> e sua contribuiÃ§Ã£o Ã© muito importante para o sucesso desta iniciativa.</p>
            <p>Em breve vocÃª receberÃ¡ mais informaÃ§Ãµes sobre como participar e contribuir com o processo.</p>
            <p>Se tiver alguma dÃºvida, nÃ£o hesite em entrar em contato conosco.</p>
            <br>
            <p>Atenciosamente,<br>Equipe de Planejamento EstratÃ©gico</p>
        </body>
        </html>
        """

        return self.send_email([participant_email], subject, body, html_body)


# Singleton instance
email_service = EmailService()
