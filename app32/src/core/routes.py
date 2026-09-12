from flask import Blueprint, jsonify
import logging

logger = logging.getLogger(__name__)

# Criação do Blueprint para as rotas do núcleo (Core/Body)
core_bp = Blueprint('core', __name__, template_folder='../templates')

@core_bp.route('/chat', methods=['GET'])
def chat_view():
    """Descontinua a UI de chat que não possuía identidade do APP32."""
    return jsonify({
        "error": "legacy_chat_retired",
        "detail": "Use a superfície autenticada /agents/sapiens do APP32.",
    }), 410

@core_bp.route('/api/v2/chat', methods=['POST'])
def chat_api():
    """Bloqueia o runtime legado sem autenticação, tenant ou tool policy."""
    return jsonify({
        "error": "legacy_chat_retired",
        "detail": "Use /api/agents/chat autenticado, que resolve usuário e company_id no runtime oficial.",
    }), 410
