import html
import logging
import os
import re
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
from src.core.theme_tokens import get_summary_email_theme

logger = logging.getLogger(__name__)


class EmailService:
    """Service for email integration with multiple providers"""

    def __init__(self):
        self.provider = os.environ.get("EMAIL_PROVIDER", "smtp")
        self.smtp_server = os.environ.get("MAIL_SERVER")
        self.smtp_port = int(os.environ.get("MAIL_PORT") or 587)
        self.smtp_use_tls = os.environ.get("MAIL_USE_TLS", "true").strip().lower() == "true"
        self.smtp_use_ssl = os.environ.get("MAIL_USE_SSL", "false").strip().lower() == "true"
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

    def _load_db_config_fallback(self) -> None:
        """
        Fallback para credenciais salvas em integrations (type='email').
        Mantém compatibilidade com a tela de integrações do sistema.
        """
        try:
            from database.postgresql_db import get_integration

            record = get_integration("email_integration")
            if not record:
                return

            config = record.get("config") if isinstance(record.get("config"), dict) else {}
            provider = (config.get("provider") or record.get("provider") or self.provider or "smtp")
            provider = str(provider).strip().lower() or "smtp"

            self.provider = provider
            self.smtp_server = self.smtp_server or config.get("server")
            self.smtp_port = int(config.get("port") or self.smtp_port or 587)
            if "use_tls" in config:
                self.smtp_use_tls = bool(config.get("use_tls"))
            if "use_ssl" in config:
                self.smtp_use_ssl = bool(config.get("use_ssl"))
            self.smtp_username = self.smtp_username or config.get("username")
            self.smtp_secret = self.smtp_secret or config.get("password")
            self.default_sender = self.default_sender or config.get("default_sender") or config.get("from_email")
            self.from_name = config.get("from_name") or self.from_name
            self.webhook_url = self.webhook_url or config.get("webhook_url")
            self.inbound_protocol = str(config.get("inbound_protocol") or self.inbound_protocol or "").strip().lower()
            self.inbound_host = self.inbound_host or config.get("inbound_host")
            self.inbound_port = int(config.get("inbound_port") or self.inbound_port or 0)
            self.inbound_username = self.inbound_username or config.get("inbound_username")
            self.inbound_password = self.inbound_password or config.get("inbound_password")
            if "inbound_use_ssl" in config:
                self.inbound_use_ssl = bool(config.get("inbound_use_ssl"))
        except Exception as err:
            logger.debug("Falha ao carregar configuracao Email do DB: %s", err)

    def _reload_runtime_config(self) -> None:
        self.__init__()
        provider = (self.provider or "smtp").strip().lower()
        if provider == "smtp" and (not self.smtp_server or not self.smtp_username or not self.smtp_secret):
            self._load_db_config_fallback()
        elif provider == "webhook" and not self.webhook_url:
            self._load_db_config_fallback()

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
            self._reload_runtime_config()
            html_body = html_body or self.build_transactional_email_html(
                subject=subject,
                body=body,
            )
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

    def build_transactional_email_html(
        self,
        subject: str,
        body: str,
        *,
        preheader: Optional[str] = None,
        eyebrow: str = "Sapiens • Versus Gestão Corporativa",
        title: Optional[str] = None,
        footer_note: str = "Mensagem automática enviada pelo Sapiens.",
    ) -> str:
        theme = get_summary_email_theme()
        safe_subject = html.escape(str(subject or "Comunicação Versus"))
        safe_title = html.escape(str(title or subject or "Comunicação Versus"))
        safe_preheader = html.escape(
            str(preheader or self._build_email_preheader(body=body))
        )
        safe_footer_note = html.escape(str(footer_note or ""))
        body_html = self._render_transactional_body_html(body or "")

        return f"""
<!doctype html>
<html lang="pt-BR">
  <body style="margin:0;padding:0;background:{theme['page_bg']};font-family:Segoe UI,Arial,sans-serif;color:{theme['text_primary']};">
    <div style="display:none;max-height:0;overflow:hidden;opacity:0;color:transparent;">
      {safe_preheader}
    </div>
    <div style="max-width:920px;margin:24px auto;padding:0 14px;">
      <div style="background:{theme['header_gradient']};color:#fff;border-radius:16px;padding:24px 28px;box-shadow:0 8px 22px rgba(15,23,42,.22);">
        <div style="font-size:11px;opacity:.95;letter-spacing:.8px;text-transform:uppercase;font-weight:700;">{html.escape(eyebrow)}</div>
        <h1 style="margin:10px 0 6px;font-size:25px;line-height:1.25;font-weight:800;">{safe_title}</h1>
        <div style="font-size:14px;opacity:.98;line-height:1.5;">
          Assunto: <strong>{safe_subject}</strong><br>
          Data base: <strong>{html.escape(datetime.now().strftime('%d/%m/%Y %H:%M'))}</strong>
        </div>
      </div>

      <div style="background:{theme['card_bg']};border:1px solid {theme['card_border']};border-radius:16px;padding:22px 24px;margin-top:14px;line-height:1.65;">
        {body_html}
      </div>

      <div style="background:{theme['card_bg']};border:1px solid {theme['card_border']};border-radius:16px;padding:18px 24px;margin-top:14px;">
        <div style="font-size:16px;font-weight:800;color:{theme['text_primary']};">Sapiens Versus</div>
        <div style="font-size:14px;color:{theme['signature_accent']};font-weight:700;margin-top:2px;">Versus Gestão Corporativa</div>
        <div style="font-size:13px;color:{theme['text_secondary']};margin-top:8px;">
          E-mail:
          <a href="mailto:sapiens@gestaoversus.com.br" style="color:{theme['signature_accent']};text-decoration:none;">sapiens@gestaoversus.com.br</a>
        </div>
        <div style="font-size:13px;color:{theme['text_secondary']};margin-top:4px;">Telefone: 71 9 8238-5225</div>
        <div style="margin-top:14px;">
          <img src="cid:versus_signature_logo" alt="Versus Gestão Corporativa" style="max-width:280px;width:100%;height:auto;display:block;border:0;">
        </div>
      </div>

      <div style="text-align:center;color:{theme['text_muted']};font-size:12px;margin:14px 0 6px;">
        {safe_footer_note}
      </div>
    </div>
  </body>
</html>
"""

    def _build_email_preheader(self, body: str) -> str:
        normalized = re.sub(r"\s+", " ", str(body or "").strip())
        if not normalized:
            return "Atualização automática enviada pelo Sapiens."
        return normalized[:140]

    def _render_transactional_body_html(self, body: str) -> str:
        theme = get_summary_email_theme()
        blocks: List[str] = []
        current_list: List[str] = []

        def flush_list() -> None:
            nonlocal current_list
            if not current_list:
                return
            items = "".join(
                f"<li style='margin:0 0 8px;'>{item}</li>" for item in current_list
            )
            blocks.append(
                f"<ul style='margin:0 0 16px 20px;padding:0;color:{theme['text_secondary']};font-size:14px;line-height:1.7;'>{items}</ul>"
            )
            current_list = []

        for raw_line in str(body or "").splitlines():
            line = raw_line.strip()
            if not line:
                flush_list()
                continue

            bullet = None
            if line.startswith("- "):
                bullet = line[2:].strip()
            elif line.startswith("• "):
                bullet = line[2:].strip()
            elif re.match(r"^\d+\.\s+", line):
                bullet = re.sub(r"^\d+\.\s+", "", line, count=1).strip()

            if bullet is not None:
                current_list.append(self._render_inline_email_html(bullet))
                continue

            flush_list()
            line_html = self._render_inline_email_html(line)
            if line.endswith(":"):
                blocks.append(
                    f"<div style='margin:16px 0 8px;font-size:13px;font-weight:800;letter-spacing:.4px;text-transform:uppercase;color:{theme['signature_accent']};'>{line_html}</div>"
                )
            else:
                blocks.append(
                    f"<p style='margin:0 0 14px;font-size:14px;color:{theme['text_secondary']};line-height:1.7;'>{line_html}</p>"
                )

        flush_list()
        if not blocks:
            blocks.append(
                f"<p style='margin:0;font-size:14px;color:{theme['text_secondary']};line-height:1.7;'>Sem conteúdo adicional.</p>"
            )
        return "".join(blocks)

    def _render_inline_email_html(self, text: str) -> str:
        safe = html.escape(str(text or ""))
        safe = re.sub(
            r"(https?://[^\s<]+)",
            r"<a href='\1' style='color:#0f766e;text-decoration:none;font-weight:700;'>\1</a>",
            safe,
        )
        safe = re.sub(
            r"([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})",
            r"<a href='mailto:\1' style='color:#0f766e;text-decoration:none;font-weight:700;'>\1</a>",
            safe,
        )
        safe = re.sub(r"\*([^\*]+)\*", r"<strong>\1</strong>", safe)
        return safe

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
            if self.smtp_use_ssl:
                server = smtplib.SMTP_SSL(self.smtp_server, self.smtp_port)
            else:
                server = smtplib.SMTP(self.smtp_server, self.smtp_port)
                if self.smtp_use_tls:
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
        self._reload_runtime_config()
        if not all([self.smtp_server, self.smtp_username, self.smtp_secret]):
            return {
                "success": False,
                "error": "ConfiguraÃ§Ã£o SMTP incompleta",
                "provider": "smtp",
            }

        try:
            # Testar conexÃ£o SMTP
            if self.smtp_use_ssl:
                server = smtplib.SMTP_SSL(self.smtp_server, self.smtp_port)
            else:
                server = smtplib.SMTP(self.smtp_server, self.smtp_port)
                if self.smtp_use_tls:
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
        subject = f"Bem-vindo ao Planejamento Estratégico - {plan_name}"

        body = f"""
Olá {participant_name},

Bem-vindo ao processo de planejamento estratégico da empresa.

Você foi convidado a participar do plano "{plan_name}" e sua contribuição é muito importante para o sucesso desta iniciativa.

Em breve você receberá mais informações sobre como participar e contribuir com o processo.

Se tiver alguma dúvida, não hesite em entrar em contato conosco.

Atenciosamente,
Equipe de Planejamento Estratégico
        """.strip()

        html_body = self.build_transactional_email_html(
            subject=subject,
            body=body,
            title="Bem-vindo ao Planejamento Estratégico",
            preheader=f"Convite para participação no plano {plan_name}.",
        )

        return self.send_email([participant_email], subject, body, html_body)



# Singleton instance
email_service = EmailService()
