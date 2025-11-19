import logging
import os
import smtplib
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from typing import List, Optional, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)

class EmailService:
    """Service for email integration with multiple providers"""
    
    def __init__(self):
        self.provider = os.environ.get('EMAIL_PROVIDER', 'smtp')
        self.smtp_server = os.environ.get('MAIL_SERVER')
        self.smtp_port = int(os.environ.get('MAIL_PORT') or 587)
        self.smtp_username = os.environ.get('MAIL_USERNAME')
        self.smtp_secret = os.environ.get('MAIL_PASSWORD')
        self.webhook_url = os.environ.get('EMAIL_WEBHOOK_URL')
    
    def send_email(self, to_emails: List[str], subject: str, body: str, 
                   html_body: Optional[str] = None, attachments: Optional[List[str]] = None) -> bool:
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
            if self.provider == 'smtp':
                return self._send_smtp_email(to_emails, subject, body, html_body, attachments)
            elif self.provider == 'webhook':
                return self._send_webhook_email(to_emails, subject, body, html_body, attachments)
            else:
                return self._send_local_email(to_emails, subject, body, html_body, attachments)
        except Exception:
            logger.exception("Error sending email")
            return False
    
    def _send_smtp_email(self, to_emails: List[str], subject: str, body: str, 
                        html_body: Optional[str] = None, attachments: Optional[List[str]] = None) -> bool:
        """Send email using SMTP"""
        if not all([self.smtp_server, self.smtp_username, self.smtp_secret]):
            logger.warning("SMTP configuration incomplete")
            return False
        
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['From'] = self.smtp_username
            msg['To'] = ', '.join(to_emails)
            msg['Subject'] = subject
            
            # Add text body
            text_part = MIMEText(body, 'plain', 'utf-8')
            msg.attach(text_part)
            
            # Add HTML body if provided
            if html_body:
                html_part = MIMEText(html_body, 'html', 'utf-8')
                msg.attach(html_part)
            
            # Add attachments
            if attachments:
                for file_path in attachments:
                    if os.path.exists(file_path):
                        with open(file_path, 'rb') as attachment:
                            part = MIMEBase('application', 'octet-stream')
                            part.set_payload(attachment.read())
                            encoders.encode_base64(part)
                            part.add_header(
                                'Content-Disposition',
                                f'attachment; filename= {os.path.basename(file_path)}'
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
    
    def _send_webhook_email(self, to_emails: List[str], subject: str, body: str, 
                           html_body: Optional[str] = None, attachments: Optional[List[str]] = None) -> bool:
        """Send email using webhook"""
        if not self.webhook_url:
            logger.warning("Email webhook URL not configured")
            return False
        
        payload = {
            'to_emails': to_emails,
            'subject': subject,
            'body': body,
            'html_body': html_body,
            'attachments': attachments,
            'timestamp': str(datetime.utcnow())
        }
        
        try:
            response = requests.post(
                self.webhook_url,
                json=payload,
                timeout=30
            )
            return response.status_code == 200
        except Exception:
            logger.exception("Webhook error")
            return False
    
    def _send_local_email(self, to_emails: List[str], subject: str, body: str, 
                         html_body: Optional[str] = None, attachments: Optional[List[str]] = None) -> bool:
        """Simulate email sending locally"""
        logger.info(
            "LOCAL EMAIL SIMULATION to=%s subject=%s attachments=%s",
            ', '.join(to_emails),
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
            if self.provider == 'smtp':
                return self._test_smtp_connection()
            elif self.provider == 'webhook':
                return self._test_webhook_connection()
            else:
                return self._test_local_connection()
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'provider': self.provider
            }
    
    def _test_smtp_connection(self) -> Dict[str, Any]:
        """Testa conexÃ£o SMTP"""
        if not all([self.smtp_server, self.smtp_username, self.smtp_secret]):
            return {
                'success': False,
                'error': 'ConfiguraÃ§Ã£o SMTP incompleta',
                'provider': 'smtp'
            }
        
        try:
            # Testar conexÃ£o SMTP
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.smtp_username, self.smtp_secret)
            server.quit()
            
            return {
                'success': True,
                'provider': 'smtp',
                'message': f'ConexÃ£o SMTP estabelecida com {self.smtp_server}:{self.smtp_port}'
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'provider': 'smtp'
            }
    
    def _test_webhook_connection(self) -> Dict[str, Any]:
        """Testa conexÃ£o com webhook"""
        if not self.webhook_url:
            return {
                'success': False,
                'error': 'URL do webhook nÃ£o configurada',
                'provider': 'webhook'
            }
        
        try:
            response = requests.post(
                self.webhook_url,
                json={'test': True, 'message': 'Teste de conexÃ£o'},
                timeout=10
            )
            
            if response.status_code == 200:
                return {
                    'success': True,
                    'provider': 'webhook',
                    'message': 'ConexÃ£o com webhook estabelecida com sucesso'
                }
            else:
                return {
                    'success': False,
                    'error': f'Erro HTTP {response.status_code}',
                    'provider': 'webhook'
                }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'provider': 'webhook'
            }
    
    def _test_local_connection(self) -> Dict[str, Any]:
        """Testa conexÃ£o local"""
        return {
            'success': True,
            'provider': 'local',
            'message': 'Modo local ativo - email simulado'
        }
    
    def send_welcome_email(self, participant_email: str, participant_name: str, plan_name: str) -> bool:
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

