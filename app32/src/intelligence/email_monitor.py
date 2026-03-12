import logging
import os
from typing import Optional
from src.intelligence.identity import resolve_user_identity, get_best_company_id
from src.intelligence.execution import run_agent_with_context, extract_response_text
from models import db

logger = logging.getLogger(__name__)

def process_incoming_email(sender_email: str, subject: str, body: str):
    """
    Processa um e-mail recebido e gera uma resposta via Sapiens Agent.
    """
    logger.info(f"EMAIL INBOUND: From {sender_email} | Subject: {subject}")

    # 1. Resolve Identidade
    from models.user import User
    user = resolve_user_identity(sender_email, 'email')
    
    if not user:
        logger.warning(f"EMAIL: Remetente {sender_email} não reconhecido.")
        return None

    # 2. Executa o Agente
    try:
        company_id = get_best_company_id(user)

        try:
            from services.proactive_service import try_handle_summary_followup
            handled_followup, followup_response = try_handle_summary_followup(
                user=user,
                company_id=company_id,
                incoming_text=body,
                channel="email",
            )
        except Exception as followup_err:
            logger.exception("Falha ao processar follow-up do resumo por e-mail: %s", followup_err)
            handled_followup, followup_response = False, None

        if handled_followup and followup_response:
            return followup_response

        user_msg = f"Assunto: {subject}\n\n{body}"

        response = run_agent_with_context(
            user_id=user.id,
            user_msg=user_msg,
            channel="email",
            thread_prefix="email",
            company_id=company_id,
            metadata={"subject": subject}
        )
        
        response_text = extract_response_text(response)
        
        # 3. Retorna o texto para ser enviado por e-mail
        # O serviço que chama esta função deve ser responsável pelo envio via SMTP.
        return response_text
        
    except Exception as e:
        logger.error(f"EMAIL PROCESSING ERROR: {str(e)}")
        return "Desculpe, ocorreu um erro ao processar seu e-mail."

def fetch_and_process_emails():
    """
    Exemplo de função para ser agendada via Scheduler.
    Faria o polling de uma conta IMAP.
    """
    # Placeholder: IMAP logic would go here
    # For each new email: process_incoming_email(...)
    pass
