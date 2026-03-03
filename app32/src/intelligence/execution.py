import os
import logging
from typing import Dict, Any, List, Optional
from src.intelligence.tool_context import set_sapiens_context, reset_sapiens_context
from src.intelligence.memory import get_checkpointer
from src.intelligence.work_agents.graph import create_work_agent_workflow

logger = logging.getLogger(__name__)

def run_agent_with_context(
    user_id: int,
    user_msg: str,
    channel: str = "web",
    thread_prefix: str = "chat",
    thread_id: Optional[str] = None,
    company_id: Optional[int] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Executa o workflow do Agente Sapiens com gestão de contexto unificada (@ARQUITETO).
    Suporta: Web, Telegram, Instagram, WhatsApp, E-mail.
    """
    # 1. Identificação de Empresa (Fallback se não fornecido)
    if not company_id:
        from models.employee import Employee
        first_emp = Employee.query.filter_by(user_id=user_id).first()
        if first_emp:
            company_id = first_emp.company_id

    # 2. Configura a Thread do LangGraph
    if not thread_id:
        thread_id = f"{thread_prefix}_{user_id}"
    
    config = {"configurable": {"thread_id": thread_id}}
    
    # --- CONTEXTO DE AGENTE (Thread-Safe) ---
    token = set_sapiens_context(
        user_id=user_id,
        company_id=company_id,
        channel=channel,
        thread_id=thread_id,
        metadata=metadata
    )
    
    # Set legacy env vars (@ARQUITETO requirement for some old services)
    os.environ['ACTIVE_USER_ID'] = str(user_id)
    if company_id:
        os.environ['ACTIVE_COMPANY_ID'] = str(company_id)

    try:
        with get_checkpointer() as checkpointer:
            graph = create_work_agent_workflow(checkpointer=checkpointer)
            
            inputs = {"messages": [("user", user_msg)]}
            
            logger.info(f"SAPIENS INVOKE [{channel.upper()}]: Thread {thread_id} | User {user_id}")
            response = graph.invoke(inputs, config=config)
            return response
            
    except Exception as e:
        logger.error(f"SAPIENS ERROR [{channel.upper()}]: {str(e)}")
        raise e
    finally:
        # Cleanup
        if 'ACTIVE_COMPANY_ID' in os.environ:
            del os.environ['ACTIVE_COMPANY_ID']
        if 'ACTIVE_USER_ID' in os.environ:
            del os.environ['ACTIVE_USER_ID']
        reset_sapiens_context(token)

def extract_response_text(response: Dict[str, Any]) -> str:
    """Extrai o texto final da resposta do LangGraph."""
    final_messages = response.get("messages", [])
    if not final_messages:
        return "Desculpe, não consegui processar sua solicitação."
        
    last_message = final_messages[-1]
    
    # Se for dict/list (LangGraph schema)
    if hasattr(last_message, 'content'):
        return last_message.content
    
    # Se for o formato de tupla (human/ai, content)
    if isinstance(last_message, tuple):
        return last_message[1]
    
    # Se for string
    return str(last_message)
