import logging
from flask import Blueprint, request, jsonify
from src.intelligence.identity import resolve_user_identity, get_best_company_id
from src.intelligence.execution import run_agent_with_context, extract_response_text
from services.whatsapp_service import whatsapp_service
from models import db

whatsapp_webhook_bp = Blueprint('whatsapp_webhook', __name__)
logger = logging.getLogger(__name__)

@whatsapp_webhook_bp.route('/whatsapp', methods=['POST'])
def handle_whatsapp():
    """
    Webhook para recebimento de mensagens do WhatsApp (Z-API).
    Suporta também Instagram Direct se vier pelo mesmo provedor.
    """
    data = request.json
    if not data:
        return jsonify({"status": "no data"}), 400

    # Estrutura padrão Z-API: data['phone'], data['text']['message']
    # Nota: A estrutura pode variar dependendo da configuração da Z-API
    phone = data.get('phone')
    message_text = data.get('text', {}).get('message') or data.get('value') # Fallback para outros formatos
    
    if not phone or not message_text:
        return jsonify({"status": "invalid payload"}), 200 # Z-API espera 200

    logger.info(f"WHATSAPP INBOUND: From {phone} | Msg: {message_text[:50]}...")

    # 1. Resolve Identidade
    user = resolve_user_identity(phone, 'whatsapp')
    if not user:
        # Se não encontrar, podemos logar ou enviar mensagem de "número não vinculado"
        logger.warning(f"WHATSAPP: Telefone {phone} não vinculado a nenhum usuário.")
        return jsonify({"status": "user not found"}), 200

    # 2. Executa o Agente
    try:
        company_id = get_best_company_id(user)
        response = run_agent_with_context(
            user_id=user.id,
            user_msg=message_text,
            channel="whatsapp",
            thread_prefix="wa",
            company_id=company_id,
            metadata={"phone": phone}
        )
        
        response_text = extract_response_text(response)
        
        # 3. Envia Resposta de Volta via WhatsApp
        if response_text:
            whatsapp_service.send_message(phone, response_text)
            
        return jsonify({"status": "success"}), 200
        
    except Exception as e:
        logger.error(f"WHATSAPP WEBHOOK ERROR: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 200

@whatsapp_webhook_bp.route('/instagram', methods=['POST'])
def handle_instagram():
    """Webhook específico para Instagram Direct se separado."""
    data = request.json
    # Logic similar to WhatsApp but identifying by Instagram ID
    # implementation depends on the specific provider payload
    return jsonify({"status": "received"}), 200
